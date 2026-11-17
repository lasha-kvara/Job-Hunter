import re
import os
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

from . import settings
from .assessment import friendly_location, is_home
from .models import JobPost

logger = logging.getLogger(__name__)



class CandidateScorer:
    """
    Evaluates job postings against the configured candidate profile.
    Dynamically loads target roles and technical skills from candidate-profile.md; the fallback
    skills, target roles, seniority bonuses and title penalties come from config.yml (`role`).
    """

    @staticmethod
    def _role() -> dict:
        return settings.section("role")

    @classmethod
    def default_keywords(cls) -> Dict[str, int]:
        return {str(k).lower(): int(v) for k, v in (cls._role().get("fallback_skills") or {}).items()}

    @classmethod
    def default_target_roles(cls) -> List[str]:
        return [str(r).lower() for r in cls._role().get("target_roles") or []]

    _cached_keywords = None
    _cached_target_roles = None

    @classmethod
    def _resolve_profile_path(cls) -> Optional[Path]:
        """Finds active candidate-profile.md in common repository locations (never uses template)."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        candidates = [
            repo_root / "Linkedin Agent" / "candidate-profile.md",
            repo_root / "candidate-profile.md",
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    @classmethod
    def load_profile_criteria(cls) -> Tuple[dict, List[str]]:
        """
        Parses candidate-profile.md for target roles and technical skills.
        Returns a tuple of (core_keywords_dict, target_roles_list).
        Initializes purely from the profile if available, falling back to
        defaults only when no profile is configured.
        """
        if cls._cached_keywords is not None and cls._cached_target_roles is not None:
            return cls._cached_keywords, cls._cached_target_roles

        profile_path = cls._resolve_profile_path()
        parsed_keywords: Dict[str, int] = {}
        parsed_roles: List[str] = []

        if profile_path and profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 1. Parse target roles
                roles_match = re.search(r"##\s+Target\s+roles\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
                if roles_match:
                    for line in roles_match.group(1).splitlines():
                        line = line.strip().lstrip("-* ").lower()
                        # Skip empty lines or placeholder template lines like [Role Name]
                        if not line or line.startswith("["):
                            continue
                        # Extract abbreviations/acronyms in parentheses (e.g. "Software Development Engineer in Test (SDET)")
                        acronyms = re.findall(r"\((.*?)\)", line)
                        clean_line = re.sub(r"\(.*?\)", "", line).strip()
                        if clean_line:
                            parsed_roles.append(clean_line)
                        for acr in acronyms:
                            acr = acr.strip()
                            if len(acr) > 1:
                                parsed_roles.append(acr)

                # 2. Parse skills
                skills_match = re.search(r"##\s+Skills\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
                if skills_match:
                    for line in skills_match.group(1).splitlines():
                        line = line.strip().lstrip("-* ")
                        if not line or line.startswith("#"):
                            continue
                        # Strip markdown bold/italic markers before splitting
                        clean_line = line.replace("**", "").replace("*", "").strip()
                        parts = clean_line.split(":", 1)
                        if len(parts) == 2:
                            category = parts[0].strip().lower()
                            items_str = parts[1].strip()
                            # Skip placeholder template lines like [e.g. Python, TypeScript] or [Your skills]
                            if items_str.startswith("[") or "e.g." in items_str.lower():
                                continue
                            items = [it.strip().lower().strip("`*[] ") for it in items_str.split(",") if it.strip()]
                            weight = 15 if any(c in category for c in ["framework", "language", "core"]) else 10
                            for item in items:
                                if len(item) > 1:
                                    parsed_keywords[item] = weight

                profile_read_success = True
            except Exception as e:
                logger.warning(f"Could not read or parse candidate profile at {profile_path}: {e}. Falling back to default criteria.")
                profile_read_success = False

        # Strict candidate profile grounding:
        # If a candidate profile exists, was read successfully, and contains criteria,
        # score against parsed profile criteria (falling back to defaults for any unconfigured dimension).
        # Fall back completely to default SDET qualifications if no profile file exists or parsing failed.
        if profile_path and profile_path.exists() and profile_read_success and (parsed_keywords or parsed_roles):
            keywords = parsed_keywords if parsed_keywords else cls.default_keywords()
            target_roles = list(set(parsed_roles)) if parsed_roles else cls.default_target_roles()
        else:
            keywords = cls.default_keywords()
            target_roles = cls.default_target_roles()

        cls._cached_keywords = keywords
        cls._cached_target_roles = target_roles
        return keywords, target_roles



    @classmethod
    def score_job(cls, job: JobPost) -> JobPost:
        """Calculates fit_score (0-100), fit_reasons, and fit_grade for a JobPost."""
        text_to_search = f"{job.title} {job.description} {job.location}".lower()
        title_lower = job.title.lower()

        score = 0
        reasons: List[str] = []

        core_keywords, target_roles = cls.load_profile_criteria()

        # 1. Check title seniority
        for kw, weight in (cls._role().get("seniority_bonus") or {}).items():
            kw, weight = str(kw).lower(), int(weight)
            if re.search(rf'\b{re.escape(kw)}\b', title_lower):
                score += weight
                reasons.append(f"Senior role: '{kw.title()}' (+{weight})")
                break

        # 2. Check title role relevance against profile target roles
        role_matched = False
        for kw in target_roles:
            if kw in title_lower:
                score += 20
                reasons.append(f"Target role match in title: '{kw.upper()}' (+20)")
                role_matched = True
                break

        # 3. Check core skills in description / title
        matched_skills = []
        target_roles_set = set(target_roles)
        for kw, weight in core_keywords.items():
            # Skip role terms already scored in step 2
            if role_matched and kw in target_roles_set:
                continue
            pattern = rf'(?<![a-zA-Z0-9]){re.escape(kw)}(?![a-zA-Z0-9])'
            if re.search(pattern, text_to_search):
                score += weight
                matched_skills.append(kw)


        if matched_skills:
            # Highlight top 4 matched technologies
            top_tech = ", ".join(matched_skills[:5])
            reasons.append(f"Matched tech stack: {top_tech}")

        # 4. Remote preference
        has_negative_remote = bool(re.search(
            r'\b(?:not\s+remote|no\s+remote|non-remote|not\s+available\s+for\s+remote|remote\s+work\s+is\s+not\s+available|no\s+remote\s+option)\b',
            text_to_search,
            re.IGNORECASE
        ))
        if job.is_remote or (re.search(r'\b(?:remote|telecommute|work\s+from\s+home|wfh)\b', text_to_search, re.IGNORECASE) and not has_negative_remote):
            score += 10
            reasons.append("Remote friendly (+10)")

        # 5. Check negative signals
        for neg_kw, penalty in (cls._role().get("title_penalties") or {}).items():
            neg_kw, penalty = str(neg_kw).lower(), int(penalty)
            if re.search(rf'\b{re.escape(neg_kw)}\b', title_lower):
                score += penalty
                reasons.append(f"Penalty for '{neg_kw}' ({penalty})")

        # 6. On-site outside the home country (config.yml: location.home_places) without relocation
        loc = job.location or ""
        has_relocation = bool(re.search(r'\b(?:relocation|visa\s+sponsorship|sponsorship\s+provided)\b', text_to_search, re.IGNORECASE))
        looks_remote = job.is_remote or bool(re.search(r'\b(remote|home[- ]based|anywhere)\b', loc, re.IGNORECASE))
        if loc and not looks_remote and not is_home(loc) and not friendly_location(loc) and not has_relocation:
            score -= 40
            reasons.append(f"On-site outside home country without relocation: '{loc}' (-40)")

        # Normalize score between 0 and 100
        score = max(0, min(100, score))
        job.fit_score = score
        job.fit_reasons = reasons

        # Assign fit grade
        if score >= 80:
            job.fit_grade = "🌟 STRONG MATCH"
        elif score >= 60:
            job.fit_grade = "✅ GOOD MATCH"
        elif score >= 40:
            job.fit_grade = "⚠️ MODERATE"
        else:
            job.fit_grade = "❌ LOW FIT"

        return job

    @classmethod
    def score_all(cls, jobs: List[JobPost]) -> List[JobPost]:
        """Scores and sorts jobs by fit_score descending."""
        scored = [cls.score_job(j) for j in jobs]
        return sorted(scored, key=lambda x: x.fit_score, reverse=True)
