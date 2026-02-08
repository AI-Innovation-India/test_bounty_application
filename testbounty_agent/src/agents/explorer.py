"""
Explorer Agent - Discovers and maps the entire application
Crawls all pages, identifies forms, buttons, links, and groups into modules
"""

from __future__ import annotations

import asyncio
import json
import platform
import sys
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
import re


class ExplorerAgent:
    """
    Agent that explores an application and creates a complete map of:
    - All pages/routes
    - Forms and input fields
    - Buttons and clickable elements
    - Navigation links
    - Auth-required pages
    - Grouped into logical modules
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.visited_urls: set = set()
        self.pages: List[Dict] = []
        self.modules: Dict[str, Dict] = {}
        self.auth_pages: List[str] = []
        self.browser: Optional[Browser] = None

    async def explore(self, max_pages: int = 50) -> Dict[str, Any]:
        """
        Main exploration method - crawls the entire application
        Returns a complete app map with modules

        On Windows, uses synchronous Playwright in thread pool to avoid async subprocess issue
        """
        # On Windows, use sync version in thread pool to avoid NotImplementedError
        if platform.system() == 'Windows':
            with ThreadPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(executor, self._explore_sync, max_pages)
                return result
        else:
            # On Unix systems, use async version normally
            from playwright.async_api import async_playwright, Page, Browser
            async with async_playwright() as p:
                self.browser = await p.chromium.launch(headless=True)
                context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 720}
                )
                page = await context.new_page()

                # Start exploration from base URL
                await self._explore_page(page, self.base_url, max_pages)

                await self.browser.close()

            # Group pages into modules
            self._group_into_modules()

            return {
                "base_url": self.base_url,
                "total_pages": len(self.pages),
                "pages": self.pages,
                "modules": self.modules,
                "auth_pages": self.auth_pages
            }

    def _explore_sync(self, max_pages: int = 50) -> Dict[str, Any]:
        """
        Synchronous exploration for Windows - avoids async subprocess issues
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = context.new_page()

            # Start exploration from base URL
            self._explore_page_sync(page, self.base_url, max_pages)

            browser.close()

        # Group pages into modules
        self._group_into_modules()

        return {
            "base_url": self.base_url,
            "total_pages": len(self.pages),
            "pages": self.pages,
            "modules": self.modules,
            "auth_pages": self.auth_pages
        }

    async def _explore_page(self, page: Page, url: str, max_pages: int):
        """Explore a single page and discover its elements"""
        if url in self.visited_urls or len(self.visited_urls) >= max_pages:
            return

        # Only explore same domain
        if urlparse(url).netloc != self.domain:
            return

        self.visited_urls.add(url)

        try:
            response = await page.goto(url, wait_until='networkidle', timeout=15000)
            if not response:
                return

            await page.wait_for_timeout(1000)  # Wait for JS to load

            # Extract page information
            page_info = await self._extract_page_info(page, url)
            self.pages.append(page_info)

            # Check if this is an auth page
            if self._is_auth_page(page_info):
                self.auth_pages.append(url)

            # Find and explore linked pages
            links = await self._extract_links(page)
            for link in links:
                full_url = urljoin(url, link)
                if full_url not in self.visited_urls:
                    await self._explore_page(page, full_url, max_pages)

        except Exception as e:
            print(f"Error exploring {url}: {e}")

    async def _extract_page_info(self, page: Page, url: str) -> Dict:
        """Extract all relevant information from a page"""

        # Get page title
        title = await page.title()

        # Extract forms
        forms = await self._extract_forms(page)

        # Extract buttons
        buttons = await self._extract_buttons(page)

        # Extract inputs (outside forms)
        inputs = await self._extract_inputs(page)

        # Extract navigation elements
        nav_links = await self._extract_nav_links(page)

        # Extract modals/dialogs
        modals = await self._extract_modals(page)

        # Detect page type
        page_type = self._detect_page_type(url, title, forms, buttons)

        return {
            "url": url,
            "path": urlparse(url).path or '/',
            "title": title,
            "type": page_type,
            "forms": forms,
            "buttons": buttons,
            "inputs": inputs,
            "nav_links": nav_links,
            "modals": modals,
            "requires_auth": self._requires_auth(url, title)
        }

    async def _extract_forms(self, page: Page) -> List[Dict]:
        """Extract all forms from the page with precise CSS selectors"""
        forms = []
        form_elements = await page.query_selector_all('form')

        for i, form in enumerate(form_elements):
            form_id = await form.get_attribute('id') or f"form_{i}"
            form_action = await form.get_attribute('action') or ''
            form_method = await form.get_attribute('method') or 'get'
            form_class = await form.get_attribute('class') or ''

            # Build form selector - prioritize action, then id, then class
            if form_action and form_action.strip():
                # Use action attribute for most reliable targeting
                form_selector = f"form[action='{form_action}']"
            elif form_id and form_id != f"form_{i}":
                form_selector = f"#{form_id}"
            elif form_class:
                form_selector = f"form.{form_class.split()[0]}"
            else:
                form_selector = f"form:nth-of-type({i+1})"

            # Get form fields with actual selectors
            fields = []
            inputs = await form.query_selector_all('input, select, textarea')
            for inp in inputs:
                inp_type = await inp.get_attribute('type') or 'text'
                inp_name = await inp.get_attribute('name') or ''
                inp_id = await inp.get_attribute('id') or ''
                inp_placeholder = await inp.get_attribute('placeholder') or ''
                inp_required = await inp.get_attribute('required') is not None
                inp_class = await inp.get_attribute('class') or ''

                if inp_type not in ['hidden', 'submit']:
                    # Build the most reliable selector for this input
                    selector = self._build_input_selector(inp_id, inp_name, inp_type, inp_class)

                    fields.append({
                        "type": inp_type,
                        "name": inp_name,
                        "id": inp_id,
                        "placeholder": inp_placeholder,
                        "required": inp_required,
                        "selector": selector  # Actual CSS selector
                    })

            # Get submit button with selector
            submit_btn = await form.query_selector('button[type="submit"], input[type="submit"], .btn-submit, .submit-button, button, input[type="button"]')
            submit_text = ''
            submit_selector = ''
            if submit_btn:
                try:
                    submit_text = await submit_btn.inner_text()
                except:
                    submit_text = await submit_btn.get_attribute('value') or 'Submit'

                btn_id = await submit_btn.get_attribute('id') or ''
                btn_class = await submit_btn.get_attribute('class') or ''
                btn_type = await submit_btn.get_attribute('type') or ''
                tag = await submit_btn.evaluate("el => el.tagName.toLowerCase()")

                # Build submit button selector - prioritize ID, then class, then type
                if btn_id:
                    submit_selector = f"#{btn_id}"
                elif btn_class:
                    # Use the most specific class (prefer classes with 'submit', 'login', 'button')
                    classes = btn_class.split()
                    specific_class = None
                    for cls in classes:
                        if any(keyword in cls.lower() for keyword in ['submit', 'login', 'register', 'signup']):
                            specific_class = cls
                            break
                    if specific_class:
                        submit_selector = f"{tag}.{specific_class}"
                    else:
                        submit_selector = f"{tag}.{classes[0]}"
                elif btn_type == 'submit':
                    submit_selector = f"{form_selector} {tag}[type='submit']"
                else:
                    submit_selector = f"{form_selector} button, {form_selector} input[type='submit']"

            forms.append({
                "id": form_id,
                "selector": form_selector,
                "action": form_action,
                "method": form_method.upper(),
                "fields": fields,
                "submit_text": submit_text.strip() if submit_text else 'Submit',
                "submit_selector": submit_selector
            })

        return forms

    def _build_input_selector(self, inp_id: str, inp_name: str, inp_type: str, inp_class: str) -> str:
        """Build the best CSS selector for an input element"""
        selectors = []

        # ID is most reliable
        if inp_id:
            selectors.append(f"#{inp_id}")

        # Name is second best
        if inp_name:
            selectors.append(f"input[name='{inp_name}']")
            selectors.append(f"[name='{inp_name}']")

        # Type + class combination
        if inp_type and inp_class:
            first_class = inp_class.split()[0]
            selectors.append(f"input[type='{inp_type}'].{first_class}")

        # Just type as fallback
        if inp_type:
            selectors.append(f"input[type='{inp_type}']")

        # Return comma-separated list of selectors to try
        return ", ".join(selectors[:3]) if selectors else "input"

    async def _extract_buttons(self, page: Page) -> List[Dict]:
        """Extract all buttons from the page"""
        buttons = []
        btn_elements = await page.query_selector_all('button, [role="button"], a.btn, a.button, .btn, input[type="button"]')

        seen_texts = set()
        for btn in btn_elements:
            text = (await btn.inner_text()).strip()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)

            btn_id = await btn.get_attribute('id') or ''
            btn_class = await btn.get_attribute('class') or ''
            btn_type = await btn.get_attribute('type') or 'button'
            onclick = await btn.get_attribute('onclick') or ''

            # Determine button action
            action = self._determine_button_action(text, btn_class, onclick)

            buttons.append({
                "text": text,
                "id": btn_id,
                "type": btn_type,
                "action": action
            })

        return buttons

    async def _extract_inputs(self, page: Page) -> List[Dict]:
        """Extract standalone inputs (not in forms)"""
        inputs = []
        # Find inputs not inside forms
        input_elements = await page.query_selector_all('input:not(form input), textarea:not(form textarea)')

        for inp in input_elements:
            inp_type = await inp.get_attribute('type') or 'text'
            if inp_type in ['hidden']:
                continue

            inp_name = await inp.get_attribute('name') or await inp.get_attribute('id') or ''
            inp_placeholder = await inp.get_attribute('placeholder') or ''

            inputs.append({
                "type": inp_type,
                "name": inp_name,
                "placeholder": inp_placeholder
            })

        return inputs

    async def _extract_nav_links(self, page: Page) -> List[Dict]:
        """Extract navigation links"""
        nav_links = []
        # Look for nav elements, sidebars, headers
        nav_elements = await page.query_selector_all('nav a, header a, .sidebar a, .nav a, [role="navigation"] a')

        seen_hrefs = set()
        for link in nav_elements:
            href = await link.get_attribute('href') or ''
            text = (await link.inner_text()).strip()

            if not href or href in seen_hrefs or href.startswith('#') or href.startswith('javascript:'):
                continue
            seen_hrefs.add(href)

            nav_links.append({
                "text": text,
                "href": href
            })

        return nav_links

    async def _extract_modals(self, page: Page) -> List[Dict]:
        """Detect potential modals/dialogs"""
        modals = []
        modal_elements = await page.query_selector_all('[role="dialog"], .modal, [data-modal], [aria-modal="true"]')

        for i, modal in enumerate(modal_elements):
            modal_id = await modal.get_attribute('id') or f"modal_{i}"
            modal_title = ''
            title_el = await modal.query_selector('h1, h2, h3, .modal-title')
            if title_el:
                modal_title = (await title_el.inner_text()).strip()

            modals.append({
                "id": modal_id,
                "title": modal_title
            })

        return modals

    async def _extract_links(self, page: Page) -> List[str]:
        """Extract all links from the page"""
        links = []
        link_elements = await page.query_selector_all('a[href]')

        for link in link_elements:
            href = await link.get_attribute('href')
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                links.append(href)

        return links

    def _detect_page_type(self, url: str, title: str, forms: List, buttons: List) -> str:
        """Detect the type of page based on content"""
        path = urlparse(url).path.lower()
        title_lower = title.lower()

        # Auth pages
        if any(x in path for x in ['/login', '/signin', '/sign-in', '/auth']):
            return 'login'
        if any(x in path for x in ['/register', '/signup', '/sign-up']):
            return 'register'
        if any(x in path for x in ['/forgot', '/reset', '/password']):
            return 'password_reset'

        # Dashboard/Home
        if any(x in path for x in ['/dashboard', '/home', '/overview']):
            return 'dashboard'
        if path == '/' or path == '':
            return 'landing'

        # Settings/Profile
        if any(x in path for x in ['/settings', '/preferences', '/config']):
            return 'settings'
        if any(x in path for x in ['/profile', '/account', '/user']):
            return 'profile'

        # CRUD pages
        if any(x in path for x in ['/create', '/new', '/add']):
            return 'create'
        if any(x in path for x in ['/edit', '/update', '/modify']):
            return 'edit'
        if any(x in path for x in ['/list', '/all', '/index']):
            return 'list'
        if any(x in path for x in ['/view', '/detail', '/show']):
            return 'detail'

        # Check forms
        form_fields = []
        for form in forms:
            form_fields.extend([f['name'].lower() for f in form.get('fields', [])])

        if any(x in form_fields for x in ['email', 'password', 'username']):
            if 'register' in title_lower or 'sign up' in title_lower:
                return 'register'
            return 'login'

        return 'general'

    def _is_auth_page(self, page_info: Dict) -> bool:
        """Check if page is an authentication page"""
        return page_info['type'] in ['login', 'register', 'password_reset']

    def _requires_auth(self, url: str, title: str) -> bool:
        """Determine if page likely requires authentication"""
        path = urlparse(url).path.lower()

        # These pages typically don't require auth
        public_paths = ['/login', '/signin', '/register', '/signup', '/forgot', '/reset', '/about', '/contact', '/pricing']
        if any(p in path for p in public_paths) or path == '/':
            return False

        # These typically require auth
        auth_paths = ['/dashboard', '/settings', '/profile', '/account', '/admin', '/create', '/edit']
        if any(p in path for p in auth_paths):
            return True

        return False  # Default to not requiring auth

    def _determine_button_action(self, text: str, css_class: str, onclick: str) -> str:
        """Determine what action a button performs"""
        text_lower = text.lower()

        if any(x in text_lower for x in ['submit', 'save', 'create', 'add', 'post']):
            return 'submit'
        if any(x in text_lower for x in ['delete', 'remove', 'trash']):
            return 'delete'
        if any(x in text_lower for x in ['edit', 'update', 'modify']):
            return 'edit'
        if any(x in text_lower for x in ['cancel', 'close', 'back']):
            return 'cancel'
        if any(x in text_lower for x in ['login', 'sign in', 'signin']):
            return 'login'
        if any(x in text_lower for x in ['logout', 'sign out', 'signout']):
            return 'logout'
        if any(x in text_lower for x in ['search', 'find']):
            return 'search'
        if any(x in text_lower for x in ['download', 'export']):
            return 'download'
        if any(x in text_lower for x in ['upload', 'import']):
            return 'upload'

        return 'click'

    def _group_into_modules(self):
        """Group discovered pages into logical modules"""
        module_mapping = {
            'auth': ['login', 'register', 'password_reset'],
            'dashboard': ['dashboard', 'landing'],
            'profile': ['profile', 'settings'],
            'crud': ['create', 'edit', 'list', 'detail'],
            'general': ['general']
        }

        for module_name, page_types in module_mapping.items():
            module_pages = [p for p in self.pages if p['type'] in page_types]
            if module_pages:
                self.modules[module_name] = {
                    "name": module_name.title(),
                    "pages": module_pages,
                    "requires_auth": any(p['requires_auth'] for p in module_pages),
                    "page_count": len(module_pages)
                }


    def _explore_page_sync(self, page, url: str, max_pages: int):
        """Synchronous version of _explore_page for Windows"""
        if url in self.visited_urls or len(self.visited_urls) >= max_pages:
            return

        # Only explore same domain
        if urlparse(url).netloc != self.domain:
            return

        self.visited_urls.add(url)

        try:
            response = page.goto(url, wait_until='networkidle', timeout=15000)
            if not response:
                return

            page.wait_for_timeout(1000)  # Wait for JS to load

            # Extract page information
            page_info = self._extract_page_info_sync(page, url)
            self.pages.append(page_info)

            # Check if this is an auth page
            if self._is_auth_page(page_info):
                self.auth_pages.append(url)

            # Find and explore linked pages
            links = self._extract_links_sync(page)
            for link in links:
                full_url = urljoin(url, link)
                if full_url not in self.visited_urls:
                    self._explore_page_sync(page, full_url, max_pages)

        except Exception as e:
            print(f"Error exploring {url}: {e}")

    def _extract_page_info_sync(self, page, url: str) -> Dict:
        """Synchronous version of _extract_page_info for Windows"""
        # Get page title
        title = page.title()

        # Extract forms
        forms = self._extract_forms_sync(page)

        # Extract buttons
        buttons = self._extract_buttons_sync(page)

        # Extract inputs (outside forms)
        inputs = self._extract_inputs_sync(page)

        # Extract navigation elements
        nav_links = self._extract_nav_links_sync(page)

        # Extract modals/dialogs
        modals = self._extract_modals_sync(page)

        # Detect page type
        page_type = self._detect_page_type(url, title, forms, buttons)

        return {
            "url": url,
            "path": urlparse(url).path or '/',
            "title": title,
            "type": page_type,
            "forms": forms,
            "buttons": buttons,
            "inputs": inputs,
            "nav_links": nav_links,
            "modals": modals,
            "requires_auth": self._requires_auth(url, title)
        }

    def _extract_forms_sync(self, page) -> List[Dict]:
        """Synchronous version of _extract_forms for Windows"""
        forms = []
        form_elements = page.query_selector_all('form')

        for i, form in enumerate(form_elements):
            form_id = form.get_attribute('id') or f"form_{i}"
            form_action = form.get_attribute('action') or ''
            form_method = form.get_attribute('method') or 'get'
            form_class = form.get_attribute('class') or ''

            # Build form selector - prioritize action, then id, then class
            if form_action and form_action.strip():
                form_selector = f"form[action='{form_action}']"
            elif form_id and form_id != f"form_{i}":
                form_selector = f"#{form_id}"
            elif form_class:
                form_selector = f"form.{form_class.split()[0]}"
            else:
                form_selector = f"form:nth-of-type({i+1})"

            # Get form fields with actual selectors
            fields = []
            inputs = form.query_selector_all('input, select, textarea')
            for inp in inputs:
                inp_type = inp.get_attribute('type') or 'text'
                inp_name = inp.get_attribute('name') or ''
                inp_id = inp.get_attribute('id') or ''
                inp_placeholder = inp.get_attribute('placeholder') or ''
                inp_required = inp.get_attribute('required') is not None
                inp_class = inp.get_attribute('class') or ''

                if inp_type not in ['hidden', 'submit']:
                    selector = self._build_input_selector(inp_id, inp_name, inp_type, inp_class)

                    fields.append({
                        "type": inp_type,
                        "name": inp_name,
                        "id": inp_id,
                        "placeholder": inp_placeholder,
                        "required": inp_required,
                        "selector": selector
                    })

            # Get submit button with selector
            submit_btn = form.query_selector('button[type="submit"], input[type="submit"], .btn-submit, .submit-button, button, input[type="button"]')
            submit_text = ''
            submit_selector = ''
            if submit_btn:
                try:
                    submit_text = submit_btn.inner_text()
                except:
                    submit_text = submit_btn.get_attribute('value') or 'Submit'

                btn_id = submit_btn.get_attribute('id') or ''
                btn_class = submit_btn.get_attribute('class') or ''
                btn_type = submit_btn.get_attribute('type') or ''
                tag = submit_btn.evaluate("el => el.tagName.toLowerCase()")

                # Build submit button selector
                if btn_id:
                    submit_selector = f"#{btn_id}"
                elif btn_class:
                    classes = btn_class.split()
                    specific_class = None
                    for cls in classes:
                        if any(keyword in cls.lower() for keyword in ['submit', 'login', 'register', 'signup']):
                            specific_class = cls
                            break
                    if specific_class:
                        submit_selector = f"{tag}.{specific_class}"
                    else:
                        submit_selector = f"{tag}.{classes[0]}"
                elif btn_type == 'submit':
                    submit_selector = f"{form_selector} {tag}[type='submit']"
                else:
                    submit_selector = f"{form_selector} button, {form_selector} input[type='submit']"

            forms.append({
                "id": form_id,
                "selector": form_selector,
                "action": form_action,
                "method": form_method.upper(),
                "fields": fields,
                "submit_text": submit_text.strip() if submit_text else 'Submit',
                "submit_selector": submit_selector
            })

        return forms

    def _extract_buttons_sync(self, page) -> List[Dict]:
        """Synchronous version of _extract_buttons for Windows"""
        buttons = []
        btn_elements = page.query_selector_all('button, [role="button"], a.btn, a.button, .btn, input[type="button"]')

        seen_texts = set()
        for btn in btn_elements:
            text = btn.inner_text().strip()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)

            btn_id = btn.get_attribute('id') or ''
            btn_class = btn.get_attribute('class') or ''
            btn_type = btn.get_attribute('type') or 'button'
            onclick = btn.get_attribute('onclick') or ''

            action = self._determine_button_action(text, btn_class, onclick)

            buttons.append({
                "text": text,
                "id": btn_id,
                "type": btn_type,
                "action": action
            })

        return buttons

    def _extract_inputs_sync(self, page) -> List[Dict]:
        """Synchronous version of _extract_inputs for Windows"""
        inputs = []
        input_elements = page.query_selector_all('input:not(form input), textarea:not(form textarea)')

        for inp in input_elements:
            inp_type = inp.get_attribute('type') or 'text'
            if inp_type in ['hidden']:
                continue

            inp_name = inp.get_attribute('name') or inp.get_attribute('id') or ''
            inp_placeholder = inp.get_attribute('placeholder') or ''

            inputs.append({
                "type": inp_type,
                "name": inp_name,
                "placeholder": inp_placeholder
            })

        return inputs

    def _extract_nav_links_sync(self, page) -> List[Dict]:
        """Synchronous version of _extract_nav_links for Windows"""
        nav_links = []
        nav_elements = page.query_selector_all('nav a, header a, .sidebar a, .nav a, [role="navigation"] a')

        seen_hrefs = set()
        for link in nav_elements:
            href = link.get_attribute('href') or ''
            text = link.inner_text().strip()

            if not href or href in seen_hrefs or href.startswith('#') or href.startswith('javascript:'):
                continue
            seen_hrefs.add(href)

            nav_links.append({
                "text": text,
                "href": href
            })

        return nav_links

    def _extract_modals_sync(self, page) -> List[Dict]:
        """Synchronous version of _extract_modals for Windows"""
        modals = []
        modal_elements = page.query_selector_all('[role="dialog"], .modal, [data-modal], [aria-modal="true"]')

        for i, modal in enumerate(modal_elements):
            modal_id = modal.get_attribute('id') or f"modal_{i}"
            modal_title = ''
            title_el = modal.query_selector('h1, h2, h3, .modal-title')
            if title_el:
                modal_title = title_el.inner_text().strip()

            modals.append({
                "id": modal_id,
                "title": modal_title
            })

        return modals

    def _extract_links_sync(self, page) -> List[str]:
        """Synchronous version of _extract_links for Windows"""
        links = []
        link_elements = page.query_selector_all('a[href]')

        for link in link_elements:
            href = link.get_attribute('href')
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                links.append(href)

        return links


async def explore_application(url: str, max_pages: int = 50) -> Dict[str, Any]:
    """
    Convenience function to explore an application
    """
    explorer = ExplorerAgent(url)
    return await explorer.explore(max_pages)


if __name__ == "__main__":
    # Test exploration
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    result = asyncio.run(explore_application(url))
    print(json.dumps(result, indent=2))
