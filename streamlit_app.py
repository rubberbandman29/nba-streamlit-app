# Re-run the Streamlit script generation due to code execution environment reset.

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playergamelog, commonteamroster
import datetime

st.set_page_config(layout="wide")
st.title("NBA Player Insights – Bettor Dashboard")

# --- Load Teams and Players ---
team_data = teams.get_teams()
team_names = sorted([team['full_name'] for team in team_data])
selected_team = st.selectbox("Select Team", team_names)

team_id = next(team['id'] for team in team_data if team['full_name'] == selected_team)
roster = commonteamroster.CommonTeamRoster(team_id=team_id)
roster_df = roster.get_data_frames()[0]
roster_names = roster_df['PLAYER'].tolist()

all_active_players = [p for p in players.get_players() if p['is_active']]
team_players = [p for p in all_active_players if p['full_name'] in roster_names]
player_names = sorted([p['full_name'] for p in team_players])
selected_player = st.selectbox("Select Player", player_names)

# --- Input Controls ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    selected_line = st.number_input("Over/Under Line", min_value=0.0, value=20.5)
with col2:
    lookback_games = st.slider("Look Back Games", min_value=5, max_value=30, value=15)
with col3:
    season_range = st.selectbox("Seasons to Look Back", list(range(2, 26)), index=0)

# --- Helper Function to Generate Seasons ---
def generate_past_seasons(n):
    base_year = datetime.datetime.now().year
    if datetime.datetime.now().month < 10:
        base_year -= 1
    return [f"{year}-{str(year+1)[-2:]}" for year in range(base_year, base_year - n, -1)]

# --- Load Multi-Season Logs ---
@st.cache_data(show_spinner=True)
def load_multi_season_logs(player_id, seasons):
    frames = []
    for season in seasons:
        try:
            log = playergamelog.PlayerGameLog(player_id=player_id, season=season, season_type_all_star='Regular Season')
            df = log.get_data_frames()[0]
            df['SEASON'] = season
            frames.append(df)
        except:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

seasons_to_load = generate_past_seasons(season_range)
player_id = next(p['id'] for p in team_players if p['full_name'] == selected_player)
df = load_multi_season_logs(player_id, seasons_to_load)

# --- Preprocess Data ---
if df.empty:
    st.warning("No data available for this player across selected seasons.")
    st.stop()

df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
df['OPPONENT'] = df['MATCHUP'].str.extract("vs. (.*)|@ (.*)").bfill(axis=1).iloc[:, 0]
df['HOME'] = df['MATCHUP'].str.contains('vs.')
df['PTS'] = pd.to_numeric(df['PTS'])
df['MIN'] = pd.to_numeric(df['MIN'])
df['PTS_PER_MIN'] = df['PTS'] / df['MIN']
df['OVER_LINE'] = df['PTS'] > selected_line

# Add label with season abbreviation for better x-axis
df['SEASON_LABEL'] = df['SEASON'].str[:4].astype(int) + 1
df['DATE_LABEL'] = df['GAME_DATE'].dt.strftime('%b %d') + " " + df['SEASON_LABEL'].astype(str).str[-2:] + "'"

with col4:
    opponent_options = sorted(df['OPPONENT'].dropna().unique())
    selected_opponent = st.selectbox("Played Against", ["All"] + opponent_options)

# --- Filter Logic ---
if selected_opponent != "All":
    df = df[df['OPPONENT'] == selected_opponent].sort_values('GAME_DATE', ascending=False)
else:
    df = df.sort_values('GAME_DATE', ascending=False).head(lookback_games)

# --- Summary ---
avg_pts = df['PTS'].mean()
avg_min = df['MIN'].mean()
over_rate = df['OVER_LINE'].mean() * 100

st.markdown(f"**{selected_player}** averages **{avg_pts:.1f} PPG** and **{avg_min:.1f} minutes** over the last **{len(df)}** games.")
st.markdown(f"**Over Line Hit Rate:** {over_rate:.0f}% (Line: {selected_line} points)")
if selected_opponent != "All":
    st.markdown(f"*Showing all games against {selected_opponent} across last {season_range} seasons*")

# Visualizations with updated labels follow here (omitted for brevity)
