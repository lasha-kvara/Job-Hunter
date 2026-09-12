"""
Profile Manager: Single Source of Truth for Candidate Facts
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

class CandidateProfile:
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or config.PROFILE_FILE
        self.raw_content = ""
        self.sections: Dict[str, str] = {}
        self.load_profile()

    def load_profile(self) -> None:
        """Reads candidate-profile.md from disk."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Profile file not found at {self.file_path}")
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.raw_content = f.read()

        self._parse_sections()

    def _parse_sections(self) -> None:
        """Parses markdown sections based on ## headers."""
        current_section = "Header"
        lines = self.raw_content.splitlines()
        section_lines: Dict[str, List[str]] = {current_section: []}

        for line in lines:
            header_match = re.match(r"^##\s+(.+)$", line)
            if header_match:
                current_section = header_match.group(1).strip()
                section_lines[current_section] = []
            else:
                section_lines[current_section].append(line)

        self.sections = {k: "\n".join(v).strip() for k, v in section_lines.items()}

    def get_candidate_name(self) -> str:
        m = re.search(r"^#\s+Candidate\s+Profile:\s*(.+)$", self.raw_content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return "Candidate"

    def get_summary(self) -> str:
        for sec_name, content in self.sections.items():
            if "summary" in sec_name.lower():
                return content
        return "Senior SDET with 7+ years of experience bridging development and reliability."

    def get_target_roles(self) -> List[str]:
        for sec_name, content in self.sections.items():
            if "target roles" in sec_name.lower():
                return [line.lstrip("- *").strip() for line in content.splitlines() if line.strip().startswith(("-", "*"))]
        return [
            "QA Automation Engineer",
            "Software Development Engineer in Test (SDET)",
            "Test Automation Engineer Lead",
            "QA Lead",
            "AI-based Automation Engineer"
        ]

    def get_salary_expectation(self) -> str:
        for sec_name, content in self.sections.items():
            if "salary" in sec_name.lower():
                clean_lines = [
                    re.sub(r"[*_`]", "", re.sub(r"^[-*\s]+", "", l)).strip()
                    for l in content.splitlines()
                    if l.strip()
                ]
                for l in clean_lines:
                    if l and not l.startswith("[") and "amount" not in l.lower() and not l.lower().startswith("disclose"):
                        # Normalize prefixes (e.g., Minimum, Target, Expected, At least, Around)
                        val = re.sub(r"^(?:minimum|target|expected|approx(?:\.|\w*)|around|at least)\s*:?\s*", "", l, flags=re.IGNORECASE).strip()
                        # Remove trailing parenthetical remarks like (or gross annual) or (gross)
                        val = re.sub(r"\s*\([^)]*(?:annual|gross|net|negotiable)[^)]*\)", "", val, flags=re.IGNORECASE).strip()
                        val = val.rstrip(".").strip()
                        if val:
                            return val
        return ""

    def get_availability(self) -> str:
        for sec_name, content in self.sections.items():
            if "availability" in sec_name.lower():
                for line in content.splitlines():
                    clean = re.sub(r"^[-*\s]+", "", line).strip().strip("*_` ")
                    if clean and not clean.startswith("[") and "e.g." not in clean.lower():
                        return clean
        return ""

    def get_experience_summary(self) -> str:
        for sec_name, content in self.sections.items():
            if "experience" in sec_name.lower():
                return content
        return ""

    def get_skills_summary(self) -> str:
        for sec_name, content in self.sections.items():
            if "skills" in sec_name.lower() and "personal" not in sec_name.lower():
                return content
        return ""

    def get_preferences(self) -> Dict[str, str]:
        prefs = {}
        for sec_name, content in self.sections.items():
            if any(k in sec_name.lower() for k in ["preference", "logistic", "work preference"]):
                for line in content.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        clean_k = re.sub(r"^[-*\s]+", "", k).strip().lower()
                        clean_v = v.strip().strip("*_` ")
                        if clean_v.startswith("["):
                            continue
                        if "notice" in clean_k:
                            prefs["notice_period"] = clean_v
                        elif "mode" in clean_k or "work" in clean_k:
                            prefs["work_mode"] = clean_v
                        elif "relocate" in clean_k or "relocation" in clean_k:
                            prefs["relocation"] = clean_v
                        elif "zone" in clean_k or "timezone" in clean_k:
                            prefs["timezone"] = clean_v

        salary_exp = self.get_salary_expectation()
        if salary_exp:
            prefs["min_salary"] = salary_exp

        return {
            "notice_period": prefs.get("notice_period", "Negotiable"),
            "work_mode": prefs.get("work_mode", "Remote / Hybrid"),
            "relocation": prefs.get("relocation", "Open to relocation"),
            "timezone": prefs.get("timezone", ""),
            "min_salary": prefs.get("min_salary", "")
        }

    def get_contacts(self) -> Dict[str, str]:
        contacts = {}
        for sec_name, content in self.sections.items():
            if "contact" in sec_name.lower():
                for line in content.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        clean_k = re.sub(r"^[-*\s]+", "", k).strip().lower()
                        contacts[clean_k] = v.strip()
        return contacts or {
            "phone": "[Your Phone]",
            "email": "[Your Email]",
            "linkedin": "https://linkedin.com",
            "github": "https://github.com",
            "portfolio": ""
        }

    def get_section(self, name: str) -> str:
        """Returns the raw content of a section matching name (case-insensitive)."""
        for sec_name, content in self.sections.items():
            if name.lower() in sec_name.lower():
                return content
        return ""

    def get_cv_file_path(self, strict: bool = False) -> str:
        """Dynamically parses CV/Resume file path from env override or candidate profile."""
        # 1. Check environment variable / config override first
        env_cv_path = getattr(config, "DEFAULT_CV_PATH", "") or os.getenv("DEFAULT_CV_PATH", "")
        if env_cv_path and str(env_cv_path).strip():
            candidate_path = str(env_cv_path).strip()
            if candidate_path and not candidate_path.startswith("path/to") and not candidate_path.startswith("["):
                return candidate_path

        # 2. Parse from candidate profile
        cv_match = re.search(r"ALWAYS upload the CV from:\s*[`'\"]?([^`'\"\n\r]+)[`'\"]?", self.raw_content, re.IGNORECASE)
        if cv_match:
            candidate_path = cv_match.group(1).strip()
            # Ignore template placeholders like 'path/to/your/CV.pdf'
            if candidate_path and not candidate_path.startswith("path/to") and not candidate_path.startswith("["):
                return candidate_path
        # Look for any explicit path ending with .pdf under CV section
        sec = self.get_section("cv") or self.get_section("resume")
        if sec:
            path_match = re.search(r"[`'\"]?([a-zA-Z]:\\[^`'\"\n\r]+\.pdf|/[^`'\"\n\r]+\.pdf)[`'\"]?", sec)
            if path_match:
                candidate_path = path_match.group(1).strip()
                if candidate_path and not candidate_path.startswith("path/to") and not candidate_path.startswith("["):
                    return candidate_path

        if strict:
            raise ValueError(
                "CV file path is not configured in candidate-profile.md or DEFAULT_CV_PATH environment variable. "
                "Please configure DEFAULT_CV_PATH in .env or update the 'ALWAYS upload the CV from: ...' line in candidate-profile.md before applying."
            )
        return "[Not configured in candidate-profile.md]"

    def get_compact_context_prompt(self) -> str:
        """Returns a high-density, token-efficient summary (~150-200 tokens) derived directly
        from the parsed candidate-profile.md (Single Source of Truth)."""
        name = self.get_candidate_name()
        summary = self.get_summary()
        roles = ", ".join(self.get_target_roles()[:3])
        prefs = self.get_preferences()
        salary = self.get_salary_expectation() or prefs.get("min_salary", "")
        skills = self.get_section("skills")
        if skills:
            skill_lines = [line.strip("- *") for line in skills.splitlines() if line.strip().startswith(("-", "*"))]
            skills_summary = "; ".join(skill_lines[:4]) if skill_lines else "QA Automation, Playwright, Selenium, C#, Python"
        else:
            skills_summary = "QA Automation, Playwright, Selenium, C#, Python"

        return f"""Candidate Profile (Compact): {name}
Summary: {summary}
Target Roles: {roles}
Key Skills: {skills_summary}
Salary Expectation: {salary}
Timezone: {prefs.get('timezone', 'GMT+4')} | Work Mode: {prefs.get('work_mode', 'Remote / Hybrid')} | Notice: {prefs.get('notice_period', '1 month')}
Note: For deep historical project metrics or full architecture breakdowns, escalate to candidate-profile.md."""

    def get_full_context_prompt(self) -> str:
        """Returns the formatted profile for feeding to LLM prompts."""
        name = self.get_candidate_name()
        return f"""
Candidate Profile: {name}
Single Source of Truth:
{self.raw_content}
"""

if __name__ == "__main__":
    profile = CandidateProfile()
    print("Candidate Name:", profile.get_candidate_name())
    print("Target Roles:", profile.get_target_roles())
    print("Preferences:", profile.get_preferences())
    print("Contacts:", profile.get_contacts())
