"""
Helper functions for views.py
"""
import logging
import re
from collections import Counter

from django.db import IntegrityError
from django.db.models import Q
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from papernet import sources, query
from papernet.sources import crossref
from papernet import models
from papernet.data import cleaning
from papernet.models import Reader, Project, Paper, Perusal, Reference

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


"""
Helper Functions
----------------
"""


def _data(models, flag=True):
    """Utility to serialize models and query sets

    Parameters
    ----------
    models : iterable of papernet.model


    """

    # To make calling easier
    if flag is False:
        return models

    return [m.data for m in models]


def decode(obj):
    """Helper function to decode JSON floats and ints as numeric."""
    if isinstance(obj, str):
        # First attempt to parse as float
        try:
            return float(obj)
        except ValueError:
            # Then try int
            try:
                return int(obj)
            except ValueError:
                # Then accept string
                return obj
    elif isinstance(obj, dict):
        return {k: decode(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decode(v) for v in obj]
    else:
        return obj


"""
User functions
--------------
Create and manage users
"""


def setup_primary_project(reader):
    """Create initial primary project for reader"""

    # Check no other project exists for the reader
    assert Project.objects.filter(reader=reader).exists() is False

    logger.info("Creating primary project for reader %s", reader)
    project = Project(reader=reader, title="My Papers",
                      description="Default Project", primary=True)

    # TODO: worry about deleting primary project
    project.save()

    return project


def create_reader(user):
    """Create a new reader for the user"""
    reader = Reader(user=user)
    reader.save()

    project = setup_primary_project(reader)

    return reader


def get_reader(user):
    """Get or create a Reader for the user"""
    if isinstance(user, int):
        User = get_user_model()
        user = User.objects.get(pk=user)

    if not user.is_authenticated:
        logger.error("Cannot create Reader for user %s, not authenticated")
        return False

    reader = Reader.objects.filter(user=user).first()

    if reader is None:
        reader = create_reader(user)

    return reader


def get_user(request):
    """Retrieve user data from request"""
    user = request.user
    if not user.is_authenticated:
        return {"is_authenticated": False}

    reader = get_reader(user)

    data = reader.data

    data["is_authenticated"] = True

    return data


def get_perusal_by_id(perusal_id, user):
    """Get perusal and ensure user is reader"""
    reader = get_reader(user)
    perusal = Perusal.objects.get(pk=perusal_id)

    if perusal.reader != reader:
        raise PermissionDenied("User does not have access to Perusal")

    return perusal


def get_reader_top(reader, data=False):
    """Return the top journals, authors, and papers for the user"""
    journals = query.top_journals_for_reader(reader)
    authors = query.top_authors_for_reader(reader)
    latest = query.latest_papers_for_reader(reader, authors, journals)

    reader_papers = Paper.objects.filter(pk__in=reader.perusal_set.all())
    top = query.get_similar_papers(reader_papers)

    if data is True:
        journals = [j.data for j in journals]
        authors = [a.data for a in authors]
        latest = [p.preview for p in latest]
        top = [p.data for p, c in top]

    return {"journals": journals, "authors": authors,
            "latest": latest, "top": top}


"""
Scraping
--------
Functions to query and add data
"""


def get_work(doi_raw, retrieve=True):
    """Retrieve data from doi and store in db"""

    doi = cleaning.clean_doi(doi_raw)
    if doi is None:
        raise ValueError("DOI is not valid: %s" % (doi_raw))

    paper = Paper.objects.filter(doi=doi).first()
    if paper is not None:
        logger.debug("Paper already exists")
        return paper

    if retrieve is not True:
        logger.debug("Paper does not exist, retrieve=False. Returning None")
        return

    logger.info("Retrieving paper: %s", doi)
    data = crossref.get_work(doi)

    if data.get('DOI') is None:
        raise ValueError("DOI (%s) returned bad data: %s" % doi, data)

    paper = add_work(data)

    return paper


def add_work(data, citations=True, force=False):
    """Add work to database from crossref data"""
    doi = data['DOI']
    paper, created = Paper.objects.get_or_create(doi=doi)

    if not created and not force:
        logger.debug("Paper already exists: %s", paper)
        if paper.retrieved and not force:
            return paper

    paper.from_crossref(data)

    # Authors
    paper.retrieve_authors(data.get('author', []))

    # Journal
    issn = cleaning.get_issn(data)

    if issn['issn']:
        journal = get_journal_by_issn(issn["issn"])

        if journal is None:
            try:
                journal = models.Journal.objects.create(**issn)
                journal.from_crossref(data)
                logger.info("Created new journal: %r", journal)
            except IntegrityError:
                # TODO: Find out why this happens
                logger.error("Could not create Journal for "
                             "%s: Duplicate ISSN: %s", paper, issn)

    else:
        logger.error("Could not create Journal for "
                     "%s: No issn available: %s", paper, issn)
        journal = None

    # Publication
    publication, created = models.Publication.objects.get_or_create(
        paper=paper, journal=journal)
    publication.from_crossref(data)

    # Citations
    if citations:
        logger.debug("Adding citations for %s", paper)
        paper.add_citations(data)

        _ = get_cited_by(paper)

    paper.save()
    return paper


def get_cited_by(paper, retrieve=False):
    """Retrieve and store all papers which a paper is cited by"""

    # TODO: Find existing refs here

    citation_data = crossref.get_citations(paper.doi)
    logger.debug("Retrieved %s citations for %s", len(citation_data), paper)

    cited_doi = paper.doi

    for res in citation_data:

        citing_doi = res['citing']

        try:
            citing = get_work(citing_doi, retrieve=retrieve)

        except (ValueError, TypeError) as e:
            logger.error(str(e))

        else:
            ref, c = Reference.objects.get_or_create(
                citing_doi=citing_doi,
                cited_doi=cited_doi,
                defaults={"citing_paper": citing,
                          "cited_paper": paper,
                          "oci": res.get('oci', "")}
            )

            if c:
                # Log nonexistence of citing->cited reference
                if citing is not None:
                    logger.error("Backward reference not found: %s", ref)

    return citation_data


"""
Journal
-------
"""


def get_journal_by_issn(issn):
    """Get journal by issn"""
    query = Q(issn=issn) | Q(electronic_issn=issn) | Q(print_issn=issn)
    journals = models.Journal.objects.filter(query)

    if len(journals) > 1:
        logger.info("Merging %s journals with issn: %s", len(journals), issn)
        return merge_journals(*journals)

    return journals.first()


def merge_journals(*args):
    """Merge journals together"""
    if len(args) < 2:
        raise ValueError("Must pass at least two journals")

    print_issn = set([p.print_issn for p in args if p.print_issn])
    if len(print_issn) > 1:
        raise ValueError("All print issn must be equal or '': %r", print_issn)

    electronic_issn = set([p.electronic_issn for p in args if p.electronic_issn])
    if len(print_issn) > 1:
        raise ValueError("All electronic_issn must be equal or '': %r",
                         electronic_issn)

    primary, others = args[0], args[1:]

    primary.print_issn = print_issn.pop()
    primary.electronic_issn = electronic_issn.pop()
    primary.save()

    # Update issn
    for other in others:
        for publication in other.publication_set.all():
            if publication.paper.publication_set.filter(journal=primary).exists():
                publication.delete()
                continue
            publication.journal = primary
            publication.save()
        other.delete()

    return primary



"""
Projects
--------
"""


def get_project_by_id(project_id, reader):
    """Get project by id"""
    project = Project.objects.get(pk=project_id)

    # Ensure reader is correct
    assert project.reader == reader

    return project


def add_to_project(paper, project, reader):
    """Create a new perusal linking the paper, project, and reader"""

    # Check reader has access to project
    assert project.reader.pk == reader.pk

    # Check is unique
    perusal, created = Perusal.objects.get_or_create(paper=paper,
                                                     reader=reader,
                                                     project=project)
    if created:
        logger.debug("Created new perusal: %s", perusal)
    else:
        logger.debug("Perusal already exists: %s", perusal)

    # Create new perusal
    perusal.save()

    return perusal


def get_perusal(paper, project, reader, save=False):
    """Create a new perusal linking the paper, project, and reader"""

    # Check reader has access to project
    assert project.reader.pk == reader.pk

    # Check is unique
    perusal = Perusal.objects.filter(paper=paper, reader=reader,
                                     project=project).first()
    if perusal is not None:
        return perusal

    perusal = Perusal(paper=paper, reader=reader, project=project)

    # Create new perusal
    if save is True:
        perusal.save()

    return perusal


def get_paper_metadata(paper, user):
    """Get perusal info for paper"""
    reader = get_reader(user)
    perusals = Perusal.objects.filter(reader=reader, paper=paper)
    metadata = [perusal.metadata for perusal in perusals]
    projects = [m['project'] for m in metadata]
    return {"projects": projects, "metadata": metadata}


def copy_project(source, target):
    """copy data from source project to target project"""
    reader = source.reader

    # Ensure same reader
    assert reader == target.reader

    for source_perusal in source.perusal_set.all():
        paper = source_perusal.paper
        target_perusal = add_to_project(paper, target, reader)
        target_perusal.notes = source_perusal.notes
        target_perusal.status = source_perusal.status
        target_perusal.status_updated = source_perusal.status_updated
        target_perusal.priority = source_perusal.priority

        for tag in source_perusal.tag_set.all():
            target_perusal.add_tag(tag.content)

        target_perusal.save()

    target.save()
    return target
