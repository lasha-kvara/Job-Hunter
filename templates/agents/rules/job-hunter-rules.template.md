# Job Hunter & Auto-Apply Workspace Rules (Template)

These behavioral constraints and filtering policies govern all job search, scraping, and application activities.

## 1. Candidate Data - ZERO Hallucination Invariant (STRICT)
- **Single Source of Truth:** `Linkedin Agent/candidate-profile.md` (or your local candidate profile).
- **Full Name, Email, Phone, Location:** MUST be dynamically read from `candidate-profile.md`.
- **NEVER** guess, invent, or use dummy contact information or emails.
- **QA Experience & Skills:** Factual statements (years, frameworks, languages) must match `candidate-profile.md` 1:1.

## 2. Never Abandon on 2FA / OTP / Captcha / Blocker (CRITICAL USER INVARIANT)
- **NEVER skip, abandon, or surrender** a job application when an authentication code, 2FA, OTP, CAPTCHA, or verification prompt appears.
- **Step 1 (Check Active Email Tab):** If the verification code is sent to the candidate's email (as defined in `candidate-profile.md`) and an email tab is already open in the browser session, switch to that tab to fetch the verification code autonomously.
- **Step 2 (Pause & Prompt User):** If the code/CAPTCHA cannot be resolved autonomously (e.g., SMS 2FA, manual image captcha, account password approval): **IMMEDIATELY PAUSE** execution. Alert the user with the exact requirement and **STOP** until the user confirms or provides the code. Never switch to another job application without resolving or user instruction.

## 3. File Upload Rule - NEVER Trigger OS File Dialog (CRITICAL)
- **NEVER** click visual "Upload CV" / "Choose File" buttons using mouse/pixel clicks! Doing so triggers the native OS file picker dialog which freezes browser automation.
- **ALWAYS** attach files by setting the file path directly on the DOM element:
  - Playwright: `locator('input[type="file"]').set_input_files(cv_file_path)`
  - CDP / JS: Find the `input[type="file"]` in the DOM tree (even if hidden with `display:none` or `opacity:0`) and set its files directly.
- **CV Path:** Resolve dynamically from the CV/Resume path specified in `candidate-profile.md`.

## 4. Human-like Pacing & Anti-Bot Stealth (CRITICAL)
- Avoid robotic straight-line clicks and instant typing bursts.
- Add realistic human typing delay (50-120ms per character).
- Scroll naturally (wheel 200-400px, brief 1-2s pause to simulate reading) before interacting with form fields.
- Respect site load events and avoid clicking disabled buttons.

## 5. ATS Quirks & Anti-Honeypot Rules
- **Indeed SmartApply:** Never click generic `button:has-text("Continue")` — Indeed renders honeypot buttons (`hp-continue-button-*`). Always use `getByTestId('continue-button')` and `getByTestId('submit-application-button')`.
- **Greenhouse ATS:** For location comboboxes (`react-select`), clear first, type with delay, and click `#react-select-*-option-0`.
- **Contextual Checkbox Analysis:** Always analyze each question and candidate fit individually before checking or unchecking options. Never make blind or automated assumptions: if none of the options apply, "None of the above" should be checked; if positive options apply, select only the matching ones and avoid contradictory combinations (e.g. checking both positive skills and "None of the above").

## 6. Duplicate Application Prevention
- Before submitting any application, cross-check:
  1. `Job Hunter Agent/job-applications-report.md`
  2. `linkedin-pipeline.md`
- If the company or jobId already exists, skip it to avoid spamming the employer.

## 7. Screening Answers & Factual Grounding
- Form values (years of experience, languages, frameworks, education) must strictly match `candidate-profile.md`.
- Never overstate or invent non-existent experience.

## 8. Detailed Reporting
- Every processed or submitted job must be logged into `job-applications-report.md` with full details:
  - Role Title, Company Name, Job URL
  - Location & Work Mode
  - Full Job Description & Technical Requirements
  - Answers given to questions + Salary stated
  - Date and Application Status (`submitted`, `review-needed`, `filtered-out`)
