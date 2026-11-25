import json, os
from datetime import datetime
import ast
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID", ""))
API = f"https://api.telegram.org/bot{TOKEN}"

def api(method, payload=None):
    r = requests.post(f"{API}/{method}", json=payload or {}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data["result"]

def send(chat_id, message):
    api("sendMessage", {"chat_id": chat_id, "text": message, "disable_web_page_preview": True})

def load_jobs():
    try:
        with open("docs/jobs.json", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def response(command, data):
    jobs = data.get("jobs", [])
    if command in ("/start", "/help"):
        return ("🤖 AKHIL GOVT JOB TRACKER\n\nCommands:\n"
                "/status – അവസാന Scan വിവരങ്ങൾ\n"
                "/latest – പുതിയതായി കണ്ടെത്തിയ അറിയിപ്പുകൾ\n"
                "/sources – നിരീക്ഷിക്കുന്ന ഔദ്യോഗിക സൈറ്റുകൾ\n"
                "/help – സഹായം\n\n"
                "അറിയിപ്പുകൾ സാധ്യതയുള്ളവയാണ്. യോഗ്യതയും അവസാന തീയതിയും ഔദ്യോഗിക വിജ്ഞാപനത്തിൽ പരിശോധിക്കുക.")
    if command == "/status":
        updated = data.get("updated_at", "ഇതുവരെ ലഭ്യമല്ല")
        try:
            updated = datetime.fromisoformat(updated.replace("Z", "+00:00")).strftime("%d-%m-%Y %H:%M UTC")
        except Exception:
            pass
        return (f"📊 TRACKER STATUS\nഅവസാന Scan: {updated}\n"
                f"പരിശോധിച്ച ഉറവിടങ്ങൾ: {data.get('sources_checked', 0)}\n"
                f"കണ്ടെത്തിയ അറിയിപ്പുകൾ: {len(jobs)}\n"
                f"Source errors: {len(data.get('source_errors', []))}\n\n"
                "⚠️ എല്ലാ സർക്കാർ ഒഴിവുകളും കണ്ടെത്തുമെന്ന് ഉറപ്പില്ല.")
    if command == "/latest":
        if not jobs:
            return "Dashboard-ൽ ഇപ്പോൾ അറിയിപ്പുകളൊന്നുമില്ല. അടുത്ത Scan-ൽ വീണ്ടും പരിശോധിക്കുക."
        lines = ["🆕 LATEST POSSIBLE NOTICES"]
        for j in jobs[:7]:
            lines.append(f"\n🏛️ {j.get('authority', 'വകുപ്പ്')}\n💼 {j.get('title', 'തസ്തിക')}\n📄 {j.get('url', '')}")
        lines.append("\n⚠️ അറിയിപ്പുകൾ ഔദ്യോഗികമായി പരിശോധിച്ചശേഷം മാത്രം അപേക്ഷിക്കുക.")
        return "\n".join(lines)[:3900]
    if command == "/sources":
        try:
            with open("job_finder.py", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            sources = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SOURCES" for t in node.targets):
                    sources = ast.literal_eval(node.value)
                    break
            lines = ["🌐 MONITORED OFFICIAL SOURCES"]
            lines.extend(f"{i}. {s['name']} – {s['url']}" for i, s in enumerate(sources, 1))
            lines.append("\nഇത് എല്ലാ സർക്കാർ വകുപ്പുകളുടെയും സമ്പൂർണ്ണ പട്ടികയല്ല.")
            return "\n".join(lines)[:3900]
        except Exception:
            return "Source പട്ടിക ഇപ്പോൾ വായിക്കാൻ കഴിഞ്ഞില്ല. Dashboard: https://akhilesdf6.github.io/akhil-govt-job-tracker/"
    return "ഈ Command ലഭ്യമല്ല. /help അയച്ച് Commands കാണുക."

def main():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram secrets are not configured")
    api("setMyCommands", {"commands": [
        {"command": "start", "description": "Start the government job tracker bot"},
        {"command": "help", "description": "Show available bot commands"},
        {"command": "status", "description": "Show tracker scan status"},
        {"command": "latest", "description": "Show latest possible job notices"},
        {"command": "sources", "description": "List monitored official sources"}
    ]})
    try:
        with open("telegram_offset.json", encoding="utf-8") as f:
            offset = int(json.load(f).get("offset", 0))
    except (OSError, ValueError, TypeError):
        offset = 0
    updates = api("getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["message"]})
    data = load_jobs()
    next_offset = offset
    for update in updates:
        next_offset = max(next_offset, int(update["update_id"]) + 1)
        message = update.get("message", {})
        chat = message.get("chat", {})
        if str(chat.get("id", "")) != CHAT_ID:
            continue
        incoming = (message.get("text") or "").strip()
        if not incoming.startswith("/"):
            continue
        command = incoming.split()[0].split("@")[0].lower()
        send(chat["id"], response(command, data))
    with open("telegram_offset.json", "w", encoding="utf-8") as f:
        json.dump({"offset": next_offset}, f)
    print(f"Processed {len(updates)} Telegram update(s).")

if __name__ == "__main__":
    main()
