"""Company career boards read straight from public ATS APIs
(Greenhouse, Ashby, Lever, SmartRecruiters, Recruitee).

These endpoints need no login, no browser and no CAPTCHA, so a scan of many companies takes
seconds and returns the full posting text. The list of boards lives in
`Job Hunter Agent/ats-boards.json` (tracked, generic companies) plus an optional
`ats-boards.local.json` next to it (git-ignored, personal additions). Both have the shape
{"greenhouse": [...], "ashby": [...], "lever": [...], "lever_eu": [...], "smartrecruiters": [...],
"recruitee": [...]}.
"""
import html
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

from .. import settings
from ..models import JobPost

logger = logging.getLogger(__name__)

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

BOARDS_DIR = Path(__file__).resolve().parent.parent.parent
KINDS = ("greenhouse", "ashby", "lever", "lever_eu", "smartrecruiters", "recruitee")

# Which titles count is set in config.yml: role.title_keywords (one must appear) and
# role.title_exclude (none may appear). Query words are added to the keywords, except words too
# generic to mean a role on their own ("automation" alone hits RevOps / GTM / IT automation roles).
GENERIC_WORDS = {"engineer", "engineering", "senior", "sr", "lead", "staff", "principal", "remote", "and", "the",
                 "for", "automation", "automated", "software", "developer"}
REMOTE_RE = re.compile(r"\b(remote|anywhere|distributed|work from home)\b", re.I)


def _strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t\xa0]+", " ", text).strip()


def _title_matcher(query: str):
    role = settings.section("role")
    words = [w for w in re.findall(r"[a-z0-9#+.]+", (query or "").lower()) if len(w) > 2 and w not in GENERIC_WORDS]
    wanted = settings.words_regex(list(role.get("title_keywords") or []) + words)
    noise = settings.words_regex(role.get("title_exclude") or [])
    if wanted is None:
        raise ValueError("config.yml: role.title_keywords is empty and the query has no specific words")
    return lambda title: bool(wanted.search(title or "")) and not (noise and noise.search(title or ""))


def _parse_date(value) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):  # Lever: epoch milliseconds
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, OSError):
        return None


class AtsBoardsProvider:
    """Scans configured Greenhouse / Ashby / Lever boards for QA / SDET roles."""

    TIMEOUT = 20

    @classmethod
    def load_boards(cls, boards_dir: Optional[Path] = None) -> Dict[str, List[str]]:
        boards_dir = boards_dir or BOARDS_DIR
        merged: Dict[str, List[str]] = {k: [] for k in KINDS}
        for name in ("ats-boards.json", "ats-boards.local.json"):
            path = boards_dir / name
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Could not read {path.name}: {e}")
                continue
            for kind in KINDS:
                for token in data.get(kind, []):
                    if token not in merged[kind]:
                        merged[kind].append(token)
        return merged

    # ---- per-ATS fetchers: return a list of JobPost for one board -----------------------------

    @classmethod
    def _greenhouse(cls, session, token: str, wanted) -> List[JobPost]:
        base = f"https://boards-api.greenhouse.io/v1/boards/{token}"
        r = session.get(f"{base}/jobs", timeout=cls.TIMEOUT)
        if not r.ok:
            return []
        posts = []
        for j in r.json().get("jobs", []):
            if not wanted(j.get("title")):
                continue
            # The list call without content is light; fetch the body only for matching titles.
            desc = ""
            d = session.get(f"{base}/jobs/{j['id']}", timeout=cls.TIMEOUT)
            if d.ok:
                desc = _strip_html(d.json().get("content", ""))
            loc = (j.get("location") or {}).get("name", "")
            company = (d.json().get("company_name") if d.ok else None) or token
            posts.append(JobPost(
                title=j.get("title", ""), company=company, job_url=j.get("absolute_url", ""),
                source="greenhouse", location=loc,
                date_posted=j.get("first_published") or j.get("updated_at"),
                is_remote=bool(REMOTE_RE.search(loc)), description=desc[:6000],
            ))
        return posts

    @classmethod
    def _ashby(cls, session, token: str, wanted) -> List[JobPost]:
        r = session.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true",
                        timeout=cls.TIMEOUT)
        if not r.ok:
            return []
        posts = []
        for j in r.json().get("jobs", []):
            if not wanted(j.get("title")) or j.get("isListed") is False:
                continue
            loc = j.get("location", "")
            extra = [a.get("location", "") for a in j.get("secondaryLocations", []) or []]
            if extra:
                loc = "; ".join([loc] + extra)
            comp = (j.get("compensation") or {}).get("compensationTierSummary") or ""
            desc = (j.get("descriptionPlain") or _strip_html(j.get("descriptionHtml", "")))
            if comp:
                desc = f"Compensation: {comp}\n{desc}"
            posts.append(JobPost(
                title=j.get("title", ""), company=token, job_url=j.get("jobUrl", ""), source="ashby",
                location=loc, date_posted=j.get("publishedAt"),
                job_type=j.get("employmentType"),
                is_remote=bool(j.get("isRemote")) or str(j.get("workplaceType", "")).lower() == "remote",
                description=desc[:6000],
            ))
        return posts

    @classmethod
    def _lever(cls, session, token: str, wanted, eu: bool = False) -> List[JobPost]:
        host = "api.eu.lever.co" if eu else "api.lever.co"
        r = session.get(f"https://{host}/v0/postings/{token}?mode=json", timeout=cls.TIMEOUT)
        if not r.ok:
            return []
        posts = []
        for j in r.json():
            if not wanted(j.get("text")):
                continue
            cats = j.get("categories") or {}
            loc = cats.get("location") or "; ".join(cats.get("allLocations") or [])
            lists = "\n".join(f"{x.get('text', '')}: {_strip_html(x.get('content', ''))}" for x in j.get("lists") or [])
            desc = f"{j.get('descriptionPlain', '')}\n{lists}\n{j.get('additionalPlain', '')}"
            posts.append(JobPost(
                title=j.get("text", ""), company=token, job_url=j.get("hostedUrl", ""), source="lever",
                location=loc, date_posted=_parse_date(j.get("createdAt")).isoformat() if j.get("createdAt") else None,
                job_type=cats.get("commitment"),
                is_remote=str(j.get("workplaceType", "")).lower() == "remote" or bool(REMOTE_RE.search(loc)),
                description=desc[:6000],
            ))
        return posts

    @classmethod
    def _smartrecruiters(cls, session, token: str, wanted) -> List[JobPost]:
        base = f"https://api.smartrecruiters.com/v1/companies/{token}/postings"
        posts, offset = [], 0
        while offset < 1000:
            r = session.get(f"{base}?limit=100&offset={offset}", timeout=cls.TIMEOUT)
            if not r.ok:
                break
            data = r.json()
            for j in data.get("content", []):
                if not wanted(j.get("name")):
                    continue
                loc_info = j.get("location") or {}
                loc = loc_info.get("fullLocation") or ", ".join(x for x in (loc_info.get("city"), loc_info.get("country")) if x)
                loc = re.sub(r"(,\s*)+", ", ", loc).strip(", ")
                if loc_info.get("remote"):
                    loc = f"Remote ({loc})" if loc else "Remote"
                desc, url = "", f"https://jobs.smartrecruiters.com/{token}/{j.get('id')}"
                d = session.get(f"{base}/{j.get('id')}", timeout=cls.TIMEOUT)
                if d.ok:
                    body = d.json()
                    url = body.get("postingUrl") or url
                    sections = (body.get("jobAd") or {}).get("sections") or {}
                    desc = "\n".join(_strip_html((sections.get(k) or {}).get("text", ""))
                                     for k in ("jobDescription", "qualifications", "additionalInformation"))
                posts.append(JobPost(
                    title=j.get("name", ""), company=(j.get("company") or {}).get("name") or token, job_url=url,
                    source="smartrecruiters", location=loc, date_posted=j.get("releasedDate"),
                    job_type=(j.get("typeOfEmployment") or {}).get("label"),
                    is_remote=bool(loc_info.get("remote")), description=desc[:6000],
                ))
            offset += 100
            if offset >= data.get("totalFound", 0):
                break
        return posts

    @classmethod
    def _recruitee(cls, session, token: str, wanted) -> List[JobPost]:
        r = session.get(f"https://{token}.recruitee.com/api/offers/", timeout=cls.TIMEOUT)
        if not r.ok:
            return []
        posts = []
        for j in r.json().get("offers", []):
            if not wanted(j.get("title")):
                continue
            remote = bool(j.get("remote"))
            # For remote offers city/country is often just the HQ, so keep the offer's own label only.
            loc = j.get("location") or ""
            if not remote:
                loc = ", ".join(x for x in (j.get("city"), j.get("country")) if x) or loc
            desc = f"{_strip_html(j.get('description', ''))}\n{_strip_html(j.get('requirements', ''))}"
            posts.append(JobPost(
                title=j.get("title", ""), company=j.get("company_name") or token, job_url=j.get("careers_url", ""),
                source="recruitee", location=loc,
                date_posted=str(j.get("published_at") or "").replace(" UTC", "+00:00").replace(" ", "T", 1) or None,
                job_type=j.get("employment_type_code"), is_remote=remote, description=desc[:6000],
            ))
        return posts

    # ---- public entry point -------------------------------------------------------------------

    @classmethod
    def search(
        cls,
        query: str = "",
        max_age_days: int = 0,  # 0 = no cutoff: these APIs list only open jobs; age becomes a "stale" flag
        is_remote: bool = True,
        boards: Optional[Dict[str, List[str]]] = None,
        workers: int = 12,
    ) -> List[JobPost]:
        boards = boards if boards is not None else cls.load_boards()
        wanted = _title_matcher(query)
        session = requests.Session()
        session.headers.update({"User-Agent": "job-hunter-aggregator/1.0", "Accept": "application/json"})

        tasks = []
        for kind in KINDS:
            for token in boards.get(kind, []):
                if kind == "greenhouse":
                    tasks.append((token, lambda t=token: cls._greenhouse(session, t, wanted)))
                elif kind == "ashby":
                    tasks.append((token, lambda t=token: cls._ashby(session, t, wanted)))
                elif kind == "smartrecruiters":
                    tasks.append((token, lambda t=token: cls._smartrecruiters(session, t, wanted)))
                elif kind == "recruitee":
                    tasks.append((token, lambda t=token: cls._recruitee(session, t, wanted)))
                else:
                    tasks.append((token, lambda t=token, eu=(kind == "lever_eu"): cls._lever(session, t, wanted, eu)))

        posts: List[JobPost] = []
        failed: List[str] = []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(fn): token for token, fn in tasks}
            for fut, token in futures.items():
                try:
                    posts.extend(fut.result())
                except Exception as e:  # one dead board must not stop the scan
                    failed.append(token)
                    logger.debug(f"ATS board {token} failed: {e}")
        if failed:
            print(f"  -> ATS boards that did not answer: {', '.join(failed)}")

        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days) if max_age_days else None
        result = []
        for p in posts:
            posted = _parse_date(p.date_posted)
            if cutoff and posted and posted < cutoff:
                continue
            if is_remote and not p.is_remote and not REMOTE_RE.search(p.description[:1500]):
                continue
            result.append(p)
        return result
