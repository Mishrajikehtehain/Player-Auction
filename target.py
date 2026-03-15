import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Target Rating Calculator", layout="wide", page_icon="🎯")
st.title("🎯 Target Rating & Market Capacity Calculator")
st.markdown("Calculate the exact squad average needed to mathematically dominate the auction.")

# ==========================================
# 1. SIDEBAR: AUCTION PARAMETERS
# ==========================================
with st.sidebar:
    st.header("⚙️ Market Parameters")
    total_teams = st.number_input("Total Teams in Auction", min_value=2, max_value=20, value=10, step=1)
    squad_size = st.number_input("Target Squad Size per Team", min_value=11, max_value=25, value=18, step=1)
    
    st.markdown("---")
    st.header("📂 Data Input")
    uploaded_file = st.file_uploader("Upload player.csv", type=['csv'])

# ==========================================
# 2. CORE ENGINE
# ==========================================
@st.cache_data
def calculate_target_metrics(df, teams, size):
    # Clean data
    if 'rating' in df.columns:
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df.dropna(subset=['name', 'rating'], inplace=True)
    
    # Sort from best to worst
    df = df.sort_values(by='rating', ascending=False).reset_index(drop=True)
    
    # Calculate Market Capacity
    market_capacity = teams * size
    
    # Split the pool into "Drafted" (Top N) and "Unsold" (The rest)
    if len(df) <= market_capacity:
        drafted_pool = df.copy()
        unsold_pool = pd.DataFrame()
    else:
        drafted_pool = df.head(market_capacity).copy()
        unsold_pool = df.iloc[market_capacity:].copy()
        
    # Calculate Statistics on the Drafted Pool
    par_score = drafted_pool['rating'].mean()
    spread = drafted_pool['rating'].std()
    
    # Championship Target: Mean + 0.75 Standard Deviations
    championship_target = par_score + (0.75 * spread)
    
    return drafted_pool, unsold_pool, par_score, spread, championship_target, market_capacity

# ==========================================
# 3. DASHBOARD OUTPUT
# ==========================================
if uploaded_file is not None:
    raw_df = pd.read_csv(uploaded_file)
    
    # FIXED: Added .strip() to cleanly format the headers without throwing a TypeError
    raw_df.columns = raw_df.columns.str.lower().str.strip()
    
    if 'rating' not in raw_df.columns:
        st.error("❌ Invalid CSV. Missing 'rating' column. Did you upload the raw stats instead of the processed player.csv?")
    else:
        # Run Math
        drafted, unsold, par, std_dev, target, capacity = calculate_target_metrics(raw_df.copy(), total_teams, squad_size)
        
        # --- HEADLINE METRICS ---
        st.header("Quantitative Output")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Market Capacity", f"{capacity} Players", help="Total players that will actually be bought.")
        col2.metric("The Par Score (Market Average)", f"{par:.2f}", help="If you hit this, you are perfectly average.")
        col3.metric("🎯 Championship Target", f"{target:.2f}", delta=f"+{target - par:.2f} over Par", help="Plug this exact number into your V5 Quant Terminal.")
        
        st.markdown("---")
        
        # --- VISUALIZATION ---
        st.subheader("Talent Distribution: Drafted vs Unsold")
        
        # Tag the data for the chart
        drafted['Status'] = 'Expected to be Drafted'
        if not unsold.empty:
            unsold['Status'] = 'Expected Unsold'
            viz_df = pd.concat([drafted, unsold])
        else:
            viz_df = drafted
            st.warning("⚠️ Your player pool is smaller than the Market Capacity. Every player will be bought. Expect hyper-inflation.")
            
        fig = px.histogram(
            viz_df, x="rating", color="Status", 
            nbins=30, 
            color_discrete_map={'Expected to be Drafted': '#2E86C1', 'Expected Unsold': '#E74C3C'},
            title=f"The Cutoff Line: Top {capacity} Players"
        )
        
        # Add mathematical lines to the chart
        fig.add_vline(x=par, line_dash="dash", line_color="black", annotation_text=f"Par Score: {par:.1f}")
        fig.add_vline(x=target, line_width=3, line_color="green", annotation_text=f"TARGET: {target:.1f}")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # --- DATA TABLES ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Elite Tier (Top 10)")
            st.dataframe(drafted[['name', 'role', 'type', 'rating']].head(10), hide_index=True)
        with c2:
            st.subheader("The Cutoff Line (Last In)")
            st.dataframe(drafted[['name', 'role', 'type', 'rating']].tail(10), hide_index=True)

else:
    st.info("Upload your processed player.csv to calculate your Target Rating.")