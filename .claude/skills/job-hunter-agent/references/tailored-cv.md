# Tailored CV for external applications

One CV per vacancy, built from the master CV so it matches the job description and parses well in
the employer's ATS, without adding anything that is not true. Tool: `python cv_tools.py`
(master CV folder = `cv.dir` in `config.yml`; master file = `cv.master`, format of
`cv/master.example.html`; PDF name = `candidate.cv_file_name`).

## 1. Analyse the vacancy
From the full job description (not just the title), list:
- **Must-have** skills, tools, languages and frameworks (exact wording used in the posting).
- **Nice-to-have** items.
- Seniority, domain (fintech, e-commerce, mobile, AI…), and the exact job title.
- Repeated phrases: ATS ranking mostly rewards the posting's own terms.

## 2. Match against the facts
Mark each keyword as:
- **Have**: appears in the master CV, `candidate-profile.md` or `screening-playbook.md` (same thing,
  any wording).
- **Missing**: in none of them.

Only "Have" keywords may appear in the tailored CV. "Missing" keywords are reported to the user as
gaps and never added, even if the candidate "probably" knows them.

## 3. Write the spec
Create `<cv.dir>/specs/<company>-<role>.json` (paths inside are relative to `cv.dir`):

```json
{
  "folder":   "tailored/2026-11-18-acme-senior-backend",
  "subtitle": "Senior Backend Engineer",
  "summary":  "Rewritten summary that leads with the must-haves, using the posting's terms.",
  "skills":   {"Languages": ["Go", "Python", "SQL"]},
  "bullets":  {"Acme Corp": [2, 0, 1, 3]},
  "tags":     {"Acme Corp": ["Go", "Kubernetes", "AWS"]}
}
```

- **folder:** `tailored/<YYYY-MM-DD>-<company>-<role>` (lowercase, hyphens, ASCII).
- **subtitle:** the posting's title, if it is one of the profile's target roles or an equivalent of a
  title the candidate has held.
- **summary:** lead with the experience that matches the must-haves, in the posting's terms. Keep
  the facts; every number must already be in the master.
- **skills / tags:** new order per group or job, most relevant first; items left out are dropped.
  Only existing items (check the master's spelling).
- **bullets:** new order of a job's bullets by index (0 = first in the master), most relevant first;
  indexes left out are dropped (older jobs first if the CV gets long). The job is matched by the
  start of its company line.

Never change employers, titles held, dates, numbers, education or contact details: the tool cannot,
and `check` rejects them.

## 4. Build and check

```bash
python cv_tools.py build "<cv.dir>/specs/<file>.json"        # add --pages 1 only if a one-page CV is requested
```

This writes `tailored/<folder>/CVindex.html`, the designed PDF `tailored/<folder>/<cv_file_name>` and
the ATS PDF `tailored/<folder>/ats/<cv_file_name>` (single column, A4, no photo, plain text, fitted to
2 pages), after a fact check against the master:
- **errors stop the build**: changed name, contacts, employers, titles, dates, education, languages;
  a skill or tag in neither the master nor the profile / playbook; a number not in the master.
- **warnings** (review them): rewritten summary, renamed skill ("Selenium" → "Selenium WebDriver"),
  skill taken from the profile instead of the master.

If you edit a tailored HTML by hand (e.g. to reword a bullet in the posting's terms, same meaning),
run `python cv_tools.py check <path>` and then `designed` / `ats` for that file.

## 5. Upload
- **Any online application form or ATS** (Lever, Greenhouse, Workable, Ashby, SmartRecruiters,
  Recruitee, HireHive, Helio, company career portals): the **ATS** PDF.
- **LinkedIn Easy Apply:** no upload; the master ATS CV stored on LinkedIn is used (no duplicates).
- **Email applications**, a CV a recruiter asks for in a LinkedIn message, a referral, or a form
  that explicitly asks for a designed / visual CV: the designed PDF.

Both files have the same name, `<cv_file_name>` (recruiters see it; no company name, no "ATS").
Confirm the chosen PDF exists and is not empty, then upload it with `browser_file_upload`.
If the build fails, upload the master ATS PDF (`python cv_tools.py master` creates it) and say so.

## 6. Report
In the applications report entry add: tailored folder path, must-have coverage (e.g. 9/11), the
missing keywords and any check warnings. In the final summary to the user, list the gaps that came
up across jobs, so the master CV can be improved with real experience.
