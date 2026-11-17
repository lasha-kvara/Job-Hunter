# Privacy and safety

## What stays on your computer

These files are personal and git-ignored; they are never committed or uploaded by Git:

| File | Contains |
|---|---|
| `config.yml` | profession, country, time zone, CV file name |
| `Linkedin Agent/candidate-profile.md` | your facts, contacts, salary, CV path |
| `Job Hunter Agent/screening-playbook.md` | your answers to screening questions |
| `Job Hunter Agent/job-applications-report.md` | every application: company, answers, salary stated |
| `Linkedin Agent/linkedin-pipeline.md` | recruiter conversations and interview stages |
| `Job Hunter Agent/ats-boards.local.json` | companies you added (often ones you applied to) |
| `search_results.md`, `Job Hunter Agent/jobs_feed.json`, `seen_jobs.json` | search results and history |
| `.env`, `.mcp.json`, `.playwright-mcp/` | API keys, machine paths, browser snapshots |

Your logins live in the browser profile `~/.playwright-job-hunter` (outside the repository).
Delete that folder to sign out everywhere.

Before you push a fork, `git status` should show none of the files above. The agent's rules forbid
copying their contents (names, phone numbers, companies) into tracked files.

## What leaves your computer

- **Job sites and company boards** you search and apply on: their normal traffic, plus what you
  submit in forms.
- **Your AI provider**: Claude Code sends the files and pages it reads to Anthropic to do the work.
  The optional Gemini key in `.env` sends LinkedIn drafting prompts to Google.
- Nothing else: no telemetry, no analytics, no Job-Hunter server.

## Safety rules built into the agents

- Applications are sent only for the shortlist items you approve; recruiter messages and interview
  confirmations only after you approve each one.
- Passwords, 2FA / OTP codes, CAPTCHAs, account sign-ups and online assessments are always done by
  you. The agent pauses and tells you what is needed.
- Answers come only from your profile and playbook; unknown facts are asked, never guessed.
- Files are uploaded with the browser tool, never through an operating-system dialog.

## Terms of service

Automating job sites (especially LinkedIn) may violate their terms and can get an account
restricted. Keep volumes human (the LinkedIn agent paces itself: see
`.claude/skills/linkedin-agent/references/pacing-rules.md`), review what is sent, and use the tool
at your own responsibility.
