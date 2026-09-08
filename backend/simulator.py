import json
import random

def load_player(name, database_path="data/players.json"):
    with open(database_path, "r") as f:
        db = json.load(f)
    
    # Case-insensitive search match
    for player_name, data in db.items():
        if name.lower() in player_name.lower():
            return data
    raise ValueError(f"Player '{name}' not found in database.")

def sample_shot_zone(offensive_zones):
    """
    Selects a shot zone based on the player's real-world attempt frequency.
    """
    zones = list(offensive_zones.keys())
    weights = [offensive_zones[z].get("freq", 0.1) for z in zones]
    
    # Fallback if frequencies don't sum nicely
    if sum(weights) <= 0:
        return "short_mid"
    
    return random.choices(zones, weights=weights, k=1)[0]

def simulate_possession(offense, defense, score):
    """
    Runs a single 1v1 possession and returns an event dictionary.
    """
    events = []
    
    # 1. Turnover / Steal Check (per-100 normalized rate)
    base_tov_chance = (offense["defense"]["tov_per_100"] / 100.0) * 0.5
    base_stl_chance = (defense["defense"]["stl_per_100"] / 100.0) * 0.5
    turnover_prob = min(max(base_tov_chance + base_stl_chance, 0.03), 0.20)
    
    if random.random() < turnover_prob:
        return {
            "type": "TURNOVER",
            "shooter": offense["name"],
            "defender": defense["name"],
            "zone": None,
            "points": 0,
            "description": f"{defense['name']} strips the ball from {offense['name']}! Turnover."
        }

    # 2. Pick Shot Zone based on player tendencies
    zone = sample_shot_zone(offense["zones"])
    zone_stats = offense["zones"][zone]
    base_fg_pct = zone_stats.get("fg_pct", 0.40)

    # 3. Block Check (rim and mid-range have higher block vulnerabilities)
    block_multiplier = 1.4 if zone in ["rim", "short_mid"] else 0.4
    block_prob = (defense["defense"]["blk_per_100"] / 100.0) * block_multiplier * 0.3
    
    if random.random() < block_prob:
        return {
            "type": "BLOCKED",
            "shooter": offense["name"],
            "defender": defense["name"],
            "zone": zone,
            "points": 0,
            "description": f"{offense['name']} attempts a shot from {zone.replace('_', ' ')}, but {defense['name']} gets a hand on it! Swatted away."
        }

    # 4. Make or Miss
    # 3-pointers are worth 2; 2-pointers are worth 1 (traditional street 1v1 rules)
    points_awarded = 2 if zone == "three_pt" else 1

    if random.random() < base_fg_pct:
        return {
            "type": "MADE",
            "shooter": offense["name"],
            "defender": defense["name"],
            "zone": zone,
            "points": points_awarded,
            "description": f"{offense['name']} hits a {points_awarded}-pointer from {zone.replace('_', ' ')} over {defense['name']}!"
        }
    else:
        return {
            "type": "MISSED",
            "shooter": offense["name"],
            "defender": defense["name"],
            "zone": zone,
            "points": 0,
            "description": f"{offense['name']} clanks the shot from {zone.replace('_', ' ')}."
        }

def run_game(player1_name, player2_name, target_score=11):
    p1 = load_player(player1_name)
    p2 = load_player(player2_name)

    scores = {p1["name"]: 0, p2["name"]: 0}
    play_by_play = []
    
    # Coin flip for first possession
    current_offense, current_defense = (p1, p2) if random.random() > 0.5 else (p2, p1)
    possession_num = 1

    print(f"\n Starting 1v1: {p1['name']} vs. {p2['name']} (First to {target_score}) \n")

    while scores[p1["name"]] < target_score and scores[p2["name"]] < target_score:
        possession_result = simulate_possession(current_offense, current_defense, scores)
        scores[current_offense["name"]] += possession_result["points"]

        # Log event
        event_record = {
            "possession": possession_num,
            "score": dict(scores),
            **possession_result
        }
        play_by_play.append(event_record)

        print(f"[{scores[p1['name']]} - {scores[p2['name']]}] Possession {possession_num}: {possession_result['description']}")

        # Standard street rules: Loser's ball (switch possession every turn)
        current_offense, current_defense = current_defense, current_offense
        possession_num += 1

    winner = p1["name"] if scores[p1["name"]] >= target_score else p2["name"]
    print(f"\n Game Over! {winner} wins {scores[winner]} to {scores[p1['name'] if winner == p2['name'] else p2['name']]}!\n")

    return {
        "winner": winner,
        "final_score": scores,
        "play_by_play": play_by_play
    }

if __name__ == "__main__":
    # Test run between any two players in your database
    run_game("Kawhi Leonard", "Paul George")