"""
Academic Research & Answer Generation Engine.
Uses Gemini API with internet knowledge, enforces permanent humanizer rules,
and aligns answers with instructions retrieved from the Vector DB.
Includes resilient retry and automatic fallback across high-availability models.
"""
import re
import time
from typing import List, Dict, Any, Optional
from modules.permanent_rules import get_permanent_humanizer_rules
from modules.instruction_rag import InstructionRAGEngine

def count_words(text: str) -> int:
    """Accurately counts words in text, ignoring code block markers."""
    clean = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    words = re.findall(r'\b[A-Za-z0-9\-\']+\b', clean)
    return len(words)

class GeminiAssignmentWriter:
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.permanent_rules = get_permanent_humanizer_rules()
        self._init_client()

    def _init_client(self):
        """Initializes Google GenAI client."""
        from google import genai
        self.client = genai.Client(api_key=self.api_key)

    def _generate_with_fallback(self, prompt: str) -> str:
        """
        Attempts generation using active resilient models with automatic retry on 503/429 spikes.
        Models prioritized: gemini-3.5-flash -> gemini-3.5-flash-lite -> gemini-3.1-flash-lite.
        """
        models_to_try = [
            self.model_name,
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite"
        ]
        unique_models = []
        for m in models_to_try:
            if m not in unique_models:
                unique_models.append(m)

        last_err = None
        for model_id in unique_models:
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model_id,
                        contents=prompt
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    last_err = e
                    err_str = str(e)
                    # If 503 high demand or temporary spike, wait 2 seconds before retry
                    if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                        time.sleep(2)
                        continue
                    else:
                        break  # Fall back to next model immediately for other errors

        if last_err:
            raise last_err
        return ""

    def draft_answer(
        self,
        question: Dict[str, Any],
        rag_engine: Optional[InstructionRAGEngine] = None
    ) -> Dict[str, Any]:
        """
        Researches and drafts an in-depth academic answer for a single question.
        Adheres to RAG-retrieved instructions and permanent humanizer rules.
        """
        q_num = question.get("number", 1)
        q_text = question.get("text", "")
        marks = question.get("marks", 10)

        # Retrieve instructions from Vector DB
        retrieved_instructions = ""
        if rag_engine:
            retrieved_instructions = rag_engine.get_instructions_context(q_text)

        # Target word count based on marks
        if marks >= 10:
            target_min, target_max = 400, 500
        elif marks >= 5:
            target_min, target_max = 200, 250
        else:
            target_min, target_max = 300, 450

        system_prompt = f"""
{self.permanent_rules}

ASSIGNMENT INSTRUCTIONS (RETRIEVED FROM VECTOR DATABASE):
{retrieved_instructions if retrieved_instructions else "Follow standard university academic standards: 400-500 words for 10-mark questions, 200-250 for 5-mark questions. Times New Roman tone, Justified."}
"""

        user_prompt = f"""
QUESTION {q_num} ({marks} Marks):
{q_text}

MANDATORY WRITING & PRESENTATION REQUIREMENTS:
1. Target Word Count: You MUST write between {target_min} and {target_max} words. Provide deep academic, theoretical, and practical analysis.
2. Academic Paper Presentation:
   - This is a formal university examination submission, NOT a coding sandbox or terminal session.
   - NEVER output ASCII art diagrams or character boxes (+----+).
   - Do NOT output raw Markdown header hashes (#, ##, ###). Use bold numbered headings like '**1. Title**'.
   - If code is needed, include ONLY compact, focused snippets (3 to 6 lines max) illustrating the core syntax. Never paste full boilerplate files or terminal outputs.
   - For mathematical or layout sizing, write readable text formulas (e.g. *Total Width = Content Width + Padding + Border*), never LaTeX dollars ($$).
   - Avoid raw backticks around standard words; use bold (**term**) for key terminology.
3. Anti-AI Cadence: Start immediately without introductory throat-clearing. Vary your sentence lengths. Strictly avoid banned vocabulary (no delve, testament, furthermore, seamless, crucial, tapestry, beacon, paramount).
4. Accuracy: Ensure all technical facts, syntax, and comparisons are up to date and accurate.
"""

        full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

        # Generate draft with fallback
        answer = self._generate_with_fallback(full_prompt)
        word_count = count_words(answer)

        # Word count audit loop (expand if under target)
        if word_count < (target_min - 35):
            expansion_prompt = f"""
{system_prompt}

The answer below for Question {q_num} ({marks} Marks) is currently only {word_count} words.
The requirement is strictly between {target_min} and {target_max} words.

Current Draft:
\"\"\"
{answer}
\"\"\"

TASK:
Expand this answer to meet between {target_min} and {target_max} words.
Add more analytical depth, architectural comparison, and theoretical context.
Do NOT add large code dumps or ASCII diagrams. Keep code minimal (3-5 lines max).
Maintain the authentic humanized student tone without banned words.
Output ONLY the complete revised answer.
"""
            try:
                revised_answer = self._generate_with_fallback(expansion_prompt)
                if revised_answer:
                    answer = revised_answer
                    word_count = count_words(answer)
            except Exception as e:
                # If expansion experiences a server spike, keep the already-generated draft safely
                print(f"Notice: Word expansion skipped due to temporary server load ({e}). Using base answer.")

        return {
            "number": q_num,
            "question": q_text,
            "marks": marks,
            "answer": answer.strip(),
            "word_count": word_count
        }
