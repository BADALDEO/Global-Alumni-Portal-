from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from jobs.models import Application, Job
from planner.models import NetworkingActivity, Resume, SearchGoal
from referrals.models import ReferralRequest
from tracker.models import ExternalApplication
from tracker.services import sync_portal_application

PASSWORD = "Demo@1234"
DEMO_USERNAMES = ["student1", "student2", "alumni1", "alumni2", "alumni3", "company1"]


def demo_pdf():
    text = "BT /F1 20 Tf 30 80 Td (Demo Resume) Tj ET"
    objs = [
        "<</Type/Catalog/Pages 2 0 R>>",
        "<</Type/Pages/Kids[3 0 R]/Count 1>>",
        "<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 160]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        f"<</Length {len(text)}>>\nstream\n{text}\nendstream",
        "<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out, offsets = "%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF"
    return out.encode()


class Command(BaseCommand):
    help = "Create demo users, jobs, applications and referrals so every screen has data."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo users first")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            User.objects.filter(username__in=DEMO_USERNAMES).delete()
            self.stdout.write("Old demo data removed.")
        elif User.objects.filter(username="student1").exists():
            self.stdout.write(self.style.WARNING("Demo data already exists. Use --reset to recreate it."))
            return

        today = timezone.localdate()

        def make_user(username, first, last, role, **extra):
            user = User(username=username, first_name=first, last_name=last,
                        email=f"{username}@example.com", role=role, **extra)
            user.set_password(PASSWORD)
            user.save()
            return user

        student1 = make_user("student1", "Aarav", "Sharma", "student", graduation_year=today.year + 1,
                             bio="Final-year CSE student who loves building full stack apps with Python and Django.")
        student2 = make_user("student2", "Priya", "Verma", "student", graduation_year=today.year)
        alumni1 = make_user("alumni1", "Rohan", "Mehta", "alumni", company_name="TCS", designation="Senior Software Engineer",
                            graduation_year=2018, bio="Backend engineer. Happy to help juniors with referrals and interview prep.",
                            linkedin_url="https://www.linkedin.com/", github_url="https://github.com/",
                            leetcode_url="https://leetcode.com/", open_to_mentorship=True)
        alumni2 = make_user("alumni2", "Sneha", "Kapoor", "alumni", company_name="Infosys", designation="Technical Lead",
                            graduation_year=2016, bio="Leading a platform team. Ask me about Java and cloud roles.",
                            linkedin_url="https://www.linkedin.com/", github_url="https://github.com/",
                            open_to_mentorship=True)
        alumni3 = make_user("alumni3", "Karan", "Singh", "alumni", company_name="Zoho", designation="Product Engineer",
                            graduation_year=2020, linkedin_url="https://www.linkedin.com/",
                            leetcode_url="https://leetcode.com/")
        company1 = make_user("company1", "Neha", "Joshi", "company", company_name="Accenture", designation="Talent Acquisition")

        # ---- jobs
        jobs_data = [
            (alumni1, "Python Backend Developer", "TCS", "job", "Bengaluru", "6-9 LPA", "Python, Django, REST, SQL", 21,
             "Build and maintain backend services for enterprise clients. You will work with a small team, write clean APIs and own features end to end."),
            (alumni1, "Software Engineer Intern", "TCS", "internship", "Remote", "20,000/month", "Python, Git, Problem solving", 14,
             "A 6-month internship with mentorship from senior engineers and a chance of a pre-placement offer."),
            (alumni2, "Java Full Stack Developer", "Infosys", "job", "Pune", "5-8 LPA", "Java, Spring Boot, React", 30,
             "Join the digital engineering team building customer-facing portals."),
            (alumni3, "Product Engineer", "Zoho", "job", "Chennai", "8-12 LPA", "Data structures, Java, JavaScript", 18,
             "Work on products used by millions. Strong fundamentals matter more than frameworks."),
            (alumni3, "Frontend Intern", "Zoho", "internship", "Chennai", "15,000/month", "HTML, CSS, JavaScript", 10,
             "Learn by shipping UI components used in real products."),
            (company1, "Associate Software Engineer", "Accenture", "job", "Hyderabad", "4.5-6 LPA", "Any programming language, SQL", 25,
             "Campus hiring drive for the 2026 batch. Structured training in your first 8 weeks."),
            (company1, "Data Analyst Intern", "Accenture", "internship", "Gurugram", "18,000/month", "Excel, SQL, Python", 12,
             "Analyse business data and build dashboards for client teams."),
            (alumni2, "DevOps Engineer", "Infosys", "job", "Remote", "7-10 LPA", "Linux, Docker, CI/CD, AWS", 40,
             "Automate delivery pipelines and keep production healthy."),
        ]
        jobs = []
        for poster, title, company, jtype, loc, pay, skills, days, desc in jobs_data:
            jobs.append(Job.objects.create(
                posted_by=poster, title=title, company_name=company, job_type=jtype, location=loc,
                salary_or_stipend=pay, skills_required=skills, description=desc,
                apply_deadline=today + timedelta(days=days),
            ))

        # ---- applications made on the portal (these sync into the tracker)
        pdf = demo_pdf()
        for job, status in ((jobs[0], "shortlisted"), (jobs[1], "applied")):
            application = Application(job=job, student=student1, cover_note="I would love to contribute to this team.")
            application.resume.save("demo_resume.pdf", ContentFile(pdf), save=False)
            application.status = status
            application.save()
            sync_portal_application(application)

        # ---- applications made elsewhere
        def months_ago(n, day=10):
            month, year = today.month - n, today.year
            while month <= 0:
                month += 12
                year -= 1
            return today.replace(year=year, month=month, day=min(day, 28))

        tracked = [
            ("Google", "Backend Engineer", "linkedin", "interview", 1, 5),
            ("Amazon", "SDE Intern", "linkedin", "rejected", 4, 12),
            ("Microsoft", "Software Engineer", "linkedin", "no_response", 3, 3),
            ("Flipkart", "Backend Developer", "linkedin", "applied", 0, 4),
            ("Wipro", "Python Developer", "naukri", "selected", 2, 8),
            ("Capgemini", "Analyst", "naukri", "rejected", 3, 20),
            ("HCL", "Django Developer", "naukri", "no_response", 2, 25),
            ("Paytm", "Full Stack Intern", "indeed", "interview", 1, 18),
            ("Swiggy", "Software Engineer", "indeed", "applied", 0, 2),
            ("Razorpay", "Backend Intern", "indeed", "rejected", 4, 6),
            ("Freshworks", "Associate Engineer", "company_site", "interview", 1, 9),
            ("Cisco", "Software Intern", "company_site", "no_response", 5, 14),
            ("Adobe", "Frontend Engineer", "company_site", "rejected", 5, 2),
            ("Startup Hub", "Python Intern", "other", "applied", 0, 1),
        ]
        for company, title, platform, status, ago, day in tracked:
            ExternalApplication.objects.create(
                user=student1, company_name=company, job_title=title, platform=platform,
                status=status, applied_date=min(months_ago(ago, day), today),
                job_link="https://example.com/jobs", notes="",
            )

        google = ExternalApplication.objects.get(user=student1, company_name="Google")

        # ---- referrals
        ReferralRequest.objects.create(
            student=student1, alumni=alumni1, job=jobs[0], company_name="TCS", job_title="Python Backend Developer",
            message="Hi Rohan, I am a final-year CSE student with Django project experience. I applied on the portal and would be grateful for a referral.",
            status="pending",
        )
        ReferralRequest.objects.create(
            student=student1, alumni=alumni2, company_name="Infosys", job_title="Java Full Stack Developer",
            message="Hello Sneha, I am interested in the Java Full Stack opening. I have built two full stack projects. Could you please refer me?",
            status="accepted", alumni_reply="Happy to help. Please email me your resume and I will submit the referral this week.",
            responded_at=timezone.now() - timedelta(days=2),
        )
        ReferralRequest.objects.create(
            student=student1, alumni=alumni3, external_application=google, company_name="Google", job_title="Backend Engineer",
            message="Hi Karan, sharing my application for a Backend Engineer role. Any guidance or a referral would mean a lot.",
            status="rejected", alumni_reply="Sorry, I am not at Google. I can review your resume though.",
            responded_at=timezone.now() - timedelta(days=5),
        )
        ReferralRequest.objects.create(
            student=student2, alumni=alumni1, company_name="TCS", job_title="Software Engineer Intern",
            message="Hi Rohan, I would like to apply for the internship. Could you refer me?", status="pending",
        )


        # ---- job search plan: resume library, follow-ups, daily activity, networking
        goal = SearchGoal.objects.create(
            user=student1, daily_application_target=5, daily_networking_target=3, active_days_per_week=6
        )

        resumes = {}
        for key, title, version, role, default in (
            ("backend", "Backend developer resume", "v2", "Python / Django developer", True),
            ("fullstack", "Full stack resume", "v1", "Full stack developer", False),
            ("intern", "Internship resume", "v1", "Software intern", False),
        ):
            resume = Resume(user=student1, title=title, version=version, target_role=role,
                            notes="Demo resume version.", is_default=default)
            resume.file.save(f"{key}_resume.pdf", ContentFile(pdf), save=False)
            resume.save()
            resumes[key] = resume

        for company, key in (("Google", "backend"), ("Wipro", "backend"), ("Microsoft", "backend"),
                             ("Paytm", "fullstack"), ("Freshworks", "fullstack"),
                             ("Amazon", "intern"), ("Razorpay", "intern")):
            entry = ExternalApplication.objects.get(user=student1, company_name=company)
            entry.resume_version = resumes[key]
            entry.resume = resumes[key].file.name
            entry.save()

        # reminders: recent ones are due or upcoming, old ones were already followed up
        for entry in ExternalApplication.objects.filter(user=student1, portal_application__isnull=True):
            if entry.status in ("applied", "no_response", "interview"):
                due = entry.applied_date + timedelta(days=7)
                entry.follow_up_date = due
                entry.follow_up_done = due < today - timedelta(days=10)
                entry.save(update_fields=["follow_up_date", "follow_up_done"])

        # the last two weeks of daily applications (index 0 = today)
        companies = ["Zomato", "Meesho", "PhonePe", "Atlassian", "Oracle", "SAP", "Mphasis", "LTIMindtree",
                     "Tech Mahindra", "Cognizant", "Deloitte", "ThoughtWorks", "Nagarro", "Persistent"]
        platforms = ["linkedin", "naukri", "indeed", "company_site", "internshala", "glassdoor", "wellfound", "referral"]
        statuses = ["applied", "no_response", "interview", "applied", "rejected", "applied"]
        daily = [3, 5, 6, 4, 0, 5, 7, 5, 2, 6, 5, 4, 3, 5]
        n = 0
        for back, count in enumerate(daily):
            day = today - timedelta(days=back)
            for _ in range(count):
                status = "applied" if back == 0 else statuses[n % len(statuses)]
                applied = ExternalApplication.objects.create(
                    user=student1, company_name=companies[n % len(companies)],
                    job_title=["Software Engineer", "Python Developer", "Backend Intern", "Full Stack Developer"][n % 4],
                    platform=platforms[n % len(platforms)], status=status, applied_date=day,
                    follow_up_date=day + timedelta(days=7), follow_up_done=False,
                    resume_version=resumes["backend"] if n % 3 == 0 else None,
                )
                if applied.resume_version:
                    applied.resume = applied.resume_version.file.name
                    applied.save(update_fields=["resume"])
                n += 1

        for platform, activity, name, role, alumnus, days_ago, notes in (
            ("linkedin", "connect", "Rohan Mehta", "Senior Software Engineer at TCS", alumni1, 0, "Sent a note about backend roles."),
            ("linkedin", "message", "Sneha Kapoor", "Technical Lead at Infosys", alumni2, 0, "Asked about the Java opening."),
            ("linkedin", "connected", "Rohan Mehta", "Senior Software Engineer at TCS", alumni1, 1, "Accepted my request."),
            ("github", "explore", "Karan Singh", "Product Engineer at Zoho", alumni3, 1, "Read through his open-source projects."),
            ("leetcode", "connect", "Meera Iyer", "Competitive programmer", None, 2, "Followed her contest write-ups."),
            ("college", "meeting", "Sneha Kapoor", "Technical Lead at Infosys", alumni2, 3, "20 minute call about interviews."),
            ("linkedin", "connect", "Priya Nair", "Recruiter at Accenture", None, 3, "Recruiter for the 2026 drive."),
            ("college", "message", "Vikram Rao", "Final-year senior", None, 4, "Asked for resume feedback."),
            ("github", "connect", "Ananya Das", "Django contributor", None, 5, "Commented on her PR."),
            ("linkedin", "reply", "Priya Nair", "Recruiter at Accenture", None, 6, "She shared the application link."),
        ):
            NetworkingActivity.objects.create(
                user=student1, platform=platform, activity=activity, contact_name=name, contact_role=role,
                is_alumni=alumnus is not None, alumni=alumnus, date=today - timedelta(days=days_ago), notes=notes,
            )

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(f"Logins (password for all: {PASSWORD}):")
        for name in DEMO_USERNAMES:
            self.stdout.write(f"  {name}")
