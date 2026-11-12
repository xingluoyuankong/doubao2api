"""lzA6-derived a_bogus signing fallback (single attempt, lazy browser).

Design (see integrated/DESIGN.md §6):
- Main path is wang pure HTTP and never touches a browser.
- Only when the pure-HTTP request fails with a signature/risk-control
  class error do we call this module, exactly once.
- The browser is launched lazily, used for one frontierSign call, then
  closed. It is never kept resident (AWS has ~899 MB available; a resident
  Chromium at 300-800 MB does not fit).
- No retry loop here: a second failure propagates as an error.

Adapted from sources/lza6/app/services/playwright_manager.py
(get_signed_url: sort params alphabetically, add the static device
fingerprint + msToken, call window.byted_acrawler.frontierSign).
No credential or fingerprint value from the upstream repo is copied here;
callers must supply the fingerprint from the deployment's own session.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Optional
from urllib.parse import urlencode


class SigningUnavailable(RuntimeError):
    pass


SIGNATURE_ERROR_HINTS = ("a_bogus", "msToken", "frontierSign", "签名", "风控", "验证码", "captcha")


def is_signature_error(text: str) -> bool:
    low = (text or "").lower()
    return any(h.lower() in low for h in SIGNATURE_ERROR_HINTS) or " 401" in low or " 403" in low


async def sign_url_once(base_url: str, base_params: Dict[str, str],
                        fingerprint: Dict[str, str], ms_token: Optional[str],
                        timeout_s: float = 30.0) -> str:
    """Return the a_bogus-signed URL, or raise SigningUnavailable.

    Raises SigningUnavailable (never retries) when Playwright is missing,
    the browser cannot start, frontierSign is absent, or msToken is missing.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - depends on deployment env
        raise SigningUnavailable("Playwright 未安装：签名兜底不可用") from exc
    if not ms_token:
        raise SigningUnavailable("无 msToken：无法构建签名请求")
    params = dict(base_params)
    params.update(fingerprint)
    params["msToken"] = ms_token
    query = urlencode(dict(sorted(params.items())))
    url_with_params = f"{base_url}?{query}"
    try:
        async with asyncio.timeout(timeout_s):
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True,
                                                   args=["--no-sandbox", "--disable-setuid-sandbox"])
                try:
                    page = await browser.new_page()
                    await page.goto("https://www.doubao.com", wait_until="domcontentloaded")
                    await page.wait_for_function(
                        "() => typeof window.byted_acrawler?.frontierSign === 'function'",
                        timeout=30000)
                    sig = await page.evaluate(
                        f'window.byted_acrawler.frontierSign("{query}")')
                finally:
                    await browser.close()
    except Exception as exc:
        raise SigningUnavailable(f"签名兜底失败：{type(exc).__name__}") from exc
    if isinstance(sig, dict):
        bogus = sig.get("X-Bogus") or sig.get("a_bogus") or ""
    else:
        bogus = str(sig or "")
    if not bogus:
        raise SigningUnavailable("frontierSign 未返回 a_bogus")
    sep = "&" if "?" in url_with_params else "?"
    return f"{url_with_params}{sep}a_bogus={bogus}"
