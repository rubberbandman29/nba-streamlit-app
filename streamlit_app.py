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

# Load player data
player_id = next(p['id'] for p in team_players if p['full_name'] == selected_player)
now = datetime.datetime.now()
season_start = now.year - 1 if now.month < 10 else now.year
season_str = f"{season_start}-{str(season_start + 1)[-2:]}"
gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season_str, season_type_all_star='Regular Season')
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
selected_opponent = st.selectbox("Filter by Opponent", ["All"] + opponents)

if selected_opponent != "All":
    df = df[df['OPPONENT'] == selected_opponent]

# Insights
avg_pts = df['PTS'].mean()
avg_min = df['MIN'].mean()
over_rate = df['OVER_LINE'].mean() * 100

st.markdown(f"**{selected_player}** averages **{avg_pts:.1f} PPG** and **{avg_min:.1f} minutes**.")
st.markdown(f"**Over Line Hit Rate:** {over_rate:.0f}% (Line: {selected_line} points)")

# Graph 1: Scatter – Minutes vs Points
st.subheader("1. Minutes vs Points (Recency Colored)")
fig1, ax1 = plt.subplots()
days_since = (df['GAME_DATE'].max() - df['GAME_DATE']).dt.days
sc = ax1.scatter(df['MIN'], df['PTS'], c=days_since, cmap='coolwarm', edgecolors='black', s=100)
m, b = np.polyfit(df['MIN'], df['PTS'], 1)
ax1.plot(df['MIN'], m * df['MIN'] + b, '--', color='black', label=f"Trend: y={m:.1f}x+{b:.1f}")
ax1.set_xlabel("Minutes")
ax1.set_ylabel("Points")
ax1.legend()
ax1.grid(True)
fig1.colorbar(sc, ax=ax1, label="Days Ago")
st.pyplot(fig1)

# Graph 2: Game-by-Game PTS and MIN
st.subheader("2. Game-by-Game Points and Minutes")
fig2, ax2 = plt.subplots()
ax2.plot(df['GAME_DATE'], df['PTS'], marker='o', label='Points', color='royalblue')
ax2.plot(df['GAME_DATE'], df['MIN'], marker='s', label='Minutes', color='darkorange')
ax2.fill_between(df['GAME_DATE'], df['PTS'], df['MIN'], where=df['PTS'] > df['MIN'], color='blue', alpha=0.2)
ax2.fill_between(df['GAME_DATE'], df['PTS'], df['MIN'], where=df['PTS'] < df['MIN'], color='red', alpha=0.2)
ax2.set_xticks(df['GAME_DATE'])
ax2.set_xticklabels(df['GAME_DATE'].dt.strftime('%b %d'), rotation=45)
ax2.set_ylabel("Stat Value")
ax2.legend()
ax2.grid(True)
st.pyplot(fig2)

# Graph 3: Bar Chart – Points vs Line
st.subheader("3. Points vs Over/Under Line")
fig3, ax3 = plt.subplots()
colors = ['green' if val else 'red' for val in df['OVER_LINE']]
ax3.bar(df['GAME_DATE'].dt.strftime('%b %d'), df['PTS'], color=colors)
ax3.axhline(selected_line, linestyle='--', color='black', label=f"Line: {selected_line}")
ax3.set_ylabel("Points")
ax3.set_xticklabels(df['GAME_DATE'].dt.strftime('%b %d'), rotation=45)
ax3.legend()
ax3.grid(True)
st.pyplot(fig3)

# Graph 4: Heatmap – PTS per MIN
st.subheader("4. Scoring Efficiency Heatmap (PTS/MIN)")
fig4, ax4 = plt.subplots(figsize=(10, 1.5))
heat = np.array([df['PTS_PER_MIN']])
im = ax4.imshow(heat, cmap='coolwarm', aspect='auto')
for i, v in enumerate(df['PTS_PER_MIN']):
    ax4.text(i, 0, f"{v:.2f}", ha='center', va='center',
             color='white' if v > df['PTS_PER_MIN'].mean() else 'black', fontsize=8)
ax4.set_xticks(np.arange(len(df)))
ax4.set_xticklabels(df['GAME_DATE'].dt.strftime('%b %d'), rotation=45)
ax4.set_yticks([])
fig4.colorbar(im, ax=ax4, orientation='vertical')
st.pyplot(fig4)

# Graph 5: Deviation from Average
st.subheader("5. Deviation from 15-Game Average")
fig5, ax5 = plt.subplots()
avg_pts = df['PTS'].mean()
diff = df['PTS'] - avg_pts
ax5.bar(df['GAME_DATE'].dt.strftime('%b %d'), diff, color='purple')
ax5.axhline(0, color='black', linestyle='--')
ax5.axhline(avg_pts - avg_pts, color='blue', linestyle='-', label=f"Avg PTS = {avg_pts:.1f}")
ax5.set_ylabel("Points vs Avg")
ax5.set_xticklabels(df['GAME_DATE'].dt.strftime('%b %d'), rotation=45)
ax5.legend()
ax5.grid(True)
st.pyplot(fig5)

# Graph 6: Donut Chart – Over vs Under
st.subheader("6. Over vs Under Line")
over_count = df['OVER_LINE'].sum()
under_count = len(df) - over_count
fig6, ax6 = plt.subplots()
ax6.pie([over_count, under_count], labels=['Over', 'Under'], autopct='%1.0f%%', startangle=90,
        colors=['green', 'red'], wedgeprops=dict(width=0.4))
ax6.set_title("Over/Under Distribution")
st.pyplot(fig6)
