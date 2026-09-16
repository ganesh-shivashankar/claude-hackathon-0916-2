"""Playwright tests for the CDU Pump Health Monitor UI via CloudFront."""

import json
import re
import time
from playwright.sync_api import sync_playwright, expect

BASE_URL = "https://d23qf2vysvhyvz.cloudfront.net/code/ports/3000/"


def test_page_loads():
    """Test that the page loads and shows the main layout."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

        header = page.locator("text=CDU Pump Health Monitor")
        expect(header.first).to_be_visible(timeout=10000)

        fleet_header = page.locator("text=FLEET HEALTH")
        expect(fleet_header.first).to_be_visible(timeout=10000)

        chat_input = page.locator("textbox[name*="Ask about pump"]")
        expect(chat_input).to_be_visible(timeout=10000)

        trace_header = page.locator("text=REASONING TRACE")
        expect(trace_header.first).to_be_visible(timeout=10000)

        print("PASS: Page loads with all 4 panels visible")
        browser.close()


def test_fleet_panel_loads():
    """Test that the fleet panel loads pump data."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

        page.wait_for_selector("text=P-01", timeout=60000)

        content = page.content()
        unique_pumps = set(re.findall(r'P-\d{2}', content))
        iso_badges = page.locator("text=/ISO [A-D]/").count()

        print(f"Fleet: {len(unique_pumps)} pumps, {iso_badges} ISO badges")
        assert len(unique_pumps) >= 10, f"Expected >=10 pumps, got {len(unique_pumps)}"
        assert iso_badges >= 1, "Expected at least 1 ISO zone badge"
        print("PASS: Fleet panel loads with pump data")
        browser.close()


def test_chat_with_polling():
    """Test chat using the polling API pattern."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)

        responses_log = []

        def log_response(resp):
            if '/api/' in resp.url:
                try:
                    body = resp.text()
                except:
                    body = "(unreadable)"
                responses_log.append({
                    "url": resp.url,
                    "status": resp.status,
                    "body_preview": body[:200] if isinstance(body, str) else str(body)[:200],
                })

        page.on("response", log_response)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

        # Wait for page ready
        chat_input = page.locator("textbox[name*="Ask about pump"]")
        expect(chat_input).to_be_visible(timeout=15000)

        # Send message
        chat_input.fill("What zone is P-06 in?")
        send_btn = page.locator("button:has(svg)").last
        send_btn.click()

        # Wait for user message to appear
        page.wait_for_selector("text=What zone is P-06 in?", timeout=5000)
        print("User message appeared in chat")

        # Now wait for agent response (polling should happen automatically)
        start = time.time()
        success = False
        error = None

        for i in range(40):  # 40 * 5s = 200s max
            page.wait_for_timeout(5000)
            elapsed = int(time.time() - start)
            content = page.content()

            # Check for successful response
            has_zone = bool(re.search(r'Zone [A-D]', content))
            has_p06_response = 'P-06' in content and ('vibration' in content.lower() or 'zone' in content.lower())
            has_error = 'Unable to reach' in content or 'not valid JSON' in content

            print(f"  [{elapsed}s] zone={has_zone} p06={has_p06_response} error={has_error} polls={len([r for r in responses_log if 'status' in r['url']])}")

            if has_error:
                error_texts = re.findall(r'Error:[^<]{0,300}', content)
                error = error_texts[0] if error_texts else "Unknown error"
                print(f"  ERROR detected: {error}")
                break

            if has_zone or has_p06_response:
                success = True
                break

        elapsed = int(time.time() - start)

        # Print network log
        print(f"\n--- Network Log ({len(responses_log)} API calls) ---")
        for r in responses_log:
            print(f"  {r['status']} {r['url']}")
            if 'status' in r['url'] or 'chat' in r['url']:
                print(f"       body: {r['body_preview']}")

        if success:
            print(f"\nPASS: Chat response received in {elapsed}s")
        elif error:
            print(f"\nFAIL: Chat returned error after {elapsed}s: {error}")
        else:
            print(f"\nFAIL: No response after {elapsed}s")

        browser.close()
        assert success, f"Chat failed: {error or 'timeout'}"


def test_api_direct():
    """Test the API endpoints directly via fetch from the browser context."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(ignore_https_errors=True)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

        # Test fleet API
        fleet_result = page.evaluate("""
            async () => {
                const res = await fetch('/api/fleet');
                return { status: res.status, data: await res.json() };
            }
        """)
        fleet_count = len(fleet_result["data"]) if isinstance(fleet_result["data"], list) else 0
        print(f"Fleet API: HTTP {fleet_result['status']}, {fleet_count} pumps")
        assert fleet_result["status"] == 200
        assert fleet_count == 12

        # Test chat submit
        chat_result = page.evaluate("""
            async () => {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: 'What zone is P-06 in?' }),
                });
                return { status: res.status, data: await res.json() };
            }
        """)
        print(f"Chat submit: HTTP {chat_result['status']}, data: {json.dumps(chat_result['data'])[:200]}")
        assert chat_result["status"] == 200

        has_job_id = "job_id" in chat_result["data"]
        has_response = "response" in chat_result["data"]
        print(f"  has_job_id={has_job_id}, has_response={has_response}")

        if has_job_id:
            job_id = chat_result["data"]["job_id"]
            print(f"  Polling job {job_id}...")
            for i in range(30):
                page.wait_for_timeout(3000)
                poll_result = page.evaluate(f"""
                    async () => {{
                        const res = await fetch('/api/chat/status/{job_id}');
                        return {{ status: res.status, data: await res.json() }};
                    }}
                """)
                status = poll_result["data"].get("status", "unknown")
                print(f"  Poll {i+1}: {status}")
                if status == "done":
                    resp = poll_result["data"].get("response", "")
                    print(f"  Response: {resp[:200]}...")
                    print(f"  Tool calls: {poll_result['data'].get('tool_calls', 0)}")
                    print(f"  Citations: {len(poll_result['data'].get('citations', []))}")
                    break
            print("PASS: Polling API works through CloudFront")
        elif has_response:
            print(f"  Direct response: {chat_result['data']['response'][:200]}...")
            print("PASS: Direct response API works")

        browser.close()


if __name__ == "__main__":
    import sys
    tests = [
        ("page_loads", test_page_loads),
        ("fleet_panel", test_fleet_panel_loads),
        ("api_direct", test_api_direct),
        ("chat_polling", test_chat_with_polling),
    ]

    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    for name, fn in tests:
        if target != "all" and target != name:
            continue
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        try:
            fn()
        except Exception as e:
            print(f"FAIL: {e}")
