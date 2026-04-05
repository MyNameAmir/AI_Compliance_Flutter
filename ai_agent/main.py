from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from typing import List

from test_full_pipeline import (
    read_pdf_text,
    normalize_text,
    get_or_create_vector_store,
    retrieve_top_chunks,
    evaluate_incident,
    extract_decision_label,
)

app = FastAPI()

# Allow CORS for Flutter frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file to the server."""
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{upload_file.filename}")
    with open(file_path, "wb") as f:
        f.write(upload_file.file.read())
    return file_path


@app.post("/analyze")
async def analyze_files(policy: UploadFile, incident: UploadFile):
    try:
        # Save uploaded files
        policy_path = save_upload_file(policy)
        incident_path = save_upload_file(incident)

        # Process incident text
        incident_raw = read_pdf_text(incident_path)
        incident_text = normalize_text(incident_raw)

        # Process policy and retrieve chunks
        vs_id = get_or_create_vector_store(policy_path)
        top_chunks = retrieve_top_chunks(vs_id, incident_text, top_k=10)

        # Evaluate incident
        violation_result = evaluate_incident(top_chunks, incident_text)
        decision_label = extract_decision_label(violation_result)

        # Prepare response
        response = {
            "decision": decision_label,
            "top_chunks": [{"score": score, "chunk": chunk} for score, chunk in top_chunks],
            "report": violation_result,
        }

        return JSONResponse(content=response)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)