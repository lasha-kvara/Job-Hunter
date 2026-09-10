import logging
from typing import List, Optional
from ..models import JobPost

logger = logging.getLogger(__name__)


class JobSpyProvider:
    """
    Multi-platform job scraper using python-jobspy.
    Supports: LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs.
    """

    SUPPORTED_SITES = ["indeed", "linkedin", "glassdoor", "zip_recruiter", "google"]

    @classmethod
    def search(
        cls,
        search_term: str,
        location: str = "Remote",
        sites: Optional[List[str]] = None,
        results_wanted: int = 15,
        hours_old: int = 72,
        country_indeed: str = "USA",
        is_remote: bool = True,
    ) -> List[JobPost]:
        """Runs multi-site search via jobspy."""
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy is not installed. Run: pip install python-jobspy")
            return []

        active_sites = [s for s in (sites or cls.SUPPORTED_SITES) if s in cls.SUPPORTED_SITES]
        if not active_sites:
            active_sites = ["indeed", "google"]

        posts: List[JobPost] = []

        try:
            df = scrape_jobs(
                site_name=active_sites,
                search_term=search_term,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed=country_indeed,
                is_remote=is_remote,
            )

            if df is None or df.empty:
                return []

            # Convert dataframe rows to JobPost objects
            for _, row in df.iterrows():
                try:
                    title = str(row.get("title", "") or "").strip()
                    company = str(row.get("company", "") or "").strip()
                    job_url = str(row.get("job_url", "") or "").strip()
                    source = str(row.get("site", "") or "jobspy").lower()

                    if not title or not job_url:
                        continue

                    # Parse numbers safely
                    salary_min = None
                    if "min_amount" in row and row["min_amount"] is not None:
                        try:
                            val = float(row["min_amount"])
                            if val > 0:
                                salary_min = val
                        except (ValueError, TypeError):
                            pass

                    salary_max = None
                    if "max_amount" in row and row["max_amount"] is not None:
                        try:
                            val = float(row["max_amount"])
                            if val > 0:
                                salary_max = val
                        except (ValueError, TypeError):
                            pass

                    job_post = JobPost(
                        title=title,
                        company=company,
                        job_url=job_url,
                        source=source,
                        location=str(row.get("location", "") or location),
                        date_posted=str(row.get("date_posted", "") or ""),
                        salary_min=salary_min,
                        salary_max=salary_max,
                        salary_currency=str(row.get("currency", "USD") or "USD"),
                        salary_period=str(row.get("interval", "yearly") or "yearly"),
                        job_type=str(row.get("job_type", "") or ""),
                        is_remote=bool(row.get("is_remote", is_remote)),
                        description=str(row.get("description", "") or "")[:2000],  # keep preview
                    )
                    posts.append(job_post)
                except Exception as row_err:
                    logger.debug(f"Error parsing job row: {row_err}")
                    continue

        except Exception as e:
            logger.warning(f"JobSpy scrape encountered an issue: {e}")

        return posts
