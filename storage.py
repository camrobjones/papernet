"""
storage.py
----------
Draws on data source APIs and manages storage in db models
""" 

import json
import logging

from django.utils import timezone as tz
from django.db.models import Count, Q

from papernet import models, aux, sources
from papernet.models.pipeline import Attribution, SourceLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


TWO_YA = tz.now() - tz.timedelta(days=730)
TWO_YA_STR = TWO_YA.strftime("%Y-%m-%d")


"""
Helper functions
----------------
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


"""
Abstract base classes
---------------------
"""


class DataManager():
    """ABC"""
    sources = {}
    model = None
    obj = None

    def retrieve(self):
        """Placeholder"""
        raise NotImplementedError(
            "retrieve not implemented on Abstract Base Class")

    def create_attribution(self, source):
        """Create Attribution linking source to model"""
        logger.debug("Creating attribution with source: %r", source)
        attribution = Attribution(model=self.obj, source=source)
        attribution.save()

    def log_source(self, result):
        """Create a sourcelog from a result"""
        logger.debug("Creating SourceLog for result: %r", result)
        source = SourceLog(request=result.request)
        source.save()

        data = json.dumps(result.data)

        source.store_data(data, file_type='json')

        return source

    def update(self, data, source):
        """Add data to object, create attribution, save

        Args:
            data (sources.Data): Data object
        """

        # Update data
        _safe_update(self.obj, data)

        # Create attribution
        self.create_attribution(source)

    def refresh(self):
        """Refresh data from db"""
        result = self.retrieve()
        source = self.log_source(result)
        self.update(result.data, source)

    @property
    def sources(self):
        attributions = Attribution.objects.filter(model=self.obj)
        sources = [a.source for a in attributions]
        return sources
    


"""
Papers
------
Manage Paper Data
"""


class PaperData(DataManager):
    """Extract and store data for journals"""
    model = "Paper"

    def __init__(self, paper):
        assert isinstance(paper, models.Paper)
        self.obj = paper
        self.paper = paper
        self.doi = self.paper.doi
        self.publication = self.paper.publication

    def retrieve(self):
        """Retrieve data for the model from sources"""
        result = sources.get_work(self.doi)
        return result

    def update_fulltext(self):
        """Update the paper's fulltext attributes"""
        logger.info("Updating fulltext for paper: %r", self.paper)
        self.papertext, created = models.PaperText.objects.get_or_create(
            paper=self.paper, publication=self.publication
            )
        if self.papertext.updated is not None and self.papertext.link is None:
            logger.info("Publication not accessible via API: %r", self.publication)
            return

        # Get fulltext source
        self.fulltext_source = sources.get_fulltext(self.publication)

        # Retrieve source if necessary
        if self.fulltext_source.pdf is None:
            logger.info("Retrieving FulltextSource for %r", self.publication)
            self.fulltext_source.retrieve()

        # Check if source is accessible
        if self.fulltext_source.link is None:
            logger.info("Publication not accessible via API: %r", self.publication)
            self.papertext.updated = tz.now()
            return

        data = self.fulltext_source.data

        # Update DB vals
        _safe_update(self.papertext, data)

        # Update paper abstract
        paper_data = {
            "abstract": data.get("abstract", ""),
            "keywords": data.get("keywords", ""),
        }
        _safe_update(self.paper, paper_data)
        self.paper.save()

        # Add file
        if self.papertext.pdf.name != self.fulltext_source.filename:
            self.papertext.pdf.name = self.fulltext_source.filename

        # Updated
        self.papertext.updated = tz.now()

        self.papertext.save()



"""
Journals
--------
Manage and update Journal Data
"""


class JournalData(DataManager):
    """Extract and store data for journals"""

    def __init__(self, journal):
        assert isinstance(journal, models.Journal)
        self.journal = journal
        self.papers = journal.get_papers(n=None)

    def get_volumes(self):
        """Get volumes """
        pass

    def get_state(self):
        """Get local state of journal and source states"""

        # TODO: Validate ISSN

        # Get local state
        local = {}
        local['total_count'] = self.papers.count()

        local['current_count'] = self.papers.filter(
            publication__published__gte=TWO_YA).count()

        fname = "publication__published__year"
        years = self.papers.values(fname).order_by(fname)
        by_year = years.annotate(n=Count(fname))
        by_year = {y[fname]: y['n'] for y in by_year}

        local['by_year'] = by_year

        years = [year for year in by_year.keys() if year]

        local['max_year'] = max(years)
        local['min_year'] = min(years)

        self.local = local

        cr_data = sources.get_journal(self.journal.issn)

        cr_state = {"raw": cr_data}

        counts = cr_data['counts']

        cr_state['total_count'] = counts['total-dois']
        cr_state['current_count'] = counts['current-dois']

        by_year = cr_data['breakdowns']['dois-by-issued-year']
        by_year = {year: count for year, count in by_year}

        cr_state['by_year'] = by_year

        years = [year for year in by_year.keys() if year]

        cr_state['min_year'] = min(years)
        cr_state['max_year'] = max(years)

        self.sources['crossref'] = cr_state

    def missing_papers(self, year=None):
        """Return the number of missing papers"""
        if year is None:
            cr_total = self.sources['crossref']['total_count']
            local_total = self.local['total_count']
            return cr_total - local_total

        cr = self.sources['crossref']['by_year'].get(year, 0)
        loc = self.local['by_year'].get(year, 0)

        return cr - loc

    def add_papers(self, since=TWO_YA, **kwargs):
        """Add missing papers from sources"""
        years = range(tz.now().year, since.year - 1, -1)

        for year in years:
            missing = self.missing_papers(year=year)

            if missing == 0:
                logger.info("Skipping %s as there are no papers missing",
                            year)
                continue

            # filters = f"from-pub-date:{year-1},until-pub-date:{year}"
            filters = {"from_date": tz.datetime(year, 1, 1),
                       "until_date": tz.datetime(year + 1, 1, 1)}

            kwargs.update({"filters": filters})

            for work in sources.scrape_journal(
                    self.journal.issn, **kwargs):

                aux.add_work(work)

        logger.info()

