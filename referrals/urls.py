from django.urls import path

from . import views

app_name = "referrals"

urlpatterns = [
    path("", views.referral_list, name="list"),
    path("alumni/", views.alumni_directory, name="directory"),
    path("request/", views.referral_request, name="request"),
    path("<int:pk>/", views.referral_detail, name="detail"),
    path("<int:pk>/respond/", views.referral_respond, name="respond"),
    path("<int:pk>/withdraw/", views.referral_withdraw, name="withdraw"),
    path("<int:pk>/resume/", views.referral_resume, name="resume"),
]
