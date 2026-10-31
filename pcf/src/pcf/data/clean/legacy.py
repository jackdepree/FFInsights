"""The old player-slot cleaning, copied from `old/code/Fatigue_Model_Prod.ipynb` (cells 1-4).

This is the faithful copy (step 1 of OLD_INVENTORY.md's copy, test, improve). It's kept as the
benchmark the improved functions are measured against, and golden tests check it still equals the
notebook. Don't fix anything here: improvements live in `players`, `depth_charts` and `slots`.

The only change from the notebook: the two `warnings.filterwarnings('ignore')` lines are gone.
They silenced warnings for the whole process and didn't affect any output.

Known problems, kept on purpose (cleaning-port exploration and results):
- Players missing from that week's depth chart are labelled 'special' (F4).
- Depth order is a cumulative mean in file order, which isn't chronological (F7).
- Player lists are cut at 11 a side, and padding slots become a player called 'None' (F10).
"""

import numpy as np
import pandas as pd


def pivot_wide_both_sides(data):

    # Filter for valid play types
    data = data[data["play_type"].isin(["run", "pass"])].copy()

    # Sort for consistency
    data = data.sort_values(["game_id", "play_id"])

    # Helper function to expand player columns
    def expand_player_col(df, col_name):
        side = col_name.split("_")[0]  # offense or defense

        # Fill missing with empty string to allow split
        players_split = df[col_name].fillna("").str.split(";")

        # Pad each list to exactly 11 players (or truncate)
        players_list = players_split.apply(lambda lst: (lst + [None] * 11)[:11])

        # Convert to DataFrame
        players_df = pd.DataFrame(
            players_list.tolist(), columns=[f"{side}_player_{i + 1}" for i in range(11)]
        )

        return players_df

    # Expand offense and defense player columns
    offense_wide = expand_player_col(data, "offense_players")
    defense_wide = expand_player_col(data, "defense_players")

    # Concatenate expanded columns with the original DataFrame
    pbp_wide = pd.concat([data.reset_index(drop=True), offense_wide, defense_wide], axis=1)

    # Drop potential duplicates
    pbp_wide = pbp_wide.drop_duplicates(subset=["game_id", "play_id"])

    # Drop rows with NaN in offense_players or defense_players
    pbp_wide = pbp_wide.dropna(subset=["offense_players", "defense_players"])

    return pbp_wide


def clean_depth_charts(depth_charts):
    # Remove duplicates on season, club_code, week, gsis_id
    depth_charts_copy = depth_charts.drop_duplicates(
        subset=["season", "club_code", "week", "gsis_id"]
    )
    depth_charts_copy = depth_charts_copy[
        depth_charts_copy["formation"].str.contains("Offense|Defense", regex=True)
    ].copy()

    # Replace 'T' and 'G' in 'position' with the value from 'depth_position'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].isin(["T", "G"]),
        depth_charts_copy["depth_position"],
        depth_charts_copy["position"],
    )

    # Replace 'LOT' in 'position'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].isin(["LOT"]), "LT", depth_charts_copy["position"]
    )

    # Replace 'ROT' in 'position'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].isin(["ROT"]), "RT", depth_charts_copy["position"]
    )

    # Replace 'RDE' and 'LDE'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].isin(["RDE", "LDE"]), "DE", depth_charts_copy["position"]
    )

    # Replace 'RDT' and 'LDT'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].isin(["RDT", "LDT"]), "DT", depth_charts_copy["position"]
    )

    # Replace 'DB' with 'CB'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].isin(["LB"]), "MLB", depth_charts_copy["position"]
    )

    # Replace 'K', 'P', 'LS'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].isin(["\n ", "K", "P", "LS"]),
        "special",
        depth_charts_copy["position"],
    )

    # Replace 'DB' with 'CB'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].isin(["DB"]), "CB", depth_charts_copy["position"]
    )

    # Replace '\n'
    depth_charts_copy["position"] = np.where(
        depth_charts_copy["position"].str.contains(" "), "special", depth_charts_copy["position"]
    )

    # Replace 'SBBYE'
    depth_charts_copy["week"] = np.where(
        depth_charts_copy["week"].isna(), "23", depth_charts_copy["week"]
    )

    # Seniority counter
    depth_charts_copy["seniority"] = depth_charts_copy.groupby(["gsis_id"]).cumcount() + 1

    # Cumulative sum of depth_team per gsis_team
    depth_charts_copy["depth_team"] = depth_charts_copy["depth_team"].astype(int)
    depth_charts_copy["depth_team_sum"] = depth_charts_copy.groupby(["gsis_id"])[
        "depth_team"
    ].cumsum()

    # Cumulative mean of depth_team per gsis_team
    depth_charts_copy["depth_team_mean"] = (
        depth_charts_copy["depth_team_sum"] / depth_charts_copy["seniority"]
    )

    # Sort by season, club_code, week, position, depth_team_mean
    depth_charts_copy = depth_charts_copy.sort_values(["depth_team_mean"], ascending=True)

    # Cumulative count of season, week, club_team, position
    depth_charts_copy["depth_team_estimator"] = (
        depth_charts_copy.groupby(["season", "week", "club_code", "position"]).cumcount() + 1
    )

    # depth_charts_copy['depth_team_estimator'] = depth_charts_copy['depth_team_estimator'].astype(int)
    depth_charts_copy["depth_team_estimator"] = depth_charts_copy["depth_team_estimator"].astype(
        str
    )

    # Define position_label
    depth_charts_copy["position_label"] = depth_charts_copy["position"] + depth_charts_copy[
        "depth_team_estimator"
    ].astype(str)
    depth_charts_copy["season"] = depth_charts_copy["season"].astype(int)
    depth_charts_copy["gsis_id"] = depth_charts_copy["gsis_id"].astype(str)
    depth_charts_copy["week"] = (
        depth_charts_copy["week"].astype(str).str.replace(".0", "", regex=False).astype(int)
    )

    return depth_charts_copy


def pivot_long_both_sides(pbp_wide, depth_charts):

    # Clean depth charts
    depth_charts_clean = clean_depth_charts(depth_charts)

    # Combine offense and defense player columns into long format
    long_df = pd.wide_to_long(
        pbp_wide.reset_index(),
        stubnames=["offense_player", "defense_player"],
        i=["index"],  # preserves play-wise indexing
        j="player_number",
        sep="_",
        suffix="\\d+",
    ).reset_index()

    # Stack both sides
    offense_df = long_df[
        ["game_id", "play_id", "offense_player", "player_number", "season", "week"]
    ].copy()
    offense_df.rename(columns={"offense_player": "player_id"}, inplace=True)

    defense_df = long_df[
        ["game_id", "play_id", "defense_player", "player_number", "season", "week"]
    ].copy()
    defense_df.rename(columns={"defense_player": "player_id"}, inplace=True)

    all_long = pd.concat([offense_df, defense_df], ignore_index=True)

    # Deduplicate depth_charts BEFORE merge to prevent cartesian product
    depth_charts_dedup = depth_charts_clean.drop_duplicates(subset=["season", "week", "gsis_id"])[
        ["season", "week", "gsis_id", "position_label", "full_name"]
    ]

    # Merge with depth charts
    all_long["player_id"] = all_long["player_id"].astype(str).str.strip()
    depth_charts_dedup["gsis_id"] = depth_charts_dedup["gsis_id"].astype(str).str.strip()
    merged = all_long.merge(
        depth_charts_dedup,
        left_on=["season", "week", "player_id"],
        right_on=["season", "week", "gsis_id"],
        how="left",
    )

    # Drop unnecessary
    merged = merged.drop(columns=["gsis_id"])

    # Replace the dropna with a fillna for debugging
    merged["position_label"] = merged["position_label"].fillna("special")

    # Filter nulls
    merged = merged.dropna(subset=["player_id", "position_label"])

    # Deduplicate on the final result
    merged = merged.drop_duplicates(subset=["game_id", "play_id", "player_id"])

    return merged.sort_values(["game_id", "play_id"])


def get_position_groups(_):
    """
    Returns a dictionary with keys for 'offense', 'defense', and position groups,
    and values as lists of hard-coded position_labels.
    Ignores the input and uses a fixed list.
    """
    position_labels = [
        "C1",
        "C2",
        "C3",
        "C4",
        "CB1",
        "CB2",
        "CB3",
        "CB4",
        "CB5",
        "CB6",
        "CB7",
        "CB8",
        "DE1",
        "DE2",
        "DE3",
        "DE4",
        "DE5",
        "DE6",
        "DE7",
        "DT1",
        "DT2",
        "DT3",
        "DT4",
        "DT5",
        "DT6",
        "DT7",
        "FB1",
        "FB2",
        "FS1",
        "FS2",
        "FS3",
        "FS4",
        "ILB1",
        "ILB2",
        "ILB3",
        "ILB4",
        "ILB5",
        "ILB6",
        "LG1",
        "LG2",
        "LG3",
        "LT1",
        "LT2",
        "LT3",
        "MLB1",
        "MLB2",
        "MLB3",
        "NT1",
        "NT2",
        "NT3",
        "OLB1",
        "OLB2",
        "OLB3",
        "OLB4",
        "OLB5",
        "OLB6",
        "QB1",
        "QB2",
        "QB3",
        "RB1",
        "RB2",
        "RB3",
        "RB4",
        "RB5",
        "RG1",
        "RG2",
        "RG3",
        "RT1",
        "RT2",
        "RT3",
        "SS1",
        "SS2",
        "SS3",
        "SS4",
        "SS5",
        "TE1",
        "TE2",
        "TE3",
        "TE4",
        "TE5",
        "WR1",
        "WR2",
        "WR3",
        "WR4",
        "WR5",
        "WR6",
        "WR7",
        "special1",
    ]

    group_dict = {
        "offense": [
            p
            for p in position_labels
            if any(
                p.startswith(x) for x in ["QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT"]
            )
        ],
        "defense": [
            p
            for p in position_labels
            if any(
                p.startswith(x) for x in ["DE", "DT", "NT", "OLB", "ILB", "MLB", "CB", "FS", "SS"]
            )
        ],
        "qbs": [p for p in position_labels if p.startswith("QB")],
        "rbs": [p for p in position_labels if p.startswith("RB") or p.startswith("FB")],
        "tes": [p for p in position_labels if p.startswith("TE")],
        "wrs": [p for p in position_labels if p.startswith("WR")],
        "ol": [
            p
            for p in position_labels
            if p.startswith(("LT", "LG", "C", "RG", "RT")) and not p.startswith("CB")
        ],
        "dl": [p for p in position_labels if p.startswith(("DE", "DT", "NT"))],
        "lbs": [p for p in position_labels if p.startswith(("OLB", "ILB", "MLB"))],
        "cbs": [p for p in position_labels if p.startswith("CB")],
        "ss": [p for p in position_labels if p.startswith(("SS", "FS"))],
        "special": [p for p in position_labels if p.startswith("special")],
    }

    return group_dict
