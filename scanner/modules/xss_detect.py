import time
from selenium.webdriver.common.by import By

XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    '"><script>alert(1)</script>',
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
]

def run_xss_scan(driver, target_url):
    findings = []
    driver.get(target_url)
    time.sleep(0.5)

    inputs = driver.find_elements(By.TAG_NAME, "input")
    skip_types = {"hidden", "submit", "button", "checkbox", "radio", "file"}

    for field in inputs:
        field_type = field.get_attribute("type") or "text"
        field_name = field.get_attribute("name") or field.get_attribute("id") or "unknown"

        if field_type in skip_types:
            continue

        for payload in XSS_PAYLOADS:
            driver.get(target_url)
            time.sleep(0.3)

            try:
                f = driver.find_element(By.NAME, field_name)
                f.clear()
                f.send_keys(payload)

                # Try submitting the form
                try:
                    f.submit()
                except:
                    pass

                time.sleep(0.5)

                # Check for alert dialog (script execution)
                try:
                    alert = driver.switch_to.alert
                    alert.dismiss()
                    findings.append({
                        "module": "xss",
                        "severity": "critical",
                        "field": field_name,
                        "payload": payload,
                        "evidence": "Alert dialog executed — confirmed XSS",
                    })
                    break
                except:
                    pass

                # Check for reflected payload in DOM
                if payload in driver.page_source:
                    findings.append({
                        "module": "xss",
                        "severity": "high",
                        "field": field_name,
                        "payload": payload,
                        "evidence": f"Payload reflected unescaped in response at {driver.current_url}",
                    })
                    break

            except Exception:
                continue

    return findings