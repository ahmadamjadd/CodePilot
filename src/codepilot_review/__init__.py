"""CodePilot Review package."""

from functools import lru_cache

from codepilot_review.graph.workflow import build_graph


@lru_cache(maxsize=1)
def _compiled_graph():
	return build_graph()


def run_review(diff: str) -> str:
	"""Run the full code review pipeline and return the Markdown report."""
	result = _compiled_graph().invoke({"git_diff": diff, "execution_trace": []})
	return result.get("review_markdown", "")


__all__ = ["run_review"]