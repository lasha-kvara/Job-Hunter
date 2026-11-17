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
    from aggregator import settings

    # Tests use the documented defaults only, never the user's personal config.yml.
    settings.use(settings.example())
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
    assert "| Verdict | Rating | Score | Job Title |" in table
    print("  [+] AggregatorEngine: Markdown table formatting verified.")

    # 3.7 Assessment: 1-5 rating, verdicts, blockers, legitimacy, duplicates
    from datetime import datetime, timezone
    from aggregator.assessment import assess, RepostTracker
    now = datetime(2026, 11, 17, tzinfo=timezone.utc)

    good = JobPost(title="Senior SDET", company="Acme", job_url="https://acme.com/1", source="ats",
                   location="Remote - EMEA", is_remote=True, date_posted="2026-11-10T00:00:00Z",
                   description="Remote within Europe. " + "Playwright TypeScript CI/CD. " * 30)
    good.fit_score = 90
    assess(good, now=now)
    assert good.rating == 4.6 and good.verdict == "Apply" and not good.flags, (good.rating, good.verdict, good.flags)

    us_only = JobPost(title="QA Automation Engineer", company="Outside", job_url="https://o.com/2", source="ats",
                      location="Remote", is_remote=True,
                      description="Fully remote; we welcome applicants based anywhere in the United States or Canada. " * 10)
    us_only.fit_score = 90
    assess(us_only, now=now)
    assert us_only.verdict == "Skip" and us_only.rating <= 2.0 and us_only.flags[0].startswith("BLOCK"), us_only.flags

    us_loc = JobPost(title="SDET", company="X", job_url="https://x.com/3", source="ats", location="Remote - US",
                     is_remote=True, description="Build tests. " * 50)
    us_loc.fit_score = 80
    assess(us_loc, now=now)
    assert us_loc.verdict == "Skip" and "region-locked" in us_loc.flags[0], us_loc.flags

    paren = JobPost(title="QA/DevOps Engineer", company="D", job_url="https://d.com/9", source="ats",
                    location="San Francisco Bay Area or Remote (U.S.)", is_remote=True, description="Tests. " * 80)
    paren.fit_score = 100
    assess(paren, now=now)
    assert paren.verdict == "Skip" and "region-locked" in paren.flags[0], paren.flags

    marketing = JobPost(title="QA Automation Engineer", company="O", job_url="https://o.com/8", source="ats",
                        location="Remote", is_remote=True,
                        description="Loved by athletes worldwide. " * 5 + "We welcome applicants based anywhere in the United States or Canada.")
    marketing.fit_score = 100
    assess(marketing, now=now)
    assert marketing.verdict == "Skip" and "residency" in marketing.flags[0], marketing.flags

    onsite = JobPost(title="QA Engineer", company="P", job_url="https://p.com/7", source="ats",
                     location="Sofia, Bulgaria", is_remote=False, description="Office in Sofia. " * 40)
    onsite.fit_score = 100
    assess(onsite, now=now)
    assert onsite.verdict == "Skip" and "on-site/hybrid abroad" in onsite.flags[0], onsite.flags

    tbilisi = JobPost(title="QA Engineer", company="G", job_url="https://g.ge/6", source="jobs_ge",
                      location="Tbilisi", is_remote=False, description="Office in Tbilisi. " * 40)
    tbilisi.fit_score = 80
    assess(tbilisi, now=now)
    assert tbilisi.verdict == "Apply" and not tbilisi.flags, tbilisi.flags

    auth = JobPost(title="SDET", company="Y", job_url="https://y.com/4", source="ats", location="Remote",
                   is_remote=True, description="You must be legally authorized to work in the United States. " * 8)
    auth.fit_score = 80
    assess(auth, now=now)
    assert auth.verdict == "Skip" and "work authorization" in auth.flags[0], auth.flags

    stale = JobPost(title="SDET", company="Z", job_url="https://z.com/5", source="ats", location="Remote, Worldwide",
                    is_remote=True, date_posted="2026-09-01T00:00:00Z", description="Too short.")
    stale.fit_score = 75
    assess(stale, now=now)
    assert any(f.startswith("stale") for f in stale.flags) and "thin description" in stale.flags
    assert stale.rating == 3.5 and stale.verdict == "Consider", (stale.rating, stale.verdict)

    dup = JobPost(title="Senior QA Automation Engineer", company="Ankix", job_url="https://jobs.ankix.com/77",
                  source="ats", location="Remote", is_remote=True, description="Remote. " * 80)
    dup.fit_score = 90
    assess(dup, applied_text="- 1. ankix — senior qa automation engineer | external | submitted", now=now)
    assert dup.applied and dup.verdict == "Skip" and dup.flags[0] == "already applied", dup.flags

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tr = RepostTracker(Path(tmp) / "seen.json")
        a1 = JobPost(title="SDET", company="Q", job_url="https://q.com/a", source="ats")
        assert tr.check(a1, now=datetime(2026, 10, 1, tzinfo=timezone.utc)) is None
        tr.save()
        tr2 = RepostTracker(Path(tmp) / "seen.json")
        a2 = JobPost(title="SDET", company="Q", job_url="https://q.com/b", source="ats")
        assert "reposted" in (tr2.check(a2, now=now) or ""), "repost not detected"
    print("  [+] Assessment: rating/verdict, US-only + work-auth blockers, stale/thin/repost flags, duplicate check verified.")

    # 3.8 ATS boards provider (deterministic mocks for Greenhouse, Ashby, Lever)
    from aggregator.sources.ats_provider import AtsBoardsProvider

    def fake_get(self, url, timeout=None, **kw):
        r = MagicMock(); r.ok = True; r.status_code = 200
        if "boards-api.greenhouse.io" in url and url.endswith("/jobs"):
            r.json.return_value = {"jobs": [
                {"id": 1, "title": "Senior QA Automation Engineer", "absolute_url": "https://gh/1",
                 "location": {"name": "Remote, Europe"}, "first_published": "2026-11-15T00:00:00Z"},
                {"id": 2, "title": "Account Executive", "absolute_url": "https://gh/2", "location": {"name": "Remote"}}]}
        elif "boards-api.greenhouse.io" in url:
            r.json.return_value = {"content": "&lt;p&gt;Playwright &amp; TypeScript&lt;/p&gt;", "company_name": "GH Co"}
        elif "ashbyhq" in url:
            r.json.return_value = {"jobs": [
                {"title": "SDET", "jobUrl": "https://ashby/1", "location": "Berlin", "isRemote": False,
                 "workplaceType": "OnSite", "publishedAt": "2026-11-14T00:00:00Z", "descriptionPlain": "Office role"},
                {"title": "Test Engineer", "jobUrl": "https://ashby/2", "location": "Remote", "isRemote": True,
                 "publishedAt": "2026-06-01T00:00:00Z", "descriptionPlain": "old"}]}
        elif "smartrecruiters.com" in url and "/postings?" in url:
            r.json.return_value = {"totalFound": 2, "content": [
                {"id": "11", "name": "Senior QA Engineer", "company": {"name": "SR Co"}, "releasedDate": "2026-11-15T00:00:00Z",
                 "location": {"city": "Tbilisi", "country": "ge", "remote": True, "fullLocation": "Tbilisi, Georgia"}},
                {"id": "12", "name": "Lawyer", "company": {"name": "SR Co"}, "location": {"remote": True}}]}
        elif "smartrecruiters.com" in url:
            r.json.return_value = {"postingUrl": "https://jobs.smartrecruiters.com/srco/11-qa",
                                   "jobAd": {"sections": {"jobDescription": {"text": "<p>Playwright</p>"}}}}
        elif "recruitee.com" in url:
            r.json.return_value = {"offers": [
                {"title": "QA Automation Engineer", "careers_url": "https://rc.recruitee.com/o/qa", "location": "Remote job",
                 "city": "San Francisco", "country": "United States", "remote": True, "company_name": "RC Ltd",
                 "published_at": "2026-11-16 10:01:42 UTC", "description": "<p>Remote</p>", "requirements": ""}]}
        else:  # lever
            r.json.return_value = [{"text": "QA Engineer (Playwright)", "hostedUrl": "https://lever/1",
                                    "categories": {"location": "Tbilisi, Georgia", "commitment": "Full-time"},
                                    "workplaceType": "remote", "createdAt": 1763164800000,
                                    "descriptionPlain": "Remote role", "lists": []}]
        return r

    with patch.object(requests.Session, "get", fake_get):
        ats_jobs = AtsBoardsProvider.search(query="QA Automation Engineer", max_age_days=30000, is_remote=True,
                                            boards={"greenhouse": ["ghco"], "ashby": ["ash"], "lever": ["lev"], "lever_eu": []})
    titles = sorted(j.title for j in ats_jobs)
    # Account Executive: wrong title; Berlin SDET: on-site; old Ashby job is kept only because max_age_days is huge here.
    assert titles == ["QA Engineer (Playwright)", "Senior QA Automation Engineer", "Test Engineer"], titles
    gh_job = next(j for j in ats_jobs if j.source == "greenhouse")
    assert gh_job.company == "GH Co" and "Playwright & TypeScript" in gh_job.description, gh_job
    with patch.object(requests.Session, "get", fake_get):
        recent = AtsBoardsProvider.search(query="", max_age_days=30, is_remote=True,
                                          boards={"greenhouse": [], "ashby": ["ash"], "lever": [], "lever_eu": []})
    assert recent == [] or all(j.date_posted >= "2026-10" for j in recent), [j.title for j in recent]
    with patch.object(requests.Session, "get", fake_get):
        more = AtsBoardsProvider.search(query="", max_age_days=30000, is_remote=True,
                                        boards={"smartrecruiters": ["srco"], "recruitee": ["rc"]})
    by_src = {j.source: j for j in more}
    assert set(by_src) == {"smartrecruiters", "recruitee"} and len(more) == 2, [j.title for j in more]
    sr = by_src["smartrecruiters"]
    assert sr.company == "SR Co" and sr.job_url.endswith("11-qa") and "Playwright" in sr.description and sr.location.startswith("Remote")
    rc = by_src["recruitee"]
    # Remote Recruitee offers keep their own label, not the HQ country (which would look US-locked).
    assert rc.location == "Remote job" and rc.company == "RC Ltd" and rc.date_posted.startswith("2026-11-16T10:01:42"), rc
    # 3.9 A different person's config.yml changes title filter, home country and scoring
    import copy
    other = copy.deepcopy(settings.example())
    other["role"].update(title_keywords=["frontend", "front-end", "react"], title_exclude=["intern"],
                         target_roles=["frontend developer"], fallback_skills={"react": 20, "typescript": 15})
    other["location"].update(home_places=["poland", "warsaw", "kraków"], home_exclude=[],
                             locked_regions=["us", "united states"], check_regions=["uk"])
    other["candidate"]["timezone_window"] = [-1, 2]
    settings.use(other)
    CandidateScorer._cached_keywords = None
    CandidateScorer._cached_target_roles = None
    from aggregator.sources.ats_provider import _title_matcher
    m = _title_matcher("")
    assert m("Senior Frontend Engineer (React)") and not m("Senior QA Engineer") and not m("Frontend Intern")
    warsaw = JobPost(title="Frontend Developer", company="W", job_url="https://w.pl/1", source="ats",
                     location="Warsaw, Poland", is_remote=False, description="Office. " * 80)
    warsaw.fit_score = 80
    assess(warsaw, now=now)
    assert warsaw.verdict == "Apply" and not warsaw.flags, warsaw.flags
    tbilisi_now = JobPost(title="Frontend Developer", company="T", job_url="https://t.ge/1", source="ats",
                          location="Tbilisi, Georgia", is_remote=False, description="Office. " * 80)
    tbilisi_now.fit_score = 80
    assess(tbilisi_now, now=now)
    assert tbilisi_now.verdict == "Skip" and "on-site/hybrid abroad" in tbilisi_now.flags[0], tbilisi_now.flags
    with patch.object(CandidateScorer, "_resolve_profile_path", return_value=None):
        kws, roles = CandidateScorer.load_profile_criteria()
    assert kws == {"react": 20, "typescript": 15} and roles == ["frontend developer"], (kws, roles)
    settings.use(settings.example())
    CandidateScorer._cached_keywords = None
    CandidateScorer._cached_target_roles = None
    print("  [+] Settings: another profession/country in config.yml changes title filter, home country and fallback skills.")

    # 3.10 Every profession preset loads and its title filter keeps the right titles
    samples = {
        "qa-automation": (["Senior QA Automation Engineer", "SDET II", "Test Automation Lead"],
                          ["Data Quality Analyst", "Growth Marketer (QA Automation)", "Senior Backend Engineer"]),
        "frontend": (["Senior Frontend Engineer", "React Developer", "Front-End Developer"],
                     ["Product Designer", "Backend Engineer"]),
        "backend": (["Senior Backend Engineer (Go)", "Java Developer", "Node.js Engineer"],
                    ["Frontend Engineer", "Account Executive"]),
        "fullstack": (["Full Stack Engineer", "Senior Full-Stack Developer"],
                      ["Software Engineer, Infrastructure", "Analytics Lead, Full Stack"]),
        "mobile": (["Senior iOS Engineer", "Android Developer", "React Native Engineer"],
                   ["Account Executive, Mobile Gaming", "Mobile QA Engineer"]),
        "devops": (["Senior DevOps Engineer", "Site Reliability Engineer", "Platform Engineer"],
                   ["Corporate Security Infrastructure Project Manager"]),
        "data-engineer": (["Senior Data Engineer", "Analytics Engineer"], ["Data Entry Clerk", "Data Analyst"]),
        "data-analyst": (["Senior Data Analyst", "Product Analyst"], ["Data Engineer", "Credit Analytics AVP"]),
        "ml-engineer": (["Machine Learning Engineer", "Senior Data Scientist", "LLM Engineer"],
                        ["Solutions Architect - AI/ML", "HTML Developer"]),
        "product-designer": (["Senior Product Designer", "UX Designer", "UI/UX Designer"],
                             ["Frontend Engineer", "Interior Designer"]),
        "product-manager": (["Senior Product Manager", "Product Owner"],
                            ["Product Marketing Manager", "Product Designer"]),
    }
    assert sorted(samples) == settings.available_presets(), settings.available_presets()
    for name, (keep, drop) in samples.items():
        cfg_p = settings.example(name)
        role = cfg_p["role"]
        for key in ("default_query", "target_roles", "title_keywords", "fallback_skills"):
            assert role.get(key), f"preset {name}: role.{key} is empty"
        assert role["seniority_bonus"] and role["title_penalties"].get("intern"), f"{name}: shared defaults lost"
        settings.use(cfg_p)
        m = _title_matcher("")
        bad = [t for t in keep if not m(t)] + [f"!{t}" for t in drop if m(t)]
        assert not bad, f"preset {name}: {bad}"
    settings.use(settings.example())
    try:
        settings.compose({}, "no-such-preset")
        raise AssertionError("unknown preset accepted")
    except ValueError:
        pass
    clr = JobPost(title="Staff SRE (TS/SCI)", company="C", job_url="https://c.com/1", source="ats",
                  location="Remote", is_remote=True, description="Remote. " * 80)
    clr.fit_score = 90
    assess(clr, now=now)
    assert clr.verdict == "Skip" and "security clearance" in clr.flags[0], clr.flags
    print(f"  [+] Presets: {len(samples)} profession presets load and filter titles correctly; clearance jobs blocked.")
    print(f"  [+] ATS Provider (Deterministic Mock): {len(ats_jobs) + len(more)} QA jobs from Greenhouse/Ashby/Lever/SmartRecruiters/Recruitee; title, remote and age filters verified.")

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
    if prof.is_template_profile:
        assert compact_prompt == full_prompt, "Template profiles must sanitize full prompt to match compact context"
        print(f"  [+] Profile Manager (Template): Compact and full context sanitized identically ({len(compact_prompt)} chars).")
    else:
        assert len(compact_prompt) < len(full_prompt), "Compact prompt must be significantly smaller than full prompt"
        print(f"  [+] Profile Manager: Compact context ({len(compact_prompt)} chars) is ~{round((1 - len(compact_prompt)/len(full_prompt))*100)}% smaller than full ({len(full_prompt)} chars).")

    # Verify size comparison on a configured fixture profile regardless of environment
    prof_configured = CandidateProfile()
    prof_configured.file_path = PROJECT_ROOT / "candidate-profile.fixture.md"
    prof_configured.raw_content = "# Candidate Profile: Regression Candidate\n\n" + ("Detailed background information\n" * 100)
    prof_configured.sections = {
        "Summary": "A seasoned engineer with extensive distributed systems and QA experience.",
        "Target Roles": "- Senior QA Automation Engineer\n- SDET",
        "Key Skills": "- Python, Playwright, CI/CD",
        "Experience": "- **2020 — Present: QA Lead @ Tech Corp**\n" + ("  * Built robust automation pipelines\n" * 20),
    }
    cfg_compact = prof_configured.get_compact_context_prompt()
    cfg_full = prof_configured.get_full_context_prompt()
    assert len(cfg_compact) < len(cfg_full), "Configured profile compact prompt must be significantly smaller than full prompt"
    print(f"  [+] Profile Manager (Configured fixture): Compact context ({len(cfg_compact)} chars) is ~{round((1 - len(cfg_compact)/len(cfg_full))*100)}% smaller than full ({len(cfg_full)} chars).")


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

# -------------------------------------------------------------
# 5. SETUP WIZARD (init.py) AND HEALTH CHECK (doctor.py)
# -------------------------------------------------------------
print("\n[TEST GROUP 5] Testing setup wizard and doctor...")
try:
    import importlib.util, builtins, types, tempfile, json as _json, yaml as _yaml
    from unittest.mock import patch

    def _load(name):
        spec = importlib.util.spec_from_file_location(f"_jh_{name}", PROJECT_ROOT / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    init_mod = _load("init")
    doctor_mod = _load("doctor")
    from aggregator import settings as _settings

    def wizard(answers, preset=None):
        it = iter(answers)
        with patch.object(builtins, "input", lambda *_: next(it)), patch("sys.stdout", new=io.StringIO()):
            return _yaml.safe_load(init_mod.build_config(types.SimpleNamespace(yes=False, preset=preset)))

    # Defaults-only run produces a valid config that composes with its preset
    with patch("sys.stdout", new=io.StringIO()):
        dflt = _yaml.safe_load(init_mod.build_config(types.SimpleNamespace(yes=True, preset="devops")))
    assert dflt["preset"] == "devops" and dflt["candidate"]["cv_file_name"] == "Firstname_Lastname_CV.pdf"
    assert _settings.compose(dflt)["role"]["default_query"] == "DevOps Engineer"

    # A Polish frontend developer: EU removed from check regions, home = Poland + cities
    pl = wizard(["frontend", "Jan Kowalski", "Poland", "Warsaw, Krakow", "en", "1", "-2..3", "y"])
    assert pl["candidate"] == {"reply_language": "en", "timezone": "GMT+1", "timezone_window": [-2, 3],
                               "cv_file_name": "Jan_Kowalski_CV.pdf"}, pl["candidate"]
    assert pl["location"]["home_places"] == ["poland", "warsaw", "krakow"]
    assert "poland" not in pl["location"]["check_regions"] and "eu" not in pl["location"]["check_regions"]

    # A US data analyst: US regions are home, not locked; relocation off
    us = wizard(["data-analyst", "Jane Doe", "United States", "Austin", "en", "-6", "", "n"])
    assert us["candidate"]["timezone_window"] == [-9, -3] and us["location"]["open_to_relocation"] is False
    assert "us" in us["location"]["home_places"] and "us" not in us["location"]["locked_regions"]
    assert "canada" in us["location"]["locked_regions"]

    # Unknown preset is re-asked, then accepted
    again = wizard(["designer", "product-designer", "A B", "Georgia", "", "ka", "4", "", "y"])
    assert again["preset"] == "product-designer" and again["location"]["home_exclude"]
    mcp = init_mod.mcp_config()["mcpServers"]
    assert set(mcp) == {"playwright", "playwright-headless"} and "--headless" in str(mcp["playwright-headless"])
    print("  [+] init.py: wizard writes valid config.yml for QA/Georgia, frontend/Poland and analyst/US users; .mcp.json has both browsers.")

    # Doctor: placeholders, CV detection, JSON output
    tmpl = (PROJECT_ROOT / "Linkedin Agent" / "candidate-profile.template.md").read_text(encoding="utf-8")
    assert doctor_mod.placeholders(tmpl) > 10
    assert doctor_mod.placeholders((PROJECT_ROOT / "Job Hunter Agent" / "screening-playbook.template.md").read_text(encoding="utf-8")) > 5
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "cv.pdf").write_bytes(b"%PDF-1.4")
        doctor_mod.results.clear()
        doctor_mod.check_cv(f"## CV / Resume file rules\n- CV folder: `{tmp}`\n  - ATS: `cv.pdf`\n## Next")
        assert doctor_mod.results[-1]["status"] == "OK", doctor_mod.results
        doctor_mod.check_cv(f"## CV / Resume file rules\n- ALWAYS upload the CV from: `{tmp}/missing.pdf`\n")
        assert doctor_mod.results[-1]["status"] == "FAIL", doctor_mod.results
        doctor_mod.check_cv(tmpl)
        assert doctor_mod.results[-1]["status"] == "WARN", doctor_mod.results
    import subprocess
    out = subprocess.run([sys.executable, str(PROJECT_ROOT / "doctor.py"), "--json"], capture_output=True, text=True,
                         encoding="utf-8", cwd=PROJECT_ROOT)
    report = _json.loads(out.stdout)
    assert {"ok", "checks"} <= set(report) and any(c["check"] == "config.yml" for c in report["checks"])
    print(f"  [+] doctor.py: placeholder count, CV path detection (folder / absolute / template) and --json output verified.")
    print("  => ALL SETUP TESTS PASSED!")
except Exception as e:
    print(f"  ❌ FAILED in Setup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 ALL CHECKS PASSED: OLD AND NEW COMPONENTS FUNCTION FLAWLESSLY!")
print("=" * 60)

