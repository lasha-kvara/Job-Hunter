"""
LinkedIn Agent - Interactive Terminal & CLI Runner
"""
import sys
import os
import argparse
import asyncio
import warnings
from pathlib import Path
from typing import Optional

# Suppress future warnings from legacy SDKs
warnings.filterwarnings("ignore")

# Force UTF-8 for Windows console / PowerShell
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src.profile_manager import CandidateProfile
from src.pipeline_manager import PipelineTracker
from src.response_generator import ResponseGenerator
from src.browser_controller import LinkedInBrowserController
from src.scheduler import InterviewScheduler

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    HAS_RICH = True
    console = Console(force_terminal=True, legacy_windows=False)
except ImportError:
    HAS_RICH = False
    console = None

def show_banner(profile: Optional[CandidateProfile] = None):
    name = profile.get_candidate_name() if profile else "Candidate"
    roles = profile.get_target_roles() if profile else []
    primary_role = roles[0] if roles else "Job-Seeker"
    candidate_label = f"{name} ({primary_role})"
    if HAS_RICH:
        from rich.markup import escape
        safe_label = escape(candidate_label)
        banner = f"""
[bold cyan]╔══════════════════════════════════════════════════════════════════════╗
║                    💼 LINKEDIN JOB-SEEKER AGENT                     ║
║              Candidate: [bold yellow]{safe_label:^45}[/bold yellow] ║
╚══════════════════════════════════════════════════════════════════════╝[/bold cyan]
        """
        console.print(banner)
    else:
        print("=" * 60)
        print(f"LinkedIn Job-Seeker Agent - {candidate_label}")
        print("=" * 60)

def show_pipeline_summary(tracker: PipelineTracker):
    report_bullets = tracker.generate_brief_report(max_bullets=5)
    if HAS_RICH:
        panel_content = "\n".join([f"• {b}" for b in report_bullets])
        console.print(Panel(panel_content, title="[bold green]📋 Pipeline-ის მოკლე ანგარიში (≤ 5 bullets)[/bold green]", expand=False))
    else:
        print("\n--- Pipeline-ის მოკლე ანგარიში ---")
        for b in report_bullets:
            print(f"- {b}")

def show_profile_facts(profile: CandidateProfile):
    if HAS_RICH:
        table = Table(title="👤 კანდიდატის ძირითადი ფაქტები")
        table.add_column("პარამეტრი", style="cyan", no_wrap=True)
        table.add_column("მნიშვნელობა", style="magenta")

        table.add_row("კანდიდატი", profile.get_candidate_name())
        table.add_row("სამიზნე როლები", ", ".join(profile.get_target_roles()[:3]) + "...")
        table.add_row("ხელფასის მოლოდინი", profile.get_salary_expectation())
        table.add_row("Notice Period", profile.get_preferences().get("notice_period", "1 month"))
        table.add_row("სამუშაო ფორმატი", profile.get_preferences().get("work_mode", "Remote / Hybrid"))
        table.add_row("რელოკაცია", profile.get_preferences().get("relocation", "Yes"))
        table.add_row("საკონტაქტო მეილი", profile.get_contacts().get("email", ""))
        table.add_row("CV ფაილი", profile.get_cv_file_path(strict=False))

        console.print(table)
    else:
        print("\n--- კანდიდატის ფაქტები ---")
        print("სახელი:", profile.get_candidate_name())
        print("ხელფასი:", profile.get_salary_expectation())
        print("სამუშაო ფორმატი:", profile.get_preferences())

async def run_browser_check():
    controller = LinkedInBrowserController()
    if HAS_RICH:
        console.print(f"[yellow]🌐 ვუკავშირდებით Chrome/Brave-ს CDP პორტზე ({config.CDP_PORT})...[/yellow]")
    else:
        print(f"Connecting to browser on port {config.CDP_PORT}...")

    try:
        await controller.connect()
        if HAS_RICH:
            console.print("[green]✔ დაკავშირება წარმატებულია! ვამოწმებთ LinkedIn შეტყობინებებს (pacing rules)...[/green]")
        else:
            print("Connected. Checking messages...")

        messages = await controller.check_unread_messages()

        if not messages:
            msg = "ახალი მესიჯები არ არის — ყველა საუბარი მეორე მხარეს ელოდება."
            if HAS_RICH:
                console.print(f"[bold green]{msg}[/bold green]")
            else:
                print(msg)
        else:
            if HAS_RICH:
                table = Table(title="📥 ბოლო შეტყობინებები")
                table.add_column("#", style="dim")
                table.add_column("კონტაქტი", style="cyan")
                table.add_column("წაუკითხავი", style="red")
                table.add_column("ნაწყვეტი", style="white")

                for m in messages:
                    table.add_row(
                        str(m["index"] + 1),
                        m["name"],
                        "🔴 დიახ" if m["is_unread"] else "⚪ არა",
                        m["snippet"][:60] + "..." if len(m["snippet"]) > 60 else m["snippet"]
                    )
                console.print(table)
            else:
                for m in messages:
                    print(f"[{'UNREAD' if m['is_unread'] else 'READ'}] {m['name']}: {m['snippet']}")

    except Exception as e:
        if HAS_RICH:
            console.print(f"[bold red]❌ შეცდომა:[/bold red] {e}")
            console.print(f"[yellow]💡 რჩევა: დარწმუნდით, რომ გაშვებულია `start_browser.bat` ან ბრაუზერი `--remote-debugging-port={config.CDP_PORT}`-ით.[/yellow]")
        else:
            print(f"Error: {e}")
    finally:
        await controller.disconnect()

def handle_draft_response(generator: ResponseGenerator):
    if HAS_RICH:
        console.print("\n[bold cyan]✍️ პასუხის დრაფტის მომზადება[/bold cyan]")
        contact_name = Prompt.ask("რეკრუტერის სახელი (მაგ. Sarah / მარიამი)", default="")
        hr_message = Prompt.ask("შემოსული შეტყობინების ტექსტი")
    else:
        contact_name = input("Contact Name: ")
        hr_message = input("HR Message: ")

    draft, requires_approval = generator.draft_llm_response(hr_message, contact_name=contact_name)

    if HAS_RICH:
        status_color = "red" if requires_approval else "green"
        warning = "[bold red]⚠️ ყურადღება: ეს შეტყობინება შეიცავს ხელფასის ან შეხვედრის დეტალებს. გაგზავნამდე აუცილებელია მომხმარებლის დადასტურება![/bold red]\n" if requires_approval else ""
        console.print(Panel(f"{warning}[bold white]{draft}[/bold white]", title="[bold green]📝 მომზადებული პასუხი[/bold green]"))
    else:
        print("\n--- მომზადებული პასუხი ---")
        if requires_approval:
            print("⚠️ REQUIRES APPROVAL BEFORE SENDING")
        print(draft)

def handle_update_status(tracker: PipelineTracker):
    if HAS_RICH:
        console.print("\n[bold cyan]🔄 საუბრის სტატუსის განახლება[/bold cyan]")
        search_term = Prompt.ask("კომპანიის ან კონტაქტის სახელი (მაგ. TechCorp, Acme, GlobalTech)")
        status_options = ["waiting", "pending-user", "scheduled", "in-progress", "closed"]
        new_status = Prompt.ask(f"ახალი სტატუსი ({'/'.join(status_options)})", choices=status_options, default="waiting")
    else:
        search_term = input("Search term (Company/Contact): ")
        new_status = input("New status (waiting/pending-user/scheduled/in-progress/closed): ")

    success = tracker.update_status(search_term, new_status)
    if success:
        if HAS_RICH:
            console.print(f"[bold green]✔ სტატუსი წარმატებით განახლდა: '{search_term}' -> `{new_status}`[/bold green]")
        else:
            print(f"Status updated: {search_term} -> {new_status}")
    else:
        if HAS_RICH:
            console.print(f"[bold red]❌ ჩანაწერი სახელწოდებით '{search_term}' ვერ მოიძებნა pipeline-ში.[/bold red]")
        else:
            print(f"Item not found: {search_term}")

def interactive_menu():
    profile = CandidateProfile()
    tracker = PipelineTracker()
    generator = ResponseGenerator(profile)
    scheduler = InterviewScheduler(profile)

    while True:
        show_banner(profile)
        show_pipeline_summary(tracker)

        if HAS_RICH:
            console.print("\n[bold yellow]აირჩიეთ მოქმედება:[/bold yellow]")
            console.print("1. 📥 LinkedIn შეტყობინებების შემოწმება (Browser CDP Check)")
            console.print("2. ✍️ რეკრუტერისთვის პასუხის მომზადება (Draft Reply)")
            console.print("3. 📅 გასაუბრების დროის შეთავაზება / დადასტურება")
            console.print("4. 🔄 Pipeline-ში სტატუსის განახლება (Update Status)")
            console.print("5. 👤 კანდიდატის ფაქტებისა და მონაცემების ნახვა")
            console.print(f"6. 🌐 Chrome / Brave-ის გაშვება დებაგ რეჟიმში (Port {config.CDP_PORT})")
            console.print("0. 🚪 გასვლა (Exit)")

            choice = Prompt.ask("შეიყვანეთ ნომერი", choices=["0", "1", "2", "3", "4", "5", "6"], default="1")
        else:
            print("\n1. Check Messages | 2. Draft Reply | 3. Interview Time | 4. Update Status | 5. View Profile | 6. Start Browser | 0. Exit")
            choice = input("Choice: ")

        if choice == "1":
            asyncio.run(run_browser_check())
        elif choice == "2":
            handle_draft_response(generator)
        elif choice == "3":
            if HAS_RICH:
                lang = Prompt.ask("ენა (ka/en)", choices=["ka", "en"], default="en")
                console.print(f"\n[bold green]📅 შემოთავაზებული დროის შაბლონი:[/bold green]\n{scheduler.get_standard_slots(lang)}")
            else:
                print(scheduler.get_standard_slots("en"))
        elif choice == "4":
            handle_update_status(tracker)
            tracker.load_pipeline()
        elif choice == "5":
            show_profile_facts(profile)
        elif choice == "6":
            bat_path = Path(__file__).resolve().parent / "start_browser.bat"
            os.system(f'start cmd /c "{bat_path}"')
        elif choice == "0":
            if HAS_RICH:
                console.print("[bold cyan]ნახვამდის! წარმატებულ გასაუბრებებს გისურვებთ! ✨[/bold cyan]")
            break

        if HAS_RICH:
            Prompt.ask("\n[dim]დააჭირეთ Enter-ს გასაგრძელებლად...[/dim]", default="")

def main():
    parser = argparse.ArgumentParser(description="LinkedIn Job-Seeker Agent CLI")
    parser.add_argument("--status", action="store_true", help="Display pipeline brief report")
    parser.add_argument("--check-browser", action="store_true", help="Check LinkedIn unread messages via CDP")
    parser.add_argument("--draft", type=str, help="Draft a grounded reply to a recruiter message")
    parser.add_argument("--name", type=str, default="", help="Contact name for drafting")

    args = parser.parse_args()

    tracker = PipelineTracker()
    profile = CandidateProfile()
    generator = ResponseGenerator(profile)

    if args.status:
        show_pipeline_summary(tracker)
        return

    if args.check_browser:
        asyncio.run(run_browser_check())
        return

    if args.draft:
        draft, req_appr = generator.draft_llm_response(args.draft, contact_name=args.name)
        print(f"\n[DRAFT]:\n{draft}")
        if req_appr:
            print("\n[WARNING]: Requires user approval before sending.")
        return

    interactive_menu()

if __name__ == "__main__":
    main()
