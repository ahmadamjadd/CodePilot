from __future__ import annotations

import hashlib
import json
import re
from typing import List, Optional

from codepilot_review.llm.base import LLMClient
from codepilot_review.llm.groq_client import GroqClient
from codepilot_review.models.clean_code import CleanCodeFinding, CleanCodeSeverity


class CleanCodeAgent:
    """Clean code review agent.

    Performs deterministic heuristic checks and LLM-based analysis for comprehensive
    review. LLM-based checks are mandatory.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm = llm_client or GroqClient()

    def _make_id(self, text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]

    def review(self, git_diff: str) -> List[CleanCodeFinding]:
        findings: List[CleanCodeFinding] = []

        for line in git_diff.splitlines():
            if not line.startswith("+"):
                continue

            code = line[1:].strip()

            if not code:
                continue

            if len(code) > 140:
                findings.append(
                    CleanCodeFinding(
                        id=self._make_id(code),
                        rule="long-line",
                        severity=CleanCodeSeverity.LOW,
                        description="Added line is very long and may hurt readability.",
                        confidence=0.7,
                        recommendation="Break the line into smaller expressions or helper variables.",
                        metadata={"length": len(code), "line": code[:200]},
                    )
                )

            if re.search(r"\b(temp|tmp|foo|bar|data|result1|result2|x|y)\b", code):
                findings.append(
                    CleanCodeFinding(
                        id=self._make_id(code + "-naming"),
                        rule="weak-naming",
                        severity=CleanCodeSeverity.MEDIUM,
                        description="Variable or symbol naming appears unclear.",
                        confidence=0.6,
                        recommendation="Use descriptive names that communicate intent.",
                        metadata={"line": code[:200]},
                    )
                )

            if code.count("(") > 3 and len(code) > 80:
                findings.append(
                    CleanCodeFinding(
                        id=self._make_id(code + "-complex"),
                        rule="complex-expression",
                        severity=CleanCodeSeverity.MEDIUM,
                        description="Expression may be too complex to read or maintain easily.",
                        confidence=0.55,
                        recommendation="Extract parts of the expression into named helper variables or functions.",
                        metadata={"line": code[:200]},
                    )
                )

        findings.extend(self._llm_review(git_diff))
        return self._dedupe_findings(findings)

    def _dedupe_findings(self, findings: List[CleanCodeFinding]) -> List[CleanCodeFinding]:
        seen: set[tuple] = set()
        deduped: List[CleanCodeFinding] = []
        for finding in findings:
            key = (finding.rule, finding.severity.value, finding.description)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(finding)
        return deduped

    def _extract_json_array(self, text: str) -> Optional[list]:
        m = re.search(r"(\[\s*(?:.|\n)*?\])", text, flags=re.MULTILINE)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception:
            return None

    def _llm_review(self, git_diff: str) -> List[CleanCodeFinding]:
        prompt = (
            "You are a clean code reviewer. Analyze the following unified git "
            "diff and return a JSON array of findings. Each finding must be an "
            "object with the keys: id, rule, severity (high/medium/low/info), "
            "description, file_path, line_start, line_end, confidence, recommendation, metadata. "
            "Evaluate variable naming, function naming, readability, maintainability, SOLID, DRY, "
            "complexity, code duplication, function size, and modularity. "
            "Return only the JSON array and no additional text.\n\nDiff:\n" + git_diff
        )

        try:
            resp = self.llm.generate(prompt, params={"max_tokens": 2000})
        except Exception:
            return []

        text_candidates = []
        if isinstance(resp, str):
            text_candidates.append(resp)
        elif isinstance(resp, dict):
            for key in ("result", "output", "text", "response", "content"):
                val = resp.get(key)
                if isinstance(val, str):
                    text_candidates.append(val)
            for key in ("outputs", "choices"):
                val = resp.get(key)
                if isinstance(val, list) and val:
                    parts = []
                    for item in val:
                        if isinstance(item, dict):
                            for subkey in ("text", "content", "output"):
                                v = item.get(subkey)
                                if isinstance(v, str):
                                    parts.append(v)
                            message = item.get("message")
                            if isinstance(message, dict):
                                content = message.get("content")
                                if isinstance(content, str):
                                    parts.append(content)
                        elif isinstance(item, str):
                            parts.append(item)
                    if parts:
                        text_candidates.append("\n".join(parts))

        try:
            text_candidates.append(json.dumps(resp))
        except Exception:
            pass

        parsed: Optional[list] = None
        for txt in text_candidates:
            parsed = self._extract_json_array(txt)
            if parsed is not None:
                break

        if not parsed:
            return []

        findings: List[CleanCodeFinding] = []
        for item in parsed:
            try:
                severity = CleanCodeSeverity(item.get("severity", "info"))
            except Exception:
                severity = CleanCodeSeverity.INFO

            fid = item.get("id") or self._make_id(json.dumps(item))

            findings.append(
                CleanCodeFinding(
                    id=fid,
                    rule=item.get("rule", "llm-finding"),
                    severity=severity,
                    description=item.get("description", ""),
                    file_path=item.get("file_path"),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                    confidence=float(item.get("confidence", 0.5)),
                    recommendation=item.get("recommendation"),
                    metadata=item.get("metadata", {}),
                )
            )

        return findings
