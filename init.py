#!/usr/bin/env python3
"""Job-Hunter setup: one command from a fresh clone to a working install.

    python init.py              # interactive
    python init.py --yes        # accept defaults (CI / re-runs)

Steps (each one skips itself when already done, nothing personal is ever overwritten):
  1. check Python >= 3.10           5. config.yml from a few questions (profession, country, ...)
  2. create .venv                   6. .mcp.json for Claude Code (Playwright MCP, headed + headless)
  3. install requirements.txt       7. .env from .env.example
  4. install Playwright Chromium    8. run doctor.py
  + copy the personal templates (profile, playbook, report, pipeline) to their git-ignored names

Only the standard library is used here, because this runs before the dependencies exist.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WIN = platform.system() == "Windows"
VENV = ROOT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")

TEMPLATES = [
    ("Linkedin Agent/candidate-profile.template.md", "Linkedin Agent/candidate-profile.md"),
    ("Linkedin Agent/linkedin-pipeline.template.md", "Linkedin Agent/linkedin-pipeline.md"),
    ("Job Hunter Agent/job-applications-report.template.md", "Job Hunter Agent/job-applications-report.md"),
    ("Job Hunter Agent/screening-playbook.template.md", "Job Hunter Agent/screening-playbook.md"),
]

# Countries whose people usually also need these regions removed from "locked" (they live there).
REGION_OF = {
    "united states": ["us", "usa", "u.s.", "u.s.a.", "united states", "north america", "americas", "san francisco",
                      "bay area", "new york", "nyc", "seattle", "austin", "boston", "chicago", "los angeles", "denver"],
    "canada": ["canada", "north america", "americas", "toronto", "vancouver", "montreal"],
    "india": ["india", "apac", "apj"],
    "brazil": ["brazil", "latam", "latin america", "americas"],
    "mexico": ["mexico", "latam", "latin america", "americas", "north america"],
    "argentina": ["argentina", "latam", "latin america", "americas"],
    "australia": ["australia", "apac", "apj"],
}


EU = {"austria", "belgium", "bulgaria", "croatia", "cyprus", "czechia", "czech republic", "denmark", "estonia",
      "finland", "france", "germany", "greece", "hungary", "ireland", "italy", "latvia", "lithuania", "luxembourg",
      "malta", "netherlands", "poland", "portugal", "romania", "slovakia", "slovenia", "spain", "sweden"}


def say(msg: str = "") -> None:
    print(msg, flush=True)


def step(n: int, title: str) -> None:
    say(f"\n[{n}/8] {title}")


def run(cmd, **kw) -> bool:
    say("      $ " + " ".join(str(c) for c in cmd))
    return subprocess.call([str(c) for c in cmd], cwd=ROOT, **kw) == 0


def ask(question: str, default: str, assume_yes: bool) -> str:
    if assume_yes:
        return default
    try:
        answer = input(f"      {question} [{default}]: ").strip()
    except EOFError:
        return default
    return answer or default


def yes_no(question: str, default: bool, assume_yes: bool) -> bool:
    answer = ask(question + " (y/n)", "y" if default else "n", assume_yes).lower()
    return answer.startswith("y")


def presets() -> list:
    return sorted(p.stem for p in (ROOT / "presets").glob("*.yml"))


def parse_window(text: str, fallback):
    try:
        lo, hi = [int(x) for x in text.replace(" ", "").split("..")]
        return [min(lo, hi), max(lo, hi)]
    except ValueError:
        return fallback


def load_example_list(key: str) -> list:
    """Reads a location.<key> flow list from config.example.yml without PyYAML (may wrap lines)."""
    text = (ROOT / "config.example.yml").read_text(encoding="utf-8")
    start = text.index(f"{key}:")
    body = text[text.index("[", start) + 1: text.index("]", start)]
    return [w.strip().strip('"') for w in body.replace("\n", " ").split(",") if w.strip()]


def build_config(args) -> str:
    y = args.yes
    names = presets()
    say("      Professions: " + ", ".join(names))
    preset = args.preset or ask("Your profession (preset)", "qa-automation", y)
    while preset not in names:
        if y:
            raise SystemExit(f"Unknown preset '{preset}'. Choose one of: {', '.join(names)}")
        preset = ask(f"Unknown preset. Choose one of {', '.join(names)}", "qa-automation", y)

    full_name = ask("Your full name (used for the CV file name)", "Firstname Lastname", y)
    cv_name = "_".join(full_name.split()) + "_CV.pdf"
    country = ask("Country you live in", "Georgia", y)
    cities = ask("Cities in that country to treat as home (comma separated)", "", y)
    language = ask("Language the agents should talk to you in (en, ka, de, uk, ...)", "en", y)
    tz = ask("Your UTC offset, e.g. 4 for GMT+4, -5 for GMT-5", "0", y)
    try:
        tz_n = int(float(tz))
    except ValueError:
        tz_n = 0
    window = parse_window(ask("UTC offsets you can work with (from..to)", f"{tz_n - 3}..{tz_n + 3}", y),
                          [tz_n - 3, tz_n + 3])
    relocate = yes_no("Open to relocation if the employer offers it?", True, y)

    home = [w.strip().lower() for w in [country] + cities.split(",") if w.strip()]
    home += {"united states": ["us", "usa", "u.s.", "u.s.a."], "united kingdom": ["uk", "england"]}.get(country.lower(), [])
    lines = [
        "# Personal settings (git-ignored), written by init.py. Only keys that differ from",
        "# config.example.yml + your preset are needed; edit freely. Docs: config.example.yml, presets/README.md",
        f"preset: {preset}",
        "",
        "candidate:",
        f"  reply_language: {language}",
        f'  timezone: "GMT{tz_n:+d}"',
        f"  timezone_window: {json.dumps(window)}",
        f'  cv_file_name: "{cv_name}"',
        "",
        "location:",
        f"  home_country: {json.dumps(country)}",
        f"  home_places: {json.dumps(home, ensure_ascii=False)}",
        f"  home_exclude: {json.dumps(['georgia, usa', 'georgia, us', 'atlanta'] if country.lower() == 'georgia' else [])}",
        f"  open_to_relocation: {'true' if relocate else 'false'}",
    ]
    # The example lists assume someone outside the US / EU; drop the places this user lives in.
    lived_in = set(REGION_OF.get(country.lower(), [])) | set(home)
    if country.lower() in EU:
        lived_in |= {"eu", "european union"}
    if country.lower() in ("united kingdom", "uk", "england", "scotland", "wales"):
        lived_in |= {"uk", "united kingdom", "england", "london"}
    for key in ("locked_regions", "check_regions"):
        example = load_example_list(key)
        if lived_in & set(example):
            lines.append(f"  # Regions you live in are removed from the example's {key}.")
            lines.append(f"  {key}: {json.dumps([w for w in example if w not in lived_in])}")
    return "\n".join(lines) + "\n"


def mcp_config() -> dict:
    profile = "${USERPROFILE}\\.playwright-job-hunter" if IS_WIN else "${HOME}/.playwright-job-hunter"
    base = ["-y", "@playwright/mcp@0.0.83", "--user-data-dir", profile, "--allow-unrestricted-file-access"]

    def server(headless: bool) -> dict:
        args = base[:2] + (["--headless"] if headless else []) + base[2:]
        return {"command": "cmd", "args": ["/c", "npx"] + args} if IS_WIN else {"command": "npx", "args": args}

    return {"mcpServers": {"playwright": server(False), "playwright-headless": server(True)}}


def main() -> int:
    ap = argparse.ArgumentParser(description="Set up Job-Hunter in this folder.")
    ap.add_argument("--yes", "-y", action="store_true", help="accept all defaults, no questions")
    ap.add_argument("--preset", help="profession preset for config.yml (see presets/)")
    ap.add_argument("--no-venv", action="store_true", help="use the current Python instead of .venv")
    ap.add_argument("--no-install", action="store_true", help="skip pip install")
    ap.add_argument("--no-browser", action="store_true", help="skip the Playwright Chromium download")
    ap.add_argument("--force-config", action="store_true", help="rewrite config.yml (keeps a .bak copy)")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy code page
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    say("Job-Hunter setup")
    step(1, "Python version")
    if sys.version_info < (3, 10):
        say(f"      ✗ Python {platform.python_version()} found; 3.10 or newer is required.")
        return 1
    say(f"      ✓ Python {platform.python_version()}")

    step(2, "Virtual environment (.venv)")
    py = Path(sys.executable)
    if args.no_venv:
        say("      skipped (--no-venv): using " + str(py))
    elif VENV_PY.exists():
        py = VENV_PY
        say("      ✓ .venv already exists")
    else:
        if not run([sys.executable, "-m", "venv", str(VENV)]):
            say("      ✗ could not create .venv")
            return 1
        py = VENV_PY
        say("      ✓ created .venv")

    step(3, "Python packages")
    if args.no_install:
        say("      skipped (--no-install)")
    elif not run([py, "-m", "pip", "install", "-q", "-r", "requirements.txt"]):
        say("      ✗ pip install failed; fix the error above and run init.py again")
        return 1
    else:
        say("      ✓ requirements installed")

    step(4, "Playwright Chromium (CV PDFs, live checks, headed apply demo)")
    if args.no_browser or args.no_install:
        say("      skipped")
    elif run([py, "-m", "playwright", "install", "chromium"]):
        say("      ✓ Chromium ready")
    else:
        say("      ! Chromium download failed; searching still works. Retry: python -m playwright install chromium")

    say("\n      Personal files (git-ignored):")
    for src, dst in TEMPLATES:
        target = ROOT / dst
        if target.exists():
            say(f"      ✓ {dst} (kept)")
        else:
            shutil.copyfile(ROOT / src, target)
            say(f"      + {dst} (from template: fill it in)")

    step(5, "config.yml (profession, country, language)")
    cfg = ROOT / "config.yml"
    if cfg.exists() and not args.force_config:
        say("      ✓ config.yml exists (kept; --force-config to rewrite)")
    else:
        if cfg.exists():
            shutil.copyfile(cfg, cfg.with_suffix(".yml.bak"))
            say("      saved the old one as config.yml.bak")
        cfg.write_text(build_config(args), encoding="utf-8")
        say("      ✓ wrote config.yml")

    step(6, "Claude Code browser (.mcp.json for Playwright MCP)")
    mcp = ROOT / ".mcp.json"
    if mcp.exists():
        say("      ✓ .mcp.json exists (kept)")
    else:
        mcp.write_text(json.dumps(mcp_config(), indent=2) + "\n", encoding="utf-8")
        say("      ✓ wrote .mcp.json (headed + headless, one shared browser profile)")
    if not shutil.which("npx"):
        say("      ! Node.js (npx) not found: install Node.js 18+ to use the browser from Claude Code")

    step(7, ".env (optional API keys and ports)")
    env = ROOT / ".env"
    if env.exists():
        say("      ✓ .env exists (kept)")
    else:
        shutil.copyfile(ROOT / ".env.example", env)
        say("      + .env from .env.example (all keys optional)")

    step(8, "Health check (doctor.py)")
    ok = run([py, "doctor.py"])

    activate = r".venv\Scripts\activate" if IS_WIN else "source .venv/bin/activate"
    say("\nNext steps:")
    say("  1. Fill in Linkedin Agent/candidate-profile.md and Job Hunter Agent/screening-playbook.md")
    say("     (or open Claude Code here and say: \"set up my profile\" — it interviews you and fills them).")
    say(f"  2. {activate}  then  python search_jobs.py --sources ats")
    say("  3. Re-check any time with: python doctor.py")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
