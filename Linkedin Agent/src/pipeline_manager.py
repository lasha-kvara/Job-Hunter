"""
Pipeline Manager: Tracking and Updating Active LinkedIn Conversations & Job Applications
"""
import re
from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

class OpportunityItem:
    def __init__(self, title: str, category: str, content: str, status: str = "waiting", contact: str = "", next_step: str = ""):
        self.title = title
        self.category = category
        self.content = content
        self.status = status
        self.contact = contact
        self.next_step = next_step

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "category": self.category,
            "status": self.status,
            "contact": self.contact,
            "next_step": self.next_step,
            "content": self.content
        }

class PipelineTracker:
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or config.PIPELINE_FILE
        self.raw_content = ""
        self.opportunities: List[OpportunityItem] = []
        self.last_updated: str = str(date.today())
        self.load_pipeline()

    def load_pipeline(self) -> None:
        """Reads linkedin-pipeline.md from disk and parses items."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Pipeline file not found at {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            self.raw_content = f.read()

        self._parse_content()

    def _parse_content(self) -> None:
        """Parses markdown headers and extracts opportunities."""
        self.opportunities = []
        current_category = "General"
        current_item_title = ""
        current_item_lines: List[str] = []

        lines = self.raw_content.splitlines()
        for line in lines:
            if line.startswith("Last updated:"):
                self.last_updated = line.replace("Last updated:", "").strip()

            cat_match = re.match(r"^##\s+(.+)$", line)
            if cat_match:
                if current_item_title:
                    self._save_current_item(current_item_title, current_category, current_item_lines)
                    current_item_title = ""
                    current_item_lines = []
                current_category = cat_match.group(1).strip()
                continue

            item_match = re.match(r"^###\s+(\d+\.\s+)?(.+)$", line)
            if item_match:
                if current_item_title:
                    self._save_current_item(current_item_title, current_category, current_item_lines)
                    current_item_lines = []
                current_item_title = item_match.group(2).strip()
                continue

            if current_item_title:
                current_item_lines.append(line)

        if current_item_title:
            self._save_current_item(current_item_title, current_category, current_item_lines)

    def _save_current_item(self, title: str, category: str, lines: List[str]) -> None:
        content = "\n".join(lines).strip()
        status = "waiting"
        contact = ""
        next_step = ""

        # Extract status
        status_match = re.search(r"Status:\s*`?([a-zA-Z\-]+)`?", content, re.IGNORECASE)
        if status_match:
            status = status_match.group(1).lower()

        # Extract contact
        contact_match = re.search(r"Contact:\s*(.+)", content, re.IGNORECASE)
        if contact_match:
            contact = contact_match.group(1).strip()

        # Extract next step
        next_match = re.search(r"Next step:\s*(.+)", content, re.IGNORECASE)
        if next_match:
            next_step = next_match.group(1).strip()

        self.opportunities.append(OpportunityItem(
            title=title,
            category=category,
            content=content,
            status=status,
            contact=contact,
            next_step=next_step
        ))

    def get_all_opportunities(self) -> List[OpportunityItem]:
        return self.opportunities

    def get_by_status(self, status: str) -> List[OpportunityItem]:
        return [item for item in self.opportunities if item.status == status.lower()]

    def update_status(self, search_term: str, new_status: str, note: Optional[str] = None) -> bool:
        """Updates status of matching opportunity in raw_content and writes back."""
        found = False
        search_lower = search_term.lower()

        for item in self.opportunities:
            if search_lower in item.title.lower() or (item.contact and search_lower in item.contact.lower()):
                item.status = new_status.lower()
                found = True
                break

        if not found:
            return False

        # Update in raw content
        # Pattern to replace status line for the item
        today_str = str(date.today())
        self.raw_content = re.sub(r"Last updated:\s*[\d\-]+", f"Last updated: {today_str}", self.raw_content)

        # Replace status in text
        pattern = rf"(###\s+(?:\d+\.\s+)?.*?{re.escape(search_term)}[\s\S]*?Status:\s*)`?[a-zA-Z\-]+`?"
        def repl(m):
            return f"{m.group(1)}`{new_status.lower()}`"

        new_content, count = re.subn(pattern, repl, self.raw_content, flags=re.IGNORECASE)
        if count > 0:
            if note:
                # Append last action / note if requested
                pass
            self.raw_content = new_content
            self.save_pipeline()
            return True

        return False

    def save_pipeline(self) -> None:
        """Writes the updated content to disk."""
        # Safety invariant: never write to template files to prevent personal data leaking into git
        target_file = self.file_path
        if "template" in target_file.name.lower():
            clean_name = re.sub(r"[\._-]template(?=\.[a-zA-Z0-9]+$|$)", "", target_file.name, flags=re.IGNORECASE)
            if clean_name.lower() == target_file.name.lower():
                clean_name = "linkedin-pipeline.md"
            target_file = target_file.parent / clean_name
            self.file_path = target_file
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(self.raw_content)

    def generate_brief_report(self, max_bullets: int = 5) -> List[str]:
        """
        Generates ≤ 5 bullet summary strictly following linkedin-agent rules.
        """
        bullets = []

        scheduled = self.get_by_status("scheduled")
        pending_user = self.get_by_status("pending-user")
        waiting = self.get_by_status("waiting")

        if scheduled:
            for s in scheduled:
                bullets.append(f"📅 **{s.title}** — გასაუბრება ჩანიშნულია / დადასტურებულია.")

        if pending_user:
            for p in pending_user:
                bullets.append(f"⚠️ **{p.title}** — ელოდება მომხმარებლის გადაწყვეტილებას ({p.next_step or 'დადასტურება'})")

        active_opps = [o for o in self.opportunities if "active" in o.category.lower() and o.status == "waiting"]
        for o in active_opps:
            bullets.append(f"⏳ **{o.title}** ({o.contact or 'HR'}) — {o.next_step or 'ელოდება მეორე მხარის პასუხს'}")

        easy_apply_count = len([o for o in self.opportunities if "easy apply" in o.category.lower()])
        remote_apply_count = len([o for o in self.opportunities if "remote-site" in o.category.lower()])

        if easy_apply_count or remote_apply_count:
            bullets.append(f"📊 **განაცხადები:** {easy_apply_count} LinkedIn Easy Apply და {remote_apply_count} Remote ATS განაცხადი აქტიურ მოლოდინშია.")

        if not bullets:
            return ["ახალი მესიჯები არ არის — ყველა საუბარი მეორე მხარეს ელოდება."]

        return bullets[:max_bullets]

if __name__ == "__main__":
    tracker = PipelineTracker()
    print("Total opportunities:", len(tracker.get_all_opportunities()))
    print("\nBrief Report (≤ 5 bullets):")
    for b in tracker.generate_brief_report():
        print("-", b)
