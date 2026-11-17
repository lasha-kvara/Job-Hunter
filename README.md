# Job-Hunter

[![tests](https://github.com/lasha-kvara/Job-Hunter/actions/workflows/tests.yml/badge.svg)](https://github.com/lasha-kvara/Job-Hunter/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**An AI job-search assistant that finds vacancies for your profession, rates them against your
profile and applies to the ones you approve, from your own computer.**

[ქართული ვერსია → README.ka.md](README.ka.md)

Job-Hunter runs inside [Claude Code](https://claude.com/claude-code) (or as plain Python scripts
without any AI). You describe yourself once (profile, CV, where you can work); it then scans
company career pages and job boards, rates every vacancy 1–5, shows you a shortlist, fills in and
submits the applications you approve, and keeps a report. A second agent handles recruiter
messages on LinkedIn and interview scheduling.

- **Any profession.** 11 presets (QA, frontend, backend, full-stack, mobile, DevOps, data engineer,
  data analyst, ML, product designer, product manager), or your own.
- **Any country.** You set where you live and which regions you can work for; jobs you could never
  take (remote "US only", clearances, on-site abroad without relocation) are filtered out.
- **~200 company boards** read straight from Greenhouse, Ashby, Lever, SmartRecruiters and
  Recruitee, plus LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs and jobs.ge.
- **You stay in control.** Nothing is sent without your approval of the shortlist; passwords, 2FA
  codes, CAPTCHAs and online tests are always yours; the agent answers only from facts you wrote.
- **Private by default.** Your profile, CV, settings and history stay on your disk (git-ignored).

---

## How it works

```text
 profile + CV + config.yml
          │
          ▼
   search  ──►  rate 1–5 + flags  ──►  shortlist  ──►  YOU approve  ──►  apply in the browser  ──►  report
 (boards,        (skills, level,        (best first,     ("1, 3, 5")      (forms filled from your     (what was sent,
  job sites)      location, legitimacy)  one line each)                    profile; you do 2FA/CAPTCHA)  answers, CV)
```

| Verdict | Rating | Meaning |
|---|---|---|
| **Apply** | ≥ 4.0 | strong fit, no blockers |
| **Consider** | 3.5–3.9 | fits with gaps |
| **Research first** | 2.5–3.4 | unclear location, stack or legitimacy |
| **Skip** | < 2.5 or a blocker | not shown in the shortlist |

Blockers: remote limited to regions you can't work in, required work authorization or security
clearance, on-site abroad without relocation, or a job you already applied to. Old, reposted or
very vague postings lose points. Details: [scoring rules](.claude/skills/job-hunter-agent/references/scoring.md).

---

## Quick start

Requirements: **Python 3.10+**, **Git**, and **Node.js 18+** (for Claude Code's browser).

```bash
git clone https://github.com/lasha-kvara/Job-Hunter.git
cd Job-Hunter
python init.py
```

`init.py` creates `.venv`, installs the packages and Playwright Chromium, copies the personal
templates, asks 8 short questions (profession, name, country, cities, language, time zone, working
hours range, relocation) to write `config.yml`, writes `.mcp.json` for Claude Code, and ends with a
health check. It never overwrites a file you already have, so it is safe to run again.
Non-interactive: `python init.py --yes --preset frontend`.

Next, fill in your profile. Either edit the two files by hand:

- `Linkedin Agent/candidate-profile.md`: facts, experience, skills, salary, contacts, CV path
- `Job Hunter Agent/screening-playbook.md`: ready answers for application forms

or open the folder in Claude Code and say **"set up my profile"**: it reads your CV, asks only what
the CV can't tell (salary, work authorization, relocation, ...) and fills both files.

```bash
python doctor.py        # what is installed, what is still missing, and how to fix it
```

<details><summary>Manual setup (without init.py)</summary>

```bash
python -m venv .venv
.venv\Scripts\activate              # Linux / macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp config.example.yml config.yml    # then set preset, location and candidate
```
Copy each `*.template.md` next to itself without `.template`, and create `.mcp.json` as described
in [docs/claude-code.md](docs/claude-code.md). Optional: copy `.env.example` to `.env`.
</details>

---

## Using it with Claude Code

Open the folder in Claude Code, approve the two Playwright MCP servers once, and ask in your own
words (any language):

| You say | What happens |
|---|---|
| *"Find remote frontend jobs that fit me"* | search + rating, shortlist with numbers |
| *"Apply to 1, 3 and 5"* | fills and submits exactly those; asks you if a form needs an unknown fact |
| *"Check my LinkedIn messages"* | reads recruiter threads, drafts replies for your approval |
| *"Schedule the interview with Anna"* | proposes slots in your time zone, confirms only after you agree |
| *"Show my applications report"* | what was sent where, with answers and the CV used |

The agent asks once whether to use a visible (headed) or background (headless) browser; both share
one browser profile, so you sign in to LinkedIn and job sites only once. Setup details, prompts and
rules: [docs/claude-code.md](docs/claude-code.md).

**What the agent never does:** type passwords or 2FA codes, solve CAPTCHAs, take online tests or
assessments for you, invent experience, apply beyond the approved shortlist, or send a recruiter
message you haven't approved.

---

## Using it without AI (command line)

Search, rating and the LinkedIn pipeline also work as plain Python, no AI account needed.

```bash
python search_jobs.py --sources ats --hide-skip           # company boards only, ~30 s
python search_jobs.py --preset devops --min-rating 3.5    # another profession for one run
python search_jobs.py --query "Senior SDET" --no-remote --sources jobs_ge indeed
python search_jobs.py --list-presets
```

| Option | Default | Description |
|---|---|---|
| `--preset NAME` | from `config.yml` | profession preset for this run |
| `--query`, `-q` | preset's `default_query` | search keywords for job sites |
| `--sources`, `-s` | `search.sources` in config | `ats`, `indeed`, `linkedin`, `google`, `glassdoor`, `zip_recruiter`, `jobs_ge` |
| `--hide-skip` | off | drop Skip verdicts |
| `--min-rating` | 0 | drop jobs rated below this (1–5) |
| `--min-score` | 45 | drop jobs with keyword fit below this (0–100) |
| `--remote` / `--no-remote` | remote | remote-only, or include on-site / hybrid |
| `--location`, `-l` | `Remote` | location for job sites |
| `--country` | `USA` | Indeed country |
| `--limit`, `-n` | 10 | results per job site |
| `--hours` | 72 | job sites: posted in the last N hours |
| `--ats-days` | 0 (all) | company boards: posted in the last N days |
| `--export-md` | `search_results.md` | Markdown report path |

Output: a table in the terminal, `search_results.md`, and `Job Hunter Agent/jobs_feed.json`.

LinkedIn pipeline manager (terminal menu, optional Gemini key for AI drafts):

```bash
python "Linkedin Agent/run.py"
```

---

## Make it yours

| What | Where |
|---|---|
| Profession | `preset:` in `config.yml` → [presets/](presets/README.md) |
| Country, cities, regions you can / can't work for, time zone, language | `config.yml` → [docs/configuration.md](docs/configuration.md) |
| Facts about you | `Linkedin Agent/candidate-profile.md` |
| Answers to screening questions | `Job Hunter Agent/screening-playbook.md` |
| Companies to scan | `Job Hunter Agent/ats-boards.json` (shared) / `ats-boards.local.json` (yours) → [docs/job-sources.md](docs/job-sources.md) |

---

## Project layout

```text
init.py / doctor.py           setup wizard and health check
search_jobs.py                search + rating CLI
config.example.yml            all settings, documented (copy: config.yml, git-ignored)
presets/                      profession presets
CLAUDE.md, .claude/skills/    Claude Code rules and the two agents (job-hunter, linkedin)
Job Hunter Agent/
  aggregator/                 engine, sources (ATS boards, JobSpy, jobs.ge), scorer, assessment, settings
  ats-boards.json             company boards to scan
  *.template.md               report and screening-playbook templates
Linkedin Agent/               recruiter pipeline CLI, profile parser, reply drafts, templates
docs/                         configuration, Claude Code, job sources, privacy, troubleshooting
test_regression.py            test suite
```

---

## Privacy

Everything personal stays on your machine and is git-ignored: `config.yml`, `.mcp.json`, `.env`,
your profile, playbook, applications report, LinkedIn pipeline and search results. There is no
telemetry and no Job-Hunter server. Data leaves your computer only to the job sites you apply on,
and to the AI you choose (Claude Code; optionally Gemini for LinkedIn drafts). Automating job sites
may be against their terms of service; you are responsible for how you use this tool.
More: [docs/privacy.md](docs/privacy.md).

---

## Help, tests, contributing

- Something doesn't work: `python doctor.py`, then [docs/troubleshooting.md](docs/troubleshooting.md).
- Tests: `python test_regression.py`
- Contributions are welcome, especially presets, company boards and job sources:
  [CONTRIBUTING.md](CONTRIBUTING.md). Changes: [CHANGELOG.md](CHANGELOG.md).

The 1–5 rating, verdicts and legitimacy signals were inspired by
[career-ops](https://github.com/career-ops-hq/career-ops) (MIT).

## License

[MIT](LICENSE)
