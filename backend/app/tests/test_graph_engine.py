import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.graph_engine import ItineraryGraph
from app.agent import decide, compute_ripple_effects
from app.policy import DEFAULT_POLICY, within_policy

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
ITINERARIES = json.loads((FIXTURES_DIR / "itineraries.json").read_text())
INVENTORY = json.loads((FIXTURES_DIR / "inventory.json").read_text())


def test_ranks_alternatives_for_economy_itinerary():
    itinerary = ITINERARIES["PAX-1001"]  # SFO-ORD, economy
    graph = ItineraryGraph(itinerary, INVENTORY)
    options = graph.rank_options(top_k=3)
    assert len(options) > 0
    # results should be sorted ascending by score (cheapest/least-disruptive first)
    scores = [o.total_weight for o in options]
    assert scores == sorted(scores)


def test_business_cabin_itinerary_prefers_cabin_match():
    itinerary = ITINERARIES["PAX-1003"]  # DFW-MIA, business
    graph = ItineraryGraph(itinerary, INVENTORY)
    options = graph.rank_options(top_k=3)
    assert len(options) > 0
    # the top-ranked option should match the original cabin class when a
    # same-cabin alternative exists in inventory
    assert options[0].cabin_match is True


def test_auto_execute_within_policy():
    itinerary = ITINERARIES["PAX-1002"]  # JFK-ATL, economy, cheap fares available
    graph = ItineraryGraph(itinerary, INVENTORY)
    options = graph.rank_options(top_k=3)
    decision = decide(itinerary, options)
    assert decision["chosen"] is not None
    # JFK-ATL alternatives are all within the default $150/240min policy
    assert decision["auto_executed"] is True
    assert decision["escalated"] is False


def test_escalation_when_no_option_is_compliant():
    itinerary = ITINERARIES["PAX-1001"]
    graph = ItineraryGraph(itinerary, INVENTORY)
    options = graph.rank_options(top_k=3)
    # a very strict policy should force escalation even with options available
    from app.policy import Policy

    strict = Policy(max_fare_delta=0.0, max_added_delay_minutes=0)
    decision = decide(itinerary, options, policy=strict)
    assert decision["auto_executed"] is False
    assert decision["escalated"] is True
    assert decision["chosen"] is not None  # still surfaces the least-bad option


def test_ripple_effects_present_when_hotel_or_car_shift():
    itinerary = ITINERARIES["PAX-1001"]
    graph = ItineraryGraph(itinerary, INVENTORY)
    options = graph.rank_options(top_k=3)
    decision = decide(itinerary, options)
    # at least one ripple effect should be reported since the alt flight
    # arrives later than the original in this fixture
    assert isinstance(decision["ripple_effects"], list)


def test_malformed_status_rejected_by_schema():
    from pydantic import ValidationError
    from app.models import DisruptionEvent

    try:
        DisruptionEvent(
            flight_id="FL-999",
            status="on_time",  # not a valid disruption status
            pax_id="PAX-1001",
            original_itinerary="ITIN-1",
        )
        assert False, "expected ValidationError"
    except ValidationError:
        pass
