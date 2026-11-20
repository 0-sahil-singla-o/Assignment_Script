"""
FastAPI Backend Server for AI Academic Assignment Studio.
Exposes clean RESTful & Server-Sent Events (SSE) streaming endpoints.
"""
import os
import sys
import json
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

# Ensure parent directory is in sys.path to access modules/
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")

from modules.config import UPLOADS_DIR, OUTPUT_DIR
from modules.question_scanner import (
    extract_raw_text,
    scan_questions_with_groq,
    scan_questions_with_gemini,
    get_active_groq_models,
    is_meaningful_question_text
)
from modules.instruction_analyzer import analyze_instructions_with_gemini, DEFAULT_PDF_SPECS
from modules.instruction_rag import InstructionRAGEngine
from modules.gemini_writer import GeminiAssignmentWriter
from modules.pdf_compiler import compile_final_pdf
from backend.validators import validate_metadata

app = FastAPI(
    title="AI Academic Assignment Studio API",
    description="Backend API for high-speed question scanning, instruction analysis, and ReportLab compilation.",
    version="2.0.0"
)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- SCHEMAS -----------------
class KeyConfig(BaseModel):
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

class QuestionItem(BaseModel):
    number: Any = 1
    text: str
    marks: Any = 10

class GenerateRequest(BaseModel):
    metadata: Dict[str, Any]
    questions: List[Dict[str, Any]]
    layout_specs: Optional[Dict[str, Any]] = None
    pdf_layout_specs: Optional[Dict[str, Any]] = None
    content_guidelines: Optional[str] = ""
    content_writing_guidelines: Optional[str] = ""

# ----------------- ROUTES -----------------
@app.get("/api/health")
def health_check():
    """Returns API health status, configured credentials, and active Groq models."""
    load_dotenv(BASE_DIR / ".env", override=True)
    groq_key = os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    groq_models = ["llama-3.3-70b-versatile"]
    if groq_key:
        try:
            groq_models = get_active_groq_models(groq_key)
        except Exception:
            pass

    return {
        "status": "healthy",
        "has_groq_key": bool(groq_key and len(groq_key) > 5),
        "has_gemini_key": bool(gemini_key and len(gemini_key) > 5),
        "groq_models": groq_models
    }


@app.post("/api/config/keys")
def update_keys(config: KeyConfig):
    """Updates API keys in local .env file."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        env_file.touch()

    if config.groq_api_key is not None:
        set_key(str(env_file), "GROQ_API_KEY", config.groq_api_key.strip())
        os.environ["GROQ_API_KEY"] = config.groq_api_key.strip()

    if config.gemini_api_key is not None:
        set_key(str(env_file), "GEMINI_API_KEY", config.gemini_api_key.strip())
        os.environ["GEMINI_API_KEY"] = config.gemini_api_key.strip()

    return {"status": "success", "message": "Credentials successfully updated"}


@app.post("/api/validate/metadata")
def validate_metadata_endpoint(metadata: Dict[str, Any]):
    """Validates course and student metadata using shared validation rules."""
    is_valid, errors, first_error = validate_metadata(metadata)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail={"errors": errors, "message": first_error, "isValid": False}
        )
    return {"status": "success", "isValid": True, "message": "Academic metadata verified"}


@app.post("/api/scan")
async def scan_questions(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None)
):
    """Scans questions using Groq Cloud API with automatic Gemini fallback, with robust validation."""
    load_dotenv(BASE_DIR / ".env", override=True)
    groq_key = os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    target_field = "file" if (file and file.filename) else "rawText"
    text_to_scan = raw_text or ""

    if file and file.filename:
        save_path = UPLOADS_DIR / file.filename
        try:
            content = await file.read()
            with open(save_path, "wb") as f:
                f.write(content)
            text_to_scan = extract_raw_text(save_path)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "errors": {"file": f"Failed to read uploaded file: {str(e)}"},
                    "message": f"Failed to read uploaded file: {str(e)}",
                    "field": "file",
                    "isValid": False
                }
            )

        if not text_to_scan or not text_to_scan.strip():
            raise HTTPException(
                status_code=422,
                detail={
                    "errors": {"file": "Could not extract readable text from uploaded file. Please ensure it is not scanned as an image or password-protected."},
                    "message": "Could not extract readable text from uploaded file. Please ensure it is not scanned as an image or password-protected.",
                    "field": "file",
                    "isValid": False
                }
            )
    else:
        # Validate pasted raw text
        if not text_to_scan or not text_to_scan.strip():
            raise HTTPException(
                status_code=422,
                detail={
                    "errors": {"rawText": "Please paste question paper text or upload a PDF document."},
                    "message": "Please paste question paper text or upload a PDF document.",
                    "field": "rawText",
                    "isValid": False
                }
            )

        is_valid, validation_msg = is_meaningful_question_text(text_to_scan)
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "errors": {"rawText": validation_msg},
                    "message": validation_msg,
                    "field": "rawText",
                    "isValid": False
                }
            )

    if not groq_key and not gemini_key:
        raise HTTPException(
            status_code=500,
            detail={
                "errors": {target_field: "AI API credentials missing. Please configure your Groq or Gemini API key in settings or .env."},
                "message": "AI API credentials missing. Please configure your Groq or Gemini API key in settings or .env.",
                "field": target_field,
                "isValid": False
            }
        )

    scanned = []
    groq_err = None
    gemini_err = None

    # 1. Try Groq LPU first if configured
    if groq_key:
        try:
            scanned = await asyncio.to_thread(
                scan_questions_with_groq,
                text_to_scan,
                groq_api_key=groq_key,
                model_name=model_name
            )
        except Exception as e:
            groq_err = str(e)
            print(f"Notice: Groq scan error: {e}")

    # 2. Resilient fallback to Gemini if Groq returned empty or encountered error
    if not scanned and gemini_key:
        try:
            scanned = await asyncio.to_thread(
                scan_questions_with_gemini,
                text_to_scan,
                gemini_api_key=gemini_key
            )
        except Exception as e:
            gemini_err = str(e)
            print(f"Notice: Gemini fallback scan error: {e}")

    if not scanned:
        # Construct helpful message based on API failure vs empty extraction
        if groq_err and gemini_err:
            msg = f"API connection failure during question scan. (Groq: {groq_err}; Gemini: {gemini_err})"
        elif groq_err and not gemini_key:
            msg = f"API error while scanning questions: {groq_err}"
        else:
            msg = "No valid academic questions could be identified in the provided content. Please verify your question paper or add questions manually."

        raise HTTPException(
            status_code=422,
            detail={
                "errors": {target_field: msg},
                "message": msg,
                "field": target_field,
                "isValid": False
            }
        )

    return {"status": "success", "questions": scanned, "count": len(scanned)}


@app.post("/api/analyze-instructions")
async def analyze_instructions(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    """Analyzes instructions using Gemini and splits physical PDF specs from writing guidelines."""
    load_dotenv(BASE_DIR / ".env", override=True)
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is not configured. Please add it in settings.")

    text_to_analyze = raw_text or ""
    if file and file.filename:
        save_path = UPLOADS_DIR / file.filename
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        text_to_analyze += "\n\n" + extract_raw_text(save_path)

    if not text_to_analyze.strip():
        return {
            "status": "success",
            "pdf_layout_specs": DEFAULT_PDF_SPECS.copy(),
            "layout_specs": DEFAULT_PDF_SPECS.copy(),
            "content_guidelines": "Standard university academic guidelines active: strictly 300-350 words for 10-mark questions, 150-200 for 5-mark questions.",
            "content_writing_guidelines": "Standard university academic guidelines active: strictly 300-350 words for 10-mark questions, 150-200 for 5-mark questions."
        }

    try:
        specs, guidelines = await asyncio.to_thread(
            analyze_instructions_with_gemini,
            text_to_analyze,
            gemini_key
        )
        return {
            "status": "success",
            "pdf_layout_specs": specs,
            "layout_specs": specs,
            "content_guidelines": guidelines,
            "content_writing_guidelines": guidelines
        }
    except Exception as e:
        print(f"Instruction analysis fallback on error: {e}")
        return {
            "status": "success",
            "pdf_layout_specs": DEFAULT_PDF_SPECS.copy(),
            "layout_specs": DEFAULT_PDF_SPECS.copy(),
            "content_guidelines": text_to_analyze or "Standard university academic guidelines active: strictly 300-350 words for 10-mark questions.",
            "content_writing_guidelines": text_to_analyze or "Standard university academic guidelines active: strictly 300-350 words for 10-mark questions."
        }


@app.post("/api/generate-stream")
async def generate_assignment_stream(request: GenerateRequest):
    """
    Streams live answer drafting progress via Server-Sent Events (SSE),
    then compiles the final university PDF.
    """
    load_dotenv(BASE_DIR / ".env", override=True)
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is not configured.")

    async def event_generator():
        writer = GeminiAssignmentWriter(api_key=gemini_key)
        rag = InstructionRAGEngine()
        answers = []
        total_q = len(request.questions)
        active_guidelines = request.content_guidelines or request.content_writing_guidelines or ""
        active_specs = request.layout_specs or request.pdf_layout_specs or {}

        yield f"data: {json.dumps({'type': 'start', 'total': total_q})}\n\n"
        yield f"data: {json.dumps({'type': 'progress', 'progress': 5, 'message': 'Initiating generation session...'})}\n\n"

        # Validate metadata against shared academic rules before generation
        is_meta_valid, meta_errors, meta_err_msg = validate_metadata(request.metadata)
        if not is_meta_valid:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Validation Error: {meta_err_msg}'})}\n\n"
            return

        for idx, q_obj in enumerate(request.questions):
            q_dict = q_obj if isinstance(q_obj, dict) else q_obj.model_dump()
            q_num_raw = q_dict.get("number", idx + 1)
            q_label = f"Q{q_num_raw}" if not str(q_num_raw).lower().startswith("q") else str(q_num_raw)
            
            yield f"data: {json.dumps({'type': 'progress', 'progress': int(5 + (idx / total_q) * 80), 'message': f'Drafting answer for {q_label}...'})}\n\n"

            # Run drafting synchronously in thread to avoid blocking event loop
            try:
                loop = asyncio.get_event_loop()
                ans_data = await loop.run_in_executor(
                    None,
                    writer.draft_answer,
                    q_dict,
                    active_guidelines,
                    rag
                )
                answers.append(ans_data)

                # Check if word count matches target bounds (300-350 for 10M, 150-200 for 5M)
                marks = int(q_dict.get("marks", 5) or 5)
                is_in_bounds = True
                if marks >= 10 and (ans_data["word_count"] < 290 or ans_data["word_count"] > 360):
                    is_in_bounds = False
                elif marks == 5 and (ans_data["word_count"] < 140 or ans_data["word_count"] > 210):
                    is_in_bounds = False

                done_payload = {
                    'type': 'question_drafted',
                    'index': idx,
                    'number': q_label,
                    'marks': marks,
                    'word_count': ans_data['word_count'],
                    'in_bounds': is_in_bounds,
                    'answer': ans_data['answer'],
                    'answer_excerpt': ans_data['answer'][:200]
                }
                yield f"data: {json.dumps(done_payload)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error drafting {q_label}: {str(e)}'})}\n\n"
                return

        # Compile PDF
        yield f"data: {json.dumps({'type': 'compiling', 'progress': 90, 'message': 'Compiling official ReportLab submission PDF...'})}\n\n"

        try:
            course_name = request.metadata.get("course_code_name", "Assignment").split("-")[0].strip().replace(" ", "_")
            output_filename = f"Assignment_{course_name}_Submission.pdf"
            output_pdf_path = OUTPUT_DIR / output_filename

            compile_final_pdf(
                output_path=output_pdf_path,
                metadata=request.metadata,
                answers=answers,
                layout_specs=active_specs
            )

            file_size_bytes = output_pdf_path.stat().st_size
            file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

            page_count = 1
            try:
                reader = pypdf.PdfReader(str(output_pdf_path))
                page_count = len(reader.pages)
            except Exception:
                pass

            completed_payload = {
                'type': 'completed',
                'filename': output_filename,
                'file_size_mb': file_size_mb,
                'size_mb': file_size_mb,
                'page_count': page_count,
                'download_url': f'/api/download/{output_filename}'
            }
            yield f"data: {json.dumps(completed_payload)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'PDF Compilation error: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/download/{filename}")
def download_pdf(filename: str):
    """Downloads or previews the compiled PDF."""
    pdf_path = OUTPUT_DIR / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Requested PDF file not found.")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
