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

# Get roster using commonteamroster endpoint
roster = commonteamroster.CommonTeamRoster(team_id=team_id)
roster_df = roster.get_data_frames()[0]
roster_names = roster_df['PLAYER'].tolist()

# Get all active players and filter by roster names
all_active_players = [p for p in players.get_players() if p['is_active']]
team_players = [p for p in all_active_players if p['full_name'] in roster_names]
player_names = sorted([p['full_name'] for p in team_players])
selected_player = st.selectbox("Select Player", player_names)

selected_line = st.number_input("Enter Over/Under Line for Points", min_value=0.0, value=20.5)
lookback_games = st.slider("Look Back Games", min_value=5, max_value=30, value=15, step=1)

# Load player data
player_id = next(p['id'] for p in team_players if p['full_name'] == selected_player)
gamelog = playergamelog.PlayerGameLog(player_id=player_id, season_type_all_star='Regular Season')
df = gamelog.get_data_frames()[0]

# Preprocess
df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
df = df[['GAME_DATE', 'MATCHUP', 'PTS', 'MIN']]
df['OPPONENT'] = df['MATCHUP'].str.extract("vs. (.*)|@ (.*)").bfill(axis=1).iloc[:, 0]
df['HOME'] = df['MATCHUP'].str.contains('vs.')
df['PTS'] = pd.to_numeric(df['PTS'])
df['MIN'] = pd.to_numeric(df['MIN'])
df['PTS_PER_MIN'] = df['PTS'] / df['MIN']
df['OVER_LINE'] = df['PTS'] > selected_line

opponents = sorted(df['OPPONENT'].unique())
selected_opponent = st.selectbox("Played Against (Opponent)", ["All"] + opponents)

if selected_opponent != "All":
    df = df[df['OPPONENT'] == selected_opponent].sort_values('GAME_DATE', ascending=False).head(5)
else:
    df = df.sort_values('GAME_DATE', ascending=False).head(lookback_games)

# Insights
avg_pts = df['PTS'].mean()
avg_min = df['MIN'].mean()
over_rate = df['OVER_LINE'].mean() * 100

st.markdown(f"**{selected_player}** averages **{avg_pts:.1f} PPG** and **{avg_min:.1f} minutes** over the last **{len(df)}** games.")
st.markdown(f"**Over Line Hit Rate:** {over_rate:.0f}% (Line: {selected_line} points)")
if selected_opponent != "All":
    st.markdown(f"*Filtered by last 5 games against {selected_opponent}*")

# The rest of the code with the two-column visualizations and notes follows below...
