"""
Base Classes for sources
------------------------
"""
from functools import wraps
import logging
from inspect import signature
from urllib.parse import urljoin, urlencode

import requests
from django.core.cache import cache
from django.utils import timezone as tz

from papernet.models import pipeline

"""
Constants
---------
"""
logger = logging.getLogger()

SESSION = requests.Session()

CACHE_TIMEOUT = 60 * 60 * 24 * 30  # 1 month

"""
Helper functions
"""


def encode_url(url, params=None):
    """Encode and join url and query"""
    return urljoin(url, ("?" + urlencode(params) if params else ""))


def build_filter(from_date=None, until_date=None, abstract=None, **kwargs):
    """Build a crossref API filter from params"""
    filter_strings = []
    if from_date:
        date_string = from_date.strftime('%Y-%m-%d')
        filter_strings.append(f"from-pub-date:{date_string}")

    if until_date:
        date_string = until_date.strftime('%Y-%m-%d')
        filter_strings.append(f"until-pub-date:{date_string}")

    if abstract:
        filter_strings.append(f"has-abstract:true")

    for k, v in kwargs.items():
        filter_strings.append(f"{k}:{v}")

    return ",".join(filter_strings)


"""
Cache
-----
"""


def check_cache(url):
    """Return cached data if available"""
    data = cache.get(url)
    if data is not None:
        logger.info("Retrieved %s from cache: %.20s", url, data)
        return data
    logger.debug("Cache %s not found", url)


def set_cache(url, data, timeout=CACHE_TIMEOUT):
    """Cache `data` with key `url` for `timeout`"""
    cache.set(url, data, timeout)
    logger.debug("Cached response from %s for %r", url, timeout)


def cache_response(func):
    """Get and set results from inner in cache
    ----
    To be replaced with SourceLog system
    """
    @wraps(func)
    def request(*args, **kwargs):

        # ignore cache if force is True
        force = kwargs.pop("force", False)

        # Build URL and check cache
        arguments = signature(func).bind(*args, **kwargs).arguments
        url = arguments.get('url', "")
        params = arguments.get('params', {})
        full_url = encode_url(url, params)

        if not force:
            cached = check_cache(full_url)

            if cached is not None:

                # Return result
                return cached

        # Get fresh result
        res = func(*args, **kwargs)

        # Set cache with result if response is ok
        if res.ok:
            set_cache(full_url, res, CACHE_TIMEOUT)
        return res

    return request


"""
Logging
-------
Log requests and data
"""

"""
Requests
--------
"""


class Data():
    """Store information about how source data is used"""
    def __init__(self, request, response, data):
        self.request = request
        self.response = response
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __getattr__(self, name):
        if name in self._data:
            return self.__getitem__(name)

        raise AttributeError(f"'Data' object has no attribute '{name}'")


class Result():
    """Result of Data Source query"""
    def __init__(self, request, response):
        """Initialize result"""
        self.request = request
        self.response = response
        self.data = None


class DataSource():
    """ABC for all data sources"""

    def __init__(self, session=None):
        self.session = session or SESSION
        self.history = []

    # @cache_response
    def _get_url(self, url, params=None, **kwargs):

        # ignore cache if force is True
        no_wait = kwargs.pop("no_wait", False)

        params = params or {}

        # Initialize wait
        wait = 0

        # Rate Limit Request
        if not no_wait:
            wait = pipeline.rate_limit(url=url, params=params)

        # Log start time
        start_time = tz.now()
        response = self.session.get(url, params=params, **kwargs)

        # Log end time
        end_time = tz.now()

        # Store log
        request = pipeline.log_request(
            url=url, params=params, start_time=start_time,
            end_time=end_time, response=response, wait=wait)

        result = Result(request=request, response=response)

        return result


class FulltextSource():
    """Base class for fulltext sources"""
    pass


