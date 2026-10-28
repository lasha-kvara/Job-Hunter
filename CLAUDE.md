# Job-Hunter (Claude Code)

Job search and application assistant for one candidate. Two skills do the work:
- `job-hunter-agent`: find vacancies, filter, apply in the browser, log to the report.
- `linkedin-agent`: recruiter conversations, interview scheduling, pipeline updates.

The browser is Playwright MCP (`.mcp.json`): `playwright` is headed, `playwright-headless` is
headless, both share one persistent profile. Pages are analysed live from snapshots; there are no
pre-written apply scripts.

## Candidate data: zero hallucination
- Every candidate fact (name, contacts, experience, skills, salary, CV path, links) comes from
  `Linkedin Agent/candidate-profile.md` and `Job Hunter Agent/screening-playbook.md`.
- Never guess or invent a value. If a form or recruiter asks for something not in those files, ask
  the user.
- These files and the reports are personal and git-ignored. Never commit them or copy their
  contents into tracked files.

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
- Reply to the user in Georgian. Status reports are ≤ 5 bullets.

## Code
- Python 3.10+. Use the project venv: `.venv/Scripts/python.exe` on Windows.
- Tests: `.venv/Scripts/python.exe test_regression.py`.
- Aggregator CLI: `python search_jobs.py --help`.
