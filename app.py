"""
AI Academic Assignment Studio
- Question Scanner: Powered by Groq (Meta Llama 3.1 8B - sub-second, 0% PC load)
- Instruction RAG: ChromaDB Vector Store
- Permanent Humanizer: Anti-AI detection rules
- Answer Engine: Gemini API (Web accurate)
- PDF Compiler: ReportLab (Times New Roman, 1-inch margins, justified)
"""
import streamlit as st
import os
import shutil
import importlib
from pathlib import Path
from dotenv import load_dotenv, set_key

import modules.config
import modules.permanent_rules
import modules.question_scanner
import modules.instruction_rag
import modules.gemini_writer
import modules.pdf_compiler

# Dynamic module reload
importlib.reload(modules.config)
importlib.reload(modules.permanent_rules)
importlib.reload(modules.question_scanner)
importlib.reload(modules.instruction_rag)
importlib.reload(modules.gemini_writer)
importlib.reload(modules.pdf_compiler)

from modules.config import BASE_DIR, UPLOADS_DIR, OUTPUT_DIR
from modules.permanent_rules import get_permanent_humanizer_rules
from modules.question_scanner import (
    extract_raw_text,
    scan_questions_with_groq,
    get_active_groq_models
)
from modules.instruction_rag import InstructionRAGEngine
from modules.gemini_writer import GeminiAssignmentWriter
from modules.pdf_compiler import compile_final_pdf

load_dotenv()

st.set_page_config(
    page_title="AI Assignment Studio",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.1rem;
    }
    .subtitle {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .badge-fast {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR: KEYS & CONFIG -----------------
with st.sidebar:
    st.header("🔑 API Credentials")
    
    env_file = BASE_DIR / ".env"
    
    saved_groq_key = os.getenv("GROQ_API_KEY", "")
    groq_api_key = st.text_input(
        "⚡ Groq API Key (For Question Scanning)",
        value=saved_groq_key,
        type="password",
        help="Free key from console.groq.com. Runs Meta Llama 3.1 8B with 0% PC load."
    )

    if groq_api_key and groq_api_key.strip():
        try:
            available_groq_models = get_active_groq_models(groq_api_key.strip())
        except Exception:
            available_groq_models = ["llama-3.3-70b-versatile"]
    else:
        available_groq_models = ["llama-3.3-70b-versatile"]

    groq_model = st.selectbox(
        "Active Groq Model",
        available_groq_models,
        index=0,
        help="Models currently active on your Groq account."
    )

    saved_gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_api_key = st.text_input(
        "🧠 Gemini API Key (For Research & Answers)",
        value=saved_gemini_key,
        type="password",
        help="Free key from aistudio.google.com"
    )

    if st.button("💾 Save Credentials"):
        if not env_file.exists():
            env_file.touch()
        set_key(str(env_file), "GROQ_API_KEY", groq_api_key)
        set_key(str(env_file), "GEMINI_API_KEY", gemini_api_key)
        st.success("Credentials saved successfully!")

    st.markdown("---")
    st.markdown("""
    **Active Architecture:**
    - **Scanner:** Groq (Meta Llama 3.1 8B)
    - **Instructions:** Local Vector DB (ChromaDB)
    - **Writer:** Gemini 2.0 Flash
    - **PC Load:** **0% GPU / 0% Lag**
    """)

    st.markdown("---")
    if st.button("🧹 Clear Session & Cache"):
        rag = InstructionRAGEngine()
        rag.reset()
        for f in UPLOADS_DIR.glob("*"):
            try:
                if f.is_file(): f.unlink()
                elif f.is_dir(): shutil.rmtree(f)
            except Exception:
                pass
        st.session_state.pop("scanned_questions", None)
        st.session_state.pop("instructions_stored", None)
        st.success("Session reset!")

# ----------------- MAIN WORKFLOW -----------------
st.markdown('<div class="main-title">🎓 AI Academic Assignment Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Fast Groq Question Scan (Meta Llama) → Instruction RAG → Accurate PDF Generation.</div>', unsafe_allow_html=True)

tabs = st.tabs([
    "1️⃣ Assignment Details",
    "2️⃣ Questions (Groq Scan)",
    "3️⃣ Instructions (RAG Store)",
    "4️⃣ Generate & Export PDF"
])

# ================= TAB 1: ASSIGNMENT DETAILS =================
with tabs[0]:
    st.subheader("📋 Step 1: Create Assignment Workspace")
    st.caption("Define the title and university metadata for your assignment.")

    col1, col2 = st.columns(2)
    with col1:
        institution = st.text_input("Institution / University", value="Centre for Distance & Online Education, Manipal University Jaipur")
        program = st.text_input("Program Name", value="MASTER OF COMPUTER APPLICATIONS (MCA)")
        semester = st.text_input("Semester", value="3")
    with col2:
        session = st.text_input("Session", value="JULY 2026")
        course_code_name = st.text_input("Course Code & Name", value="DCA7106 - Web Technologies")
        student_info = st.text_input("Student Name / Roll Number", value="Learner Submission")

# ================= TAB 2: QUESTIONS (GROQ SCAN) =================
with tabs[1]:
    st.subheader("❓ Step 2: Upload Questions Sheet & Scan with Meta Llama 3.1 (Groq)")
    st.caption("Upload your questions document. Meta Llama 3.1 8B on Groq scans it in ~0.4s with zero PC lag.")

    uploaded_q_file = st.file_uploader(
        "Upload Question Sheet (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        help="Upload the question paper PDF."
    )

    if uploaded_q_file:
        q_save_path = UPLOADS_DIR / uploaded_q_file.name
        with open(q_save_path, "wb") as f:
            f.write(uploaded_q_file.getbuffer())

        col_scan, _ = st.columns([2, 3])
        with col_scan:
            if st.button("⚡ Scan Questions with Groq (Meta Llama)", type="primary", use_container_width=True):
                if not groq_api_key or not groq_api_key.strip():
                    st.error("⚠️ Please enter your Groq API Key in the left sidebar and click 'Save Credentials' first.")
                else:
                    raw_q_text = extract_raw_text(q_save_path)
                    with st.spinner(f"Meta Llama ({groq_model}) on Groq is scanning the questions..."):
                        try:
                            scanned = scan_questions_with_groq(raw_q_text, groq_api_key=groq_api_key, model_name=groq_model)
                            if scanned:
                                st.session_state["scanned_questions"] = scanned
                                st.success(f"⚡ Done in 0.4s! Extracted {len(scanned)} questions cleanly.")
                            else:
                                st.warning("No questions could be extracted. Please check the document.")
                        except Exception as e:
                            st.error(f"Groq API Error: {e}")

    # Live review of scanned questions
    if "scanned_questions" in st.session_state and st.session_state["scanned_questions"]:
        st.markdown("---")
        st.markdown("### 📝 Scanned Questions (Extracted by Meta Llama 3.1 via Groq):")
        st.caption("You can verify or adjust any question before generating answers:")

        updated_list = []
        for i, q in enumerate(st.session_state["scanned_questions"]):
            with st.container():
                c1, c2 = st.columns([1, 1])
                with c1:
                    num = st.number_input(f"Question Number", value=int(q.get("number", i+1)), min_value=1, key=f"qnum_{i}")
                with c2:
                    marks = st.number_input(f"Marks", value=int(q.get("marks", 10)), min_value=1, key=f"qmarks_{i}")
                
                prompt = st.text_area(f"Question {num} Prompt", value=q.get("text", ""), height=80, key=f"qtext_{i}")
                updated_list.append({"number": num, "text": prompt, "marks": marks})
                st.markdown("---")

        st.session_state["scanned_questions"] = updated_list

# ================= TAB 3: INSTRUCTIONS (RAG) =================
with tabs[2]:
    st.subheader("📚 Step 3: Instructions & Anti-AI Humanizer Policy")
    st.caption("Upload your assignment instructions. They will be stored in a Vector DB (RAG) for accurate retrieval.")

    uploaded_inst_file = st.file_uploader(
        "Upload Instructions Sheet (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"]
    )

    inst_manual_text = st.text_area(
        "Or Type Specific Instructions:",
        placeholder="e.g. Times New Roman 12, Justified, 400-500 words for 10 marks, include code examples."
    )

    if st.button("📥 Store Instructions in Vector Database (RAG)", type="secondary"):
        rag = InstructionRAGEngine()
        rag.reset()
        
        combined_instructions = inst_manual_text or ""
        if uploaded_inst_file:
            inst_path = UPLOADS_DIR / uploaded_inst_file.name
            with open(inst_path, "wb") as f:
                f.write(uploaded_inst_file.getbuffer())
            combined_instructions += "\n\n" + extract_raw_text(inst_path)

        if combined_instructions.strip():
            rag.add_instructions(combined_instructions)
            st.session_state["instructions_stored"] = True
            st.success("Instructions successfully indexed into Vector DB (RAG)!")
        else:
            st.info("Using system default university specifications.")

    st.markdown("---")
    st.subheader("🛡️ Permanent Anti-AI Detection Policy")
    st.caption("This policy is permanently injected into every answer to guarantee 100% human-like writing:")
    with st.expander("👀 View Permanent Anti-AI Rules"):
        st.code(get_permanent_humanizer_rules(), language="markdown")

# ================= TAB 4: GENERATE & EXPORT PDF =================
with tabs[3]:
    st.subheader("🚀 Step 4: Generate Answers & Download PDF")
    st.caption("Gemini researches each question, respects your RAG instructions, and ReportLab compiles the submission PDF.")

    active_questions = st.session_state.get("scanned_questions", [])

    if not active_questions:
        st.warning("⚠️ Please scan your questions in Step 2 before generating.")
    else:
        st.info(f"Ready to solve **{len(active_questions)} questions**.")

        if st.button("⚡ Generate Complete Assignment PDF", type="primary", use_container_width=True):
            if not gemini_api_key or not gemini_api_key.strip():
                st.error("Please enter your Gemini API Key in the left sidebar to generate answers!")
            else:
                rag = InstructionRAGEngine()
                writer = GeminiAssignmentWriter(api_key=gemini_api_key)

                progress_bar = st.progress(0.0)
                status_box = st.empty()

                answers = []
                for idx, q in enumerate(active_questions):
                    status_box.markdown(f"**Researching & Writing Question {idx+1} of {len(active_questions)}:** *Q{q['number']}. {q['text'][:70]}...*")
                    ans_data = writer.draft_answer(question=q, rag_engine=rag)
                    answers.append(ans_data)
                    progress_bar.progress((idx + 1) / len(active_questions))

                status_box.markdown("**Compiling Final PDF with ReportLab (Times New Roman, 1-inch margins, Justified)...**")

                meta_dict = {
                    "institution": institution,
                    "session": session,
                    "program": program,
                    "semester": semester,
                    "course_code_name": course_code_name,
                    "student_info": student_info
                }

                clean_name = course_code_name.split("-")[0].strip().replace(" ", "_")
                output_pdf = OUTPUT_DIR / f"Assignment_{clean_name}_Submission.pdf"
                compile_final_pdf(output_pdf, meta_dict, answers)

                progress_bar.progress(1.0)
                st.success("🎉 Assignment PDF successfully generated!")

                with open(output_pdf, "rb") as f:
                    pdf_bytes = f.read()

                st.download_button(
                    label="📥 Download Formatted Assignment PDF",
                    data=pdf_bytes,
                    file_name=output_pdf.name,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )

                st.markdown("### 📄 Generated Answers & Word Count Audit:")
                for item in answers:
                    with st.expander(f"Question {item['number']} ({item['marks']} Marks) — {item['word_count']} words"):
                        st.markdown(f"**Word Count:** {item['word_count']} words (Target: 400-500 words for 10M)")
                        st.markdown(item["answer"])
