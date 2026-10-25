"""Score ranked root-service findings using fixed human-labelled offline examples.

Synthetic fixture scores are not field accuracy and cannot authorize actions.
"""
from __future__ import annotations
import re
from .correlation import IncidentFinding

_CASE=re.compile(r"[a-z][a-z0-9_-]{0,39}\Z")
_SERVICE=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class RootEvaluationError(ValueError):
    """Safe fixed error code."""


def evaluate_root_rankings(cases: list[dict], *, minimum_cases: int=30) -> dict:
    if type(cases) is not list or not 1<=len(cases)<=500:
        raise RootEvaluationError("invalid_dataset")
    if type(minimum_cases) is not int or not 30<=minimum_cases<=500:
        raise RootEvaluationError("invalid_gate")
    ids=set()
    top1=top3=abstained=0
    for case in cases:
        if type(case) is not dict or set(case)!={"case_id","expected_service","finding"}:
            raise RootEvaluationError("invalid_case")
        name,expected,finding=(case[k] for k in ("case_id","expected_service","finding"))
        if (type(name) is not str or _CASE.fullmatch(name) is None
                or type(expected) is not str or _SERVICE.fullmatch(expected) is None
                or type(finding) is not IncidentFinding or finding.model_used
                or finding.calibrated or
                finding.status not in {"INSUFFICIENT_EVIDENCE","PENDING_HUMAN_APPROVAL"}
                or len(finding.ranked_services)>3
                or any(type(s) is not str or _SERVICE.fullmatch(s) is None
                       for s in finding.ranked_services)):
            raise RootEvaluationError("invalid_case")
        if name in ids:
            raise RootEvaluationError("duplicate_case")
        ids.add(name)
        if not finding.ranked_services:
            abstained+=1
        else:
            top1+=int(finding.ranked_services[0]==expected)
            top3+=int(expected in finding.ranked_services)
    count=len(cases)
    return {"schema_version":1,"case_count":count,
            "top1_accuracy":top1/count,"top3_accuracy":top3/count,
            "abstention_rate":abstained/count,
            "minimum_sample_met":count>=minimum_cases,
            "production_evaluation":False,
            "promotion_authorized":False,
            "false_action_rate":None,
            "human_override_rate":None,
            "measured_cost_per_incident":None}
