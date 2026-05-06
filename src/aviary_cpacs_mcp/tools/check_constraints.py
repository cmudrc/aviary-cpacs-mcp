"""Evaluate user-defined constraints against mission results."""

from __future__ import annotations

from typing import Any

from ..session_manager import session_manager

SUPPORTED_VARIABLES = {
    "total_fuel_burned_kg",
    "fuel_burned_kg",
    "gtow_kg",
    "wing_mass_kg",
    "reserve_fuel_kg",
    "zero_fuel_weight_kg",
    "total_distance_nm",
    "total_time_hr",
    "fuel_fraction",
}

VALID_OPERATORS = {"<=", ">=", "=="}


def check_constraints(payload: dict[str, Any]) -> dict[str, Any]:
    """Check whether mission results satisfy a list of constraints.

    Parameters
    ----------
    payload : dict
        ``session_id`` – mission session.
        ``constraints`` – list of dicts, each with:
            ``variable`` – result field name.
            ``operator`` – one of ``<=``, ``>=``, ``==``.
            ``value`` – target numeric value.
            ``label`` – optional human-readable label.
    """
    session_id = payload.get("session_id")
    if not session_id:
        return {"error": {"type": "ValidationError", "message": "session_id is required"}}

    session = session_manager.get(str(session_id))
    if session.results is None:
        return {"error": {"type": "RuntimeError", "message": "No results yet. Call run_mission first."}}

    constraints = payload.get("constraints", [])
    if not constraints:
        return {"error": {"type": "ValidationError", "message": "constraints list must not be empty"}}

    results_data = session.results
    constraint_results = []
    all_satisfied = True

    for c in constraints:
        variable = c.get("variable", "")
        operator = c.get("operator", "")
        target = c.get("value")
        label = c.get("label", f"{variable} {operator} {target}")

        if variable not in SUPPORTED_VARIABLES:
            return {
                "error": {
                    "type": "ValidationError",
                    "message": f"Unknown constraint variable: '{variable}'. Supported: {sorted(SUPPORTED_VARIABLES)}",
                }
            }

        if operator not in VALID_OPERATORS:
            return {
                "error": {
                    "type": "ValidationError",
                    "message": f"Invalid operator: '{operator}'. Must be one of: {sorted(VALID_OPERATORS)}",
                }
            }

        actual = results_data.get(variable)
        if actual is None:
            constraint_results.append(
                {
                    "label": label,
                    "variable": variable,
                    "satisfied": False,
                    "actual_value": None,
                    "target_value": target,
                    "margin": None,
                }
            )
            all_satisfied = False
            continue

        target_f = float(target)
        actual_f = float(actual)

        if operator == "<=":
            satisfied = actual_f <= target_f
            margin = target_f - actual_f
        elif operator == ">=":
            satisfied = actual_f >= target_f
            margin = actual_f - target_f
        else:  # "=="
            tol = abs(target_f) * 0.01 if target_f != 0 else 0.01
            satisfied = abs(actual_f - target_f) <= tol
            margin = tol - abs(actual_f - target_f)

        if not satisfied:
            all_satisfied = False

        constraint_results.append(
            {
                "label": label,
                "variable": variable,
                "operator": operator,
                "target_value": target_f,
                "actual_value": round(actual_f, 2),
                "satisfied": satisfied,
                "margin": round(margin, 2),
            }
        )

    n_ok = sum(1 for r in constraint_results if r["satisfied"])
    summary = f"{n_ok} of {len(constraint_results)} constraints satisfied."

    return {
        "success": True,
        "session_id": session_id,
        "all_satisfied": all_satisfied,
        "results": constraint_results,
        "summary": summary,
    }
