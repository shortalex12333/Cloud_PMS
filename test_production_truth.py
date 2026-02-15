#!/usr/bin/env python3
"""
TRUTH FINDER: What Actually Happens on Production?

This script will:
1. Open production in browser
2. Login
3. Search for a part
4. Click it
5. Capture ALL console messages
6. Report FACTS, not guesses
"""

import sys
from playwright.sync_api import sync_playwright

BASE_URL = "https://app.celeste7.ai"

def test_production():
    print("\n" + "="*80)
    print("TRUTH FINDER: Testing Production Behavior")
    print("="*80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Capture ALL console messages
        console_messages = []
        page_errors = []

        def handle_console(msg):
            entry = f"[{msg.type}] {msg.text}"
            console_messages.append(entry)
            print(f"  {entry}")

        def handle_error(error):
            error_text = str(error)
            page_errors.append(error_text)
            print(f"  [ERROR] {error_text}")

        page.on("console", handle_console)
        page.on("pageerror", handle_error)

        try:
            # STEP 1: Login
            print("\n[STEP 1] Logging in...")
            page.goto(f"{BASE_URL}/login")
            page.wait_for_selector('input[type="email"]', timeout=10000)
            page.fill('input[type="email"]', "x@alex-short.com")
            page.fill('input[type="password"]', "Password2!")
            page.click('button[type="submit"]')
            page.wait_for_timeout(5000)

            url_after_login = page.url
            print(f"  ✓ Logged in, URL: {url_after_login}")

            # STEP 2: Search
            print("\n[STEP 2] Searching for 'filter'...")
            search_input = page.locator('[data-testid="search-input"]')
            search_input.fill("filter")
            page.wait_for_timeout(3000)

            results = page.locator('[data-testid="search-result-item"]')
            count = results.count()
            print(f"  ✓ Found {count} results")

            if count == 0:
                print("\n❌ NO RESULTS - Cannot test click behavior")
                browser.close()
                return

            # STEP 3: Check state before click
            print("\n[STEP 3] Pre-click state...")
            url_before = page.url
            print(f"  URL before: {url_before}")

            # STEP 4: Click first result
            print("\n[STEP 4] Clicking first result...")
            print("  (Watching for console messages...)")
            first_result = results.first
            first_result.click()
            page.wait_for_timeout(3000)

            # STEP 5: Check what happened
            print("\n[STEP 5] Post-click state...")
            url_after = page.url
            print(f"  URL after: {url_after}")

            if url_before != url_after:
                print(f"  ⚠️  URL CHANGED (navigation occurred)")
            else:
                print(f"  ✓ URL stayed the same (no navigation)")

            # Check for ContextPanel
            context_panel = page.locator('[data-testid="context-panel"]')
            try:
                is_visible = context_panel.is_visible(timeout=2000)
                if is_visible:
                    entity_type = context_panel.get_attribute("data-entity-type")
                    print(f"  ✓ ContextPanel visible, type: {entity_type}")
                else:
                    print(f"  ✗ ContextPanel NOT visible")
            except:
                print(f"  ✗ ContextPanel NOT found or not visible")

            # Check page content
            page_text = page.content()
            if "Application error" in page_text:
                print(f"  ⚠️  'Application error' found in page")

            # Take screenshot
            page.screenshot(path="/tmp/PRODUCTION_TRUTH_screenshot.png", full_page=True)
            print(f"\n  📸 Screenshot saved: /tmp/PRODUCTION_TRUTH_screenshot.png")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page_errors.append(str(e))

        finally:
            # SUMMARY
            print("\n" + "="*80)
            print("TRUTH SUMMARY")
            print("="*80)

            print(f"\n✓ Console messages captured: {len(console_messages)}")
            print(f"✓ Page errors captured: {len(page_errors)}")

            if page_errors:
                print("\n🔴 PAGE ERRORS DETECTED:")
                for i, error in enumerate(page_errors, 1):
                    print(f"  {i}. {error}")

            # Look for specific evidence
            relevant_logs = [msg for msg in console_messages if any(kw in msg.lower() for kw in [
                'spotlightsearch', 'contextpanel', 'showcontext', 'navigating', 'router', 'opening'
            ])]

            if relevant_logs:
                print("\n📋 RELEVANT CONSOLE LOGS:")
                for log in relevant_logs:
                    print(f"  {log}")

            # Check for evidence of fix
            has_showcontext = any('showContext' in msg or 'Opening in ContextPanel' in msg for msg in console_messages)
            has_router_push = any('Navigating to' in msg or 'router.push' in msg for msg in console_messages)

            print("\n🔍 EVIDENCE CHECK:")
            print(f"  showContext() calls: {'✓ YES' if has_showcontext else '✗ NO'}")
            print(f"  router.push() calls: {'✓ YES' if has_router_push else '✗ NO'}")

            if has_showcontext:
                print("\n✅ FIX IS DEPLOYED - Code uses showContext()")
            elif has_router_push:
                print("\n❌ OLD CODE STILL RUNNING - Uses router.push()")
            else:
                print("\n⚠️  UNCLEAR - No relevant logs found")

            print("\n" + "="*80)
            browser.close()

if __name__ == "__main__":
    test_production()
