"""
Graph engine — no LLM calls.

Models an itinerary as a directed graph:

    START -> flight_alt_1 -> hotel_alt_1 -> car_alt_1 -> END
          -> flight_alt_2 -> hotel_alt_2 -> car_alt_2 -> END
          ...

Edge weights combine:
  - delay cost   (extra minutes of arrival delay vs. the original schedule)
  - fare delta   (extra dollars vs. the original fare)
  - cabin penalty (fixed penalty if the alternative doesn't match the
                   original cabin class)

We use networkx's shortest_simple_paths (a generalization of Dijkstra that
ranks *multiple* loopless paths by weight) to return the top 2-3 compliant
alternatives, not just a single best path.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import networkx as nx

DATE_FMT = "%Y-%m-%dT%H:%M:%S"

# Tunable weight coefficients
MINUTES_WEIGHT = 1.0          # cost per minute of extra delay vs. original arrival
FARE_WEIGHT = 0.5             # cost per dollar of fare delta
CABIN_MISMATCH_PENALTY = 150  # flat penalty if cabin class changes


def _parse(dt: str) -> datetime:
    return datetime.strptime(dt, DATE_FMT)


@dataclass
class RankedOption:
    flight: dict
    hotel: dict
    car: dict
    total_weight: float
    delay_minutes: int
    fare_delta: float
    cabin_match: bool

    def to_dict(self) -> dict:
        return {
            "flight": self.flight,
            "hotel": self.hotel,
            "car": self.car,
            "score": round(self.total_weight, 2),
            "delay_minutes": self.delay_minutes,
            "fare_delta": round(self.fare_delta, 2),
            "cabin_match": self.cabin_match,
        }


class ItineraryGraph:
    """Builds and ranks a per-disruption itinerary graph."""

    def __init__(self, original_itinerary: dict, inventory: dict):
        self.original = original_itinerary
        self.inventory = inventory
        self.graph = nx.DiGraph()

    def _route_key(self) -> str:
        f = self.original["flight"]
        return f"{f['origin']}-{f['destination']}"

    def _city(self) -> str:
        return self.original["flight"]["destination"]

    def build(self) -> nx.DiGraph:
        g = self.graph
        route = self._route_key()
        city = self._city()

        flights = self.inventory.get("flights_by_route", {}).get(route, [])
        hotels = self.inventory.get("hotels_by_city", {}).get(city, [])
        cars = self.inventory.get("cars_by_city", {}).get(city, [])

        g.add_node("START")
        g.add_node("END")

        original_arrival = _parse(self.original["flight"]["arrival"])
        original_fare = self.original["flight"]["fare"]
        original_cabin = self.original["flight"]["cabin_class"]

        for i, f in enumerate(flights):
            fnode = ("flight", f["flight_id"])
            g.add_node(fnode, data=f)
            new_arrival = _parse(f["arrival"])
            delay_minutes = max(0, int((new_arrival - original_arrival).total_seconds() // 60))
            fare_delta = max(0.0, f["fare"] - original_fare)
            cabin_match = f["cabin_class"] == original_cabin
            weight = (
                delay_minutes * MINUTES_WEIGHT
                + fare_delta * FARE_WEIGHT
                + (0 if cabin_match else CABIN_MISMATCH_PENALTY)
            )
            g.add_edge("START", fnode, weight=weight)

            for h in hotels:
                # feasible only if hotel check-in is not before the new flight arrives
                checkin = _parse(h["check_in"])
                if checkin < new_arrival:
                    continue
                hnode = ("hotel", h["hotel_id"], f["flight_id"])
                if hnode not in g:
                    g.add_node(hnode, data=h)
                hotel_wait_minutes = max(0, int((checkin - new_arrival).total_seconds() // 60))
                g.add_edge(fnode, hnode, weight=hotel_wait_minutes * 0.1)

                for c in cars:
                    pickup = _parse(c["pickup"])
                    # feasible only if the car can be picked up at/after the
                    # new flight lands (rental counters are at the airport)
                    if pickup < new_arrival:
                        continue
                    cnode = ("car", c["car_id"], h["hotel_id"], f["flight_id"])
                    if cnode not in g:
                        g.add_node(cnode, data=c)
                    g.add_edge(hnode, cnode, weight=1.0)
                    g.add_edge(cnode, "END", weight=0.0)

        return g

    def rank_options(self, top_k: int = 3) -> list[RankedOption]:
        g = self.build()
        if "START" not in g or "END" not in g or not g.has_node("END"):
            return []
        try:
            paths = list(
                itertools.islice(
                    nx.shortest_simple_paths(g, "START", "END", weight="weight"),
                    top_k,
                )
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

        results = []
        original_arrival = _parse(self.original["flight"]["arrival"])
        original_fare = self.original["flight"]["fare"]
        original_cabin = self.original["flight"]["cabin_class"]

        for path in paths:
            flight_node = next(n for n in path if isinstance(n, tuple) and n[0] == "flight")
            hotel_node = next(n for n in path if isinstance(n, tuple) and n[0] == "hotel")
            car_node = next(n for n in path if isinstance(n, tuple) and n[0] == "car")

            flight = g.nodes[flight_node]["data"]
            hotel = g.nodes[hotel_node]["data"]
            car = g.nodes[car_node]["data"]

            total_weight = sum(
                g[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1)
            )
            new_arrival = _parse(flight["arrival"])
            delay_minutes = max(0, int((new_arrival - original_arrival).total_seconds() // 60))
            fare_delta = max(0.0, flight["fare"] - original_fare)
            cabin_match = flight["cabin_class"] == original_cabin

            results.append(
                RankedOption(
                    flight=flight,
                    hotel=hotel,
                    car=car,
                    total_weight=total_weight,
                    delay_minutes=delay_minutes,
                    fare_delta=fare_delta,
                    cabin_match=cabin_match,
                )
            )
        return results


def _minutes(n: int):
    from datetime import timedelta

    return timedelta(minutes=n)
