# CyberShield

A Django-based penetration testing management platform that streamlines the full lifecycle of a pentest engagement — from client onboarding to final report delivery with AI-assisted analysis.

## Features

- **Role-Based Access Control** — Three-tier hierarchy: Admin, Team Leader, and Pentester. Leaders can view all team reports and are the sole authorized submitters; members access only their own work.
- **Client Communication Pipeline** — Automated emails at every engagement milestone: team assignment, team leader contact details, report status updates, and final report delivery.
- **NOVA AI Integration** — Gemini API generates an executive summary for each submitted report. Admin reviews the summary, adds remarks, and approves or denies accordingly.
- **Automated DAST Scanner** — Selenium-powered scanner performs login brute force testing, XSS detection, and form enumeration against authorized targets.
- **OTP Registration** — Secure user onboarding via OTP verification.
- **PDF Report Generation** — Approved reports are automatically converted to PDF and emailed directly to the client.

## Tech Stack

- **Backend** — Django, Python
- **Database** — PostgreSQL (SQLite supported)
- **AI** — Google Gemini API
- **Automation** — Selenium

## Setup

```bash
git clone https://github.com/SahilRpanjwani/cybershield.git
cd cybershield
pip install -r requirements.txt
```

Configure environment variables:
```
GEMINI_API_KEY=your_key
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_app_password
```

```bash
python manage.py migrate
python manage.py runserver
```

## Team

- Sahil Panjwani
- Mahir
- Hetkumar
