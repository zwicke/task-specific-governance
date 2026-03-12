import streamlit as st
import pandas as pd
import plotly.express as px
import json
from engine import InferenceConfig, get_pareto_frontier

# --- 1. INITIALIZATION: Must be the very first Streamlit call ---
st.set_page_config(
    page_title="Task-Tethered Tradeoff Tool", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. THEME-AWARE STYLING ---
# We keep only the structural CSS (spacing/borders) and let Streamlit 
# handle the colors. This prevents the "white-out" on mobile.
st.markdown("""
    <style>
    .main { background-color: transparent; }
    .priority-container { 
        padding: 25px; 
        border-radius: 12px; 
        border: 1px solid rgba(151, 151, 151, 0.2); 
        margin-bottom: 30px; 
    }
    /* Simple utility for the report sections later */
    .cfo-banner { border-left: 10px solid #dc3545; padding-left: 20px; }
    .tradeoff-banner { border-left: 10px solid #ffc107; padding-left: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. TOP OF PAGE: STRATEGIC OVERVIEW (Native Version) ---
st.title("🚀 AI Model-Decision-Tradeoff Tool")

# Using st.info ensures perfect background/text contrast on all devices
st.info("""
**Strategic Purpose:** This tool tethers model performance to your **actual workload**. 
Instead of generic "Intelligence," it calculates model fitness based on your 
specific mix of tasks (Coding, Summarization, etc.).
""")

# Use a native container for the guide to maintain clean spacing
with st.container():
    st.subheader("Operational Guide")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Step 1: Inventory Your Workload Mix** Define the percentage of your AI traffic dedicated to specific tasks. This creates a "Capability Requirement" for the models.
        
        **Step 2: Map Usage & Identify Task-Gaps** Upload your 'Actuals' CSV. The maps will reveal if you are using an "overqualified" model or an "underqualified" one.
        """)
        
    with col2:
        st.markdown("""
        **Step 3: Analyze Portfolio Tradeoffs** Observe the **"Inflexibility Tax"**—the cost of using a single heavyweight model for a workload dominated by simple tasks.
        
        **Step 4: Execute Deployment Sign-off** Select the target model that best fits your task profile and document the rationale.
        """)

st.divider()

# --- STEP 1: WORKLOAD INVENTORY ---
st.header("🛡️ 1️⃣ Define Your Strategic Workload Mix")
with st.container():
    st.markdown('<div class="priority-container">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: v_sum = st.slider("Summarization %", 0, 100, 40)
    with c2: v_code = st.slider("Coding/Logic %", 0, 100, 20)
    with c3: v_ext = st.slider("Data Extraction %", 0, 100, 30)
    with c4: v_cre = st.slider("Creative Writing %", 0, 100, 10)
    
    total = v_sum + v_code + v_ext + v_cre
    if total != 100: st.error(f"Total is {total}%. Adjust sliders to equal 100%.")
    
    task_mix = {"Summarization": v_sum/100, "Coding": v_code/100, "Extraction": v_ext/100, "Creative": v_cre/100}
    
    st.markdown("---")
    sc1, sc2 = st.columns(2)
    with sc1: w_c = st.slider("Cost Sensitivity", 1, 10, 5)
    with sc2: w_s = st.slider("Sustainability Priority", 1, 10, 5)
    st.markdown('</div>', unsafe_allow_html=True)

# --- ENGINE ---
def get_task_data(mix, wc, ws):
    try:
        with open('prices.json', 'r') as f:
            raw_data = json.load(f)
        configs = [InferenceConfig(**c) for c in raw_data['configurations']]
    except: return pd.DataFrame()

    leaders = [c for c in configs if c.model_name in [l.model_name for l in get_pareto_frontier(configs)]]
    rows = []
    for l in leaders:
        cost = l.calculate_normalized_cost()
        carb = l.get_carbon_footprint()
        perf = l.get_weighted_task_performance(mix)
        
        # Reactive Math
        iq_n = perf / 10.0
        cost_n = 1.0 - (cost / 50.0) # Normalized against a $50 ceiling
        carb_n = 1.0 - (carb / 1500.0) # Normalized against 1500g ceiling
        
        raw_score = (iq_n * 100) + (cost_n * (wc**3)) + (carb_n * (ws**3))
        
        rows.append({"Model": l.model_name, "Cost": cost, "Performance": round(perf, 2), "Carbon": carb, "Raw": raw_score, "Status": "Market Leader"})
    
    res_df = pd.DataFrame(rows)
    if not res_df.empty:
        r_min, r_max = res_df["Raw"].min(), res_df["Raw"].max()
        r_range = r_max - r_min if r_max != r_min else 1
        res_df["Match Score"] = ((res_df["Raw"] - r_min) / r_range) * (100 - 15) + 15
    return res_df

df = get_task_data(task_mix, w_c, w_s)

# --- STEP 2: MAPPING ---
st.header("📍 2️⃣ Map Usage & Identify Task-Gaps")
uploaded_actuals = st.file_uploader("Upload 'Actuals' CSV", type="csv")

if uploaded_actuals and uploaded_actuals.size > 0:
    actual_df = pd.read_csv(uploaded_actuals)
    actual_df['Status'] = 'Your Actual Usage'
    actual_df['Match Score'] = 45
    # For simplicity in Vibe 2, we map 'Intelligence' from actuals to 'Performance'
    actual_df = actual_df.rename(columns={'Intelligence': 'Performance'})
    actual_model = actual_df.iloc[0]
    df = pd.concat([df, actual_df], ignore_index=True)
else:
    actual_model = None

col_m1, col_m2 = st.columns(2)
chart_key = f"{total}_{w_c}_{w_s}"
with col_m1:
    fig_cost = px.scatter(df, x="Cost", y="Performance", size="Match Score", color="Status", 
                          hover_name="Model", title="Financial Efficiency (Task-Specific)",
                          labels={"Performance": "Workload Fitness (1-10)"}, size_max=100,
                          color_discrete_map={'Market Leader': '#00E5FF', 'Your Actual Usage': '#ff4b4b'})
    st.plotly_chart(fig_cost, use_container_width=True, key=f"c_{chart_key}")

with col_m2:
    fig_carb = px.scatter(df, x="Carbon", y="Performance", size="Match Score", color="Status", 
                          hover_name="Model", title="Environmental Debt (Task-Specific)",
                          labels={"Performance": "Workload Fitness (1-10)"}, size_max=100,
                          color_discrete_map={'Market Leader': '#00E5FF', 'Your Actual Usage': '#ff4b4b'})
    st.plotly_chart(fig_carb, use_container_width=True, key=f"s_{chart_key}")

# --- STEP 3: ANALYSIS ---
st.header("💡 3️⃣ Analyze Portfolio Tradeoffs")
if actual_model is not None:
    best = df[df['Status'] == 'Market Leader'].sort_values('Raw', ascending=False).iloc[0]
    st.markdown(f"""
    <div class="executive-report cfo-banner">
        <h3>🚨 Workload Misalignment Detected</h3>
        <p><b>Observation:</b> Your workload is <b>{v_sum}% Summarization</b>. While your current model is powerful, 
        <b>{best['Model']}</b> provides 95% of the required fitness at a fraction of the cost.</p>
        <p>This suggests the organization is paying a <b>"Logic Premium"</b> for tasks that primarily require extraction and formatting.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="executive-report tradeoff-banner">
    <h3>🚲 Tradeoff Analysis: The Right-Sizing Invitation</h3>
    <p><b>The Insight:</b> By tethering models to tasks, we see that high-volume, low-complexity tasks (like your 30% Extraction volume) 
    do not benefit from heavyweight reasoning. </p>
    <p><b>The Tradeoff:</b> Not diversifying your portfolio for these specific tasks is an implicit choice to trade capital 
    efficiency for architectural simplicity (The Inflexibility Tax).</p>
</div>
""", unsafe_allow_html=True)

# --- STEP 4: SIGN-OFF ---
st.header("📝 4️⃣ Execute Deployment Sign-off")
l1, l2 = st.columns(2)
with l1:
    selected = st.selectbox("Assign Target Configuration", df[df['Status'] == 'Market Leader']['Model'].unique())
    owner = st.text_input("Accountable Stakeholder")
    final_rationale = st.text_area("Audit Rationale", placeholder="Why does this model fit our specific workload mix?")
with l2:
    st.write("### 🧾 Deployment Receipt")
    final_row = df[df['Model'] == selected].iloc[0]
    st.table(pd.DataFrame({
        "Metric": ["Workload Fitness", "Market Cost", "Carbon Impact"],
        "Target": [f"{final_row['Performance']}/10", f"${final_row['Cost']:.2f}", f"{final_row['Carbon']:.1f}g"]
    }))
    st.download_button("💾 Export Task-Audit", data=f"OWNER: {owner}\nMODEL: {selected}\nRATIONALE: {final_rationale}", file_name="task_audit.txt")