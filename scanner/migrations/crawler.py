from selenium.webdriver.common.by import By
from collections import deque
import time

def crawl_target(driver, base_url, max_pages=10):
    visited = set()
    queue = deque([base_url])

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited or not url.startswith(base_url):
            continue
        try:
            driver.get(url)
            time.sleep(0.4)
            visited.add(url)
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and href.startswith(base_url):
                    queue.append(href.split("#")[0])
        except Exception:
            continue

    print(f"[CRAWLER] Discovered pages: {visited}")  # add this line
    return visited


def find_login_page(driver, pages):
    """Return the URL most likely to be the login page."""
    login_hints = ["login", "signin", "sign-in", "auth", "account"]
    for url in pages:
        if any(hint in url.lower() for hint in login_hints):
            return url
    return None


def auto_detect_login_selectors(driver, login_url):
    """
    Heuristically detect username, password, and submit selectors
    from a login page. Returns dict or None if detection fails.
    """
    driver.get(login_url)
    time.sleep(0.5)

    password_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    if not password_fields:
        return None  # not a login form

    password_field = password_fields[0]
    password_name = password_field.get_attribute("name") or password_field.get_attribute("id")

    # Username is usually the input just before the password field
    all_inputs = driver.find_elements(By.TAG_NAME, "input")
    skip = {"hidden", "submit", "button", "checkbox", "radio", "file", "password"}
    text_inputs = [i for i in all_inputs if (i.get_attribute("type") or "text") not in skip]

    if not text_inputs:
        return None

    username_field = text_inputs[-1]  # last text input before password
    username_name = username_field.get_attribute("name") or username_field.get_attribute("id")

    # Submit: prefer button[type=submit], fallback to input[type=submit]
    submits = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
    if not submits:
        return None

    return {
        "username_sel": f"[name='{username_name}']",
        "password_sel": f"[name='{password_name}']",
        "submit_sel": "button[type='submit']",
    }