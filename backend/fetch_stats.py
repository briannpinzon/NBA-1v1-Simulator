import os
import json
import time
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_and_save():
    print("1. Fetching shooting splits from Basketball-Reference...")
    shooting_url = "https://www.basketball-reference.com/leagues/NBA_2024_shooting.html"
    
    # Read HTML tables directly via pandas
    dfs = pd.read_html(shooting_url, storage_options=HEADERS)
    df_shoot = dfs[0]

    # Flatten headers if multi-index
    df_shoot.columns = ['_'.join(c).strip() if isinstance(c, tuple) else c for c in df_shoot.columns]
    
    # Filter repeated header rows inside table
    player_col_shoot = [c for c in df_shoot.columns if 'Player' in c][0]
    df_shoot = df_shoot[df_shoot[player_col_shoot] != 'Player'].copy()

    print("2. Fetching per-100 possessions stats (defense)...")
    time.sleep(3)  # Respect rate-limiting
    per_poss_url = "https://www.basketball-reference.com/leagues/NBA_2024_per_poss.html"
    dfs_poss = pd.read_html(per_poss_url, storage_options=HEADERS)
    df_poss = dfs_poss[0]
    
    df_poss.columns = ['_'.join(c).strip() if isinstance(c, tuple) else c for c in df_poss.columns]
    player_col_poss = [c for c in df_poss.columns if 'Player' in c][0]
    df_poss = df_poss[df_poss[player_col_poss] != 'Player'].copy()

    print("3. Processing and building JSON database...")
    merged = pd.merge(df_shoot, df_poss, left_on=player_col_shoot, right_on=player_col_poss)

    players = {}
    for _, row in merged.iterrows():
        raw_name = str(row[player_col_shoot])
        name = raw_name.replace('*', '').strip()

        try:
            # Safe float converter helper
            def to_float(val, default=0.0):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            # Detect distance columns dynamically
            def get_stat(df_row, pattern):
                matches = [c for c in df_row.index if pattern in c]
                return to_float(df_row[matches[0]]) if matches else 0.0

            players[name] = {
                "name": name,
                "team": str(row.get('Tm_shoot', row.get('Tm_x', 'UNK'))),
                "zones": {
                    "rim": {
                        "freq": get_stat(row, '0-3') if get_stat(row, '0-3') <= 1.0 else get_stat(row, '0-3') / 100.0,
                        "fg_pct": get_stat(row, 'FG%') # general fallback if granular isn't available
                    },
                    "short_mid": {
                        "freq": get_stat(row, '3-10') if get_stat(row, '3-10') <= 1.0 else get_stat(row, '3-10') / 100.0,
                        "fg_pct": 0.45
                    },
                    "long_mid": {
                        "freq": get_stat(row, '16-3P') if get_stat(row, '16-3P') <= 1.0 else get_stat(row, '16-3P') / 100.0,
                        "fg_pct": 0.42
                    },
                    "three_pt": {
                        "freq": get_stat(row, '3P') if get_stat(row, '3P') <= 1.0 else get_stat(row, '3P') / 100.0,
                        "fg_pct": to_float(row.get('3P%_shoot', row.get('3P%_x', 0.35)))
                    }
                },
                "defense": {
                    "stl_per_100": to_float(row.get('STL_poss', row.get('STL_y', 1.5))),
                    "blk_per_100": to_float(row.get('BLK_poss', row.get('BLK_y', 0.8))),
                    "tov_per_100": to_float(row.get('TOV_poss', row.get('TOV_y', 2.0)))
                }
            }
        except Exception:
            continue

    os.makedirs("data", exist_ok=True)
    with open("data/players.json", "w") as f:
        json.dump(players, f, indent=2)

    print(f"\n[Success] Generated stats for {len(players)} players into 'data/players.json'!")

if __name__ == "__main__":
    fetch_and_save()