import os
import tempfile
from playwright.sync_api import sync_playwright


def html_to_png(html_content: str, width: int = 480, height: int = 480) -> bytes:
    """HTMLをPlaywrightでレンダリングしてPNGバイトを返す。"""
    with tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(html_content)
        tmp_path = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"file://{tmp_path}")
            page.wait_for_load_state("networkidle")
            # Google Fontsの読み込みを待つ
            page.wait_for_timeout(2000)
            png_bytes = page.screenshot(
                clip={"x": 0, "y": 0, "width": width, "height": height}
            )
            browser.close()
        return png_bytes
    finally:
        os.unlink(tmp_path)
