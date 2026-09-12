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

    @staticmethod
    def is_placeholder(val: str) -> bool:
        """Determines whether a value is an unconfigured template placeholder or example instruction."""
        if not val:
            return True
        s = val.strip()
        # Direct bracketed placeholders: [Full Name], [Your Email], [e.g. ...], [Your professional summary...]
        if s.startswith("[") and s.endswith("]"):
            return True
        if s.startswith("[") or s.endswith("]"):
            return True
        # Bracketed template tags within string: $[Amount], [e.g. ...], [Your ...], path/to/...
        if re.search(r"(\[.*?\]|\$\[.*?\]|path/to/|e\.g\.)", s, re.IGNORECASE):
            clean = re.sub(r"(\[.*?\]|\$\[.*?\]|usd/month|or gross annual|\(or gross annual\))", "", s, flags=re.IGNORECASE).strip()
            if not clean or clean in {"$", "minimum", "target", "expected"}:
                return True
        if s.lower() in {"candidate", "[full name]", "your name", "[your name]"}:
            return True
        return False

    @property
    def is_template_profile(self) -> bool:
        """Returns True if the loaded profile is the unconfigured template."""
        if self.file_path and self.file_path.name.endswith(".template.md"):
            return True
        name = self.get_candidate_name()
        if not name:
            if "Fill in your details below" in self.raw_content or "[Full Name]" in self.raw_content:
                return True
        return False

    def get_candidate_name(self) -> str:
        m = re.search(r"^#\s+Candidate\s+Profile:\s*(.+)$", self.raw_content, re.MULTILINE)
        if m:
            val = m.group(1).strip()
            if not self.is_placeholder(val):
                return val
        return ""

    def get_summary(self) -> str:
        for sec_name, content in self.sections.items():
            if "summary" in sec_name.lower():
                val = content.strip()
                if val and not self.is_placeholder(val):
                    return val
        return ""

    def get_target_roles(self) -> List[str]:
        for sec_name, content in self.sections.items():
            if "target roles" in sec_name.lower():
                roles = []
                for line in content.splitlines():
                    if line.strip().startswith(("-", "*")):
                        role = line.lstrip("- *").strip()
                        if role and not self.is_placeholder(role):
                            roles.append(role)
                if self.is_template_profile and all("e.g." in r.lower() or self.is_placeholder(r) for r in roles):
                    return []
                return roles
        return []

    def get_salary_expectation(self) -> str:
        for sec_name, content in self.sections.items():
            if "salary" in sec_name.lower():
                clean_lines = [
                    re.sub(r"[*_`]", "", re.sub(r"^[-*\s]+", "", l)).strip()
                    for l in content.splitlines()
                    if l.strip()
                ]
                for l in clean_lines:
                    if l and not self.is_placeholder(l) and not l.lower().startswith("disclose"):
                        # Normalize prefixes (e.g., Minimum, Target, Expected, At least, Around)
                        val = re.sub(r"^(?:minimum|target|expected|approx(?:\.|\w*)|around|at least)\s*:?\s*", "", l, flags=re.IGNORECASE).strip()
                        # Remove trailing parenthetical remarks like (or gross annual) or (gross)
                        val = re.sub(r"\s*\([^)]*(?:annual|gross|net|negotiable)[^)]*\)", "", val, flags=re.IGNORECASE).strip()
                        val = val.rstrip(".").strip()
                        if val and not self.is_placeholder(val):
                            return val
        return ""

    def get_availability(self) -> str:
        for sec_name, content in self.sections.items():
            if "availability" in sec_name.lower():
                for line in content.splitlines():
                    clean = re.sub(r"^[-*\s]+", "", line).strip().strip("*_` ")
                    if clean and not self.is_placeholder(clean):
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
                        if self.is_placeholder(clean_v):
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
            "notice_period": prefs.get("notice_period", ""),
            "work_mode": prefs.get("work_mode", ""),
            "relocation": prefs.get("relocation", ""),
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
                        clean_v = v.strip().strip("*_` ")
                        if self.is_placeholder(clean_v):
                            continue
                        contacts[clean_k] = clean_v
        return contacts

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
            if candidate_path and not self.is_placeholder(candidate_path) and "path/to" not in candidate_path.lower() and "your/cv" not in candidate_path.lower():
                return candidate_path

        # 2. Parse from candidate profile
        cv_match = re.search(r"ALWAYS upload the CV from:\s*[`'\"]?([^`'\"\n\r]+)[`'\"]?", self.raw_content, re.IGNORECASE)
        if cv_match:
            candidate_path = cv_match.group(1).strip()
            # Ignore template placeholders like 'path/to/your/CV.pdf'
            if candidate_path and not self.is_placeholder(candidate_path) and "path/to" not in candidate_path.lower() and "your/cv" not in candidate_path.lower():
                return candidate_path
        # Look for any explicit path ending with .pdf under CV section
        sec = self.get_section("cv") or self.get_section("resume")
        if sec:
            path_match = re.search(r"[`'\"]?([a-zA-Z]:\\[^`'\"\n\r]+\.pdf|/[^`'\"\n\r]+\.pdf)[`'\"]?", sec)
            if path_match:
                candidate_path = path_match.group(1).strip()
                if candidate_path and not self.is_placeholder(candidate_path) and "path/to" not in candidate_path.lower() and "your/cv" not in candidate_path.lower():
                    return candidate_path

        if strict:
            raise ValueError(
                "CV file path is not configured in candidate-profile.md or DEFAULT_CV_PATH environment variable. "
                "Please configure DEFAULT_CV_PATH in .env or update the 'ALWAYS upload the CV from: ...' line in candidate-profile.md before applying."
            )
        return "[Not configured in candidate-profile.md]"

    def get_previous_companies(self) -> List[str]:
        """
        Dynamically extracts candidate's previous employers and featured project names
        from Experience and Featured Projects sections in candidate-profile.md.
        """
        companies = []
        exp = self.get_experience_summary()
        if exp:
            # Matches '- **... @ Company Name**'
            for line in exp.splitlines():
                m = re.search(r'@\s+([^—–\(\n]+)', line)
                if m:
                    comp = re.sub(r'[*_`]', '', m.group(1)).strip()
                    if comp and comp not in companies:
                        companies.append(comp)

        featured = self.get_section("featured projects")
        if featured:
            for line in featured.splitlines():
                m = re.match(r"^[-*]\s+[*_`]*(.+?)[*_`]*(?:\s+—|\s+–|\s+\(|$)", line)
                if m:
                    comp = re.sub(r'[*_`]', '', m.group(1)).strip()
                    if comp and comp not in companies:
                        companies.append(comp)

        return companies

    @staticmethod
    def _bound_field(val: str, max_len: int, default: str = "") -> str:
        s = " ".join(val.split()).strip()
        if not s:
            return default
        if len(s) > max_len:
            return s[:max_len - 3].rsplit(" ", 1)[0] + "..."
        return s

    def get_compact_context_prompt(self) -> str:
        """Returns a high-density, token-efficient summary (~150-200 tokens) derived directly
        from the parsed candidate-profile.md (Single Source of Truth)."""
        name = self._bound_field(self.get_candidate_name(), 50, "Candidate")

        # Bound summary to preserve compact token budget (~150-200 tokens)
        summary_raw = self.get_summary().strip()
        first_para = summary_raw.split("\n\n")[0].strip()
        summary = self._bound_field(first_para, 220, "[Not configured in candidate-profile.md]")

        raw_roles = ", ".join(self.get_target_roles()[:3])
        roles = self._bound_field(raw_roles, 70, "[Not configured in candidate-profile.md]")

        prefs = self.get_preferences()
        raw_salary = self.get_salary_expectation() or prefs.get("min_salary", "")
        salary = self._bound_field(raw_salary, 40, "[Not specified]")

        # Explicitly use get_skills_summary() to skip Personal Skills (competencies)
        skills = self.get_skills_summary()
        if skills:
            skill_lines = []
            for line in skills.splitlines():
                if line.strip().startswith(("-", "*")):
                    bullet = line.strip("- *").strip()
                    if ":" in bullet:
                        cat, val = bullet.split(":", 1)
                        clean_val = val.strip().strip("*_` ")
                        if clean_val and not self.is_placeholder(clean_val):
                            clean_cat = re.sub(r"[*_`]", "", cat).strip()
                            skill_lines.append(f"{clean_cat}: {clean_val}")
                    else:
                        clean_bullet = re.sub(r"[*_`]", "", bullet).strip()
                        if clean_bullet and not self.is_placeholder(clean_bullet):
                            skill_lines.append(clean_bullet)
            raw_skills = "; ".join(skill_lines[:4]) if skill_lines else ""
            clean_skills = re.sub(r"[*_`]", "", raw_skills).strip()
            skills_summary = self._bound_field(clean_skills, 140, "[Not configured in candidate-profile.md]")
        else:
            skills_summary = "[Not configured in candidate-profile.md]"

        raw_tz = prefs.get("timezone", "")
        clean_tz = re.sub(r";.*$", "", raw_tz).strip() if raw_tz else ""
        tz = self._bound_field(clean_tz, 35, "[Not specified]")

        raw_notice = prefs.get("notice_period", "")
        clean_notice = re.sub(r"\(.*?\)", "", raw_notice).strip() if raw_notice else ""
        notice = self._bound_field(clean_notice, 35, "[Not specified]")

        raw_work_mode = prefs.get("work_mode", "")
        clean_work_mode = re.sub(r"\(.*?\)", "", raw_work_mode).strip() if raw_work_mode else ""
        work_mode = self._bound_field(clean_work_mode, 35, "[Not specified]")

        raw_reloc = prefs.get("relocation", "")
        clean_reloc = re.sub(r"\(.*?\)", "", raw_reloc).strip() if raw_reloc else ""
        reloc = self._bound_field(clean_reloc, 35, "[Not specified]")

        raw_avail = self.get_availability().strip()
        avail = self._bound_field(raw_avail, 35, "[Not specified]")

        prompt = f"""Candidate Profile (Compact): {name}
Summary: {summary}
Target Roles: {roles}
Key Skills: {skills_summary}
Salary Expectation: {salary}
Timezone: {tz} | Work Mode: {work_mode} | Relocation: {reloc} | Notice: {notice} | Availability: {avail}
Note: For deep historical project metrics or full architecture breakdowns, escalate to candidate-profile.md."""
        return prompt[:950]

    def get_full_context_prompt(self) -> str:
        """Returns the formatted profile for feeding to LLM prompts."""
        name = self.get_candidate_name() or "Candidate"
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
