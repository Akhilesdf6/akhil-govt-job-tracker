import json, os, re, hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Official recruitment portals. This is a broad monitor, not an exhaustive feed:
# many departments publish vacancies only on their own regional/department pages.
SOURCES = [
    {"name":"Kerala PSC", "url":"https://www.keralapsc.gov.in/extra-ordinary-gazette-date", "base":"https://www.keralapsc.gov.in", "kind":"Kerala State"},
    {"name":"Kerala High Court", "url":"https://hckerala.gov.in/", "base":"https://hckerala.gov.in", "kind":"Kerala State"},
    {"name":"SSC", "url":"https://ssc.gov.in/for-notice-board", "base":"https://ssc.gov.in", "kind":"Central"},
    {"name":"SSC Karnataka-Kerala Region", "url":"https://ssckkr.gov.in/", "base":"https://ssckkr.gov.in", "kind":"Central"},
    {"name":"UPSC", "url":"https://upsc.gov.in/whats-new", "base":"https://upsc.gov.in", "kind":"Central"},
    {"name":"Railway RRB Apply", "url":"https://www.rrbapply.gov.in/", "base":"https://www.rrbapply.gov.in", "kind":"Central"},
    {"name":"Indian Railways", "url":"https://indianrailways.gov.in/", "base":"https://indianrailways.gov.in", "kind":"Central"},
    {"name":"India Post GDS", "url":"https://indiapostgdsonline.gov.in/", "base":"https://indiapostgdsonline.gov.in", "kind":"Central"},
    {"name":"India Post", "url":"https://www.indiapost.gov.in/", "base":"https://www.indiapost.gov.in", "kind":"Central"},
    {"name":"IBPS", "url":"https://www.ibps.in/", "base":"https://www.ibps.in", "kind":"Public Sector Banks"},
    {"name":"SBI Careers", "url":"https://sbi.co.in/web/careers/current-openings", "base":"https://sbi.co.in", "kind":"Public Sector Banks"},
    {"name":"RBI Opportunities", "url":"https://opportunities.rbi.org.in/scripts/vacancies.aspx", "base":"https://opportunities.rbi.org.in", "kind":"Statutory Institution"},
    {"name":"NABARD Careers", "url":"https://www.nabard.org/careers-notices1.aspx?cid=693&id=26", "base":"https://www.nabard.org", "kind":"Statutory Institution"},
    {"name":"LIC Careers", "url":"https://licindia.in/careers", "base":"https://licindia.in", "kind":"Public Sector Insurance"},
    {"name":"Employment News", "url":"https://employmentnews.gov.in/", "base":"https://employmentnews.gov.in", "kind":"Central Government"},
    {"name":"ISRO Careers", "url":"https://www.isro.gov.in/Careers.html", "base":"https://www.isro.gov.in", "kind":"Central"},
    {"name":"DRDO", "url":"https://www.drdo.gov.in/", "base":"https://www.drdo.gov.in", "kind":"Central"},
    {"name":"ESIC", "url":"https://www.esic.gov.in/recruitments", "base":"https://www.esic.gov.in", "kind":"Central"},
]
KEYWORDS = re.compile(
    r"\b(clerk|ldc|lower division|junior assistant|office assistant|office attendant|"
    r"data entry|typist|computer assistant|computer operator|mts|multi tasking|chsl|ntpc|"
    r"level[- ]?1|group[- ]?d|peon|attender|helper|gds|gramin dak|branch postmaster|abpm|"
    r"postman|mail guard|postal assistant|apprentice|tradesman|constable|forest guard|"
    r"driver|stenographer|selection post|recruitment|vacancy|vacancies|notification)\b", re.I
)
ROLE_HINTS = re.compile(
    r"\b(clerk|ldc|lower division|junior assistant|office assistant|office attendant|"
    r"data entry|typist|computer assistant|computer operator|mts|multi tasking|chsl|ntpc|"
    r"level[- ]?1|group[- ]?d|peon|attender|helper|gds|gramin dak|branch postmaster|abpm|"
    r"postman|mail guard|postal assistant|apprentice|tradesman|constable|forest guard|"
    r"driver|stenographer|selection post)\b", re.I
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"AkhilGovtJobTracker/1.1 (official recruitment notice monitor; low-frequency requests)"})

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
                if not title or len(title) < 4 or not ROLE_HINTS.search(title):
                    continue
                if not href.startswith("https://") or href in found:
                    continue
                # Ignore obvious navigation and social links.
                if any(x in href.lower() for x in ("facebook.com", "instagram.com", "youtube.com", "twitter.com")):
                    continue
                found.add(href)
                digest = hashlib.sha256((source["name"]+title+href).encode()).hexdigest()[:14]
                jobs.append({
                    "id":digest, "authority":source["name"], "title":title[:180],
                    "url":href, "source_page":source["url"], "category":source["kind"],
                    "status":"Possible relevant notice — official notification and eligibility must be checked",
                    "eligibility":"Not verified. Check SSLC/+2 requirement, age cutoff, SC reservation/relaxation, domicile, physical standards, fee and last date in the official notice.",
                    "checked_at":datetime.now(timezone.utc).isoformat()
                })
        except Exception as exc:
            errors.append({"source":source["name"],"error":str(exc)[:240]})
    # Keep all unique matches found in this scan; dashboard labels them as unverified.
    unique = {j["id"]: j for j in jobs}
    return list(unique.values())[:300], errors

def send_telegram(message):
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID GitHub secret")
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id":chat_id,"text":message,"disable_web_page_preview":True}, timeout=20)
    r.raise_for_status()
    if not r.json().get("ok"):
        raise RuntimeError("Telegram API rejected the message")

def main():
    jobs, errors = get_jobs()
    os.makedirs("docs", exist_ok=True)
    output = {
        "updated_at":datetime.now(timezone.utc).isoformat(),
        "jobs":jobs,
        "source_errors":errors,
        "sources_checked":len(SOURCES),
        "notice":"Broad official-portal keyword monitoring, not exhaustive. Matches are unverified notices, not confirmed eligible vacancies. Read the official notification before applying."
    }
    with open("docs/jobs.json","w",encoding="utf-8") as f:
        json.dump(output,f,ensure_ascii=False,indent=2)
    old = set()
    try:
        with open("seen_ids.json",encoding="utf-8") as f: old=set(json.load(f))
    except (OSError, ValueError): pass
    new = [j for j in jobs if j["id"] not in old]
    if new:
        lines=["🔔 AKHIL GOVT JOB TRACKER","New possible government-job notices (eligibility NOT verified):"]
        for j in new[:10]:
            lines += [f"• {j['authority']}: {j['title']}", j["url"]]
        if len(new)>10:
            lines.append(f"+ {len(new)-10} more. Dashboard: https://akhilesdf6.github.io/akhil-govt-job-tracker/")
        lines.append("Before applying, verify SSLC/+2, age, SC rules, Kerala eligibility and last date in the official notice.")
        send_telegram("\\n".join(lines)[:3900])
    with open("seen_ids.json","w",encoding="utf-8") as f:
        json.dump(sorted(old|{j["id"] for j in jobs}),f)
    print(f"Checked {len(SOURCES)} official portals; collected {len(jobs)} possible notices; {len(new)} new; {len(errors)} source errors.")
    for e in errors: print("SOURCE ERROR:",e)

if __name__=="__main__":
    main()
