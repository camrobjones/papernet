"""Papernet tasks"""

import logging
import re

from celery import shared_task

from papernet import sources
from papernet.sources import crossref
from papernet.models import Paper, Project
from papernet.aux import add_work, get_work, get_reader, add_to_project


logger = logging.getLogger('papernet')

# @app.task(bind=True)
@shared_task
def retrieve_citations(pk):
    """Retrieve citations for paper"""
    logger.debug("Task: retrieve_citations(pk=%s)", pk)
    paper = Paper.objects.get(pk=pk)
    paper.retrieve()
    paper.retrieve_citations()


@shared_task
def get_author_papers(author):
    """Retrieve papers by author"""
    logger.debug("Task: get_author_papers(author=%s)", author)
    for work in crossref.scrape_author(author):
        add_work(work)


@shared_task
def get_journal_papers(issn):
    """Retrieve papers in journal"""
    logger.debug("Task: get_journal_papers(issn=%s)", issn)
    for work in crossref.scrape_journal(issn):
        add_work(work)


@shared_task(bind=True)
def get_works(self, data, project_id=None, user_id=None):
    """Retrieve papers in journal"""
    # TODO: deal with no project & user
    logger.debug("Task: get_works_papers(project_id=%s, user_id=%s)",
                 project_id, user_id)

    state = "IN PROGRESS"
    meta = {"total": len(data), "current": 0, "added": 0, "error": 0,
            "errors": []}

    project = Project.objects.get(pk=project_id)

    reader = get_reader(user_id)

    self.update_state(state=state, meta=meta)
    for row in data:

        try:
            paper = get_work(row['DOI'])

        except (ValueError, TypeError) as e:
            meta['error'] += 1
            meta['errors'].append(str(e))
            logger.error("Failed to get paper: %s", e)

        else:
            perusal = add_to_project(paper, project, reader)
            meta['added'] += 1

            status = row.get('Status')
            if status:
                perusal.status = status

            priority = row.get("Priority")
            if priority and isinstance(priority, int):
                perusal.priority = priority

            notes = row.get("Notes")
            if notes:
                perusal.notes = notes

            tag_string = row.get("Tags", [])
            if tag_string:
                tags = re.split('[;,:] *', tag_string)
                for tag in tags:
                    perusal.add_tag(tag)

        meta['current'] += 1
        self.update_state(state=state, meta=meta)

    return meta
