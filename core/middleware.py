from django.shortcuts import redirect

EXEMPT_PREFIXES = ("/static/", "/admin/", "/accounts/", "/logout/", "/complete-profile/")


class CompleteProfileMiddleware:
    """People who joined with Google must choose their role before using the portal."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and not getattr(user, "profile_completed", True)
            and not request.path.startswith(EXEMPT_PREFIXES)
        ):
            return redirect("complete_profile")
        return self.get_response(request)
