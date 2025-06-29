import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playergamelog
import datetime

st.set_page_config(layout="wide")
st.title("NBA Player Stats – Bettor Insights Dashboard")

# --- Load Teams and Players ---
team_data = teams.get_teams()
team_names = sorted([team['full_name'] for team in team_data])
selected_team = st.selectbox("Select Team", team_names)

team_id = next(team['id'] for team in team_data if team['full_name'] == selected_team)
team_players = [p for p in players.get_players() if p['is_active'] and p['team_id'] == team_id]
player_names = sorted([p['full_name'] for p in team_players])
selected_player = st.selectbox("Select Player", player_names)

selected_line = st.number_input("Enter Over/Under Line for Points", min_value=0.0, value=20.5)

# Load player ID and game log
player_id = next(p['id'] for p in team_players if p['full_name'] == selected_player)
now = datetime.datetime.now()
season_start = now.year - 1 if now.month < 10 else now.year
season_str = f"{season_start}-{str(season_start + 1)[-2:]}"
gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season_str, season_type_all_star='Regular Season')
df = gamelog.get_data_frames()[0]
df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
df = df[['GAME_DATE', 'MATCHUP', 'PTS', 'MIN']]
df = df.dropna().sort_values('GAME_DATE', ascending=False)
df['OPPONENT'] = df['MATCHUP'].str.extract("vs. (.*)|@ (.*)").bfill(axis=1).iloc[:, 0]
df['HOME'] = df['MATCHUP'].str.contains('vs.')
df['PTS'] = pd.to_numeric(df['PTS'])
df['MIN'] = pd.to_numeric(df['MIN'])
df['PTS_PER_MIN'] = df['PTS'] / df['MIN']
df['OVER_LINE'] = df['PTS'] > selected_line

opponents = sorted(df['OPPONENT'].unique())
selected_opponent = st.selectbox("Filter: Games Played Against", ["All"] + opponents)

if selected_opponent != "All":
    df = df[df['OPPONENT'] == selected_opponent]

# Display key stats
avg_pts = df['PTS'].mean()
over_rate = df['OVER_LINE'].mean() * 100

st.markdown(f"**{selected_player}** has averaged **{avg_pts:.1f} PPG** in the selected games.")
st.markdown(f"**Hit Rate:** {over_rate:.0f}% over the line of {selected_line} points.")

# Plot
col1, col2 = st.columns(2)
with col1:
    st.subheader("Points vs Minutes (Scatter)")
    fig1, ax1 = plt.subplots()
    days_since = (df['GAME_DATE'].max() - df['GAME_DATE']).dt.days
    sc = ax1.scatter(df['MIN'], df['PTS'], c=days_since, cmap='coolwarm', edgecolors='black', s=100)
    m, b = np.polyfit(df['MIN'], df['PTS'], 1)
    ax1.plot(df['MIN'], m * df['MIN'] + b, '--', color='black', label='Trend')
    ax1.set_xlabel("Minutes")
    ax1.set_ylabel("Points")
    ax1.legend()
    ax1.grid(True)
    fig1.colorbar(sc, ax=ax1, label="Days Ago")
    st.pyplot(fig1)

with col2:
    st.subheader("PTS vs Selected Line")
    fig2, ax2 = plt.subplots()
    colors = ['green' if x else 'red' for x in df['OVER_LINE']]
    ax2.bar(df['GAME_DATE'].dt.strftime('%b %d'), df['PTS'], color=colors)
    ax2.axhline(selected_line, linestyle='--', color='black', label=f'Line: {selected_line}')
    ax2.set_ylabel("Points")
    ax2.set_xticklabels(df['GAME_DATE'].dt.strftime('%b %d'), rotation=45)
    ax2.legend()
    ax2.grid(True)
    st.pyplot(fig2)

# Optional donut chart
over_count = df['OVER_LINE'].sum()
under_count = len(df) - over_count
fig3, ax3 = plt.subplots()
ax3.pie([over_count, under_count], labels=['Over', 'Under'], autopct='%1.0f%%', startangle=90,
        colors=['green', 'red'], wedgeprops=dict(width=0.4))
ax3.set_title("Over/Under Distribution")
st.pyplot(fig3)
