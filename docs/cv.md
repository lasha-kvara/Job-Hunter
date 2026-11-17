# Your CV: master, tailored copies, designed and ATS PDFs

Job-Hunter keeps **one master CV** (HTML) and builds a **tailored copy per vacancy** from it: same
facts, reordered and reworded for the job, in two PDFs:

| PDF | Looks like | Used for |
|---|---|---|
| **Designed** | two columns, photo, colours (the master's own design) | e-mail applications, recruiters, referrals |
| **ATS** | one column, A4, no photo, plain text, fitted to 2 pages | every online form and ATS |

LinkedIn Easy Apply uses the CV already stored on LinkedIn; nothing is uploaded there.

## Set up the master (once)

1. `python init.py` copies the template to `my-cv/CVindex.html` (git-ignored).
   Already have a CV folder elsewhere? Set it in `config.yml`:
   ```yaml
   cv:
     dir: "D:/Documents/CV"       # folder with the master, photo and tailored/
     master: CVindex.html
   ```
2. Replace the example content (Jane Doe) with your CV. Keep the class names: they are how the tools
   read the CV. The comment at the top of [`cv/master.example.html`](../cv/master.example.html) lists them.
   Easiest: in Claude Code say *"put my CV into my-cv/CVindex.html"* and give it your current CV.
3. Optional photo: put `photo.jpg` next to it and replace the placeholder with
   `<img src="photo.jpg" alt="Your Name" />`.
4. Set the PDF file name: `candidate.cv_file_name` in `config.yml` (e.g. `Jane_Doe_CV.pdf`).
5. Check and render it:
   ```bash
   python doctor.py              # "Master CV: Jane Doe: 3 jobs, 15 skills" -> your name here
   python cv_tools.py master     # my-cv/<cv_file_name> and my-cv/ats/<cv_file_name>
   ```
   Open both PDFs once and fix anything that looks wrong in the HTML.

## Per vacancy (the agent does this)

The agent writes a small spec and runs one command:

```bash
python cv_tools.py build my-cv/specs/acme-backend.json
```

```json
{
  "folder":   "tailored/2026-11-18-acme-backend",
  "subtitle": "Senior Backend Engineer",
  "summary":  "Backend engineer with 7+ years in Python and Go services ...",
  "skills":   {"Languages": ["Go", "Python"]},
  "bullets":  {"Acme Corp": [2, 0, 1]},
  "tags":     {"Acme Corp": ["Go", "AWS"]}
}
```

Result in `my-cv/tailored/2026-11-18-acme-backend/`: `CVindex.html`, the designed PDF and
`ats/<cv_file_name>`. Full rules for the agent:
[tailored-cv.md](../.claude/skills/job-hunter-agent/references/tailored-cv.md).

## The fact check

Every build is compared with the master before any PDF is written.

- **Stops the build:** a changed name, contact, employer, job title, date, education or language; a
  skill or tag that is in neither the master nor your profile / playbook; a number (years, %, counts)
  that is not in the master.
- **Warnings to review:** rewritten summary, reworded bullet, renamed skill ("Selenium" →
  "Selenium WebDriver"), skill taken from the profile rather than the master.

Hand-edited copy? `python cv_tools.py check path/to/CVindex.html`.

## All commands

| Command | Does |
|---|---|
| `python cv_tools.py build SPEC [--pages 1]` | tailor + check + designed and ATS PDFs |
| `python cv_tools.py tailor SPEC` | tailored HTML only (+ check) |
| `python cv_tools.py check HTML` | compare a tailored copy with the master |
| `python cv_tools.py master [--pages 1]` | PDFs of the master itself |
| `python cv_tools.py designed IN.html OUT.pdf` | designed PDF of any CV HTML |
| `python cv_tools.py ats IN.html OUT.pdf [--pages 1]` | ATS PDF of any CV HTML |

`--pages 1` only when a vacancy or recruiter asks for a one-page CV. PDFs need Playwright Chromium
(`python -m playwright install chromium`; `python doctor.py` checks it).
