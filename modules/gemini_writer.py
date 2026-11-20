"""
Academic Research & Answer Generation Engine.
Uses Gemini API with internet knowledge, enforces permanent humanizer rules,
and aligns answers directly with content instructions uploaded by the user.
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
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash-lite"):
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
        Models prioritized: user model -> gemini-3.5-flash-lite -> gemini-3.5-flash.
        """
        models_to_try = [
            self.model_name,
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash"
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
        content_instructions: str = "",
        rag_engine: Optional[InstructionRAGEngine] = None
    ) -> Dict[str, Any]:
        """
        Researches and drafts an in-depth academic answer for a single question.
        Adheres directly to user-provided content instructions and permanent humanizer rules.
        """
        q_num = question.get("number", 1)
        q_text = question.get("text", "")
        marks = question.get("marks", 10)

        # Combine content instructions with RAG context if both exist
        active_instructions = content_instructions.strip()
        if not active_instructions and rag_engine:
            active_instructions = rag_engine.get_instructions_context(q_text)

        # Determine target word count based on marks and instructions
        # Standard university assessment benchmarks (e.g. Manipal / CDOE):
        # 10 marks -> strictly 300 to 350 words
        # 5 marks  -> strictly 150 to 200 words
        if marks >= 10:
            target_min, target_max = 300, 350
        elif marks >= 5:
            target_min, target_max = 150, 200
        else:
            target_min, target_max = 250, 300

        # Dynamically check if content_instructions specifies a custom word range for this mark tier
        if active_instructions:
            pattern = rf'{marks}\s*[-\s]?marks?.*?(\d{{2,4}})\s*(?:to|-)\s*(\d{{2,4}})\s*words?'
            m_match = re.search(pattern, active_instructions, re.IGNORECASE)
            if m_match:
                target_min = int(m_match.group(1))
                target_max = int(m_match.group(2))
            else:
                gen_pattern = r'(\d{2,4})\s*(?:to|-)\s*(\d{2,4})\s*words?'
                gen_match = re.search(gen_pattern, active_instructions, re.IGNORECASE)
                if gen_match and marks >= 10:
                    target_min = int(gen_match.group(1))
                    target_max = int(gen_match.group(2))

        system_prompt = f"""
{self.permanent_rules}

======================================================================
MANDATORY ASSIGNMENT & CONTENT GUIDELINES (UPLOADED BY EVALUATOR):
{active_instructions if active_instructions else "Follow standard university academic standards: 300-350 words for 10-mark questions, 150-200 for 5-mark questions. Times New Roman tone, Justified."}
======================================================================
"""

        user_prompt = f"""
QUESTION {q_num} ({marks} Marks):
{q_text}

MANDATORY WRITING & CONTENT REQUIREMENTS:
1. Strict Word Count & Answering Guidelines:
   - Adhere strictly to the word range and answering guidelines given in the ASSIGNMENT INSTRUCTIONS above for a {marks}-mark question.
   - For this {marks}-mark question, you must write between {target_min} and {target_max} words. The word count must never fall below the lower limit ({target_min} words) or exceed the upper limit ({target_max} words).
   - Provide deep academic, theoretical, and practical analysis.
2. Academic Paper Presentation:
   - This is a formal university examination submission, NOT a coding sandbox or terminal session.
   - Plain academic writing only: NO color highlighting, NO shaded background boxes.
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

        # Word count audit loop: expand if under target
        if word_count < (target_min - 25):
            expansion_prompt = f"""
{system_prompt}

The answer below for Question {q_num} ({marks} Marks) is currently only {word_count} words.
The requirement is strictly between {target_min} and {target_max} words. The word count must never fall below {target_min} words.

Current Draft:
\"\"\"
{answer}
\"\"\"

TASK:
Expand this answer so its word count is between {target_min} and {target_max} words.
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
                print(f"Notice: Word expansion skipped due to temporary server load ({e}). Using base answer.")

        # Word count audit loop: condense/trim if over target
        elif word_count > (target_max + 15):
            trim_prompt = f"""
{system_prompt}

The answer below for Question {q_num} ({marks} Marks) is currently {word_count} words, which exceeds the strict upper limit of {target_max} words.
The requirement is strictly between {target_min} and {target_max} words (ideal target ~{(target_min + target_max)//2} words).

Current Draft:
\"\"\"
{answer}
\"\"\"

TASK:
Condense and tighten this answer so its word count is strictly between {target_min} and {target_max} words.
Remove redundant filler, streamline explanations, and keep all core technical concepts and code snippets intact.
Output ONLY the complete condensed revised answer.
"""
            try:
                revised_answer = self._generate_with_fallback(trim_prompt)
                if revised_answer:
                    answer = revised_answer
                    word_count = count_words(answer)
            except Exception as e:
                print(f"Notice: Word trimming skipped ({e}). Using base answer.")

        return {
            "number": q_num,
            "question": q_text,
            "marks": marks,
            "answer": answer.strip(),
            "word_count": word_count
        }
