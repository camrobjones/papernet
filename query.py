"""
Querying
--------
Access models and perform complex queries
"""

from collections import Counter

from django.db.models import Count, Q, F, Func

from papernet import models
from papernet.models import (Paper, Perusal, Reader, Journal, Author)


"""
Helper functions
----------------
"""

"""
Query Class
-----------
General Purpose Data Query Class
"""

class Query():
    """
    General Purpose Data Query Class
    """

    def __init__(self):
        pass

    def get(self, model, fields=None, filter=None, order=None, limit=None):
        """Retrieve data from the database"""
        model = models.get(model)




"""
Reader
------
Query for items relevant to a reader
"""


def top_journals_for_reader(reader, n=5):
    """Return the top n journals for reader by number of perusals for their papers"""
    cond = Q(publication__paper__perusal__reader=reader)
    agg = Count('publication__paper__perusal', filter=cond)
    annotated = Journal.objects.annotate(n_papers=agg)
    ordered = annotated.order_by('-n_papers')
    return ordered[:n]


def top_authors_for_reader(reader, n=5):
    """Return the top n journals for reader by number of perusals for their papers"""
    cond = Q(authorship__paper__perusal__reader=reader)
    agg = Count('authorship__paper__perusal', filter=cond)
    annotated = Author.objects.annotate(n_papers=agg)
    ordered = annotated.order_by('-n_papers')
    return ordered[:n]


def latest_papers_for_reader(reader, authors=None, journals=None, n=5):
    """Return recent papers by reader's top author or journal"""
    authors = authors or top_authors_for_reader(reader)
    journals = journals or top_journals_for_reader(reader)

    in_authors = Q(authorship__author__in=authors)
    in_journals = Q(publication__journal__in=journals)
    has_pub_date = Q(publication__published__isnull=False)

    papers = Paper.objects.filter(in_authors | in_journals, has_pub_date)
    ordered = papers.order_by('-publication__published')
    return ordered[:n]


"""
Scrape Prioritising
-------------------
"""


def most_cited_missing_dois(n=10, citing_dois=None):
    """Get the n most cited dois that do not exist in the db"""
    fieldname = 'cited_doi'
    refs = Reference.objects.filter(cited_paper=None)

    if citing_dois is not None:
        refs = refs.filter(citing_doi__in=citing_dois)

    refs = refs.values(fieldname).order_by(fieldname)
    refs = refs.annotate(the_count=Count(fieldname))
    top_dois = refs.order_by('-the_count')[:10]
    return top_dois


def most_cited_missing_for_project(project=None, n=10):
    """Get the n most cited missing dois for a project"""
    proj_dois = list(project.perusal_set.values_list('paper__doi', flat=True))
    missing_dois = most_cited_missing_dois(n=n, citing_dois=proj_dois)


"""
Similarity
----------
"""

# TODO: Improve model similarity
# - Class which stores ratio info etc
# - Relative similarity (not just raw cites!)
# - Cache


def get_shared_refs(papers):
    """Get a counter of shared refs by papers"""
    tally = Counter()
    for paper in papers:
        tally.update(paper.cited_papers(n=None, order=None))
    return tally


def get_shared_cites(papers):
    """Get a counter of shared refs by papers"""
    tally = Counter()
    for paper in papers:
        tally.update(paper.citing_papers(n=None, order=None))
    return tally


def _get_similar_papers(refs, cites):
    """Get a counter of papers which share refs and cites"""
    ref_cites = get_shared_cites(refs)
    cite_refs = get_shared_refs(cites)
    total = ref_cites + cite_refs
    return total


def get_similar_papers(papers, n=5):
    """Return most similar papers"""
    refs = get_shared_refs(papers)
    cites = get_shared_cites(papers)
    similar = _get_similar_papers(refs, cites)

    return similar.most_common(n)
