
import pytest
from playwright.sync_api import sync_playwright

def test_mock():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://example.com")
        print("Mock test executed for https://example.com")
        browser.close()

if __name__ == "__main__":
    test_mock()
