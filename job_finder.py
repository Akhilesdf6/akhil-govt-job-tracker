import json, os, re, hashlib, html
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Broad official-portal monitoring; not an exhaustive vacancy feed.
SOURCES = [
    {"name":"Kerala PSC","url":"https://www.keralapsc.gov.in/","base":"https://www.keralapsc.gov.in","kind":"Kerala State"},
    {"name":"Kerala High Court Main Site","url":"https://highcourt.kerala.gov.in/","base":"https://highcourt.kerala.gov.in","kind":"Kerala State"},
    {"name":"Kerala High Court Recruitment Portal","url":"https://hckrecruitment.keralacourts.in/","base":"https://hckrecruitment.keralacourts.in","kind":"Kerala State"},
    {"name":"Kerala Employment","url":"https://employment.kerala.gov.in/","base":"https://employment.kerala.gov.in","kind":"Kerala State"},
    {"name":"SSC","url":"https://ssc.gov.in/","base":"https://ssc.gov.in","kind":"Central"},
    {"name":"SSC Karnataka-Kerala Region","url":"https://ssckkr.gov.in/","base":"https://ssckkr.gov.in","kind":"Central"},
    {"name":"UPSC Recruitment Tests","url":"https://cms.upsc.gov.in/recruitment-tests/notice/","base":"https://cms.upsc.gov.in","kind":"Central"},
    {"name":"UPSC What's New","url":"https://upsc.gov.in/whats-new","base":"https://upsc.gov.in","kind":"Central"},
    {"name":"Railway RRB Apply","url":"https://www.rrbapply.gov.in/","base":"https://www.rrbapply.gov.in","kind":"Central"},
    {"name":"Indian Railways","url":"https://indianrailways.gov.in/","base":"https://indianrailways.gov.in","kind":"Central"},
    {"name":"India Post Recruitments","url":"https://www.indiapost.gov.in/vacancies/recruitments?hl=en-US","base":"https://www.indiapost.gov.in","kind":"Central"},
    {"name":"India Post GDS","url":"https://www.indiapost.gov.in/gdsonlineengagement","base":"https://www.indiapost.gov.in","kind":"Central"},
    {"name":"IBPS","url":"https://www.ibps.in/","base":"https://www.ibps.in","kind":"Public Sector Banks"},
    {"name":"SBI Careers","url":"https://sbi.co.in/web/careers/current-openings","base":"https://sbi.co.in","kind":"Public Sector Banks"},
    {"name":"RBI Opportunities","url":"https://opportunities.rbi.org.in/scripts/vacancies.aspx","base":"https://opportunities.rbi.org.in","kind":"Statutory Institution"},
    {"name":"NABARD Careers","url":"https://www.nabard.org/careers-notices1.aspx?cid=693&id=26","base":"https://www.nabard.org","kind":"Statutory Institution"},
    {"name":"LIC Careers","url":"https://licindia.in/careers","base":"https://licindia.in","kind":"Public Sector Insurance"},
    {"name":"Employment News All Jobs","url":"https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All","base":"https://employmentnews.gov.in","kind":"Central Government"},
    {"name":"ISRO Careers","url":"https://www.isro.gov.in/Careers.html","base":"https://www.isro.gov.in","kind":"Central"},
    {"name":"DRDO","url":"https://www.drdo.gov.in/","base":"https://www.drdo.gov.in","kind":"Central"},
    {"name":"ESIC","url":"https://www.esic.gov.in/recruitments","base":"https://www.esic.gov.in","kind":"Central"},
    {"name":"Department of Financial Services","url":"https://financialservices.gov.in/vacancies","base":"https://financialservices.gov.in","kind":"Central Government"},
    {"name":"Food Corporation of India","url":"https://fci.gov.in/recruitment","base":"https://fci.gov.in","kind":"Central PSU"},
    {"name":"SEBI Vacancies","url":"https://www.sebi.gov.in/sebiweb/about/AboutAction.do?doVacancies=yes","base":"https://www.sebi.gov.in","kind":"Statutory Institution"},
    {"name":"NITI Aayog Recruitment","url":"https://www.niti.gov.in/work-niti/vacancy-circular","base":"https://www.niti.gov.in","kind":"Central Government"},
    {"name":"ITPO Careers","url":"https://www.itpo.gov.in/career-at-itpo","base":"https://www.itpo.gov.in","kind":"Central PSU"},
    {"name":"National Career Service Government Vacancies","url":"https://www.ncs.gov.in/pages/govt-job-vacancies.aspx","base":"https://www.ncs.gov.in","kind":"Central Government"}
]
EXCLUDE_HINTS = re.compile(r"\b(shortlisted|short list|response sheet|answer key|admit card|hall ticket|call letter|interview|result|ranked list|exam held|objection redressal|provisional list|final list)\b", re.I)
ROLE_HINTS = re.compile(
    r"\b(clerk|ldc|lower division|assistant|attendant|data entry|typist|computer|"
    r"operator|mts|multi tasking|chsl|ntpc|level[- ]?1|group[- ]?d|peon|helper|"
    r"support staff|watchman|security guard|fireman|cleaner|gds|gramin dak|"
    r"branch postmaster|abpm|postman|mail guard|postal assistant|apprentice|"
    r"tradesman|constable|forest guard|driver|stenographer|selection post|"
    r"technician|lab assistant|staff nurse)\b", re.I
)
# Broad second-pass terms intentionally include generic recruitment notices too.
# This favors recall over precision; every result must be checked in its official notice.
RECRUITMENT_HINTS = re.compile(
    r"\b(recruitment|vacanc(?:y|ies)|notification|advertisement|apply online|"
    r"applications? invited|engagement|appointment|direct recruitment|"
    r"career opportunities|job openings|selection process|employment notice)\b", re.I
)
SESSION = requests.Session()
retry_policy = Retry(total=3, connect=3, read=3, status=3, backoff_factor=1.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "POST"]), respect_retry_after_header=True)
adapter = HTTPAdapter(max_retries=retry_policy)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)
SESSION.headers.update({"User-Agent":"AkhilGovtJobTracker/1.3 (official recruitment notice monitor; low-frequency requests)"})

def get_jobs():
    jobs, errors = [], []
    for source in SOURCES:
        try:
            response = SESSION.get(source["url"], timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            found = set()
            for a in soup.select("a[href]"):
                parent_text = " ".join(a.parent.get_text(" ", strip=True).split()) if a.parent else ""
                link_text = " ".join(a.get_text(" ", strip=True).split())
                # Parent/card text already includes link text on most portals; avoid duplication.
                title = parent_text if parent_text and link_text.lower() in parent_text.lower() else " ".join((link_text + " " + parent_text).split())
                href = urljoin(source["base"], a.get("href", ""))
                if not title or len(title) < 4 or not (ROLE_HINTS.search(title) or RECRUITMENT_HINTS.search(title)) or EXCLUDE_HINTS.search(title):
                    continue
                if not href.startswith("https://") or href in found:
                    continue
                if any(x in href.lower() for x in ("facebook.com", "instagram.com", "youtube.com", "twitter.com")):
                    continue
                found.add(href)
                # Trim repeated adjacent title fragments caused by anchor + parent text.
                words = title.split()
                half = len(words) // 2
                if len(words) > 8 and words[:half] == words[half:]:
                    title = " ".join(words[:half])
                digest = hashlib.sha256((source["name"]+title+href).encode()).hexdigest()[:14]
                jobs.append({
                    "id":digest, "authority":source["name"], "title":title[:180],
                    "url":href, "source_page":source["url"], "category":source["kind"],
                    "status":"Possible notice — verify official notification before applying",
                    "eligibility":"Not verified. Check qualification, age cutoff, SC reservation/relaxation, domicile, physical standards, fee and last date in the official notice.",
                    "checked_at":datetime.now(timezone.utc).isoformat()
                })
        except Exception as exc:
            errors.append({"source":source["name"],"error":str(exc)[:240]})
    unique = {j["id"]: j for j in jobs}
    return list(unique.values()), errors

def send_telegram(message):
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing Telegram GitHub secrets")
    r = SESSION.post(f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id":chat_id,"text":message,"parse_mode":"HTML","disable_web_page_preview":True}, timeout=20)
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
        for j in new:
            # Bold, scannable HTML alert with the official notice link.
            authority = html.escape(j["authority"])
            title = html.escape(j["title"])
            category = html.escape(j["category"])
            notice_url = html.escape(j["url"], quote=True)
            card = [
                "🔔 <b>AKHIL GOVT JOB ALERT</b>",
                "🆕 <b>പുതിയ ജോലി അറിയിപ്പ്</b>",
                "",
                f"🏛️ <b>വകുപ്പ്:</b> {authority}",
                f"💼 <b>തസ്തിക / Post:</b> {title}",
                f"📂 <b>വിഭാഗം:</b> {category}",
                "",
                "🎓 <b>യോഗ്യത:</b> വിജ്ഞാപനത്തിൽ പരിശോധിക്കുക",
                "🎂 <b>പ്രായപരിധി:</b> വിജ്ഞാപനത്തിൽ പരിശോധിക്കുക",
                "🏷️ <b>SC ഇളവ് / സംവരണം:</b> വിജ്ഞാപനത്തിൽ പരിശോധിക്കുക",
                "💰 <b>ശമ്പളം:</b> വിജ്ഞാപനത്തിൽ പരിശോധിക്കുക",
                "📅 <b>അവസാന തീയതി:</b> സ്ഥിരീകരിച്ചിട്ടില്ല",
                "",
                f"🔗 <b>നേരിട്ടുള്ള ഔദ്യോഗിക ലിങ്ക്:</b> <a href=\"{notice_url}\">ഇവിടെ തുറക്കുക</a>",
                "",
                "⚠️ <b>ശ്രദ്ധിക്കുക:</b> ഇത് സാധ്യതയുള്ള അറിയിപ്പാണ്. അപേക്ഷ ഇപ്പോഴും തുറന്നിട്ടുണ്ടോ, യോഗ്യതയുണ്ടോ എന്ന് ഔദ്യോഗിക വിജ്ഞാപനത്തിൽ ഉറപ്പാക്കുക.",
                "📊 <b>Dashboard:</b> https://akhilesdf6.github.io/akhil-govt-job-tracker/"
            ]
            send_telegram("\n".join(card))
    with open("seen_ids.json","w",encoding="utf-8") as f:
        json.dump(sorted(old|{j["id"] for j in jobs}),f)
    print(f"Checked {len(SOURCES)} official portals; collected {len(jobs)} possible notices; {len(new)} new; {len(errors)} source errors.")
    for e in errors: print("SOURCE ERROR:",e)

if __name__=="__main__":
    main()
