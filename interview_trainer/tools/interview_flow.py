"""
Interview Session Flow — orchestrates resume parsing → adaptive question generation
→ answer evaluation in a single conversational session.
"""
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from interview_trainer.tools.interview_tools import (
    parse_resume_and_role,
    generate_interview_question,
    evaluate_candidate_answer,
)


class InterviewSessionInput(BaseModel):
    resume_text: str = Field(..., description="Full text of the candidate's resume")
    job_role: str = Field(..., description="Target job role the candidate is interviewing for")
    candidate_name: str = Field(default="Candidate", description="Candidate's name")
    num_questions: int = Field(default=5, description="Number of interview questions (3-10)")


class InterviewSessionOutput(BaseModel):
    session_summary: str = Field(description="JSON string containing all Q&A pairs with scores")
    candidate_name: str = Field(description="Candidate name for report generation")
    job_role: str = Field(description="Job role that was interviewed for")


@flow(
    name="interview_session_flow",
    display_name="Interview Session Flow",
    description=(
        "Conducts a full adaptive mock interview: parses resume, generates targeted "
        "questions, and evaluates each answer using IBM watsonx Granite."
    ),
    input_schema=InterviewSessionInput,
)
def build_interview_session_flow(aflow: Flow) -> Flow:
    """
    CRITICAL: Flow function signature is build_<name>(aflow: Flow) -> Flow
    Nodes:
      1. parse_resume  — extracts skills & topics from resume
      2. prompt_node   — LLM plans question order & difficulty progression
      3. generate_q    — generates each question
      4. evaluate_a    — evaluates each answer and collects feedback
    """
    # Node 1: Parse resume to get profile
    parse_node = aflow.tool(parse_resume_and_role)

    # Node 2: Generate the first/next interview question
    question_node = aflow.tool(generate_interview_question)

    # Node 3: Evaluate the candidate's answer
    evaluate_node = aflow.tool(evaluate_candidate_answer)

    # Sequence: parse → generate question → evaluate answer
    aflow.sequence(START, parse_node, question_node, evaluate_node, END)
    return aflow
