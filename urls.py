from django.urls import path
from django.views.generic import TemplateView

from papernet import views

urlpatterns = [
    path('', views.home),
    path('net', views.net),
    path('network/', views.network),
    path('doi', views.get_by_doi),
    path('search', views.search),
    path('search_cr', views.search_cr),

    path('table/<str:key>/', views.table),
    path('papers/', views.paper_table),
    path('paper/<int:pk>/', views.paper_info),
    path('author/<int:pk>/', views.author_info),
    path('authors/', views.author_table),

    path('journal/<int:pk>/', views.journal_info),
    path('journal/<int:pk>/vol/<int:vol>/', views.volume_info),
    path('journals/', views.journal_table),

    path('update/paper/<int:pk>/', views.update_paper),
    path('update/author/<int:pk>/', views.update_author),
    path('update/journal/<int:pk>/', views.update_journal),

    path('modify/perusal/', views.modify_perusal),
    path('modify/perusal/tags/', views.modify_tags),

    path('refresh', views.refresh),
    path('profile/', views.profile),

    path('create_project/', views.create_project),
    path('project/<int:pk>/', views.project_home),
    path('project/data/<int:pk>/', views.project_data),
    path('similar/', views.find_similar_papers),

    path('add_to_project/', views.add_to_project),
    path('upload_csv/', views.upload_csv),

    path('get_progress/', views.get_progress),

    path('monitor/', views.getlogs),
    path('data_creation/', views.data_creation),

    # User views
    path('login_user/', views.login_user),
    path('signup/', views.signup),
    path('logout/', views.logout_user),
    path('user_data/', views.user_data),

    path("vue",
         TemplateView.as_view(template_name="application.html"),
         name="app",
         ),
]
