# 💼 LinkedIn Job-Seeker Agent (Lasha Kvaratskhelia)

სრულყოფილი **LinkedIn Job-Seeker Agent** სისტემა **ლაშა კვარაცხელიას** (Senior SDET) საკანდიდატო პროფილის, აქტიური საუბრების (Pipeline) და რეკრუტერებთან კომუნიკაციის სამართავად.

---

## 🌟 ძირითადი შესაძლებლობები

1. **ორმაგი სამუშაო რეჟიმი (Dual Operating Modes):**
   - **Antigravity IDE Mode (Native Skill):** აგენტი ინტეგრირებულია პირდაპირ Antigravity-ში (`.agents/skills/linkedin-agent/`). შეგიძლიათ ჩატში პირდაპირ დაავალოთ მესიჯების გადამოწმება, პასუხის მომზადება ან pipeline-ის განახლება.
   - **Standalone Python Runner & CLI:** ინტერაქტიული ტერმინალი (`python run.py`) და Playwright CDP ბრაუზერის ავტომატიზაცია.
2. **მკაცრი ფაქტობრივი სიზუსტე (Strict Grounding):**
   - პასუხები ეფუძნება ექსკლუზიურად `candidate-profile.md`-ს (7+ წლიანი SDET გამოცდილება, TBC, Digital Area, VTB, C#, Python, Java, Playwright, K6).
   - არასდროს იგონებს არარსებულ უნარებს ან ფაქტებს.
3. **უსაფრთხოების & ხელფასის პოლიტიკა:**
   - ხელფასის მოთხოვნა: მინიმუმ **$4,500 USD/თვეში** (მხოლოდ პირდაპირი კითხვის დროს).
   - გასაუბრების დროის დადასტურება: **მხოლოდ მომხმარებლის წინასწარი თანხმობით**.
   - ავთენტიფიკაცია: უკავშირდება თქვენს უკვე დალოგინებულ ბრაუზერს (CDP Port 9222) — არანაირი პაროლები ან 2FA.
4. **ადამიანური ქცევის იმიტაცია (Human-like Browsing & Pacing):**
   - Feed-ზე შესვლა -> პაუზა 2–3 წმ -> Messaging-ზე გადასვლა.
   - ნელი აკრეფა (Character-by-character delay).
   - მაქსიმუმ 5 საუბრის ნახვა ერთ სესიაზე (LinkedIn-ის უსაფრთხოების დასაცავად).
5. **სწრაფი და ლაკონიური რეპორტინგი:**
   - ანგარიშები წარმოდგენილია მაქსიმუმ **≤ 5 ბულეტად**.

---

## 📂 ფაილების სტრუქტურა

```text
Agents/Linkedin And Jobs/
├── .agents/
│   ├── rules/
│   │   ├── job-hunter-rules.md           # ვაკანსიების ძიებისა და უსაფრთხოების წესები
│   │   └── linkedin-rules.md             # LinkedIn-ის ქცევისა და უსაფრთხოების წესები
│   └── skills/
│       ├── job-hunter-agent/             # Job Hunter Agent-ის Skill
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── platforms-guide.md
│       │       └── screening-answers.md
│       └── linkedin-agent/               # LinkedIn Agent-ის Skill
│           ├── SKILL.md
│           └── references/
│               ├── pacing-rules.md       # ბრაუზერის pacing წესები
│               └── templates.md          # შეტყობინებების შაბლონები (GE/EN)
├── Job Hunter Agent/
│   └── job-applications-report.md        # გაგზავნილი ვაკანსიების სრული რეპორტი & სტატისტიკა
├── Linkedin Agent/
│   ├── candidate-profile.md              # კანდიდატის სრული პროფილი (Single Source of Truth)
│   ├── linkedin-pipeline.md              # აქტიური ვაკანსიების & საუბრების ტრეკერი
│   ├── linkedin-agent.md                 # აგენტის სრული ინსტრუქცია
│   ├── config.py                         # პარამეტრები და კონფიგურაცია
│   ├── requirements.txt                  # Python ბიბლიოთეკები
│   ├── start_browser.bat                 # Chrome/Brave-ის გაშვება CDP Debug რეჟიმში (Port 9222)
│   ├── run.py                            # ინტერაქტიული ტერმინალის UI & CLI
│   ├── README.md                         # დოკუმენტაცია
│   └── src/
│       ├── profile_manager.py            # პროფილის ფაქტების მენეჯერი
│       ├── pipeline_manager.py           # Pipeline-ის პარსერი & რეპორტერი
│       ├── response_generator.py         # პასუხების გენერატორი (GE/EN, Gemini/Rules)
│       ├── browser_controller.py         # Playwright CDP კონტროლერი
│       └── scheduler.py                  # გასაუბრების დროების დამხმარე
├── add_jobs.py                           # დამხმარე სკრიპტი რეპორტისთვის
├── headed_apply.py                       # Headed რეჟიმში აპლიკაციის სკრიპტი
└── run_headed.py                         # Headed ბრაუზერის გაშვების სკრიპტი
```

---

## 🚀 როგორ გამოვიყენოთ

### 1. Antigravity IDE-დან (ჩატის რეჟიმი)
უბრალოდ მიწერეთ Antigravity-ს ნებისმიერი დავალება:
- *"შეამოწმე რა ხდება ჩემს LinkedIn Pipeline-ში"*
- *"მომიმზადე პასუხი EPAM-ის რეკრუტერისთვის ინგლისურად"*
- *"Tetiana-ს მივწეროთ, რომ ჩემი ხელფასის მოლოდინია $4500"*
- *"რა სტატუსშია Astra Tech-ის გასაუბრება?"*

Antigravity ავტომატურად გაააქტიურებს `linkedin-agent` skill-ს და შეასრულებს დავალებას.

---

### 2. Standalone Python CLI / ინტერაქტიული მენიუდან

#### ნაბიჯი 1: დააყენეთ ბიბლიოთეკები (თუ საჭიროა)
```bash
pip install -r "c:\Users\PC\OneDrive\Desktop\Agents\Linkedin And Jobs\Linkedin Agent\requirements.txt"
```

#### ნაბიჯი 2: გაუშვით ბრაუზერი დებაგ რეჟიმში
ორჯერ დააჭირეთ `start_browser.bat`-ს (ან გაუშვით ტერმინალიდან):
```bash
c:\Users\PC\OneDrive\Desktop\Agents\Linkedin And Jobs\Linkedin Agent\start_browser.bat
```
*ეს გახსნის Chrome-ს ან Brave-ს `9222` პორტზე, სადაც თქვენი LinkedIn პროფილი ავტორიზებულია.*

#### ნაბიჯი 3: გაუშვით აგენტი
```bash
python "c:\Users\PC\OneDrive\Desktop\Agents\Linkedin And Jobs\Linkedin Agent\run.py"
```

გამოჩნდება ინტერაქტიული მენიუ:
```text
╔══════════════════════════════════════════════════════════════════════╗
║                    💼 LINKEDIN JOB-SEEKER AGENT                     ║
║              Candidate: Lasha Kvaratskhelia (Senior SDET)            ║
╚══════════════════════════════════════════════════════════════════════╝

📋 Pipeline-ის მოკლე ანგარიში (≤ 5 bullets)
• 📅 Astra Tech — გასაუბრება ჩანიშნულია / დადასტურებულია.
• ⏳ EPAM (Ketevan Gobadze) — reply when Luka/Ketevan responds with call details.
• ⏳ Merab Enukidze — reply when Merab confirms a time.
• 📊 განაცხადები: 5 LinkedIn Easy Apply და 10 Remote ATS განაცხადი აქტიურ მოლოდინშია.

აირჩიეთ მოქმედება:
1. 📥 LinkedIn შეტყობინებების შემოწმება (Browser CDP Check)
2. ✍️ რეკრუტერისთვის პასუხის მომზადება (Draft Reply)
3. 📅 გასაუბრების დროის შეთავაზება / დადასტურება
4. 🔄 Pipeline-ში სტატუსის განახლება (Update Status)
5. 👤 კანდიდატის ფაქტებისა და მონაცემების ნახვა
6. 🌐 Chrome / Brave-ის გაშვება დებაგ რეჟიმში (Port 9222)
0. 🚪 გასვლა (Exit)
```

#### CLI Command Shortcuts:
```bash
# Pipeline მოკლე რეპორტის ნახვა:
python run.py --status

# რეკრუტერის მესიჯზე პასუხის დრაფტის მომზადება:
python run.py --draft "Hi Lasha, what is your salary expectation?" --name "Tetiana"

# LinkedIn შეტყობინებების შემოწმება ბრაუზერში:
python run.py --check-browser
```

---

## 🔒 უსაფრთხოების წესები
- **არასდროს შეიყვანოთ პაროლი** აგენტის მეშვეობით.
- **Async Stop & Wait:** აგენტი მესიჯის გაგზავნის შემდეგ ჩერდება და ელოდება თქვენს შემდეგ მითითებას (არ ხდება განუწყვეტელი პოლინგი).
- **CAPTCHA შეჩერება:** თუ LinkedIn აჩვენებს უჩვეულო აქტივობას ან CAPTCHA-ს, აგენტი მყისიერად ჩერდება და გატყობინებთ.
