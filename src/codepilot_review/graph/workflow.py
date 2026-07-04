from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from codepilot_review.agents.clean_code_agent import CleanCodeAgent
from codepilot_review.agents.lead_reviewer_agent import LeadReviewerAgent
from codepilot_review.agents.security_agent import SecurityAgent
from codepilot_review.models.clean_code import CleanCodeFinding, CleanCodeSeverity
from codepilot_review.models.security import SecurityFinding, Severity
from codepilot_review.models.state import ReviewGraphState


def _extend_trace(state: ReviewGraphState, marker: str) -> list[str]:
    trace = list(state.get("execution_trace", []))
    trace.append(marker)
    return trace


def _build_security_findings(serialized_findings: list[dict[str, object]]) -> list[SecurityFinding]:
    return [
        SecurityFinding(
            id=finding.get("id", ""),
            rule=finding.get("rule", ""),
            severity=Severity(finding.get("severity", "info")),
            description=finding.get("description", ""),
            file_path=finding.get("file_path"),
            line_start=finding.get("line_start"),
            line_end=finding.get("line_end"),
            confidence=finding.get("confidence", 0.5),
            recommendation=finding.get("recommendation"),
            metadata=finding.get("metadata", {}),
        )
        for finding in serialized_findings
    ]


def _build_clean_code_findings(
    serialized_findings: list[dict[str, object]],
) -> list[CleanCodeFinding]:
    return [
        CleanCodeFinding(
            id=finding.get("id", ""),
            rule=finding.get("rule", ""),
            severity=CleanCodeSeverity(finding.get("severity", "info")),
            description=finding.get("description", ""),
            file_path=finding.get("file_path"),
            line_start=finding.get("line_start"),
            line_end=finding.get("line_end"),
            confidence=finding.get("confidence", 0.5),
            recommendation=finding.get("recommendation"),
            metadata=finding.get("metadata", {}),
        )
        for finding in serialized_findings
    ]


def security_agent_node(state: ReviewGraphState) -> dict[str, object]:
    """Run the Security Review Agent."""
    trace = _extend_trace(state, "security_agent_started")
    findings = SecurityAgent().review(state.get("git_diff", ""))
    trace.append("security_agent_completed")

    return {
        "execution_trace": trace,
        "security_findings": [f.to_dict() for f in findings],
    }


def clean_code_agent_node(state: ReviewGraphState) -> dict[str, object]:
    """Run the Clean Code Review Agent."""
    trace = _extend_trace(state, "clean_code_agent_started")
    findings = CleanCodeAgent().review(state.get("git_diff", ""))
    trace.append("clean_code_agent_completed")

    return {
        "execution_trace": trace,
        "clean_code_findings": [f.to_dict() for f in findings],
    }


def lead_reviewer_node(state: ReviewGraphState) -> dict[str, object]:
    """Run the Lead Reviewer Agent to generate the final Markdown report."""
    trace = _extend_trace(state, "lead_reviewer_started")
    markdown_report = LeadReviewerAgent().generate_report(
        state.get("git_diff", ""),
        _build_security_findings(state.get("security_findings", [])),
        _build_clean_code_findings(state.get("clean_code_findings", [])),
    )
    trace.append("lead_reviewer_completed")

    return {
        "execution_trace": trace,
        "review_markdown": markdown_report,
    }


def build_graph():
    """Build the complete code review workflow."""
    graph = StateGraph(ReviewGraphState)

    graph.add_node("security_agent", security_agent_node)
    graph.add_node("clean_code_agent", clean_code_agent_node)
    graph.add_node("lead_reviewer", lead_reviewer_node)

    graph.add_edge(START, "security_agent")
    graph.add_edge("security_agent", "clean_code_agent")
    graph.add_edge("clean_code_agent", "lead_reviewer")
    graph.add_edge("lead_reviewer", END)

    return graph.compile()