from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from engagements.models import Engagement
from .utils import get_driver
from .modules.login_brute import run_login_brute
from .modules.xss_detect import run_xss_scan
from .modules.form_enum import run_form_enum
from .nova import generate_auto_analysis, chat_with_nova


from CyberShield.scanner.migrations.crawler import crawl_target, find_login_page, auto_detect_login_selectors

@login_required
def run_scan(request, engagement_id):
    print("=== RUN_SCAN CALLED ===")  # add this
    print("=== RUN_SCAN CALLED ===")
    engagement = get_object_or_404(Engagement, id=engagement_id)
    print(f"=== TARGET: {engagement.request.website_url!r} ===")

    engagement = get_object_or_404(Engagement, id=engagement_id)
    target = engagement.request.website_url

    if not target:
        messages.error(request, "No target URL set on this engagement's request.")
        return redirect("users:pentester_dashboard")

    driver = get_driver(headless=True)
    all_findings = []

    try:
        # Step 1: crawl and discover pages
        pages = crawl_target(driver, target, max_pages=10)

        # Step 2: scan every discovered page for XSS and forms
        for page in pages:
            all_findings.extend(run_xss_scan(driver, page))
            all_findings.extend(run_form_enum(driver, page))

        # Step 3: auto-detect and brute login page
        login_url = find_login_page(driver, pages)
        if login_url:
            selectors = auto_detect_login_selectors(driver, login_url)
            if selectors:
                all_findings.extend(run_login_brute(
                    driver,
                    target_url=login_url,
                    username_sel=selectors["username_sel"],
                    password_sel=selectors["password_sel"],
                    submit_sel=selectors["submit_sel"],
                ))

    finally:
        driver.quit()

    # ... rest unchanged

    # Save results
    for f in all_findings:
        ScanResult.objects.create(
            engagement=engagement,
            module=f.get("module", "unknown"),
            severity=f.get("severity", "info"),
            evidence=f.get("evidence", ""),
            detail=f,
        )

    # NOVA auto-analysis
    try:
        results = ScanResult.objects.filter(engagement=engagement)
        summary = generate_auto_analysis(results)
        NOVAAnalysis.objects.update_or_create(
            engagement=engagement,
            defaults={"summary": summary}
        )
    except Exception as e:
        pass  # don't break the scan if NOVA fails

    messages.success(request, f"Scan complete — {len(all_findings)} findings saved.")
    return redirect("scan_results", engagement_id=engagement_id)


from .models import ScanResult, NOVAAnalysis


def scan_results(request, engagement_id):
    engagement = get_object_or_404(Engagement, id=engagement_id)
    results = ScanResult.objects.filter(engagement=engagement)

    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
    results = sorted(results, key=lambda x: severity_order.get(x.severity, 5))

    counts = {
        'critical': sum(1 for r in results if r.severity == 'critical'),
        'high': sum(1 for r in results if r.severity == 'high'),
        'medium': sum(1 for r in results if r.severity == 'medium'),
        'low': sum(1 for r in results if r.severity == 'low'),
        'info': sum(1 for r in results if r.severity == 'info'),
    }

    try:
        nova_analysis = NOVAAnalysis.objects.get(engagement=engagement)
    except NOVAAnalysis.DoesNotExist:
        nova_analysis = None

    return render(request, 'scanner/results.html', {
        'engagement': engagement,
        'results': results,
        'counts': counts,
        'nova_analysis': nova_analysis,
    })


@login_required
@require_POST
def nova_chat(request, engagement_id):
    engagement = get_object_or_404(Engagement, id=engagement_id)
    results = ScanResult.objects.filter(engagement=engagement)

    data = json.loads(request.body)
    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    if not user_message:
        return JsonResponse({"error": "Empty message"}, status=400)

    try:
        reply = chat_with_nova(results, history, user_message)
        return JsonResponse({"reply": reply})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)