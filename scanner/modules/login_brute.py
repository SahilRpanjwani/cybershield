import time
from selenium.webdriver.common.by import By

COMMON_PASSWORDS = [
    "admin", "password", "123456", "admin123",
    "test", "guest", "root", "toor", "pass", "qwerty",
]

def run_login_brute(driver, target_url, username_sel, password_sel, submit_sel, usernames=None):
    if usernames is None:
        usernames = ["admin", "test", "user", "root", "guest"]

    findings = []

    for username in usernames:
        for password in COMMON_PASSWORDS:
            driver.get(target_url)
            time.sleep(0.4)

            try:
                driver.find_element(By.CSS_SELECTOR, username_sel).send_keys(username)
                driver.find_element(By.CSS_SELECTOR, password_sel).send_keys(password)
                driver.find_element(By.CSS_SELECTOR, submit_sel).click()
                time.sleep(0.8)

                current_url = driver.current_url
                page_text = driver.page_source.lower()
                fail_keywords = ["invalid", "incorrect", "wrong", "error", "failed"]
                failed = any(k in page_text for k in fail_keywords)

                if current_url != target_url and not failed:
                    findings.append({
                        "module": "login_brute",
                        "severity": "critical",
                        "username": username,
                        "password": password,
                        "evidence": f"Login succeeded — redirected to {current_url}",
                    })
                    break  # found one for this username, move on

            except Exception as e:
                continue

            time.sleep(0.2)

    return findings