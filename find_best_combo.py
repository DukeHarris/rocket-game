import itertools
import json
import os

# Load config from JSON file
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.json")

with open(config_path, "r") as f:
    config_data = json.load(f)

MATERIALS = config_data["MATERIALS"]
SCENARIOS = config_data.get("SCENARIOS", [])

def calculate_stats(combo, min_temp, starting_budget):
    units = len(combo)
    cost = sum(m["cost"] for m in combo)
    temp = sum(m["temp"] for m in combo)
    toughness = sum(m["toughness"] for m in combo)
    density = sum(m["density"] for m in combo)
    strength = sum(m["strength"] for m in combo)
    formability = sum(m["formability"] for m in combo)
    
    # Base range
    range_val = density * (strength + formability) * 100
    
    # Apply leftover budget to range (100$ = 500 extra range)
    leftover = starting_budget - cost
    range_val += (leftover / 100) * 500
    
    heat_fail = temp < min_temp
    success_chance = max(0.0, min(100.0, (toughness - 4) * 10))
    
    final_range = range_val
    if heat_fail:
        final_range = 0
        
    return {
        "cost": cost,
        "range": final_range,
        "temp": temp,
        "toughness": toughness,
        "heat_fail": heat_fail,
        "success_chance": success_chance,
        "density": density,
        "strength": strength,
        "formability": formability
    }

def find_best_for_scenario(scenario):
    max_units = scenario.get("MAX_UNITS", 5)
    starting_budget = scenario.get("STARTING_BUDGET", 4500)
    min_temp = scenario.get("MIN_TEMP", 8)
    
    print(f"\n=======================================================")
    print(f"SCENARIO: {scenario.get('name', 'Unnamed')}")
    print(f"Budget: ${starting_budget} | Min Temp: {min_temp}")
    print(f"=======================================================")
    
    all_combos = []
    for i in range(1, max_units + 1):
        all_combos.extend(list(itertools.combinations_with_replacement(MATERIALS, i)))
    
    valid_combos = []
    for combo in all_combos:
        stats = calculate_stats(combo, min_temp, starting_budget)
        if stats["cost"] <= starting_budget:
            valid_combos.append({
                "combo": combo,
                "stats": stats
            })
    
    # Sort by range (descending), then cost (ascending)
    valid_combos.sort(key=lambda x: (-x["stats"]["range"], x["stats"]["cost"]))
    
    print(f"Total valid combinations (cost <= {starting_budget}): {len(valid_combos)}")
    if not valid_combos:
        print("No valid combinations found for this scenario.")
        return
        
    print("\n--- TOP 10 COMBINATIONS ---")
    for i, item in enumerate(valid_combos[:10]):
        combo = item["combo"]
        stats = item["stats"]
        
        # Count materials
        counts = {}
        for m in combo:
            counts[m["name"]] = counts.get(m["name"], 0) + 1
        
        counts_str = ", ".join([f"{v}x {k}" for k, v in counts.items()])
        
        print(f"{i+1}. Range: {stats['range']:,} | Cost: ${stats['cost']} | Stats: T:{stats['temp']}, Tgh:{stats['toughness']}, D:{stats['density']}, S:{stats['strength']}, F:{stats['formability']}")
        print(f"   Materials: {counts_str}")
        if stats["success_chance"] < 100:
            print(f"   (WARNING: {100 - stats['success_chance']:.0f}% chance of explosion due to low toughness)")
        print("-" * 20)

if __name__ == "__main__":
    if SCENARIOS:
        for s in SCENARIOS:
            find_best_for_scenario(s)
    else:
        print("No scenarios found in config.json")
