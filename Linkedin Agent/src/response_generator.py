"""
Response Generator: Generates accurate, bilingual, friendly-professional candidate replies.
Strictly grounded in candidate-profile.md facts.
"""
import os
import re
import warnings
from typing import Dict, Any, Optional, Tuple
import sys
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.profile_manager import CandidateProfile

HAS_NEW_GENAI = False
HAS_LEGACY_GENAI = False

try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    try:
        import google.generativeai as legacy_genai
        HAS_LEGACY_GENAI = True
    except ImportError:
        pass

class ResponseGenerator:
    def __init__(self, profile: Optional[CandidateProfile] = None):
        self.profile = profile or CandidateProfile()
        self.api_key = config.GEMINI_API_KEY
        self.client = None
        self.legacy_model = None

        if self.api_key:
            if HAS_NEW_GENAI:
                try:
                    self.client = genai.Client(api_key=self.api_key)
                except Exception:
                    self.client = None
            elif HAS_LEGACY_GENAI:
                try:
                    legacy_genai.configure(api_key=self.api_key)
                    self.legacy_model = legacy_genai.GenerativeModel(config.DEFAULT_MODEL)
                except Exception:
                    self.legacy_model = None

    def detect_language(self, text: str) -> str:
        """Detects whether text is Georgian or English/Other."""
        # Check for Georgian Unicode block: \u10A0-\u10FF
        if re.search(r"[\u10A0-\u10FF]", text):
            return "ka"
        return "en"

    def draft_template_response(self, intent: str, contact_name: str = "", role_or_details: str = "", language: str = "en") -> str:
        """Fallback template-based response adhering strictly to persona."""
        name = contact_name or "there"
        candidate_name = self.profile.get_candidate_name()
        first_name = candidate_name.split()[0] if candidate_name and not candidate_name.startswith("[") else ""
        signoff_en = f"Best, {first_name}" if first_name else "Best regards"
        signoff_ka = f"პატივისცემით, {first_name}" if first_name else "პატივისცემით"
        salary_str = self.profile.get_salary_expectation()

        if intent == "initial_reply":
            if language == "ka":
                role_str = f"{role_or_details}-ს" if role_or_details else "ვაკანსიის"
                return f"გამარჯობა {name}, მადლობა დაინტერესებისთვის! სიამოვნებით გავეცნობი {role_str} პოზიციის დეტალებს. თუ შეგიძლიათ გამიზიაროთ გუნდისა და პროექტის შესახებ დამატებითი ინფორმაცია. სიამოვნებით გავისაუბრებთ. {signoff_ka}"
            else:
                role_phrase = f"the {role_or_details} role" if role_or_details else "this opportunity"
                return f"Hello {name}, thanks for reaching out! I'm interested in {role_phrase}. Could you share more details about the position and the team? I'd be happy to schedule an introductory call. {signoff_en}"

        elif intent == "greeting":
            if language == "ka":
                return f"გამარჯობა {name}, კარგად, მადლობა! თქვენ როგორ ბრძანდებით? რით შემიძლია დაგეხმაროთ? {signoff_ka}"
            else:
                return f"Hello {name}, I'm doing well, thanks for asking! How are you doing? How can I help you today? {signoff_en}"

        elif intent == "propose_time":
            tz = self.profile.get_preferences().get("timezone", "").strip()
            details_lower = role_or_details.lower() if role_or_details else ""
            has_timezone = bool(
                role_or_details and (
                    (tz and tz.lower() in details_lower)
                    or re.search(r"\b(?:utc|gmt|est|edt|pst|pdt|cst|cdt|cet|cest)(?:[+-]\d+(?::\d{2})?)?\b", details_lower)
                )
            )
            if not has_timezone and not tz:
                return (
                    "Please configure candidate timezone in candidate-profile.md before generating interview availability proposals."
                    if language != "ka"
                    else "გასაუბრების დროის შეთავაზებამდე მიუთითეთ დროის სარტყელი candidate-profile.md-ში."
                )
            slots = role_or_details or self.profile.get_availability()
            if not slots or any(k in slots.lower() for k in ["flexible", "confirm", "user", "ask"]):
                return (
                    f"Please provide specific interview slots to propose to the recruiter (Candidate timezone: {tz})."
                    if language != "ka"
                    else f"გთხოვთ მიუთითოთ გასაუბრებისთვის ხელმისაწვდომი დრო რეკრუტერისთვის შესათავაზებლად (დროის სარტყელი: {tz})."
                )
            tz_str = "" if has_timezone else f" ({tz})"
            if language == "ka":
                return f"გამარჯობა {name}, შემიძლია შემოგთავაზოთ {slots}{tz_str}. რომელი დრო იქნება თქვენთვის უფრო მოსახერხებელი?"
            else:
                return f"Hello {name}, I'm available on {slots}{tz_str}. Which time works best for your schedule?"

        elif intent == "confirm_interview":
            tz = self.profile.get_preferences().get("timezone", "").strip()
            details_lower = role_or_details.lower() if role_or_details else ""
            has_timezone = bool(
                role_or_details and (
                    (tz and tz.lower() in details_lower)
                    or re.search(r"\b(?:utc|gmt|est|edt|pst|pdt|cst|cdt|cet|cest)(?:[+-]\d+(?::\d{2})?)?\b", details_lower)
                )
            )
            if not has_timezone and not tz:
                return (
                    "Please configure candidate timezone in candidate-profile.md or specify it before confirming the interview."
                    if language != "ka"
                    else "გასაუბრების დროის დადასტურებამდე მიუთითეთ დროის სარტყელი candidate-profile.md-ში."
                )
            tz_str = "" if has_timezone else f" ({tz})"
            if language == "ka":
                return f"{role_or_details or 'შეთანხმებული დრო'}{tz_str} ჩემთვის სრულად მისაღებია. შევხვდებით გასაუბრებაზე!"
            else:
                return f"{role_or_details or 'The proposed time'}{tz_str} works perfectly for me. Looking forward to our discussion!"

        elif intent == "salary_expectation":
            if salary_str:
                if language == "ka":
                    return f"ჩემი გამოცდილებიდან და ტექნიკური უნარებიდან გამომდინარე, ჩემი სახელფასო მოლოდინია {salary_str}. სიამოვნებით განვიხილავ დეტალებს მას შემდეგ, რაც უკეთ გავეცნობით პროექტის მასშტაბს."
                else:
                    return f"Based on my experience and technical background, my compensation expectation is {salary_str}. Happy to discuss further once we explore the technical requirements and project scope in detail."
            else:
                if language == "ka":
                    return "სიამოვნებით განვიხილავ სახელფასო მოლოდინს მას შემდეგ, რაც უკეთ გავეცნობით პოზიციის მოთხოვნებსა და პროექტის მასშტაბს."
                else:
                    return "I would be happy to discuss compensation expectations once we explore the technical requirements and project scope in detail."

        elif intent == "follow_up":
            if language == "ka":
                return f"გამარჯობა {name}, უბრალოდ შეგახსენებთ თავს — ხომ არ გაქვთ რაიმე სიახლე პროცესთან დაკავშირებით? მადლობა!"
            else:
                return f"Hi {name}, just following up to check if there are any updates regarding our discussion. Thanks!"

        # Default short reply
        if language == "ka":
            return f"გამარჯობა {name}, მადლობა შეტყობინებისთვის! დეტალებს გავეცნობი და მალე დაგიბრუნდებით. {signoff_ka}"
        else:
            return f"Hello {name}, thanks for your message! I will review the details and get back to you shortly. {signoff_en}"

    def _is_deep_query(self, message: str) -> bool:
        """
        Determines whether the recruiter message specifically asks for deep candidate
        project details, architecture breakdowns, or past historical metrics (L2 escalation),
        while keeping general recruiter pitches ('we have an exciting project and need details') in compact context (L1).
        """
        msg = message.lower()

        # Explicit technical deep dive / architecture terms or past company names
        explicit_terms = [
            "architecture", "deep dive", "project breakdown", "framework design",
            "load test", "performance test", "system design",
            "tbc", "digital area", "biletebi", "optimo", "vtb",
            "არქიტექტურა", "წინა პროექტ", "წინა სამუშაო", "მეტრიკ", "მიღწევ"
        ]
        if any(term in msg for term in explicit_terms):
            return True

        # Candidate project/experience inquiry patterns (targeted at candidate's work/history)
        candidate_deep_patterns = [
            r"\b(?:your|past|previous|prior)\s+(?:projects?|experience|background|history|roles?|work|metrics?|achievements?)\b",
            r"\b(?:tell|share|describe|walk me through|what)\b.*\b(?:projects?|experience|background|history|framework|architecture|metrics?|achievements?)\b",
            r"\b(?:გვიამბეთ|მომიყევი|გვითხარით)\b.*\b(?:პროექტ|გამოცდილებ|კომპანი)\b"
        ]
        return any(re.search(p, msg) for p in candidate_deep_patterns)

    def draft_llm_response(self, hr_message: str, contact_name: str = "", context: str = "") -> Tuple[str, bool]:
        """
        Uses Gemini to generate a grounded response.
        Returns (draft_message, requires_user_confirmation).
        """
        language = self.detect_language(hr_message)
        requires_user_confirmation = False

        # Safety / keyword check for unconfirmed items
        if any(w in hr_message.lower() for w in ["salary", "rate", "compensation", "ხელფას", "ანაზღაურებ"]):
            requires_user_confirmation = True
        if any(w in hr_message.lower() for w in ["interview", "call", "schedule", "time", "შეხვედრ", "გასაუბრებ", "საათ"]):
            requires_user_confirmation = True

        if not self.client and not self.legacy_model:
            # Check for casual greetings only if no sensitive topic or role discussion is present
            has_role_keyword = any(w in hr_message.lower() for w in ["role", "position", "opportunity", "opening", "job", "vacancy", "პოზიცი", "ვაკანსი", "შემოთავაზებ"])
            if (
                not requires_user_confirmation
                and not has_role_keyword
                and any(w in hr_message.lower() for w in ["how are you", "how're you", "how r u", "როგორ ხარ", "როგორ ბრძანდებით", "როგორ ხართ"])
            ):
                return self.draft_template_response("greeting", contact_name, language=language), False
            # Use template engine
            if any(w in hr_message.lower() for w in ["salary", "rate", "compensation", "ხელფას", "ანაზღაურებ"]):
                return self.draft_template_response("salary_expectation", contact_name, language=language), True
            if any(w in hr_message.lower() for w in ["interview", "call", "schedule", "time", "შეხვედრ", "გასაუბრებ", "საათ", "დრო"]):
                return self.draft_template_response("propose_time", contact_name, language=language), True
            return self.draft_template_response("initial_reply", contact_name, language=language), requires_user_confirmation

        candidate_name = self.profile.get_candidate_name()
        salary_str = self.profile.get_salary_expectation()
        tz = self.profile.get_preferences().get("timezone", "")
        salary_rule = f"state expectation from profile ({salary_str})" if salary_str else "state that compensation can be discussed once project scope is explored"
        tz_rule = f"propose availability in candidate timezone ({tz})" if tz else "propose availability and confirm recruiter preferred timezone"

        # Tiered Token Optimization: use compact context for standard recruiter chat,
        # escalate to full context only when deep candidate project/architecture details are queried.
        profile_context = (
            self.profile.get_full_context_prompt() if self._is_deep_query(hr_message)
            else self.profile.get_compact_context_prompt()
        )

        system_instruction = f"""You are representing candidate {candidate_name} in LinkedIn conversations with HR/Recruiters.
Candidate Profile (Single Source of Truth):
{profile_context}

Rules:
1. Tone: Friendly-professional, concise, warm, respectful.
2. Language: Respond in { 'Georgian' if language == 'ka' else 'English' }.
3. NEVER invent facts, skills, companies, or salary not present in profile.
4. If salary is asked: {salary_rule}.
5. If interview time is asked: {tz_rule}.
6. Keep length short (2-4 sentences). Do not write essays.
"""

        prompt = f"""Recruiter / HR Message:
\"{hr_message}\"

Contact Name: {contact_name or 'Recruiter'}
Additional Context: {context or 'None'}

Draft the exact response message to be sent to this recruiter:"""

        try:
            if self.client:
                response = self.client.models.generate_content(
                    model=config.DEFAULT_MODEL,
                    contents=f"{system_instruction}\n\n{prompt}"
                )
                text = response.text.strip()
                return text, requires_user_confirmation
            elif self.legacy_model:
                response = self.legacy_model.generate_content(
                    f"{system_instruction}\n\n{prompt}"
                )
                text = response.text.strip()
                return text, requires_user_confirmation
        except Exception as e:
            # Fallback to template
            return self.draft_template_response("initial_reply", contact_name, language=language), requires_user_confirmation

        return self.draft_template_response("initial_reply", contact_name, language=language), requires_user_confirmation

if __name__ == "__main__":
    generator = ResponseGenerator()
    msg_en = "Hi, we saw your profile and have an opening. Are you open to discussing it?"
    draft_en, req_en = generator.draft_llm_response(msg_en, contact_name="Sarah")
    print(f"EN Draft (Requires approval: {req_en}):\n{draft_en}\n")

    msg_ka = "გამარჯობა, მაინტერესებს თქვენი სახელფასო მოლოდინი ამ პოზიციაზე."
    draft_ka, req_ka = generator.draft_llm_response(msg_ka, contact_name="მარიამი")
    print(f"KA Draft (Requires approval: {req_ka}):\n{draft_ka}\n")
