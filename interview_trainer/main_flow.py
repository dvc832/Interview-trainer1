"""
main_flow.py — Programmatic test runner for Interview Trainer flows.
Run from the project root:
    export PYTHONPATH=/path/to/adk/src:/path/to/adk:.
    python3 interview_trainer/main_flow.py
"""
import asyncio
import json
from pathlib import Path

from interview_trainer.tools.interview_flow import build_interview_session_flow
from interview_trainer.tools.report_flow import build_performance_report_flow

GENERATED = Path(__file__).resolve().parent / "generated"
GENERATED.mkdir(exist_ok=True)


async def test_interview_session():
    """Compile and dump the interview session flow spec."""
    print("Compiling interview_session_flow …")
    flow_def = await build_interview_session_flow().compile_deploy()
    flow_def.dump_spec(str(GENERATED / "interview_session_flow.json"))
    print("  → Spec written to generated/interview_session_flow.json")

    sample_resume = (
        "John Doe — Software Engineer\n"
        "5 years Python, Django, REST APIs, PostgreSQL, AWS, Docker, Kubernetes.\n"
        "Led migration of monolith to microservices at TechCorp."
    )
    result = await flow_def.invoke(
        {
            "resume_text": sample_resume,
            "job_role": "Senior Software Engineer",
            "candidate_name": "John Doe",
            "num_questions": 3,
        },
        debug=True,
    )
    print("Session result:", json.dumps(result, indent=2))
    return result


async def test_report_flow(qa_history: list):
    """Compile and run the performance report flow."""
    print("\nCompiling performance_report_flow …")
    flow_def = await build_performance_report_flow().compile_deploy()
    flow_def.dump_spec(str(GENERATED / "performance_report_flow.json"))
    print("  → Spec written to generated/performance_report_flow.json")

    result = await flow_def.invoke(
        {
            "candidate_name": "John Doe",
            "job_role": "Senior Software Engineer",
            "qa_history": json.dumps(qa_history),
        },
        debug=True,
    )
    print("Report result:", result.get("report_markdown", "")[:500], "…")
    return result


async def main():
    session_result = await test_interview_session()
    # Use dummy history if test session doesn't return structured data
    dummy_history = [
        {
            "question": "Explain microservices vs monolith.",
            "answer": "Microservices split the app into independent services.",
            "score": 7,
            "strengths": "Good high-level understanding",
            "improvements": "Missed trade-offs",
        }
    ]
    history = session_result.get("session_summary", dummy_history)
    if isinstance(history, str):
        try:
            history = json.loads(history)
        except Exception:
            history = dummy_history
    await test_report_flow(history)


if __name__ == "__main__":
    asyncio.run(main())
