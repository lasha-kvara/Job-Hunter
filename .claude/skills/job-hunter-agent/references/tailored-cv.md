# Tailored CV for every application

One CV per vacancy, built from the master CV so it matches the job description and parses well in
the employer's ATS, without adding anything that is not true.

## 1. Analyse the vacancy
From the full job description (not just the title), list:
- **Must-have** skills, tools, languages and frameworks (exact wording used in the posting).
- **Nice-to-have** items.
- Seniority, domain (fintech, e-commerce, mobile, AI…), and the exact job title.
- Repeated phrases: ATS ranking mostly rewards the posting's own terms.

## 2. Match against the facts
Mark each keyword as:
- **Have**: appears in the master `CVindex.html` or `candidate-profile.md` (same thing, any wording).
- **Missing**: not in either source.

Only "Have" keywords may appear in the tailored CV. "Missing" keywords are reported to the user as
gaps and never added, even if the candidate "probably" knows them.

## 3. Create the tailored copy
1. Folder: `<CV folder>\tailored\<YYYY-MM-DD>-<company>-<role>\` (lowercase, hyphens, ASCII).
2. Copy the master `CVindex.html` into it and change the photo path to `../../CvPhoto.jpg`.
3. Edit only the copy. Allowed changes:
   - **Subtitle** under the name: the posting's title, if it is one of the profile's target roles
     or an equivalent of a title the candidate has held (e.g. "Senior QA Automation Engineer").
   - **Professional Summary:** rewrite to lead with the experience that matches the must-haves,
     using the posting's terms. Keep the facts and numbers from the master.
   - **Skills:** reorder groups and badges so matching skills come first; rename a badge to the
     posting's wording when it means the same thing ("API Testing" → "REST API testing" only if REST
     is in the master); drop badges that are irrelevant to this job if space is needed.
   - **Experience bullets:** reorder within each job so the most relevant come first; rephrase a
     bullet to use the posting's terms if the meaning stays the same; drop weakly relevant bullets
     from older jobs if the CV gets too long.
   - **Tags** under each job: reorder or trim to the relevant ones.
4. Never change: employers, titles held, dates, numbers and metrics, education, contact details.
   Never add a skill, tool, project, certification or achievement that is not in the sources.
5. Keep the same layout and length (no extra pages).

## 4. Check before generating
- Every must-have marked "Have" appears in the copy at least once, ideally in the summary or a
  bullet and in skills.
- Diff the copy against the master: every changed line is a reorder, a removal, or a rewording of
  an existing fact.
- Contact details, name and dates are identical to the master.

## 5. Generate and upload
Generate both variants from the tailored copy (run from the CV folder):
- Designed: `node generate-pdf.js "tailored\<folder>\CVindex.html" "tailored\<folder>\Lasha_Kvaratskhelia_CV.pdf"`
- ATS: `node build-ats.js "tailored\<folder>\CVindex.html" "tailored\<folder>\ats\Lasha_Kvaratskhelia_CV.pdf"`
  (single column, A4, no photo, plain text; content is read from the same HTML, so both always match).

Which one to upload:
- **LinkedIn Easy Apply** and **any online application form or ATS** (Lever, Greenhouse, Workable,
  Ashby, SmartRecruiters, Recruitee, HireHive, Helio, company career portals): the **ATS** variant.
  Easy Apply forwards the file to the employer's ATS (the job URL often shows
  `applicantTrackingSystemName`), and LinkedIn parses it for recruiter search.
- **Email applications**, a CV a recruiter asks for in a LinkedIn message, a referral, or a form
  that explicitly asks for a designed/visual CV: the designed variant.

Each Easy Apply upload adds a file to the LinkedIn resume list. In the final report, remind the
user how many tailored CVs were added so they can clean the list; never delete them yourself.

Both files are named `Lasha_Kvaratskhelia_CV.pdf` (recruiters see the name; no company name, no
"ATS"). Confirm the chosen PDF exists and is not empty, then upload it.

## 6. Report
In the applications report entry add: tailored folder path, must-have coverage (e.g. 9/11), and the
missing keywords. In the final summary to the user, list the gaps that came up across jobs, so the
master CV can be improved with real experience.
