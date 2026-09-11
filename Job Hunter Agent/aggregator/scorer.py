import re
import os
from pathlib import Path
from typing import List, Tuple, Dict
from .models import JobPost



class CandidateScorer:
    """
    Evaluates job postings against the configured candidate profile.
    Dynamically loads target roles and technical skills from candidate-profile.md,
    with robust fallback to standard SDET/engineering keywords.
    """

    DEFAULT_CORE_KEYWORDS = {
        # Automation Frameworks
        "playwright": 18,
        "selenium": 10,
        "cypress": 10,
        "appium": 8,
        "restassured": 8,
        # Languages
        "typescript": 12,
        "javascript": 10,
        "python": 12,
        "c#": 12,
        ".net": 10,
        # SDET & QA Automation terms
        "sdet": 20,
        "qa automation": 18,
        "automation engineer": 18,
        "software development engineer in test": 20,
        "test automation": 16,
        "test architect": 15,
        # Performance & API
        "k6": 12,
        "jmeter": 8,
        "api testing": 10,
        "postman": 8,
        # DevOps & CI/CD
        "ci/cd": 10,
        "github actions": 8,
        "gitlab": 8,
        "docker": 8,
        "jenkins": 6,
    }

    SENIORITY_KEYWORDS = {
        "senior": 15,
        "sr": 15,
        "lead": 15,
        "staff": 15,
        "principal": 15,
    }

    NEGATIVE_KEYWORDS = {
        "intern": -40,
        "internship": -40,
        "junior": -25,
        "entry level": -20,
        "manual tester": -25,
        "manual testing only": -40,
        "no automation": -40,
    }

    _cached_keywords = None
    _cached_target_roles = None

    @classmethod
    def _resolve_profile_path(cls) -> Path:
        """Finds candidate-profile.md in common repository locations."""
        candidates = [
            Path("Linkedin Agent/candidate-profile.md"),
            Path(__file__).resolve().parent.parent.parent / "Linkedin Agent" / "candidate-profile.md",
            Path("candidate-profile.md"),
            Path(__file__).resolve().parent.parent.parent / "Linkedin Agent" / "candidate-profile.template.md",
        ]
        for p in candidates:
            if p.exists():
                return p
        return candidates[0]

    @classmethod
    def load_profile_criteria(cls) -> Tuple[dict, List[str]]:
        """
        Parses candidate-profile.md for target roles and technical skills.
        Returns a tuple of (core_keywords_dict, target_roles_list).
        """
        if cls._cached_keywords is not None and cls._cached_target_roles is not None:
            return cls._cached_keywords, cls._cached_target_roles

        profile_path = cls._resolve_profile_path()
        keywords = dict(cls.DEFAULT_CORE_KEYWORDS)
        target_roles = [
            "sdet",
            "qa automation",
            "automation engineer",
            "test automation",
            "software development engineer in test",
        ]

        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 1. Parse target roles
                roles_match = re.search(r"##\s+Target\s+roles\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
                if roles_match:
                    parsed_roles = []
                    for line in roles_match.group(1).splitlines():
                        line = line.strip().lstrip("-* ").lower()
                        if line and not line.startswith("["):
                            parsed_roles.append(line)
                    if parsed_roles:
                        target_roles = parsed_roles

                # 2. Parse skills
                skills_match = re.search(r"##\s+Skills\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
                if skills_match:
                    for line in skills_match.group(1).splitlines():
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        # e.g. - **Languages:** Python, TypeScript, Java
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            category = parts[0].lower()
                            items_str = parts[1].replace("[", "").replace("]", "")
                            items = [it.strip().lower() for it in items_str.split(",") if it.strip()]
                            
                            weight = 15 if any(c in category for c in ["framework", "language", "core"]) else 10
                            for item in items:
                                if len(item) > 1 and not item.startswith("e.g."):
                                    keywords[item] = weight

            except Exception:
                pass

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
        for kw, weight in cls.SENIORITY_KEYWORDS.items():
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
        if job.is_remote or "remote" in text_to_search:
            score += 10
            reasons.append("Remote friendly (+10)")

        # 5. Check negative signals
        for neg_kw, penalty in cls.NEGATIVE_KEYWORDS.items():
            if re.search(rf'\b{re.escape(neg_kw)}\b', title_lower):
                score += penalty
                reasons.append(f"Penalty for '{neg_kw}' ({penalty})")

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
