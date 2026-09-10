"""
Browser Controller: Playwright CDP controller with human-like pacing and safety constraints.
Connects to an existing Chrome/Brave session on http://localhost:9222.
"""
import time
import asyncio
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

class LinkedInBrowserController:
    def __init__(self, cdp_endpoint: str = config.CDP_ENDPOINT):
        self.cdp_endpoint = cdp_endpoint
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_conversations_opened = 0

    async def connect(self) -> bool:
        """Connects to the remote debugging Chrome/Brave browser via CDP or launches persistent context."""
        if not HAS_PLAYWRIGHT:
            raise ImportError("Playwright is not installed. Run: pip install playwright")

        self.playwright = await async_playwright().start()

        # Step 1: Try connecting over CDP
        try:
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_endpoint)
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                pages = self.context.pages
                self.page = pages[0] if pages else await self.context.new_page()
            else:
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
            return True
        except Exception:
            pass

        # Step 2: Fallback to launching persistent browser context
        config.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            # Check for Chrome or standard channel
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(config.USER_DATA_DIR),
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            pages = self.context.pages
            self.page = pages[0] if pages else await self.context.new_page()
            return True
        except Exception as e:
            await self.disconnect()
            raise ConnectionError(f"Could not connect via CDP or launch persistent context: {e}")

    async def disconnect(self) -> None:
        """Disconnects cleanly without closing the user's browser."""
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

    async def _check_safety_checkpoint(self) -> bool:
        """Checks if LinkedIn is showing a CAPTCHA or security challenge."""
        if not self.page:
            return False
        content = await self.page.content()
        if "checkpoint/challenge" in self.page.url or "captcha" in content.lower() or "unusual activity" in content.lower():
            return True
        return False

    async def navigate_to_messaging_with_pacing(self) -> bool:
        """
        Follows human-like pacing rules:
        1. Opens linkedin.com/feed/ first
        2. Pauses 2-3s
        3. Navigates to Messaging
        """
        if not self.page:
            return False

        # Step 1: Open Feed
        await self.page.goto(config.LINKEDIN_FEED_URL, wait_until="domcontentloaded")
        await asyncio.sleep(config.PAGE_LOAD_WAIT_SEC)

        if await self._check_safety_checkpoint():
            raise SecurityError("LinkedIn CAPTCHA or security checkpoint detected! Stopping immediately.")

        # Step 2: Navigate to messaging
        messaging_nav = self.page.locator('a[href*="/messaging/"], button[aria-label*="Messaging"]').first
        if await messaging_nav.is_visible():
            await messaging_nav.hover()
            await asyncio.sleep(config.HOVER_DELAY_SEC)
            await messaging_nav.click()
        else:
            await self.page.goto(config.LINKEDIN_MESSAGING_URL, wait_until="domcontentloaded")

        await asyncio.sleep(config.PAGE_LOAD_WAIT_SEC)
        return True

    async def check_unread_messages(self) -> List[Dict[str, str]]:
        """
        Inspects the conversations list for unread badges and active threads.
        Limit: Reads max 5 conversations per session.
        """
        if not self.page:
            return []

        await self.navigate_to_messaging_with_pacing()

        # Scroll conversation list slightly
        conversations_container = self.page.locator(".msg-conversations-container__conversations-list").first
        if await conversations_container.is_visible():
            await conversations_container.evaluate("el => el.scrollBy(0, 150)")
            await asyncio.sleep(1.0)

        # Find conversation list items
        conv_items = self.page.locator("li.msg-conversation-listitem")
        count = await conv_items.count()
        results = []

        for i in range(min(count, config.MAX_CONVERSATIONS_PER_SESSION)):
            item = conv_items.nth(i)
            text_content = await item.inner_text()
            lines = [l.strip() for l in text_content.split("\n") if l.strip()]

            # Determine if unread
            is_unread = await item.locator(".msg-conversation-card__unread-count, .notification-badge").is_visible()

            name = lines[0] if lines else f"Contact #{i+1}"
            snippet = lines[1] if len(lines) > 1 else ""

            results.append({
                "index": i,
                "name": name,
                "snippet": snippet,
                "is_unread": is_unread,
                "raw": text_content
            })

        return results

    async def type_and_send_message(self, message_text: str) -> bool:
        """
        Types message with human-like pacing and character delay into active chat.
        """
        if not self.page:
            return False

        # Locate messaging input
        textbox = self.page.locator('div[role="textbox"][aria-label*="Write a message"], .msg-form__contenteditable').first
        if not await textbox.is_visible():
            raise RuntimeError("Could not find LinkedIn message input box.")

        await textbox.hover()
        await asyncio.sleep(config.HOVER_DELAY_SEC)
        await textbox.click()
        await asyncio.sleep(config.BEFORE_TYPING_WAIT_SEC)

        # Type slowly character by character
        for char in message_text:
            await self.page.keyboard.type(char)
            await asyncio.sleep(config.TYPING_DELAY_MS / 1000.0)

        await asyncio.sleep(1.5)

        # Locate and click Send button
        send_btn = self.page.locator('button.msg-form__send-button, button[type="submit"][aria-label*="Send"]').first
        if await send_btn.is_visible() and not await send_btn.is_disabled():
            await send_btn.hover()
            await asyncio.sleep(config.HOVER_DELAY_SEC)
            await send_btn.click()
            await asyncio.sleep(config.PAGE_LOAD_WAIT_SEC)
            return True

        return False
