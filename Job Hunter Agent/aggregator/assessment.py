"""Turns a keyword fit score into a 1-5 rating, a verdict and a list of flags.

Ideas borrowed from career-ops (https://github.com/career-ops-hq/career-ops): a 1-5 score
where below 4.0 means "probably not worth it", a single verdict per job, and "Block G"
legitimacy signals (stale postings, reposts, thin descriptions). Added here: work-authorization
and region-lock blockers (a remote job limited to residents of a country you cannot work in is
out of reach), on-site-abroad blockers, and a duplicate check against our own report.

Where you live and where you can work comes from config.yml (`location`, `candidate.timezone_window`);
thresholds come from `scoring`. Verdicts: Apply · Consider · Research first · Skip (low rating or a blocker).
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import settings as cfg
from .models import JobPost

NEVER = re.compile(r"(?!x)x")
VAGUE_SCOPES = {"worldwide", "anywhere", "global", "globally"}

RELOCATION_RE = re.compile(r"\b(relocation|relocate|visa sponsorship|sponsor (a |your )?visa)\b", re.I)
NO_SPONSOR_RE = re.compile(
    r"\b(no|not|unable to|cannot|can't|will not|won't|does not|do not)\s+(currently\s+)?(provide|offer|support)?\s*"
    r"(visa\s+)?sponsor(ship)?", re.I)
SPONSOR_OK_RE = re.compile(r"\b(visa sponsorship (is )?(available|provided|offered)|we (will )?sponsor"
                           r"|relocation (package|support|assistance))\b", re.I)
REMOTE_LOC_RE = re.compile(r"\b(remote|home[- ]based|work from home)\b", re.I)
# Government clearances only citizens of that country can hold.
CLEARANCE_RE = re.compile(r"(?<![\w])(ts/sci|top secret|security clearance|secret clearance|federal classified"
                          r"|sc clearance|dv clearance|nv1|nv2)(?![\w])", re.I)


def _alt(words: Iterable[str]) -> str:
    items = sorted({str(w).strip() for w in words or [] if str(w).strip()}, key=len, reverse=True)
    return "|".join(re.escape(w) for w in items) if items else "(?!x)x"


def _bounded(words: Iterable[str]) -> "re.Pattern[str]":
    return re.compile(rf"(?<![\w])({_alt(words)})(?![\w])", re.I)


_cache: Dict[str, object] = {}


def patterns() -> Dict[str, "re.Pattern[str]"]:
    """Regexes built from the active settings (rebuilt when the settings object changes)."""
    s = cfg.get()
    if _cache.get("key") is s:
        return _cache["p"]  # type: ignore[return-value]
    loc = s.get("location") or {}
    cand = s.get("candidate") or {}
    friendly = [str(w).lower() for w in loc.get("friendly_regions") or []]
    home = loc.get("home_places") or []
    locked = loc.get("locked_regions") or []
    check = loc.get("check_regions") or []
    lo, hi = (cand.get("timezone_window") or [0, 0])[:2]
    offsets = []
    for n in range(int(lo), int(hi) + 1):
        offsets.append(r"\+ ?%d" % n if n > 0 else r"- ?%d" % -n if n < 0 else r"[+-]? ?0")
    tz = rf"(?<![\w])(gmt|utc) ?({'|'.join(offsets)})(?!\d)" if offsets else "(?!x)x"
    text_regions = [w for w in friendly if w not in VAGUE_SCOPES]
    # In a description, bare region words are often marketing ("offices across Europe"), so only
    # home places, "EMEA"-style scopes and multi-word phrases ("european time zones") count bare.
    text_bare = list(home) + [w for w in text_regions if w == "emea" or " " in w]
    p = {
        "home": _bounded(home),
        "home_exclude": _bounded(loc.get("home_exclude") or []),
        "friendly_loc": re.compile(rf"(?<![\w])({_alt(friendly)})(?![\w])|{tz}", re.I),
        "friendly_text": re.compile(
            rf"\b(work from anywhere|anywhere in the world"
            rf"|remote[- ](first[- ])?(worldwide|globally|global|{_alt(text_regions)})"
            rf"|(hire|hiring|based|located|reside|living|work) (anywhere )?(in|from|across) ({_alt(text_regions)}|any country))\b"
            rf"|(?<![\w])({_alt(text_bare)})(?![\w])|{tz}", re.I),
        "locked": _bounded(locked),
        "check": _bounded(check),
        "work_auth": re.compile(
            r"(must|need to|required to|should)\s+(already\s+)?(be\s+|have\s+)?(legally\s+)?"
            r"(authori[sz]ed|eligible|the right|permission|a valid work permit)\s+(to\s+)?(work|reside)?\s*(in|within)\s+"
            rf"(the\s+)?({_alt(list(locked) + list(check))})(?![\w])", re.I),
        "residency": re.compile(
            r"\b(based|located|reside|residing|living)\s+(anywhere\s+)?in\s+(the\s+)?"
            rf"({_alt(locked)})(?![\w])", re.I),
    }
    _cache.update(key=s, p=p)
    return p


def is_home(text: str) -> bool:
    p = patterns()
    return bool(p["home"].search(text or "")) and not p["home_exclude"].search(text or "")


def friendly_location(loc: str) -> bool:
    return bool(patterns()["friendly_loc"].search(loc or "")) or is_home(loc)


def _parse_date(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def work_auth_flags(job: JobPost) -> List[str]:
    """Returns blocker flags ("BLOCK: ...") and warnings for location / work authorization."""
    p = patterns()
    flags: List[str] = []
    loc = job.location or ""
    desc = job.description or ""
    text = f"{loc}\n{desc}"
    friendly = friendly_location(loc) or bool(p["friendly_text"].search(desc))
    sponsor_ok = bool(SPONSOR_OK_RE.search(text))
    remote = job.is_remote or bool(REMOTE_LOC_RE.search(loc)) or bool(p["friendly_loc"].search(loc))
    # A generic location ("Remote", empty) leaves the description to decide on residency; a named
    # place that is not locked (e.g. "Remote (Kyiv, Ukraine)") wins over a stray mention.
    generic_loc = not re.sub(r"(?i)\b(remote|job|home[- ]based|anywhere|or)\b|[^a-z]", "", loc)

    m = p["work_auth"].search(text)
    c = CLEARANCE_RE.search(f"{job.title}\n{text}")
    if c:
        flags.append(f"BLOCK: security clearance required ('{c.group(0)}')")
    elif m and not sponsor_ok:
        flags.append(f"BLOCK: work authorization required ('{m.group(0)[:70]}')")
    elif p["locked"].search(loc) and not friendly_location(loc):
        flags.append(f"BLOCK: region-locked ('{loc[:60]}')")
    elif loc and not remote and not is_home(loc) and not RELOCATION_RE.search(text):
        flags.append(f"BLOCK: on-site/hybrid abroad, no relocation ('{loc[:50]}')")
    else:
        r = p["residency"].search(desc)
        if r and not friendly:
            if generic_loc:
                flags.append(f"BLOCK: residency required ('{r.group(0)[:60]}')")
            else:
                flags.append(f"check residency: description says '{r.group(0)[:50]}'")

    if not any(f.startswith("BLOCK") for f in flags):
        if NO_SPONSOR_RE.search(desc) and not sponsor_ok:
            flags.append("no visa sponsorship (fine for remote/contract, not for relocation)")
        if not remote and RELOCATION_RE.search(text) and not is_home(loc):
            relocate = (cfg.section("location").get("open_to_relocation", True))
            flags.append("on-site abroad; posting mentions relocation/sponsorship"
                         + ("" if relocate else " (you said no to relocation)"))
        if p["check"].search(loc) and not friendly_location(loc):
            flags.append(f"check right to work ('{loc[:50]}')")
    return flags


def legitimacy_flags(job: JobPost, now: Optional[datetime] = None) -> List[str]:
    """career-ops Block G style signals. They lower the rating; they never decide on their own."""
    now = now or datetime.now(timezone.utc)
    stale_days = int(cfg.section("scoring").get("stale_days", 30))
    flags: List[str] = []
    posted = _parse_date(job.date_posted)
    if posted and (now - posted).days > stale_days:
        flags.append(f"stale: posted {(now - posted).days} days ago")
    desc_len = len((job.description or "").strip())
    if 0 < desc_len < 400:
        flags.append("thin description")
    return flags


class RepostTracker:
    """Remembers company+title pairs between runs to spot postings that keep reappearing."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.seen = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError, json.JSONDecodeError):
            self.seen = {}

    def check(self, job: JobPost, now: Optional[datetime] = None) -> Optional[str]:
        now = now or datetime.now(timezone.utc)
        gap = int(cfg.section("scoring").get("repost_gap_days", 7))
        key = f"{_norm(job.company)}||{_norm(job.title)}"
        entry = self.seen.setdefault(key, {"first_seen": now.date().isoformat(), "urls": []})
        flag = None
        if job.job_url and job.job_url not in entry["urls"]:
            first = datetime.fromisoformat(entry["first_seen"]).replace(tzinfo=timezone.utc)
            if entry["urls"] and (now - first) >= timedelta(days=gap):
                flag = f"reposted (same title seen since {entry['first_seen']})"
            entry["urls"] = (entry["urls"] + [job.job_url])[-10:]
        return flag

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.seen, indent=1, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def load_applied_text(paths: Iterable[Path]) -> str:
    parts = []
    for p in paths:
        try:
            parts.append(p.read_text(encoding="utf-8"))
        except OSError:
            continue
    return "\n".join(parts).lower()


def already_applied(job: JobPost, applied_text: str) -> bool:
    """True when the report or pipeline already lists this job (by URL / job id, or company + title on one line)."""
    if not applied_text:
        return False
    url = (job.job_url or "").lower().split("?")[0].rstrip("/")
    if url and url in applied_text:
        return True
    ids = re.findall(r"(?:gh_jid=|/jobs/|/view/)(\d{6,})|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", job.job_url or "", re.I)
    for a, b in ids:
        if (a or b).lower() in applied_text:
            return True
    company, title = _norm(job.company), _norm(job.title)
    if len(company) < 3 or len(title) < 6:
        return False
    return any(company in _norm(line) and title in _norm(line) for line in applied_text.splitlines() if company[:4] in line)


def verdict_for(rating: float) -> str:
    v = cfg.section("scoring").get("verdicts") or {}
    if rating >= float(v.get("apply", 4.0)):
        return "Apply"
    if rating >= float(v.get("consider", 3.5)):
        return "Consider"
    if rating >= float(v.get("research", 2.5)):
        return "Research first"
    return "Skip"


def assess(job: JobPost, applied_text: str = "", repost_flag: Optional[str] = None,
           now: Optional[datetime] = None) -> JobPost:
    """Fills job.rating, job.verdict and job.flags. Expects job.fit_score to be set already."""
    rating = 1.0 + 4.0 * max(0, min(100, job.fit_score)) / 100.0
    flags = work_auth_flags(job) + legitimacy_flags(job, now)
    if repost_flag:
        flags.append(repost_flag)
    penalties = {"stale": 0.3, "reposted": 0.3, "thin description": 0.2}
    for f in flags:
        for prefix, cost in penalties.items():
            if f.startswith(prefix):
                rating -= cost

    blocked = any(f.startswith("BLOCK") for f in flags)
    if already_applied(job, applied_text):
        job.applied = True
        flags.insert(0, "already applied")
        blocked = True
    if blocked:
        rating = min(rating, 2.0)

    job.rating = round(max(1.0, min(5.0, rating)), 1)
    job.verdict = "Skip" if blocked else verdict_for(job.rating)
    job.flags = flags
    return job
