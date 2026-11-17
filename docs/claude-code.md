# Using Job-Hunter with Claude Code

Job-Hunter's agents are two Claude Code skills plus a rules file:

| File | Role |
|---|---|
| `CLAUDE.md` | workspace rules: zero hallucination, approvals, browser rules, reply language, onboarding |
| `.claude/skills/job-hunter-agent/` | search, rate, shortlist, apply, report |
| `.claude/skills/linkedin-agent/` | recruiter messages, interview scheduling, pipeline |
| `.mcp.json` | the browser: [Playwright MCP](https://github.com/microsoft/playwright-mcp) |

## Setup

1. `python init.py` (writes `.mcp.json`; needs Node.js 18+ for `npx`).
2. Open the folder in Claude Code and approve the `playwright` and `playwright-headless` servers.
3. Say **"set up my profile"** the first time. The agent runs `doctor.py`, reads your CV and asks the
   rest (see *First run* in `CLAUDE.md`).

`.mcp.json` written by `init.py` on Windows (on Linux / macOS `"command": "npx"` without `"/c"`, and
`${HOME}/.playwright-job-hunter`):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@playwright/mcp@0.0.83",
               "--user-data-dir", "${USERPROFILE}\\.playwright-job-hunter",
               "--allow-unrestricted-file-access"]
    },
    "playwright-headless": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@playwright/mcp@0.0.83", "--headless",
               "--user-data-dir", "${USERPROFILE}\\.playwright-job-hunter",
               "--allow-unrestricted-file-access"]
    }
  }
}
```

Both servers use one browser profile outside the repository, so a login done in the visible window
is reused in the background one. Run only one of them at a time. `--allow-unrestricted-file-access`
lets the browser upload a CV stored outside the repository.

## A typical session

1. *"Find remote backend jobs for me"* → the agent asks **headed or headless**, runs the search,
   rates each job and shows a numbered shortlist:
   `3. Acme · Senior Backend Engineer · Remote EMEA · 4.4/5 Apply · Greenhouse · ⚑ stale`
2. *"Apply to 1, 3, 4"* → this is the approval. It fills and submits exactly those forms, without
   asking again per job. It stops and asks when a form needs a fact that is not in your profile or
   playbook, wants an account, a password, a payment or a test, or the page differs from the shortlist.
3. 2FA, e-mail codes, CAPTCHAs: the agent pauses and tells you; you act in the headed window and say
   "done".
4. Every processed job is logged to `Job Hunter Agent/job-applications-report.md` (status, answers,
   salary stated, CV used). The final report is at most 5 bullets in your `reply_language`.

## Rules the agents follow

- **Facts only from your files.** Name, contacts, years per skill, salary, links: from
  `candidate-profile.md` and `screening-playbook.md`. Anything else: they ask you.
- **Approvals.** Applications: one approval per shortlist. LinkedIn: every message and every
  interview confirmation is approved by you first.
- **Yours only:** passwords, 2FA / OTP codes, CAPTCHAs, account sign-ups, online assessments.
- **No duplicates:** the report and pipeline are checked before applying.
- **Remote means remote:** for foreign jobs the work mode is verified on the job page itself
  (search filters, LinkedIn's included, are not trusted).
- **CVs:** external forms get a CV tailored to the vacancy (reordered and reworded from your master
  CV, never new facts); LinkedIn Easy Apply keeps the CV already stored on LinkedIn.
- **Salary** is converted to the currency and period a form asks for at today's rate, rounded up.

## Prompts that work well

- "Search company boards only and show Apply / Consider jobs."
- "Search as a `devops` preset this time."
- "Apply to all Apply-rated jobs from the last shortlist." (approval for those items)
- "Draft replies to new recruiters but don't send anything."
- "What did I answer about salary at Acme?"
- "Add these companies to my boards: jobs.ashbyhq.com/acme, boards.greenhouse.io/foo."
