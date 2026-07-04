from __future__ import annotations

from datetime import datetime
from typing import List

from codepilot_review.models.security import SecurityFinding, Severity
from codepilot_review.models.clean_code import CleanCodeFinding, CleanCodeSeverity


class LeadReviewerAgent:
    """Lead Reviewer Agent.

    Combines security and clean code findings into a professional Markdown report
    organized by severity, category, and actionability.
    """

    SEVERITY_ORDER = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "info": 4,
    }

    def generate_report(
        self,
        git_diff: str,
        security_findings: List[SecurityFinding],
        clean_code_findings: List[CleanCodeFinding],
    ) -> str:
        """Generate a professional Markdown review report."""

        lines = [
            "# Code Review Report",
            "",
            f"**Generated:** {datetime.utcnow().isoformat()}Z",
            "",
        ]

        # Executive summary
        sec_critical = sum(1 for f in security_findings if f.severity == Severity.CRITICAL)
        sec_high = sum(1 for f in security_findings if f.severity == Severity.HIGH)
        code_high = sum(
            1 for f in clean_code_findings if f.severity == CleanCodeSeverity.HIGH
        )
        code_medium = sum(
            1 for f in clean_code_findings if f.severity == CleanCodeSeverity.MEDIUM
        )

        lines.append("## Executive Summary")
        lines.append("")
        lines.append(
            f"- **Security Findings:** {len(security_findings)} "
            f"(Critical: {sec_critical}, High: {sec_high})"
        )
        lines.append(
            f"- **Code Quality Findings:** {len(clean_code_findings)} "
            f"(High: {code_high}, Medium: {code_medium})"
        )
        lines.append(f"- **Total:** {len(security_findings) + len(clean_code_findings)} issues")
        lines.append("")

        # Security findings section
        if security_findings:
            lines.append("## 🔒 Security Review")
            lines.append("")

            sorted_sec = sorted(
                security_findings,
                key=lambda f: self.SEVERITY_ORDER.get(f.severity.value, 999),
            )

            for finding in sorted_sec:
                lines.append(self._format_finding(finding, finding.severity.value))

        # Code quality findings section
        if clean_code_findings:
            lines.append("## 📝 Code Quality Review")
            lines.append("")

            sorted_code = sorted(
                clean_code_findings,
                key=lambda f: self.SEVERITY_ORDER.get(f.severity.value, 999),
            )

            for finding in sorted_code:
                lines.append(self._format_finding(finding, finding.severity.value))

        # Summary recommendations
        lines.append("## Summary & Recommendations")
        lines.append("")

        if sec_critical > 0:
            lines.append(
                f"⚠️ **Action Required:** Address {sec_critical} critical security issue(s) "
                "before deployment."
            )
            lines.append("")

        if sec_high > 0 or code_high > 0:
            lines.append(
                f"⚠️ **High Priority:** Review and address {sec_high + code_high} "
                "high-severity issue(s) soon."
            )
            lines.append("")

        lines.append("✅ **Next Steps:**")
        lines.append("1. Review all critical and high-severity findings.")
        lines.append("2. Address recommendations in priority order.")
        lines.append("3. Re-run review after changes.")
        lines.append("")

        return "\n".join(lines)

    def _format_finding(self, finding, severity: str) -> str:
        """Format a single finding as Markdown."""
        lines = []

        severity_icon = self._severity_icon(severity)
        lines.append(f"### {severity_icon} {finding.rule}")
        lines.append("")
        lines.append(f"**Severity:** {severity.upper()}")
        lines.append(f"**Confidence:** {finding.confidence:.0%}")
        lines.append("")

        lines.append(f"**Issue:** {finding.description}")
        lines.append("")

        if finding.recommendation:
            lines.append(f"**Recommendation:** {finding.recommendation}")
            lines.append("")

        if finding.file_path:
            location_parts = [f"File: `{finding.file_path}`"]
            if finding.line_start:
                if finding.line_end and finding.line_end != finding.line_start:
                    location_parts.append(f"Lines: {finding.line_start}-{finding.line_end}")
                else:
                    location_parts.append(f"Line: {finding.line_start}")
            lines.append(", ".join(location_parts))
            lines.append("")

        if finding.metadata:
            meta_str = self._format_metadata(finding.metadata)
            if meta_str:
                lines.append(f"**Details:** {meta_str}")
                lines.append("")

        return "\n".join(lines)

    def _severity_icon(self, severity: str) -> str:
        icons = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "⚪",
        }
        return icons.get(severity.lower(), "•")

    def _format_metadata(self, metadata: dict) -> str:
        """Format metadata dict as human-readable text."""
        if not metadata:
            return ""

        parts = []
        for key, val in metadata.items():
            if isinstance(val, str) and len(val) > 100:
                val = val[:100] + "…"
            parts.append(f"{key}={val}")

        return "; ".join(parts)
