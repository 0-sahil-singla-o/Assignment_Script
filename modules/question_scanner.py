"""
Dedicated Question Scanner powered by Groq.
Dynamically fetches active models directly from Groq API to avoid deprecated models.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf

def is_meaningful_question_text(text: str) -> tuple[bool, str]:
    """
    Validates whether raw input text contains plausible question/assignment content.
    Rejects empty, too short, unbroken strings (gibberish), or non-textual spam.
    """
    cleaned = text.strip()
    if len(cleaned) < 15:
        return False, "Input text is too short (minimum 15 characters required)."

    # Extract words
    words = [w for w in re.split(r'\s+', cleaned) if len(w) > 0]
    if len(words) < 2:
        return False, "Input appears to be a single unbroken string or random characters. Please provide valid assignment questions."

    # Check for excessive single-character repetition (e.g. 'aaaaa', 'asdasdasdasd')
    if re.search(r'(.)\1{5,}', cleaned):
        return False, "Input contains repetitive random characters. Please provide valid question paper text."

    # Check average word length - normal English words average 3-9 characters. Above 20 is almost certainly gibberish
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len > 22:
        return False, "Input contains unreadable or random text. Please provide valid assignment questions."

    # Verify minimum letter content
    letter_count = len(re.findall(r'[a-zA-Z]', cleaned))
    if letter_count < 10:
        return False, "Input does not contain sufficient readable text or questions."

    return True, ""

def extract_raw_text(file_path) -> str:
    """Extracts raw text from PDF, DOCX, or TXT."""
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        text_parts = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        except Exception as e:
            print(f"Error reading PDF with pypdf: {e}")
        return "\n\n".join(text_parts)
    elif ext in [".docx", ".doc"]:
        import docx
        doc = docx.Document(str(file_path))
        return "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""

_CACHED_GROQ_MODELS = None
_CACHE_TIMESTAMP = 0

def get_active_groq_models(groq_api_key: str) -> List[str]:
    """Dynamically queries Groq API for currently active chat models with memory cache."""
    global _CACHED_GROQ_MODELS, _CACHE_TIMESTAMP
    import time
    now = time.time()
    if _CACHED_GROQ_MODELS and (now - _CACHE_TIMESTAMP < 600):
        return _CACHED_GROQ_MODELS

    from openai import OpenAI
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key, timeout=4.0)
        all_models = client.models.list()
        # Filter for pure text chat models (exclude whisper, guard, embeddings, audio, tts, orpheus, canopylabs)
        excluded_keywords = [
            "whisper", "guard", "embed", "safeguard", "orpheus",
            "canopylabs", "audio", "tts", "arabic", "vision"
        ]
        chat_models = [
            m.id for m in all_models.data
            if not any(skip in m.id.lower() for skip in excluded_keywords)
        ]
        # Priority order: qwen, gpt-oss-120b, llama-3.3, llama, gpt-oss-20b, allam
        def model_priority(m_id: str) -> int:
            low = m_id.lower()
            if "qwen" in low:
                return 0
            if "120b" in low:
                return 1
            if "llama-3.3" in low:
                return 2
            if "llama" in low:
                return 3
            if "20b" in low:
                return 4
            if "allam" in low:
                return 5
            return 6

        chat_models.sort(key=model_priority)
        result = chat_models if chat_models else ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
        _CACHED_GROQ_MODELS = result
        _CACHE_TIMESTAMP = now
        return result
    except Exception as e:
        print(f"Notice: Using cached/fallback Groq models ({e})")
        return _CACHED_GROQ_MODELS or ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]

def scan_questions_with_gemini(raw_text: str, gemini_api_key: str) -> List[Dict[str, Any]]:
    """Fallback scanner using Google Gemini API."""
    from google import genai
    client = genai.Client(api_key=gemini_api_key)
    prompt = f"""
You are an expert academic document parser.
Your task is to extract only the explicit assignment questions that are actually present in the provided text into a clean JSON list.
CRITICAL: If the text does not contain actual academic questions, is random gibberish, letters without meaning, or administrative notices without questions, you MUST return strictly an empty JSON array: []
Do NOT invent, fabricate, or hallucinate questions.
Output ONLY a raw valid JSON array of objects without markdown formatting or code fences.

Assignment text:
\"\"\"
{raw_text[:15000]}
\"\"\"

TASK:
Extract each explicit question that a student must answer into a JSON list.
Each object must have:
- "number": integer (e.g. 1, 2, 3...)
- "text": the complete question prompt text verbatim from the document.
- "marks": integer marks assigned (default to 5 if not found).

STRICT CONSTRAINTS:
1. ONLY extract questions that explicitly exist in the assignment text above.
2. If the text has NO questions, is random characters, or lacks academic question content, return strictly: []
3. DO NOT hallucinate, assume, or invent questions.

Example JSON output format:
[
  {{"number": 1, "text": "<question text from document>", "marks": 5}}
]
"""
    for model_id in ["gemini-3.5-flash-lite", "gemini-3.5-flash"]:
        try:
            resp = client.models.generate_content(model=model_id, contents=prompt)
            if resp and resp.text:
                parsed = _parse_llm_json(resp.text, source_text=raw_text)
                if parsed:
                    return parsed
        except Exception as e:
            print(f"Gemini scanner fallback attempt failed with {model_id}: {e}")
            continue
    return []

def scan_questions_with_groq(
    raw_text: str,
    groq_api_key: str,
    model_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Scans and extracts assignment questions using active Meta Llama models on Groq.
    Dynamically falls back to currently active models on Groq.
    """
    from openai import OpenAI
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_api_key
    )

    system_prompt = (
        "You are an expert academic document parser. "
        "Your task is to extract only the explicit questions that are actually present in the provided assignment text into a clean JSON list. "
        "CRITICAL: If the assignment text does not contain actual academic questions, consists of gibberish, random characters, unreadable text, or casual remarks, you MUST return strictly an empty JSON array: []. "
        "Do NOT invent, assume, or hallucinate questions. "
        "Output ONLY a raw valid JSON array of objects without markdown formatting, code fences, or explanations."
    )

    user_prompt = f"""
Analyze this assignment text:
\"\"\"
{raw_text[:15000]}
\"\"\"

TASK:
Extract each explicit question that a student must answer into a JSON list.
Each object must have:
- "number": integer (e.g. 1, 2, 3...)
- "text": the complete, clean question prompt text as written in the document.
- "marks": integer marks assigned (default to 5 if not found).

STRICT NEGATIVE CONSTRAINTS:
1. ONLY extract questions that explicitly exist in the assignment text above.
2. If the text has NO questions, is random gibberish (e.g. "sdasdasdas"), or lacks educational content, output strictly: []
3. Absolutely DO NOT invent or fabricate questions.

Expected JSON output format:
[
  {{"number": 1, "text": "<question text from document>", "marks": 5}}
]
"""
    # Fetch actual live models from the user's Groq account
    active_models = get_active_groq_models(groq_api_key)
    
    # Prioritize user chosen model if specified and valid
    models_to_try = []
    if model_name and model_name in active_models:
        models_to_try.append(model_name)
    models_to_try.extend([m for m in active_models if m not in models_to_try])

    last_error = None
    for target_model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            raw_content = response.choices[0].message.content or ""
            parsed = _parse_llm_json(raw_content, source_text=raw_text)
            if parsed:
                return parsed
        except Exception as e:
            print(f"Notice: Groq scan attempt with model {target_model} failed: {e}. Trying next active model...")
            last_error = e
            continue

    if last_error:
        raise last_error

    return []

def _is_hallucinated(q_text: str, source_text: Optional[str]) -> bool:
    """Verifies that the extracted question text actually corresponds to the source text."""
    if not source_text or not q_text:
        return False
    
    # Catch prompt placeholder leaks
    if "<question text" in q_text.lower():
        return True
    
    # Extract substantive words (length >= 4) from the extracted question
    substantive_q_words = [w.lower() for w in re.findall(r'[a-zA-Z]{4,}', q_text)]
    if not substantive_q_words:
        return False
    
    source_lower = source_text.lower()
    matches = sum(1 for w in substantive_q_words if w in source_lower)
    match_ratio = matches / len(substantive_q_words)
    # If less than 20% of substantive words exist anywhere in the source document, it's a hallucination
    return match_ratio < 0.20

def _parse_llm_json(raw_str: str, source_text: Optional[str] = None) -> List[Dict[str, Any]]:
    """Helper to clean and parse JSON array from LLM response and filter hallucinated items."""
    clean = raw_str.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    if clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    try:
        data = json.loads(clean)
        if isinstance(data, list):
            valid_questions = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                q_text = str(item.get("text", "")).strip()
                if not q_text or len(q_text) < 5:
                    continue
                # Discard items that are hallucinated or leaked placeholders
                if _is_hallucinated(q_text, source_text):
                    print(f"Filtered out hallucinated question: {q_text[:60]}...")
                    continue
                
                # Normalize marks (defaults to 5 if missing or <= 0, capped at max 50)
                try:
                    marks_val = item.get("marks")
                    marks = int(marks_val) if marks_val is not None and str(marks_val).strip() else 5
                    if marks <= 0:
                        marks = 5
                    elif marks > 50:
                        marks = 50
                except (ValueError, TypeError):
                    marks = 5
                
                valid_questions.append({
                    "number": item.get("number", len(valid_questions) + 1),
                    "text": q_text,
                    "marks": marks,
                    "sub_parts": item.get("sub_parts", [])
                })
            return valid_questions
    except Exception as e:
        print(f"Error parsing LLM JSON: {e}\nRaw output was:\n{raw_str}")
    return []
