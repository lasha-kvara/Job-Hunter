# Job-Hunter (Claude Code)

Job search and application assistant for one candidate. Two skills do the work:
- `job-hunter-agent`: find vacancies, filter, apply in the browser, log to the report.
- `linkedin-agent`: recruiter conversations, interview scheduling, pipeline updates.

The browser is Playwright MCP (`.mcp.json`): `playwright` is headed, `playwright-headless` is
headless, both share one persistent profile. Pages are analysed live from snapshots; there are no
pre-written apply scripts.
- Small helper scripts (find fields, fill given values, click Next) are allowed for speed, but they
  do mechanics only: no candidate data, no answer tables, no regex-to-answer rules. Every value
  is chosen by you per field from the profile / playbook, or asked from the user.

## First run (onboarding)
Run `python doctor.py --json` (with the venv's Python) before the first search or application, and
whenever the user says "set up my profile". If `.venv` or packages are missing, tell the user to run
`python init.py` (or run it for them with their OK). If the profile or playbook still has template
placeholders, or `config.yml` is missing, interview the user, short and in batches:
1. Ask for their CV file (path). Read it and draft the profile's Summary, Experience, Skills,
   Education and Languages from it; facts come only from the CV and the user's answers.
2. Ask what the CV cannot tell: target roles (pick a preset from `presets/`), country and city,
   time zone, relocation, work authorization / sponsorship, notice period, minimum salary,
   per-skill years where the CV is vague, contact links, reply language.
3. Write `Linkedin Agent/candidate-profile.md` and `Job Hunter Agent/screening-playbook.md` (keep the
   templates' headings) and `config.yml` (only keys that differ from the example and preset).
4. Show a short summary for confirmation, fix what the user corrects, re-run `doctor.py`.

## Candidate data: zero hallucination
- Every candidate fact (name, contacts, experience, skills, salary, CV path, links) comes from
  `Linkedin Agent/candidate-profile.md` and `Job Hunter Agent/screening-playbook.md`.
- Never guess or invent a value. If a form or recruiter asks for something not in those files, ask
  the user.
- What to search for and where the candidate can work (role, title keywords, home country,
  allowed and locked regions, time zone, reply language, CV file name) comes from `config.yml`
  (defaults and documentation: `config.example.yml`; the profession comes from
  `presets/<preset>.yml`, see `presets/README.md`).
- These files, `config.yml` and the reports are personal and git-ignored. Never commit them or
  copy their contents (names, phone numbers, emails, companies applied to) into tracked files.

## Approvals
- Applications: the user approves a numbered shortlist once; then fill and submit exactly the
  approved items without asking again per job. Never expand beyond them.
- LinkedIn: send a message or confirm an interview slot only after the user approves it.
- Passwords, 2FA/OTP codes, CAPTCHAs and account sign-ups are done by the user in the headed
  window. Pause, say what is needed, continue when they confirm.

## Browser rules
- Work from `browser_snapshot`; avoid screenshots and full-page dumps to save tokens.
- Upload files with `browser_file_upload`, never by clicking an OS file dialog.
- Check `Job Hunter Agent/job-applications-report.md` and `Linkedin Agent/linkedin-pipeline.md`
  before applying, to avoid duplicates.

## Reporting
- Reply to the user in `candidate.reply_language` from `config.yml` (if unset, in the language the
  user writes in). Status reports are ≤ 5 bullets.

## Code
- Python 3.10+. Use the project venv: `.venv/Scripts/python.exe` on Windows.
- Tests: `.venv/Scripts/python.exe test_regression.py`.
- Aggregator CLI: `python search_jobs.py --help`.
