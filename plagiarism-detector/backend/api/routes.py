"""
Flask API - Single document plagiarism detection against the web
"""

import os, sys, threading, time, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, request, jsonify

from core.text_processor import get_text_stats, extract_sentences
from core.ocr_engine import extract_text_from_image_bytes, is_supported_image
from core.similarity_engine import compute_tfidf_similarity, compute_ngram_overlap
from core.semantic_model import compute_semantic_similarity
from core.web_search import check_plagiarism_online, extract_key_sentences
from core.report_generator import generate_single_doc_report
from core.pdf_extractor import extract_text_from_pdf_bytes

api_blueprint = Blueprint('api', __name__)

# In-memory job store  {job_id: {status, progress, result}}
JOBS = {}


@api_blueprint.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "ok", "version": "2.0.0"})


@api_blueprint.route('/check', methods=['POST'])
def check():
    """
    Submit a document for plagiarism checking.
    Returns a job_id immediately; poll /result/<job_id> for progress.
    Accepts: multipart file (file) OR JSON {text: "..."}
    """
    text, meta = _extract_text(request)

    if not text or len(text.strip()) < 50:
        return jsonify({"error": "Document too short or empty (minimum 50 characters)."}), 400

    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {"status": "running", "progress": "Starting…", "result": None}

    thread = threading.Thread(target=_run_check, args=(job_id, text, meta), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@api_blueprint.route('/result/<job_id>', methods=['GET'])
def result(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@api_blueprint.route('/extract', methods=['POST'])
def extract():
    """Preview extracted text before checking."""
    text, meta = _extract_text(request)
    return jsonify({"text": text[:2000], "stats": get_text_stats(text) if text else {}, "meta": meta})


def _run_check(job_id: str, text: str, meta: dict):
    def progress(msg):
        JOBS[job_id]["progress"] = msg

    try:
        progress("Analysing document structure…")
        stats = get_text_stats(text)
        sentences = extract_key_sentences(text)

        progress("Searching the web for matching content…")
        sources = check_plagiarism_online(text, progress_callback=progress)

        progress("Computing similarity scores…")
        report = generate_single_doc_report(text, stats, sources, meta)

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["result"] = report

    except Exception as e:
        import traceback
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)
        JOBS[job_id]["trace"] = traceback.format_exc()


def _extract_text(req):
    if req.is_json:
        data = req.get_json() or {}
        text = data.get("text", "").strip()
        if text:
            return text, {"source": "text_input", "type": "text"}

    text = req.form.get("text", "").strip()
    if text:
        return text, {"source": "text_input", "type": "text"}

    file = req.files.get("file")
    if file and file.filename:
        file_bytes = file.read()
        filename = file.filename.lower()

        if is_supported_image(filename):
            from core.ocr_engine import extract_text_from_image_bytes
            extracted, ocr_meta = extract_text_from_image_bytes(file_bytes)
            ocr_meta.update({"source": "image_ocr", "filename": file.filename})
            return extracted, ocr_meta

        if filename.endswith('.pdf'):
            extracted, pdf_meta = extract_text_from_pdf_bytes(file_bytes)
            pdf_meta.update({"source": "pdf_text", "filename": file.filename, "size": len(file_bytes)})
            return extracted, pdf_meta

        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")
        return text.strip(), {"source": "text_file", "filename": file.filename, "size": len(file_bytes)}

    return "", {"source": "none"}
