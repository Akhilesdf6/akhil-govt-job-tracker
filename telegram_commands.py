import ast
import html
import json
import os
from datetime import datetime

import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID", ""))
API = f"https://api.telegram.org/bot{TOKEN}"

KEYBOARD = {
    "keyboard": [
        [{"text": "🔎 Latest Jobs"}, {"text": "📊 Status"}],
        [{"text": "🌐 Sources"}, {"text": "❓ Help"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
    "input_field_placeholder": "ഒരു command തിരഞ്ഞെടുക്കുക…",
}


def api(method, payload=None):
    r = requests.post(f"{API}/{method}", json=payload or {}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data["result"]


def send(chat_id, message):
    api("sendMessage", {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": KEYBOARD,
    })


def load_jobs():
    try:
        with open("docs/jobs.json", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def response(command, data):
    jobs = data.get("jobs", [])
    if command in ("/start", "/help", "/menu", "❓ help"):
        return (
            "🤖 <b>AKHIL AI JOB ASSISTANT</b>\n"
            "<i>Government Vacancy Tracker</i>\n\n"
            "സ്വാഗതം! പുതിയ സർക്കാർ ജോലി അറിയിപ്പുകൾ കണ്ടെത്താനും tracker പരിശോധിക്കാനും താഴെയുള്ള buttons ഉപയോഗിക്കാം.\n\n"
            "🔎 <b>Latest Jobs</b> — പുതിയതായി കണ്ടെത്തിയ അറിയിപ്പുകൾ\n"
            "📊 <b>Status</b> — അവസാന scan വിവരങ്ങൾ\n"
            "🌐 <b>Sources</b> — നിരീക്ഷിക്കുന്ന ഔദ്യോഗിക സൈറ്റുകൾ\n"
            "❓ <b>Help</b> — സഹായം\n\n"
            "Commands: /latest  /status  /sources  /help\n\n"
            "⚠️ അറിയിപ്പുകൾ സാധ്യതയുള്ളവയാണ്. യോഗ്യതയും അവസാന തീയതിയും ഔദ്യോഗിക വിജ്ഞാപനത്തിൽ ഉറപ്പാക്കുക."
        )

    if command in ("/status", "📊 status"):
        updated = data.get("updated_at", "ലഭ്യമല്ല")
        try:
            updated = datetime.fromisoformat(updated.replace("Z", "+00:00")).strftime("%d-%m-%Y %H:%M UTC")
        except (ValueError, AttributeError):
            pass
        return (
            "📊 <b>TRACKER STATUS</b>\n\n"
            f"🕒 <b>അവസാന Scan:</b> {html.escape(str(updated))}\n"
            f"🌐 <b>പരിശോധിച്ച ഉറവിടങ്ങൾ:</b> {data.get('sources_checked', 0)}\n"
            f"📌 <b>കണ്ടെത്തിയ അറിയിപ്പുകൾ:</b> {len(jobs)}\n"
            f"⚠️ <b>Source errors:</b> {len(data.get('source_errors', []))}\n\n"
            "Scan schedule: ഓരോ 3 മണിക്കൂറിലും (GitHub വൈകാൻ സാധ്യതയുണ്ട്).\n"
            "എല്ലാ സർക്കാർ ഒഴിവുകളും കണ്ടെത്തുമെന്ന് ഉറപ്പില്ല."
        )

    if command in ("/latest", "🔎 latest jobs"):
        if not jobs:
            return (
                "🔎 <b>LATEST JOB NOTICES</b>\n\n"
                "ഇപ്പോൾ Dashboard-ൽ അറിയിപ്പുകളൊന്നുമില്ല. അടുത്ത scan-ൽ വീണ്ടും പരിശോധിക്കുക.\n"
                "🌐 <a href=\"https://akhilesdf6.github.io/akhil-govt-job-tracker/\">Open Dashboard</a>"
            )
        lines = ["🔎 <b>LATEST POSSIBLE JOB NOTICES</b>"]
        for j in jobs[:7]:
            authority = html.escape(str(j.get("authority", "വകുപ്പ്")))
            title = html.escape(str(j.get("title", "തസ്തിക")))
            url = html.escape(str(j.get("url", "")), quote=True)
            link = f'<a href="{url}">Official notice / source ↗</a>' if url.startswith(("https://", "http://")) else "Link unavailable"
            lines.append(f"\n🏛️ <b>{authority}</b>\n💼 <b>{title}</b>\n🔗 {link}")
        lines.append(
            "\n⚠️ ഇവ സാധ്യതയുള്ള അറിയിപ്പുകളാണ്. അപേക്ഷിക്കുന്നതിന് മുമ്പ് ഔദ്യോഗിക വിജ്ഞാപനം വായിച്ച് യോഗ്യത, അവസാന തീയതി, അപേക്ഷാ ലിങ്ക് എന്നിവ പരിശോധിക്കുക."
        )
        return "\n".join(lines)[:3900]

    if command in ("/sources", "🌐 sources"):
        try:
            with open("job_finder.py", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            sources = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "SOURCES" for t in node.targets
                ):
                    sources = ast.literal_eval(node.value)
                    break
            lines = ["🌐 <b>MONITORED OFFICIAL SOURCES</b>"]
            lines.extend(
                f'{i}. <b>{html.escape(str(s["name"]))}</b>\n'
                f'<a href="{html.escape(str(s["url"]), quote=True)}">Open official site ↗</a>'
                for i, s in enumerate(sources, 1)
            )
            lines.append("\nഈ പട്ടിക എല്ലാ സർക്കാർ വകുപ്പുകളുടെയും സമ്പൂർണ്ണ പട്ടികയല്ല.")
            return "\n".join(lines)[:3900]
        except Exception:
            return (
                "Source പട്ടിക ഇപ്പോൾ വായിക്കാൻ കഴിഞ്ഞില്ല.\n"
                '<a href="https://akhilesdf6.github.io/akhil-govt-job-tracker/">Open Dashboard</a>'
            )

    return "ഈ option ലഭ്യമല്ല. താഴെയുള്ള menu button ഉപയോഗിക്കുക അല്ലെങ്കിൽ /help അയയ്ക്കുക."


def main():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram secrets are not configured")

    api("setMyCommands", {"commands": [
        {"command": "start", "description": "Open the job assistant menu"},
        {"command": "help", "description": "Show help and buttons"},
        {"command": "status", "description": "Show tracker scan status"},
        {"command": "latest", "description": "Show latest possible job notices"},
        {"command": "sources", "description": "List monitored official sources"},
    ]})

    try:
        with open("telegram_offset.json", encoding="utf-8") as f:
            offset = int(json.load(f).get("offset", 0))
    except (OSError, ValueError, TypeError):
        offset = 0

    updates = api("getUpdates", {
        "offset": offset,
        "timeout": 0,
        "allowed_updates": ["message"],
    })
    data = load_jobs()
    next_offset = offset

    for update in updates:
        next_offset = max(next_offset, int(update["update_id"]) + 1)
        message = update.get("message", {})
        chat = message.get("chat", {})
        if str(chat.get("id", "")) != CHAT_ID:
            continue
        incoming = (message.get("text") or "").strip()
        if not incoming:
            continue
        command = incoming.split()[0].split("@")[0].lower() if incoming.startswith("/") else incoming.lower()
        send(chat["id"], response(command, data))

    with open("telegram_offset.json", "w", encoding="utf-8") as f:
        json.dump({"offset": next_offset}, f)

    print(f"Processed {len(updates)} Telegram update(s).")


if __name__ == "__main__":
    main()
