# Papernet

This is a work in progress web application for exploring academic citation graphs.

There is a live version of the site here:
[camrobjones.com/papernet/](https://camrobjones.com/papernet/)

## Overview

The initial idea was to display interactive network graphs so that users could
explore papers which cite or are cited by a given paper. I ended up getting
distracted trying to create a more robust system for scraping and storing
paper metadata, as well as creating projects (reading lists of papers). There
were a lot of data-quality issues and I wanted to be able to track different
sources of information about the same publication. At some point the scope 
of this redesign became too large, and I got busy with other things, leaving
the site between two stools.

Many aspects of the site still don't work as intended (or even well).
There are still many data quality issues, the internal 
search only looks at paper titles, and the crossref results need to be re-ranked. 
The site was mostly designed for my own personal use, and so it's not very
user-friendly at the moment. Users need to sign in to benefit from most of the
features.

## Features

* Search for papers (stored in a database or on crossref. Crossref results are asynchronously added to the database).
* View details on
    * Papers
    * Authors
    * Journals and issues
* View collections of papers that cite or are cited by another paper
* Create projects to store related papers
* Add personal metadata to papers (via projects)
    * Ratings
    * Tags
    * Status (Read, Not Read)
    * Notes

## Database Structure

The database structure is quite extensive and tracks

* Publications
* Papers
* Journals
* Authors
* Institutions
* Citations
* Topics
* Users
* Projects
* Tags


## Tech and Project Structure

The project is built using Django as a backend, with Vue.js on the frontend. The files are generally organized according to the Django conventions.

* `models/`: Django database object schemas for papers and users (`models.py`) and the data storage pipeline (`pipeline.py`).
* `sources/`: Code related to extracting information about paper from web sources. Mostly uses `crossref.py` which inherits from `base.py`.

## Future and Roadmap

In the short term, I want to finish refactoring the source scraping and storage process, to ensure better data quality and provide better monitoring.

Following that, I want to improve the basic functionality of the site as a google-scholar-esque academic paper site:

* Improve search quality, crossref search speed, & result page
* Improve pages for papers, journals, authors etc (e.g. allow users to view all of their papers as a table).
* Improve the project functionality (UI, suggest papers, infer tag taxonomy)

Then I want to focus on the citation-graph aspect of the site (the original inspiration for the project):

* Display citation graphs (generate for papers, people, projects, institutions etc).
* Find similar and suggested papers based on citations
* Analyse paper text in order to characterize citations (salience, sentiment, does it contain a summary of the relevant significance of the paper).

Finally, I would like to use NLP more generally to extract more insights from the papers:

* No. experiments run
* Methods used
* Type of result
* Papers that agree or disagree with this paper
