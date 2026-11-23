from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from accounts.models import User


class PortalSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """If Google confirms an email that already belongs to one account, sign into that account."""
        if sociallogin.is_existing:
            return

        matches = {}
        for address in sociallogin.email_addresses:
            if address.verified and address.email:
                for user in User.objects.filter(email__iexact=address.email):
                    matches[user.pk] = user

        # never guess between several accounts
        if len(matches) == 1:
            sociallogin.connect(request, next(iter(matches.values())))

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        # new Google users still have to pick student / alumni / company
        user.profile_completed = False
        return user
