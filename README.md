# 🎯 Job-Hunter — Autonomous Job Search & Application Agent

An open-source, dual-mode job search and application engine built with **Python**, **Playwright**, and **AI Agent Skills**. Designed for software engineers, SDETs, and QA Automation professionals to discover, filter, score, and apply to vacancies across multiple platforms with a local-by-default, privacy-first architecture (zero external telemetry and explicit opt-in for optional cloud LLM APIs).

---

## 🌟 Two Ways to Use Job-Hunter

Job-Hunter is engineered to work in **two distinct modes**:

| Feature | 🤖 Mode 1: AI Agent Mode (Google Antigravity) | 💻 Mode 2: Standalone Mode (Pure Python CLI) |
| :--- | :--- | :--- |
| **Prerequisites** | Google Antigravity IDE + Python 3.10+ | Python 3.10+ only (No AI required) |
| **Interaction** | Natural language conversational prompts | Terminal CLI commands & scripts |
| **Vacancy Discovery** | Autonomous multi-platform aggregation | `python search_jobs.py --query ...` |
| **CV / Profile Fit** | Evaluated against your profile facts | Weighted keyword scoring (0–100%) |
| **Form Filling** | Autonomous dynamic DOM analysis in Headed mode | Listing inspection & navigation in Headed mode |
| **2FA / Captcha** | Pauses and prompts the user; never accesses email or credentials | Visual browser pauses for user entry |
| **LinkedIn Recruiter** | AI drafts context-aware replies & tracks stages | Interactive terminal CLI menu |

---

## 🚀 Quick Start: Installation (Common to Both Modes)

### 1. Clone the Repository
```bash
git clone https://github.com/lasha-kvara/Job-Hunter.git
cd Job-Hunter
```

### 2. Create Virtual Environment & Install Dependencies
```bash
# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux / macOS:
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Install Playwright browser engines
playwright install
```

### 3. Initialize Your Local Profiles & Trackers
Copy the provided templates to your local, git-ignored active files:

```bash
# Windows:
copy "Linkedin Agent\candidate-profile.template.md" "Linkedin Agent\candidate-profile.md"
copy "Linkedin Agent\linkedin-pipeline.template.md" "Linkedin Agent\linkedin-pipeline.md"
copy "Job Hunter Agent\job-applications-report.template.md" "Job Hunter Agent\job-applications-report.md"

# Linux / macOS:
cp "Linkedin Agent/candidate-profile.template.md" "Linkedin Agent/candidate-profile.md"
cp "Linkedin Agent/linkedin-pipeline.template.md" "Linkedin Agent/linkedin-pipeline.md"
cp "Job Hunter Agent/job-applications-report.template.md" "Job Hunter Agent/job-applications-report.md"
```

Open `Linkedin Agent/candidate-profile.md` in any editor and specify:
- **Full Name, Email, Phone, Location, Timezone**
- **Target Roles** (e.g. `QA Automation Engineer`, `Senior SDET`, `Backend Developer`)
- **Core Skills & Frameworks** (e.g. `Playwright`, `TypeScript`, `Python`, `C#`, `Selenium`)
- **Years of Experience & Past Projects**
- **Absolute Path to your CV/Resume PDF**
- **Salary Expectations**

> 🛡️ **Privacy Guarantee:** `candidate-profile.md`, `job-applications-report.md`, and `linkedin-pipeline.md` are strictly git-ignored. Your personal contact details and private application histories will never be committed or uploaded to Git.

---

## 🤖 Mode 1: Running with Google Antigravity

If you use **Google Antigravity** (or an agentic workspace supporting `.agents/` skills and rules), follow these steps to unlock full autonomous capabilities:

### Step 1: Initialize Agent Skills & Rules
Copy the included templates into your local `.agents/` workspace directory:

```bash
# Windows (PowerShell / CMD):
xcopy /E /I "templates\agents" ".agents"

# Linux / macOS:
mkdir -p .agents && cp -r templates/agents/* .agents/
```

This installs:
- **`job-hunter-agent` skill:** Autonomous vacancy discovery, location/visa filtering, dynamic form filling, and 2FA handling.
- **`linkedin-agent` skill:** Recruiter conversation management, interview scheduling, and pipeline progression.
- **`job-hunter-rules` & `linkedin-rules`:** Strict invariants enforcing **ZERO hallucination** (the agent only uses facts from your `candidate-profile.md`), anti-bot human pacing, and safe file uploads.

### Step 2: Open Workspace in Antigravity
Open the `Job-Hunter` directory in Google Antigravity. The AI assistant will automatically recognize the registered skills.

### Step 3: Use Natural Language Prompts
You can now speak directly to the agent in English or Georgian:

- **Search & Aggregation:**
  > *"Find all remote Senior SDET and QA Automation openings matching my profile across LinkedIn, Indeed, and Google Jobs."*
- **Visual Application (Headed Mode):**
  > *"Launch a visible browser and apply to the top 3 matching vacancies. Stop and ask me if an SMS 2FA code is needed."*
- **LinkedIn Messaging:**
  > *"Check my LinkedIn messages via Chrome CDP. Update the opportunity pipeline and draft polite replies to new recruiters."*
- **Assessment Tests:**
  > *"Solve the problem-solving and QA technical assessment on this BairesDev tab."*

---

## 💻 Mode 2: Running Standalone (Without Antigravity)

You do **not** need Antigravity, Docker, or paid AI tokens to run Job-Hunter. All tools run directly from your command line:

### 1. Multi-Source Vacancy Aggregator (`search_jobs.py`)
Search across **LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs**, and **Jobs.ge**; the aggregator cleans and merges results from these sources:


```bash
# Search for remote QA Automation positions
python search_jobs.py --query "QA Automation Engineer" --remote

# Search for Senior SDET with minimum 60% candidate fit score
python search_jobs.py --query "Senior SDET" --min-score 60

# Filter specific sources
python search_jobs.py --query "Playwright Automation" --sources indeed linkedin google

# Search local/on-site positions as well
python search_jobs.py --query "SDET" --no-remote --sources jobs_ge indeed
```

**Key Features:**
- **URL Sanitization:** Automatically strips 40+ tracking parameters (`utm_*`, `refId`, `trackingId`, `gh_src`, etc.).
- **Smart Deduplication:** Groups listings across platforms by normalized company + title + location signatures.
- **Dynamic Fit Scoring:** Automatically scores jobs (0–100%) based on target roles and skills in `candidate-profile.md`.
- **Outputs:** Saves feed to `Job Hunter Agent/jobs_feed.json` and exports a clean Markdown table to `search_results.md`.

---

### 2. Headed Browser Visual Inspection Demo (`headed_apply.py`)
Run an automated visual browser session to inspect vacancy listings and test human-like pacing:

```bash
python headed_apply.py
```

- Launches a visual browser with smooth action pacing (`slow_mo=300`) and natural reading scrolls.
- Demonstrates real-time vacancy discovery and navigation across target listings.
- *Note:* Full end-to-end form completion, custom question answering, and CV attachment across diverse ATS forms (Lever, Greenhouse, etc.) is handled autonomously by the AI Agent in Mode 1.


---

### 3. LinkedIn Recruiter & Pipeline Manager (`Linkedin Agent/run.py`)
An interactive terminal CLI for managing recruiter outreach:

```bash
python "Linkedin Agent/run.py"
```

**Features:**
- View active opportunities grouped by stage (`Initial Contact`, `Waiting for Reply`, `Interview Scheduled`).
- Generate grounded replies in English and Georgian.
- Track interview availability and propose dates in your timezone.

---

### 4. Connect to Your Existing Browser Session (CDP Mode)
Avoid logging in repeatedly or triggering bot challenges by attaching to your existing Chrome profile:

1. **Launch Chrome in Remote Debugging Mode:**
   - **Windows:** Double-click `Linkedin Agent/start_browser.bat`
   - **Linux / macOS:**
     ```bash
     google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_profile"
     ```
2. **Run your script or agent:**
   ```bash
   python "Linkedin Agent/run.py"
   ```
   The engine attaches to port `9222` and operates inside your logged-in browser session.

---

## 📂 Repository Structure

```text
Job-Hunter/
├── README.md                                 # Comprehensive guide & setup manual
├── requirements.txt                          # Unified Python dependencies
├── search_jobs.py                            # Multi-source vacancy aggregator CLI
├── headed_apply.py                           # Standalone Headed Playwright job apply runner
├── run_headed.py                             # Quick demo script for visual browsing
├── .gitignore                                # Strict privacy boundary for local files
│
├── templates/                                # Ready-to-use anonymized templates
│   └── agents/                               # Antigravity skill & rule templates
│       ├── rules/
│       │   ├── job-hunter-rules.md
│       │   └── linkedin-rules.md
│       └── skills/
│           ├── job-hunter-agent/
│           │   ├── SKILL.md
│           │   └── references/
│           │       └── platforms-guide.md
│           └── linkedin-agent/
│               ├── SKILL.md
│               └── references/
│                   ├── pacing-rules.md
│                   └── templates.md

│
├── Job Hunter Agent/
│   ├── aggregator/                           # Multi-source scraper engine
│   │   ├── cleaner.py                        # Tracking parameter stripper & deduplicator
│   │   ├── engine.py                         # Unified search orchestrator
│   │   ├── models.py                         # Standardized JobPost dataclass
│   │   ├── scorer.py                         # Candidate profile fit scoring engine
│   │   └── sources/
│   │       ├── jobspy_provider.py            # Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google
│   │       └── jobs_ge_provider.py           # Local Jobs.ge scraper with secure TLS
│   └── job-applications-report.template.md  # Template for submitted application logs
│
└── Linkedin Agent/
    ├── candidate-profile.template.md         # Anonymized candidate facts template
    ├── linkedin-pipeline.template.md         # Anonymized pipeline tracker template
    ├── config.py                             # Path resolution & environment config
    ├── run.py                                # Interactive terminal management CLI
    ├── start_browser.bat                     # Windows shortcut for Chrome CDP session
    └── src/
        ├── browser_controller.py             # Playwright engine with human-like pacing
        ├── pipeline_manager.py               # Application stage tracker
        ├── profile_manager.py                # Candidate profile parser
        ├── response_generator.py             # Context-aware messaging engine
        └── scheduler.py                      # Availability & interview slot validator
```

---

## 🔒 Privacy & Safety Guidelines

- **Local-First & Zero Data Harvesting:** No personal tracking or telemetry databases are used. Your candidate profile, submitted application logs, and pipeline records remain strictly on your local disk.
- **Optional Cloud AI Integration:** If you choose to configure `GEMINI_API_KEY` for LLM-powered response generation in `Linkedin Agent`, message prompts containing relevant profile context are sent directly to Google's Gemini API using your own API key. Without an API key, response generation operates 100% locally using built-in templates (vacancy search and browser sessions only contact the public job boards and sites you explicitly target).
- **Git-Ignored Files:** Your actual `candidate-profile.md`, submitted applications report, and pipeline tracker remain on your local disk only.
- **Honeypot Protection:** Bypasses hidden honeypot buttons on platforms like Indeed SmartApply.
- **Safe File Uploads:** Uploads PDFs directly to `input[type="file"]` without opening operating system file dialogs.


---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
