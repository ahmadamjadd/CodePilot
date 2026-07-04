from __future__ import annotations

import hashlib
import json
import re
from typing import List, Optional

from codepilot_review.llm.base import LLMClient
from codepilot_review.llm.groq_client import GroqClient
from codepilot_review.models.security import SecurityFinding, Severity


class SecurityAgent:
    """Security review agent.

    Performs both deterministic checks and LLM-based analysis for comprehensive
    security review. LLM-based checks are mandatory.
    """

    SECRET_PATTERNS = [
        r"(?i)apikey\s*=\s*['\"]?[A-Za-z0-9\-_=\/]+['\"]?",
        r"(?i)api_key\s*=\s*['\"]?[A-Za-z0-9\-_=\/]+['\"]?",
        r"(?i)secret\s*(?:key)?\s*=\s*['\"]?[A-Za-z0-9\-_=\/]+['\"]?",
        r"-----BEGIN (?:RSA |)PRIVATE KEY-----(?:.|\n)+?-----END (?:RSA |)PRIVATE KEY-----",
        r"(?i)password\s*=\s*['\"][^'\"]+['\"]",
    ]

    SQL_INJECTION_HINTS = [r"\+\s*\"?\s*select\b", r"format\(|%s" ]

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm = llm_client or GroqClient()

    def _make_id(self, text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]

    def review(self, git_diff: str) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []

        # Check for hardcoded secrets
        for pat in self.SECRET_PATTERNS:
            for m in re.finditer(pat, git_diff, flags=re.MULTILINE):
                snippet = m.group(0)
                fid = self._make_id(snippet)
                findings.append(
                    SecurityFinding(
                        id=fid,
                        rule="hardcoded-secret",
                        severity=Severity.CRITICAL,
                        description="Hardcoded secret or private key detected in diff.",
                        recommendation="Remove secrets from code and use a secrets manager. Rotate any exposed credentials.",
                        confidence=0.95,
                        metadata={"match": snippet[:200]},
                    )
                )

        # Simple heuristic for SQL injection risky patterns
        for hint in self.SQL_INJECTION_HINTS:
            for m in re.finditer(hint, git_diff, flags=re.IGNORECASE):
                snippet = m.group(0)
                fid = self._make_id(snippet)
                findings.append(
                    SecurityFinding(
                        id=fid,
                        rule="possible-sql-injection",
                        severity=Severity.HIGH,
                        description="Pattern that may lead to SQL injection detected.",
                        recommendation="Use parameterized queries or ORM query builders instead of string concatenation.",
                        confidence=0.6,
                        metadata={"match": snippet[:200]},
                    )
                )

        findings.extend(self._llm_review(git_diff))
        return self._dedupe_findings(findings)

    def _dedupe_findings(self, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        seen: set[tuple] = set()
        deduped: List[SecurityFinding] = []
        for finding in findings:
            key = (finding.rule, finding.severity.value, finding.description)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(finding)
        return deduped

    def _extract_json_array(self, text: str) -> Optional[list]:
        # Try to extract the first JSON array found in the text
        m = re.search(r"(\[\s*(?:.|\n)*?\])", text, flags=re.MULTILINE)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception:
            return None

    def _llm_review(self, git_diff: str) -> List[SecurityFinding]:
        """Use the LLM client to get additional security findings.

        The LLM is asked to return a JSON array of findings. We attempt to
        parse a JSON array from the model's textual reply and convert each
        element into a SecurityFinding. Any parsing error is caught and
        results in zero LLM findings (deterministic checks still apply).
        """

        prompt = (
            "You are a security code reviewer. Analyze the following unified git "
            "diff and return a JSON array of findings. Each finding must be an "
            "object with the keys: id, rule, severity (critical/high/medium/low/info), "
            "description, file_path, line_start, line_end, confidence, recommendation, metadata. "
            "Return only the JSON array and no additional text.\n\nDiff:\n" + git_diff
        )

        try:
            resp = self.llm.generate(prompt, params={"max_tokens": 1500})
        except Exception:
            return []

        # Attempt to find textual content in common response shapes
        text_candidates = []
        if isinstance(resp, str):
            text_candidates.append(resp)
        elif isinstance(resp, dict):
            # common keys that might contain text
            for key in ("result", "output", "text", "response", "content"):
                val = resp.get(key)
                if isinstance(val, str):
                    text_candidates.append(val)
            # list-style outputs
            for key in ("outputs", "choices"):
                val = resp.get(key)
                if isinstance(val, list) and val:
                    # join textual parts
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

        # Always try the stringified full response as a last resort
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

        findings: List[SecurityFinding] = []
        for item in parsed:
            try:
                severity = Severity(item.get("severity", "info"))
            except Exception:
                severity = Severity.INFO

            fid = item.get("id") or self._make_id(json.dumps(item))

            findings.append(
                SecurityFinding(
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
