import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from . import settings
from .models import JobPost
from .cleaner import deduplicate_jobs
from .scorer import CandidateScorer
from .sources.jobspy_provider import JobSpyProvider
from .sources.jobs_ge_provider import JobsGeProvider
from .sources.ats_provider import AtsBoardsProvider
from .assessment import RepostTracker, assess, load_applied_text

logger = logging.getLogger(__name__)


class AggregatorEngine:
    """
    Unified multi-source search engine.
    Orchestrates scrapers, URL cleaning, deduplication, and candidate fit scoring.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(__file__).parent.parent
        self.feed_file = self.output_dir / "jobs_feed.json"
        self.seen_file = self.output_dir / "seen_jobs.json"
        # Our own records: anything listed here is marked "already applied" and gets verdict Skip.
        self.applied_files = [
            self.output_dir / "job-applications-report.md",
            self.output_dir.parent / "Linkedin Agent" / "linkedin-pipeline.md",
        ]
        self.last_save_success: bool = False

    def search(
        self,
        query: Optional[str] = None,
        location: str = "Remote",
        sources: Optional[List[str]] = None,
        results_per_source: int = 15,
        hours_old: int = 72,
        country_indeed: str = "USA",
        is_remote: bool = True,
        min_fit_score: int = 0,
        include_jobs_ge: bool = True,
        ats_max_age_days: int = 0,
        min_rating: float = 0.0,
        hide_skip: bool = False,
    ) -> List[JobPost]:
        """
        Executes search across all requested platforms, cleans, deduplicates,
        and scores results against the configured candidate profile.
        """
        all_jobs: List[JobPost] = []
        query = query or settings.section("role").get("default_query") or ""
        if sources is None:
            target_sources = [s for s in settings.section("search").get("sources") or []
                              if s != "jobs_ge" or include_jobs_ge]
        else:
            target_sources = list(sources)

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
                country_indeed=country_indeed,
                is_remote=is_remote,
            )
            all_jobs.extend(found_jobspy)

            print(f"  -> Found {len(found_jobspy)} raw listings from JobSpy sources.")

        # 2. Local Jobs.ge Search
        if "jobs_ge" in target_sources:
            print("🇬🇪 Searching on: JOBS.GE (local / regional tech vacancies)...")
            found_jobs_ge = JobsGeProvider.search(
                query=query,
                max_results=results_per_source,
                hours_old=hours_old,
                is_remote=is_remote,
            )
            all_jobs.extend(found_jobs_ge)
            print(f"  -> Found {len(found_jobs_ge)} raw listings from Jobs.ge.")

        # 2b. Company career boards via public ATS APIs (Greenhouse / Ashby / Lever)
        if "ats" in target_sources:
            print("🏢 Searching on: ATS BOARDS (Greenhouse / Ashby / Lever public APIs)...")
            found_ats = AtsBoardsProvider.search(query=query, max_age_days=ats_max_age_days, is_remote=is_remote)
            all_jobs.extend(found_ats)
            print(f"  -> Found {len(found_ats)} matching listings on company boards.")

        print(f"\n📊 Total raw listings before deduplication: {len(all_jobs)}")

        # 3. Clean & Deduplicate
        unique_jobs = deduplicate_jobs(all_jobs)
        print(f"✨ Listings after cleaning & deduplication: {len(unique_jobs)}")

        # 4. Score Candidate Fit
        scored_jobs = CandidateScorer.score_all(unique_jobs)

        # 4b. 1-5 rating, verdict and blocker / legitimacy flags (see assessment.py)
        applied_text = load_applied_text(self.applied_files)
        tracker = RepostTracker(self.seen_file)
        for j in scored_jobs:
            assess(j, applied_text=applied_text, repost_flag=tracker.check(j))
        tracker.save()
        scored_jobs.sort(key=lambda j: (j.verdict != "Skip", j.rating, j.fit_score), reverse=True)
        if hide_skip:
            scored_jobs = [j for j in scored_jobs if j.verdict != "Skip"]
        if min_rating > 0:
            scored_jobs = [j for j in scored_jobs if j.rating >= min_rating]

        # 5. Apply score threshold
        if min_fit_score > 0:
            scored_jobs = [j for j in scored_jobs if j.fit_score >= min_fit_score]
            print(f"🎯 Listings matching minimum fit score ({min_fit_score}%): {len(scored_jobs)}")

        # 6. Save Feed to JSON
        self.last_save_success = self.save_feed(scored_jobs)

        return scored_jobs

    def save_feed(self, jobs: List[JobPost]) -> bool:
        """Persists jobs to jobs_feed.json. Returns True on success, False otherwise."""
        try:
            data = [j.to_dict() for j in jobs]
            with open(self.feed_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Feed saved to: {self.feed_file.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save jobs feed: {e}")
            return False

    @staticmethod
    def format_markdown_table(jobs: List[JobPost]) -> str:
        """Renders formatted markdown report of jobs."""
        if not jobs:
            return "No matching jobs found."

        lines = [
            "| Verdict | Rating | Score | Job Title | Company | Location | Source | Salary | Flags | Apply Link |",
            "|:---|:---:|:---:|:---|:---|:---|:---:|:---|:---|:---:|"
        ]

        for j in jobs:
            title_clean = j.title.replace("|", "-")
            company_clean = j.company.replace("|", "-")
            link_str = f"[Apply ↗]({j.job_url})" if j.job_url else "N/A"
            flags = "; ".join(j.flags).replace("|", "/") or "—"
            location = (j.location or "").replace("|", "/")
            lines.append(
                f"| {j.verdict or j.fit_grade} | **{j.rating:.1f}** | {j.fit_score}% | {title_clean} | {company_clean} | {location} | {j.source.upper()} | {j.salary_str} | {flags} | {link_str} |"
            )

        return "\n".join(lines)
