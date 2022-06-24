"""
Cleaning
--------
Utils to clean data retrieved from sources
"""

import re
import logging

logger = logging.getLogger(__name__)


def clean_name(name):
    """Clean names for matching"""
    return re.findall('\w+', name.lower())


def clean_doi(doi):
    """Return doi string
    https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    """
    if not isinstance(doi, str):
        raise TypeError("DOI must by of type str, not %s" % type(doi))

    doi = doi.lower()
    match = re.search("10.\d{4,9}/[-._;()/:A-Z0-9]+", doi, re.I)

    if match is None:
        raise ValueError("DOI is not valid: %s" % doi)

    return match.group()


def match_substrings(a, b):
    """Check if substrings of a and b match"""
    if a == b:
        return True

    a_subs = clean_name(a)
    b_subs = clean_name(b)

    if any([a_sub in b_subs for a_sub in a_subs]):
        return True

    if any([b_sub in a_subs for b_sub in b_subs]):
        return True

    return False


def match_author(query, result):
    """Check that queried author has been retrieved"""

    # Check family names match
    if not match_substrings(query['family'], result['family']):
        return False

    if not match_substrings(query['given'], result['given']):
        return False

    return True


def match_authors(query, results):
    """Look through result authors and check if one matches"""
    for res in results:
        if res.get('given') and res.get('family'):
            if match_author(query, res):
                return True
    return False


def get_issn(data):
    """Safely parse print and electronic ISSN from data"""

    # Initialize defaults
    print_issn = ""
    e_issn = ""

    issn_types = data.get('issn-type', [])
    # Try to assign both issn types
    for itype in issn_types:
        issn_type = itype.get("type", "")
        if issn_type == "print":
            print_issn = itype.get("value", "")
        elif issn_type == "electronic":
            e_issn = itype.get("value", "")
        else:
            logger.warning("ISSN type not found: %s", issn_type)

    issn = data.get('ISSN', [""])[0] or e_issn or print_issn

    out = {'issn': issn,
           'print_issn': print_issn,
           'electronic_issn': e_issn}

    return out