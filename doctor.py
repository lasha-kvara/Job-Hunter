#!/usr/bin/env python3
"""Job-Hunter health check: is everything installed and filled in?

    python doctor.py            # local checks
    python doctor.py --online   # also checks that job-board APIs are reachable
    python doctor.py --json     # machine-readable result

Each check prints OK, WARN (works, but something is missing) or FAIL (will not work), with the
command or file that fixes it. Exit code 1 when any check FAILs. Read-only: changes nothing.
"""
import argparse
import importlib
import json
import os
import platform
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Job Hunter Agent"))

OK, WARN, FAIL = "OK", "WARN", "FAIL"
results = []


def check(name: str, status: str, detail: str = "", fix: str = "") -> None:
    results.append({"check": name, "status": status, "detail": detail, "fix": fix})


def placeholders(text: str) -> int:
    """Count unfilled template placeholders such as [Full Name] or [e.g. Python]."""
    return len(re.findall(r"\[(?:e\.g\.[^\]]*|Your [^\]]*|Full Name|Amount|Year|Role|Company|City, Country|Country"
                          r"|Code|N|Answer|Language[^\]]*|University Name|Years|Degree[^\]]*)\]", text))


def check_python() -> None:
    v = platform.python_version()
    if sys.version_info < (3, 10):
        check("Python", FAIL, v, "install Python 3.10 or newer")
    else:
        in_venv = sys.prefix != sys.base_prefix
        check("Python", OK if in_venv else WARN, v + (" in .venv" if in_venv else " (not in a virtual environment)"),
              "" if in_venv else r"activate it: .venv\Scripts\activate (Windows) / source .venv/bin/activate")


def check_packages() -> None:
    required = {"requests": "requests", "bs4": "beautifulsoup4", "yaml": "pyyaml", "rich": "rich",
                "truststore": "truststore", "pandas": "pandas", "jobspy": "python-jobspy", "playwright": "playwright"}
    missing = []
    for mod, pkg in required.items():
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(pkg)
    if missing:
        check("Python packages", FAIL, "missing: " + ", ".join(missing), "pip install -r requirements.txt")
    else:
        check("Python packages", OK, f"{len(required)} required packages import")


def check_chromium() -> None:
    """Asks Playwright for the exact browser build it needs (a different revision on disk is not enough)."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:  # a real headless launch: the only reliable test (headless uses its own shell build)
                p.chromium.launch().close()
                found, detail = True, "launches"
            except Exception:
                found, detail = False, "missing for this Playwright version"
    except Exception as e:  # playwright not installed: reported by the package check
        found, detail = False, f"cannot check ({e.__class__.__name__})"
    check("Playwright Chromium", OK if found else WARN,
          detail if found else detail + " (needed for CV PDFs, not for searching)",
          "" if found else "python -m playwright install chromium")


def check_config() -> None:
    try:
        from aggregator import settings
        s = settings.get()
    except ModuleNotFoundError as e:
        check("config.yml", FAIL, f"cannot load settings: {e}", "pip install -r requirements.txt")
        return
    except Exception as e:  # broken YAML, unknown preset
        check("config.yml", FAIL, str(e), "fix config.yml (see config.example.yml)")
        return
    user = ROOT / "config.yml"
    detail = (f"preset {s.get('preset')}, home {s.get('location', {}).get('home_country')}, "
              f"replies in {s.get('candidate', {}).get('reply_language')}")
    if user.exists():
        check("config.yml", OK, detail)
    else:
        check("config.yml", WARN, "missing; using the example values (" + detail + ")", "python init.py")
    cv = s.get("candidate", {}).get("cv_file_name", "")
    if cv.startswith("Firstname"):
        check("CV file name", WARN, cv, "set candidate.cv_file_name in config.yml")


def check_master_cv() -> None:
    """The master CV that cv_tools.py tailors (config.yml: cv.dir / cv.master)."""
    try:
        sys.path.insert(0, str(ROOT))
        import cv_tools
        cv = cv_tools.cv_settings()
        master = cv["dir"] / cv["master"]
        if not master.exists():
            check("Master CV", WARN, f"{master} missing (needed for tailored CVs)",
                  "copy cv/master.example.html there, or set cv.dir in config.yml")
            return
        html = master.read_text(encoding="utf-8", errors="replace")
        data = cv_tools.extract(html)
        if "Jane Doe" in html or "JANE<br>" in html:
            check("Master CV", WARN, f"{master.name} is still the example (Jane Doe)", "replace it with your own CV")
        elif not data["name"] or not data["experience"]:
            check("Master CV", FAIL, f"{master}: no name or work experience found",
                  "use the class names of cv/master.example.html")
        else:
            check("Master CV", OK, f"{data['name']}: {len(data['experience'])} jobs, "
                  f"{sum(len(g['items']) for g in data['skills'])} skills ({master.parent})")
    except ModuleNotFoundError as e:
        check("Master CV", WARN, f"cannot check: {e}", "pip install -r requirements.txt")


def check_personal_files() -> None:
    files = {
        "Candidate profile": "Linkedin Agent/candidate-profile.md",
        "Screening playbook": "Job Hunter Agent/screening-playbook.md",
        "Applications report": "Job Hunter Agent/job-applications-report.md",
        "LinkedIn pipeline": "Linkedin Agent/linkedin-pipeline.md",
    }
    for name, rel in files.items():
        path = ROOT / rel
        if not path.exists():
            check(name, FAIL if "profile" in rel else WARN, f"{rel} missing", "python init.py")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        left = placeholders(text) if name in ("Candidate profile", "Screening playbook") else 0
        if left:
            check(name, WARN, f"{rel}: {left} template placeholders still to fill",
                  "fill it in, or ask Claude Code: \"set up my profile\"")
        else:
            check(name, OK, rel)
        if name == "Candidate profile":
            check_cv(text)


def check_cv(profile: str) -> None:
    """Finds CV files named in the profile's "CV / Resume file rules" section and checks they exist.
    Accepts absolute paths, or file names relative to a `CV folder: <path>` line."""
    sec = re.search(r"##\s*CV[^\n]*\n(.*?)(?=\n##\s|\Z)", profile, re.S | re.I)
    body = sec.group(1) if sec else ""
    expand = lambda p: Path(os.path.expandvars(os.path.expanduser(p.strip())))
    folder = re.search(r"CV folder:\s*`([^`]+)`", body, re.I)
    base = expand(folder.group(1)) if folder else None
    files = [p for p in re.findall(r"`([^`]+\.(?:pdf|docx?))`", body, re.I) if not p.startswith("path/to")]
    if not files:
        check("CV file", WARN, "no CV path in the profile", "add it under '## CV / Resume file rules'")
        return
    resolved = [expand(p) if expand(p).is_absolute() or not base else base / p for p in files]
    missing = [str(p) for p in resolved if not p.exists()]
    if missing:
        check("CV file", FAIL, "not found: " + "; ".join(missing), "fix the path in candidate-profile.md")
    else:
        check("CV file", OK, f"{len(resolved)} CV file(s) found" + (f" in {base}" if base else ""))


def check_claude_code() -> None:
    mcp = ROOT / ".mcp.json"
    if not mcp.exists():
        check("Claude Code browser", WARN, ".mcp.json missing (only needed for Claude Code)", "python init.py")
    else:
        try:
            servers = json.loads(mcp.read_text(encoding="utf-8")).get("mcpServers", {})
            ok = {"playwright", "playwright-headless"} <= set(servers)
            check("Claude Code browser", OK if ok else WARN, ".mcp.json: " + ", ".join(servers) or "no servers",
                  "" if ok else "delete .mcp.json and run python init.py")
        except json.JSONDecodeError as e:
            check("Claude Code browser", FAIL, f".mcp.json is not valid JSON: {e}", "delete it and run python init.py")
    npx = shutil.which("npx")
    check("Node.js (npx)", OK if npx else WARN, npx or "not found (Claude Code's browser runs through npx)",
          "" if npx else "install Node.js 18+ from nodejs.org")


def check_online() -> None:
    try:
        import requests
        try:
            import truststore
            truststore.inject_into_ssl()
        except ImportError:
            pass
        r = requests.get("https://boards-api.greenhouse.io/v1/boards/gitlab/jobs", timeout=15)
        check("Job-board APIs", OK if r.ok else WARN, f"Greenhouse answered {r.status_code}")
    except Exception as e:
        check("Job-board APIs", WARN, f"not reachable: {e.__class__.__name__}", "check the network / proxy / SSL")


def main() -> int:
    ap = argparse.ArgumentParser(description="Check the Job-Hunter installation.")
    ap.add_argument("--online", action="store_true", help="also call a job-board API")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args()
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    check_python()
    check_packages()
    check_chromium()
    check_config()
    check_personal_files()
    check_master_cv()
    check_claude_code()
    if args.online:
        check_online()

    failed = any(r["status"] == FAIL for r in results)
    if args.json:
        print(json.dumps({"ok": not failed, "checks": results}, indent=2, ensure_ascii=False))
        return 1 if failed else 0
    icon = {OK: "✓", WARN: "!", FAIL: "✗"}
    for r in results:
        print(f"  {icon[r['status']]} {r['check']:22} {r['detail']}")
        if r["fix"] and r["status"] != OK:
            print(f"    {'':22} → {r['fix']}")
    warns = sum(r["status"] == WARN for r in results)
    print("\n" + ("✗ Some checks failed." if failed else "✓ Ready." + (f" ({warns} optional items)" if warns else "")))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
