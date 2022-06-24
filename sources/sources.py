"""
Sources Main
------------
Dispatch calls to correct source
"""

import logging

from papernet.sources import wiley
from papernet.sources.crossref import CrossRef

crossref = CrossRef()


logger = logging.getLogger(__name__)


def get_fulltext(publication):
    """Return a FulltextSource object from the relevant source"""
    publisher = publication.journal.publisher

    if publisher == "Wiley (Blackwell Publishing)":
        return wiley.WileyFulltextSource(publication.paper)

    logger.warning("No fulltext source found for publisher: %s, (%r)",
                   publisher, publication)


def get_work(doi, **kwargs):
    """Retrieve a paper by doi."""
    # Currently crossref is the only source
    return crossref.get_work(doi, **kwargs)


def search(query):
    """Search for query in sources."""
    # Currently crossref is the only source
    return crossref.search(query)


def get_works():
    pass