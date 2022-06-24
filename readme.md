# Papernet

This is a work in progress web application for exploring academic citation graphs.

The initial idea was to display interactive network graphs so that users could
explore papers which cite or are cited by a given paper. I ended up getting
distracted trying to create a more robust system for scraping and storing
paper metadata, as well as creating projects (reading lists of papers).

The site was mostly designed for my own personal use, and so it's not very
user-friendly at the moment. Users need to sign in to benefit from many of the site
features.

Features:

* Search for papers (stored in a database or on crossref. Crossref results are asynchronously added to the database).
* View details on
    * Papers
    * Authors
    * Journals and issues
* View collections of papers that cite or are cited by another paper
* Create projects to store related papers
* Add personal metadata to papers
    * Ratings
    * Tags
    * Status (Read, Not Read)
    * Notes


There is a live version of the site here:
[camrobjones.com/papernet/](https://camrobjones.com/papernet/)