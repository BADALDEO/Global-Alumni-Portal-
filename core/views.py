from django.shortcuts import render


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def permission_denied(request, exception=None):
    return render(request, "403.html", status=403)
