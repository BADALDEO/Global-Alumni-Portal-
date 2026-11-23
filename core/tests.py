"""End-to-end checks for the main flows. Run with:  python manage.py test"""
import shutil
import tempfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from analytics.services import career_stats
from jobs.models import Application, Job
from planner.models import NetworkingActivity, Resume, SearchGoal
from planner.services import (
    application_streak, dashboard_stats, followups_due, today_progress, weekly_report,
)
from referrals.models import ReferralRequest
from tracker.models import ExternalApplication

TEMP_MEDIA = tempfile.mkdtemp()
PASSWORD = "Str0ng!Pass#9"


def pdf(name="cv.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test resume", content_type="application/pdf")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class PortalFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def make(username, role, **extra):
            return User.objects.create_user(
                username, password=PASSWORD, role=role, first_name=username.title(),
                email=f"{username}@example.com", **extra,
            )

        cls.student = make("stu", "student")
        cls.other = make("other", "student")
        cls.alumni = make("alu", "alumni", company_name="TCS")
        cls.company = make("comp", "company", company_name="Accenture")
        cls.job = Job.objects.create(
            posted_by=cls.alumni, title="Python Developer", company_name="TCS", description="Build things."
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password=PASSWORD))

    # ---------------------------------------------------------------- accounts
    def test_signup_requires_company_for_alumni(self):
        data = {
            "username": "newalu", "first_name": "New", "last_name": "Alumni", "email": "new@example.com",
            "role": "alumni", "company_name": "", "graduation_year": "2019",
            "password1": PASSWORD, "password2": PASSWORD,
        }
        response = self.client.post(reverse("signup"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newalu").exists())

        data["company_name"] = "Zoho"
        response = self.client.post(reverse("signup"), data)
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.get(username="newalu").is_alumni)

    def test_pages_render_for_every_role(self):
        names = ["dashboard", "profile", "jobs:list"]
        for user in (self.student, self.alumni, self.company):
            self.login(user)
            for name in names:
                self.assertEqual(self.client.get(reverse(name)).status_code, 200, f"{user.role} {name}")
            self.client.logout()

    # ---------------------------------------------------------------- google sign-in
    def test_google_user_must_choose_role_first(self):
        user = User.objects.create_user(
            "guser", password=PASSWORD, email="guser@example.com", first_name="Gee", profile_completed=False
        )
        self.login(user)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("complete_profile"))

        # alumni need a company
        response = self.client.post(reverse("complete_profile"), {"role": "alumni", "company_name": ""})
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("complete_profile"), {"role": "alumni", "company_name": "Zoho", "graduation_year": "2019"}
        )
        self.assertRedirects(response, reverse("dashboard"))
        user.refresh_from_db()
        self.assertEqual((user.role, user.company_name, user.profile_completed), ("alumni", "Zoho", True))

    def test_completed_users_skip_the_role_page(self):
        self.login(self.student)
        self.assertRedirects(self.client.get(reverse("complete_profile")), reverse("dashboard"))

    def test_login_page_shows_google_button_only_when_configured(self):
        with override_settings(GOOGLE_LOGIN_ENABLED=False):
            self.assertNotContains(self.client.get(reverse("login")), "Continue with Google")

    # ---------------------------------------------------------------- jobs
    def test_student_cannot_post_jobs(self):
        self.login(self.student)
        self.assertEqual(self.client.get(reverse("jobs:create")).status_code, 403)

    def test_alumni_can_post_job(self):
        self.login(self.alumni)
        response = self.client.post(reverse("jobs:create"), {
            "title": "Intern", "company_name": "TCS", "job_type": "internship",
            "description": "Learn.", "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Job.objects.filter(title="Intern", posted_by=self.alumni).exists())

    def test_apply_syncs_into_tracker_and_status_follows(self):
        self.login(self.student)
        response = self.client.post(reverse("jobs:apply", args=[self.job.pk]), {"resume": pdf(), "cover_note": "Hi"})
        self.assertEqual(response.status_code, 302)
        application = Application.objects.get(job=self.job, student=self.student)
        entry = ExternalApplication.objects.get(portal_application=application)
        self.assertEqual((entry.platform, entry.status, entry.user), ("portal", "applied", self.student))

        self.client.logout()
        self.login(self.alumni)
        self.client.post(reverse("jobs:update_status", args=[application.pk]), {"status": "shortlisted"})
        entry.refresh_from_db()
        self.assertEqual(entry.status, "interview")

    def test_cannot_apply_twice(self):
        self.login(self.student)
        self.client.post(reverse("jobs:apply", args=[self.job.pk]), {"resume": pdf()})
        self.client.post(reverse("jobs:apply", args=[self.job.pk]), {"resume": pdf("second.pdf")})
        self.assertEqual(Application.objects.filter(job=self.job, student=self.student).count(), 1)

    def test_resume_access_is_restricted(self):
        self.login(self.student)
        self.client.post(reverse("jobs:apply", args=[self.job.pk]), {"resume": pdf()})
        application = Application.objects.get(job=self.job)
        url = reverse("jobs:resume", args=[application.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.client.logout()

        self.login(self.alumni)  # the poster
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.client.logout()

        self.login(self.other)  # a stranger
        self.assertEqual(self.client.get(url).status_code, 403)

    # ---------------------------------------------------------------- tracker
    def test_tracker_records_are_private(self):
        self.login(self.student)
        response = self.client.post(reverse("tracker:create"), {
            "company_name": "Google", "job_title": "SDE", "platform": "linkedin",
            "applied_date": "2026-01-15", "status": "applied",
        })
        self.assertEqual(response.status_code, 302)
        entry = ExternalApplication.objects.get(user=self.student, company_name="Google")
        self.client.logout()

        self.login(self.other)
        self.assertEqual(self.client.get(reverse("tracker:edit", args=[entry.pk])).status_code, 404)
        self.assertEqual(
            self.client.post(reverse("tracker:quick_status", args=[entry.pk]), {"status": "selected"}).status_code, 404
        )

    def test_company_cannot_use_tracker(self):
        self.login(self.company)
        self.assertEqual(self.client.get(reverse("tracker:list")).status_code, 403)

    # ---------------------------------------------------------------- referrals
    def test_referral_request_and_response(self):
        self.login(self.student)
        payload = {
            "alumni": self.alumni.pk, "company_name": "TCS", "job_title": "Python Developer",
            "message": "Please refer me.",
        }
        response = self.client.post(reverse("referrals:request"), payload)
        self.assertEqual(response.status_code, 302)
        referral = ReferralRequest.objects.get(student=self.student)
        self.assertEqual(referral.status, "pending")

        # same pending request again is blocked
        again = self.client.post(reverse("referrals:request"), payload)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(ReferralRequest.objects.filter(student=self.student).count(), 1)

        # a student cannot respond
        denied = self.client.post(reverse("referrals:respond", args=[referral.pk]), {"decision": "accept"})
        self.assertEqual(denied.status_code, 403)
        self.client.logout()

        self.login(self.alumni)
        self.client.post(reverse("referrals:respond", args=[referral.pk]), {"decision": "accept", "reply": "Sure"})
        referral.refresh_from_db()
        self.assertEqual((referral.status, referral.alumni_reply), ("accepted", "Sure"))
        self.assertIsNotNone(referral.responded_at)

    def test_referral_hidden_from_other_users(self):
        referral = ReferralRequest.objects.create(
            student=self.student, alumni=self.alumni, company_name="TCS", job_title="Dev", message="Hi"
        )
        self.login(self.other)
        self.assertEqual(self.client.get(reverse("referrals:detail", args=[referral.pk])).status_code, 403)

    def test_referral_uses_tracked_application_status(self):
        tracked = ExternalApplication.objects.create(
            user=self.student, company_name="TCS", job_title="Dev", platform="linkedin", status="interview"
        )
        referral = ReferralRequest.objects.create(
            student=self.student, alumni=self.alumni, external_application=tracked,
            company_name="TCS", job_title="Dev", message="Hi",
        )
        self.assertEqual(referral.linked_application_status(), ("interview", "Interview"))

    # ---------------------------------------------------------------- analytics
    def test_career_stats_numbers(self):
        rows = [
            ("linkedin", "applied"), ("linkedin", "interview"), ("linkedin", "rejected"),
            ("naukri", "selected"), ("naukri", "no_response"), ("indeed", "applied"),
        ]
        for platform, status in rows:
            ExternalApplication.objects.create(
                user=self.student, company_name="C", job_title="T", platform=platform, status=status
            )
        stats = career_stats(self.student)
        totals = stats["totals"]
        self.assertEqual(totals["total"], 6)
        self.assertEqual(totals["interview"], 1)
        self.assertEqual(totals["rejected"], 1)
        self.assertEqual(totals["pending"], 3)  # 2 applied + 1 no_response
        by_platform = {p["key"]: p["count"] for p in stats["platforms"]}
        self.assertEqual(by_platform, {"linkedin": 3, "naukri": 2, "indeed": 1})

        self.login(self.student)
        self.assertEqual(self.client.get(reverse("analytics:dashboard")).status_code, 200)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class JobSearchPlanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def make(username, role, **extra):
            return User.objects.create_user(
                username, password=PASSWORD, role=role, first_name=username.title(),
                email=f"{username}@example.com", **extra,
            )

        cls.student = make("stu", "student")
        cls.other = make("other", "student")
        cls.alumni = make("alu", "alumni", company_name="TCS", designation="Engineer", linkedin_url="https://linkedin.com/in/alu")
        cls.company = make("comp", "company", company_name="Accenture")

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password=PASSWORD))

    def app(self, **kwargs):
        data = dict(user=self.student, company_name="Acme", job_title="Dev", platform="linkedin")
        data.update(kwargs)
        return ExternalApplication.objects.create(**data)

    # ---------------------------------------------------------------- access
    def test_planner_pages_open_for_candidates_only(self):
        names = ["overview", "resumes", "resume_create", "networking", "networking_create",
                 "followups", "report", "goals"]
        for user in (self.student, self.alumni):
            self.login(user)
            for name in names:
                self.assertEqual(self.client.get(reverse(f"planner:{name}")).status_code, 200, f"{user.role} {name}")
            self.client.logout()
        self.login(self.company)
        self.assertEqual(self.client.get(reverse("planner:overview")).status_code, 403)

    # ---------------------------------------------------------------- resumes
    def test_only_one_default_resume(self):
        first = Resume.objects.create(user=self.student, title="A", file=pdf("a.pdf"), is_default=True)
        second = Resume.objects.create(user=self.student, title="B", file=pdf("b.pdf"), is_default=True)
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_resume_file_is_private(self):
        resume = Resume.objects.create(user=self.student, title="A", file=pdf("a.pdf"))
        url = reverse("planner:resume_file", args=[resume.pk])
        self.login(self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.client.logout()
        self.login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_first_resume_becomes_default(self):
        self.login(self.student)
        response = self.client.post(reverse("planner:resume_create"), {"title": "Main", "version": "v1", "file": pdf()})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Resume.objects.get(user=self.student, title="Main").is_default)

    def test_tracker_uses_chosen_resume_version_and_sets_followup(self):
        resume = Resume.objects.create(user=self.student, title="Backend", version="v1", file=pdf("b.pdf"))
        self.login(self.student)
        response = self.client.post(reverse("tracker:create"), {
            "company_name": "Google", "job_title": "SDE", "platform": "linkedin",
            "applied_date": "2026-01-15", "status": "applied", "resume_version": resume.pk,
        })
        self.assertEqual(response.status_code, 302)
        entry = ExternalApplication.objects.get(company_name="Google")
        self.assertEqual(entry.resume_version, resume)
        self.assertEqual(entry.resume.name, resume.file.name)
        self.assertEqual(entry.follow_up_date, date(2026, 1, 22))  # applied date + 7 days

    def test_cannot_pick_someone_elses_resume(self):
        theirs = Resume.objects.create(user=self.other, title="Theirs", file=pdf("t.pdf"))
        self.login(self.student)
        self.client.post(reverse("tracker:create"), {
            "company_name": "Google", "job_title": "SDE", "platform": "linkedin",
            "applied_date": "2026-01-15", "status": "applied", "resume_version": theirs.pk,
        })
        self.assertFalse(ExternalApplication.objects.filter(company_name="Google").exists())

    # ---------------------------------------------------------------- follow-ups
    def test_followup_done_and_snooze(self):
        today = timezone.localdate()
        entry = self.app(follow_up_date=today - timedelta(days=1))
        self.assertEqual(followups_due(self.student).count(), 1)

        self.login(self.student)
        self.client.post(reverse("planner:followup_snooze", args=[entry.pk]))
        entry.refresh_from_db()
        self.assertEqual(entry.follow_up_date, today + timedelta(days=3))
        self.assertEqual(followups_due(self.student).count(), 0)

        entry.follow_up_date = today
        entry.save()
        self.client.post(reverse("planner:followup_done", args=[entry.pk]))
        entry.refresh_from_db()
        self.assertTrue(entry.follow_up_done)
        self.assertEqual(followups_due(self.student).count(), 0)

    def test_followup_actions_are_private(self):
        entry = self.app(follow_up_date=timezone.localdate())
        self.login(self.other)
        self.assertEqual(self.client.post(reverse("planner:followup_done", args=[entry.pk])).status_code, 404)

    def test_finished_applications_do_not_need_followups(self):
        self.app(status="rejected", follow_up_date=timezone.localdate() - timedelta(days=2))
        self.app(status="selected", follow_up_date=timezone.localdate() - timedelta(days=2))
        self.assertEqual(followups_due(self.student).count(), 0)

    # ---------------------------------------------------------------- daily target
    def test_today_progress_counts_against_target(self):
        for _ in range(3):
            self.app()
        progress = today_progress(self.student)
        self.assertEqual((progress["apps"], progress["app_target"], progress["app_remaining"]), (3, 5, 2))
        self.assertFalse(progress["app_done"])
        self.assertEqual(progress["app_pct"], 60)

    def test_streak_counts_days_target_was_met(self):
        today = timezone.localdate()
        for _ in range(5):
            self.app(applied_date=today - timedelta(days=1))
            self.app(applied_date=today)
        self.assertEqual(application_streak(self.student, 5), 2)

    def test_streak_survives_an_unfinished_today(self):
        today = timezone.localdate()
        for _ in range(5):
            self.app(applied_date=today - timedelta(days=1))
        for _ in range(2):
            self.app(applied_date=today)
        self.assertEqual(application_streak(self.student, 5), 1)

    def test_goals_can_be_changed(self):
        self.login(self.student)
        response = self.client.post(reverse("planner:goals"), {
            "daily_application_target": 7, "daily_networking_target": 0, "active_days_per_week": 5,
        })
        self.assertEqual(response.status_code, 302)
        goal = SearchGoal.objects.get(user=self.student)
        self.assertEqual((goal.daily_application_target, goal.weekly_application_target), (7, 35))
        self.assertFalse(today_progress(self.student)["net_enabled"])

    def test_weekly_report_counts_this_week(self):
        self.app()
        report = weekly_report(self.student, weeks=2)
        self.assertTrue(report[0]["current"])
        self.assertEqual(report[0]["applications"], 1)
        self.assertEqual(report[1]["applications"], 0)

    # ---------------------------------------------------------------- networking
    def test_alumni_link_fills_the_contact(self):
        self.login(self.student)
        response = self.client.post(reverse("planner:networking_create"), {
            "platform": "linkedin", "activity": "connect", "alumni": self.alumni.pk,
            "date": timezone.localdate().isoformat(),
        })
        self.assertEqual(response.status_code, 302)
        activity = NetworkingActivity.objects.get(user=self.student)
        self.assertEqual(activity.contact_name, self.alumni.display_name)
        self.assertEqual(activity.contact_role, "Engineer at TCS")
        self.assertEqual(activity.profile_url, "https://linkedin.com/in/alu")
        self.assertTrue(activity.is_alumni)

    def test_alumni_connections_count_unique_people(self):
        for activity in ("connect", "message"):
            NetworkingActivity.objects.create(
                user=self.student, platform="linkedin", activity=activity,
                contact_name="Rohan", is_alumni=True,
            )
        NetworkingActivity.objects.create(user=self.student, platform="github", activity="explore", contact_name="Rohan", is_alumni=True)
        NetworkingActivity.objects.create(user=self.student, platform="linkedin", activity="connect", contact_name="Recruiter")
        self.assertEqual(dashboard_stats(self.student)["alumni_connections"], 1)

    def test_networking_needs_a_name_and_no_future_dates(self):
        self.login(self.student)
        base = {"platform": "linkedin", "activity": "connect", "date": timezone.localdate().isoformat()}
        self.assertEqual(self.client.post(reverse("planner:networking_create"), base).status_code, 200)
        future = dict(base, contact_name="Someone", date=(timezone.localdate() + timedelta(days=2)).isoformat())
        self.assertEqual(self.client.post(reverse("planner:networking_create"), future).status_code, 200)
        self.assertFalse(NetworkingActivity.objects.exists())

    def test_networking_records_are_private(self):
        activity = NetworkingActivity.objects.create(user=self.student, platform="github", contact_name="X")
        self.login(self.other)
        self.assertEqual(self.client.get(reverse("planner:networking_edit", args=[activity.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("planner:networking_delete", args=[activity.pk])).status_code, 404)

    def test_directory_mentor_filter(self):
        mentor = User.objects.create_user("mentor", password=PASSWORD, role="alumni", company_name="Zoho", open_to_mentorship=True)
        self.login(self.student)
        response = self.client.get(reverse("referrals:directory"), {"mentor": "1"})
        names = [a.username for a in response.context["page_obj"]]
        self.assertEqual(names, [mentor.username])
