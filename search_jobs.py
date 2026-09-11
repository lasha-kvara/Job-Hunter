#!/usr/bin/env python3
"""
Job-Hunter: Multi-Source Vacancy Aggregator CLI
Searches across LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, and Jobs.ge.
Cleans URLs, removes duplicates, and scores fit against SDET / QA Automation criteria.
"""

import sys
import io
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root and Job Hunter Agent to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Job Hunter Agent"))

from aggregator.engine import AggregatorEngine


def main():
    parser = argparse.ArgumentParser(
        description="Job-Hunter: Search vacancies across multiple platforms with automated fit scoring."
    )
    parser.add_argument(
        "--query", "-q",
        default="QA Automation Engineer",
        help="Job title or search keywords (e.g. 'SDET', 'Senior QA Automation', 'Playwright')"
    )
    parser.add_argument(
        "--location", "-l",
        type=str,
        default=None,
        help="Target location (default: 'Remote' if --remote, or all locations if --no-remote)"
    )
    parser.add_argument(
        "--country",
        type=str,
        default="USA",
        help="Country for Indeed search (default: 'USA')"
    )
    parser.add_argument(
        "--sources", "-s",
        nargs="+",
        default=["indeed", "linkedin", "google", "glassdoor", "zip_recruiter", "jobs_ge"],
        help="Platforms to search: indeed, linkedin, google, glassdoor, zip_recruiter, jobs_ge"
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=10,
        help="Maximum raw results wanted per platform (default: 10)"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=72,
        help="Only search postings from the last N hours (default: 72)"
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=0,
        help="Filter out jobs with fit score below this threshold (0-100)"
    )
    parser.add_argument(
        "--remote",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Filter for remote-only positions (use --no-remote to include on-site)"
    )
    parser.add_argument(
        "--export-md",
        type=str,
        default="search_results.md",
        help="File path to save Markdown summary table (default: 'search_results.md')"
    )

    args = parser.parse_args()

    # Determine location: if not specified, use "Remote" for remote searches or "" for on-site
    resolved_location = args.location if args.location is not None else ("Remote" if args.remote else "")

    print("=" * 65)
    print("🚀 JOB-HUNTER: MULTI-SOURCE JOB AGGREGATOR")
    print("=" * 65)
    print(f"📌 Query:        {args.query}")
    print(f"📍 Location:     {resolved_location or 'All / Any'}")
    print(f"🌐 Sources:      {', '.join(args.sources)}")
    print(f"⏱️  Max Age:      {args.hours} hours")
    print(f"🎯 Min Score:    {args.min_score}%")
    print(f"🏠 Remote Only:  {args.remote}")
    print("=" * 65 + "\n")

    engine = AggregatorEngine(output_dir=PROJECT_ROOT / "Job Hunter Agent")
    jobs = engine.search(
        query=args.query,
        location=resolved_location,
        sources=args.sources,
        results_per_source=args.limit,
        hours_old=args.hours,
        country_indeed=args.country,
        is_remote=args.remote,
        min_fit_score=args.min_score,
        include_jobs_ge="jobs_ge" in args.sources
    )



    if not jobs:
        print("\n❌ No jobs found matching the criteria.")
        return

    print("\n" + "=" * 65)
    print(f"🎯 TOP MATCHING VACANCIES (Found {len(jobs)} unique jobs)")
    print("=" * 65)

    for idx, j in enumerate(jobs[:15], 1):
        print(f"\n[{idx}] {j.fit_grade} ({j.fit_score}%) — {j.title}")
        print(f"    🏢 Company:  {j.company}")
        print(f"    📍 Location: {j.location} | Source: {j.source.upper()}")
        print(f"    💰 Salary:   {j.salary_str}")
        if j.fit_reasons:
            print(f"    💡 Highlights: {'; '.join(j.fit_reasons[:3])}")
        print(f"    🔗 URL:      {j.job_url}")

    # Export to markdown table
    md_content = engine.format_markdown_table(jobs)
    md_path = PROJECT_ROOT / args.export_md
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Vacancy Search Results: {args.query}\n\n")
        f.write(f"*Location: {resolved_location or 'All / Any'} | Found: {len(jobs)} jobs*\n\n")
        f.write(md_content)

    print("\n" + "=" * 65)
    print(f"✅ Full report exported to: {md_path.name}")
    print(f"✅ Raw feed saved to:       Job Hunter Agent/jobs_feed.json")
    print("=" * 65)


if __name__ == "__main__":
    main()
