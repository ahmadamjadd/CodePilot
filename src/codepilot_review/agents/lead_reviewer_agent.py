from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, List, Optional

from codepilot_review.llm.base import LLMClient
from codepilot_review.llm.groq_client import GroqClient
from codepilot_review.models.security import SecurityFinding, Severity
from codepilot_review.models.clean_code import CleanCodeFinding, CleanCodeSeverity


_SYSTEM_PROMPT = """\
You are a principal software engineer conducting a formal code review for a \
pull request. You write with the precision and authority of a senior technical \
leader. Your audience is other engineers and engineering managers who need to \
make an informed merge decision.

Tone and style rules (follow these exactly):
- Write in clear, direct, professional English.
- Do NOT use any emojis anywhere in the report.
- Do NOT use filler words, hype, or vague praise ("great job", "looks good overall").
- Every sentence must convey concrete, actionable information.
- Use GitHub-flavored Markdown throughout.
"""

_USER_PROMPT_TEMPLATE = """\
Generate a comprehensive code review report in Markdown for the pull request \
described below. The report will be posted as a GitHub PR comment, so format \
it accordingly.

REPORT STRUCTURE (use these exact headings):

# CodePilot Review Report

**Review Date:** {generated_at}

---

## Executive Summary

Write a 3-5 sentence paragraph that:
- States the total number of findings (security and code quality separately).
- Highlights the most critical risk(s) in plain language.
- Gives an overall risk assessment (Critical / High / Moderate / Low / Clean).

---

## Security Analysis

For EACH security finding, write a subsection with:

### [Finding Title derived from the rule name]

**Severity:** [severity] | **Confidence:** [confidence as percentage]

**Description:** Write 2-3 sentences explaining WHAT was detected and WHY it \
is a security concern. Reference the specific code or pattern from the diff.

**Impact:** Explain the real-world consequences if this issue reaches production \
(e.g., credential exposure, unauthorized access, data exfiltration).

**Evidence:**
Quote or reference the specific line(s) from the diff that triggered this finding. \
Use a fenced code block with the relevant language.

**Remediation:**
Provide step-by-step remediation instructions. Where possible, include a short \
corrected code snippet showing the fix.

If there are NO security findings, write a brief statement confirming no security \
issues were detected.

---

## Code Quality Analysis

For EACH code quality finding, write a subsection with:

### [Finding Title derived from the rule name]

**Severity:** [severity] | **Confidence:** [confidence as percentage]

**Description:** Write 2-3 sentences explaining the code quality concern and \
its effect on readability, maintainability, or correctness.

**Evidence:**
Quote or reference the specific line(s) from the diff. Use a fenced code block.

**Recommendation:**
Provide a concrete suggestion with a corrected code example when applicable.

If there are NO code quality findings, write a brief statement confirming the \
code meets quality standards.

---

## Merge Decision

State clearly whether this PR is **approved**, **approved with conditions**, \
or **changes requested**. Provide 2-3 sentences of rationale referencing the \
specific findings that informed your decision.

---

## Recommended Actions

Provide a numbered list of specific next steps, ordered by priority. Each item \
should be a concrete, actionable task (not a vague suggestion).

---

INPUT DATA:

{input_json}

DIFF EXCERPT:

```
{diff_excerpt}
```

IMPORTANT REMINDERS:
- Do NOT use any emojis.
- Do NOT wrap the entire output in a code fence. Return raw Markdown.
- Be thorough. Each finding deserves detailed analysis, not a one-liner.
- Reference specific lines and code from the diff as evidence.
"""


class LeadReviewerAgent:
    """Lead Reviewer Agent.

    Combines security and clean code findings into a professional Markdown report
    organized by severity, category, and actionability. Uses a detailed system
    prompt and structured user prompt to produce thorough, LLM-written analysis
    rather than a templated summary.
    """

    SEVERITY_ORDER = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "info": 4,
    }
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm = llm_client or GroqClient()

    def generate_report(
        self,
        git_diff: str,
        security_findings: List[SecurityFinding],
        clean_code_findings: List[CleanCodeFinding],
    ) -> str:
        """Generate a professional Markdown review report using the LLM."""
        sec_critical = sum(1 for f in security_findings if f.severity == Severity.CRITICAL)
        sec_high = sum(1 for f in security_findings if f.severity == Severity.HIGH)
        code_high = sum(1 for f in clean_code_findings if f.severity == CleanCodeSeverity.HIGH)
        code_medium = sum(1 for f in clean_code_findings if f.severity == CleanCodeSeverity.MEDIUM)

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        prompt_payload = {
            "generated_at": generated_at,
            "summary": {
                "security_total": len(security_findings),
                "security_critical": sec_critical,
                "security_high": sec_high,
                "code_quality_total": len(clean_code_findings),
                "code_quality_high": code_high,
                "code_quality_medium": code_medium,
                "total_findings": len(security_findings) + len(clean_code_findings),
            },
            "security_findings": [f.to_dict() for f in security_findings],
            "clean_code_findings": [f.to_dict() for f in clean_code_findings],
        }

        diff_excerpt = git_diff[:12000]

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            generated_at=generated_at,
            input_json=json.dumps(prompt_payload, indent=2, ensure_ascii=True),
            diff_excerpt=diff_excerpt,
        )

        response = self.llm.generate(
            user_prompt,
            system_prompt=_SYSTEM_PROMPT,
            model=self.DEFAULT_MODEL,
            params={"max_tokens": 4096, "temperature": 0.15},
        )
        report = self._extract_text(response)
        if not report.strip():
            raise RuntimeError("LeadReviewerAgent received an empty report from LLM")

        # Strip markdown code fences if the LLM wraps the entire output
        report = report.strip()
        if report.startswith("```markdown"):
            report = report[len("```markdown"):].strip()
        if report.startswith("```md"):
            report = report[len("```md"):].strip()
        if report.startswith("```"):
            report = report[3:].strip()
        if report.endswith("```"):
            report = report[:-3].strip()

        return report

    def _extract_text(self, response: Any) -> str:
        if isinstance(response, str):
            return response
        if not isinstance(response, dict):
            return ""

        for key in ("text", "content", "output", "response", "result"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value

        choices = response.get("choices")
        if isinstance(choices, list):
            parts: list[str] = []
            for item in choices:
                if not isinstance(item, dict):
                    continue
                message = item.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        parts.append(content)
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text)
            if parts:
                return "\n".join(parts)

        return ""

