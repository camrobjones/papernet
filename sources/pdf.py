"""
Pdf utils
---------
Read text from PDFs
"""

import os
import re
from io import StringIO
import logging

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser


"""
Logging
-------
"""

# Module logger
logger = logging.getLogger(__name__)

# Disable pdfminer Logger
pdflogger = logging.getLogger('pdfminer')
pdflogger.setLevel(logging.WARNING)


"""
PDF Classes
"""


class PDFReader():
    """Read text from a PDF"""

    def __init__(self, filepath):
        """Initiate class"""
        self.output_string = StringIO()
        self.filepath = filepath
        self.title = ""
        self.text = ""

        assert os.path.isfile(filepath)

    def read(self):
        """Read the pdf in the filepath"""
        with open(self.filepath, 'rb') as in_file:
            parser = PDFParser(in_file)
            doc = PDFDocument(parser)
            rsrcmgr = PDFResourceManager()
            device = TextConverter(rsrcmgr, self.output_string,
                                   laparams=LAParams())
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page in PDFPage.create_pages(doc):
                interpreter.process_page(page)

        self.text = self.output_string.getvalue()


class PDFPaper():
    """Parse PDF to text and extract fields"""

    # TODO: Get author info, affiliations
    # Acknowledgements and notes
    # Just store match indexes?
    # Clean body

    def __init__(self, filepath):
        """Read PDF"""
        self.filepath = filepath
        self.reader = PDFReader(filepath)
        self.reader.read()
        self.text = self.reader.text

        self.abstract_match = None
        self.abstract = None

        self.keywords_match = None
        self.keywords = None

        self.references_match = None
        self.references = None

        self.acknowledgements_match = None
        self.acknowledgements = None

        self.body = None
        self.notes = None
        self.header = None

        self.get_sections()

    @property
    def data(self):
        """Return sections as dict"""
        data = {
            "abstract": self.abstract or "",
            "keywords": self.keywords or "",
            "references": self.references or "",
            "acknowledgements": self.acknowledgements or "",
            "notes": self.notes or "",
            "header": self.header or ""
        }

        return data

    def get_sections(self):
        """Get all sections"""
        self.get_abstract()
        self.get_keywords()
        self.get_references()
        self.get_body()

    def get_abstract(self):
        """Retrieve Paper abstract"""
        # Wiley
        match = re.search("Abstract(.*)Corr", self.text, re.S)
        self.abstract_match = match
        if match:
            self.abstract = match.groups()[0].strip()
        else:
            logger.warning("Failed to extract abstract from %s", self.filepath)

    def get_keywords(self):
        """Get Paper keywords"""
        match = re.search("Keywords: (.+?)\n\n", self.text, re.S)
        self.keywords_match = match
        if match:
            keywords = match.groups()[0]
            keyword_list = [k.strip() for k in keywords.split(';')]
            self.keywords = '; '.join(keyword_list)
        else:
            logger.warning("Failed to extract keywords from %s", self.filepath)

    def get_references(self):
        """Get Paper keywords"""
        match = re.search("References\n\n(.*)", self.text, re.S)
        self.references_match = match
        if match:
            self.references = match.groups()[0]
        else:
            logger.warning("Failed to extract references from %s", self.filepath)

    # def get_acknowledgements(self):
    #     """Get Paper keywords"""
    #     match = re.search("Acknowledgements\n\n(.*)", self.text, re.S)
    #     self.references_match = match
    #     if match:
    #         self.references = match.groups()[0]
    #     else:
    #         logger.warning("Failed to extract references from %s", self.filepath)

    def get_body(self):
        """Get main body of text"""

        # Initialize start and end indexes
        start = 0
        end = len(self.text)

        # Try to get last index of last match before body
        start_match = self.keywords_match or self.abstract_match
        if start_match:
            start = start_match.end(0)

        # Try to get last index of last match before body
        end_match = self.references_match or self.acknowledgements_match
        if end_match:
            end = end_match.start(0)

        self.body = self.text[start:end]
