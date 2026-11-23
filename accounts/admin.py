from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

PORTAL_FIELDS = (
    "role", "company_name", "designation", "graduation_year", "linkedin_url",
    "github_url", "leetcode_url", "open_to_mentorship", "bio",
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Portal info", {"fields": PORTAL_FIELDS}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Portal info", {"fields": PORTAL_FIELDS}),)
    list_display = ("username", "email", "role", "company_name", "is_staff")
    list_filter = UserAdmin.list_filter + ("role",)
