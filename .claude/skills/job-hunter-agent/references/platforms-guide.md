# Supported Job Platforms & ATS Guide

## 1. Georgian platforms

### jobs.ge
- URL: `https://jobs.ge/` (search: `https://jobs.ge/?page=1&q=QA+Automation`)
- Keywords: "QA", "Automation", "SDET", "Test Engineer", "Selenium", "Playwright".
- Flow: usually an external redirect or a company contact email shown in the listing.

### recruiter.ge
- URL: `https://recruiter.ge/`
- Flow: direct apply form, email submission, or CV upload.

## 2. Global platforms

### LinkedIn Jobs & Easy Apply
- URL: `https://www.linkedin.com/jobs/`
- Filters: keywords from the profile's target roles; location `Worldwide / Remote` or `Georgia`;
  `Easy Apply` filter when the user wants quick applications.
- Easy Apply is a multi-step dialog (contact, resume, screening questions, review). Keep the
  pre-selected default resume.
- External Apply leads to the company ATS (Lever, Greenhouse, Ashby, Workable, SmartRecruiters).

### ATS forms
- **Lever** (`jobs.lever.co`): single page; name, email, phone, resume, custom questions.
- **Greenhouse** (`boards.greenhouse.io`, `job-boards.greenhouse.io`): multi-field; EEO, work
  authorization, custom questions. Location comboboxes are react-select: clear, type, then pick the
  first option from the list that appears.
- **Indeed SmartApply**: pages contain hidden decoy "Continue" buttons (`hp-continue-button-*`).
  Use the visible buttons whose test id is `continue-button` / `submit-application-button`.
- **Workable, SmartRecruiters, Zoho Recruit**: standard field mappings.

### Remote boards (RemoteOK, Wellfound, WeWorkRemotely)
- Keep only roles that are 100% remote worldwide or GMT+4 compatible.
