"""Tank logic for fresh, grey, and black water tanks with stream-based routing."""

from __future__ import annotations

from collections import defaultdict

FRESH_TANK_CAPACITY_GALLONS = 60.0
GREY_TANK_CAPACITY_GALLONS = 60.0
BLACK_TANK_CAPACITY_GALLONS = 40.0

GREY_SPLIT = 0.5
BLACK_SPLIT = 0.5

DAILY_USAGE_GALLONS = 15.0

VALID_BANKS: frozenset[str] = frozenset({"fresh", "grey", "black"})
VALID_INPUT_POLICIES: frozenset[str] = frozenset({"weighted", "any_active"})


def _default_routing_rules() -> dict[str, dict]:
    return {
        "fresh_water_out": {
            "priority": 0,
            "input_policy": "weighted",
            "inputs": [],
            "outputs": [
                {"bank": "grey", "proportion": GREY_SPLIT},
                {"bank": "black", "proportion": BLACK_SPLIT},
            ],
            "source_bank": "fresh",
        },
        "city_water_in": {
            "priority": 0,
            "input_policy": "weighted",
            "inputs": [],
            "outputs": [
                {"bank": "grey", "proportion": GREY_SPLIT},
                {"bank": "black", "proportion": BLACK_SPLIT},
            ],
            "source_bank": None,
        },
    }


_stream_totals: dict[str, float] = {
    "fresh_water_out": 0.0,
    "city_water_in": 0.0,
}
_routing_rules: dict[str, dict] = _default_routing_rules()
_fresh_gallons_used: float = 0.0
_city_gallons_used: float = 0.0


def _normalize_inputs(stream_id: str, rule: dict) -> list[dict]:
    normalized_inputs: list[dict] = []
    raw_inputs = rule.get("inputs", [])
    if not isinstance(raw_inputs, list):
        raise ValueError(f"inputs must be a list for stream '{stream_id}'")

    for item in raw_inputs:
        if isinstance(item, str):
            normalized_inputs.append({"stream": item, "proportion": None})
            continue
        if not isinstance(item, dict):
            raise ValueError(f"invalid input entry for stream '{stream_id}'")
        source_stream = str(item.get("stream", "")).strip()
        if not source_stream:
            raise ValueError(f"input stream missing for stream '{stream_id}'")
        proportion = item.get("proportion")
        if proportion is not None:
            proportion = float(proportion)
            if proportion < 0:
                raise ValueError(f"input proportion must be >= 0 for stream '{stream_id}'")
        normalized_inputs.append({"stream": source_stream, "proportion": proportion})
    return normalized_inputs


def _normalize_outputs(stream_id: str, rule: dict) -> list[dict]:
    outputs = rule.get("outputs", [])
    if not isinstance(outputs, list):
        raise ValueError(f"outputs must be a list for stream '{stream_id}'")
    normalized_outputs: list[dict] = []
    for output in outputs:
        if not isinstance(output, dict):
            raise ValueError(f"invalid output entry for stream '{stream_id}'")
        bank = str(output.get("bank", "")).strip().lower()
        if bank not in VALID_BANKS:
            raise ValueError(f"unknown output bank '{bank}' for stream '{stream_id}'")
        proportion = float(output.get("proportion", 0.0))
        if proportion < 0:
            raise ValueError(f"output proportion must be >= 0 for stream '{stream_id}'")
        normalized_outputs.append({"bank": bank, "proportion": proportion})
    if normalized_outputs:
        total = sum(item["proportion"] for item in normalized_outputs)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"output proportions must sum to 1.0 for stream '{stream_id}'")
    return normalized_outputs


def _normalize_routing(routing_rules: dict[str, dict]) -> dict[str, dict]:
    if not isinstance(routing_rules, dict):
        raise ValueError("routing_rules must be a dict")

    normalized: dict[str, dict] = {}
    for stream_id, rule in routing_rules.items():
        sid = str(stream_id).strip()
        if not sid:
            raise ValueError("stream_id must not be empty")
        if not isinstance(rule, dict):
            raise ValueError(f"rule for '{sid}' must be a dict")

        policy = str(rule.get("input_policy", "weighted")).strip().lower()
        if policy not in VALID_INPUT_POLICIES:
            raise ValueError(f"unknown input_policy '{policy}' for stream '{sid}'")

        source_bank = rule.get("source_bank")
        if source_bank is not None:
            source_bank = str(source_bank).strip().lower()
            if source_bank not in VALID_BANKS:
                raise ValueError(f"unknown source_bank '{source_bank}' for stream '{sid}'")

        normalized[sid] = {
            "priority": int(rule.get("priority", 0)),
            "input_policy": policy,
            "inputs": _normalize_inputs(sid, rule),
            "outputs": _normalize_outputs(sid, rule),
            "source_bank": source_bank,
        }

    for stream_id, rule in normalized.items():
        for source in rule["inputs"]:
            source_stream = source["stream"]
            if source_stream not in normalized:
                raise ValueError(
                    f"unknown input stream '{source_stream}' referenced by '{stream_id}'"
                )

    graph: dict[str, list[str]] = {
        stream_id: [source["stream"] for source in rule["inputs"]]
        for stream_id, rule in normalized.items()
    }
    visited: set[str] = set()
    stack: set[str] = set()

    def _dfs(node: str) -> None:
        if node in stack:
            raise ValueError(f"routing cycle detected at '{node}'")
        if node in visited:
            return
        stack.add(node)
        for parent in graph.get(node, []):
            _dfs(parent)
        stack.remove(node)
        visited.add(node)

    for stream in graph:
        _dfs(stream)

    return normalized


def set_flow_routing(routing_rules: dict[str, dict]) -> None:
    """Set stream routing rules after validation."""
    global _routing_rules
    _routing_rules = _normalize_routing(routing_rules)
    for stream_id in _routing_rules:
        _stream_totals.setdefault(stream_id, 0.0)


def update_from_stream(stream_id: str, total_gallons_used: float) -> None:
    """Update internal state from a configured stream's cumulative reading."""
    if not stream_id:
        return
    global _fresh_gallons_used, _city_gallons_used
    total = max(0.0, float(total_gallons_used))
    _stream_totals[stream_id] = total
    if stream_id == "fresh_water_out":
        _fresh_gallons_used = total
    elif stream_id == "city_water_in":
        _city_gallons_used = total


def update_from_flow_meter(total_gallons_used: float) -> None:
    """Backward-compatible fresh water update."""
    update_from_stream("fresh_water_out", total_gallons_used)


def update_from_city_water_meter(total_gallons_used: float) -> None:
    """Backward-compatible city water update."""
    update_from_stream("city_water_in", total_gallons_used)


def _allocate_inputs(
    stream_total: float,
    rule: dict,
    source_available: dict[str, float],
) -> tuple[float, dict[str, float]]:
    inputs = rule["inputs"]
    if not inputs:
        return stream_total, {}

    available = {
        item["stream"]: max(0.0, source_available.get(item["stream"], 0.0))
        for item in inputs
    }
    total_available = sum(available.values())
    if total_available <= 0:
        return 0.0, {}

    alloc_total = min(stream_total, total_available)
    policy = rule["input_policy"]
    if policy == "any_active":
        weights = available
    else:
        weighted: dict[str, float] = {}
        for item in inputs:
            src = item["stream"]
            proportion = item["proportion"]
            weighted[src] = max(0.0, float(proportion)) if proportion is not None else 0.0
        if sum(weighted.values()) <= 0:
            weights = available
        else:
            weights = weighted

    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        return 0.0, {}

    allocations: dict[str, float] = {}
    remaining = alloc_total
    ordered_sources = [item["stream"] for item in inputs]
    for idx, src in enumerate(ordered_sources):
        if remaining <= 0:
            break
        max_for_src = available[src]
        if max_for_src <= 0:
            continue
        if idx == len(ordered_sources) - 1:
            target = remaining
        else:
            target = alloc_total * (weights[src] / weight_sum)
        amount = min(max_for_src, max(0.0, target), remaining)
        allocations[src] = amount
        remaining -= amount

    if remaining > 0:
        for src in ordered_sources:
            if remaining <= 0:
                break
            spare = available[src] - allocations.get(src, 0.0)
            if spare <= 0:
                continue
            add = min(spare, remaining)
            allocations[src] = allocations.get(src, 0.0) + add
            remaining -= add

    used_total = sum(allocations.values())
    return used_total, allocations


def _compute_water_state() -> dict[str, float]:
    source_available = {sid: total for sid, total in _stream_totals.items()}
    effective_stream_totals: dict[str, float] = {
        sid: max(0.0, total) for sid, total in _stream_totals.items()
    }
    stream_claims: dict[str, float] = defaultdict(float)
    bank_totals: dict[str, float] = {"fresh": 0.0, "grey": 0.0, "black": 0.0}

    override_streams = [
        (sid, rule)
        for sid, rule in _routing_rules.items()
        if rule.get("inputs")
    ]
    override_streams.sort(key=lambda item: item[1]["priority"], reverse=True)

    for stream_id, rule in override_streams:
        stream_total = max(0.0, _stream_totals.get(stream_id, 0.0))
        used_total, allocations = _allocate_inputs(stream_total, rule, source_available)
        effective_stream_totals[stream_id] = used_total
        for src, amount in allocations.items():
            stream_claims[src] += amount
            source_available[src] = max(0.0, source_available[src] - amount)
            src_bank = _routing_rules.get(src, {}).get("source_bank")
            if src_bank in VALID_BANKS:
                bank_totals[src_bank] -= amount

    for stream_id, claimed in stream_claims.items():
        effective_stream_totals[stream_id] = max(
            0.0, _stream_totals.get(stream_id, 0.0) - claimed
        )

    for stream_id, rule in _routing_rules.items():
        stream_total = max(0.0, effective_stream_totals.get(stream_id, 0.0))
        source_bank = rule.get("source_bank")
        if source_bank in VALID_BANKS and not rule.get("inputs"):
            bank_totals[source_bank] -= stream_total
        for output in rule.get("outputs", []):
            bank_totals[output["bank"]] += stream_total * output["proportion"]

    fresh_level = min(
        FRESH_TANK_CAPACITY_GALLONS,
        max(0.0, FRESH_TANK_CAPACITY_GALLONS + bank_totals["fresh"]),
    )
    grey_level = min(GREY_TANK_CAPACITY_GALLONS, max(0.0, bank_totals["grey"]))
    black_level = min(BLACK_TANK_CAPACITY_GALLONS, max(0.0, bank_totals["black"]))

    return {
        "fresh": round(fresh_level, 4),
        "grey": round(grey_level, 4),
        "black": round(black_level, 4),
    }


def get_fresh_level() -> dict:
    state = _compute_water_state()
    remaining = state["fresh"]
    percent = (remaining / FRESH_TANK_CAPACITY_GALLONS) * 100.0
    return {
        "capacity_gallons": FRESH_TANK_CAPACITY_GALLONS,
        "current_gallons": round(remaining, 2),
        "percent_full": round(percent, 1),
        "healthy": percent > 20.0,
    }


def get_grey_level() -> dict:
    state = _compute_water_state()
    accumulated = state["grey"]
    percent = (accumulated / GREY_TANK_CAPACITY_GALLONS) * 100.0
    return {
        "capacity_gallons": GREY_TANK_CAPACITY_GALLONS,
        "current_gallons": round(accumulated, 2),
        "percent_full": round(percent, 1),
        "healthy": percent < 80.0,
    }


def get_black_level() -> dict:
    state = _compute_water_state()
    accumulated = state["black"]
    percent = (accumulated / BLACK_TANK_CAPACITY_GALLONS) * 100.0
    return {
        "capacity_gallons": BLACK_TANK_CAPACITY_GALLONS,
        "current_gallons": round(accumulated, 2),
        "percent_full": round(percent, 1),
        "healthy": percent < 80.0,
    }


def get_water_days_remaining() -> float | None:
    if DAILY_USAGE_GALLONS <= 0:
        return None

    fresh = get_fresh_level()
    grey = get_grey_level()
    black = get_black_level()

    fresh_days = fresh["current_gallons"] / DAILY_USAGE_GALLONS

    grey_space = grey["capacity_gallons"] - grey["current_gallons"]
    grey_days = grey_space / (DAILY_USAGE_GALLONS * GREY_SPLIT)

    black_space = black["capacity_gallons"] - black["current_gallons"]
    black_days = black_space / (DAILY_USAGE_GALLONS * BLACK_SPLIT)

    return round(min(fresh_days, grey_days, black_days), 1)
