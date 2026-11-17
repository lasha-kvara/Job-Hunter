# Contributing

Thanks for helping! The most useful contributions need no deep knowledge of the code:

| Contribution | Where | Effort |
|---|---|---|
| A company board that hires remotely | `Job Hunter Agent/ats-boards.json` | one line |
| A profession preset or better keywords | `presets/` | one file + sample titles in the test |
| A local job site (your country) | `Job Hunter Agent/aggregator/sources/` | a provider + mocked test |
| Docs, translations, troubleshooting entries | `docs/`, `README.*.md` | text |
| Bug fixes | anywhere | open an issue first if the change is large |

## Setup

```bash
git clone https://github.com/<you>/Job-Hunter.git && cd Job-Hunter
python init.py --yes
python test_regression.py
```

## Rules

- **Never commit personal data.** `config.yml`, profiles, playbooks, reports, pipelines, `.env`,
  `.mcp.json` and search results are git-ignored; keep it that way. No real names, phone numbers,
  e-mails or "companies I applied to" in tracked files, test fixtures or screenshots.
- **No network in tests.** Mock HTTP (see the ATS provider tests in `test_regression.py`).
- **Nothing hard-coded for one person, profession or country.** Put it in `config.example.yml` or a
  preset.
- **Agents stay honest.** Changes to `CLAUDE.md` or the skills must keep the core rules: facts only
  from the user's files, explicit approvals before sending, passwords / 2FA / CAPTCHAs / tests left
  to the user.
- Python 3.10+, standard library first; `init.py` must stay standard-library only.

## Adding a preset

1. Copy the closest file in `presets/` to `presets/<name>.yml` and edit `role`.
2. Check it against real titles: `python search_jobs.py --preset <name> --sources ats --min-score 0`.
3. Add "must keep / must drop" titles for it in section 3.10 of `test_regression.py` (the test fails
   if a preset has no samples) and a row in `presets/README.md`.

## Adding company boards

Add tokens to `ats-boards.json` (see [docs/job-sources.md](docs/job-sources.md)), run an `ats` search
and make sure they don't show up under "did not answer". Prefer companies that hire remotely or
across several countries.

## Pull requests

- One topic per PR, a clear title (`feat:`, `fix:`, `docs:`, `chore:`), and an entry under
  *Unreleased* in `CHANGELOG.md` for user-visible changes.
- `python test_regression.py` passes.
- Describe how you checked it (command and result).
