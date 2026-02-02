import asyncio
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from pathlib import Path

from src.utils.logger import logger

class BrowserAutomationEngine:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def start(self, record_video_dir: Optional[str] = None):
        """Start the Playwright browser session."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            context_args = {"viewport": {"width": 1280, "height": 720}}
            if record_video_dir:
                 context_args["record_video_dir"] = record_video_dir
                 context_args["record_video_size"] = {"width": 1280, "height": 720}
                 
            self.context = await self.browser.new_context(**context_args)
            self.page = await self.context.new_page()
            logger.info(f"Browser started (Headless: {self.headless}, Video: {bool(record_video_dir)})")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

    async def stop(self):
        """Stop the browser session."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser stopped")

    async def navigate(self, url: str):
        """Navigate to a URL."""
        if not self.page:
            raise RuntimeError("Browser not started")
        try:
            await self.page.goto(url, wait_until="networkidle")
            logger.info(f"Navigated to: {url}")
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise

    async def take_screenshot(self, name: str, output_dir: str):
        """Take a screenshot and save it."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        try:
            path = Path(output_dir) / f"{name}.png"
            await self.page.screenshot(path=str(path), full_page=True)
            logger.info(f"Screenshot saved: {path}")
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")

    async def get_page_text(self) -> str:
        """Get visible logical text from the page."""
        if not self.page:
            return ""
        return await self.page.inner_text("body")

    async def click(self, selector: str):
        """Click an element."""
        if not self.page:
            raise RuntimeError("Browser not started")
        await self.page.click(selector)

    async def fill(self, selector: str, text: str):
        """Fill an input field."""
        if not self.page:
            raise RuntimeError("Browser not started")
        await self.page.fill(selector, text)

    async def execute_javascript(self, script: str) -> Any:
        """Execute custom JavaScript."""
        if not self.page:
            return None
        return await self.page.evaluate(script)
