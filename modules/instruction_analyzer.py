"""
Instruction Analyzer powered by Gemini.
Analyzes user-uploaded assignment instructions and splits them into:
1. Physical PDF Layout & Visual Specs (Strictly JSON for ReportLab compiler)
2. Content, Word Count, and Academic Guidelines (Text for Gemini's writing prompt)
Course metadata is excluded as it is configured independently in Step 1.
"""
import json
import re
from typing import Dict, Any, Tuple
from google import genai

DEFAULT_PDF_SPECS = {
    # Page Geometry & Limits
    "page_size": "A4",                # "LETTER" (US Letter), "A4", "LEGAL"
    "orientation": "PORTRAIT",        # "PORTRAIT" or "LANDSCAPE"
    "page_margin_inch": 1.0,          # float (uniform margin e.g. 1.25, 1.0, 0.75)
    "top_margin_inch": None,          # directional margin if specified
    "bottom_margin_inch": None,
    "left_margin_inch": None,
    "right_margin_inch": None,
    "max_pages": 12,                  # int or null
    "max_file_size_mb": 2.0,          # float or null (e.g. 1.0)

    # Typography, Spacing & Color
    "font_family": "Times-Roman",     # "Arial", "Times-Roman", "Helvetica", "Calibri", "Georgia", "Verdana"
    "font_size": 12,                  # int or float (e.g. 11, 12, 10)
    "font_color": "#000000",          # hex code e.g. "#1F3864", "#000000"
    "line_spacing": 1.33,             # float (e.g. 1.5, 1.15, 2.0, 1.0)
    "alignment": "JUSTIFIED",         # "LEFT", "JUSTIFIED", "CENTER"
    "paragraph_spacing_pt": 8,        # space after paragraphs in points

    # Heading & Section Hierarchy
    "heading_font_family": None,      # e.g. "Arial-Bold", "Times-Bold" or null (inherits)
    "heading_font_size": 13,          # int or float
    "heading_font_color": None,       # hex code or null (inherits font_color)

    # Visual Constraints
    "allow_color_images": True,       # false if instructions state 'NOT contain color images'
    "allow_text_highlighting": False, # false if instructions state 'no highlighting of text content'
    "allow_shading": False,           # false if no shaded boxes / plain white
    "plain_code_blocks": True,        # true if unshaded textbook code blocks
    "table_borders": "GRID",          # "GRID", "SIMPLE_LINES"

    # Header & Footer Pagination
    "page_numbering_format": "Page X of Y",  # "Page X of Y", "Page X", "X / Y"
    "page_number_position": "BOTTOM_RIGHT",  # "BOTTOM_RIGHT", "BOTTOM_CENTER"
    "header_rule_line": True          # boolean (draw divider line under running header)
}

def analyze_instructions_with_gemini(
    raw_text: str,
    gemini_api_key: str
) -> Tuple[Dict[str, Any], str]:
    """
    Extracts physical PDF layout specifications (JSON) and writing/content guidelines (text)
    from uploaded instruction documents.
    """
    if not raw_text or not raw_text.strip():
        return DEFAULT_PDF_SPECS.copy(), "Follow standard university academic standards: 400-500 words for 10-mark questions, 200-250 for 5-mark questions. Authentic student cadence, no plagiarism."

    client = genai.Client(api_key=gemini_api_key)

    prompt = f"""
You are an expert academic document parser and document layout analyst.
Analyze the following assignment instructions text and split it cleanly into TWO separate components:

--------------------------------------------------------------------------------
COMPONENT 1: PHYSICAL PDF LAYOUT & VISUAL SPECIFICATIONS (JSON ONLY)
Extract ONLY physical document formatting and page styling rules for the PDF compiler.
DO NOT include course metadata (Session, Program, Course Code) or word counts here.
Extract the following exact fields:

A. Page Geometry & Limits:
- "page_size": string. Look for "US Letter" -> "LETTER", "A4" -> "A4", "Legal" -> "LEGAL". Default: "A4".
- "orientation": string. "PORTRAIT" or "LANDSCAPE". Default: "PORTRAIT".
- "page_margin_inch": float. If instructions say "1.25 inch on all sides", extract 1.25. If 1 inch, extract 1.0. Default: 1.0.
- "top_margin_inch", "bottom_margin_inch", "left_margin_inch", "right_margin_inch": float or null. Extract only if distinct directional margins are specified (e.g. left margin 1.5 for binding). Otherwise null.
- "max_pages": integer or null. E.g. "shall not exceed 10 pages" -> 10. Default: 12.
- "max_file_size_mb": float or null. E.g. "less than 1 MB" -> 1.0. Default: 2.0.

B. Typography, Spacing & Color:
- "font_family": string. Extract the exact font family requested, e.g. "Arial", "Times-Roman", "Calibri", "Helvetica", "Georgia". If "Arial", extract "Arial". Default: "Times-Roman".
- "font_size": integer or float. E.g. 11, 12, 10. Default: 12.
- "font_color": string (hex code). If document specifies "Dark Blue (#1F3864)", extract "#1F3864". If black or unspecified, extract "#000000".
- "line_spacing": float. E.g. 1.5 for 1.5 line spacing, 2.0 for double, 1.0 for single. Default: 1.33.
- "alignment": string. "LEFT", "JUSTIFIED", "CENTER". E.g. "Alignment: Left" -> "LEFT". Default: "JUSTIFIED".
- "paragraph_spacing_pt": integer or float. Default: 8.

C. Heading & Section Hierarchy:
- "heading_font_family": string or null. E.g. "Arial-Bold" or null.
- "heading_font_size": integer or float. Default: 13.
- "heading_font_color": string or null. E.g. "#1F3864" or null (inherits font_color).

D. Visual & Content Constraints:
- "allow_color_images": boolean. If instructions state 'NOT contain color images', extract false. Default: true.
- "allow_text_highlighting": boolean. If instructions state 'no highlighting of text content', extract false. Default: false.
- "allow_shading": boolean. If instructions state plain white, no shaded boxes, extract false. Default: false.
- "plain_code_blocks": boolean. If code blocks should be clean unshaded textbook text, extract true. Default: true.
- "table_borders": string. "GRID" or "SIMPLE_LINES". Default: "GRID".

E. Header & Footer Pagination:
- "page_numbering_format": string. E.g. "Page X of Y", "Page X", "X / Y". Default: "Page X of Y".
- "page_number_position": string. "BOTTOM_RIGHT", "BOTTOM_CENTER". Default: "BOTTOM_RIGHT".
- "header_rule_line": boolean. Default: true.

--------------------------------------------------------------------------------
COMPONENT 2: STRUCTURED AI WRITING DIRECTIVES (TEXT FOR GEMINI PROMPT)
Do NOT output raw unorganized paragraphs or bureaucratic portal text (e.g. do NOT copy-paste "download IA question paper", "submit through LMS portal", "check preview tab", "submission deadline").
Instead, SYNTHESIZE all content, length, and integrity rules into a high-authority, structured AI WRITING DIRECTIVE:

### 1. EXACT MARK-TO-WORD COUNT RULES
- 10-Mark Questions: State the exact numerical word range (e.g., strictly between 300 and 350 words).
- 5-Mark Questions: State the exact numerical word range (e.g., strictly between 150 and 200 words).
- Mandatory Rule: Answers must fall precisely within these boundaries without underwriting or overwriting.

### 2. ACADEMIC INTEGRITY & ORIGINALITY DIRECTIVE
- Zero-Plagiarism Mandate: Explicit prohibition on copying from Internet sources, online articles, or official Self-Learning Material (SLM).
- Authentic Student Cadence: Require original synthesis, human-like sentence variety (burstiness), domain-specific vocabulary, and elimination of robotic AI clichés.

### 3. CONTENT & VISUAL CONSTRAINTS
- Explicitly state prohibition of color images, graphics, and text highlighting.
- Require high conceptual and architectural depth, clear academic subheadings, and minimal conceptual code snippets.

--------------------------------------------------------------------------------
OUTPUT FORMAT:
Output ONLY a raw valid JSON object with EXACTLY two keys:
{{
  "pdf_layout_specs": {{
    "page_size": "LETTER",
    "orientation": "PORTRAIT",
    "page_margin_inch": 1.25,
    "top_margin_inch": null,
    "bottom_margin_inch": null,
    "left_margin_inch": null,
    "right_margin_inch": null,
    "max_pages": 10,
    "max_file_size_mb": 1.0,
    "font_family": "Arial",
    "font_size": 11,
    "font_color": "#1F3864",
    "line_spacing": 1.5,
    "alignment": "LEFT",
    "paragraph_spacing_pt": 8,
    "heading_font_family": null,
    "heading_font_size": 13,
    "heading_font_color": null,
    "allow_color_images": false,
    "allow_text_highlighting": false,
    "allow_shading": false,
    "plain_code_blocks": true,
    "table_borders": "GRID",
    "page_numbering_format": "Page X of Y",
    "page_number_position": "BOTTOM_RIGHT",
    "header_rule_line": true
  }},
  "content_guidelines": "Comprehensive text of all word count rules, academic guidelines, answering standards, and course instructions..."
}}

INSTRUCTIONS TEXT TO ANALYZE:
\"\"\"
{raw_text[:15000]}
\"\"\"
"""
    # Active Gemini models with fallback
    models_to_try = [
        "gemini-3.5-flash-lite",
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
            
            # Robust JSON extraction (handles markdown code fences and preamble text)
            json_candidate = clean
            match = re.search(r'(\{.*\})', clean, re.DOTALL)
            if match:
                json_candidate = match.group(1)
            else:
                if clean.startswith("```json"):
                    json_candidate = clean[7:]
                elif clean.startswith("```"):
                    json_candidate = clean[3:]
                if json_candidate.endswith("```"):
                    json_candidate = json_candidate[:-3]
            
            parsed = json.loads(json_candidate.strip())
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
