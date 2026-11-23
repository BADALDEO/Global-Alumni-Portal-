from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.application_list, name="list"),
    path("add/", views.application_create, name="create"),
    path("<int:pk>/edit/", views.application_edit, name="edit"),
    path("<int:pk>/delete/", views.application_delete, name="delete"),
    path("<int:pk>/status/", views.quick_status, name="quick_status"),
    path("<int:pk>/resume/", views.application_resume, name="resume"),
]
