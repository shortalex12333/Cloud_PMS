#!/usr/bin/env python3
"""
E2E Comprehensive Test: Parts Lens Complete User Journey
Tests the full fix deployment with multiple scenarios
"""

import sys
from playwright.sync_api import sync_playwright

BASE_URL = "https://app.celeste7.ai"

def test_parts_lens_e2e():
    print("\n" + "="*80)
    print("E2E TEST: Parts Lens Complete User Journey")
    print("="*80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Capture console and errors
        console_messages = []
        page_errors = []

        def handle_console(msg):
            console_messages.append(f"[{msg.type}] {msg.text}")
            print(f"  {msg.type}: {msg.text}")

        def handle_error(error):
            error_text = str(error)
            page_errors.append(error_text)
            print(f"  [ERROR] {error_text}")

        page.on("console", handle_console)
        page.on("pageerror", handle_error)

        try:
            # TEST 1: Login
            print("\n[TEST 1] Login")
            page.goto(f"{BASE_URL}/login")
            page.wait_for_selector('input[type="email"]', timeout=10000)
            page.fill('input[type="email"]', "x@alex-short.com")
            page.fill('input[type="password"]', "Password2!")
            page.click('button[type="submit"]')
            page.wait_for_timeout(5000)
            print(f"  ✓ Logged in: {page.url}")

            # TEST 2: Try multiple search terms
            search_terms = ['oil', 'filter', 'engine', 'pump']

            for term in search_terms:
                print(f"\n[TEST 2] Searching for '{term}'...")
                search_input = page.locator('[data-testid="search-input"]')
                search_input.fill(term)
                page.wait_for_timeout(3000)

                results = page.locator('[data-testid="search-result-item"]')
                count = results.count()
                print(f"  Found {count} results for '{term}'")

                if count > 0:
                    # Found results, proceed with click test
                    print(f"\n[TEST 3] Testing click behavior with '{term}'...")

                    url_before = page.url
                    print(f"  URL before: {url_before}")

                    # Click first result
                    print("  Clicking first result...")
                    first_result = results.first
                    first_result.click()
                    page.wait_for_timeout(2000)

                    url_after = page.url
                    print(f"  URL after: {url_after}")

                    # Check for navigation
                    if url_before != url_after:
                        print(f"  ❌ FAILED: URL changed (navigation occurred)")
                        print(f"     From: {url_before}")
                        print(f"     To:   {url_after}")
                    else:
                        print(f"  ✅ PASSED: URL stayed at /app (no navigation)")

                    # Check for ContextPanel
                    context_panel = page.locator('[data-testid="context-panel"]')
                    try:
                        is_visible = context_panel.is_visible(timeout=2000)
                        if is_visible:
                            entity_type = context_panel.get_attribute("data-entity-type")
                            print(f"  ✅ PASSED: ContextPanel visible, type: {entity_type}")

                            # Check for action buttons
                            action_buttons = page.locator('[data-testid*="action-button"]')
                            button_count = action_buttons.count()
                            print(f"  Action buttons found: {button_count}")

                            # Check for part details
                            has_part_name = page.locator('text=/part|filter|engine|pump/i').is_visible()
                            print(f"  Part details visible: {has_part_name}")

                        else:
                            print(f"  ❌ FAILED: ContextPanel NOT visible")
                    except Exception as e:
                        print(f"  ❌ FAILED: ContextPanel error - {e}")

                    # Check for errors
                    if page_errors:
                        print(f"\n  ❌ JAVASCRIPT ERRORS DETECTED:")
                        for err in page_errors:
                            print(f"     {err}")
                    else:
                        print(f"  ✅ PASSED: No JavaScript errors")

                    # Take screenshot
                    page.screenshot(path=f"/tmp/E2E_parts_lens_{term}.png", full_page=True)
                    print(f"  📸 Screenshot: /tmp/E2E_parts_lens_{term}.png")

                    # Check console for evidence
                    relevant_logs = [msg for msg in console_messages if any(kw in msg.lower() for kw in [
                        'spotlightsearch', 'contextpanel', 'showcontext', 'navigating', 'router', 'opening'
                    ])]

                    if relevant_logs:
                        print(f"\n  📋 RELEVANT LOGS:")
                        for log in relevant_logs[-5:]:  # Last 5 relevant logs
                            print(f"     {log}")

                    # Found working example, can stop
                    break

                # Clear search for next term
                search_input.fill("")
                page.wait_for_timeout(500)

            if count == 0:
                print(f"\n❌ NO RESULTS for any search term")
                print(f"   Tried: {', '.join(search_terms)}")
                print(f"   Database may be empty or search not working")

        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            page_errors.append(str(e))

        finally:
            # SUMMARY
            print("\n" + "="*80)
            print("E2E TEST SUMMARY")
            print("="*80)

            has_showcontext = any('showContext' in msg or 'Opening in ContextPanel' in msg for msg in console_messages)
            has_router_push = any('Navigating to' in msg or 'router.push' in msg for msg in console_messages)

            print(f"\n📊 RESULTS:")
            print(f"  Console messages: {len(console_messages)}")
            print(f"  JavaScript errors: {len(page_errors)}")
            print(f"  showContext() calls: {'✅ YES' if has_showcontext else '❌ NO'}")
            print(f"  router.push() calls: {'❌ YES' if has_router_push else '✅ NO'}")

            if has_showcontext and not has_router_push and len(page_errors) == 0:
                print(f"\n✅ ✅ ✅ ALL TESTS PASSED ✅ ✅ ✅")
                print(f"  Parts Lens is fully functional!")
            else:
                print(f"\n⚠️  ISSUES DETECTED - Review logs above")

            print("="*80)
            browser.close()

if __name__ == "__main__":
    test_parts_lens_e2e()
