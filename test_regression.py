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
        role_or_details="Thursday at 16:00",
        language="en"
    )
    assert len(generated) > 20, "Response generator produced empty response"
    # 1.4 Test InterviewScheduler & Salary normalization
    scheduler = InterviewScheduler(profile)
    timezone = profile.get_preferences().get("timezone", "").strip()
    standard_proposal = scheduler.get_standard_slots("en", proposed_slots="Thursday at 16:00")
    confirmation = scheduler.format_confirmation("Thursday, Aug 27", "16:00")
    if timezone:
        assert "(" in standard_proposal and ")" in standard_proposal, "Proposal must contain timezone specification"
        assert "(" in confirmation and ")" in confirmation, "Confirmation must contain timezone specification"
    else:
        assert "timezone" in standard_proposal.lower(), "Missing timezone should be reported"
        assert "timezone" in confirmation.lower(), "Missing timezone should be reported"
    salary = profile.get_salary_expectation()
    assert "*" not in salary and "_" not in salary and "`" not in salary, "Salary contains markdown"
    assert not salary.lower().startswith("minimum"), "Salary should be normalized without leading Minimum label"
    print(f"  [+] InterviewScheduler & Salary: Proposal valid, normalized salary: '{salary}'")

    print("  => ALL EXISTING LINKEDIN AGENT TESTS PASSED!")

except Exception as e:
    print(f"  ❌ FAILED in LinkedIn Agent tests: {e}")
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
        assert script_path.is_file(), f"Required runner script not found: {script_name}"
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

    # 3.3 Test Candidate Scorer (High Fit with deterministic criteria)
    CandidateScorer._cached_keywords = {
        "playwright": 18,
        "selenium": 10,
        "typescript": 12,
        "c#": 12,
        "k6": 12,
        "ci/cd": 10,
        "sdet": 20,
    }
    CandidateScorer._cached_target_roles = ["sdet", "qa automation", "automation engineer"]

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

    # 3.5 Test Jobs.ge Provider HTML parsing (Deterministic Mock)
    from unittest.mock import patch, MagicMock
    import requests
    mock_html = """
    <html><body>
    <table class="regularEntries">
        <tr>
            <td><a href="/en/?view=jobs&id=99999" class="vip">Senior QA Automation Engineer</a></td>
            <td><a href="/en/?view=client&client=123">Bank of Georgia</a></td>
            <td>11 Sep</td>
            <td>11 Oct</td>
        </tr>
    </table>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html

    with patch.object(requests.Session, "get", return_value=mock_resp):
        jobs_ge_res = JobsGeProvider.search("qa", max_results=2)
        assert len(jobs_ge_res) >= 1, f"Expected mock job from Jobs.ge, got {len(jobs_ge_res)}"
        assert jobs_ge_res[0].title == "Senior QA Automation Engineer"
        assert jobs_ge_res[0].company == "Bank of Georgia"
        print(f"  [+] Jobs.ge Provider (Deterministic Mock): Retrieved {len(jobs_ge_res)} vacancy (Sample: '{jobs_ge_res[0].title}')")

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


# -------------------------------------------------------------
# 4. TEST TIERED TOKEN OPTIMIZATION (COMPACT VS FULL CONTEXT)
# -------------------------------------------------------------
print("\n[TEST GROUP 4] Testing Tiered Token Optimization (L1 vs L2)...")

try:
    from src.profile_manager import CandidateProfile
    from src.response_generator import ResponseGenerator

    prof = CandidateProfile()
    compact_prompt = prof.get_compact_context_prompt()
    full_prompt = prof.get_full_context_prompt()

    assert len(compact_prompt) > 0, "Compact prompt should not be empty"
    assert len(compact_prompt) < len(full_prompt), "Compact prompt must be significantly smaller than full prompt"
    print(f"  [+] Profile Manager: Compact context ({len(compact_prompt)} chars) is ~{round((1 - len(compact_prompt)/len(full_prompt))*100)}% smaller than full ({len(full_prompt)} chars).")

    gen = ResponseGenerator(profile=prof)
    # Test _is_deep_query intent classification (L1 vs L2)
    assert gen._is_deep_query("tell me about your projects") is True
    assert gen._is_deep_query("what metrics did you achieve") is True
    assert gen._is_deep_query("describe your background") is True
    assert gen._is_deep_query("მომიყევი თქვენს წინა პროექტებზე") is True
    assert gen._is_deep_query("we have an exciting project and need details") is False
    assert gen._is_deep_query("Hello, are you open to new opportunities?") is False
    print("  [+] ResponseGenerator: Intent classification reliably separates L1 inquiries from L2 deep dives.")

    # Explicitly clear API client handles to test the offline template fallback path deterministically
    gen.client = None
    gen.legacy_model = None

    # Standard greeting uses compact L1 context and template fallback
    reply_std, req_std = gen.draft_llm_response("Hello, are you open to new opportunities?", contact_name="Anna")
    assert "Anna" in reply_std, "Expected contact name in reply"
    print("  [+] ResponseGenerator: Standard greeting offline fallback successfully processed.")

    print("  => ALL TIERED TOKEN OPTIMIZATION TESTS PASSED!")

except Exception as e:
    print(f"  ❌ FAILED in Token Optimization: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 ALL CHECKS PASSED: OLD AND NEW COMPONENTS FUNCTION FLAWLESSLY!")
print("=" * 60)

