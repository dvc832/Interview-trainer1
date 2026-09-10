"""
Interview Trainer Tools - IBM watsonx Granite-4 powered adaptive interview tools.
Each tool is self-contained as required by the watsonx Orchestrate ADK.
"""
import json
import requests
from typing import Optional, List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
WX_API_URL = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"
WX_MODEL_ID = "ibm/granite-4-h-small"
WX_PROJECT_ID = "66d8b6f7-7a05-43a6-aec9-6c328b542c18"
WX_API_KEY = "aMYDMxkuJKr-0Jja5e6gafaWjbPbzoNwK9WiYY9FPJcq"

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


def _get_iam_token() -> str:
    """Fetch a short-lived IAM bearer token using the API key."""
    resp = requests.post(
        IAM_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={WX_API_KEY}",
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _call_wx(prompt: str, max_tokens: int = 800) -> str:
    """Call the IBM watsonx chat endpoint and return the generated text."""
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
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────

class ParseResumeInput(BaseModel):
    resume_text: str = Field(..., description="Full text content of the candidate's resume")
    job_role: str = Field(..., description="Target job role / title the candidate is applying for")


class ParseResumeOutput(BaseModel):
    summary: str = Field(description="Concise candidate profile summary")
    key_skills: str = Field(description="Comma-separated list of identified key skills")
    experience_level: str = Field(description="Inferred seniority: Junior / Mid / Senior")
    suggested_topics: str = Field(description="Comma-separated interview topic areas")


class GenerateQuestionInput(BaseModel):
    job_role: str = Field(..., description="Job role being interviewed for")
    topic: str = Field(..., description="Interview topic (e.g. 'Python', 'System Design')")
    difficulty: str = Field(default="medium", description="Question difficulty: easy / medium / hard")
    previous_questions: Optional[str] = Field(default="", description="Newline-separated list of already-asked questions to avoid repetition")


class GenerateQuestionOutput(BaseModel):
    question: str = Field(description="The interview question text")
    topic: str = Field(description="Topic category of the question")
    difficulty: str = Field(description="Difficulty level of the question")
    hints: str = Field(description="Key points a strong answer should cover")


class EvaluateAnswerInput(BaseModel):
    question: str = Field(..., description="The interview question that was asked")
    answer: str = Field(..., description="The candidate's answer")
    job_role: str = Field(..., description="Target job role for context")
    hints: Optional[str] = Field(default="", description="Key points the answer should cover")


class EvaluateAnswerOutput(BaseModel):
    score: int = Field(description="Score out of 10")
    strengths: str = Field(description="What the candidate did well")
    improvements: str = Field(description="Areas to improve")
    model_answer: str = Field(description="A concise model/reference answer")
    follow_up_question: str = Field(description="A natural follow-up question to probe deeper")


class GenerateReportInput(BaseModel):
    candidate_name: str = Field(default="Candidate", description="Name of the candidate")
    job_role: str = Field(..., description="Target job role")
    qa_history: str = Field(..., description="JSON string: list of {question, answer, score, strengths, improvements}")
    overall_feedback: Optional[str] = Field(default="", description="Any additional overall observations")


class GenerateReportOutput(BaseModel):
    report_markdown: str = Field(description="Full performance report in Markdown format")
    overall_score: int = Field(description="Average score out of 10")
    recommendation: str = Field(description="Hire / Consider / Not Ready")


# ──────────────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────────────

@tool(permission=ToolPermission.READ_ONLY)
def parse_resume_and_role(input: ParseResumeInput) -> ParseResumeOutput:
    """
    Analyse a candidate's resume against a target job role.

    Extracts key skills, estimates seniority, and recommends interview topics
    so subsequent question generation can be personalised.

    Args:
        input (ParseResumeInput): Resume text and target job role.

    Returns:
        ParseResumeOutput: Profile summary, skills, experience level, and interview topics.
    """
    prompt = f"""You are an expert technical recruiter. Analyse the following resume for the role of '{input.job_role}'.

RESUME:
{input.resume_text}

Respond in the following JSON format only (no extra text):
{{
  "summary": "<2-3 sentence candidate summary>",
  "key_skills": "<comma-separated skills>",
  "experience_level": "<Junior|Mid|Senior>",
  "suggested_topics": "<comma-separated interview topics relevant to the role>"
}}"""

    raw = _call_wx(prompt, max_tokens=400)
    # Extract JSON from response
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    return ParseResumeOutput(**data)


@tool(permission=ToolPermission.READ_ONLY)
def generate_interview_question(input: GenerateQuestionInput) -> GenerateQuestionOutput:
    """
    Generate an adaptive interview question for a given role, topic, and difficulty.

    Avoids repeating previously asked questions to ensure a fresh, varied session.

    Args:
        input (GenerateQuestionInput): Job role, topic, difficulty, and previous questions.

    Returns:
        GenerateQuestionOutput: A question, its topic, difficulty, and scoring hints.
    """
    avoid_block = ""
    if input.previous_questions:
        avoid_block = f"\nDo NOT repeat any of these already-asked questions:\n{input.previous_questions}\n"

    prompt = f"""You are an experienced technical interviewer for '{input.job_role}' positions.
Generate one {input.difficulty}-difficulty interview question on the topic: '{input.topic}'.
{avoid_block}
Respond in the following JSON format only (no extra text):
{{
  "question": "<the interview question>",
  "topic": "{input.topic}",
  "difficulty": "{input.difficulty}",
  "hints": "<key points a strong answer must cover>"
}}"""

    raw = _call_wx(prompt, max_tokens=300)
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    return GenerateQuestionOutput(**data)


@tool(permission=ToolPermission.READ_ONLY)
def evaluate_candidate_answer(input: EvaluateAnswerInput) -> EvaluateAnswerOutput:
    """
    Evaluate a candidate's answer to an interview question and provide detailed feedback.

    Scores the answer, highlights strengths and areas for improvement, supplies a
    model answer, and generates a contextual follow-up question.

    Args:
        input (EvaluateAnswerInput): The question, the candidate's answer, job role, and hints.

    Returns:
        EvaluateAnswerOutput: Score, strengths, improvements, model answer, follow-up question.
    """
    hints_block = f"\nExpected key points: {input.hints}" if input.hints else ""

    prompt = f"""You are a senior technical interviewer evaluating an answer for the role of '{input.job_role}'.

QUESTION: {input.question}{hints_block}

CANDIDATE'S ANSWER: {input.answer}

Score the answer out of 10 and provide constructive feedback.
Respond in the following JSON format only (no extra text):
{{
  "score": <integer 0-10>,
  "strengths": "<what the candidate did well>",
  "improvements": "<specific areas to improve>",
  "model_answer": "<a concise ideal answer in 3-5 sentences>",
  "follow_up_question": "<a relevant follow-up question to probe further>"
}}"""

    raw = _call_wx(prompt, max_tokens=500)
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    data["score"] = int(data["score"])
    return EvaluateAnswerOutput(**data)


@tool(permission=ToolPermission.READ_ONLY)
def generate_performance_report(input: GenerateReportInput) -> GenerateReportOutput:
    """
    Generate a comprehensive post-interview performance report.

    Compiles all Q&A history, computes an overall score, and produces a structured
    Markdown report with a hiring recommendation.

    Args:
        input (GenerateReportInput): Candidate name, job role, full Q&A history JSON, and optional feedback.

    Returns:
        GenerateReportOutput: Markdown report, overall score, and hiring recommendation.
    """
    prompt = f"""You are an experienced hiring manager writing a post-interview performance report.

CANDIDATE: {input.candidate_name}
ROLE: {input.job_role}
INTERVIEW Q&A HISTORY (JSON):
{input.qa_history}

{('ADDITIONAL OBSERVATIONS: ' + input.overall_feedback) if input.overall_feedback else ''}

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

    raw = _call_wx(prompt, max_tokens=1200)
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    data["overall_score"] = int(data["overall_score"])
    return GenerateReportOutput(**data)
