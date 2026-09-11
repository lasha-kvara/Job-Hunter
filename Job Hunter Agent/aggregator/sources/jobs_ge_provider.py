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
    def search(cls, query: str = "", max_results: int = 20, hours_old: Optional[int] = None) -> List[JobPost]:
        """
        Scrapes jobs.ge IT category (cid=6), parses posting dates, and filters by query and age.
        """
        jobs: List[JobPost] = []
        try:
            from datetime import datetime, timedelta

            # IT & Software category
            url = f"{cls.BASE_URL}/en/?cid=6"
            resp = requests.get(
                url,
                headers=cls.HEADERS,
                timeout=12,
                verify=True
            )
            if resp.status_code != 200:
                logger.warning(f"Jobs.ge returned non-200 status: {resp.status_code}")
                return jobs

            soup = BeautifulSoup(resp.text, "html.parser")
            query_tokens = [q.lower() for q in query.split() if len(q) > 1]
            now = datetime.now()

            # Find all table rows
            rows = soup.find_all("tr")

            for row in rows:
                if len(jobs) >= max_results:
                    break

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

                # Filter by hours_old if requested
                if hours_old is not None and pub_date_str:
                    try:
                        dt = datetime.strptime(f"{pub_date_str} {now.year}", "%d %B %Y")
                        if dt > now + timedelta(days=2):
                            dt = dt.replace(year=now.year - 1)
                        age_hours = (now - dt).total_seconds() / 3600
                        if age_hours > hours_old:
                            continue
                    except Exception:
                        pass

                # Look for company link: /en/?view=client&client=...
                company_link = row.find("a", href=lambda h: h and "view=client" in h)
                company = company_link.text.strip() if company_link and company_link.text.strip() else "Jobs.ge Employer"

                # If query specified, check for match in title
                if query_tokens:
                    title_lower = title.lower()
                    matched = any(token in title_lower for token in query_tokens)
                    if not matched:
                        continue

                # Check remote tag in entire row text (title + tags + metadata)
                row_text = row.get_text(" ", strip=True)
                is_remote = bool(re.search(r'\bremote\b', row_text, re.IGNORECASE))

                post = JobPost(
                    title=title,
                    company=company,
                    job_url=job_url,
                    source="jobs_ge",
                    location="Georgia (Tbilisi / Remote)" if is_remote else "Georgia (Tbilisi)",
                    date_posted=pub_date_str,
                    is_remote=is_remote,
                    description=f"{title} vacancy at {company} listed on Jobs.ge IT section."
                )
                jobs.append(post)


        except Exception as e:
            logger.warning(f"Jobs.ge search failed: {e}")

        return jobs

