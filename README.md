# AKHIL GOVT JOB TRACKER

A GitHub Actions based monitor for possible Kerala State and Central Government vacancies, with Telegram alerts and a GitHub Pages dashboard.

## What it does
- Checks the configured official recruitment portals every 3 hours (GitHub Actions schedule; actual start may be delayed by GitHub).
- Finds possible relevant notices using job-title keywords such as clerk, LDC, office assistant, data entry, MTS and NTPC.
- Sends Telegram alerts for newly discovered links.
- Publishes scan results to the dashboard: https://akhilesdf6.github.io/akhil-govt-job-tracker/

## Required GitHub Actions secrets
Repository → Settings → Secrets and variables → Actions:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

Never place the bot token in source code or send it in chat. Start your bot with /start before testing personal chat alerts.

## Run
Repository → Actions → Government Job Scan → Run workflow.

## Enable the dashboard
Repository → Settings → Pages → Build and deployment → Source: **GitHub Actions**. The Pages workflow will then deploy the `docs` folder.

## Important eligibility note
This first automated version is a notice-discovery system, not a legally reliable eligibility decision engine. It does not parse every notification PDF or certify age, SC category, qualification, district, physical standards, fee exemption or deadline. Check every linked official notification. The user's +2 is in progress, so roles requiring a completed Plus Two must not be treated as eligible until the qualification is passed. Do not rely on keyword matches alone.

Sources: https://www.keralapsc.gov.in/ · https://ssc.gov.in/ · https://rrb.indianrailways.gov.in/ · https://www.indiapost.gov.in/
