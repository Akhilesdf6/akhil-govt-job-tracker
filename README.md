# AKHIL GOVT JOB TRACKER

A personal vacancy-tracking project focused on Kerala State and Central Government recruitment, with Telegram notifications.

## Current setup

- GitHub Actions workflow to test the Telegram bot connection.
- Telegram credentials are read only from GitHub Actions Secrets.
- No personal date of birth, category, or private profile details are stored in this public repository.
- Vacancy collection and eligibility matching are **not yet active**. Do not treat this starter project as a live vacancy feed.

## 1. Add GitHub Actions secrets

Open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `TELEGRAM_BOT_TOKEN`: token from BotFather
- `TELEGRAM_CHAT_ID`: your Telegram user chat ID

Never put the bot token in source code, README, issues, or chat messages.

For personal alerts, open your bot in Telegram and press **Start** before testing.

## 2. Test Telegram

1. Open the repository's **Actions** tab.
2. Select **Telegram Connection Test**.
3. Press **Run workflow** → **Run workflow**.
4. Open the run and check whether it completed successfully.
5. Check Telegram for the test message.

If it fails, verify the two secret names and values. Do not share the token publicly.

## 3. Official recruitment portals

Use the official notification and application pages; always read the original notification before applying.

- Kerala PSC: https://www.keralapsc.gov.in/
- Staff Selection Commission: https://ssc.gov.in/
- UPSC: https://upsc.gov.in/
- Railway Recruitment Boards: https://www.rrbapply.gov.in/
- India Post GDS: https://indiapostgdsonline.gov.in/
- Employment News: https://employmentnews.gov.in/

## Eligibility rules planned

The tracker should check the notification's qualification, age cut-off date, category relaxations, fee rules, deadline, and official application link. Higher-secondary-required posts must remain marked **not eligible yet** until the qualification is completed.

## Important limitations

- A scheduled scanner cannot guarantee that every vacancy is found.
- Official websites may change layout or block automated access.
- A vacancy is confirmed only when its official notification is available and checked.
- This project will not submit applications or pay fees on your behalf.
