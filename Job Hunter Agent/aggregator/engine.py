import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import JobPost
from .cleaner import deduplicate_jobs
from .scorer import CandidateScorer
from .sources.jobspy_provider import JobSpyProvider
from .sources.jobs_ge_provider import JobsGeProvider

logger = logging.getLogger(__name__)


class AggregatorEngine:
    """
    Unified multi-source search engine.
    Orchestrates scrapers, URL cleaning, deduplication, and candidate fit scoring.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(__file__).parent.parent
        self.feed_file = self.output_dir / "jobs_feed.json"

    def search(
        self,
        query: str = "QA Automation Engineer",
        location: str = "Remote",
        sources: Optional[List[str]] = None,
        results_per_source: int = 15,
        hours_old: int = 72,
        is_remote: bool = True,
        min_fit_score: int = 0,
        include_jobs_ge: bool = True,
    ) -> List[JobPost]:
        """
        Executes search across all requested platforms, cleans, deduplicates,
        and scores results against the SDET candidate profile.
        """
        all_jobs: List[JobPost] = []
        target_sources = sources or ["indeed", "linkedin", "google", "glassdoor", "zip_recruiter"]

        # 1. JobSpy Multi-Platform Scraping
        jobspy_sources = [s for s in target_sources if s in JobSpyProvider.SUPPORTED_SITES]
        if jobspy_sources:
            print(f"🔍 Searching on: {', '.join(jobspy_sources).upper()} (query: '{query}', location: '{location}')...")
            found_jobspy = JobSpyProvider.search(
                search_term=query,
                location=location,
                sites=jobspy_sources,
                results_wanted=results_per_source,
                hours_old=hours_old,
                is_remote=is_remote,
            )
            all_jobs.extend(found_jobspy)
            print(f"  -> Found {len(found_jobspy)} raw listings from JobSpy sources.")

        # 2. Local Jobs.ge Search
        if include_jobs_ge or "jobs_ge" in target_sources:
            print("🇬🇪 Searching on: JOBS.GE (local / regional tech vacancies)...")
            found_jobs_ge = JobsGeProvider.search(query=query, max_results=results_per_source)
            if is_remote:
                found_jobs_ge = [job for job in found_jobs_ge if job.is_remote]
            all_jobs.extend(found_jobs_ge)
            print(f"  -> Found {len(found_jobs_ge)} raw listings from Jobs.ge.")


        print(f"\n📊 Total raw listings before deduplication: {len(all_jobs)}")

        # 3. Clean & Deduplicate
        unique_jobs = deduplicate_jobs(all_jobs)
        print(f"✨ Listings after cleaning & deduplication: {len(unique_jobs)}")

        # 4. Score Candidate Fit
        scored_jobs = CandidateScorer.score_all(unique_jobs)

        # 5. Apply score threshold
        if min_fit_score > 0:
            scored_jobs = [j for j in scored_jobs if j.fit_score >= min_fit_score]
            print(f"🎯 Listings matching minimum fit score ({min_fit_score}%): {len(scored_jobs)}")

        # 6. Save Feed to JSON
        self.save_feed(scored_jobs)

        return scored_jobs

    def save_feed(self, jobs: List[JobPost]) -> None:
        """Persists jobs to jobs_feed.json."""
        try:
            data = [j.to_dict() for j in jobs]
            with open(self.feed_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Feed saved to: {self.feed_file.name}")
        except Exception as e:
            logger.error(f"Failed to save jobs feed: {e}")

    @staticmethod
    def format_markdown_table(jobs: List[JobPost]) -> str:
        """Renders formatted markdown report of jobs."""
        if not jobs:
            return "No matching jobs found."

        lines = [
            "| Fit | Score | Job Title | Company | Location | Source | Salary | Apply Link |",
            "|:---:|:---:|:---|:---|:---|:---:|:---|:---:|"
        ]

        for j in jobs:
            title_clean = j.title.replace("|", "-")
            company_clean = j.company.replace("|", "-")
            link_str = f"[Apply ↗]({j.job_url})" if j.job_url else "N/A"
            lines.append(
                f"| {j.fit_grade} | **{j.fit_score}%** | {title_clean} | {company_clean} | {j.location} | {j.source.upper()} | {j.salary_str} | {link_str} |"
            )

        return "\n".join(lines)
