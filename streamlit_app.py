import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playergamelog, commonteamroster
import datetime

st.set_page_config(layout="wide")
st.title("🏀 NBA Player Insights – Bettor Dashboard")

# Load teams and player data
team_data = teams.get_teams()
team_names = sorted([team['full_name'] for team in team_data])
selected_team = st.selectbox("Select Team", team_names)

team_id = next(team['id'] for team in team_data if team['full_name'] == selected_team)
roster = commonteamroster.CommonTeamRoster(team_id=team_id)
roster_df = roster.get_data_frames()[0]
roster_names = roster_df['PLAYER'].tolist()

active_players = [p for p in players.get_players() if p['is_active']]
team_players = [p for p in active_players if p['full_name'] in roster_names]
player_names = sorted([p['full_name'] for p in team_players])
selected_player = st.selectbox("Select Player", player_names)

# Controls row
col1, col2, col3, col4 = st.columns(4)
with col1:
    selected_line = st.number_input("Over/Under Line", min_value=0.0, value=20.5)
with col2:
    lookback_games = st.slider("Look Back Games", min_value=5, max_value=30, value=15)
with col3:
    season_range = st.selectbox("Seasons to Look Back", list(range(2, 26)), index=0)

# Helper function for generating past seasons
def generate_past_seasons(n):
    base_year = datetime.datetime.now().year
    if datetime.datetime.now().month < 10:
        base_year -= 1
    return [f"{year}-{str(year+1)[-2:]}" for year in range(base_year, base_year - n, -1)]

# Load game logs from multiple seasons
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

if df.empty:
    st.warning("No data found for this player in selected seasons.")
    st.stop()

# Preprocess data
df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
df['OPPONENT'] = df['MATCHUP'].str.extract("vs. (.*)|@ (.*)").bfill(axis=1).iloc[:, 0]
df['PTS'] = pd.to_numeric(df['PTS'])
df['MIN'] = pd.to_numeric(df['MIN'])
df['OVER_LINE'] = df['PTS'] > selected_line
df['PTS_PER_MIN'] = df['PTS'] / df['MIN']
df['SEASON_LABEL'] = df['SEASON'].str[:4].astype(int) + 1
df['DATE_LABEL'] = df['GAME_DATE'].dt.strftime('%b %d') + " " + df['SEASON_LABEL'].astype(str).str[-2:] + "'"

with col4:
    opponent_options = sorted(df['OPPONENT'].dropna().unique())
    selected_opponent = st.selectbox("Played Against", ["All"] + opponent_options)

# Filter by opponent or last N games
if selected_opponent != "All":
    df = df[df['OPPONENT'] == selected_opponent].sort_values('GAME_DATE', ascending=False)
else:
    df = df.sort_values('GAME_DATE', ascending=False).head(lookback_games)

# Summary
avg_pts = df['PTS'].mean()
avg_min = df['MIN'].mean()
over_rate = df['OVER_LINE'].mean() * 100
st.markdown(f"**{selected_player}** averages **{avg_pts:.1f} PPG** and **{avg_min:.1f} minutes** in last **{len(df)}** games.")
st.markdown(f"**Over Line Hit Rate:** {over_rate:.0f}% (Line: {selected_line} pts)")
if selected_opponent != "All":
    st.markdown(f"*All-time vs {selected_opponent} over last {season_range} seasons*")

# Prepare visuals
df = df.reset_index(drop=True)
x = np.arange(len(df))

col_a, col_b = st.columns(2)

# Chart 1: Scatter Plot
with col_a:
    fig1, ax1 = plt.subplots()
    sc = ax1.scatter(df['MIN'], df['PTS'], c=(df['GAME_DATE'].max() - df['GAME_DATE']).dt.days,
                     cmap='coolwarm', edgecolors='black', s=100)
    m, b = np.polyfit(df['MIN'], df['PTS'], 1)
    ax1.plot(df['MIN'], m * df['MIN'] + b, '--', color='black', label=f"Trend: y={m:.1f}x+{b:.1f}")
    ax1.set_xlabel("Minutes")
    ax1.set_ylabel("Points")
    ax1.legend()
    ax1.grid(True)
    fig1.colorbar(sc, ax=ax1, label="Days Ago")
    st.pyplot(fig1)
    st.caption("📊 **Chart 1:** Correlation between minutes and points scored.")

# Chart 2: Game-by-game trend
with col_b:
    fig2, ax2 = plt.subplots()
    ax2.plot(x, df['PTS'], marker='o', label='Points', color='royalblue')
    ax2.plot(x, df['MIN'], marker='s', label='Minutes', color='darkorange')
    ax2.fill_between(x, df['PTS'], df['MIN'], where=df['PTS'] > df['MIN'], color='blue', alpha=0.2)
    ax2.fill_between(x, df['PTS'], df['MIN'], where=df['PTS'] < df['MIN'], color='red', alpha=0.2)
    ax2.set_xticks(x)
    ax2.set_xticklabels(df['DATE_LABEL'], rotation=45)
    ax2.set_ylabel("Stat Value")
    ax2.legend()
    ax2.grid(True)
    st.pyplot(fig2)
    st.caption("📈 **Chart 2:** Game-by-game minutes and points with fill trends.")

# Chart 3: Bar over/under
with col_a:
    fig3, ax3 = plt.subplots()
    colors = ['green' if val else 'red' for val in df['OVER_LINE']]
    ax3.bar(x, df['PTS'], color=colors)
    ax3.axhline(selected_line, linestyle='--', color='black', label=f"Line: {selected_line}")
    ax3.set_xticks(x)
    ax3.set_xticklabels(df['DATE_LABEL'], rotation=45)
    ax3.set_ylabel("Points")
    ax3.legend()
    ax3.grid(True)
    st.pyplot(fig3)
    st.caption("🎯 **Chart 3:** Points per game compared to your line.")

# Chart 4: Heatmap of PTS/MIN
with col_b:
    fig4, ax4 = plt.subplots(figsize=(10, 1.5))
    heat = np.array([df['PTS_PER_MIN']])
    im = ax4.imshow(heat, cmap='coolwarm', aspect='auto')
    for i, v in enumerate(df['PTS_PER_MIN']):
        ax4.text(i, 0, f"{v:.2f}", ha='center', va='center',
                 color='white' if v > df['PTS_PER_MIN'].mean() else 'black', fontsize=8)
    ax4.set_xticks(x)
    ax4.set_xticklabels(df['DATE_LABEL'], rotation=45)
    ax4.set_yticks([])
    fig4.colorbar(im, ax=ax4, orientation='vertical')
    st.pyplot(fig4)
    st.caption("🔥 **Chart 4:** Scoring efficiency (points per minute).")

# Chart 5: Deviation from average
with col_a:
    fig5, ax5 = plt.subplots()
    diff = df['PTS'] - avg_pts
    ax5.bar(x, diff, color='purple')
    ax5.axhline(0, color='black', linestyle='--')
    ax5.axhline(0, color='blue', linestyle='-', label=f"Avg PTS = {avg_pts:.1f}")
    ax5.set_xticks(x)
    ax5.set_xticklabels(df['DATE_LABEL'], rotation=45)
    ax5.set_ylabel("Points vs Avg")
    ax5.legend()
    ax5.grid(True)
    st.pyplot(fig5)
    st.caption("📉 **Chart 5:** Game points compared to player's average.")

# Chart 6: Over/Under Pie
with col_b:
    fig6, ax6 = plt.subplots()
    over_count = df['OVER_LINE'].sum()
    under_count = len(df) - over_count
    ax6.pie([over_count, under_count], labels=['Over', 'Under'], autopct='%1.0f%%',
            startangle=90, colors=['green', 'red'], wedgeprops=dict(width=0.4))
    ax6.set_title("📊 Chart 6: Over/Under Split")
    st.pyplot(fig6)
