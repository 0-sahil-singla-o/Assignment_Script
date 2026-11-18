"""
Dedicated Question Scanner powered by Groq.
Dynamically fetches active models directly from Groq API to avoid deprecated models.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf

def extract_raw_text(file_path: Path) -> str:
    """Extracts raw text from PDF, DOCX, or TXT."""
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

def get_active_groq_models(groq_api_key: str) -> List[str]:
    """Dynamically queries Groq API for currently active chat models."""
    from openai import OpenAI
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
        all_models = client.models.list()
        # Filter for text chat models (exclude whisper, guard, embeddings)
        chat_models = [
            m.id for m in all_models.data
            if not any(skip in m.id.lower() for skip in ["whisper", "guard", "embed", "safeguard"])
        ]
        # Put llama-3.3 and llama models at the front
        chat_models.sort(key=lambda x: 0 if "llama-3.3" in x else (1 if "llama" in x else 2))
        return chat_models if chat_models else ["llama-3.3-70b-versatile"]
    except Exception as e:
        print(f"Error fetching active Groq models: {e}")
        return ["llama-3.3-70b-versatile"]

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
        "Analyze the provided assignment text and extract all assignment questions into a clean JSON list. "
        "Output ONLY a raw valid JSON array of objects without markdown formatting, code fences, or explanations."
    )

    user_prompt = f"""
Analyze this assignment text:
\"\"\"
{raw_text[:15000]}
\"\"\"

TASK:
Extract each question that a student must answer into a JSON list.
Each object must have:
- "number": integer (e.g. 1, 2, 3...)
- "text": the complete, clean question prompt text. Clean up any missing spaces caused by OCR/tables.
- "marks": integer marks assigned (default to 10 if not found).

Ignore all administrative guidelines, submission deadlines, emails, and university phone numbers.

Example JSON output format:
[
  {{"number": 1, "text": "Explain the difference between an HTML tag and an HTML element...", "marks": 10}},
  {{"number": 2, "text": "Explain the different types of JavaScript operators...", "marks": 10}}
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
            parsed = _parse_llm_json(raw_content)
            if parsed:
                return parsed
        except Exception as e:
            last_error = e
            continue

    if last_error:
        raise last_error

    return []

def _parse_llm_json(raw_str: str) -> List[Dict[str, Any]]:
    """Helper to clean and parse JSON array from LLM response."""
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
            return data
    except Exception as e:
        print(f"Error parsing Groq JSON: {e}\nRaw output was:\n{raw_str}")
    return []
