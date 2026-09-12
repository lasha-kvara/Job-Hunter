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

    for script_name in ["headed_apply.py", "run_headed.py", "Linkedin Agent/run.py", "search_jobs.py"]:
        script_path = PROJECT_ROOT / script_name
        assert script_path.is_file(), f"Required runner script not found: {script_name}"
        py_compile.compile(str(script_path), doraise=True)
        print(f"  [+] {script_name}: Syntax and compilation verified OK.")

    # Exercise show_banner and show_profile_facts execution to guarantee no runtime NameError or blank labels
    sys.path.insert(0, str(PROJECT_ROOT / "Linkedin Agent"))
    import run as linkedin_runner
    linkedin_runner.show_banner(CandidateProfile())
    linkedin_runner.show_profile_facts(CandidateProfile())
    template_path_run = PROJECT_ROOT / "Linkedin Agent" / "candidate-profile.template.md"
    if template_path_run.exists():
        tmpl_inst = CandidateProfile(file_path=template_path_run)
        linkedin_runner.show_banner(tmpl_inst)
        linkedin_runner.show_profile_facts(tmpl_inst)
    print("  [+] Linkedin Agent/run.py: show_banner and show_profile_facts rendered configured and template profiles successfully.")

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

    # Test CandidateScorer unconfigured criteria fallback
    CandidateScorer._cached_keywords = None
    CandidateScorer._cached_target_roles = None
    from unittest.mock import patch
    with patch.object(CandidateScorer, "_resolve_profile_path", return_value=None):
        def_kws, def_roles = CandidateScorer.load_profile_criteria()
        assert len(def_kws) > 0, "Default keywords must be loaded when profile path is None"
        assert "sdet" in def_roles, "Default target roles must contain SDET"
    print("  [+] Scorer (Fallback): Successfully initialized default SDET criteria when profile is unconfigured.")

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

    # Test dynamic employer detection with historical inquiry requirement vs recruiter pitches
    # Set explicit in-memory fixture so regression suite does not depend on uncommitted personal profiles
    prof.file_path = PROJECT_ROOT / "candidate-profile.fixture.md"
    prof.raw_content = "# Candidate Profile: Regression Candidate"
    prof.sections["Experience"] = "- **2020 — Present: QA @ TBC**\n- **2018 — 2020: QA @ VTB Bank Georgia**"
    assert "TBC" in prof.get_previous_companies() or "VTB Bank Georgia" in prof.get_previous_companies()
    assert gen._is_deep_query("We have an open role at TBC, are you interested?") is False
    assert gen._is_deep_query("Is TBC hiring right now?") is False
    assert gen._is_deep_query("We have a VTB position open") is False
    assert gen._is_deep_query("What did you do at TBC?") is True
    assert gen._is_deep_query("Tell me about your time at VTB") is True
    # Test target-before-question coverage (e.g. 'At TBC, what did you do?') and Georgian ordering
    assert gen._is_deep_query("At TBC, what did you do?") is True
    assert gen._is_deep_query("At TBC, what was your role?") is True
    assert gen._is_deep_query("In VTB what did you do?") is True
    assert gen._is_deep_query("TBC-ში ყოფნის დროს რას აკეთებდით?") is True
    assert gen._is_deep_query("TBC-ში რა იყო თქვენი როლი?") is True
    # Test expanded historical inquiries with 'your work', 'your experience', 'your projects' and Georgian variants
    assert gen._is_deep_query("Can you tell me about your work at TBC?") is True
    assert gen._is_deep_query("Could you share your experience at TBC?") is True
    assert gen._is_deep_query("Tell me about your projects at TBC") is True
    assert gen._is_deep_query("Can you describe your work at TBC?") is True
    assert gen._is_deep_query("At TBC, tell me about your work") is True
    assert gen._is_deep_query("TBC-ზე მომიყევით") is True
    assert gen._is_deep_query("TBC-ში თქვენს გამოცდილებაზე გვითხარით") is True
    assert gen._is_deep_query("TBC-ში რას გვეტყვით თქვენს როლზე?") is True

    # Test routine recruiter pitches with technical terms (stay L1) vs candidate-directed technical inquiries (trigger L2)
    assert gen._is_deep_query("We need someone for our system architecture") is False
    assert gen._is_deep_query("The role includes performance testing") is False
    assert gen._is_deep_query("We are looking for someone with framework design experience") is False
    assert gen._is_deep_query("What framework does the role use?") is False
    assert gen._is_deep_query("How does the system design look on our project?") is False
    assert gen._is_deep_query("What does TBC do?") is False

    # Test routine recruiter compliments and pitch phrasing (stay L1) vs candidate inquiries (trigger L2)
    assert gen._is_deep_query("Your experience with Playwright is a strong fit for this role") is False
    assert gen._is_deep_query("We came across your profile and your background looks great!") is False
    assert gen._is_deep_query("Your experience caught our eye for this opening.") is False
    assert gen._is_deep_query("We love your background in QA automation!") is False
    assert gen._is_deep_query("Your experience at TBC is a strong fit") is False
    assert gen._is_deep_query("We need someone with your previous experience in automation") is False
    assert gen._is_deep_query("We are looking for someone with your past experience") is False
    assert gen._is_deep_query("Your previous experience in testing would be valuable") is False

    # Test job requirement pitches mentioning historical experience (stay L1) vs candidate inquiries (trigger L2)
    assert gen._is_deep_query("This role requires previous experience with Playwright") is False
    assert gen._is_deep_query("Looking for an engineer with prior experience in automation") is False
    assert gen._is_deep_query("The position expects past experience in load testing") is False
    assert gen._is_deep_query("Previous experience with C# is preferred") is False

    # Test possessive recruiter job pitches (stay L1) vs candidate historical inquiries (trigger L2)
    assert gen._is_deep_query("Your role will include system architecture") is False
    assert gen._is_deep_query("In this position, your work will focus on performance testing") is False
    assert gen._is_deep_query("Your role here will be fully remote") is False
    assert gen._is_deep_query("Tell me about your previous role") is True
    assert gen._is_deep_query("What was your role in system design?") is True
    assert gen._is_deep_query("Tell me about your past work") is True
    assert gen._is_deep_query("Can you provide details about the role's architecture?") is False
    assert gen._is_deep_query("Can you provide details about your architecture?") is True
    assert gen._is_deep_query("Could you share your project's performance testing metrics?") is True
    assert gen._is_deep_query("Can you tell me about your previous experience?") is True
    assert gen._is_deep_query("Walk me through your past projects") is True

    assert gen._is_deep_query("Tell me about your system architecture experience") is True
    assert gen._is_deep_query("Walk me through your test framework architecture") is True
    assert gen._is_deep_query("How did you conduct performance testing in past roles?") is True
    assert gen._is_deep_query("What framework did you use on previous projects?") is True
    assert gen._is_deep_query("What was your role at TBC?") is True
    print("  [+] ResponseGenerator: Dynamic employer extraction and technical intent classification correctly separate recruiter pitches from candidate inquiries.")

    # Test featured projects parser handles bold, hyphenated, slashed, and ampersand project names
    prof_feat = CandidateProfile()
    prof_feat.file_path = PROJECT_ROOT / "candidate-profile.fixture.md"
    prof_feat.raw_content = "# Candidate Profile: Regression Candidate"
    prof_feat.sections = {
        "Featured projects": "- **Job-Hunter** — autonomous application engine\n* `Extra.ge / Area.ge` — mobile test plans\n- QA & Reports (Tooling)"
    }
    prev_comps = prof_feat.get_previous_companies()
    assert "Job-Hunter" in prev_comps, f"Failed to extract hyphenated project: {prev_comps}"
    assert "Extra.ge / Area.ge" in prev_comps, f"Failed to extract slashed project: {prev_comps}"
    assert "QA & Reports" in prev_comps, f"Failed to extract ampersand project: {prev_comps}"
    print("  [+] Profile Manager: Featured projects parser correctly extracts hyphenated, slashed, and ampersand project names.")

    # Test availability and relocation are included in compact prompt for grounded responses
    assert "Availability:" in compact_prompt, "Compact prompt must include grounded Availability"
    assert "Relocation:" in compact_prompt, "Compact prompt must include grounded Relocation"
    print("  [+] Profile Manager: Grounded availability and relocation verified in compact prompt.")

    # Test template-backed profile placeholder normalization
    template_path = PROJECT_ROOT / "Linkedin Agent" / "candidate-profile.template.md"
    assert template_path.is_file(), f"Required template file not found: {template_path}"
    prof_tmpl = CandidateProfile(file_path=template_path)
    assert prof_tmpl.get_candidate_name() == "", "Template name [Full Name] must be normalized to empty"
    assert prof_tmpl.get_summary() == "", "Template summary instruction must be normalized to empty"
    assert prof_tmpl.get_target_roles() == [], "Template example roles must be normalized to empty"
    assert prof_tmpl.get_previous_companies() == [], "Template profile must not extract [Company] placeholder"
    assert prof_tmpl.get_salary_expectation() == "", "Template $[Amount] must be normalized to empty"
    assert prof_tmpl.get_preferences()["notice_period"] == "", "Template notice must be normalized to empty"
    assert prof_tmpl.get_contacts().get("email", "") == "", "Template email [Your Email] must be normalized to empty"
    tmpl_compact = prof_tmpl.get_compact_context_prompt()
    assert "Summary: [Not configured in candidate-profile.md]" in tmpl_compact
    assert "Target Roles: [Not configured in candidate-profile.md]" in tmpl_compact
    assert "Key Skills: [Not configured in candidate-profile.md]" in tmpl_compact
    assert "Salary Expectation: [Not specified]" in tmpl_compact
    assert prof_tmpl.get_full_context_prompt() == tmpl_compact, "Template full context must match sanitized compact prompt"
    # Test is_placeholder with valid bracketed real values vs template placeholders
    assert CandidateProfile.is_placeholder("Software Engineer [Remote]") is False, "Bracketed qualifier must not be flagged as placeholder"
    assert CandidateProfile.is_placeholder("QA Automation Lead [Contract]") is False, "Bracketed qualifier must not be flagged as placeholder"
    assert CandidateProfile.is_placeholder("[Full Name]") is True, "Full bracketed tag must be recognized as placeholder"
    assert CandidateProfile.is_placeholder("Minimum $[Amount] USD/month (or gross annual).") is True, "Unconfigured template salary line must be recognized as placeholder"
    assert CandidateProfile.is_placeholder("[e.g. 1 month / Immediate]") is True, "Example bracketed value must be recognized as placeholder"
    print("  [+] Profile Manager: is_placeholder accurately differentiates legitimate bracketed text from unconfigured template placeholders.")

    # Test unconfigured profile preserves explicit [Not specified] without inventing generic defaults
    prof_empty = CandidateProfile()
    prof_empty.sections = {}
    empty_prefs = prof_empty.get_preferences()
    assert empty_prefs["notice_period"] == "", "Unconfigured notice must be empty in preferences"
    assert empty_prefs["relocation"] == "", "Unconfigured relocation must be empty in preferences"
    assert prof_empty.get_summary() == "", "Unconfigured summary must be empty string"
    assert prof_empty.get_target_roles() == [], "Unconfigured target roles must be empty list"
    empty_compact = prof_empty.get_compact_context_prompt()
    assert "Summary: [Not configured in candidate-profile.md]" in empty_compact, "Unconfigured summary must render explicit fallback"
    assert "Target Roles: [Not configured in candidate-profile.md]" in empty_compact, "Unconfigured roles must render explicit fallback"
    assert "Relocation: [Not specified]" in empty_compact, "Unconfigured relocation must render as [Not specified]"
    assert "Notice: [Not specified]" in empty_compact, "Unconfigured notice must render as [Not specified]"
    assert "Availability: [Not specified]" in empty_compact, "Unconfigured availability must render as [Not specified]"
    print("  [+] Profile Manager: Unconfigured profiles preserve explicit [Not configured/specified] grounding markers.")

    # Test skills extraction skips Personal Skills even when personal skills appears first in profile sections
    prof_ps = CandidateProfile()
    prof_ps.sections = {
        "Personal skills (competencies)": "- Fast learner\n- Team player\n- Leadership",
        "Skills": "- Python, Playwright, C#, Selenium",
    }
    compact_ps = prof_ps.get_compact_context_prompt()
    assert "Python" in compact_ps, "Technical skills must be extracted"
    assert "Leadership" not in compact_ps, "Personal skills section must be skipped in Key Skills"
    print("  [+] Profile Manager: Skills extractor correctly prioritizes technical skills over personal skills.")

    # Test bounded compact context with excessively long prose across ALL user-controlled fields
    prof_verbose = CandidateProfile()
    prof_verbose.sections = {
        "Summary (elevator pitch)": "A" * 2000,
        "Target roles": "- Principal SDET Lead Specialist " * 50,
        "Skills": "Python, Java, TypeScript, Playwright, Selenium, Architecture, Docker, Kubernetes, AWS, GCP, Azure, Linux " * 50,
        "Salary expectation": "$4500 USD per month net with additional annual bonus structure " * 20,
        "Work preferences & logistics": "Timezone: " + "GMT+4 Georgia Tbilisi " * 20 + "\nNotice: " + "1 month notice period required " * 20 + "\nWork mode: " + "Remote / Hybrid acceptable " * 20
    }
    compact_verbose = prof_verbose.get_compact_context_prompt()
    assert len(compact_verbose) < 900, f"Compact prompt should remain bounded, got {len(compact_verbose)} chars"
    print(f"  [+] Profile Manager: Verbose profile across all fields bounded successfully ({len(compact_verbose)} chars).")

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

