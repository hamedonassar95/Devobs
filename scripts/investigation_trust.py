#!/usr/bin/env python3
"""Deterministic trust checks for Phase 8 incident investigations."""

from __future__ import annotations

TRUSTED_ACTOR = "github-actions[bot]"
HEADING = "## AI Incident Investigation"
LEGACY_MARKER = "<!-- devobs-investigation:v1 -->"
GH_AW_PREFIX = "<!-- gh-aw-agentic-workflow: Devobs Incident Investigator"
WORKFLOW_ID = "workflow_id: incident-investigator"


def trusted_incident(issue: object) -> bool:
    if not isinstance(issue, dict):
        return False
    body = issue.get("body")
    title = issue.get("title")
    user = issue.get("user")
    return (
        issue.get("state") == "open"
        and isinstance(title, str)
        and title.startswith("incident:")
        and isinstance(body, str)
        and "<!-- incident-run-id:" in body
        and isinstance(user, dict)
        and user.get("login") == TRUSTED_ACTOR
    )


def trusted_investigation(comment: object) -> bool:
    if not isinstance(comment, dict):
        return False
    body = comment.get("body")
    user = comment.get("user")
    if not isinstance(body, str) or not isinstance(user, dict):
        return False
    provenance = LEGACY_MARKER in body or (
        GH_AW_PREFIX in body and WORKFLOW_ID in body
    )
    return (
        user.get("login") == TRUSTED_ACTOR
        and HEADING in body
        and provenance
    )
