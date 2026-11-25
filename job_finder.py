import json, os, re, hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

SOURCES = [
    {"name":"Kerala PSC", "url":"https://www.keralapsc.gov.in/extra-ordinary-gazette-date", "base":"https://www.keralapsc.gov.in", "kind":"kerala"},
    {"name":"SSC", "url":"https://ssc.gov.in/for-notice-board", "base":"https://ssc.gov.in", "kind":"central"},
    {"name":"RRB", "url":"https://rrb.indianrailways.gov.in/", "base":"https://rrb.indianrailways.gov.in", "kind":"central"},
]
KEYWORDS = re.compile(r"\b(clerk|ldc|lower division|office assistant|office attendant|data entry|typist|computer assistant|computer operator|mts|multi tasking|chsl|ntpc|level[- ]?1|group[- ]?d|peon|attender|assistant)\b", re.I)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"AkhilGovtJobTracker/1.0 (vacancy notice monitor; respectful low-frequency requests)"})

def get_jobs():
    jobs, errors = [], []
    for source in SOURCES:
        try:
            response = SESSION.get(source["url"], timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            found = set()
            for a in soup.select("a[href]"):
                title = " ".join(a.get_text(" ", strip=True).split())
                href = urljoin(source["base"], a.get("href", ""))
                if not title or len(title) < 5 or not KEYWORDS.search(title):
                    continue
                if not href.startswith("https://") or href in found:
                    continue
                found.add(href)
                digest = hashlib.sha256((source["name"]+title+href).encode()).hexdigest()[:14]
                jobs.append({
                    "id":digest, "authority":source["name"], "title":title[:180],
                    "url":href, "source_page":source["url"],
                    "category":"Kerala State" if source["kind"]=="kerala" else "Central Government",
                    "status":"Needs official notification verification",
                    "eligibility":"Not yet verified — check qualification, age cutoff, category and district in the official notification.",
                    "checked_at":datetime.now(timezone.utc).isoformat()
                })
        except Exception as exc:
            errors.append({"source":source["name"],"error":str(exc)[:240]})
    # Keep a modest recent list; the source link always points to the authority's page.
    return jobs[:100], errors

def send_telegram(text):
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID GitHub secret")
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id":chat_id,"text":text,"disable_web_page_preview":True}, timeout=20)
    r.raise_for_status()
    if not r.json().get("ok"):
        raise RuntimeError("Telegram API rejected the message")

def main():
    jobs, errors = get_jobs()
    os.makedirs("docs", exist_ok=True)
    output = {"updated_at":datetime.now(timezone.utc).isoformat(),"jobs":jobs,"source_errors":errors,
              "notice":"Automated keyword discovery only. Always open the official notification and independently verify eligibility before applying."}
    with open("docs/jobs.json","w",encoding="utf-8") as f:
        json.dump(output,f,ensure_ascii=False,indent=2)
    old = set()
    try:
        with open("seen_ids.json",encoding="utf-8") as f: old=set(json.load(f))
    except (OSError, ValueError): pass
    new = [j for j in jobs if j["id"] not in old]
    if new:
        lines=["🔔 AKHIL GOVT JOB TRACKER","New possible matching notices (verify official PDF):"]
        for j in new[:8]:
            lines += [f"• {j['authority']}: {j['title']}", j["url"]]
        if len(new)>8: lines.append(f"+ {len(new)-8} more. Dashboard: https://akhilesdf6.github.io/akhil-govt-job-tracker/")
        send_telegram("\n".join(lines)[:3900])
    with open("seen_ids.json","w",encoding="utf-8") as f: json.dump(sorted(old|{j["id"] for j in jobs}),f)
    print(f"Collected {len(jobs)} possible notices; {len(new)} new; {len(errors)} source errors.")
    for e in errors: print("SOURCE ERROR:",e)

if __name__=="__main__": main()
