
import os
import re
import urllib.request
import requests
import logging

from django.conf import settings
from pdfminer.pdftypes import PDFException

from papernet.sources.base import FulltextSource
from papernet.sources.pdf import PDFPaper


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
Session setup
"""


SESSION = requests.Session()
CR_TOKEN = settings.CR_CLICKTHROUGH_TOKEN
headers = {
    "Accept": "*/*",
    "Cache-Control": "no-cache",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "cache-control": "no-cache",
    "CR-Clickthrough-Client-Token": CR_TOKEN
}

SESSION.headers.update(headers)

STORAGE_DIR = "papernet/files/papers/"


"""
Fulltext
--------
Get fulltext for DOI
"""


class WileyFulltextSource(FulltextSource):
    """Retrieve and handle fulltext from Wiley sources"""

    def __init__(self, paper):
        """Setup Fulltext Source"""
        self.paper = paper
        self.doi = paper.doi
        self.link = None
        self.filename = None
        self.pdf = None
        self.data = {}

        self.setup_file()
        self.get_fulltext()

    def get_fulltext(self, retrieve=False):
        """Get PDF, retrieving if needed."""
        if os.path.isfile(self.filename):
            try:
                self.parse_pdf()
            except PDFException:
                logger.exception("Could not parse PDF: %s", self.filename)
            else:
                return

        self.retrieve()

    def retrieve(self):
        """Retrieve PDF from source"""
        accessible = self.get_link_data()
        if not accessible:
            return None

        downloaded = self.download_pdf()
        if not downloaded:
            return None

        self.parse_pdf()

    def get_link_data(self):
        """Get the fulltext link data"""

        # TODO: Review license
        logger.debug("Getting Link data for %s", self.doi)
        opener = urllib.request.build_opener()
        opener.addheaders = [('Accept', 'application/vnd.crossref.unixsd+xml')]
        link_response = opener.open(f'http://dx.doi.org/{self.doi}')
        link_data = link_response.info()['Link']

        links = link_data.split(', ')
        match = re.search("https://api.wiley.com[^>]+", link_data)
        if match:
            self.link = match.group()
            return True
        logger.debug("No API link found in links: %s", links)
        return False

    def setup_file(self):
        """Build filename and create file dir"""

        # Build filename
        filename = os.path.join(STORAGE_DIR, self.doi + ".pdf")

        # Create containing dir
        dirname = os.path.dirname(filename)
        os.makedirs(dirname, exist_ok=True)

        self.filename = filename

    def download_pdf(self):
        """Download and save PDF"""

        # TODO: Log, check if exists
        logger.info("Downloading PDF from: %s", self.link)
        response = SESSION.get(self.link, allow_redirects=True)

        if not response.ok:
            logger.error("Bad response: %r", response)
            return False

        logger.debug("Saving PDF: %s", self.filename)
        with open(self.filename, 'wb') as f:
            f.write(response.content)

        return True

    def parse_pdf(self):
        """Parse sections from PDF"""
        self.pdf = PDFPaper(self.filename)
        self.data = self.pdf.data
