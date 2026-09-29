"""Simple policy config the agent checks before it's allowed to auto-execute."""
from dataclasses import dataclass


@dataclass
class Policy:
    max_fare_delta: float = 150.0       # dollars
    max_added_delay_minutes: int = 240  # 4 hours
    allow_cabin_downgrade: bool = False
    allow_cabin_upgrade: bool = True     # upgrades are fine, downgrades need approval


DEFAULT_POLICY = Policy()


def within_policy(option, original_cabin: str, policy: Policy = DEFAULT_POLICY) -> tuple[bool, list[str]]:
    """Returns (compliant, list_of_violations)."""
    violations = []
    if option.fare_delta > policy.max_fare_delta:
        violations.append(
            f"fare delta ${option.fare_delta:.2f} exceeds policy max ${policy.max_fare_delta:.2f}"
        )
    if option.delay_minutes > policy.max_added_delay_minutes:
        violations.append(
            f"added delay {option.delay_minutes}min exceeds policy max {policy.max_added_delay_minutes}min"
        )
    if not option.cabin_match:
        new_cabin = option.flight["cabin_class"]
        cabin_rank = {"economy": 0, "business": 1, "first": 2}
        is_upgrade = cabin_rank.get(new_cabin, 0) > cabin_rank.get(original_cabin, 0)
        if is_upgrade and not policy.allow_cabin_upgrade:
            violations.append("cabin upgrade not permitted by policy")
        if not is_upgrade and not policy.allow_cabin_downgrade:
            violations.append(f"cabin downgrade from {original_cabin} to {new_cabin} not permitted")
    return (len(violations) == 0, violations)
