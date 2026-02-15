#!/usr/bin/env python3
"""
Day 7: Test What ACTUALLY Happens When Clicking Part
Simple focused test - see the real behavior
"""

import os
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://app.celeste7.ai"
SCREENSHOT_DIR = "test-automation/screenshots/day7_actual_behavior"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def capture(page, name):
    """Capture screenshot."""
    filepath = f"{SCREENSHOT_DIR}/{name}_{int(time.time())}.png"
    page.screenshot(path=filepath, full_page=True)
    print(f"📸 {name}")

def test_what_happens():
    """Test what actually happens when clicking a part."""
    print("\n" + "="*80)
    print("TESTING: What happens when user clicks a part result?")
    print("="*80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Enable console logging
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))

        # Login
        print("\n1. Logging in...")
        page.goto(f"{BASE_URL}/login")
        page.wait_for_selector('input[type="email"]', timeout=10000)
        page.fill('input[type="email"]', "hod.test@alex-short.com")
        page.fill('input[type="password"]', "Password2!")
        page.click('button[type="submit"]')

        # Wait for login to complete
        page.wait_for_timeout(3000)
        current_url = page.url
        print(f"   After login, URL: {current_url}")
        capture(page, "01_after_login")

        # Search for part
        print("\n2. Searching for 'oil filter'...")
        search_input = page.locator('input[placeholder*="Search"], input[type="text"]').first
        search_input.fill("oil filter")
        page.wait_for_timeout(3000)
        capture(page, "02_search_results")

        # Check what results we got
        results = page.locator('[data-testid="search-result-item"]')
        result_count = results.count()
        print(f"   Found {result_count} results")

        if result_count == 0:
            print("\n❌ NO RESULTS FOUND - Cannot test click behavior")
            browser.close()
            return

        # Get info about first result
        first_result = results.first
        result_text = first_result.text_content()
        print(f"   First result: {result_text[:100]}")

        # Note current URL before click
        url_before = page.url
        print(f"\n3. Before click - URL: {url_before}")

        # Click the first result
        print("\n4. Clicking first result...")
        first_result.click()

        # Wait a moment
        page.wait_for_timeout(2000)

        # Check what happened
        url_after = page.url
        print(f"   After click - URL: {url_after}")
        capture(page, "03_after_click")

        # Did URL change?
        if url_after != url_before:
            print(f"\n📍 URL CHANGED!")
            print(f"   From: {url_before}")
            print(f"   To:   {url_after}")
            print("\n   ❌ BREAKS SINGLE SURFACE VISION (navigated away from /)")
        else:
            print(f"\n✅ URL STAYED THE SAME: {url_after}")
            print("   Single surface maintained")

        # Check for context panel
        print("\n5. Checking for ContextPanel...")
        context_panel_selectors = [
            '[data-testid="context-panel"]',
            '.context-panel',
            'aside',
            '[role="complementary"]',
            '[class*="slide"]',
            '[class*="panel"]'
        ]

        panel_found = False
        for selector in context_panel_selectors:
            panels = page.locator(selector)
            if panels.count() > 0:
                print(f"   Found element matching: {selector}")
                panel_found = True

        if not panel_found:
            print("   ❌ No context panel found")

        # Check page content - what's visible?
        print("\n6. Checking page content...")

        # Is search bar still visible?
        search_still_visible = page.locator('input[placeholder*="Search"]').is_visible()
        print(f"   Search bar visible: {search_still_visible}")

        # Is there a back button?
        back_button = page.locator('button:has-text("Back"), [aria-label*="back" i]')
        has_back_button = back_button.count() > 0
        print(f"   Back button present: {has_back_button}")

        # What headings are visible?
        headings = page.locator('h1, h2').all_text_content()
        if headings:
            print(f"   Headings on page: {headings[:3]}")

        # Final screenshot
        capture(page, "04_final_state")

        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        if url_after != url_before:
            print("❌ NAVIGATION OCCURRED - Single surface broken")
            print(f"   Navigated to: {url_after}")
        else:
            print("✅ Stayed on same URL")

        if panel_found:
            print("✅ Some panel/sidebar element found")
        else:
            print("❌ No context panel detected")

        if search_still_visible:
            print("✅ Search bar still visible")
        else:
            print("⚠️  Search bar hidden/not visible")

        browser.close()

if __name__ == "__main__":
    test_what_happens()
