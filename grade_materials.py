#!/usr/bin/env python3
"""
Material Balance Grader for Rocket Game
========================================
Analyzes each material's "power" (contribution to range) relative to its cost,
and flags materials that are over- or under-powered for their price tier.

Range formula:  density * (strength + formability) * 100
Budget bonus:   (leftover_budget / 100) * 500  (i.e. every $100 saved = 500 range)

So each material contributes to range via its stats, but also *costs* range
because spending money reduces the leftover budget bonus.
"""

import json
import os

# ── Load config ──────────────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.json")

with open(config_path, "r") as f:
    config_data = json.load(f)

MATERIALS = config_data["MATERIALS"]
SCENARIOS = config_data.get("SCENARIOS", [])

# ── Helpers ──────────────────────────────────────────────────────────────────

STAT_KEYS = ["density", "strength", "temp", "toughness", "formability"]

def stat_power(m):
    """Raw stat contribution to the range formula (single-unit perspective).
    
    In a 5-unit rocket the range is:
        sum(density) * (sum(strength) + sum(formability)) * 100
    
    A single material's *marginal* contribution depends on what else is picked,
    so we use a simplified 'solo power' metric:
        density * (strength + formability) * 100
    This represents the range a unit would produce in isolation.
    """
    return m["density"] * (m["strength"] + m["formability"]) * 100


def budget_range_cost(m):
    """Range you *lose* by spending money on this material instead of keeping
    the budget.  Every $100 spent = 500 range lost."""
    return (m["cost"] / 100) * 500


def net_range_value(m):
    """Net range impact: stat power minus the range you lose from spending."""
    return stat_power(m) - budget_range_cost(m)


def efficiency(m):
    """Stat power per dollar spent."""
    return stat_power(m) / m["cost"] if m["cost"] > 0 else float("inf")


# ── Analysis ─────────────────────────────────────────────────────────────────

def grade_materials():
    print("=" * 90)
    print("MATERIAL BALANCE REPORT")
    print("=" * 90)

    # ── Per-material stats ───────────────────────────────────────────────────
    rows = []
    for m in MATERIALS:
        sp = stat_power(m)
        brc = budget_range_cost(m)
        nrv = net_range_value(m)
        eff = efficiency(m)
        rows.append({
            "name": m["name"],
            "cost": m["cost"],
            "stat_power": sp,
            "budget_cost": brc,
            "net_range": nrv,
            "efficiency": eff,
            **{k: m[k] for k in STAT_KEYS},
        })

    # Sort by net range value descending
    rows.sort(key=lambda r: -r["net_range"])

    avg_net = sum(r["net_range"] for r in rows) / len(rows)
    avg_eff = sum(r["efficiency"] for r in rows) / len(rows)

    # ── Table ────────────────────────────────────────────────────────────────
    header = (
        f"{'Material':<18} {'Cost':>5} │ "
        f"{'D':>2} {'S':>2} {'T':>2} {'Tgh':>3} {'F':>2} │ "
        f"{'StatPwr':>8} {'BudgCost':>9} {'NetRange':>9} │ "
        f"{'Eff':>6} │ Grade"
    )
    print()
    print(header)
    print("─" * len(header))

    for r in rows:
        # Grade: how far from average net range
        deviation = r["net_range"] - avg_net
        abs_dev = abs(deviation)

        if abs_dev < 100:
            grade = "  OK"
        elif deviation > 0:
            if abs_dev > 500:
                grade = "  OP++"  # very overpowered
            else:
                grade = "  OP"
            grade += f" (+{deviation:+.0f})"
        else:
            if abs_dev > 500:
                grade = "  WEAK--"
            else:
                grade = "  WEAK"
            grade += f" ({deviation:+.0f})"

        print(
            f"{r['name']:<18} ${r['cost']:>4} │ "
            f"{r['density']:>2} {r['strength']:>2} {r['temp']:>2} {r['toughness']:>3} {r['formability']:>2} │ "
            f"{r['stat_power']:>8,} {r['budget_cost']:>9,} {r['net_range']:>+9,} │ "
            f"{r['efficiency']:>6.2f} │{grade}"
        )

    print("─" * len(header))
    print(f"{'AVERAGE':<18} {'':>5} │ {'':>2} {'':>2} {'':>2} {'':>3} {'':>2} │ "
          f"{'':>8} {'':>9} {avg_net:>+9,.0f} │ {avg_eff:>6.2f} │")

    # ── Summary / flags ──────────────────────────────────────────────────────
    print()
    print("=" * 90)
    print("BALANCE FLAGS")
    print("=" * 90)

    overpowered = [r for r in rows if r["net_range"] - avg_net > 200]
    underpowered = [r for r in rows if r["net_range"] - avg_net < -200]
    dominated = []

    # Check for strict domination: material A dominates B if A has >=
    # stats in ALL categories AND costs <= B.
    for i, a in enumerate(rows):
        for j, b in enumerate(rows):
            if i == j:
                continue
            a_stats = [a[k] for k in STAT_KEYS]
            b_stats = [b[k] for k in STAT_KEYS]
            if all(av >= bv for av, bv in zip(a_stats, b_stats)) and a["cost"] <= b["cost"]:
                dominated.append((a["name"], b["name"]))

    if overpowered:
        print("\n🟢 OVERPOWERED (too good for their cost):")
        for r in overpowered:
            print(f"   • {r['name']:18s}  cost=${r['cost']:>4}  net_range={r['net_range']:>+,}")
            print(f"     → Consider raising cost or lowering density/strength/formability")

    if underpowered:
        print("\n🔴 UNDERPOWERED (too expensive for their stats):")
        for r in underpowered:
            print(f"   • {r['name']:18s}  cost=${r['cost']:>4}  net_range={r['net_range']:>+,}")
            print(f"     → Consider lowering cost or raising density/strength/formability")

    if dominated:
        print("\n⚠️  DOMINATED MATERIALS (strictly worse than another material):")
        for better, worse in dominated:
            print(f"   • {worse} is dominated by {better} (same or better stats AND cheaper/equal)")

    if not overpowered and not underpowered and not dominated:
        print("\n✅ No major balance issues detected.")

    # ── Scenario-specific analysis ───────────────────────────────────────────
    print()
    print("=" * 90)
    print("SCENARIO-SPECIFIC NOTES")
    print("=" * 90)
    for scenario in SCENARIOS:
        min_temp = scenario.get("MIN_TEMP", 8)
        max_units = scenario.get("MAX_UNITS", 5)
        budget = scenario.get("STARTING_BUDGET", 4500)
        name = scenario.get("name", "Unnamed")
        print(f"\n── {name} (budget=${budget}, min_temp={min_temp}, max_units={max_units}) ──")

        # Which materials are viable for temp requirement?
        # With max_units slots, average temp per slot needed is min_temp / max_units
        avg_temp_needed = min_temp / max_units
        low_temp = [m for m in MATERIALS if m["temp"] < avg_temp_needed]
        high_temp = [m for m in MATERIALS if m["temp"] >= avg_temp_needed + 1]

        if low_temp:
            print(f"  Materials with below-average temp (need avg {avg_temp_needed:.1f}/unit):")
            for m in low_temp:
                print(f"    • {m['name']} (temp={m['temp']}) — using many of these risks heat failure")
        
        # Check which materials can never be afforded in a full loadout
        too_expensive = [m for m in MATERIALS if m["cost"] * max_units > budget]
        if too_expensive:
            print(f"  Too expensive to fill all {max_units} slots:")
            for m in too_expensive:
                total = m["cost"] * max_units
                print(f"    • {m['name']} (${m['cost']}/unit × {max_units} = ${total} > ${budget})")

    # ── Ranking summary ──────────────────────────────────────────────────────
    print()
    print("=" * 90)
    print("RANKING SUMMARY (by net range value)")
    print("=" * 90)
    for i, r in enumerate(rows, 1):
        bar_len = max(0, int((r["net_range"] + 2000) / 100))
        bar = "█" * bar_len
        print(f"  {i:>2}. {r['name']:<18} {r['net_range']:>+6,}  {bar}")


if __name__ == "__main__":
    grade_materials()
