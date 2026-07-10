"""AWS Lambda handler for CodePilot GitHub pull request reviews."""

import json
import logging
import os
from typing import Any

import requests

from codepilot_review import run_review

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _parse_webhook_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Parse a GitHub webhook payload stored inside an SQS message."""

    body = record.get("body")

    if body is None:
        raise ValueError("SQS record does not contain a body")

    payload = json.loads(body)

    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object")

    return payload


def _extract_github_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract GitHub metadata from the webhook payload."""

    repository = payload.get("repository") or {}
    pull_request = payload.get("pull_request") or {}

    return {
        "repository": repository.get("full_name"),
        "pull_request_number": pull_request.get("number"),
        "action": payload.get("action"),
    }


def _fetch_pull_request_diff(metadata: dict[str, Any]) -> str:
    """Fetch the raw diff for a GitHub pull request."""

    repository = metadata["repository"]
    pull_request_number = metadata["pull_request_number"]

    if not repository or not pull_request_number:
        raise ValueError("Missing repository or pull request number")

    url = (
        f"https://api.github.com/repos/"
        f"{repository}/pulls/{pull_request_number}"
    )

    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Token is optional for reading public repositories
    if token:
        headers["Authorization"] = f"Bearer {token}"

    logger.info(
        "Fetching diff for %s PR #%s",
        repository,
        pull_request_number,
    )

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    diff = response.text

    if not diff.strip():
        raise ValueError("GitHub returned an empty diff")

    return diff


def _post_pull_request_comment(metadata: dict[str, Any], report: str) -> None:
    """Post the markdown review as a GitHub PR comment."""

    repository = metadata["repository"]
    pull_request_number = metadata["pull_request_number"]

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not configured")

    url = (
        f"https://api.github.com/repos/"
        f"{repository}/issues/{pull_request_number}/comments"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = requests.post(
        url,
        headers=headers,
        json={"body": report},
        timeout=30,
    )

    response.raise_for_status()

    logger.info("Successfully posted review comment to GitHub")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process GitHub pull request webhook messages received from SQS."""

    try:
        records = event.get("Records", [])

        if not records:
            raise ValueError("No SQS records found")

        for record in records:

            payload = _parse_webhook_payload(record)

            if "pull_request" not in payload:
                logger.info("Ignoring non pull_request event")
                continue

            metadata = _extract_github_metadata(payload)

            logger.info(
                "Repository=%s PR=%s Action=%s",
                metadata["repository"],
                metadata["pull_request_number"],
                metadata["action"],
            )

            # Only review these PR events
            if metadata["action"] not in {
                "opened",
                "reopened",
                "synchronize",
            }:
                logger.info(
                    "Ignoring pull request action '%s'",
                    metadata["action"],
                )
                continue

            diff = _fetch_pull_request_diff(metadata)

            logger.info("Fetched diff (%d bytes)", len(diff))

            report = run_review(diff)

            logger.info("Review generated successfully")

            _post_pull_request_comment(metadata, report)

            logger.info("Review posted successfully")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Webhook processed successfully."
                }
            ),
        }

    except Exception as error:
        logger.exception("Webhook processing failed")

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": str(error),
                }
            ),
        }