import streamlit as st
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime

# Wide layout
st.set_page_config(layout="wide")
st.title("🎯 NBA Player Stats – Minutes vs Points (Last 15 Games)")

# Get active players
all_players = players.get_players()
active_players = sorted([p['full_name'] for p in all_players if p['is_active']])
player_name = st.selectbox("Select a Player", active_players)

# Get selected player's ID and data
player_id = next(p['id'] for p in all_players if p['full_name'] == player_name)
now = datetime.datetime.now()
season_start = now.year - 1 if now.month < 10 else now.year
season_str = f"{season_start}-{str(season_start + 1)[-2:]}"
gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season_str, season_type_all_star='Regular Season')
df = gamelog.get_data_frames()[0]
df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
df = df.sort_values('GAME_DATE', ascending=False).head(15)
df = df[['GAME_DATE', 'MIN', 'PTS']].dropna()
df['MIN'] = pd.to_numeric(df['MIN'], errors='coerce')
df['PTS'] = pd.to_numeric(df['PTS'], errors='coerce')
df = df.sort_values('GAME_DATE')

# Split columns for side-by-side charts
col1, col2 = st.columns([1, 1])

# --- Chart 1: Scatter Plot ---
with col1:
    st.subheader("📊 Minutes vs Points (Scatter)")
    fig1, ax1 = plt.subplots(figsize=(7.5, 5.5))
    df['days_since'] = (df['GAME_DATE'].max() - df['GAME_DATE']).dt.days
    scatter = ax1.scatter(df['MIN'], df['PTS'], c=df['days_since'], cmap='Blues', s=100, edgecolor='black', alpha=0.9)

    # Add trend line
    m, b = np.polyfit(df['MIN'], df['PTS'], 1)
    ax1.plot(df['MIN'], m * df['MIN'] + b, color='red', linestyle='--', linewidth=2, label='Trend Line')

    # Annotate points
    for _, row in df.iterrows():
        ax1.text(row['MIN'] + 0.3, row['PTS'] + 0.3, f"{int(row['PTS'])} pts\n{int(row['MIN'])} min", fontsize=8)

    ax1.set_xlabel('Minutes Played')
    ax1.set_ylabel('Points Scored')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend()

    # ✅ Add colorbar (Days Ago)
    cbar = fig1.colorbar(scatter, ax=ax1)
    cbar.set_label('Days Ago')

    fig1.tight_layout()
    st.pyplot(fig1)

# --- Chart 2: Game-by-Game Trend ---
with col2:
    st.subheader("📈 Game-by-Game Trend")
    fig2, ax2 = plt.subplots(figsize=(7.5, 5.5))

    # Fill between
    ax2.fill_between(df['GAME_DATE'], df['PTS'], df['MIN'],
                     where=(df['PTS'] > df['MIN']), interpolate=True, color='steelblue', alpha=0.4, label='Points > Minutes')
    ax2.fill_between(df['GAME_DATE'], df['PTS'], df['MIN'],
                     where=(df['PTS'] < df['MIN']), interpolate=True, color='darkorange', alpha=0.4, label='Minutes > Points')

    # Line plots
    ax2.plot(df['GAME_DATE'], df['PTS'], marker='o', color='royalblue', linewidth=2.5, label='Points')
    ax2.plot(df['GAME_DATE'], df['MIN'], marker='s', color='orange', linewidth=2.5, label='Minutes')

    # Trend lines
    z_pts = np.polyfit(range(len(df)), df['PTS'], 1)
    z_min = np.polyfit(range(len(df)), df['MIN'], 1)
    ax2.plot(df['GAME_DATE'], np.polyval(z_pts, range(len(df))), linestyle='--', color='blue', alpha=0.6)
    ax2.plot(df['GAME_DATE'], np.polyval(z_min, range(len(df))), linestyle='--', color='orange', alpha=0.6)

    # Highlights
    max_pts = df.loc[df['PTS'].idxmax()]
    max_min = df.loc[df['MIN'].idxmax()]
    ax2.scatter(max_pts['GAME_DATE'], max_pts['PTS'], s=180, edgecolor='black', facecolor='crimson', zorder=5)
    ax2.scatter(max_min['GAME_DATE'], max_min['MIN'], s=180, edgecolor='black', facecolor='green', zorder=5)
    ax2.annotate(f"{int(max_pts['PTS'])} pts", (max_pts['GAME_DATE'], max_pts['PTS']), xytext=(0, 10),
                 textcoords="offset points", ha='center', fontsize=10, fontweight='bold', color='crimson')
    ax2.annotate(f"{int(max_min['MIN'])} min", (max_min['GAME_DATE'], max_min['MIN']), xytext=(0, -18),
                 textcoords="offset points", ha='center', fontsize=10, fontweight='bold', color='green')

    # Axis formatting
    ax2.set_xticks(df['GAME_DATE'])
    ax2.set_xticklabels(df['GAME_DATE'].dt.strftime('%b %d'), rotation=45)
    ax2.set_ylabel('Stat Value')
    ax2.set_xlabel('Game Date')
    ax2.grid(True, linestyle='--', alpha=0.4)
    ax2.legend()

    fig2.tight_layout()
    st.pyplot(fig2)
