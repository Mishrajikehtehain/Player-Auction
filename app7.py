import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. INITIALIZATION & STATE
# ==========================================
st.set_page_config(page_title="V5 Warfare Terminal", layout="wide", page_icon="⚔️", initial_sidebar_state="expanded")

TEAM_NAMES = ["MY_SQUAD"] + [f"Team_{i}" for i in range(2, 11)]

if 'auction_state' not in st.session_state:
    st.session_state.auction_state = {
        'teams': {t: {
            'purse': 100.0, 'slots_left': 18, 'points': 0.0, 
            'os': 0, 'uncap': 0, 'wk': 0, 'bat': 0, 'bowl': 0, 'ar': 0, 'roster': []
        } for t in TEAM_NAMES},
        'ledger': []
    }

# ==========================================
# 2. SIDEBAR: PARAMETERS & UPLOAD
# ==========================================
with st.sidebar:
    st.header("⚙️ Core Liquidity")
    total_purse = st.number_input("Purse (Cr)", value=100.0, step=1.0)
    target_squad = st.number_input("Squad Size", value=18, step=1)
    target_avg = st.number_input("Target Avg Rating", value=82.0, step=0.5)
    
    st.markdown("---")
    st.header("🔒 Roster Constraints")
    max_os = st.number_input("Max OS", value=8, step=1)
    min_uncap = st.number_input("Min Uncapped", value=2, step=1)
    min_wk = st.number_input("Min WK", value=1, step=1)
    min_bat = st.number_input("Min Bat", value=3, step=1)
    min_bowl = st.number_input("Min Bowl", value=3, step=1)
    base_filler = st.number_input("Floor Price (Cr)", value=0.2, step=0.1)
    
    st.markdown("---")
    uploaded_file = st.file_uploader("Upload DB (CSV)", type=['csv'])

    if st.button("⚠️ WIPE MARKET MEMORY"):
        st.session_state.auction_state = {
            'teams': {t: {'purse': total_purse, 'slots_left': target_squad, 'points': 0.0, 'os': 0, 'uncap': 0, 'wk': 0, 'bat': 0, 'bowl': 0, 'ar': 0, 'roster': []} for t in TEAM_NAMES},
            'ledger': []
        }
        st.rerun()

# ==========================================
# 3. VECTORIZED PRICING ENGINE (ROBUST)
# ==========================================
@st.cache_data
def process_data(df, purse, squad_size):
    df.columns = df.columns.str.lower().str.strip()
    
    # Robust coercion to prevent crashes from dirty CSVs
    num_cols = ['base_price', 'runs', 'strike_rate', 'bat_avg', 'wickets', 'economy', 'bowl_avg', 'rating']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df.dropna(subset=['name', 'rating'], inplace=True)

    median_r = df['rating'].median()
    df['premium_points'] = np.where(df['rating'] > median_r, df['rating'] - median_r, 0)
    
    top_points_sum = df.nlargest(squad_size, 'rating')['premium_points'].sum()
    price_per_point = (purse * 0.8) / top_points_sum if top_points_sum > 0 else 0
    
    df['intrinsic_value'] = (df['base_price'] + (df['premium_points'] * price_per_point)).round(2)
    df['rpc'] = np.where(df['intrinsic_value'] > 0, (df['rating'] / df['intrinsic_value']).round(2), 0)
    return df.sort_values('rating', ascending=False)

def get_market_kappa(ledger):
    if not ledger: return 1.0
    ldf = pd.DataFrame(ledger)
    total_exp = ldf['expected_val'].sum()
    total_act = ldf['actual_price'].sum()
    return total_act / total_exp if total_exp > 0 else 1.0

# ==========================================
# 4. UI ARCHITECTURE
# ==========================================
if uploaded_file is not None:
    raw_df = pd.read_csv(uploaded_file)
    df = process_data(raw_df, total_purse, target_squad)
    
    ledger = st.session_state.auction_state['ledger']
    sold_names = [p['name'] for p in ledger]
    available_df = df[~df['name'].isin(sold_names)]
    my_state = st.session_state.auction_state['teams']['MY_SQUAD']
    kappa = get_market_kappa(ledger)

    # --- TOP TICKER ---
    st.markdown("### 📡 Live Telemetry")
    t1, t2, t3, t4, t5 = st.columns(5)
    slots_left = my_state['slots_left']
    d_rem = ((target_avg * target_squad) - my_state['points']) / slots_left if slots_left > 0 else 0
    avg_budget = my_state['purse'] / slots_left if slots_left > 0 else 0
    
    t1.metric("Liquidity", f"{my_state['purse']:.2f} Cr")
    t2.metric("Slots Open", f"{slots_left}/{target_squad}")
    t3.metric(r"Req. Density ($D_{rem}$)", f"{d_rem:.2f}")
    t4.metric("Avg Slot Budget", f"{avg_budget:.2f} Cr")
    t5.metric(r"Inflation ($\kappa$)", f"{kappa:.2f}")
    st.markdown("---")

    tab_exec, tab_intel, tab_warfare, tab_market = st.tabs(["⚡ Trade Execution", "🧠 Auto-Scout", "⚔️ War Room", "📊 Macro Market"])

    # ------------------------------------------
    # TAB 1: TRADE EXECUTION FLOOR
    # ------------------------------------------
    with tab_exec:
        c_intel, c_form = st.columns([1.5, 1])
        
        with c_intel:
            st.subheader("🤖 Algorithmic Target Analysis")
            selected_player = st.selectbox("Player on the Block", available_df['name'], label_visibility="collapsed", key='exec_player')
            p = df[df['name'] == selected_player].iloc[0]
            
            p_type = str(p.get('type', '')).strip().upper()
            p_role = str(p.get('role', '')).strip().upper()
            
            shadow_price = p['intrinsic_value'] * kappa
            abs_max = my_state['purse'] - ((slots_left - 1) * base_filler)
            strat_max = min(abs_max, shadow_price * 1.1)
            
            st.info(f"**{p['name']}** | Rating: **{p['rating']}** | Role: **{p_role}** | Type: **{p_type}**")
            
            if slots_left <= 0: st.error("🔴 FOLD. SQUAD FULL.")
            elif p_type == 'OS' and my_state['os'] >= max_os: st.error("🔴 FOLD. OVERSEAS LIMIT REACHED.")
            elif p['rating'] < d_rem - 3: st.warning(f"🟡 CAUTION. Damages required average ({d_rem:.1f}).")
            else: st.success(f"🟢 CLEAR TO BID. Max limit: {strat_max:.2f} Cr")
                
            m1, m2, m3 = st.columns(3)
            m1.metric("Intrinsic Value", f"{p['intrinsic_value']:.2f} Cr")
            m2.metric("Shadow Price (Inflation)", f"{shadow_price:.2f} Cr")
            m3.metric("Your Strategic Max", f"{strat_max:.2f} Cr")

        with c_form:
            st.subheader("🔨 Drop Hammer")
            with st.form("trade_form"):
                sold_price = st.number_input("Hammer Price (Cr)", min_value=0.2, step=0.1, value=float(p['base_price']))
                buyer = st.selectbox("Winning Team", TEAM_NAMES)
                submitted = st.form_submit_button("Execute Block Trade", use_container_width=True)
                
                if submitted:
                    b_state = st.session_state.auction_state['teams'][buyer]
                    b_max_bid = b_state['purse'] - ((b_state['slots_left'] - 1) * base_filler)
                    
                    if b_state['slots_left'] <= 0: st.error(f"❌ {buyer} roster full.")
                    elif p_type == 'OS' and b_state['os'] >= max_os: st.error(f"❌ {buyer} OS limit hit.")
                    elif sold_price > b_max_bid: st.error(f"❌ Bankruptcy! {buyer} max is {b_max_bid:.2f} Cr.")
                    else:
                        b_state['purse'] -= sold_price
                        b_state['slots_left'] -= 1
                        b_state['points'] += p['rating']
                        b_state['roster'].append(selected_player)
                        
                        if p_type == 'OS': b_state['os'] += 1
                        elif p_type == 'UNCAP': b_state['uncap'] += 1
                        
                        if p_role == 'WK': b_state['wk'] += 1
                        elif p_role == 'BAT': b_state['bat'] += 1
                        elif p_role == 'BOWL': b_state['bowl'] += 1
                        elif p_role == 'AR': b_state['ar'] += 1
                        
                        st.session_state.auction_state['ledger'].append({
                            'name': selected_player, 'rating': p['rating'], 'expected_val': p['intrinsic_value'],
                            'actual_price': sold_price, 'buyer': buyer, 'role': p_role
                        })
                        st.rerun()

    # ------------------------------------------
    # TAB 2: GAME THEORY & WARFARE (NEW)
    # ------------------------------------------
    with tab_warfare:
        st.header("⚔️ Psychological Warfare & Game Theory")
        
        c_bleed, c_bottle = st.columns(2)
        
        with c_bleed:
            st.subheader("🩸 1. The Liquidity Squeeze")
            st.markdown("Force a rival to overpay and calculate the exact moment it destroys their strategy.")
            
            w_rival = st.selectbox("Select Target Rival", [t for t in TEAM_NAMES if t != "MY_SQUAD"])
            w_player = st.selectbox("Player on Block", available_df['name'], key='war_player')
            w_p_data = df[df['name'] == w_player].iloc[0]
            
            r_state = st.session_state.auction_state['teams'][w_rival]
            r_max_bid = r_state['purse'] - ((r_state['slots_left'] - 1) * base_filler) if r_state['slots_left'] > 0 else 0
            
            # The Bail-Out Price (1.25x Shadow Price)
            bail_out = (w_p_data['intrinsic_value'] * kappa) * 1.25
            bail_out = min(bail_out, r_max_bid - 0.1) # Don't bid past their mathematical limit
            
            st.info(f"**Target:** {w_rival} | **Purse:** {r_state['purse']:.2f} Cr | **Max Bid:** {r_max_bid:.2f} Cr")
            
            st.metric("🚨 The Bail-Out Price (Hard Fold Here)", f"{max(base_filler, bail_out):.2f} Cr", help="Bid confidently up to this price. Drop out instantly once reached. They will suffer the Winner's Curse.")
            
            bait_price = st.slider("Simulate Rival Winning at Price:", min_value=0.2, max_value=float(r_max_bid) if r_max_bid > 0.2 else 1.0, value=float(min(5.0, r_max_bid)), step=0.1)
            
            if r_state['slots_left'] > 1:
                r_future_avg = (r_state['purse'] - bait_price) / (r_state['slots_left'] - 1)
                st.warning(f"If {w_rival} buys at {bait_price} Cr, their average budget for remaining {r_state['slots_left']-1} slots crashes to **{r_future_avg:.2f} Cr/slot**.")

        with c_bottle:
            st.subheader("⏳ 2. Bottleneck Weaponization")
            st.markdown("Identify supply starvation across the 10 teams and artificially inflate prices.")
            
            # Calculate Global Demand vs Supply
            roles = ['WK', 'BAT', 'BOWL', 'AR']
            mins = {'WK': min_wk, 'BAT': min_bat, 'BOWL': min_bowl, 'AR': 1} # Assuming 1 AR min for general logic
            
            bottle_data = []
            for r in roles:
                # Total demand: sum of (min required - currently owned) across all rivals
                demand = sum([max(0, mins[r] - st.session_state.auction_state['teams'][t][r.lower()]) for t in TEAM_NAMES if t != "MY_SQUAD"])
                # Viable Supply: Rating > 75
                supply = len(available_df[(available_df['role'].str.upper() == r) & (available_df['rating'] >= 75)])
                
                status = "🟢 Safe"
                if demand > supply: status = "🔴 WEAPONIZE (Starved)"
                elif demand >= supply * 0.7: status = "🟡 Inflate Price"
                
                bottle_data.append({"Role": r, "Rival Demand (Slots)": demand, "Viable Supply (>75)": supply, "Warfare Signal": status})
                
            st.dataframe(pd.DataFrame(bottle_data), hide_index=True, use_container_width=True)
            st.caption("*If Signal is WEAPONIZE, bid up any player of this role aggressively. Rivals have no choice but to overpay or enter a Dead State.*")

    # ------------------------------------------
    # TAB 3: LIVE AUTO-SCOUT
    # ------------------------------------------
    with tab_intel:
        sc1, sc2 = st.columns([1, 1.5])
        with sc1:
            st.subheader("🚦 My Roster Constraints")
            c_df = pd.DataFrame({
                "Role": ["Overseas", "Uncapped", "Wicketkeeper", "Batsman", "Bowler"],
                "Current": [my_state['os'], my_state['uncap'], my_state['wk'], my_state['bat'], my_state['bowl']],
                "Target": [f"Max {max_os}", f"Min {min_uncap}", f"Min {min_wk}", f"Min {min_bat}", f"Min {min_bowl}"]
            })
            st.dataframe(c_df, hide_index=True, use_container_width=True)
            
        with sc2:
            st.subheader(r"🎯 Auto-Scout Recommendations")
            st.markdown(f"Optimal targets matching your required $D_{{rem}}$ of **{d_rem:.2f}**.")
            
            viable = available_df[
                (available_df['rating'] >= d_rem - 1) & 
                (available_df['intrinsic_value'] * kappa <= avg_budget * 1.5)
            ].copy()
            
            if my_state['wk'] < min_wk: viable = viable[viable['role'].str.upper() == 'WK']
            elif my_state['uncap'] < min_uncap: viable = viable[viable['type'].str.upper() == 'UNCAP']
                
            if not viable.empty:
                st.dataframe(viable[['name', 'role', 'type', 'rating', 'intrinsic_value', 'rpc']].head(5), hide_index=True, use_container_width=True)
            else:
                st.warning("No mathematically safe targets found.")

    # ------------------------------------------
    # TAB 4: MACRO ECONOMICS
    # ------------------------------------------
    with tab_market:
        st.subheader("Global Market State")
        team_data = []
        for t, data in st.session_state.auction_state['teams'].items():
            team_data.append({
                "Team": t,
                "Purse": data['purse'],
                "Slots": data['slots_left'],
                "OS": data['os'], "WK": data['wk'],
                "Max Bid": data['purse'] - ((data['slots_left'] - 1) * base_filler) if data['slots_left'] > 0 else 0
            })
        st.dataframe(pd.DataFrame(team_data).set_index("Team").style.format("{:.2f}", subset=["Purse", "Max Bid"]).background_gradient(subset=["Purse"], cmap="Greens"), use_container_width=True)
        
        st.subheader("Transaction Ledger")
        if ledger: st.dataframe(pd.DataFrame(ledger), use_container_width=True)
else:
    st.info("Upload CSV Data to Initialize Terminal.")