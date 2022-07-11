"""
Papernet API
"""
import logging
import json
from collections import Counter
from email.utils import parseaddr

import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count
from django.utils import timezone as tz
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from celery.result import AsyncResult
from django.core.exceptions import ValidationError

from papernet import models, sources, aux, tasks, query

# Get an instance of a logger
logger = logging.getLogger(__name__)


def home(request, message=None):
    """Homepage"""
    context = {"message": message}

    reader = aux.get_reader(request.user)

    if reader:
        reader_data = reader.data
        reader_data['top'] = aux.get_reader_top(reader, data=True)
        context['reader'] = reader_data

    # TODO: Get other papers if not

    return render(request, 'papernet/home.html', context)


def profile(request):
    """User profile page"""
    user = request.user
    if not user.is_authenticated:
        return home(request, "Please create an account.")

    reader = aux.get_reader(user)
    if reader is None:
        return home(request, "Something went wrong.")

    context = {"reader": reader.data}

    return render(request, 'papernet/profile.html', context)


def net(request, message=None):
    """Homepage"""
    context = {"message": message}
    return render(request, 'papernet/net.html', context)


def network(request, message=None):
    """Homepage"""
    paper = models.Paper.objects.get(pk=35)
    cited_papers = paper.cited_papers(n=50)
    citing_papers = paper.citing_papers(n=50)

    papers = [paper] + list(cited_papers) + list(citing_papers)
    nodes = [{"id": p.pk, "year": p.year, "ref": p.ref,
              "group": 1, "citations": p.citation_count}
             for p in papers]

    links = []
    for cited_paper in cited_papers:
        for citing_paper in cited_paper.citing_papers(n=100):
            if citing_paper in papers:
                links.append({"source": citing_paper.pk,
                              "target": cited_paper.pk,
                              "value": 1})

    for citing_paper in citing_papers:
        for cited_paper in citing_paper.cited_papers(n=100):
            if cited_paper in papers:
                links.append({"source": citing_paper.pk,
                              "target": cited_paper.pk,
                              "value": 1})

    data = {"nodes": nodes, "links": links}

    context = {"data": data}
    return render(request, 'papernet/network.html', context)


"""
API Views
---------
"""


def get_progress(request):
    """Get status of task"""
    task_id = request.GET.get('task_id')
    result = AsyncResult(task_id)
    task = {"state": result.state, "info": result.info}
    out = {"task": task, "success": True}
    return JsonResponse(out)


def get_by_doi(request):
    """Retrieve a paper by doi and return JSON object"""
    doi = request.GET.get('doi')

    paper = aux.get_work(doi_raw=doi)

    # Check doi
    if paper is None:
        return JsonResponse({"success": False})

    citations = paper.cited_papers(n=10)
    citations_data = [c.preview for c in citations if c]

    cited_by = paper.citing_papers(n=10)
    cited_by_data = [c.preview for c in cited_by if c]

    out = {}
    out['paper'] = paper.data
    out['citations'] = citations_data
    out['cited_by'] = cited_by_data

    return JsonResponse(out)


def update_paper(request, pk):
    """Refresh data for paper"""
    paper = models.Paper.objects.get(pk=pk)

    result = sources.get_work(doi=paper.doi)
    aux.add_work(result.data, force=True)

    # paper.retrieve(citations=False, force=True)
    tasks.retrieve_citations.delay(paper.pk)

    return paper_info(request, pk)


def update_journal(request, pk):
    """Retrieve journal papers"""
    journal = models.Journal.objects.get(pk=pk)

    task = tasks.get_journal_papers.delay(journal.issn)

    return JsonResponse({"success": True, "task_id": task.id})


def update_author(request, pk):
    """Retrieve author papers"""
    author = models.Author.objects.get(pk=pk)
    author_data = {"given": author.first_name, "family": author.last_name}
    task = tasks.get_author_papers.delay(author_data)

    return JsonResponse({"success": True, "task_id": task.id})


def search(request):
    """Search for a specific document"""
    time0 = tz.now()
    query = request.GET.get('query')
    logger.debug("Init search with query %s", query)
    papers = models.Paper.objects.filter(title__icontains=query)
    # Sort by n citations
    papers = papers.annotate(num_cited_by=Count('cited_by'))
    papers = papers.order_by('-num_cited_by')[:5]
    time1 = tz.now()
    logger.debug("%s Local results found in %s", len(papers), time1 - time0)

    out = {'results': [paper.preview for paper in papers]}

    return JsonResponse(out)


def search_cr(request):
    """Search query in crossref"""
    time0 = tz.now()
    query = request.GET.get('query')
    cr_results = sources.search(query)["items"]
    cr_data = []
    for res in cr_results:
        if 'DOI' not in res:
            print("No DOI for res, ", res)
            # TODO: log/flag
            continue
        paper, _ = models.Paper.objects.get_or_create(doi=res["DOI"])
        paper.from_crossref(res)
        paper.retrieve_authors(res.get('author', []))
        paper.save()
        tasks.retrieve_citations.delay(paper.pk)
        cr_data.append(paper)

    cr_data = cr_data[:5]

    out = {"results": [paper.preview for paper in cr_data]}

    time1 = tz.now()
    logger.debug("%s Crossref results found in %s", len(cr_data),
                 time1 - time0)

    return JsonResponse(out)


def refresh(request):
    """refresh"""
    doi = request.GET.get('doi')
    paper, created = models.Paper.objects.get_or_create(doi=doi)
    paper.retrieve(force=True)
    paper.retrieve_citations()

    return get_by_doi(request)


def modify_perusal(request):
    """Alter a value on a perusal"""

    # Retrieve request data
    post = json.loads(request.body.decode('utf-8'))
    post_keys = ['perusal_id', 'field', 'value', 'project_id', 'paper_id']
    perusal_id, field, value, project_id, paper_id = [post.get(k) for k in post_keys]

    if perusal_id is not None:
        perusal = aux.get_perusal_by_id(perusal_id, request.user)
    else:
        reader = aux.get_reader(request.user)
        project = aux.get_project_by_id(project_id, reader=reader)
        paper = models.Paper.objects.get(pk=paper_id)
        perusal = aux.get_perusal(reader=reader, project=project, paper=paper)

    setattr(perusal, field, value)
    if field == 'status':
        perusal.status_updated = tz.now()

    perusal.save()
    return JsonResponse({"success": True})


def create_project(request):
    """Asynchronously create project."""
    # Retrieve request data
    post = json.loads(request.body.decode('utf-8'), object_hook=aux.decode)

    # Retrieve parameters
    title = post.get('title')
    reader = aux.get_reader(request.user)
    project = models.Project.objects.create(reader=reader, title=title)

    out = {"success": True, "pk": project.pk}

    return JsonResponse(out)


def modify_tags(request):
    """Alter a value on a perusal"""

    # Retrieve request data
    post = json.loads(request.body.decode('utf-8'))
    post_keys = ['perusal_id', 'add', 'content', 'project_id', 'paper_id']
    perusal_id, add, content, project_id, paper_id = [post.get(k) for k in post_keys]

    if perusal_id is not None:
        perusal = aux.get_perusal_by_id(perusal_id, request.user)
    else:
        reader = aux.get_reader(request.user)
        project = aux.get_project_by_id(project_id, reader=reader)
        paper = models.Paper.objects.get(pk=paper_id)
        perusal = aux.get_perusal(reader=reader, project=project, paper=paper)

    if add is True:
        perusal.add_tag(content)
    elif add is False:
        perusal.remove_tag(content)
    else:
        raise TypeError("add must be bool, not %s" % type(add))
    perusal.save()
    return JsonResponse({"success": True})


def upload_csv(request):
    """Upload csv and add to project"""

    # post = json.loads(request.body.decode('utf-8'))
    project_id = request.POST.get('project_id')
    user_id = request.user.pk

    csv = request.FILES['csv']
    df = pd.read_csv(csv.file)

    data = df.to_dict(orient='records')

    task = tasks.get_works.delay(data, project_id, user_id)

    return JsonResponse({"success": True, "task_id": task.id})


def add_to_project(request):
    """Add paper to project"""

    # Retrieve request data
    post = json.loads(request.body.decode('utf-8'))

    paper_id = int(post.get('paper_id'))
    project_id = int(post.get('project_id'))
    user = request.user

    paper = models.Paper.objects.get(pk=paper_id)
    project = models.Project.objects.get(pk=project_id)
    reader = aux.get_reader(user)

    perusal = aux.add_to_project(paper, project, reader)
    return JsonResponse({"success": True,
                         "perusal_id": perusal.pk})


"""
User views
----------
- get_user
- login
- logout
- signup
"""


def login_user(request):
    """Asynchronously log user in"""

    # Retrieve request data
    post = json.loads(request.body.decode('utf-8'), object_hook=aux.decode)

    # Retrieve simulation parameters
    username = post.get('username')
    password = post.get('password')

    # check if username is email
    User = get_user_model()
    if not User.objects.filter(username=username).exists():
        email_query = User.objects.filter(email=username)
        if email_query.count() == 1:
            username = email_query.first().username

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        user_data = aux.get_user(request)
        out = {"success": True, "user": user_data}

    else:
        # Return an 'invalid login' error message.
        message = "Incorrect username or password."
        out = {"success": False, "message": message}

    return JsonResponse(out)


def logout_user(request):
    """Asynchronously log user out"""
    logout(request)
    request.COOKIES['neurons'] = []
    out = {"success": True}
    return JsonResponse(out)


def signup(request):
    """Asynchronously create new user."""

    # Retrieve request data
    post = json.loads(request.body.decode('utf-8'), object_hook=aux.decode)

    # Retrieve simulation parameters
    username = post.get('username')
    email = post.get('email')
    password = post.get('password')
    password_confirm = post.get('passwordConfirm')

    # Validate inputs
    errors = []
    User = get_user_model()

    out = {"success": False, "errors": errors}

    # Check username is unique
    if (User.objects.filter(username=username).exists() or
       User.objects.filter(email=username).exists()):
        errors.append("That username is already in use.")
        return JsonResponse(out)

    # Check email is valid
    parsed = parseaddr(email)[1]
    if '@' not in parsed or len(parsed) < 3:
        errors.append("Please enter a valid email address.")
        return JsonResponse(out)

    # Check email is unique
    if User.objects.filter(email=email).exists():
        errors.append("That email is already in use.")
        return JsonResponse(out)

    # Validate password
    try:
        validate_password(password)
    except ValidationError as e:
        errors += e
        return JsonResponse(out)

    # Check passwords match
    if password != password_confirm:
        errors.append("Passwords do not match.")
        return JsonResponse(out)

    # Convert guests
    if request.user.is_authenticated and request.user.guest:
        user = request.user
        user.username = username
        user.email = email
        user.guest = False
        user.set_password(password)
        user.save()

    # Create new users
    else:
        user = User.objects.create_user(username, email, password)
        login(request, user)

    user_data = aux.get_user(request)
    out = {"success": True, "user": user_data}

    return JsonResponse(out)


def user_data(request):
    """Asynchronously get user data."""
    user_data = aux.get_user(request)
    out = {"success": True, "user": user_data}

    return JsonResponse(out)


"""
Table Views
"""


def table(request, key="Paper"):
    """Create a data table to view data"""
    model = getattr(models, key)

    objects = model.objects.all()
    fields = [f.name for f in model._meta.fields]
    data = []
    for obj in objects:
        serializable = [obj.serializable_value(f) for f in fields]
        data.append(serializable)

    out = {'model': model,
           'fields': fields,
           'data': data}

    return render(request, 'papernet/table.html', out)


def paper_view(request, reader, project, papers, query):
    """Format data for paper table"""
    paper_data = []
    print("running paper_view with {}".format(len(papers)))
    tags = Counter()
    for paper in papers:
        print("running paper {}".format(paper))
        perusal = aux.get_perusal(reader=reader, paper=paper,
                                  project=project, save=False)
        perusal_data = perusal.data
        tags.update(perusal_data['meta']['tags'])
        paper_data.append(perusal_data)

    project_data = project.preview
    info = {"title": "Papers", "description": query,
            "statuses": models.DEFAULT_STATUSES, "tags": tags.most_common(),
            "project": project_data}

    out = {'papers': paper_data, 'info': info}

    return render(request, 'papernet/paper_table.html', out)


def paper_table(request):
    """View a table of papers"""
    citing_paper_id = request.GET.get('citing_paper')
    cited_paper_id = request.GET.get('cited_paper')
    order = request.GET.get('order', '-no_citations')
    limit = min(request.GET.get('limit', 50), 200)
    title = request.GET.get('title')

    reader = aux.get_reader(request.user)
    project = reader.project_set.get(primary=True)

    papers = models.Paper.objects.all()

    query = ""

    # Queries
    if title is not None:
        papers = papers.filter(title__icontains=title)

    if citing_paper_id is not None:
        citing_paper = models.Paper.objects.get(pk=citing_paper_id)
        papers = papers.filter(cited_by__in=citing_paper.citations.all())
        query += f"cited by {citing_paper.ref}"

    if cited_paper_id is not None:
        cited_paper = models.Paper.objects.get(pk=cited_paper_id)
        papers = papers.filter(citations__in=cited_paper.cited_by.all())
        query += f"citing {cited_paper.ref}"

    if order is not None:
        papers = papers.annotate(no_citations=Count('citations'))
        papers = papers.order_by(order)

    papers = papers[:limit]

    return paper_view(request, reader, project, papers, query)


def find_similar_papers(request):
    """Return similar papers to request"""
    logger.info("Finding similar papers")
    project_id = int(request.GET.get('project_id'))
    project = models.Project.objects.get(pk=project_id)
    perusals = project.get_papers()
    papers = [perusal.paper for perusal in perusals]
    reader = aux.get_reader(request.user)

    # for paper in papers:
    #     data = get_cited_by(paper)
    logger.info("Getting refs")
    refs = aux.get_shared_refs(papers)
    cites = aux.get_shared_cites(papers)
    logger.info("Getting similar")
    similar = aux._get_similar_papers(refs, cites)

    logger.info("Done")
    papers = [s[0] for s in similar.most_common(20)]

    query = f"Similar papers to {project.title}"

    return paper_view(request, reader, project, papers, query)


def author_table(request):
    """Query authors"""
    authors = models.Author.objects.all()

    query = request.GET.get('query')
    order = request.GET.get('order')
    limit = request.GET.get('limit', 200)

    if query is not None:
        authors = authors.filter(last_name__icontains=query)

    authors = authors[:limit]

    author_data = [author.data for author in authors]

    out = {'data': author_data, 'query': query}

    return render(request, 'papernet/author_table.html', out)


def journal_table(request):
    """Query authors"""
    journals = models.Journal.objects.all()

    title = request.GET.get('query')
    order = request.GET.get('order', '-publications')
    limit = request.GET.get('limit', 200)

    query = ""

    if title is not None:
        journals = journals.filter(title__icontains=query)
        query += f"Title includes '{title}'"

    if order is not None:
        journals = journals.annotate(publications=Count('publication'))
        journals = journals.order_by(order)

    journals = journals[:limit]

    journal_data = [journal.data for journal in journals]

    out = {'data': journal_data, 'query': query}

    return render(request, 'papernet/journal_table.html', out)


def get_project_data(pk):
    """Project data"""
    project = models.Project.objects.get(pk=pk)
    perusals = project.get_papers()

    tags = Counter()
    paper_data = []

    for perusal in perusals:
        perusal_data = perusal.data
        tags.update(perusal_data['meta']['tags'])
        paper_data.append(perusal_data)

    project_data = project.preview

    data = {
        "info": {
            "title": project.title,
            "description": project.description,
            "statuses": models.DEFAULT_STATUSES,
            "tags": tags.most_common(),
            "project": project_data
            },
        "project": project.data,
        "papers": paper_data
    }

    return data


def project_data(request, pk):
    """Return project data as JsonResponse"""
    return JsonResponse(get_project_data(pk))


def project_home(request, pk):
    """Project home view"""
    return render(request, 'papernet/paper_table.html', get_project_data(pk))



"""
Info functions
"""


def paper_info(request, pk):
    """View a detailed info about a paper"""
    paper = models.Paper.objects.get(pk=pk)

    paper_data = paper.data
    refs = [ref.preview for ref in paper.cited_papers()]
    paper_data['references'] = refs

    cites = [ref.preview for ref in paper.citing_papers()]
    paper_data['citations'] = cites

    out = aux.get_paper_metadata(paper, request.user)
    out.update({'paper': paper_data})

    return render(request, 'papernet/paper_info.html', out)


def author_info(request, pk):
    """View a detailed info about an author"""
    author = models.Author.objects.get(pk=pk)

    author_data = author.data

    out = {'author': author_data}

    return render(request, 'papernet/author_info.html', out)


def journal_info(request, pk):
    """View a detailed info about a journal"""
    journal = models.Journal.objects.get(pk=pk)

    journal_data = journal.data

    papers = journal.get_papers(n=5)
    journal_data['papers'] = [p.preview for p in papers]

    authors = journal.get_authors(n=5)
    author_data = []
    for a in authors:
        a_data = a.preview
        a_data['journal_papers'] = a.journal_papers
        author_data.append(a_data)
    journal_data['authors'] = author_data

    out = {'journal': journal_data}

    return render(request, 'papernet/journal_info.html', out)


def volume_info(request, pk, vol):
    """View a detailed info about a journal"""
    journal = models.Journal.objects.get(pk=pk)

    journal_data = journal.data

    papers = journal.get_papers(n=None).filter(publication__volume=vol)
    journal_data['papers'] = [p.data for p in papers]

    out = {'journal': journal_data, 'volume': vol}

    return render(request, 'papernet/volume_info.html', out)


"""
Monitoring
----------
"""


def getlogs(request):
    """Display logging data"""
    interval = request.GET.get('interval', 'H')
    logs = models.RequestLog.objects.all()
    log_data = [[log.url, log.end_time, log.delta] for log in logs]
    df = pd.DataFrame(log_data)
    df.columns = ['url', 'end_time', 'delta']
    df = df.set_index('end_time').groupby(pd.Grouper(freq=interval)).count()
    df = df.reset_index()
    data = df.values.tolist()
    colnames = list(df.columns)
    return render(request, 'papernet/monitor.html', {'data': data,
                                                     'colnames': colnames})


def data_creation(request):
    """Display data_creation data"""
    interval = request.GET.get('interval', 'H')
    model_name = request.GET.get('model', 'Paper')
    model = getattr(models, model_name)
    mods = model.objects.all()
    mod_data = [[mod.pk, mod.created] for mod in mods]
    df = pd.DataFrame(mod_data)
    df.columns = ['pk', 'created']
    df = df.set_index('created').groupby(pd.Grouper(freq=interval)).count()
    df = df.reset_index()
    data = df.values.tolist()
    colnames = list(df.columns)
    return render(request, 'papernet/monitor.html', {'data': data,
                                                     'colnames': colnames})

