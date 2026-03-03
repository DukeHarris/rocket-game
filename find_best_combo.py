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

def calculate_stats(combo, min_temp, min_toughness):
    units = len(combo)
    cost = sum(m["cost"] for m in combo)
    temp = sum(m["temp"] for m in combo)
    toughness = sum(m["toughness"] for m in combo)
    density = sum(m["density"] for m in combo)
    strength = sum(m["strength"] for m in combo)
    formability = sum(m["formability"] for m in combo)
    
    # Base range
    range_val = density * (strength + formability) * 100
    
    heat_fail = temp < min_temp
    vibration_fail = toughness < min_toughness
    
    final_range = range_val
    if heat_fail:
        final_range = 0
    elif vibration_fail:
        final_range = final_range // 2
        
    return {
        "cost": cost,
        "range": final_range,
        "temp": temp,
        "toughness": toughness,
        "heat_fail": heat_fail,
        "vibration_fail": vibration_fail,
        "density": density,
        "strength": strength,
        "formability": formability
    }

def find_best_for_scenario(scenario):
    max_units = scenario.get("MAX_UNITS", 5)
    max_cost = scenario.get("MAX_COST", 2500)
    min_temp = scenario.get("MIN_TEMP", 8)
    min_toughness = scenario.get("MIN_TOUGHNESS", 13)
    
    print(f"\n=======================================================")
    print(f"SCENARIO: {scenario.get('name', 'Unnamed')}")
    print(f"Budget: ${max_cost} | Min Temp: {min_temp} | Min Toughness: {min_toughness}")
    print(f"=======================================================")
    
    all_combos = list(itertools.combinations_with_replacement(MATERIALS, max_units))
    
    valid_combos = []
    for combo in all_combos:
        stats = calculate_stats(combo, min_temp, min_toughness)
        if stats["cost"] <= max_cost:
            valid_combos.append({
                "combo": combo,
                "stats": stats
            })
    
    # Sort by range (descending), then cost (ascending)
    valid_combos.sort(key=lambda x: (-x["stats"]["range"], x["stats"]["cost"]))
    
    print(f"Total valid combinations (cost <= {max_cost}): {len(valid_combos)}")
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
        if stats["vibration_fail"]:
            print("   (WARNING: Toughness below threshold, range halved)")
        print("-" * 20)

if __name__ == "__main__":
    if SCENARIOS:
        for s in SCENARIOS:
            find_best_for_scenario(s)
    else:
        print("No scenarios found in config.json")
