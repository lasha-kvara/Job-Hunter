import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from ..models import JobPost

logger = logging.getLogger(__name__)

# Use native system certificate store (Windows/macOS) for secure TLS verification
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass


class JobsGeProvider:
    """
    Scrapes IT, Software Engineering and QA vacancies directly from jobs.ge.
    """

    BASE_URL = "https://jobs.ge"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9,ka;q=0.8",
    }

    @classmethod
    def _fetch_description(cls, job_url: str, session: requests.Session) -> str:
        """Fetches the announcement body from the listing page for richer scoring context."""
        try:
            resp = session.get(job_url, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                dtable = soup.find(class_="dtable")
                if dtable:
                    return dtable.get_text(" ", strip=True)
        except Exception:
            pass
        return ""

    @classmethod
    def search(
        cls,
        query: str = "",
        max_results: int = 20,
        hours_old: Optional[int] = None,
        is_remote: bool = False,
    ) -> List[JobPost]:
        """
        Scrapes jobs.ge IT category (cid=6), parses posting dates, filters by query and age,
        and concurrently enriches listings with full announcement descriptions.
        """
        jobs: List[JobPost] = []
        try:
            from datetime import datetime, timedelta
            from concurrent.futures import ThreadPoolExecutor

            # IT & Software category
            url = f"{cls.BASE_URL}/en/?cid=6"
            session = requests.Session()
            session.headers.update(cls.HEADERS)

            resp = session.get(
                url,
                timeout=12,
            )
            if resp.status_code != 200:
                logger.warning(f"Jobs.ge returned non-200 status: {resp.status_code}")
                return jobs

            soup = BeautifulSoup(resp.text, "html.parser")
            query_tokens = [q.lower() for q in query.split() if len(q) > 1]
            now = datetime.now()

            # Find all table rows
            rows = soup.find_all("tr")
            matching_candidates = []
            secondary_candidates = []

            for row in rows:
                # Look for job link: /en/?view=jobs&id=...
                job_link = row.find("a", href=lambda h: h and "view=jobs&id=" in h)
                if not job_link:
                    continue

                title = job_link.text.strip()
                if not title:
                    continue

                href = job_link.get("href", "")
                if href.startswith("/"):
                    job_url = f"{cls.BASE_URL}{href}"
                else:
                    job_url = f"{cls.BASE_URL}/{href}"

                # Extract date from cells (typically column -2 is published date, e.g. "11 September")
                tds = row.find_all("td")
                pub_date_str = ""
                if len(tds) >= 5:
                    pub_date_str = tds[-2].text.strip()

                # Filter by hours_old if requested (strict date parsing)
                if hours_old is not None:
                    if not pub_date_str:
                        continue
                    parsed_dt = None
                    for fmt in ["%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%Y-%m-%d"]:
                        try:
                            date_to_parse = f"{pub_date_str} {now.year}" if len(pub_date_str.split()) == 2 and "%Y" in fmt else pub_date_str
                            parsed_dt = datetime.strptime(date_to_parse, fmt)
                            break
                        except Exception:
                            pass
                    if parsed_dt is None:
                        # Skip undated or unrecognized date formats when time filter is requested
                        continue
                    if parsed_dt > now + timedelta(days=2):
                        parsed_dt = parsed_dt.replace(year=now.year - 1)
                    age_hours = (now - parsed_dt).total_seconds() / 3600
                    if age_hours > hours_old:
                        continue

                # Check remote tag in entire row text (title + tags + metadata)
                row_text = row.get_text(" ", strip=True)
                has_remote = bool(re.search(r'\bremote\b', row_text, re.IGNORECASE))
                if is_remote and not has_remote:
                    continue

                # Look for company link: /en/?view=client&client=...
                company_link = row.find("a", href=lambda h: h and "view=client" in h)
                company = company_link.text.strip() if company_link and company_link.text.strip() else "Jobs.ge Employer"

                # Check if title directly matches query
                title_lower = title.lower()
                title_matched = not query_tokens or (query.lower() in title_lower) or all(token in title_lower for token in query_tokens)

                cand = {
                    "title": title,
                    "company": company,
                    "job_url": job_url,
                    "pub_date_str": pub_date_str,
                    "has_remote": has_remote,
                    "title_matched": title_matched,
                }

                if title_matched:
                    matching_candidates.append(cand)
                    if len(matching_candidates) >= max_results:
                        break
                else:
                    # Collect a bounded set of non-title matches to check their full announcement text
                    if len(secondary_candidates) < max_results:
                        secondary_candidates.append(cand)

            candidates_to_enrich = (matching_candidates + secondary_candidates)[:max_results * 2]
            if not candidates_to_enrich:
                return []

            # Concurrently enrich candidate descriptions using thread-safe worker sessions
            def enrich(cand):
                with requests.Session() as worker_session:
                    worker_session.headers.update(cls.HEADERS)
                    desc = cls._fetch_description(cand["job_url"], worker_session)
                if not desc:
                    desc = f"{cand['title']} vacancy at {cand['company']} listed on Jobs.ge IT section."
                return cand, desc

            with ThreadPoolExecutor(max_workers=5) as executor:
                enriched_results = list(executor.map(enrich, candidates_to_enrich))

            for cand, desc in enriched_results:
                if len(jobs) >= max_results:
                    break

                # Query matching: check title OR fetched description
                if query_tokens and not cand["title_matched"]:
                    full_text = f"{cand['title']} {desc}".lower()
                    matched = (query.lower() in full_text) or all(token in full_text for token in query_tokens)
                    if not matched:
                        continue

                post = JobPost(
                    title=cand["title"],
                    company=cand["company"],
                    job_url=cand["job_url"],
                    source="jobs_ge",
                    location="Georgia (Tbilisi / Remote)" if cand["has_remote"] else "Georgia (Tbilisi)",
                    date_posted=cand["pub_date_str"],
                    is_remote=cand["has_remote"],
                    description=desc
                )
                jobs.append(post)

        except Exception as e:
            logger.warning(f"Jobs.ge search failed: {e}")

        return jobs

