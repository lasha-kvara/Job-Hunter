# Troubleshooting

Start with `python doctor.py` (add `--online` to test the job-board APIs). Every warning or failure
comes with the command or file that fixes it.

| Problem | Fix |
|---|---|
| `python` not found / wrong version | Install Python 3.10+; on Windows tick "Add to PATH", or use `py init.py`. |
| `ModuleNotFoundError` (yaml, jobspy, ...) | Activate the venv (`.venv\Scripts\activate` / `source .venv/bin/activate`) or `pip install -r requirements.txt`. |
| Chromium download fails | `python -m playwright install chromium`; behind a proxy set `HTTPS_PROXY`. Searching works without it. |
| `npx` not found / MCP servers don't start | Install Node.js 18+, restart the terminal and Claude Code. |
| `Unknown preset 'x'` | `python search_jobs.py --list-presets`, fix `preset:` in `config.yml`. |
| Broken `config.yml` | `python doctor.py` shows the YAML error; or `python init.py --force-config` (keeps a `.bak`). |
| SSL / certificate errors on corporate networks | `truststore` uses the system certificate store; make sure it is installed (`pip install truststore`). |
| "ATS boards that did not answer: x" | The company moved or closed its board; remove the token or fix it ([job-sources.md](job-sources.md)). |
| Search finds nothing | `--min-score 0` and no `--hide-skip` to see what is filtered and why (Flags column); check `title_keywords` of your preset. |
| Too many "region-locked" Skips | Your `locked_regions` may include where you live; see [configuration.md](configuration.md). |
| Windows: "running scripts is disabled on this system" when activating `.venv` | Run once in PowerShell: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` (answer `Y`), or use Command Prompt with `.venv\Scripts\activate.bat`, or call `.venv\Scripts\python.exe` directly. |
| Garbled ✓ / characters in the Windows console | Run in Windows Terminal, or `set PYTHONIOENCODING=utf-8`. |
| LinkedIn shows Hybrid / On-site jobs under "Remote" | Known: LinkedIn ignores its own filter. The agent checks each job page; trust the verdict, not the filter. |
| A site asks for a login, code or CAPTCHA | Do it yourself in the headed browser window, then tell the agent "done". |
| The agent asks something about you | The fact is missing from your profile / playbook. Answer, and add it there so it is not asked again. |
| Tests fail | `python test_regression.py` prints the failing check; tests never use your personal files or the network. |

Still stuck? Open an issue with the `doctor.py --json` output (remove anything personal first).
