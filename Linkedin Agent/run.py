"""
LinkedIn Agent - Interactive Terminal & CLI Runner
"""
import sys
import os
import argparse
import asyncio
import warnings
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Any

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
    name = (profile.get_candidate_name() if profile else "") or "Candidate"
    roles = profile.get_target_roles() if profile else []
    primary_role = roles[0] if roles else "Job-Seeker"
    candidate_label = f"{name} ({primary_role})"
    if len(candidate_label) > 45:
        candidate_label = candidate_label[:42] + "..."
    if HAS_RICH:
        from rich.markup import escape
        from rich import box
        safe_label = escape(candidate_label)
        console.print(
            Panel(
                f"[bold cyan]💼 LINKEDIN JOB-SEEKER AGENT[/bold cyan]\n[bold white]Candidate:[/bold white] [bold yellow]{safe_label}[/bold yellow]",
                box=box.DOUBLE,
                style="cyan",
                expand=False,
                padding=(0, 6)
            )
        )
    else:
        print("=" * 60)
        print(f"LinkedIn Job-Seeker Agent - {candidate_label}")
        print("=" * 60)

def show_pipeline_summary(tracker: PipelineTracker):
    report_bullets = tracker.generate_brief_report(max_bullets=5)
    if HAS_RICH:
        panel_content = "\n".join([f"• {b}" for b in report_bullets])
        console.print(Panel(panel_content, title="[bold green]📋 Pipeline summary (≤ 5 bullets)[/bold green]", expand=False))
    else:
        print("\n--- Pipeline summary ---")
        for b in report_bullets:
            print(f"- {b}")

def show_profile_facts(profile: CandidateProfile):
    def _val(v: Any) -> str:
        if not v or CandidateProfile.is_placeholder(str(v)) or str(v).startswith("[Not configured"):
            return "[not set]"
        return str(v)

    if HAS_RICH:
        table = Table(title="👤 Candidate facts")
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        all_roles = profile.get_target_roles()
        roles_display = ", ".join(all_roles[:3])
        if len(all_roles) > 3:
            roles_display += "..."
        table.add_row("Candidate", _val(profile.get_candidate_name()))
        table.add_row("Target roles", roles_display if roles_display else "[not set]")
        table.add_row("Salary expectation", _val(profile.get_salary_expectation()))
        table.add_row("Notice Period", _val(profile.get_preferences().get("notice_period")))
        table.add_row("Work mode", _val(profile.get_preferences().get("work_mode")))
        table.add_row("Relocation", _val(profile.get_preferences().get("relocation")))
        table.add_row("Contact e-mail", _val(profile.get_contacts().get("email")))
        table.add_row("CV file", _val(profile.get_cv_file_path(strict=False)))

        console.print(table)
    else:
        print("\n--- Candidate facts ---")
        print("Name:", _val(profile.get_candidate_name()))
        print("Salary:", _val(profile.get_salary_expectation()))
        prefs = profile.get_preferences()
        print("Work mode:", _val(prefs.get("work_mode")))
        print("Notice Period:", _val(prefs.get("notice_period")))
        print("Relocation:", _val(prefs.get("relocation")))
        print("Contact e-mail:", _val(profile.get_contacts().get("email")))
        print("CV file:", _val(profile.get_cv_file_path(strict=False)))

async def run_browser_check():
    controller = LinkedInBrowserController()
    if HAS_RICH:
        console.print(f"[yellow]🌐 Connecting to Chrome/Brave on CDP port ({config.CDP_PORT})...[/yellow]")
    else:
        print(f"Connecting to browser on port {config.CDP_PORT}...")

    try:
        await controller.connect()
        if HAS_RICH:
            console.print("[green]✔ Connected. Checking LinkedIn messages (with pacing rules)...[/green]")
        else:
            print("Connected. Checking messages...")

        messages = await controller.check_unread_messages()

        if not messages:
            msg = "No new messages: every conversation is waiting on the other side."
            if HAS_RICH:
                console.print(f"[bold green]{msg}[/bold green]")
            else:
                print(msg)
        else:
            if HAS_RICH:
                table = Table(title="📥 Latest messages")
                table.add_column("#", style="dim")
                table.add_column("Contact", style="cyan")
                table.add_column("Unread", style="red")
                table.add_column("Snippet", style="white")

                for m in messages:
                    table.add_row(
                        str(m["index"] + 1),
                        m["name"],
                        "🔴 yes" if m["is_unread"] else "⚪ no",
                        m["snippet"][:60] + "..." if len(m["snippet"]) > 60 else m["snippet"]
                    )
                console.print(table)
            else:
                for m in messages:
                    print(f"[{'UNREAD' if m['is_unread'] else 'READ'}] {m['name']}: {m['snippet']}")

    except Exception as e:
        if HAS_RICH:
            console.print(f"[bold red]❌ Error:[/bold red] {e}")
            console.print(f"[yellow]💡 Tip: start the browser with `start_browser.bat` or `--remote-debugging-port={config.CDP_PORT}` first.[/yellow]")
        else:
            print(f"Error: {e}")
    finally:
        await controller.disconnect()

def handle_draft_response(generator: ResponseGenerator):
    has_ai = bool(generator.client or generator.legacy_model)
    if HAS_RICH:
        console.print("\n[bold cyan]✍️ Draft a reply[/bold cyan]")
        if has_ai:
            console.print(f"[dim green]🤖 AI Engine: Active ({config.DEFAULT_MODEL})[/dim green]")
        else:
            console.print("[dim yellow]📋 Mode: offline templates (for AI drafts set GEMINI_API_KEY in .env and install requirements-optional.txt)[/dim yellow]")
        contact_name = Prompt.ask("Recruiter name (e.g. Sarah)", default="")
        hr_message = Prompt.ask("Text of the recruiter's message")
    else:
        contact_name = input("Contact Name: ")
        hr_message = input("HR Message: ")

    draft, requires_approval = generator.draft_llm_response(hr_message, contact_name=contact_name)

    if HAS_RICH:
        status_color = "red" if requires_approval else "green"
        warning = "[bold red]⚠️ This reply mentions salary or a meeting time: review and approve it before sending![/bold red]\n" if requires_approval else ""
        console.print(Panel(f"{warning}[bold white]{draft}[/bold white]", title="[bold green]📝 Draft reply[/bold green]"))
    else:
        print("\n--- Draft reply ---")
        if requires_approval:
            print("⚠️ REQUIRES APPROVAL BEFORE SENDING")
        print(draft)

def handle_update_status(tracker: PipelineTracker):
    if HAS_RICH:
        console.print("\n[bold cyan]🔄 Update a conversation's status[/bold cyan]")
        search_term = Prompt.ask("Company or contact name (e.g. TechCorp, Acme)")
        status_options = ["waiting", "pending-user", "scheduled", "in-progress", "closed"]
        new_status = Prompt.ask(f"New status ({'/'.join(status_options)})", choices=status_options, default="waiting")
    else:
        search_term = input("Search term (Company/Contact): ")
        new_status = input("New status (waiting/pending-user/scheduled/in-progress/closed): ")

    success = tracker.update_status(search_term, new_status)
    if success:
        if HAS_RICH:
            console.print(f"[bold green]✔ Status updated: '{search_term}' -> `{new_status}`[/bold green]")
        else:
            print(f"Status updated: {search_term} -> {new_status}")
    else:
        if HAS_RICH:
            console.print(f"[bold red]❌ No pipeline entry matches '{search_term}'.[/bold red]")
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
            console.print("\n[bold yellow]Choose an action:[/bold yellow]")
            console.print("1. 📥 Check LinkedIn messages (browser, CDP)")
            console.print("2. ✍️ Draft a reply to a recruiter")
            console.print("3. 📅 Propose / confirm interview times")
            console.print("4. 🔄 Update a pipeline status")
            console.print("5. 👤 Show candidate facts")
            console.print(f"6. 🌐 Start Chrome / Brave in debug mode (port {config.CDP_PORT})")
            console.print("0. 🚪 Exit")

            choice = Prompt.ask("Enter a number", choices=["0", "1", "2", "3", "4", "5", "6"], default="1")
        else:
            print("\n1. Check Messages | 2. Draft Reply | 3. Interview Time | 4. Update Status | 5. View Profile | 6. Start Browser | 0. Exit")
            choice = input("Choice: ")

        if choice == "1":
            asyncio.run(run_browser_check())
        elif choice == "2":
            handle_draft_response(generator)
        elif choice == "3":
            if HAS_RICH:
                lang = Prompt.ask("Language of the message (ka/en)", choices=["ka", "en"], default="en")
                console.print(f"\n[bold green]📅 Suggested interview slots:[/bold green]\n{scheduler.get_standard_slots(lang)}")
            else:
                print(scheduler.get_standard_slots("en"))
        elif choice == "4":
            handle_update_status(tracker)
            tracker.load_pipeline()
        elif choice == "5":
            show_profile_facts(profile)
        elif choice == "6":
            base_dir = Path(__file__).resolve().parent
            if sys.platform == "win32":
                bat_path = base_dir / "start_browser.bat"
                os.system(f'start cmd /c "{bat_path}"')
            else:
                sh_path = base_dir / "start_browser.sh"
                if sh_path.exists():
                    os.system(f'bash "{sh_path}" &')
                else:
                    candidates = []
                    if sys.platform == "darwin":
                        candidates.extend([
                            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                            "/Applications/Chromium.app/Contents/MacOS/Chromium",
                        ])
                    candidates.extend([
                        shutil.which("google-chrome"),
                        shutil.which("google-chrome-stable"),
                        shutil.which("brave-browser"),
                        shutil.which("chromium"),
                        shutil.which("chromium-browser"),
                    ])
                    browser_bin = next((c for c in candidates if c and (os.path.isfile(c) or shutil.which(c))), None)
                    if browser_bin:
                        subprocess.Popen(
                            [browser_bin, f"--remote-debugging-port={config.CDP_PORT}", f"--user-data-dir={config.USER_DATA_DIR}"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                    else:
                        msg = f"⚠️ Chrome/Brave not found. Start a browser yourself with: --remote-debugging-port={config.CDP_PORT}"
                        if HAS_RICH:
                            console.print(f"[yellow]{msg}[/yellow]")
                        else:
                            print(msg)
        elif choice == "0":
            if HAS_RICH:
                console.print("[bold cyan]Goodbye, and good luck with your interviews! ✨[/bold cyan]")
            break

        if HAS_RICH:
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")

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
