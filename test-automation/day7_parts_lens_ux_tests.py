#!/usr/bin/env python3
"""
Day 7: Parts Lens UX Testing - CRITICAL FIXES
Tests the actual user journey for Parts Lens that is currently BROKEN

PRIORITY FIXES:
1. User clicks part → Detail view MUST open (currently nothing happens)
2. Detail view shows correct data (name, description, stock, location)
3. Action buttons work (Adjust Inventory, Order Part, etc.)
4. RBAC enforcement (different roles see different actions)
5. Image upload/change works

This tests WHAT USERS ACTUALLY EXPERIENCE, not isolated backend APIs.
"""

import os
import sys
from playwright.sync_api import sync_playwright, expect
import time

# Test users
TEST_USERS = {
    "captain": {
        "email": "x@alex-short.com",
        "password": "Password2!",
        "role": "captain",
    },
    "hod": {
        "email": "hod.test@alex-short.com",
        "password": "Password2!",
        "role": "chief_engineer",
    },
    "crew": {
        "email": "crew.test@alex-short.com",
        "password": "Password2!",
        "role": "crew",
    },
}

BASE_URL = "https://app.celeste7.ai"
SCREENSHOT_DIR = "test-automation/screenshots/day7_parts_lens"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def capture_screenshot(page, name: str):
    """Capture screenshot with timestamp."""
    filename = f"{name}_{int(time.time() * 1000)}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    page.screenshot(path=filepath, full_page=True)
    print(f"📸 Screenshot: {filename}")


def login(page, role: str):
    """Login as specified role."""
    user = TEST_USERS[role]
    print(f"\n🔐 Logging in as {role}: {user['email']}")

    page.goto(f"{BASE_URL}/login")
    page.wait_for_selector('input[type="email"]', timeout=10000)

    page.fill('input[type="email"]', user["email"])
    page.fill('input[type="password"]', user["password"])
    page.click('button[type="submit"]')

    # Wait for redirect away from login
    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
    print(f"✅ Logged in as {role}")


def test_part_click_opens_detail(page):
    """
    CRITICAL TEST: User clicks part → Detail view opens
    Currently BROKEN: Nothing happens when clicking part
    """
    print("\n" + "="*80)
    print("TEST 1: Click Part → Detail View Opens (CURRENTLY BROKEN)")
    print("="*80)

    login(page, "hod")

    # Search for a part
    print("\n1. Searching for 'oil filter'...")
    search_input = page.locator('input[placeholder*="Search"], [data-testid="search-input"]')
    search_input.fill("oil filter")

    # Wait for results
    page.wait_for_timeout(2000)
    capture_screenshot(page, "01_search_results")

    # Find part cards
    print("2. Looking for part cards in results...")
    part_cards = page.locator('[data-testid="part-card"], [data-entity-type="part"]')

    if part_cards.count() == 0:
        print("❌ FAIL: No part cards found in search results")
        return False

    print(f"   Found {part_cards.count()} part cards")

    # Click first part card
    print("3. Clicking first part card...")
    first_part = part_cards.first()

    # Get part name before clicking
    part_name = first_part.locator("h3").text_content()
    print(f"   Clicking part: {part_name}")

    first_part.click()
    page.wait_for_timeout(1000)

    capture_screenshot(page, "02_after_click")

    # Check if detail view opened
    print("4. Checking if detail view/context panel opened...")

    # Look for context panel (slides from right)
    context_panel = page.locator('[data-testid="context-panel"], .context-panel, aside')

    if context_panel.count() == 0:
        print("❌ FAIL: No context panel found after clicking part")
        print("   This is BROKEN - clicking part does nothing!")
        return False

    # Check if panel is visible
    if not context_panel.is_visible():
        print("❌ FAIL: Context panel exists but is not visible")
        print("   Panel might be hidden or not sliding open")
        return False

    print("✅ PASS: Context panel opened after clicking part")

    # Verify detail view shows correct part
    print("5. Verifying detail view shows clicked part...")

    detail_title = page.locator('h1, h2, h3').filter(has_text=part_name)

    if detail_title.count() == 0:
        print(f"⚠️  WARNING: Could not verify part name '{part_name}' in detail view")
    else:
        print(f"✅ Detail view shows: {part_name}")

    capture_screenshot(page, "03_detail_view_open")
    return True


def test_detail_view_shows_correct_data(page):
    """
    TEST: Detail view displays all part data correctly
    Should show: name, part number, stock quantity, location, supplier, etc.
    """
    print("\n" + "="*80)
    print("TEST 2: Detail View Shows Correct Data")
    print("="*80)

    login(page, "hod")

    # Search and click part
    print("\n1. Searching for 'oil filter' and clicking result...")
    search_input = page.locator('input[placeholder*="Search"], [data-testid="search-input"]')
    search_input.fill("oil filter")
    page.wait_for_timeout(2000)

    part_cards = page.locator('[data-testid="part-card"], [data-entity-type="part"]')
    if part_cards.count() > 0:
        part_cards.first().click()
        page.wait_for_timeout(1000)
        capture_screenshot(page, "04_detail_data_view")
    else:
        print("❌ No parts found to test")
        return False

    # Check for expected data fields
    print("2. Checking for data fields in detail view...")

    expected_fields = [
        ("Part Number", "P/N:"),
        ("Stock Quantity", "Stock:"),
        ("Location", "Location:"),
    ]

    found_fields = 0
    for field_name, field_text in expected_fields:
        if page.locator(f'text=/{field_text}/i').count() > 0:
            print(f"   ✅ {field_name} displayed")
            found_fields += 1
        else:
            print(f"   ❌ {field_name} NOT displayed")

    if found_fields == len(expected_fields):
        print(f"✅ PASS: All {found_fields} data fields displayed correctly")
        return True
    else:
        print(f"⚠️  PARTIAL: {found_fields}/{len(expected_fields)} fields displayed")
        return False


def test_action_buttons_work(page):
    """
    TEST: Action buttons in detail view are clickable and work
    Should show: Adjust Inventory, Order Part, etc.
    """
    print("\n" + "="*80)
    print("TEST 3: Action Buttons Work")
    print("="*80)

    login(page, "hod")

    # Search and open part detail
    print("\n1. Opening part detail view...")
    search_input = page.locator('input[placeholder*="Search"], [data-testid="search-input"]')
    search_input.fill("oil filter")
    page.wait_for_timeout(2000)

    part_cards = page.locator('[data-testid="part-card"], [data-entity-type="part"]')
    if part_cards.count() > 0:
        part_cards.first().click()
        page.wait_for_timeout(1000)
    else:
        print("❌ No parts found")
        return False

    # Look for action buttons
    print("2. Looking for action buttons...")

    # Common action button selectors
    action_buttons = page.locator('button:has-text("Adjust"), button:has-text("Order"), button:has-text("Log"), [data-testid*="action"], .action-button')

    button_count = action_buttons.count()
    print(f"   Found {button_count} action buttons")

    if button_count == 0:
        print("❌ FAIL: No action buttons found in detail view")
        return False

    # Try clicking first action button
    print("3. Testing first action button...")
    first_button = action_buttons.first()
    button_text = first_button.text_content()
    print(f"   Clicking button: {button_text}")

    first_button.click()
    page.wait_for_timeout(1000)

    capture_screenshot(page, "05_action_button_clicked")

    # Check if modal/form opened
    modal = page.locator('[role="dialog"], .modal, [data-testid*="modal"]')

    if modal.count() > 0 and modal.is_visible():
        print(f"✅ PASS: Action button '{button_text}' opened modal/form")
        return True
    else:
        print(f"⚠️  WARNING: Button clicked but no modal appeared")
        print("   Action might execute directly or UI response is missing")
        return False


def test_rbac_different_roles(page):
    """
    TEST: Different roles see different actions (RBAC enforcement)
    Captain should see more actions than Crew
    """
    print("\n" + "="*80)
    print("TEST 4: RBAC - Different Roles See Different Actions")
    print("="*80)

    results = {}

    for role in ["captain", "crew"]:
        print(f"\n--- Testing as {role.upper()} ---")
        login(page, role)

        # Search and open part
        search_input = page.locator('input[placeholder*="Search"], [data-testid="search-input"]')
        search_input.fill("oil filter")
        page.wait_for_timeout(2000)

        part_cards = page.locator('[data-testid="part-card"], [data-entity-type="part"]')
        if part_cards.count() > 0:
            part_cards.first().click()
            page.wait_for_timeout(1000)
        else:
            print(f"❌ No parts found for {role}")
            continue

        # Count action buttons
        action_buttons = page.locator('button:has-text("Adjust"), button:has-text("Order"), button:has-text("Log"), [data-testid*="action"]')
        button_count = action_buttons.count()

        print(f"   {role} sees {button_count} action buttons")
        results[role] = button_count

        capture_screenshot(page, f"06_rbac_{role}_actions")

        # Logout for next role
        page.goto(f"{BASE_URL}/logout")
        page.wait_for_timeout(1000)

    # Verify captain sees more actions than crew
    if "captain" in results and "crew" in results:
        if results["captain"] > results["crew"]:
            print(f"\n✅ PASS: RBAC working - Captain sees {results['captain']} actions, Crew sees {results['crew']}")
            return True
        elif results["captain"] == results["crew"]:
            print(f"\n⚠️  WARNING: Captain and Crew see same number of actions ({results['captain']})")
            print("   RBAC might not be filtering actions correctly")
            return False
        else:
            print(f"\n❌ FAIL: Crew sees MORE actions than Captain - RBAC is broken!")
            return False
    else:
        print("\n❌ Could not test RBAC - missing role data")
        return False


def test_image_upload_flow(page):
    """
    TEST: Image upload to part works
    Flow: Search part → Click → Click image placeholder → Upload new image
    Currently: Flow is MISSING/BROKEN
    """
    print("\n" + "="*80)
    print("TEST 5: Image Upload Flow (EXPECTED TO FAIL - NOT IMPLEMENTED)")
    print("="*80)

    login(page, "hod")

    # Search and open part
    print("\n1. Opening part detail view...")
    search_input = page.locator('input[placeholder*="Search"], [data-testid="search-input"]')
    search_input.fill("oil filter")
    page.wait_for_timeout(2000)

    part_cards = page.locator('[data-testid="part-card"], [data-entity-type="part"]')
    if part_cards.count() > 0:
        part_cards.first().click()
        page.wait_for_timeout(1000)
    else:
        print("❌ No parts found")
        return False

    # Look for image or image placeholder
    print("2. Looking for part image or placeholder...")

    # Possible selectors for image area
    image_elements = page.locator('img, [data-testid*="image"], .part-image, .image-placeholder, svg[class*="Package"]')

    if image_elements.count() == 0:
        print("❌ FAIL: No image or placeholder found")
        return False

    print(f"   Found {image_elements.count()} image-related elements")

    # Try clicking image
    print("3. Clicking image/placeholder...")
    image_elements.first().click()
    page.wait_for_timeout(1000)

    capture_screenshot(page, "07_image_clicked")

    # Look for upload button or file input
    upload_button = page.locator('button:has-text("Upload"), input[type="file"], [data-testid*="upload"]')

    if upload_button.count() > 0:
        print("✅ UNEXPECTED PASS: Upload UI exists!")
        return True
    else:
        print("❌ EXPECTED FAIL: No upload button/input found")
        print("   This flow needs to be implemented")
        return False


def run_all_tests():
    """Run all Parts Lens UX tests."""
    print("\n" + "="*80)
    print("DAY 7: PARTS LENS UX TESTING")
    print("Testing what users ACTUALLY experience, not backend APIs")
    print("="*80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible for debugging
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        results = {
            "Part click opens detail": test_part_click_opens_detail(page),
            "Detail view shows data": test_detail_view_shows_correct_data(page),
            "Action buttons work": test_action_buttons_work(page),
            "RBAC enforcement": test_rbac_different_roles(page),
            "Image upload flow": test_image_upload_flow(page),
        }

        browser.close()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nPass Rate: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
