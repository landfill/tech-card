"""목록 페이지 크롤링 수집. Playwright 단일 방식(폴백 없음). JS 렌더링 후 제목·링크·요약 추출. RSS 없는 사이트용."""
import asyncio
from urllib.parse import urljoin

from playwright.async_api import async_playwright

# 크롤링은 Playwright 단일 방식만 사용. HTTP/파서 폴백 없음.

_JS_EXTRACT = """
(args) => {
  const tags = args.tags.map(t => t.toLowerCase());
  const headings = document.querySelectorAll(args.selector);
  const out = [];
  for (const h of headings) {
    const title = (h.innerText || '').trim();
    if (title.length < 3) continue;
    let link = null;
    const a = h.querySelector('a[href]');
    if (a) link = a.getAttribute('href');
    let summary = '';
    let el = h.nextElementSibling;
    while (el && !tags.includes(el.tagName.toLowerCase())) {
      summary += (el.innerText || '').trim() + ' ';
      if (!link && el.tagName === 'A' && el.getAttribute('href'))
        link = el.getAttribute('href');
      else if (!link && el.querySelector('a[href]'))
        link = el.querySelector('a[href]').getAttribute('href');
      el = el.nextElementSibling;
    }
    out.push({
      title: title.slice(0, 500),
      url: link || '',
      summary: summary.trim().slice(0, 2000)
    });
  }
  return out;
}
"""


async def fetch_crawl_async(
    url: str,
    source_id: str = "",
    *,
    heading_tags: list[str] | None = None,
    max_items: int = 50,
    timeout: float = 15.0,
    wait_until: str = "domcontentloaded",
    browser=None,
) -> list[dict]:
    """목록/뉴스 페이지를 Playwright로 로드한 뒤, h2/h3 등 제목과 다음 블록(요약)·링크를 추출.

    browser가 넘어오면 해당 브라우저에서 page만 생성해 사용하고 닫지 않음.
    browser가 None이면 async_playwright()로 브라우저를 생성했다가 종료함.

    각 항목: source_id, title, url, summary, published (published는 비움).
    """
    heading_tags = heading_tags or ["h2", "h3"]
    selector = ", ".join(heading_tags)
    timeout_ms = int(timeout * 1000)
    own_browser = False
    if browser is None:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        own_browser = True

    results = []
    try:
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=timeout_ms, wait_until=wait_until)
            try:
                await page.wait_for_selector(selector, timeout=min(10000, timeout_ms))
            except Exception:
                pass
        except Exception as e:
            await page.close()
            if own_browser:
                await browser.close()
            raise RuntimeError(f"Failed to load {url}: {e}") from e

        base = page.url
        raw = await page.evaluate(
            _JS_EXTRACT,
            {"selector": selector, "tags": heading_tags},
        )
        await page.close()

        for item in raw[:max_items]:
            link = (item.get("url") or "").strip()
            if link:
                link = urljoin(base, link)
            else:
                link = base
            results.append({
                "source_id": source_id,
                "title": (item.get("title") or "")[:500],
                "url": link,
                "summary": (item.get("summary") or "")[:2000],
                "published": "",
            })
    finally:
        if own_browser:
            await browser.close()

    return results


def fetch_crawl(
    url: str,
    source_id: str = "",
    *,
    heading_tags: list[str] | None = None,
    max_items: int = 50,
    timeout: float = 15.0,
    wait_until: str = "domcontentloaded",
) -> list[dict]:
    """동기 래퍼. 단일 URL·테스트용. asyncio.run(fetch_crawl_async(...)) 호출."""
    return asyncio.run(
        fetch_crawl_async(
            url,
            source_id,
            heading_tags=heading_tags,
            max_items=max_items,
            timeout=timeout,
            wait_until=wait_until,
        )
    )
