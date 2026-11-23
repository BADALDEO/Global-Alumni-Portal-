# Global Alumni Portal

A Django web app that connects students, alumni and companies.

| Feature | What it does |
|---|---|
| **Job Portal** | Alumni and companies post jobs and internships. Students search, filter and apply with a resume. |
| **My Job Applications** | Students (and alumni) record applications made on LinkedIn, Naukri, Indeed or any site, with the resume used and a status: Applied, Interview, Selected, Rejected, No Response. Applications made on this portal are added automatically and stay in sync with the recruiter's status. |
| **Alumni Referral System** | Students browse alumni, request referrals, and alumni accept or decline with a reply. Both sides see the request and the linked application status. |
| **My Job Search Plan** | A personal planner: resume library with versions, alumni networking tracker (LinkedIn, GitHub, LeetCode, college), follow-up reminders, daily application and networking targets, weekly report and an overall job search dashboard. |
| **Career Analytics** | Total applications, interviews, rejected, pending, platform-wise statistics, monthly trend and insights, with charts. |

Extras: light and dark mode, responsive layout, profiles, alumni directory, email notifications for referrals, resumes protected behind permission checks.

## Quick start

```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt

python manage.py makemigrations accounts jobs planner tracker referrals
python manage.py migrate
python manage.py seed_demo       # optional: demo users and data
python manage.py createsuperuser # optional: for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/

### Upgrading from an earlier zip
This version changes the database structure. For a clean start, delete `db.sqlite3` and every `0*.py` file inside the `migrations` folders (keep `__init__.py`), then run the commands above.

## My Job Search Plan
Open it from the sidebar (**Job Search Plan**) or at `/plan/`.

| Part | What it does |
|---|---|
| **Overview** | Today's targets as progress rings, streak, week progress, 14-day chart, totals (applied, today, this week, alumni connections, referral requests, interviews, selected, rejected, follow-ups pending). |
| **Resumes** | Save every resume version, pick one when you log an application, see how many interviews each version got and a usage log of which resume went to which company. |
| **Networking** | Log connection requests, messages, replies and meetings on LinkedIn, GitHub, LeetCode and college network. Link alumni from the portal, or log outreach straight from the alumni directory. |
| **Follow-ups** | A reminder is set 7 days after each application (change it per application). Mark done or snooze 3 days. Overdue ones show a badge in the sidebar. |
| **Weekly report** | This week against target, day-by-day chart and the last 8 weeks. |
| **Targets** | Default 5 applications and 3 networking actions per day, 6 active days a week. All adjustable (networking can be switched off). |

Alumni profiles now also show GitHub and LeetCode links and an "Open to mentoring" tag, and the directory can filter for mentors.

## Google sign-in
The "Continue with Google" button appears on the login and signup pages once you add your Google keys. Without keys the button stays hidden and everything else works normally.

1. Open https://console.cloud.google.com/ and create a project.
2. **APIs & Services > OAuth consent screen**: choose *External*, fill the app name and your email. While the app is in *Testing*, add your own Gmail under **Test users**.
3. **APIs & Services > Credentials > Create credentials > OAuth client ID**, type **Web application**.
4. Under **Authorized redirect URIs** add exactly:
   - `http://127.0.0.1:8000/accounts/google/login/callback/`
   - `http://localhost:8000/accounts/google/login/callback/`
   - for production: `https://YOUR-DOMAIN/accounts/google/login/callback/`
5. Copy the Client ID and Client secret. Copy `.env.example` to `.env` (next to `manage.py`) and fill in:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```
6. Restart `runserver`. Open the site using the **same address** you registered (`127.0.0.1` or `localhost`).

How it works: new Google users are created automatically, then asked once to choose Student, Alumni or Company. If the Google email matches an existing account, they are signed into that account. Do not also add a "Social application" in the admin panel, the keys in `.env` are enough.

## Run the automated checks
```bash
python manage.py test
```
They cover signup rules, role permissions, apply-to-tracker sync, resume privacy, referral accept/decline, analytics numbers, the Google role step, and the job search plan (targets, streaks, follow-ups, resume versions, networking).

## Demo logins
After `python manage.py seed_demo`, the password for every account is **Demo@1234**

| Username | Role |
|---|---|
| `student1` | Student (has applications, referrals and analytics data) |
| `student2` | Student |
| `alumni1`, `alumni2`, `alumni3` | Alumni (TCS, Infosys, Zoho) |
| `company1` | Company (Accenture) |

Use `python manage.py seed_demo --reset` to recreate the demo data. Delete these accounts before going live.

## Project layout
```
accounts/    users, roles, signup/login, profile, dashboard
jobs/        job portal and applicants
tracker/     My Job Applications (+ portal sync)
referrals/   alumni directory and referral requests
analytics/   Career Analytics
planner/     My Job Search Plan (resumes, networking, targets, follow-ups, weekly report)
core/        shared helpers (form styling, protected file serving, sidebar context)
templates/   all pages (Bootstrap 5 + custom design system in static/css/style.css)
```

## Deploying (Render, Railway, PythonAnywhere...)
1. Set the environment variables listed in `.env.example` (`DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`).
2. Build command: `./build.sh`  Start command: `gunicorn config.wsgi`
3. Resumes are stored on disk in `MEDIA_ROOT`. On hosts with temporary disks, attach a persistent disk and point `MEDIA_ROOT` to it, otherwise uploaded resumes are lost on redeploy.
4. Create an admin with `python manage.py createsuperuser`.
