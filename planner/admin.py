from django.contrib import admin

from .models import NetworkingActivity, Resume, SearchGoal


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("title", "version", "user", "is_default", "created_at")


@admin.register(SearchGoal)
class SearchGoalAdmin(admin.ModelAdmin):
    list_display = ("user", "daily_application_target", "daily_networking_target", "active_days_per_week")


@admin.register(NetworkingActivity)
class NetworkingActivityAdmin(admin.ModelAdmin):
    list_display = ("contact_name", "platform", "activity", "user", "date", "is_alumni")
    list_filter = ("platform", "activity", "is_alumni")
