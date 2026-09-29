"""
Decision layer (agentic).

Takes the ranked alternatives from the graph engine + a policy config,
picks the best compliant option, computes ripple effects on dependent
legs (hotel/car), and produces a short natural-language justification.

If ANTHROPIC_API_KEY is set in the environment, justifications are
generated with a real LLM call. Otherwise we fall back to a deterministic
template so the whole demo still runs with zero external dependencies.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from .graph_engine import RankedOption
from .policy import DEFAULT_POLICY, Policy, within_policy

DATE_FMT = "%Y-%m-%dT%H:%M:%S"


def _parse(dt: str) -> datetime:
    return datetime.strptime(dt, DATE_FMT)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%b %d, %I:%M %p").replace(" 0", " ")


def compute_ripple_effects(original: dict, chosen: RankedOption) -> list[dict]:
    """Explicit, visible re-evaluation of dependent legs (hotel + car)."""
    ripples = []

    orig_hotel_checkin = _parse(original["hotel"]["check_in"])
    new_hotel_checkin = _parse(chosen.hotel["check_in"])
    if new_hotel_checkin != orig_hotel_checkin:
        ripples.append(
            {
                "leg": "hotel",
                "field": "check_in",
                "from": original["hotel"]["check_in"],
                "to": chosen.hotel["check_in"],
                "reason": "Hotel check-in shifted to line up with the new flight arrival time.",
            }
        )
    if chosen.hotel["hotel_id"] != original["hotel"]["hotel_id"]:
        ripples.append(
            {
                "leg": "hotel",
                "field": "property",
                "from": original["hotel"]["name"],
                "to": chosen.hotel["name"],
                "reason": "Original property unavailable at the new check-in time; rebooked to nearest equivalent.",
            }
        )

    orig_car_pickup = _parse(original["car"]["pickup"])
    new_car_pickup = _parse(chosen.car["pickup"])
    if new_car_pickup != orig_car_pickup:
        ripples.append(
            {
                "leg": "car",
                "field": "pickup",
                "from": original["car"]["pickup"],
                "to": chosen.car["pickup"],
                "reason": "Rental car pickup shifted to match the adjusted hotel check-in.",
            }
        )
    if chosen.car["car_id"] != original["car"]["car_id"]:
        ripples.append(
            {
                "leg": "car",
                "field": "vendor",
                "from": original["car"]["vendor"],
                "to": chosen.car["vendor"],
                "reason": "Original rental vendor slot unavailable at the new pickup time; rebooked to nearest equivalent.",
            }
        )
    return ripples


def _template_justification(option: RankedOption, violations: list[str], escalated: bool) -> str:
    f = option.flight
    if escalated:
        return (
            f"Best available alternative is {f['carrier']} {f['flight_number']} "
            f"({option.delay_minutes} min later, ${option.fare_delta:.2f} fare delta), "
            f"but it falls outside policy: {', '.join(violations)}. Routed for member approval."
        )
    return (
        f"Rebooked onto {f['carrier']} {f['flight_number']}, departing {_fmt(_parse(f['departure']))}. "
        f"Adds {option.delay_minutes} min vs. original arrival and a ${option.fare_delta:.2f} fare delta, "
        f"both within policy limits, so this was auto-executed."
    )


def _llm_justification(option: RankedOption, violations: list[str], escalated: bool) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import requests

        f = option.flight
        prompt = (
            "You are a travel concierge agent. In 2 sentences, explain this rebooking "
            "decision to a card member in plain, warm, concise language. "
            f"New flight: {f['carrier']} {f['flight_number']} departing {f['departure']}. "
            f"Added delay: {option.delay_minutes} minutes. Fare delta: ${option.fare_delta:.2f}. "
            f"Cabin match: {option.cabin_match}. "
            f"Policy violations: {violations if violations else 'none'}. "
            f"Escalated for approval: {escalated}."
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        return text.strip() or None
    except Exception:
        return None


def decide(
    original_itinerary: dict,
    ranked_options: list[RankedOption],
    policy: Policy = DEFAULT_POLICY,
) -> dict:
    """
    Returns a decision dict:
      {
        options_considered: [...],
        chosen: {...} | None,
        auto_executed: bool,
        escalated: bool,
        reasoning: str,
        ripple_effects: [...]
      }
    """
    original_cabin = original_itinerary["flight"]["cabin_class"]

    if not ranked_options:
        return {
            "options_considered": [],
            "chosen": None,
            "auto_executed": False,
            "escalated": True,
            "reasoning": "No alternative inventory found for this route. Routed for member approval.",
            "ripple_effects": [],
        }

    scored = []
    for opt in ranked_options:
        compliant, violations = within_policy(opt, original_cabin, policy)
        scored.append((opt, compliant, violations))

    compliant_options = [s for s in scored if s[1]]

    if compliant_options:
        chosen, _, _ = compliant_options[0]
        ripples = compute_ripple_effects(original_itinerary, chosen)
        reasoning = _llm_justification(chosen, [], escalated=False) or _template_justification(
            chosen, [], escalated=False
        )
        return {
            "options_considered": [o.to_dict() for o, _, _ in scored],
            "chosen": chosen.to_dict(),
            "auto_executed": True,
            "escalated": False,
            "reasoning": reasoning,
            "ripple_effects": ripples,
        }

    # nothing complies -> escalate with the least-bad option surfaced for the member
    best, _, violations = scored[0]
    ripples = compute_ripple_effects(original_itinerary, best)
    reasoning = _llm_justification(best, violations, escalated=True) or _template_justification(
        best, violations, escalated=True
    )
    return {
        "options_considered": [o.to_dict() for o, _, _ in scored],
        "chosen": best.to_dict(),
        "auto_executed": False,
        "escalated": True,
        "reasoning": reasoning,
        "ripple_effects": ripples,
    }

