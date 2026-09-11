import sys
import io
from pathlib import Path

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent

print("=" * 60)
print("🧪 RUNNING FULL REGRESSION & NEW FEATURE TEST SUITE")
print("=" * 60)

# -------------------------------------------------------------
# 1. TEST EXISTING MODULES (Linkedin Agent)
# -------------------------------------------------------------
print("\n[TEST GROUP 1] Testing Existing 'Linkedin Agent' Components...")

sys.path.insert(0, str(PROJECT_ROOT / "Linkedin Agent"))

try:
    from src.profile_manager import CandidateProfile
    from src.pipeline_manager import PipelineTracker
    from src.response_generator import ResponseGenerator
    from src.scheduler import InterviewScheduler
    import config

    print("  [+] Imports: All LinkedIn Agent core modules imported successfully.")

    # 1.1 Test CandidateProfile loading
    profile = CandidateProfile()
    name = profile.get_candidate_name()
    roles = profile.get_target_roles()
    print(f"  [+] CandidateProfile: Loaded '{name}', Roles: {roles[:2]}")

    # 1.2 Test PipelineTracker loading
    tracker = PipelineTracker()
    all_opps = tracker.get_all_opportunities()
    waiting_opps = tracker.get_by_status("waiting")
    print(f"  [+] PipelineTracker: Loaded {len(all_opps)} total items ({len(waiting_opps)} waiting items).")

    # 1.3 Test ResponseGenerator
    rg = ResponseGenerator(profile)
    generated = rg.draft_template_response(
        intent="propose_time",
        contact_name="Sarah",
        role_or_details="Senior SDET",
        language="en"
    )
    assert len(generated) > 20, "Response generator produced empty response"
    print(f"  [+] ResponseGenerator: Generated valid response ({len(generated)} chars): '{generated[:50]}...'")

    print("  => ALL EXISTING LINKEDIN AGENT TESTS PASSED!")

except Exception as e:
    print(f"  ❌ FAILED in Linkedin Agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# -------------------------------------------------------------
# 2. TEST EXISTING RUNNER SCRIPTS (headed_apply.py, run_headed.py)
# -------------------------------------------------------------
print("\n[TEST GROUP 2] Testing Existing Runner Scripts...")

try:
    import py_compile

    for script_name in ["headed_apply.py", "run_headed.py", "Linkedin Agent/run.py"]:
        script_path = PROJECT_ROOT / script_name
        if script_path.exists():
            py_compile.compile(str(script_path), doraise=True)
            print(f"  [+] {script_name}: Syntax and compilation verified OK.")

    print("  => ALL EXISTING RUNNER SCRIPTS PASSED!")

except Exception as e:
    print(f"  ❌ FAILED in Runner Scripts: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# -------------------------------------------------------------
# 3. TEST NEW AGGREGATOR MODULES
# -------------------------------------------------------------
print("\n[TEST GROUP 3] Testing New Multi-Source Aggregator...")

sys.path.insert(0, str(PROJECT_ROOT / "Job Hunter Agent"))

try:
    from aggregator.models import JobPost
    from aggregator.cleaner import clean_job_url, deduplicate_jobs, normalize_string
    from aggregator.scorer import CandidateScorer
    from aggregator.sources.jobs_ge_provider import JobsGeProvider
    from aggregator.sources.jobspy_provider import JobSpyProvider
    from aggregator.engine import AggregatorEngine

    print("  [+] Imports: All Aggregator modules imported successfully.")

    # 3.1 Test URL Cleaner (including spjobid and spreportid)
    test_dirty_url = "https://www.linkedin.com/jobs/view/9876543210/?utm_source=share&utm_medium=member_desktop&refId=abc&trackingId=def123"
    cleaned = clean_job_url(test_dirty_url)
    expected = "https://www.linkedin.com/jobs/view/9876543210/"
    assert cleaned == expected, f"URL cleaner mismatch: {cleaned} != {expected}"

    test_sp_url = "https://example.com/job?spJobID=12345&spReportId=67890&utm_medium=email"
    cleaned_sp = clean_job_url(test_sp_url)
    assert cleaned_sp == "https://example.com/job", f"spJobID cleaning failed: {cleaned_sp}"
    print(f"  [+] URL Cleaner: Stripped tracking parameters (including spJobID/spReportId) -> {cleaned}")


    # 3.2 Test Deduplication
    post1 = JobPost(title="Senior QA Automation Engineer", company="Acme Inc", job_url="https://acme.com/job1?ref=1", source="indeed")
    post2 = JobPost(title="Sr. QA Automation Engineer", company="Acme, Inc.", job_url="https://acme.com/job1?utm_source=google", source="google")
    post3 = JobPost(title="Staff SDET", company="Beta Corp", job_url="https://beta.com/job2", source="glassdoor")
    
    deduped = deduplicate_jobs([post1, post2, post3])
    assert len(deduped) == 2, f"Expected 2 deduplicated jobs, got {len(deduped)}"
    print(f"  [+] Deduplication: Successfully reduced 3 raw postings to {len(deduped)} unique.")

    # 3.3 Test Candidate Scorer (High Fit)
    sdet_job = JobPost(
        title="Lead SDET (Playwright, C#)",
        company="Tech Leader",
        job_url="https://techleader.com/job",
        source="indeed",
        is_remote=True,
        description="Looking for an SDET with Playwright, C#, TypeScript, K6, and CI/CD."
    )
    scored_sdet = CandidateScorer.score_job(sdet_job)
    assert scored_sdet.fit_score >= 80, f"Expected score >= 80, got {scored_sdet.fit_score}"
    assert "STRONG MATCH" in scored_sdet.fit_grade
    print(f"  [+] Scorer (High Fit): {scored_sdet.fit_score}% - {scored_sdet.fit_grade}")

    # 3.4 Test Candidate Scorer (Demotion)
    junior_job = JobPost(
        title="Junior Manual QA Tester",
        company="Small Co",
        job_url="https://smallco.com/job",
        source="indeed",
        description="Manual testing only. No automation required."
    )
    scored_junior = CandidateScorer.score_job(junior_job)
    assert scored_junior.fit_score < 40, f"Expected score < 40, got {scored_junior.fit_score}"
    print(f"  [+] Scorer (Demotion): Penalized junior/manual -> {scored_junior.fit_score}% ({scored_junior.fit_grade})")

    # 3.5 Test Jobs.ge Live Retrieval
    jobs_ge_res = JobsGeProvider.search("qa", max_results=3)
    assert len(jobs_ge_res) > 0, "Jobs.ge search returned 0 results"
    print(f"  [+] Jobs.ge Provider: Retrieved {len(jobs_ge_res)} live vacancies (Sample: '{jobs_ge_res[0].title}')")

    # 3.6 Test AggregatorEngine output formatting
    engine = AggregatorEngine()
    table = engine.format_markdown_table([scored_sdet, scored_junior])
    assert "| Fit | Score | Job Title |" in table
    print("  [+] AggregatorEngine: Markdown table formatting verified.")

    print("  => ALL NEW AGGREGATOR TESTS PASSED!")

except Exception as e:
    print(f"  ❌ FAILED in Aggregator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 ALL CHECKS PASSED: OLD AND NEW COMPONENTS FUNCTION FLAWLESSLY!")
print("=" * 60)
