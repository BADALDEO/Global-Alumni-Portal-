from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.job_list, name="list"),
    path("post/", views.job_create, name="create"),
    path("posted/", views.my_posted_jobs, name="my_posted"),
    path("applied/", views.my_portal_applications, name="my_applications"),
    path("application/<int:pk>/status/", views.update_application_status, name="update_status"),
    path("application/<int:pk>/resume/", views.application_resume, name="resume"),
    path("<int:pk>/", views.job_detail, name="detail"),
    path("<int:pk>/edit/", views.job_edit, name="edit"),
    path("<int:pk>/delete/", views.job_delete, name="delete"),
    path("<int:pk>/apply/", views.apply, name="apply"),
    path("<int:pk>/applicants/", views.applicants, name="applicants"),
]
