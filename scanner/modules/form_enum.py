import time
from selenium.webdriver.common.by import By

def run_form_enum(driver, target_url):
    driver.get(target_url)
    time.sleep(0.5)

    findings = []
    inputs = driver.find_elements(By.TAG_NAME, "input")
    textareas = driver.find_elements(By.TAG_NAME, "textarea")
    selects = driver.find_elements(By.TAG_NAME, "select")

    hidden_fields = []
    all_fields = []

    for el in inputs:
        field_type = el.get_attribute("type") or "text"
        field_name = el.get_attribute("name") or el.get_attribute("id") or "unnamed"
        field_value = el.get_attribute("value") or ""

        all_fields.append({"name": field_name, "type": field_type})

        if field_type == "hidden":
            hidden_fields.append({"name": field_name, "value": field_value})

    for el in textareas:
        all_fields.append({"name": el.get_attribute("name") or "unnamed", "type": "textarea"})

    for el in selects:
        all_fields.append({"name": el.get_attribute("name") or "unnamed", "type": "select"})

    if all_fields:
        findings.append({
            "module": "form_enum",
            "severity": "info",
            "evidence": f"Discovered {len(all_fields)} input fields: {[f['name'] for f in all_fields]}",
            "fields": all_fields,
        })

    if hidden_fields:
        findings.append({
            "module": "form_enum",
            "severity": "medium",
            "evidence": f"Found {len(hidden_fields)} hidden fields with exposed values: {hidden_fields}",
            "fields": hidden_fields,
        })

    return findings