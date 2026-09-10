"""
Performance Report Flow — compiles the full Q&A history into a comprehensive
Markdown report with scores and a hiring recommendation.
"""
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from interview_trainer.tools.interview_tools import generate_performance_report


class ReportFlowInput(BaseModel):
    candidate_name: str = Field(default="Candidate", description="Candidate's name")
    job_role: str = Field(..., description="Target job role")
    qa_history: str = Field(
        ...,
        description=(
            "JSON string — list of objects each with keys: "
            "question, answer, score, strengths, improvements"
        ),
    )


class ReportFlowOutput(BaseModel):
    report_markdown: str = Field(description="Full Markdown performance report")
    overall_score: int = Field(description="Average score out of 10")
    recommendation: str = Field(description="Hire / Consider / Not Ready")


@flow(
    name="performance_report_flow",
    display_name="Performance Report Flow",
    description=(
        "Generates a comprehensive post-interview performance report with scores, "
        "skill assessments, and a hiring recommendation using IBM watsonx Granite."
    ),
    input_schema=ReportFlowInput,
)
def build_performance_report_flow(aflow: Flow) -> Flow:
    """
    CRITICAL: Flow function signature is build_<name>(aflow: Flow) -> Flow
    Single node: calls generate_performance_report tool with full Q&A history.
    """
    report_node = aflow.tool(generate_performance_report)
    aflow.sequence(START, report_node, END)
    return aflow
