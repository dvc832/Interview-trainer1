"""
backend/app.py — Flask REST API backend for the Interview Trainer web UI.
Bridges the React frontend to IBM watsonx Granite for interview operations.

Run:
    pip install flask flask-cors requests
    python interview_trainer/backend/app.py

Endpoints:
    POST /api/parse_resume        — parse resume + job role
    POST /api/generate_question   — generate next question
    POST /api/evaluate_answer     — evaluate a candidate answer
    POST /api/generate_report     — generate final performance report
    GET  /api/health              — health check
"""

import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow requests from the frontend (same origin or local dev)

# ──────────────────────────────────────────────────────────────────────────────
# IBM watsonx configuration
# ──────────────────────────────────────────────────────────────────────────────
WX_API_URL = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"
WX_MODEL_ID = "ibm/granite-4-h-small"
WX_PROJECT_ID = "66d8b6f7-7a05-43a6-aec9-6c328b542c18"
WX_API_KEY = "aMYDMxkuJKr-0Jja5e6gafaWjbPbzoNwK9WiYY9FPJcq"
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


def _get_iam_token() -> str:
    resp = requests.post(
        IAM_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={WX_API_KEY}",
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _call_wx(prompt: str, max_tokens: int = 800) -> str:
    token = _get_iam_token()
    payload = {
        "model_id": WX_MODEL_ID,
        "project_id": WX_PROJECT_ID,
        "messages": [{"role": "user", "content": prompt}],
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": 0.7,
        },
    }
    resp = requests.post(
        WX_API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _extract_json(raw: str) -> dict:
    """Safely extract the first JSON object from a raw string."""
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in response: {raw[:200]}")
    return json.loads(raw[start:end])


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": WX_MODEL_ID})


@app.route("/api/parse_resume", methods=["POST"])
def parse_resume():
    """
    Body: { "resume_text": str, "job_role": str }
    Returns: { summary, key_skills, experience_level, suggested_topics }
    """
    body = request.get_json()
    resume_text = body.get("resume_text", "")
    job_role = body.get("job_role", "")

    if not resume_text or not job_role:
        return jsonify({"error": "resume_text and job_role are required"}), 400

    prompt = f"""You are an expert technical recruiter. Analyse the following resume for the role of '{job_role}'.

RESUME:
{resume_text}

Respond in the following JSON format only (no extra text):
{{
  "summary": "<2-3 sentence candidate summary>",
  "key_skills": "<comma-separated skills>",
  "experience_level": "<Junior|Mid|Senior>",
  "suggested_topics": "<comma-separated interview topics relevant to the role>"
}}"""

    try:
        raw = _call_wx(prompt, max_tokens=400)
        data = _extract_json(raw)
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/generate_question", methods=["POST"])
def generate_question():
    """
    Body: { "job_role": str, "topic": str, "difficulty": str, "previous_questions": str }
    Returns: { question, topic, difficulty, hints }
    """
    body = request.get_json()
    job_role = body.get("job_role", "")
    topic = body.get("topic", "General")
    difficulty = body.get("difficulty", "medium")
    previous_questions = body.get("previous_questions", "")

    avoid_block = ""
    if previous_questions:
        avoid_block = f"\nDo NOT repeat any of these already-asked questions:\n{previous_questions}\n"

    prompt = f"""You are an experienced technical interviewer for '{job_role}' positions.
Generate one {difficulty}-difficulty interview question on the topic: '{topic}'.
{avoid_block}
Respond in the following JSON format only (no extra text):
{{
  "question": "<the interview question>",
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "hints": "<key points a strong answer must cover>"
}}"""

    try:
        raw = _call_wx(prompt, max_tokens=300)
        data = _extract_json(raw)
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/evaluate_answer", methods=["POST"])
def evaluate_answer():
    """
    Body: { "question": str, "answer": str, "job_role": str, "hints": str }
    Returns: { score, strengths, improvements, model_answer, follow_up_question }
    """
    body = request.get_json()
    question = body.get("question", "")
    answer = body.get("answer", "")
    job_role = body.get("job_role", "")
    hints = body.get("hints", "")

    if not question or not answer:
        return jsonify({"error": "question and answer are required"}), 400

    hints_block = f"\nExpected key points: {hints}" if hints else ""

    prompt = f"""You are a senior technical interviewer evaluating an answer for the role of '{job_role}'.

QUESTION: {question}{hints_block}

CANDIDATE'S ANSWER: {answer}

Score the answer out of 10 and provide constructive feedback.
Respond in the following JSON format only (no extra text):
{{
  "score": <integer 0-10>,
  "strengths": "<what the candidate did well>",
  "improvements": "<specific areas to improve>",
  "model_answer": "<a concise ideal answer in 3-5 sentences>",
  "follow_up_question": "<a relevant follow-up question to probe further>"
}}"""

    try:
        raw = _call_wx(prompt, max_tokens=500)
        data = _extract_json(raw)
        data["score"] = int(data.get("score", 0))
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/generate_report", methods=["POST"])
def generate_report():
    """
    Body: { "candidate_name": str, "job_role": str, "qa_history": list }
    Returns: { report_markdown, overall_score, recommendation }
    """
    body = request.get_json()
    candidate_name = body.get("candidate_name", "Candidate")
    job_role = body.get("job_role", "")
    qa_history = body.get("qa_history", [])

    if not job_role or not qa_history:
        return jsonify({"error": "job_role and qa_history are required"}), 400

    qa_json = json.dumps(qa_history, indent=2)

    prompt = f"""You are an experienced hiring manager writing a post-interview performance report.

CANDIDATE: {candidate_name}
ROLE: {job_role}
INTERVIEW Q&A HISTORY (JSON):
{qa_json}

Write a comprehensive Markdown performance report covering:
1. Executive Summary
2. Skill Assessment by Topic (table)
3. Strengths
4. Areas for Development
5. Overall Score and Recommendation (Hire / Consider / Not Ready)

Respond in the following JSON format only (no extra text):
{{
  "report_markdown": "<full markdown report>",
  "overall_score": <integer 0-10>,
  "recommendation": "<Hire|Consider|Not Ready>"
}}"""

    try:
        raw = _call_wx(prompt, max_tokens=1200)
        data = _extract_json(raw)
        data["overall_score"] = int(data.get("overall_score", 0))
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    print("Starting Interview Trainer Backend on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
