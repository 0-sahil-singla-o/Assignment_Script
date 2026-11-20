"""
Instruction Analyzer powered by Gemini.
Analyzes user-uploaded assignment instructions and splits them into:
1. Physical PDF Layout & Visual Specs (Strictly JSON for ReportLab compiler)
2. Content, Word Count, and Academic Guidelines (Text for Gemini's writing prompt)
"""
import json
import re
from typing import Dict, Any, Tuple
from google import genai

DEFAULT_PDF_SPECS = {
    "page_margin_inch": 1.0,
    "page_size": "A4",
    "orientation": "PORTRAIT",
    "font_family": "Times-Roman",
    "font_size": 12,
    "alignment": "JUSTIFIED",
    "max_pages": 12,
    "allow_shading": False,
    "allow_colors": False,
    "plain_code_blocks": True
}

def analyze_instructions_with_gemini(
    raw_text: str,
    gemini_api_key: str
) -> Tuple[Dict[str, Any], str]:
    """
    Extracts PDF layout specifications (JSON) and content/academic guidelines (text)
    from uploaded instruction documents.
    """
    if not raw_text or not raw_text.strip():
        return DEFAULT_PDF_SPECS.copy(), "Follow standard university academic standards: 400-500 words for 10-mark questions, 200-250 for 5-mark questions. Times New Roman tone, Justified."

    client = genai.Client(api_key=gemini_api_key)

    prompt = f"""
You are an expert academic document parser and layout specifications analyst.
Analyze the following assignment instructions text and split it cleanly into two separate components:

COMPONENT 1: PHYSICAL PDF LAYOUT & VISUAL SPECIFICATIONS (JSON ONLY)
Extract ONLY physical PDF page rendering and styling parameters:
- "page_margin_inch": float (e.g. 1.0, 0.75, 1.25. Default is 1.0)
- "page_size": string ("A4" or "LETTER". Default "A4")
- "orientation": string ("PORTRAIT" or "LANDSCAPE". Default "PORTRAIT")
- "font_family": string ("Times-Roman" or "Helvetica". Default "Times-Roman")
- "font_size": int (Default 12)
- "alignment": string ("JUSTIFIED" or "LEFT". Default "JUSTIFIED")
- "max_pages": int or null (e.g. 12)
- "allow_shading": boolean. If instructions state 'NOT contain color images or highlighting of text content', 'no shading', 'plain white', 'no shaded boxes', or similar, set to false. Otherwise default to false for clean formal academic submissions.
- "allow_colors": boolean. If instructions state no color images or highlighting, set to false. Default to false.
- "plain_code_blocks": boolean. If true, code snippets should be plain unshaded text without grey/blue background boxes. Default to true.

COMPONENT 2: CONTENT, WORD COUNT & ACADEMIC GUIDELINES (TEXT)
Extract ALL content, word-count, and academic guidelines that the AI writer MUST follow when answering questions.
Do NOT omit any word count requirements! Include:
- Exact mark-to-word count requirements (e.g., 'Every 10-mark answer must be between 400 and 500 words', 'Every 5-mark answer must be between 200 and 250 words', 'Word count must never fall below lower limit or exceed upper limit')
- Tone and analytical depth requirements (theoretical depth, architectural concepts, clear explanations)
- Examples and code requirements (minimal conceptual snippets, no large boilerplate dumps)
- Plagiarism and originality rules (no copy-pasting, original humanized phrasing)
- Any specific syllabus guidelines or assignment submission rules

OUTPUT FORMAT:
Output ONLY a raw valid JSON object with EXACTLY two keys:
{{
  "pdf_layout_specs": {{
    "page_margin_inch": 1.0,
    "page_size": "A4",
    "orientation": "PORTRAIT",
    "font_family": "Times-Roman",
    "font_size": 12,
    "alignment": "JUSTIFIED",
    "max_pages": 12,
    "allow_shading": false,
    "allow_colors": false,
    "plain_code_blocks": true
  }},
  "content_guidelines": "Comprehensive text of all word count rules, academic guidelines, answering standards, and course instructions..."
}}

INSTRUCTIONS TEXT TO ANALYZE:
\"\"\"
{raw_text[:15000]}
\"\"\"
"""
    # Model fallback list
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-3.5-flash"
    ]

    last_error = None
    for model_id in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            raw_output = response.text or ""
            clean = raw_output.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            parsed = json.loads(clean)
            specs = parsed.get("pdf_layout_specs", {})
            # Merge with defaults to guarantee all keys exist
            final_specs = {**DEFAULT_PDF_SPECS, **specs}
            content_guidelines = parsed.get("content_guidelines", "")
            if not content_guidelines:
                content_guidelines = raw_text

            return final_specs, content_guidelines
        except Exception as e:
            last_error = e
            continue

    # Graceful fallback if API fails
    print(f"Warning: Instruction analysis using Gemini failed ({last_error}). Falling back to defaults.")
    return DEFAULT_PDF_SPECS.copy(), raw_text
