# 🎯 Job-Hunter — Automated Job Search & Application Agent

An open-source, autonomous AI-assisted agent built with **Python** and **Playwright** designed for searching, analyzing, and applying to tech jobs (QA Automation, SDET, Software Engineering) across multiple platforms.

---

## 🌟 Key Highlights

- 👁️ **Visual Headed Mode (Real-Time)**: Unlike black-box headless bots, Job-Hunter runs in a visible browser so you can watch every action (searching, scrolling, filling forms, attaching CVs) in real-time.
- 🔓 **100% Standalone (No Antigravity Required)**: Anyone with Python can clone and run this project immediately. It does not require Antigravity or any proprietary tools.
- 🛡️ **Privacy & Security First**: All profiles, credentials, and application histories stay strictly on your local machine. No tracking, no data harvesting.
- 🤖 **Human-Like Pacing**: Includes realistic browsing pauses, random delays, and smooth interactions to keep accounts safe.
- 🔌 **Chrome CDP Integration**: Connect directly to your existing, already-logged-in browser session via Chrome DevTools Protocol (`--remote-debugging-port=9222`) without sharing passwords or 2FA codes.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** installed ([python.org](https://www.python.org/))
- **Google Chrome** or Chromium browser

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/lasha-kvara/Job-Hunter.git
cd Job-Hunter
```

---

### Step 2: Install Dependencies
Create a virtual environment (recommended) and install the required packages:

```bash
# Optional: create & activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r "Linkedin Agent/requirements.txt"

# Install Playwright browser binaries
playwright install
```

---

### Step 3: Configure Your Candidate Profile
Copy the provided template and fill in your own information:

```bash
# Windows (PowerShell / CMD):
copy "Linkedin Agent\candidate-profile.template.md" "Linkedin Agent\candidate-profile.md"

# Linux / macOS:
cp "Linkedin Agent/candidate-profile.template.md" "Linkedin Agent/candidate-profile.md"
```

Open `candidate-profile.md` in any text editor and specify:
- Your target roles (e.g. `QA Automation Engineer`, `Senior SDET`)
- Skills and tech stack (e.g. `Playwright`, `Selenium`, `Python`, `TypeScript`, `CI/CD`)
- Professional experience & projects
- Contact details (Phone, Email, LinkedIn, GitHub)
- Path to your CV/Resume PDF file

> 💡 *Note: `candidate-profile.md` is automatically git-ignored so your private personal data will never be committed or pushed.*

---

### Step 4: Run the Agent

#### Option A: Headed Browser Auto-Apply
Watch the agent search and process vacancies live on screen:
```bash
python headed_apply.py
```

#### Option B: LinkedIn Interactive CLI
Manage recruiters, screen candidates, and track job pipelines:
```bash
python "Linkedin Agent/run.py"
```

#### Option C: Connect to Your Existing Logged-in Browser (CDP Mode)
If you are already logged into job platforms (like LinkedIn) and want to avoid logging in again:
1. Start your browser in remote debugging mode:
   - **Windows:** Double-click `Linkedin Agent/start_browser.bat`
   - **macOS / Linux:**
     ```bash
     google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_profile"
     ```
2. Run the agent:
   ```bash
   python "Linkedin Agent/run.py"
   ```
   The agent will automatically attach to your existing browser session.

---

## 📂 Project Structure

```text
Job-Hunter/
├── README.md                                 # Main documentation & setup guide
├── .gitignore                                # Keeps personal profiles & secrets local
├── headed_apply.py                           # Standalone Headed Playwright job apply runner
├── run_headed.py                             # Quick demo script for visual browsing
├── Job Hunter Agent/
│   └── job-applications-report.template.md  # Template for tracking submitted applications
└── Linkedin Agent/
    ├── candidate-profile.template.md         # Anonymized candidate profile template
    ├── linkedin-pipeline.template.md         # Active conversation & pipeline tracker
    ├── config.py                             # Global configuration and path resolver
    ├── requirements.txt                      # Python library dependencies
    ├── run.py                                # Interactive CLI for agent management
    ├── start_browser.bat                     # Windows shortcut for Chrome CDP debug session
    └── src/
        ├── browser_controller.py             # Playwright browser engine & human-like actions
        ├── pipeline_manager.py               # Application pipeline state manager
        ├── profile_manager.py                # Candidate facts parser & single source of truth
        ├── response_generator.py             # Context-aware messaging generator
        └── scheduler.py                      # Background scheduler & monitoring loop
```

---

## 🔒 Privacy & Git Safety
- Personal files (`candidate-profile.md`, `job-applications-report.md`, `linkedin-pipeline.md`) are ignored by Git.
- No personal contact numbers, emails, or credentials are tracked in this repository.
- Anyone can clone this repository, customize their own profile, and run it independently.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
