from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from urllib.parse import urlparse


class PlaywrightBrowser:
    def __init__(
        self,
        profile_path: str | Path,
        headless: bool = False,
        project_root: str | Path | None = None,
    ):
        self.profile_path = Path(profile_path).expanduser().resolve()
        self.headless = headless
        self.project_root = Path(project_root).resolve() if project_root else None
        self._playwright = None
        self.context = None
        self.page = None

    def start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright no está instalado; ejecuta ./setup.sh") from exc
        self.profile_path.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        try:
            launch_options = {
                "headless": self.headless,
                "viewport": {"width": 1280, "height": 900},
            }
            if self.project_root:
                debian_chromium = (
                    self.project_root / ".local-chromium/usr/lib/chromium/chromium"
                )
                if debian_chromium.is_file():
                    launch_options["executable_path"] = str(debian_chromium)
            self.context = self._playwright.chromium.launch_persistent_context(
                str(self.profile_path), **launch_options
            )
        except Exception:
            self._playwright.stop()
            self._playwright = None
            raise
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    @property
    def current_url(self) -> str:
        return self.page.url if self.page else ""

    @staticmethod
    def _validate_web_url(url: str, allow_blank: bool = False) -> None:
        if allow_blank and url == "about:blank":
            return
        if urlparse(url).scheme not in {"http", "https"}:
            raise ValueError("El browser agent solo puede abrir URLs http/https")

    def navigate(self, url: str, **_: object) -> dict:
        self._validate_web_url(url)
        self.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return self._page_state()

    def search(self, query: str, **_: object) -> dict:
        return self.navigate(f"https://duckduckgo.com/?q={quote_plus(query)}")

    def click(self, selector: str, **_: object) -> dict:
        self.page.locator(selector).first.click(timeout=15_000)
        self.page.wait_for_timeout(500)
        return self._page_state()

    def type(self, selector: str, text: str, press_enter: bool = False, **_: object) -> dict:
        locator = self.page.locator(selector).first
        locator.fill(text)
        if press_enter:
            locator.press("Enter")
            self.page.wait_for_timeout(500)
        return {"typed": True, **self._page_state()}

    def scroll(self, amount: int = 700, **_: object) -> dict:
        amount = max(-3000, min(3000, int(amount)))
        self.page.mouse.wheel(0, amount)
        return {"scrolled": amount, **self._page_state()}

    def read(self, selector: str = "body", **_: object) -> dict:
        locator = self.page.locator(selector).first
        text = locator.inner_text(timeout=15_000)[:12_000]
        links = self.page.locator("a:visible").evaluate_all(
            "els => els.slice(0, 80).map(a => ({text: (a.innerText || a.getAttribute('aria-label') || '').trim(), href: a.href}))"
        )
        controls = self.page.locator(
            "a:visible, button:visible, input:visible, textarea:visible, select:visible, [role]:visible"
        ).evaluate_all(
            """els => els.slice(0, 120).map(el => ({
              tag: el.tagName.toLowerCase(), role: el.getAttribute('role') || '',
              accessible_name: el.getAttribute('aria-label') || el.innerText?.trim() || el.placeholder || '',
              id: el.id || '', name: el.getAttribute('name') || '', type: el.getAttribute('type') || '',
              href: el.href || ''
            }))"""
        )
        return {
            **self._page_state(),
            "visible_text": text,
            "links": links,
            "accessible_controls": controls,
        }

    def screenshot(self, **_: object) -> dict:
        directory = self.profile_path.parent / "screenshots"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"browser-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.png"
        self.page.screenshot(path=str(path), full_page=False)
        return {"path": str(path), **self._page_state()}

    def back(self, **_: object) -> dict:
        self.page.go_back(wait_until="domcontentloaded", timeout=30_000)
        return self._page_state()

    def new_tab(self, url: str = "about:blank", **_: object) -> dict:
        self._validate_web_url(url, allow_blank=True)
        self.page = self.context.new_page()
        if url != "about:blank":
            self.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return self._page_state()

    def close_tab(self, **_: object) -> dict:
        if len(self.context.pages) <= 1:
            raise RuntimeError("No se puede cerrar la única pestaña")
        self.page.close()
        self.page = self.context.pages[-1]
        return self._page_state()

    def wait(self, milliseconds: int = 1000, **_: object) -> dict:
        self.page.wait_for_timeout(max(0, min(10_000, int(milliseconds))))
        return self._page_state()

    def _page_state(self) -> dict:
        return {"url": self.page.url, "title": self.page.title()[:500]}

    def close(self) -> None:
        if self.context:
            self.context.close()
        if self._playwright:
            self._playwright.stop()
        self.context = None
        self.page = None
        self._playwright = None
