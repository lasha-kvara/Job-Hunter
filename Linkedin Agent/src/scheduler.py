"""
Interview Scheduler & Availability Helper
Formats, validates, and prepares interview proposals according to candidate preferences.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.profile_manager import CandidateProfile

class InterviewScheduler:
    def __init__(self, profile: Optional[CandidateProfile] = None):
        self.profile = profile or CandidateProfile()

    def get_standard_slots(self, language: str = "en") -> str:
        """Returns standard suggested interview slots in candidate timezone."""
        tz = self.profile.get_preferences().get("timezone", "").strip()
        if not tz:
            return (
                "Please configure the candidate timezone before proposing interview slots."
                if language != "ka"
                else "გასაუბრების დროის შეთავაზებამდე მიუთითეთ კანდიდატის დროის სარტყელი."
            )
        tz_str = f" ({tz})"
        if language == "ka":
            return f"ორშაბათს 17:00-ზე ან სამშაბათს 17:00-ზე{tz_str}"
        return f"Monday at 17:00 or Tuesday at 17:00{tz_str}"

    def format_confirmation(self, date_str: str, time_str: str, timezone: Optional[str] = None, language: str = "en") -> str:
        """
        Formats a clear confirmation string containing weekday, date, time, and timezone.
        """
        tz = (timezone or self.profile.get_preferences().get("timezone", "")).strip()
        if not tz:
            return (
                "Please configure or specify the timezone before confirming the interview."
                if language != "ka"
                else "გასაუბრების დროის დადასტურებამდე მიუთითეთ დროის სარტყელი."
            )
        tz_str = f" ({tz})"
        if language == "ka":
            return f"{date_str}, {time_str} საათზე{tz_str} ჩემთვის სრულად მისაღებია. შევხვდებით გასაუბრებაზე!"
        return f"{date_str} at {time_str}{tz_str} works perfectly for me. Looking forward to our call!"

    def validate_slot_request(self, proposed_text: str) -> Dict[str, Any]:
        """
        Extracts details and marks that user confirmation is mandatory.
        """
        tz = self.profile.get_preferences().get("timezone", "")
        tz_note = f"Ensure timezone is explicitly confirmed with the recruiter (Candidate timezone: {tz})." if tz else "Ensure timezone is explicitly confirmed with the recruiter."
        return {
            "proposed_text": proposed_text,
            "requires_user_approval": True,
            "timezone_note": tz_note
        }

if __name__ == "__main__":
    scheduler = InterviewScheduler()
    print("Standard proposal (EN):", scheduler.get_standard_slots("en"))
    print("Standard proposal (KA):", scheduler.get_standard_slots("ka"))
    print("Confirmation (EN):", scheduler.format_confirmation("Thursday, Aug 27", "16:00"))
