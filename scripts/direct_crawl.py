"""
Direct VL jeonse scraper — navigable API interception with anti-detection.
Critical: removes navigator.webdriver (what Naver checks for bot detection).
"""

import asyncio
import json
import csv
import re
import os
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
OUTPUT_DIR = Path(__file__).resolve().parent / "naverland-scrapper" / "data"
SESSION_DIR = OUTPUT_DIR / "playwright_profiles"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

TARGET_DONGS = [
    ("홍제동", 37.586, 126.947),
    ("홍은동", 37.593, 126.933),
    ("연희동", 37.572, 126.933),
    ("남가좌동", 37.579, 126.921),
    ("북가좌동", 37.581, 126.912),
    ("신사동", 37.596, 126.911),
    ("응암동", 37.592, 126.918),
]

# Dongs already processed (to avoid re-crawling if we restart)
COMPLETED_DONGS = set()


async def crawl_dong(name, lat, lon):
    """Crawl one dong by capturing Naver API responses in headed Chrome."""
    from playwright.async_api import async_playwright

    listings = []

    async with async_playwright() as p:
        # Try local Chrome first (matches app behavior)
        chrome_path = None
        for candidate in [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]:
            if os.path.exists(candidate):
                chrome_path = candidate
                break

        launch_kwargs = {
            "headless": False,
        }
        if chrome_path:
            launch_kwargs["executable_path"] = chrome_path
            print(f"  Using Chrome: {chrome_path}")
            browser = await p.chromium.launch(**launch_kwargs)
        else:
            print("  Using Playwright Chromium")
            browser = await p.chromium.launch(**launch_kwargs)

        # Try to reuse session cookies from previous run
        session_file = SESSION_DIR / "desktop_storage_state.json"
        context_kwargs = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "locale": "ko-KR",
        }
        if session_file.exists():
            try:
                context_kwargs["storage_state"] = str(session_file)
                print(f"  Reusing session: {session_file}")
            except Exception:
                pass

        context = await browser.new_context(**context_kwargs)

        # Block heavy resources (images, fonts, media)
        async def block_heavy(route):
            if route.request.resource_type in ("image", "media", "font"):
                await route.abort()
                return
            await route.continue_()

        await context.route("**/*", block_heavy)

        page = await context.new_page()

        # ---- CRITICAL: Remove navigator.webdriver (Naver bot detection) ----
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        # Intercept API responses
        captured_responses = []

        async def on_response(response):
            url = response.url
            if "api/articles" in url and response.status == 200:
                try:
                    data = await response.json()
                    captured_responses.append({
                        "url": url,
                        "data": data,
                    })
                except Exception:
                    pass

        page.on("response", on_response)

        # Warm up — navigate to Naver first to get cookies
        try:
            await page.goto("https://new.land.naver.com/", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
        except Exception:
            pass

        # Navigate to VL jeonse list view
        url = f"https://new.land.naver.com/houses?ms={lat},{lon},15&a=VL&b=B1&e=RETAIL"
        print(f"  Navigating: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"  [WARN] page.goto timeout: {e}")

        # Wait for dynamic content and API calls
        await asyncio.sleep(3)

        # Check if we're getting content
        title = ""
        try:
            title = await page.title()
        except Exception:
            pass
        print(f"  Page title: {title}")

        # Scroll to trigger lazy loading
        for i in range(8):
            try:
                await page.evaluate("window.scrollBy(0, 600)")
                await asyncio.sleep(2)
            except Exception:
                pass

        # Parse all captured API responses
        seen_article_nos = set()
        for cap in captured_responses:
            data = cap["data"]
            articles = []
            if isinstance(data, dict):
                articles = data.get("articleList", [])
                if not articles:
                    articles = data.get("list", [])
            elif isinstance(data, list):
                articles = data

            for art in articles:
                if not isinstance(art, dict):
                    continue
                ano = str(art.get("articleNo", art.get("article_no", "")))
                if not ano or ano in seen_article_nos:
                    continue
                seen_article_nos.add(ano)

                trade = art.get("tradeType", art.get("trade_type", ""))
                if trade and "B1" not in str(trade) and "전세" not in str(trade):
                    continue

                deposit = art.get("dealPrice", art.get("price", art.get("deposit", "")))
                listings.append({
                    "_source_dong": name,
                    "articleNo": ano,
                    "complexNo": art.get("complexNo", art.get("complex_no", "")),
                    "complexName": art.get("complexName", art.get("complex_name", art.get("buildingName", ""))),
                    "address": art.get("address", art.get("roadAddress", art.get("detailAddress", ""))),
                    "deposit": deposit,
                    "supplyArea": art.get("supplyArea", art.get("supply_area", art.get("area1", ""))),
                    "exclusiveArea": art.get("exclusiveArea", art.get("exclusive_area", art.get("area2", ""))),
                    "floor": art.get("floor", art.get("floorInfo", "")),
                    "totalFloor": art.get("totalFloor", art.get("total_floor", "")),
                    "direction": art.get("direction", art.get("directionName", "")),
                    "roomCount": art.get("roomCount", art.get("room_count", "")),
                    "bathroomCount": art.get("bathroomCount", art.get("bathroom_count", "")),
                    "agentName": art.get("agentName", art.get("agent_name", "")),
                    "agentPhone": art.get("agentPhone", art.get("agent_phone", "")),
                    "registrationDate": art.get("registrationDate", art.get("registration_date", art.get("regDate", ""))),
                    "description": art.get("description", ""),
                    "articleFeatureDesc": art.get("articleFeatureDesc", ""),
                    "buildingType": art.get("buildingType", ""),
                    "_api_url": cap["url"],
                })

        # Save session for next run
        try:
            await context.storage_state(path=str(session_file))
            print(f"  Session saved: {session_file}")
        except Exception:
            pass

        await browser.close()

    print(f"  Total unique jeonse listings: {len(listings)}")
    return listings


async def main():
    all_listings = []

    for name, lat, lon in TARGET_DONGS:
        if name in COMPLETED_DONGS:
            print(f"\n  {name} — already completed, skipping")
            continue
        print(f"\n{'='*50}")
        print(f"  {name} ({lat}, {lon})")
        print(f"{'='*50}")
        try:
            listings = await crawl_dong(name, lat, lon)
            all_listings.extend(listings)
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            # Save partial results
            COMPLETED_DONGS.add(name)

    if not all_listings:
        print("\nNo listings collected from any dong.")
        return

    timestamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"direct_crawl_{timestamp}.csv"

    all_keys = set()
    for item in all_listings:
        all_keys.update(item.keys())
    fieldnames = sorted(all_keys)

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_listings)

    print(f"\n{'='*50}")
    print(f"Exported {len(all_listings)} listings to {csv_path}")
    print(f"Next: python scripts/convert_naverland.py {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
