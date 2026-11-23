from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("resumes/", views.resume_list, name="resumes"),
    path("resumes/add/", views.resume_create, name="resume_create"),
    path("resumes/<int:pk>/edit/", views.resume_edit, name="resume_edit"),
    path("resumes/<int:pk>/delete/", views.resume_delete, name="resume_delete"),
    path("resumes/<int:pk>/default/", views.resume_default, name="resume_default"),
    path("resumes/<int:pk>/file/", views.resume_file, name="resume_file"),
    path("networking/", views.networking_list, name="networking"),
    path("networking/add/", views.networking_create, name="networking_create"),
    path("networking/<int:pk>/edit/", views.networking_edit, name="networking_edit"),
    path("networking/<int:pk>/delete/", views.networking_delete, name="networking_delete"),
    path("followups/", views.followup_list, name="followups"),
    path("followups/<int:pk>/done/", views.followup_done, name="followup_done"),
    path("followups/<int:pk>/snooze/", views.followup_snooze, name="followup_snooze"),
    path("report/", views.weekly_report_view, name="report"),
    path("targets/", views.goals, name="goals"),
]
