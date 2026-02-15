#!/usr/bin/env python3
"""
E2E Test: All Entity Types - Verify No Fragmented URLs
Tests that clicking ANY entity type uses ContextPanel, not navigation
"""

import sys
from playwright.sync_api import sync_playwright

BASE_URL = "https://app.celeste7.ai"

# Test various search terms likely to return different entity types
ENTITY_SEARCHES = {
    'parts': ['oil filter', 'engine part', 'pump', 'spare'],
    'work_orders': ['maintenance', 'repair', 'work order', 'task'],
    'equipment': ['engine', 'generator', 'pump', 'motor'],
    'faults': ['fault', 'error', 'issue', 'problem'],
    'documents': ['manual', 'procedure', 'document', 'guide'],
}

def test_all_entity_types():
    print("\n" + "="*80)
    print("E2E TEST: All Entity Types - No Fragmented URLs")
    print("="*80)

    results_summary = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Capture console
        console_messages = []
        page_errors = []

        def handle_console(msg):
            text = f"[{msg.type}] {msg.text}"
            console_messages.append(text)

        def handle_error(error):
            page_errors.append(str(error))
            print(f"  ❌ ERROR: {error}")

        page.on("console", handle_console)
        page.on("pageerror", handle_error)

        try:
            # Login
            print("\n[SETUP] Logging in...")
            page.goto(f"{BASE_URL}/login")
            page.wait_for_selector('input[type="email"]', timeout=10000)
            page.fill('input[type="email"]', "x@alex-short.com")
            page.fill('input[type="password"]', "Password2!")
            page.click('button[type="submit"]')
            page.wait_for_timeout(5000)
            print(f"  ✓ Logged in")

            # Test each entity category
            for category, search_terms in ENTITY_SEARCHES.items():
                print(f"\n{'='*80}")
                print(f"TESTING: {category.upper()}")
                print(f"{'='*80}")

                found_result = False

                for term in search_terms:
                    if found_result:
                        break

                    print(f"\n  Searching: '{term}'")
                    search_input = page.locator('[data-testid="search-input"]')
                    search_input.fill(term)
                    page.wait_for_timeout(3000)

                    results = page.locator('[data-testid="search-result-item"]')
                    count = results.count()

                    if count > 0:
                        print(f"  ✓ Found {count} results")
                        found_result = True

                        # Test click behavior
                        url_before = page.url
                        first_result = results.first
                        first_result.click()
                        page.wait_for_timeout(2000)

                        url_after = page.url

                        # Check results
                        test_result = {
                            'search_term': term,
                            'results_count': count,
                            'url_before': url_before,
                            'url_after': url_after,
                            'navigation_occurred': url_before != url_after,
                            'panel_opened': False,
                            'errors': len(page_errors),
                        }

                        # Check for fragmented URLs
                        if url_before != url_after:
                            print(f"  ❌ FAILED: URL changed")
                            print(f"     From: {url_before}")
                            print(f"     To:   {url_after}")
                            test_result['status'] = 'FAILED'
                        else:
                            print(f"  ✅ PASSED: URL stayed at /app")
                            test_result['status'] = 'PASSED'

                        # Check ContextPanel
                        context_panel = page.locator('[data-testid="context-panel"]')
                        try:
                            is_visible = context_panel.is_visible(timeout=2000)
                            if is_visible:
                                entity_type = context_panel.get_attribute("data-entity-type")
                                print(f"  ✅ ContextPanel opened: {entity_type}")
                                test_result['panel_opened'] = True
                                test_result['entity_type'] = entity_type
                            else:
                                print(f"  ⚠️  ContextPanel not visible")
                        except:
                            print(f"  ⚠️  ContextPanel not found")

                        # Check for errors
                        if page_errors:
                            print(f"  ❌ JavaScript errors: {len(page_errors)}")
                            test_result['status'] = 'FAILED'
                        else:
                            print(f"  ✅ No JavaScript errors")

                        results_summary[category] = test_result

                        # Close panel for next test
                        page.keyboard.press('Escape')
                        page.wait_for_timeout(500)

                        # Screenshot
                        page.screenshot(path=f"/tmp/E2E_{category}_{term.replace(' ', '_')}.png")

                    else:
                        print(f"  ⚠️  No results")

                    # Clear search
                    search_input.fill("")
                    page.wait_for_timeout(500)

                if not found_result:
                    print(f"\n  ❌ No data found for {category}")
                    results_summary[category] = {'status': 'SKIPPED', 'reason': 'No data'}

        except Exception as e:
            print(f"\n❌ TEST EXCEPTION: {e}")

        finally:
            # SUMMARY REPORT
            print("\n" + "="*80)
            print("TEST SUMMARY")
            print("="*80)

            passed = 0
            failed = 0
            skipped = 0

            for category, result in results_summary.items():
                status = result.get('status', 'UNKNOWN')
                if status == 'PASSED':
                    passed += 1
                    icon = "✅"
                elif status == 'FAILED':
                    failed += 1
                    icon = "❌"
                elif status == 'SKIPPED':
                    skipped += 1
                    icon = "⏭️ "
                else:
                    icon = "❓"

                print(f"\n{icon} {category.upper()}: {status}")
                if status in ['PASSED', 'FAILED']:
                    print(f"   Search: '{result['search_term']}'")
                    print(f"   Results: {result['results_count']}")
                    print(f"   Navigation: {'YES ❌' if result['navigation_occurred'] else 'NO ✅'}")
                    print(f"   Panel opened: {'YES ✅' if result['panel_opened'] else 'NO ⚠️'}")
                    print(f"   Errors: {result['errors']}")
                elif status == 'SKIPPED':
                    print(f"   Reason: {result.get('reason', 'Unknown')}")

            print(f"\n" + "="*80)
            print(f"FINAL RESULTS")
            print(f"="*80)
            print(f"  ✅ Passed: {passed}")
            print(f"  ❌ Failed: {failed}")
            print(f"  ⏭️  Skipped: {skipped}")

            # Check for fragmented URLs
            has_fragmented_urls = any(
                r.get('navigation_occurred', False)
                for r in results_summary.values()
                if r.get('status') in ['PASSED', 'FAILED']
            )

            # Check for showContext usage
            has_showcontext = any('showContext' in msg or 'Opening in ContextPanel' in msg for msg in console_messages)
            has_router_push = any('Navigating to' in msg or 'router.push' in msg for msg in console_messages)

            print(f"\n📊 ARCHITECTURE VERIFICATION:")
            print(f"  Fragmented URLs detected: {'❌ YES (BAD!)' if has_fragmented_urls else '✅ NO (GOOD!)'}")
            print(f"  showContext() calls: {'✅ YES' if has_showcontext else '❌ NO'}")
            print(f"  router.push() calls: {'❌ YES (BAD!)' if has_router_push else '✅ NO (GOOD!)'}")

            if failed == 0 and not has_fragmented_urls and has_showcontext and not has_router_push:
                print(f"\n✅ ✅ ✅ ALL TESTS PASSED ✅ ✅ ✅")
                print(f"  Single-surface architecture verified across all entity types!")
            elif skipped > 0 and failed == 0:
                print(f"\n⚠️  TESTS INCOMPLETE - Some entity types have no data")
            else:
                print(f"\n❌ TESTS FAILED - Review errors above")

            print("="*80)
            browser.close()

if __name__ == "__main__":
    test_all_entity_types()
