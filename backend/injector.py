"""
Standalone disruption injector.

Fires fake flight-status webhooks at a running instance of the API so you
can trigger the live demo from a terminal instead of the UI button.

Usage:
    python injector.py single [--pax-id PAX-1001]
    python injector.py storm [--count 12]
"""
import argparse
import sys

import requests

BASE_URL = "http://localhost:8000"


def fire_single(pax_id: str | None):
    resp = requests.post(
        f"{BASE_URL}/inject/single", params={"pax_id": pax_id} if pax_id else {}
    )
    resp.raise_for_status()
    print(resp.json())


def fire_storm(count: int):
    resp = requests.post(f"{BASE_URL}/inject/storm", params={"count": count})
    resp.raise_for_status()
    data = resp.json()
    print(f"Storm fired: {data['fired']} disruption events")


def main():
    parser = argparse.ArgumentParser(description="Fire disruption events at the concierge API")
    sub = parser.add_subparsers(dest="mode", required=True)

    single = sub.add_parser("single", help="fire one disruption event")
    single.add_argument("--pax-id", default=None)

    storm = sub.add_parser("storm", help="fire many disruption events in quick succession")
    storm.add_argument("--count", type=int, default=12)

    args = parser.parse_args()
    if args.mode == "single":
        fire_single(args.pax_id)
    elif args.mode == "storm":
        fire_storm(args.count)


if __name__ == "__main__":
    main()
