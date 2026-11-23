from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

handler404 = "core.views.page_not_found"
handler403 = "core.views.permission_denied"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("jobs/", include("jobs.urls")),
    path("applications/", include("tracker.urls")),
    path("referrals/", include("referrals.urls")),
    path("plan/", include("planner.urls")),
    path("analytics/", include("analytics.urls")),
    # keep our own styled login/signup pages as the only entry points
    path("accounts/login/", RedirectView.as_view(pattern_name="login")),
    path("accounts/signup/", RedirectView.as_view(pattern_name="signup")),
    path("accounts/", include("allauth.urls")),
    path("", include("accounts.urls")),
]
