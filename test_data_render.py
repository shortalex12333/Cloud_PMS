#!/usr/bin/env python3
"""
TRUTH TEST: Does ContextPanel Actually Show Data?
Verify that clicking shows REAL data from backend, not just empty panel
"""

import sys
from playwright.sync_api import sync_playwright

BASE_URL = "https://app.celeste7.ai"

def test_data_rendering():
    print("\n" + "="*80)
    print("DATA RENDER TEST: Does ContextPanel Show Real Data?")
    print("="*80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Login
            print("\n[1] Logging in...")
            page.goto(f"{BASE_URL}/login")
            page.wait_for_selector('input[type="email"]', timeout=10000)
            page.fill('input[type="email"]', "x@alex-short.com")
            page.fill('input[type="password"]', "Password2!")
            page.click('button[type="submit"]')
            page.wait_for_timeout(5000)
            print(f"  ✓ Logged in")

            # Search
            print("\n[2] Searching for 'maintenance'...")
            search_input = page.locator('[data-testid="search-input"]')
            search_input.fill("maintenance")
            page.wait_for_timeout(3000)

            results = page.locator('[data-testid="search-result-item"]')
            count = results.count()
            print(f"  ✓ Found {count} results")

            if count == 0:
                print("  ❌ No results to test")
                browser.close()
                return

            # Get result metadata
            first_result = results.first
            result_text = first_result.text_content()
            print(f"\n[3] First result preview:")
            print(f"  {result_text[:200]}...")

            # Click
            print(f"\n[4] Clicking first result...")
            first_result.click()
            page.wait_for_timeout(3000)

            # Check ContextPanel
            print(f"\n[5] Checking ContextPanel content...")
            context_panel = page.locator('[data-testid="context-panel"]')

            if not context_panel.is_visible():
                print("  ❌ FAILED: ContextPanel not visible")
                browser.close()
                return

            print(f"  ✓ ContextPanel is visible")

            # Take screenshot BEFORE checking
            page.screenshot(path="/tmp/DATA_RENDER_contextpanel.png", full_page=True)
            print(f"  📸 Screenshot: /tmp/DATA_RENDER_contextpanel.png")

            # Check for actual content
            panel_content = page.locator('[data-testid="context-panel-content"]')

            # Check for various data indicators
            checks = {
                'Empty state': page.locator('[data-testid="context-panel-empty"]').is_visible(),
                'Card component': page.locator('[data-testid*="-card"]').count() > 0,
                'Text content': len(panel_content.text_content().strip()) > 50,
                'Headings (h1-h3)': page.locator('[data-testid="context-panel"] h1, [data-testid="context-panel"] h2, [data-testid="context-panel"] h3').count() > 0,
                'Paragraphs': page.locator('[data-testid="context-panel"] p').count() > 0,
                'Action buttons': page.locator('[data-testid="context-panel"] button').count() > 0,
            }

            print(f"\n[6] Content Analysis:")
            has_content = False
            for check_name, result in checks.items():
                status = "✅ YES" if result else "❌ NO"
                print(f"  {check_name}: {status}")
                if check_name != 'Empty state' and result:
                    has_content = True

            # Get actual text content
            panel_text = panel_content.text_content()
            print(f"\n[7] Panel Text Content ({len(panel_text)} chars):")
            if len(panel_text) > 0:
                print(f"  First 300 chars:")
                print(f"  ---")
                print(f"  {panel_text[:300]}")
                print(f"  ---")
            else:
                print(f"  ❌ EMPTY - No text content!")

            # Check for entity-specific data
            print(f"\n[8] Entity Data Check:")

            # Work order fields
            wo_fields = {
                'Title/ID': page.locator('text=/WO-|work order|title/i').count() > 0,
                'Status': page.locator('text=/pending|in_progress|completed/i').count() > 0,
                'Priority': page.locator('text=/low|medium|high|urgent/i').count() > 0,
                'Description': page.locator('text=/description|details/i').count() > 0,
                'Equipment': page.locator('text=/equipment|assigned/i').count() > 0,
            }

            for field, found in wo_fields.items():
                status = "✅ FOUND" if found else "⚠️  NOT FOUND"
                print(f"  {field}: {status}")

            # Network check - did it fetch data?
            print(f"\n[9] Backend Data Fetch Check:")
            print(f"  (Checking for API calls...)")
            # Note: This would require network interception setup
            print(f"  ⚠️  Network monitoring not set up in this test")

            # VERDICT
            print(f"\n" + "="*80)
            print(f"VERDICT")
            print(f"="*80)

            if checks['Empty state']:
                print(f"❌ FAILED: Panel shows 'Select an item to view details'")
                print(f"   Panel opened but NO DATA rendered")
                print(f"   Possible issues:")
                print(f"   - Backend not returning data")
                print(f"   - Frontend not fetching data")
                print(f"   - showContext() not passing metadata correctly")
            elif has_content and len(panel_text) > 100:
                print(f"✅ PASSED: Panel shows REAL DATA")
                print(f"   Content length: {len(panel_text)} chars")
                print(f"   Components rendered: {checks['Card component']}")
                print(f"   Action buttons: {checks['Action buttons']}")
            elif len(panel_text) > 0:
                print(f"⚠️  PARTIAL: Panel has some content but seems incomplete")
                print(f"   Content length: {len(panel_text)} chars (expected >100)")
            else:
                print(f"❌ FAILED: Panel is EMPTY")
                print(f"   No text content found")

            print(f"="*80)

        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()

        finally:
            input("\nPress Enter to close browser...")
            browser.close()

if __name__ == "__main__":
    test_data_rendering()
