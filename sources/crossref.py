"""Crossref API"""

import json
import logging
from urllib.parse import urljoin, urlencode
from collections import Counter

import requests

from django.utils import timezone as tz
from django.core.cache import cache

from papernet.sources.base import DataSource
from papernet.data import cleaning

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
setup request session
---------------------
"""
SESSION = requests.Session()
UA_HEADER = "Papernet/1.1 (https://camrobjones/papernet; "
UA_HEADER += "mailto:crjones94@googlemail.com)"
SESSION.headers.update({"User-Agent": UA_HEADER})


BASE_URL = "https://api.crossref.org/"

WORK_URL = urljoin(BASE_URL, "works/")
JOURNAL_URL = urljoin(BASE_URL, "journals/")


"""
OPEN CITATIONS
"""
COCI_BASE_URL = "https://w3id.org/oc/index/coci/api/v1/"
REFERENCES_URL = urljoin(COCI_BASE_URL, 'references/')
CITATIONS_URL = urljoin(COCI_BASE_URL, 'citations/')

"""
Utils
-----
"""


def get_json(url, params=None):
    """Request the url and parse the result to a JSON object."""
    # TODO: replace w/ generic functions like get_work
    url = urljoin(url, ("?" + urlencode(params) if params else ""))
    response = requests.get(url)

    data = json.loads(response.content)
    return data

"""
Request functions
-----------------
"""


class CrossRef(DataSource):
    """Class for handling requests to crossref"""

    def __init__(self):
        super(CrossRef, self).__init__(SESSION)

    def get_work(self, doi, **kwargs):
        """Retrieve work at specified doi"""
        url = urljoin(WORK_URL, doi)
        result = self._get_url(url, **kwargs)

        data = json.loads(result.response.content)

        result.data = data['message']
        return result

    def get_journal(self, issn):
        """Retrieve journal at specified issn"""
        return get_json(urljoin(JOURNAL_URL, issn))['message']

    def search(self, query):
        """Free-form search query"""
        return get_json(WORK_URL, {"query": query})['message']


def scrape_author(author, rows=200):
    """Search for papers by an author"""
    names = [author.get('given', ''), author.get('family', '')]
    query_string = " ".join(names)

    if not query_string:
        logger.error("Length of author names must be > 1")
        raise ValueError("Length of author names must be > 1")

    params = {"query.author": query_string, "rows": rows}

    # Make request
    res = get_json(WORK_URL, params)['message']
    items = res['items']

    tally = Counter()
    for work in items:
        res_authors = work['author']
        # TODO: Move to AuthorData Manager
        if cleaning.match_authors(author, res_authors):
            tally['added'] += 1
            yield work
        else:
            tally['rejected'] += 1
            logger.debug("rejected match: %s", res_authors)

    logger.debug("Author query complete: %s", tally)


def get_works(filters=None, sort='issued', chunksize=20, limit=None,
              order='desc'):
    """Get and papers matching query"""
    logger.debug("Getting works with filters: %r", filters)

    # Initialize variables
    finished = False
    offset = 0
    count = 0
    total = "Unknown"

    # Query Params
    params = {"rows": chunksize,
              "filter": filters,
              "offset": offset,
              "sort": sort,
              "order": order}

    while not finished:
        logger.debug("Getting results %s - %s of %s", offset,
                     offset + chunksize, total)

        # filters = filters or {}
        # filters['issn'] = issn
        # filter_string = build_filter(**filters)

        res = get_json(WORK_URL, params)['message']

        # Update total
        if res['total-results'] != total:
            total = res['total-results']

            if limit is None:
                limit = total

            logger.info("%s total results returned. Limit set to %s."
                        "Scraping rows %s - %s of %s", total, limit,
                        offset, offset + chunksize, total)

        items = res['items']
        logger.debug("%s items returned", len(items))

        for work in items:

            yield work

            count += 1

        if len(items) < chunksize or offset >= limit:
            finished = True

        offset += chunksize

    logger.info("%s papers of %s retrieved", count, total)


"""
Open citation functions
-----------------------
"""


def get_citations(doi):
    """Get citations for doi"""
    return get_json(urljoin(CITATIONS_URL, doi))
