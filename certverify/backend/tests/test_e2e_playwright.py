import pytest
from playwright.sync_api import sync_playwright


def test_playwright_e2e_login_and_navigation():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login Page
        page.goto("http://localhost:3000/login", wait_until="networkidle")
        assert "CertVerify AI" in page.title() or "Sign in" in page.content()

        # 2. Perform authentication
        page.locator('input[type="email"], input[name="email"]').first.fill("qa_tester@certverify.io")
        page.locator('input[type="password"]').first.fill("Password123!")
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_url("**/dashboard", timeout=10000)

        # 3. Verify Dashboard
        heading_dash = page.get_by_role("heading", name="Workspace Overview")
        heading_dash.wait_for(timeout=15000)
        assert heading_dash.is_visible()

        # 4. Verify History Navigation
        page.goto("http://localhost:3000/history", wait_until="networkidle")
        heading_hist = page.get_by_role("heading", name="Verification History")
        heading_hist.wait_for(timeout=15000)
        assert heading_hist.is_visible()

        # 5. Verify Admin Panel Navigation (Admin RBAC)
        page.goto("http://localhost:3000/admin", wait_until="networkidle")
        heading_admin = page.get_by_role("heading", name="Enterprise Administration Panel")
        heading_admin.wait_for(timeout=15000)
        assert heading_admin.is_visible()

        # 6. Verify Developer Page Navigation
        page.goto("http://localhost:3000/developer", wait_until="networkidle")
        heading_dev = page.get_by_role("heading", name="Developer & B2B Integration Suite")
        heading_dev.wait_for(timeout=15000)
        assert heading_dev.is_visible()

        browser.close()
