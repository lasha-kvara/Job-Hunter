# LinkedIn Agent

Manages recruiter conversations: reads LinkedIn messages, drafts replies grounded in your profile,
proposes and confirms interview times, and keeps the opportunity pipeline up to date.

Two ways to use it:

- **Claude Code** (recommended): the `linkedin-agent` skill in `.claude/skills/linkedin-agent/`.
  Say *"check my LinkedIn messages"* or *"reply to Anna"*; every message and every interview
  confirmation is shown to you and sent only after you approve it. See
  [docs/claude-code.md](../docs/claude-code.md).
- **Terminal CLI** (no AI needed): `run.py`, described below.

## Files

| File | Purpose |
|---|---|
| `candidate-profile.md` | your facts: the only source for replies (template: `candidate-profile.template.md`) |
| `linkedin-pipeline.md` | opportunities and their status (template: `linkedin-pipeline.template.md`) |
| `linkedin-agent.md` | full behaviour rules for the agent |
| `config.py` | paths, CDP port, pacing limits, optional Gemini settings (from `.env`) |
| `run.py` | interactive CLI and shortcuts |
| `start_browser.bat` | Windows: start Chrome / Brave with remote debugging on `CDP_PORT` |
| `src/` | profile parser, pipeline tracker, reply generator, scheduler, browser controller |

The personal files are created by `python init.py` and are git-ignored.

## Terminal CLI

```bash
python "Linkedin Agent/run.py"                       # interactive menu
python "Linkedin Agent/run.py" --status              # pipeline summary (≤ 5 bullets)
python "Linkedin Agent/run.py" --draft "Hi, what is your salary expectation?" --name "Jane"
python "Linkedin Agent/run.py" --check-browser       # unread LinkedIn messages via your browser
```

Menu: check messages · draft a reply · propose / confirm interview times · update a pipeline
status · show candidate facts · start the browser in debug mode.

### Reading messages from your own browser (CDP)

`--check-browser` and menu item 1 attach to a Chrome / Brave you are already logged in to, so the
agent never sees your password:

```bash
# Windows
"Linkedin Agent\start_browser.bat"

# Linux / macOS
google-chrome --remote-debugging-port="${CDP_PORT:-9222}" --user-data-dir="$HOME/.linkedin-agent-profile"
```

### AI drafts (optional)

Replies are built from templates and your profile. For AI-written drafts:

```bash
pip install -r requirements-optional.txt
```

and set `GEMINI_API_KEY` in `.env` (model: `LINKEDIN_AGENT_MODEL`, default `gemini-2.5-flash`).
Drafts that mention salary or a meeting time are always marked as needing your approval.

## Rules

- Facts only from `candidate-profile.md`; anything missing is asked, never invented.
- Salary is stated only when a recruiter asks; interview slots are confirmed only by you.
- Replies are written in the recruiter's language (English and Georgian templates included).
- Human pacing: at most 5 conversations per session, waits between steps, character-by-character
  typing (`config.py`, `.claude/skills/linkedin-agent/references/pacing-rules.md`).
- Passwords, 2FA codes and CAPTCHAs are always yours: the agent stops and tells you.
