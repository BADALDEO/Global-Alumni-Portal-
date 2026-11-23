from django.shortcuts import render

from accounts.decorators import role_required

from .services import career_stats


@role_required("student", "alumni")
def dashboard(request):
    stats = career_stats(request.user)
    return render(request, "analytics/dashboard.html", {
        "stats": stats,
        "chart": stats["chart"],
        "has_data": stats["totals"]["total"] > 0,
    })
