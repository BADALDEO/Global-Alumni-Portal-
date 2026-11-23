from django.contrib import admin

from .models import ReferralRequest


@admin.register(ReferralRequest)
class ReferralRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "alumni", "company_name", "job_title", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("student__username", "alumni__username", "company_name", "job_title")
