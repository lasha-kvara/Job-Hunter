import re
from typing import List, Tuple
from .models import JobPost


class CandidateScorer:
    """
    Evaluates job postings against the candidate's core qualifications:
    7+ years SDET, Playwright, TypeScript, Python, C#, Selenium, K6, CI/CD.
    """

    CORE_KEYWORDS = {
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

    @classmethod
    def score_job(cls, job: JobPost) -> JobPost:
        """Calculates fit_score (0-100), fit_reasons, and fit_grade for a JobPost."""
        text_to_search = f"{job.title} {job.description} {job.location}".lower()
        title_lower = job.title.lower()

        score = 0
        reasons: List[str] = []

        # 1. Check title seniority
        for kw, weight in cls.SENIORITY_KEYWORDS.items():
            if re.search(rf'\b{re.escape(kw)}\b', title_lower):
                score += weight
                reasons.append(f"Senior role: '{kw.title()}' (+{weight})")
                break

        # 2. Check title role relevance
        role_matched = False
        for kw in ["sdet", "qa automation", "automation engineer", "test automation"]:
            if kw in title_lower:
                score += 20
                reasons.append(f"Target role match in title: '{kw.upper()}' (+20)")
                role_matched = True
                break

        # 3. Check core skills in description / title
        matched_skills = []
        for kw, weight in cls.CORE_KEYWORDS.items():
            # Skip role terms already scored in step 2
            if role_matched and kw in {"sdet", "qa automation", "automation engineer", "test automation"}:
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
