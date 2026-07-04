from __future__ import annotations

from typing import TypedDict


class ReviewGraphState(TypedDict, total=False):
    git_diff: str
    execution_trace: list[str]
    security_findings: list[dict[str, object]]
    clean_code_findings: list[dict[str, object]]
    review_markdown: str