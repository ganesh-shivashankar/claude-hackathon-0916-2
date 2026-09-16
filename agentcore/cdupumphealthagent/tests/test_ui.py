"""Playwright tests for the CDU Pump Health Monitor UI via CloudFront."""

import json
import re
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://d23qf2vysvhyvz.cloudfront.net/code/ports/3000/"


def test_page_loads():
    """Test that the page loads and shows all 4 panels."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

        assert page.locator("text=CDU Pump Health Monitor").first.is_visible(), "Title not visible"
        assert page.locator("text=FLEET HEALTH").first.is_visible(), "Fleet panel not visible"
        assert page.locator("text=REASONING TRACE").first.is_visible(), "Trace panel not visible"
        assert page.get_by_placeholder("Ask about pump").is_visible(), "Chat input not visible"

        print("PASS: All 4 panels visible")
        browser.close()


def test_fleet_panel():
    """Test that the fleet panel loads all 12 pumps."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("text=P-01", timeout=60000)

        content = page.content()
        pumps = set(re.findall(r'P-\d{2}', content))
        iso_count = len(page.locator("text=/ISO [A-D]/").all())

        assert len(pumps) >= 10, f"Expected >=10 pumps, got {len(pumps)}"
        assert iso_count >= 1, "No ISO zone badges"
        print(f"PASS: {len(pumps)} pumps loaded, {iso_count} ISO badges")
        browser.close()


def test_api_fleet():
    """Test fleet API from browser context."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

        result = page.evaluate('''async () => {
            const r = await fetch("/api/fleet");
            const d = await r.json();
            return {status: r.status, count: d.length, first: d[0]};
        }''')

        assert result["status"] == 200, f"Fleet API returned {result['status']}"
        assert result["count"] == 12, f"Expected 12 pumps, got {result['count']}"
        assert "pump_id" in result["first"], "Missing pump_id in fleet data"
        assert "vibration_zone" in result["first"], "Missing vibration_zone in fleet data"
        print(f"PASS: Fleet API returns {result['count']} pumps")
        browser.close()


def test_api_chat():
    """Test chat API from browser context — direct response."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

        result = page.evaluate('''async () => {
            const r = await fetch("/api/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({message: "What zone is P-06 in?"})
            });
            const d = await r.json();
            return {
                status: r.status,
                hasResponse: !!d.response,
                responseLen: (d.response || "").length,
                toolCalls: d.tool_calls || 0,
                citationCount: (d.citations || []).length,
                hasTrace: !!d.trace,
                preview: (d.response || "").substring(0, 200)
            };
        }''')

        assert result["status"] == 200, f"Chat returned {result['status']}"
        assert result["hasResponse"], "No response field in chat result"
        assert result["responseLen"] > 100, f"Response too short ({result['responseLen']} chars)"
        assert result["hasTrace"], "No trace in response"
        print(f"PASS: Chat API works — {result['responseLen']} chars, {result['toolCalls']} tools, {result['citationCount']} citations")
        print(f"  Preview: {result['preview']}...")
        browser.close()


def test_chat_ui_e2e():
    """End-to-end: click suggestion chip, wait for agent response in UI."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("text=P-01", timeout=60000)

        page.get_by_role("button", name="What's the health of P-07?").click()
        print("Clicked P-07 chip, waiting for response...")

        start = time.time()
        success = False
        for _ in range(24):  # 24 * 5s = 2 min
            page.wait_for_timeout(5000)
            elapsed = int(time.time() - start)
            msgs = page.locator("[class*='msg-']").all_text_contents()
            agent_msgs = [m for m in msgs if len(m) > 50 and "Error" not in m and "no response" not in m]

            if agent_msgs:
                print(f"PASS: Response in {elapsed}s — {len(agent_msgs[-1])} chars")
                print(f"  Preview: {agent_msgs[-1][:200]}...")
                success = True
                break
            print(f"  [{elapsed}s] waiting...")

        assert success, "No agent response within 2 minutes"
        browser.close()


if __name__ == "__main__":
    import sys
    tests = [
        ("page_loads", test_page_loads),
        ("fleet_panel", test_fleet_panel),
        ("api_fleet", test_api_fleet),
        ("api_chat", test_api_chat),
        ("chat_e2e", test_chat_ui_e2e),
    ]

    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    passed = 0
    failed = 0

    for name, fn in tests:
        if target != "all" and target != name:
            continue
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

    if target == "all":
        print(f"\n{'='*60}")
        print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed}")
        print(f"{'='*60}")
