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

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    HAS_RICH = True
    console = Console(legacy_windows=False)
except ImportError:
    HAS_RICH = False
    console = None


def validate_min_score(val: str) -> int:
    try:
        score = int(val)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid integer: '{val}'")
    if not (0 <= score <= 100):
        raise argparse.ArgumentTypeError(f"--min-score must be between 0 and 100, got {score}")
    return score


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
        choices=["indeed", "linkedin", "google", "glassdoor", "zip_recruiter", "jobs_ge"],
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
        type=validate_min_score,
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

    if HAS_RICH:
        from rich.markup import escape
        banner_body = (
            f"[bold cyan]📌 Query:[/bold cyan]        [bold white]{escape(str(args.query))}[/bold white]\n"
            f"[bold cyan]📍 Location:[/bold cyan]     [white]{escape(str(resolved_location or 'All / Any'))}[/white]\n"
            f"[bold cyan]🌐 Sources:[/bold cyan]      [yellow]{escape(', '.join(args.sources))}[/yellow]\n"
            f"[bold cyan]⏱️  Max Age:[/bold cyan]      {args.hours} hours  |  "
            f"[bold cyan]🎯 Min Score:[/bold cyan] {args.min_score}%  |  "
            f"[bold cyan]🏠 Remote Only:[/bold cyan] {args.remote}"
        )
        console.print(Panel(banner_body, title="[bold cyan]🚀 JOB-HUNTER: MULTI-SOURCE JOB AGGREGATOR[/bold cyan]", box=box.ROUNDED, expand=False))
    else:
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
        if HAS_RICH:
            console.print("\n[bold red]❌ No jobs found matching the criteria.[/bold red]")
        else:
            print("\n❌ No jobs found matching the criteria.")
    else:
        if HAS_RICH:
            from rich.markup import escape
            table = Table(title=f"🎯 TOP MATCHING VACANCIES (Found {len(jobs)} unique jobs)", box=box.ROUNDED)
            table.add_column("#", style="dim", justify="right", no_wrap=True)
            table.add_column("Fit Rating", justify="center", no_wrap=True)
            table.add_column("Job Title", style="bold white")
            table.add_column("Company", style="cyan")
            table.add_column("Location", style="yellow")
            table.add_column("Salary", style="green")
            table.add_column("Source", style="blue")
            table.add_column("URL", style="dim")

            for idx, j in enumerate(jobs[:15], 1):
                if j.fit_score >= 80:
                    score_markup = f"[bold green]{j.fit_score}% {escape(j.fit_grade)}[/bold green]"
                elif j.fit_score >= 60:
                    score_markup = f"[bold yellow]{j.fit_score}% {escape(j.fit_grade)}[/bold yellow]"
                else:
                    score_markup = f"[dim]{j.fit_score}% {escape(j.fit_grade)}[/dim]"

                # Show title and highlights together so matching reasons are preserved
                title_markup = escape(j.title)
                if j.fit_reasons:
                    highlights = escape("; ".join(j.fit_reasons[:2]))
                    title_markup += f"\n[dim italic]💡 {highlights}[/dim italic]"

                loc_str = j.location or ("Remote" if j.is_remote else "Not specified")
                salary_display = escape(j.salary_str) if j.salary_str else "[dim]—[/dim]"

                # Clickable hyperlink retaining full target URL
                display_url = j.job_url if len(j.job_url) <= 35 else j.job_url[:32] + "..."
                url_markup = f"[link={escape(j.job_url)}][underline]{escape(display_url)}[/underline][/link]"

                table.add_row(
                    str(idx),
                    score_markup,
                    title_markup,
                    escape(j.company),
                    escape(loc_str),
                    salary_display,
                    escape(j.source.upper()),
                    url_markup
                )
            console.print("\n", table)
        else:
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

    # Export to markdown table (always written so zero-result searches update stale reports)
    md_content = engine.format_markdown_table(jobs)
    md_path = PROJECT_ROOT / args.export_md
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Vacancy Search Results: {args.query}\n\n")
            f.write(f"*Location: {resolved_location or 'All / Any'} | Found: {len(jobs)} jobs*\n\n")
            f.write(md_content)
        if HAS_RICH:
            from rich.markup import escape
            summary_text = f"[green]✔ Full report exported to:[/green] [bold white]{escape(md_path.name)}[/bold white]\n"
            if getattr(engine, "last_save_success", False):
                summary_text += "[green]✔ Raw feed saved to:[/green]       [bold white]Job Hunter Agent/jobs_feed.json[/bold white]"
            else:
                summary_text += "[bold yellow]⚠️ Note: Raw feed was not saved for this run.[/bold yellow]"
            console.print("\n", Panel(summary_text, title="[bold green]Export Complete[/bold green]", box=box.ROUNDED, expand=False))
        else:
            print("\n" + "=" * 65)
            print(f"✅ Full report exported to: {md_path.name}")
            if getattr(engine, "last_save_success", False):
                print(f"✅ Raw feed saved to:       Job Hunter Agent/jobs_feed.json")
            else:
                print(f"⚠️ Note: Raw feed was not saved for this run.")
            print("=" * 65)
    except Exception as e:
        if HAS_RICH:
            console.print(f"\n[bold red]⚠️ Could not export markdown report: {e}[/bold red]")
        else:
            print(f"\n⚠️ Could not export markdown report: {e}")


if __name__ == "__main__":
    main()
