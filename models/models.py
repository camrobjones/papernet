"""
Django db models to store paper info
"""
import re
from collections import Counter
from operator import itemgetter
import logging
from datetime import datetime as dt

from django.conf import settings
from django.db import models
from django.db.models import Q, Count, Sum, Max, Min
from django.utils import timezone as tz

from papernet import sources
from papernet.sources import crossref
from papernet.data import cleaning

# Get an instance of a logger
logger = logging.getLogger(__name__)
"""
DB architecture stolen from:
https://www.isi.fraunhofer.de/content/dam/isi/dokumente/cci/innovation-systems-policy-analysis/2010/discussionpaper_22_2010.pdf
"""

DEFAULT_STATUSES = ("Read", "Not read", "In Progress")

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATE_FIELDS = ["published-print", "published-online", "issued", "created"]


PREPOSITIONS = ["in", "by", "on", "for", "to", "from", "when", "after"]
PREP_REGEX = re.compile(" | ".join(PREPOSITIONS), re.I)
PUNCT_REGEX = re.compile("[.:(-] ")
NUM_REGEX = re.compile("[1-9]+")

"""
Helper function
---------------
# TODO: Move to utils and funcs to storage
"""


def _safe_update(model, data, overwrite=False):
    """Only add data if model data is blank"""

    model_fields = [f.name for f in model._meta.get_fields()]

    for field, value in data.items():

        if field not in model_fields:
            logger.warning("Bad field passed to %s: %s", model, field)
            continue

        current = getattr(model, field)

        if overwrite or not current:

            if not value:
                logger.warning("No %s found for %s: %s", field, model, value)

            else:
                setattr(model, field, value)

        else:
            if current != value:
                logger.warning("Not overwriting %s on %s with %s",
                               field, model, value)


def extract_date(date_obj):
    """Helper to extract dates from crossref dates"""

    if not date_obj:
        return None

    if date_obj.get('date-time'):
        try:
            return dt.strptime(date_obj['date-time'], ISO_FORMAT)
        except ValueError:
            pass

    if date_obj.get('timestamp'):
        try:
            timestamp = date_obj['timestamp']
            if timestamp > 1e10:
                timestamp = timestamp / 1000
            return dt.fromtimestamp(timestamp)
        except ValueError:
            pass

    if date_obj.get('date-parts'):
        date_parts = date_obj['date-parts']
        if date_parts:
            date = date_parts[0] + [1, 1, 1]
            return tz.datetime(*date[:3])

    return None


def extract_dates(data):
    """Parse dates for date keys"""
    dates = {}
    for key in DATE_FIELDS:
        try:
            dates[key] = extract_date(data[key])
        except:
            pass

    return dates


def truncate_title(title, max_len=50, min_len=10):
    title = re.sub("\s+", " ", title)
    if len(title) < max_len:
        return title

    for pattern in [PUNCT_REGEX, NUM_REGEX, PREP_REGEX]:

        title_parts = re.split(pattern, title)

        # Take the first part if it's not too short
        if len(title_parts[0]) > min_len and len(title_parts[0]) < max_len:
            return title_parts[0]

        # If it is, try the first two together
        if len(title_parts[0]) < min_len:

            if len(title_parts) > 2:

                try:
                    title = re.match(f".*{title_parts[1]}", title).group()
                    if len(title) > min_len and len(title) < max_len:
                        return title

                except AttributeError:
                    # TODO: Find out where this happens
                    logger.error("Title parts not found: %s", title)

        # Use the first part of the title
        elif len(title_parts[0]) > max_len:
            title = title_parts[0]

    return f"{title[:max_len-3]}..."


"""
Object Classes
--------------
"""


class Author(models.Model):
    """Author"""
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    website = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    scholar = models.URLField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def from_crossref(self, author_data):
        """Retrieve metadata from crossref"""
        self.first_name = author_data.get('given', '')
        self.last_name = author_data.get('family', '')
        self.save()

    @property
    def paper_count(self):
        """Number of published papers"""
        return self.authorship_set.count()

    def citation_count(self):
        """Total citations (with optional filters)"""
        papers = self.get_papers(n=None)
        result = papers.aggregate(Sum('citations__count'))
        return result['citations__count__sum']

    def get_papers(self, n=5, order='-citations__count'):
        """Get papers written by the author"""
        papers = Paper.objects.filter(authorship__in=self.authorship_set.all())
        if order is not None:
            papers = papers.annotate(Count('citations'))
            papers = papers.order_by(order)
        return papers[:n]

    def get_coauthors(self, n=5, order='-coauthorships'):
        """Get coauthors"""
        papers = self.get_papers(n=None)
        aships = Authorship.objects.filter(paper__in=papers)
        authors = Author.objects.filter(authorship__in=aships).exclude(pk=self.pk)
        if order is not None:
            authors = authors.annotate(coauthorships=Count('authorship', Q(pk__in=aships)))
            authors = authors.order_by(order)
        authors = authors[:n]
        out = []
        for author in authors:
            data = author.preview
            data['coauthorships'] = author.coauthorships
            data['top_paper'] = str(author.get_papers(n=1).first())
            out.append(data)
        return out

    @property
    def preview(self):
        """Light data"""
        out = {"last_name": self.last_name,
               "name": str(self),
               "paper_count": self.paper_count,
               "citation_count": self.citation_count(),
               "pk": self.pk}
        return out

    @property
    def data(self):
        """Get data about author objects"""
        out = {"first_name": self.first_name,
               "last_name": self.last_name,
               "name": str(self),
               "pk": self.pk,
               "paper_count": self.paper_count,
               "citation_count": self.citation_count()}
        out['papers'] = [p.data for p in self.get_papers()]
        out['coauthors'] = self.get_coauthors(n=5)
        return out

    def create_authorship(self, paper, position):
        """Create authorship relationship"""
        authorship = Authorship(author=self,
                                paper=paper,
                                position=position)
        authorship.save()
        return authorship


class Paper(models.Model):
    """Paper"""
    title = models.CharField(max_length=200)
    short_title = models.CharField(max_length=50, blank=True)
    subtitle = models.CharField(max_length=200, blank=True, default="")

    doi = models.CharField(max_length=128, unique=True)
    article_type = models.CharField(max_length=128, blank=True)

    abstract = models.TextField(blank=True, default="")
    keywords = models.TextField(blank=True, default="")
    references_count = models.IntegerField(default=0)
    is_referenced_by_count = models.IntegerField(default=0)

    retrieved = models.DateTimeField(blank=True, default=None, null=True)
    updated = models.DateTimeField(blank=True, default=None, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ref or self.short_title or self.doi

    @property
    def ref(self):
        """Author (year) representation"""
        author_names = [a.last_name for a in self.authors if a.last_name]
        if len(author_names) < 3:
            author_string = " & ".join(author_names)
        else:
            author_string = f"{author_names[0]} et al."

        if self.year:
            author_string += f" ({self.year})"
        return author_string

    @property
    def authors(self):
        """Return Author objects associated with Paper"""
        # TODO: ensure author ordering
        authorships = Authorship.objects.filter(paper=self.pk)
        paper_authors = [a.author for a in authorships]
        return paper_authors

    @property
    def publication(self):
        """Paper's publication"""
        publications = self.publication_set.all()

        if publications.count() != 1 and self.retrieved:
            logger.error("Paper id(%s) has %s publications.",
                         self.pk, publications.count())

        if publications.count() == 0:
            publication = Publication.objects.create(paper=self)
            return publication

        return publications.first()

    @property
    def year(self):
        """Year of publication"""
        pub = self.publication
        if pub and pub.published:
            return getattr(pub.published, 'year')
        return None

    @property
    def journal(self):
        """Journal paper was published in"""
        if self.publication is None:
            return Journal()

        if self.publication.journal is None:
            return Journal()

        return self.publication.journal

    @property
    def preview(self):
        """Serializable data"""
        out = {
            "title": self.title,
            "short_title": self.short_title,
            "ref": self.ref,
            "doi": self.doi,
            "cites": self.citation_count,
            "pk": self.pk,
            "year": self.year,
        }
        return out

    @property
    def data(self):
        """Serializable data"""
        out = {
            "title": self.title,
            "short_title": self.short_title,
            "ref": self.ref,
            "authors": [a.preview for a in self.authors],
            "year": self.year,
            "doi": self.doi,
            "cites": self.citation_count,
            "refs": self.reference_count,
            "updated": self.updated,
            "journal": self.journal.preview,
            "volume": self.publication.volume,
            "issue": self.publication.issue,
            "pages": self.publication.pages,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "pk": self.pk
        }
        return out

    def cited_papers(self, n=5, order='-citations__count'):
        """List of papers which this paper cites"""
        papers = Paper.objects.filter(cited_by__in=self.citations.all())
        if order is not None:
            papers = papers.annotate(models.Count('citations'))
            papers = papers.order_by(order)
        return papers[:n]

    def citing_papers(self, n=5, order='-citations__count'):
        """List of papers which cite this paper"""
        papers = Paper.objects.filter(citations__in=self.cited_by.all())
        if order is not None:
            papers = papers.annotate(models.Count('citations'))
            papers = papers.order_by(order)
        return papers[:n]

    @property
    def citation_count(self):
        """Number of citations the paper has received"""
        return self.cited_by.count()

    @property
    def reference_count(self):
        """Number of citations the paper contains"""
        return self.citations.count()

    def from_crossref(self, data, citations=True):
        """Retrieve metadata from crossref"""
        title = data.get('title')
        short_title = data.get('short-title')
        if isinstance(short_title, list) and short_title:
            short_title = short_title[0]
        # Warn if title retrieve fails
        if not title:
            logger.warning("title not found for doi: %s", self.doi)
            # TODO: Take short title?
        else:
            title = title[0]
            title = truncate_title(title, 200, 20)
            self.title = title
            short_title = short_title or title
            self.short_title = truncate_title(short_title, 50, 10)

        # filter out keys
        update_data = {}
        update_data['article_type'] = data.get('type', '')
        update_data['is_referenced_by_count'] = data.get(
            'is-referenced-by-count', 0)
        update_data['references_count'] = data.get(
            'references-count', 0)
        update_data['abstract'] = data.get('abstract', '')

        # safe update
        _safe_update(self, update_data, overwrite=True)

        self.retrieve_authors(data.get('author', []))

        # Store update info
        self.retrieved = tz.now()
        self.updated = tz.now()
        self.save()

        return self

    def retrieve_authors(self, data):
        """Retrieve author data"""
        authorships = []
        for entry in data:

            # Extract data
            first = entry.get('given', '')
            last = entry.get('family', '')
            affiliations = entry.get('affiliation', '')
            position = entry.get('sequence', '')

            # Get or create author
            author, created = Author.objects.get_or_create(
                first_name=first, last_name=last)

            # Check if authorship exists
            ship = Authorship.objects.filter(author=author, paper=self)
            if not ship.exists():
                authorship = author.create_authorship(self, position)

                # Author affiliations
                for affiliation in affiliations:
                    authorship.create_affiliation(self, affiliation)

                authorships.append(authorship)
        return authorships

    def retrieve_citations(self):
        """Retrieve and save citations as papers"""
        logger.info("Retrieving citations for %s", self)
        c, t0 = Counter(), tz.now()

        citations = Reference.objects.filter(citing_doi=self.doi)
        logger.debug("Identified %s citations", citations.count())

        for ref in citations:
            if self.__class__.objects.filter(doi=ref.cited_doi).first() is None:
                ref_p = self.__class__(doi=ref.cited_doi)
                ref_p.save()
                ref_p.retrieve()
                ref.cited_paper = ref_p
                ref.save()
                c['added'] += 1
            else:
                c['duplicate'] += 1

        delta = (tz.now()-t0).total_seconds()
        logger.info("Retrieval complete in %ss. %s added and %s duplicates",
                    delta, c['added'], c['duplicate'])

    def add_citations(self, data):
        """Add citations"""
        references = data.get('reference', [])
        tally = Counter()
        logger.debug("Adding %s citations for %s", len(references), self)
        for ref in references:
            ref_doi = ref.get("DOI")

            if ref_doi is None:
                # logger.debug("Missing citation: %s", ref)
                tally['missing doi'] += 1
                continue

            cited = self.__class__.objects.filter(doi=ref_doi).first()
            reference, c = Reference.objects.get_or_create(
                citing_doi=self.doi,
                cited_doi=ref_doi,
                defaults={"citing_paper": self,
                          "cited_paper": cited}
                )
            if c:
                reference.from_crossref(ref)
                reference.save()
                tally['added'] += 1
            else:
                tally['duplicates'] += 1

        logger.debug(dict(tally))

        return tally

    def retrieve(self, citations=True, force=False):
        """Fetch metadata from crossref using API"""
        logger.debug('Retrieving %s; citations=%s, force=%s',
                     self, citations, force)

        start = tz.now()
        if self.retrieved:
            logger.debug('Data already retrieved from doi:%s', self.doi)
            if not force:
                return None

        result = sources.get_work(self.doi)
        data = result.data
        self.from_crossref(data, citations=citations)

        delta = (tz.now() - start).total_seconds()
        logger.info("Retrieved '%s' in %s", self, delta)

        return data


class Institution(models.Model):
    """Institution"""
    name = models.CharField(max_length=128)
    url = models.URLField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    post_code = models.CharField(max_length=128, blank=True)
    street = models.CharField(max_length=128, blank=True)
    country = models.CharField(max_length=128, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    raw = models.TextField(default="", blank=True)


class Container(models.Model):
    """Parent Class for Journal and Book"""


class Journal(models.Model):
    """Journal"""
    title = models.CharField(max_length=256, blank=True)
    abbreviation = models.CharField(max_length=128, blank=True)

    issn = models.CharField(max_length=128, unique=True)
    electronic_issn = models.CharField(max_length=128, blank=True)
    print_issn = models.CharField(max_length=128, blank=True)
    journal_type = models.CharField(max_length=128, blank=True)

    total_doi = models.IntegerField(default=0)
    publisher = models.CharField(blank=True, default="", max_length=128)

    last_updated = models.DateTimeField(blank=True, null=True, default=None)
    last_retrieved = models.DateTimeField(blank=True, null=True, default=None)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        label = self.abbreviation or self.title
        if len(label) > 10:
            label = label[:7] + "..."

        return f"{label} ({self.pk})"

    @property
    def preview(self):
        """Serializable data about Journal"""
        out = {"title": self.title,
               "pk": self.pk}
        return out

    @property
    def data(self):
        """Serializable data about Journal"""
        out = {"title": self.title,
               "abbreviation": self.abbreviation,
               "journal_type": self.journal_type,
               "paper_count": self.paper_count,
               "volumes": self.get_volumes(),
               "pk": self.pk}
        return out

    def get_papers(self, n=5, order="-publication__published"):
        """Get papers published in journal"""
        publications = self.publication_set.all()
        papers = Paper.objects.filter(publication__in=publications)
        if order is not None:
            papers = papers.order_by(order)
        return papers[:n]

    def get_volumes(self):
        """List of volumes"""
        pubs = self.publication_set.values('volume').order_by('volume')
        vols = pubs.annotate(n=Count('volume'), pub_from=Min('published'),
                             pub_to=Max('published'))
        return vols.order_by('-pub_to')

    @property
    def paper_count(self):
        """Number of publications"""
        return self.get_papers(n=None, order=None).count()

    def get_authors(self, n=5, order='-journal_papers'):
        """Get authors who have published in journal"""
        papers = self.get_papers(n=None)
        authors = Author.objects.filter(authorship__paper__in=papers)

        if order is not None:
            in_journal = Count('authorship', Q(authorship__paper__in=papers))
            authors = authors.annotate(journal_papers=in_journal)
            authors = authors.order_by(order)
        return authors[:n]

    def from_crossref(self, data, save=True):
        """Retrieve institution from data"""
        update = {}
        update['title'] = data.get('container-title', [""])[0]
        update['abbreviation'] = data.get('short-container-title', [""])[0]
        issn = cleaning.get_issn(data)
        update.update(issn)

        _safe_update(self, update)

        if save:
            self.save()

    def retrieve_data(self, save=True):
        """Retrieve Journal data from crossref"""

        # Request data from crossref
        raw_data = crossref.get_journal(self.issn)

        # Extract ISSN
        data = cleaning.get_issn(raw_data)

        if self.issn not in data.values():
            raise ValueError("Retrieved data for Journal"
                             "(%s) has different ISSN: %s", self.issn, data)

        data['title'] = raw_data.get("title", "")
        data['total_doi'] = raw_data.get('counts', {}).get('total-dois', 0)
        data['publisher'] = raw_data.get('publisher', "")

        for subject in raw_data['subjects']:

            name = subject.get('name')
            code = subject.get('code')

            if name and code:
                topic, created = Topic.objects.get_or_create(
                    name=name, code=code, journal=self, topic_type="ASJC")

        # Subjects

        _safe_update(self, data, overwrite=True)

        self.last_retrieved = tz.now()

        if save is True:
            self.save()

        return raw_data


"""
Relationship Classes
--------------
"""


class Authorship(models.Model):
    """Authorship"""
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
    )
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
    )
    position = models.CharField(max_length=128, blank=True)

    def __repr__(self):
        return f"<Authorship: {self.author.last_name} ({self.paper})>"

    def create_affiliation(self, paper, affiliation):
        """Create affiliation for paper"""
        name = affiliation.get('name')
        if name is None:
            return None
        institution, created = Institution.objects.get_or_create(raw=name)
        aff, created = Affiliation.objects.get_or_create(
            authorship=self, institution=institution)


class Affiliation(models.Model):
    """Affiliation"""
    authorship = models.ForeignKey(
        Authorship,
        on_delete=models.CASCADE,
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    email = models.CharField(max_length=128, blank=True)


class Reference(models.Model):
    """Reference"""
    class Meta:
        """Ensure unique references"""
        unique_together = ['citing_doi', 'cited_doi']

    citing_doi = models.CharField(max_length=128)
    cited_doi = models.CharField(max_length=128)

    citing_paper = models.ForeignKey(
        Paper,
        related_name="citations",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    cited_paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
        related_name="cited_by",
        blank=True,
        null=True,
    )
    created = models.DateTimeField(auto_now_add=True)

    oci = models.CharField(max_length=1024, blank=True, default="")
    author = models.CharField(max_length=128, blank=True)
    journal = models.CharField(max_length=128, blank=True)
    title = models.CharField(max_length=128, blank=True)
    publication_year = models.CharField(max_length=128, blank=True)
    cit_key = models.CharField(max_length=128, blank=True)

    def from_crossref(self, data):
        """Extract data from crossref dict format"""
        self.author = data.get('author', '')
        self.journal = truncate_title(data.get('journal-title', ''), 128)
        self.title = truncate_title(data.get('volume-title', ''), 128)
        self.publication_year = data.get('year', '')
        self.cit_key = data.get('key', '')


class Publication(models.Model):
    """Publication"""
    journal = models.ForeignKey(
        Journal,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
    )

    published = models.DateField(blank=True, null=True)
    published_online = models.DateField(blank=True, null=True)
    published_print = models.DateField(blank=True, null=True)

    volume = models.CharField(max_length=128, blank=True)
    issue = models.CharField(max_length=128, blank=True)
    pages = models.CharField(max_length=128, blank=True)
    source = models.URLField(blank=True, null=True)

    file = models.FileField(upload_to='papernet/publications/',
                            blank=True, null=True, default=None)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{str(self.paper)} - {str(self.journal)} ({self.pk})"

    def from_crossref(self, data):
        """Retrieve publication from data"""
        dates = extract_dates(data) or extract_dates(
            data.get('journal-issue'), {})

        if any(dates):
            self.published_online = dates.get("published_online")
            self.published_print = dates.get("published_online")

            self.published = min(dates.values())

        # file
        self.volume = data.get('volume', '')
        self.issue = data.get('issue', '')
        self.pages = data.get('pages', '')
        self.source = data.get('source', '')
        self.save()


class Topic(models.Model):
    """Subject areas for Journals and Papers"""
    name = models.CharField(max_length=128)
    code = models.IntegerField(unique=True)
    journal = models.ForeignKey(
        Journal,
        on_delete=models.CASCADE,
        related_name="topics",
        related_query_name="topic"
    )
    topic_type = models.CharField(max_length=128, blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ensure unique references"""
        unique_together = ['code', 'journal', 'topic_type']


class PaperText(models.Model):
    """Paper"""
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
    )
    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    pdf = models.FileField(upload_to='papernet/files/papers/',
                           blank=True, null=True, default=None)
    link = models.URLField(blank=True, null=True, default=None)
    header = models.TextField(blank=True, default="")
    abstract = models.TextField(blank=True, default="")
    keywords = models.TextField(blank=True, default="")
    body = models.TextField(blank=True, default="")
    acknowledgements = models.TextField(blank=True, default="")
    references = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(blank=True, null=True, default=None)


"""
User classes
"""


class Reader(models.Model):
    """Associate custom data with user"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(default=tz.now)
    image = models.ImageField(upload_to='papernet/',
                              default="papernet/guest.jpg")
    bio = models.TextField(blank=True, default="")

    def get_perusals(self, n=5, order='-last_active'):
        """Retrieve paperships associated with reader"""
        perusals = self.perusal_set.all()
        if order is not None:
            perusals = perusals.order_by(order)
        return perusals[:n]

    def get_projects(self, n=5, order='-last_active'):
        """Retrieve reader's projects"""
        projects = self.project_set.all()
        if order is not None:
            projects = projects.order_by(order)
        return projects[:n]

    @property
    def projects(self):
        return self.get_projects(n=None)

    @property
    def data(self):
        """Serializable Perusal data"""
        papers = [p.preview for p in self.get_perusals()]

        projects = [p.preview for p in self.get_projects()]

        out = {"username": self.user.username,
               "created": self.created,
               "created": self.created.isoformat(),
               "last_active": self.last_active.isoformat(),
               "last_active": self.last_active,
               "image_url": self.image.url,
               "image": self.image.url,
               "papers": papers,
               "projects": projects,
               "guest": False}
        return out


class Project(models.Model):
    """Collection of Papers"""
    reader = models.ForeignKey(
        Reader,
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=80)
    description = models.TextField(blank=True, default="")
    primary = models.BooleanField(default=False)
    last_active = models.DateTimeField(default=tz.now)

    def paper_count(self):
        """No of papers in project"""
        # TODO: distinct papers? Multiple authors
        return self.perusal_set.count()

    def get_papers(self):
        """Get papers related to the project"""
        # TODO: rename "get_perusals" or ensure perusals can behave as papers
        return self.perusal_set.all()

    def get_statuses(self):
        """Get a list of all Perusal statuses"""
        # TODO: Make more performant
        papers = self.get_papers()
        statuses = set([p.status for p in papers])
        statuses.update(DEFAULT_STATUSES)
        return list(statuses)

    def get_tags(self):
        """Get a list of all Perusal tags"""
        # TODO: Make more performant
        papers = self.get_papers()
        c = Counter()
        [c.update(p.tags) for p in papers]
        return c.most_common()

    @property
    def preview(self):
        """Serializable Project data"""
        out = {"title": self.title,
               "paper_count": self.paper_count(),
               "last_active": self.last_active,
               "pk": self.pk}
        return out

    @property
    def data(self):
        out = self.preview
        out['description'] = self.description
        out['statuses'] = self.get_statuses()
        out['tags'] = self.get_tags()
        return out


class Perusal(models.Model):
    """Relationship between Reader and Paper"""
    reader = models.ForeignKey(
        Reader,
        on_delete=models.CASCADE,
    )
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(default=tz.now)
    notes = models.TextField(blank=True, default="")
    status = models.CharField(blank=True, default="None", max_length=150)
    status_updated = models.DateTimeField(default=tz.now)
    rating = models.IntegerField(default=0)
    priority = models.IntegerField(default=0)

    def __repr__(self):
        name, ref, = self.reader.user.username, self.paper.ref
        title = self.project.title
        return f"<Perusal: {name} {ref} {title}>"

    @property
    def tags(self):
        return [t.content for t in self.tag_set.all()]

    def add_tag(self, content):
        """Add a tag to the perusal"""
        tag, created = Tag.objects.get_or_create(perusal=self, content=content)
        if not created:
            logger.warning("Tag '%s' already exists", content)
        return tag

    def remove_tag(self, content):
        """Remove a tag"""
        tag = self.tag_set.filter(content=content).first()
        if tag is None:
            logger.warning("Tag '%s' does not exist", content)
            return
        tag.delete()



    @property
    def metadata(self):
        """Perusal specific data"""
        out = {"created": self.created,
               "last_active": self.last_active,
               "notes": self.notes,
               "status": self.status,
               "status_updated": self.status_updated,
               "rating": self.rating,
               "priority": self.priority,
               "pk": self.pk,
               "tags": self.tags,
               "project": {"pk": self.project.pk,
                           "title": self.project.title}}
        return out


    @property
    def data(self):
        """Perusal data. Paper data plus metadata."""
        out = self.paper.data
        out["meta"] = self.metadata
        return out

    @property
    def preview(self):
        """Preview of serializable data"""
        paper = self.paper
        out = {"pk": paper.pk,
               "ref": paper.ref,
               "title": paper.title,
               "cites": paper.citation_count,
               "last_active": self.last_active}
        return out


class Tag(models.Model):
    """Tags which associate Perusals with Papers"""
    perusal = models.ForeignKey(
        Perusal,
        on_delete=models.CASCADE,
    )
    content = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)
