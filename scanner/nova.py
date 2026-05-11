import google.generativeai as genai
from django.conf import settings
import logging
import traceback

logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_AVAILABLE = False
model = None

if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)

        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)

        if available_models:
            model_name = available_models[0]
            model = genai.GenerativeModel(model_name)
            GEMINI_AVAILABLE = True
            print(f"Gemini configured successfully with model: {model_name}")
        else:
            print("No models with generateContent support found.")

    except Exception as e:
        print(f"Gemini configuration error: {e}")
        traceback.print_exc()
else:
    print("GEMINI_API_KEY not found in settings")


# ─── Scan-based helpers (existing) ────────────────────────────────────────────

def build_findings_context(results):
    if not results:
        return "No findings were recorded in this scan."
    lines = ["SCAN FINDINGS:"]
    for r in results:
        lines.append(f"\n[{r.severity.upper()}] {r.module}")
        lines.append(f"Evidence: {r.evidence}")
        if r.detail.get("username"):
            lines.append(f"Credentials: {r.detail['username']} / {r.detail['password']}")
        if r.detail.get("payload"):
            lines.append(f"Payload: {r.detail['payload']}")
        if r.detail.get("fields"):
            lines.append(f"Fields: {r.detail['fields']}")
    return "\n".join(lines)


def generate_auto_analysis(results):
    if not GEMINI_AVAILABLE:
        return "NOVA is unavailable: No Gemini models available or API key invalid."
    context = build_findings_context(results)
    prompt = f"""You are NOVA, an AI security analyst for CyberShield, a penetration testing platform.

A DAST scan has just completed. Analyze the findings below and provide:
1. A brief executive summary (2-3 sentences)
2. Top 3 most critical issues with a one-line explanation each
3. Immediate recommended actions (bullet points, max 5)
4. Overall risk rating: Critical / High / Medium / Low

Keep your response concise and professional. Use plain text, no markdown.

{context}"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        traceback.print_exc()
        return f"Error generating analysis: {str(e)}"


def chat_with_nova(results, conversation_history, user_message):
    if not GEMINI_AVAILABLE:
        return "NOVA is currently unavailable. Please check your API key."

    context = build_findings_context(results)
    full_prompt = f"""You are NOVA, an AI security analyst for CyberShield, a penetration testing platform.
You are helping a pentester understand and act on scan findings.
Be concise, technical, and specific to the findings provided.
Use plain text only, no markdown symbols.

SCAN CONTEXT:
{context}

Pentester: {user_message}
NOVA:"""

    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        traceback.print_exc()
        return f"Sorry, I encountered an error: {str(e)}"


# ─── Report-based analysis (NEW) ──────────────────────────────────────────────

def generate_report_analysis(report):
    """
    Generate a professional NOVA analysis for a pentester-written report.
    Called automatically when a report is submitted (status -> submitted).
    Returns the analysis string.
    """
    if not GEMINI_AVAILABLE:
        return "NOVA analysis unavailable: Gemini API not configured."

    prompt = f"""You are NOVA, an AI security analyst for CyberShield, a penetration testing platform.

A pentester has submitted a security assessment report. Analyze it and produce a structured review with:

1. EXECUTIVE SUMMARY (3-4 sentences suitable for a non-technical client)
2. SEVERITY ASSESSMENT — confirm or challenge the stated severity ({report.severity}) with a one-line justification
3. KEY FINDINGS — bullet list of the most important issues extracted from the findings
4. REMEDIATION PRIORITIES — top 3-5 actionable recommendations in priority order
5. RISK RATING — your independent overall risk rating: Critical / High / Medium / Low

Be professional, precise, and client-ready. Use plain text only, no markdown symbols.

--- REPORT DETAILS ---
Title: {report.title}
Engagement: {report.engagement.request.company_name} ({report.engagement.request.request_type})
Stated Severity: {report.severity}
Summary: {report.summary or 'Not provided'}
Findings: {report.findings or 'Not provided'}
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        traceback.print_exc()
        return f"NOVA analysis error: {str(e)}"