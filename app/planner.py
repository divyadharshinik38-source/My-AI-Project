"""
Interview planner.

Given a candidate's mission history + the curriculum, decide which
curriculum days to probe during the interview, and WHY -- this "why"
is what makes the interview feel adaptive instead of a fixed quiz.

Scoring priority (highest signal first):
    1. FAILED missions      (passed == False)   -> definitely probe
    2. SKIPPED missions     (skipped == True)    -> probe once, gently
    3. STRUGGLED-BUT-PASSED (attempts >= 3)      -> good follow-up ground
    4. EASY FIRST-TRY PASS  (attempts == 1)      -> quick confirm / escalate
"""

from typing import Optional

MIN_DAYS = 4


def _score_mission(mission: dict) -> tuple[float, str]:
    """Return (priority_score, reason) for a single mission entry."""
    if mission.get("skipped"):
        return 3.0, "skipped this topic entirely"

    passed = mission.get("passed")
    attempts = mission.get("attempts") or 1

    if passed is False:
        return 4.0, "did not pass this mission"

    if passed is True and attempts >= 3:
        return 2.0, f"needed {attempts} attempts to pass"

    if passed is True and attempts == 1:
        return 0.5, "passed on the first attempt"

    return 1.0, "completed this mission"


def _find_curriculum_day(curriculum: dict, day_number: int) -> Optional[dict]:
    for day in curriculum["days"]:
        if day["day"] == day_number:
            return day
    return None


def _find_module_for_day(curriculum: dict, day_number: int) -> str:
    for module in curriculum["modules"]:
        lo, hi = module["days"]
        if lo <= day_number <= hi:
            return module["title"]
    return "Unknown Module"


def build_interview_plan(candidate: dict, curriculum: dict, min_days: int = MIN_DAYS) -> list[dict]:
    """
    Returns an ordered list of topic entries to interview on.
    """
    scored = []
    for mission in candidate["missions"]:
        day_number = mission["day"]
        curriculum_day = _find_curriculum_day(curriculum, day_number)
        if curriculum_day is None:
            continue  # mission references a day not in curriculum -- skip safely

        score, reason = _score_mission(mission)
        scored.append({
            "day": day_number,
            "title": curriculum_day["title"],
            "module": _find_module_for_day(curriculum, day_number),
            "objectives": curriculum_day["objectives"],
            "tools": curriculum_day["tools"],
            "reason": reason,
            "score": score,
        })

    # Highest-priority signals first
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Take top scorers, but ensure we hit min_days and don't
    # cluster every pick in the same module if we can help it.
    plan: list[dict] = []
    seen_modules: set[str] = set()

    for entry in scored:
        if len(plan) >= min_days and entry["module"] in seen_modules:
            continue
        plan.append(entry)
        seen_modules.add(entry["module"])
        if len(plan) >= max(min_days, 6):  # cap so interview doesn't run forever
            break

    # Safety net: if candidate had very few missions, top up from
    # whatever's left regardless of module repetition.
    if len(plan) < min_days:
        remaining = [e for e in scored if e not in plan]
        plan.extend(remaining[: min_days - len(plan)])

    return plan