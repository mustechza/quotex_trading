import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import json
from collections import Counter
import io
from scipy import stats

# Page configuration
st.set_page_config(
    page_title="BC.Game Crash Analyzer",
    page_icon="🎲",
    layout="wide"
)

# Title and description
st.title("🎲 BC.Game Crash Multiplier Tracker")
st.markdown("""
This app analyzes crash multipliers from BC.Game JSON data and allows **manual addition of new multipliers** 
to track patterns and predict most overdue multipliers in real-time.
""")

# Initialize session state for data persistence
if 'df' not in st.session_state:
    st.session_state.df = None
if 'manual_entries' not in st.session_state:
    st.session_state.manual_entries = []
if 'data_source' not in st.session_state:
    st.session_state.data_source = "File Upload"

def load_data_from_json(file):
    """Load and process BC.Game crash JSON data"""
    try:
        data = json.load(file)
        df = pd.DataFrame(data)
        df['rate'] = df['rate'].astype(float)
        df['beginTime_dt'] = pd.to_datetime(df['beginTime'], unit='ms')
        df['endTime_dt'] = pd.to_datetime(df['endTime'], unit='ms')
        df['prepareTime_dt'] = pd.to_datetime(df['prepareTime'], unit='ms')
        df['fetchedAt_dt'] = pd.to_datetime(df['fetchedAt'])
        df['duration_ms'] = df['endTime'] - df['beginTime']
        df['data_source'] = 'file'
        df = df.sort_values('endTime', ascending=True).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def add_manual_entry(rate, game_id=None):
    """Add a manual entry to the dataset"""
    now = datetime.now()
    timestamp_ms = int(now.timestamp() * 1000)
    
    new_entry = {
        'gameId': game_id if game_id else f"MANUAL_{len(st.session_state.manual_entries) + 1}",
        'hash': f"manual_{timestamp_ms}",
        'beginTime': timestamp_ms - 30000,
        'endTime': timestamp_ms,
        'prepareTime': timestamp_ms - 35000,
        'fetchedAt': now.isoformat(),
        'salt': "manual_entry",
        'rate': rate,
        'beginTime_dt': now - pd.Timedelta(seconds=30),
        'endTime_dt': now,
        'prepareTime_dt': now - pd.Timedelta(seconds=35),
        'fetchedAt_dt': now,
        'duration_ms': 30000,
        'data_source': 'manual'
    }
    
    st.session_state.manual_entries.append(new_entry)
    
    if st.session_state.df is not None:
        manual_df = pd.DataFrame(st.session_state.manual_entries)
        st.session_state.df = pd.concat([st.session_state.df, manual_df], ignore_index=True)
        st.session_state.df = st.session_state.df.sort_values('endTime', ascending=True).reset_index(drop=True)
    
    return True

def get_current_dataframe():
    """Get the current combined dataframe"""
    if st.session_state.df is not None:
        return st.session_state.df
    elif st.session_state.manual_entries:
        return pd.DataFrame(st.session_state.manual_entries)
    else:
        return None

# Sidebar controls
st.sidebar.header("⚙️ Settings")

# Data source selection
data_option = st.sidebar.radio(
    "Data Source",
    ["Upload JSON File", "Use Manual Entry Only", "Combine Both"]
)

# File upload section
uploaded_file = None
if data_option in ["Upload JSON File", "Combine Both"]:
    uploaded_file = st.sidebar.file_uploader("Upload BC.Game JSON file", type=['json'])
    
    if uploaded_file is not None and (st.session_state.df is None or st.session_state.data_source != "file"):
        df_loaded = load_data_from_json(uploaded_file)
        if df_loaded is not None:
            if st.session_state.manual_entries and data_option == "Combine Both":
                manual_df = pd.DataFrame(st.session_state.manual_entries)
                st.session_state.df = pd.concat([df_loaded, manual_df], ignore_index=True)
                st.session_state.df = st.session_state.df.sort_values('endTime', ascending=True).reset_index(drop=True)
                st.session_state.data_source = "combined"
            else:
                st.session_state.df = df_loaded
                st.session_state.data_source = "file"
            st.sidebar.success(f"✅ Loaded {len(df_loaded)} rounds from file!")
    
    elif st.session_state.manual_entries and data_option == "Combine Both" and st.session_state.df is not None:
        st.sidebar.success(f"✅ Combined data: {len(st.session_state.df)} total rounds")

# Manual entry only mode
if data_option == "Use Manual Entry Only" and st.session_state.manual_entries:
    st.session_state.df = pd.DataFrame(st.session_state.manual_entries)
    st.session_state.data_source = "manual_only"
    st.sidebar.success(f"✅ Using {len(st.session_state.manual_entries)} manual entries")

# Check if we have data
if st.session_state.df is None and not st.session_state.manual_entries:
    if data_option == "Use Manual Entry Only":
        st.info("👋 Welcome! Use the 'Manual Data Entry' section below to start adding multipliers.")
    else:
        st.warning("⚠️ Please upload a JSON file or add manual entries to begin analysis")
        
        with st.expander("📋 Expected JSON format example"):
            st.code("""
[
  {
    "hash": "50fe7c9b26deb719b1b0db09f13f066c6b35a2ec5a87bdd5fb78635befa7866d",
    "beginTime": 1780134306561,
    "gameId": "9292552",
    "prepareTime": 1780134299572,
    "endTime": 1780134318884,
    "fetchedAt": "2026-05-30T09:45:26.971668+00:00",
    "salt": "0000000000000000000301e2801a9a9598bfb114e574a91a887f2132f33047e6",
    "rate": "2.1"
  }
]
            """, language="json")
    
    if not st.session_state.manual_entries:
        st.stop()

# Get current dataframe
df = get_current_dataframe()
if df is None:
    st.error("No data available. Please add manual entries or upload a file.")
    st.stop()

# Display data source info
if st.session_state.data_source == "combined":
    st.info(f"📊 Data source: {len(df) - len(st.session_state.manual_entries)} file rounds + {len(st.session_state.manual_entries)} manual entries = {len(df)} total")
elif st.session_state.data_source == "manual_only":
    st.info(f"📊 Data source: {len(df)} manual entries only")
elif st.session_state.data_source == "file":
    st.info(f"📊 Data source: {len(df)} rounds from uploaded file")

# Get last N rounds
n_rounds = st.sidebar.slider("Number of recent rounds to analyze", 20, min(500, len(df)), min(100, len(df)))
recent_df = df.tail(n_rounds).copy()
recent_df = recent_df.reset_index(drop=True)

# Display basic stats
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total Rounds", len(df))
with col2:
    st.metric("Analyzed Rounds", len(recent_df))
with col3:
    st.metric("Avg Multiplier", f"{recent_df['rate'].mean():.2f}x")
with col4:
    st.metric("Max Multiplier", f"{recent_df['rate'].max():.2f}x")
with col5:
    st.metric("Min Multiplier", f"{recent_df['rate'].min():.2f}x")
with col6:
    manual_count = len(st.session_state.manual_entries)
    st.metric("Manual Entries", manual_count)

# Define multiplier ranges
bins = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0, 15.0, 25.0, 50.0, 100.0, float('inf')]
labels = ['1.00-1.50', '1.51-2.00', '2.01-2.50', '2.51-3.00', '3.01-4.00', 
          '4.01-5.00', '5.01-7.50', '7.51-10.00', '10.01-15.00', 
          '15.01-25.00', '25.01-50.00', '50.01-100.00', '100.00+']

# Main content area with tabs
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs(
    ["🎯 Overdue & Manual Entry", "📊 Frequency Table", "📈 Recent History", "📉 Statistics"]
)

# ----- TAB 1: Combined Overdue & Manual Entry -----
with main_tab1:
    st.header("🎯 Most Overdue Multipliers & Manual Entry")
    
    # Calculate expected frequency based on FULL historical data
    full_df_copy = df.copy()
    full_df_copy['range'] = pd.cut(full_df_copy['rate'], bins=bins, labels=labels, right=False)
    historical_freq = full_df_copy['range'].value_counts(normalize=True)
    
    # Calculate current frequency in recent rounds
    recent_df_copy = recent_df.copy()
    recent_df_copy['range'] = pd.cut(recent_df_copy['rate'], bins=bins, labels=labels, right=False)
    current_freq = recent_df_copy['range'].value_counts(normalize=True)
    
    # Calculate overdue score
    overdue_scores = {}
    for label in labels:
        expected = historical_freq.get(label, 0)
        actual = current_freq.get(label, 0)
        overdue_scores[label] = max(0, expected - actual)
    
    # Create overdue dataframe
    overdue_df = pd.DataFrame([
        {'Range': k, 
         'Overdue Score': v * 100, 
         'Expected %': historical_freq.get(k, 0) * 100,
         'Actual %': current_freq.get(k, 0) * 100,
         'Gap': (historical_freq.get(k, 0) - current_freq.get(k, 0)) * 100}
        for k, v in overdue_scores.items()
    ])
    overdue_df = overdue_df.sort_values('Overdue Score', ascending=False)
    
    # Create a combined table with top overdue and manual entry in one view
    st.subheader("📊 Overdue Analysis & Quick Entry")
    
    # Use columns to create a side-by-side layout
    table_col, entry_col = st.columns([2, 1])
    
    with table_col:
        # Display full overdue table
        st.markdown("**Most Overdue Predictions (All Ranges)**")
        st.dataframe(
            overdue_df,
            column_config={
                "Range": st.column_config.TextColumn("Multiplier Range", width="medium"),
                "Overdue Score": st.column_config.NumberColumn("Overdue Score", format="%.1f%%", width="small"),
                "Expected %": st.column_config.NumberColumn("Expected %", format="%.1f%%", width="small"),
                "Actual %": st.column_config.NumberColumn("Actual %", format="%.1f%%", width="small"),
                "Gap": st.column_config.NumberColumn("Gap", format="%.1f%%", width="small")
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        # Show top 3 as badges below the table
        if len(overdue_df) > 0:
            st.markdown("**🏆 Top 3 Most Overdue**")
            top_cols = st.columns(3)
            for i, col in enumerate(top_cols[:3]):
                if i < len(overdue_df):
                    top = overdue_df.iloc[i]
                    medal = ["🥇", "🥈", "🥉"][i]
                    with col:
                        st.metric(
                            label=f"{medal} {top['Range']}",
                            value=f"{top['Overdue Score']:.1f}% overdue",
                            delta=f"Expected: {top['Expected %']:.1f}% | Actual: {top['Actual %']:.1f}%"
                        )
    
    with entry_col:
        # Compact manual entry section
        st.markdown("**➕ Quick Add Multiplier**")
        
        # Single entry with preset buttons in a compact form
        with st.container():
            rate_single = st.number_input(
                "Multiplier", 
                min_value=1.0, 
                max_value=1000.0, 
                value=1.5, 
                step=0.1, 
                key="quick_rate",
                label_visibility="collapsed",
                placeholder="Enter multiplier"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Add", type="primary", use_container_width=True):
                    add_manual_entry(rate_single)
                    st.success(f"Added {rate_single}x!")
                    st.rerun()
            
            with col2:
                if st.button("📦 Batch", use_container_width=True):
                    st.session_state.show_batch = not st.session_state.get('show_batch', False)
                    st.rerun()
        
        # Quick presets in a grid
        st.markdown("**Quick Presets**")
        preset_col1, preset_col2, preset_col3 = st.columns(3)
        with preset_col1:
            if st.button("1.0x", use_container_width=True, key="q1"):
                add_manual_entry(1.0)
                st.rerun()
            if st.button("2.0x", use_container_width=True, key="q2"):
                add_manual_entry(2.0)
                st.rerun()
        with preset_col2:
            if st.button("1.5x", use_container_width=True, key="q3"):
                add_manual_entry(1.5)
                st.rerun()
            if st.button("3.0x", use_container_width=True, key="q4"):
                add_manual_entry(3.0)
                st.rerun()
        with preset_col3:
            if st.button("5.0x", use_container_width=True, key="q5"):
                add_manual_entry(5.0)
                st.rerun()
            if st.button("10.0x", use_container_width=True, key="q6"):
                add_manual_entry(10.0)
                st.rerun()
        
        # Batch entry expander
        if st.session_state.get('show_batch', False):
            with st.expander("📦 Batch Entry", expanded=True):
                batch_rates = st.text_area(
                    "Enter multipliers (one per line)",
                    placeholder="1.5\n2.0\n1.2\n3.5\n10.0",
                    height=120,
                    key="batch_area"
                )
                if st.button("Add Batch", use_container_width=True):
                    if batch_rates.strip():
                        rates = [float(x.strip()) for x in batch_rates.split('\n') if x.strip()]
                        for rate in rates:
                            add_manual_entry(rate)
                        st.success(f"Added {len(rates)} multipliers!")
                        st.session_state.show_batch = False
                        st.rerun()
        
        # Show recent manual entries count
        if st.session_state.manual_entries:
            st.markdown("---")
            st.markdown(f"**📝 Recent ({len(st.session_state.manual_entries)} total)**")
            recent_manual = pd.DataFrame(st.session_state.manual_entries[-5:][::-1])
            for _, row in recent_manual.iterrows():
                rate = row['rate']
                if rate < 1.5:
                    color = "🟢"
                elif rate < 2.0:
                    color = "🟠"
                elif rate < 5.0:
                    color = "🟡"
                elif rate < 10.0:
                    color = "🔴"
                else:
                    color = "🟣"
                st.text(f"{color} {rate}x")
    
    # Divider
    st.markdown("---")
    
    # Manual entries stats row
    if st.session_state.manual_entries:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Manual", len(st.session_state.manual_entries))
        with col2:
            avg_manual = np.mean([e['rate'] for e in st.session_state.manual_entries])
            st.metric("Avg Manual", f"{avg_manual:.2f}x")
        with col3:
            max_manual = max([e['rate'] for e in st.session_state.manual_entries])
            st.metric("Max Manual", f"{max_manual:.2f}x")
        with col4:
            min_manual = min([e['rate'] for e in st.session_state.manual_entries])
            st.metric("Min Manual", f"{min_manual:.2f}x")
    
    # Real-time update indicator
    if st.session_state.manual_entries:
        st.info(f"🔄 Real-time: Last {len(st.session_state.manual_entries)} manual entries incorporated into overdue calculations above.")
    
    # Methodology explanation
    with st.expander("ℹ️ How 'Overdue' is calculated"):
        st.markdown("""
        **Methodology:**
        1. Calculate the **expected frequency** of each multiplier range from the complete historical dataset
        2. Calculate the **actual frequency** in the last N rounds
        3. **Overdue Score = Expected % - Actual %** (only when Expected > Actual)
        4. Higher score = more overdue
        
        **Example:** If a range appears 15% of the time historically, but only 5% in recent rounds, it has a 10% overdue score.
        
        ⚠️ **Disclaimer:** This is statistical analysis only. Crash multipliers are random and past patterns don't guarantee future results.
        """)

# ----- TAB 2: Multiplier Frequency Table -----
with main_tab2:
    st.header("Multiplier Frequency Distribution")
    
    # Add range column
    recent_df_copy = recent_df.copy()
    recent_df_copy['range'] = pd.cut(recent_df_copy['rate'], bins=bins, labels=labels, right=False)
    
    # Create frequency table
    freq_table = recent_df_copy['range'].value_counts().sort_index().reset_index()
    freq_table.columns = ['Multiplier Range', 'Frequency']
    freq_table['Percentage'] = (freq_table['Frequency'] / len(recent_df) * 100).round(1)
    freq_table['Cumulative %'] = freq_table['Percentage'].cumsum().round(1)
    
    # Display table
    st.dataframe(
        freq_table,
        column_config={
            "Multiplier Range": st.column_config.TextColumn("Range", width="medium"),
            "Frequency": st.column_config.NumberColumn("Count", width="small"),
            "Percentage": st.column_config.NumberColumn("Percentage", format="%.1f%%", width="small"),
            "Cumulative %": st.column_config.NumberColumn("Cumulative", format="%.1f%%", width="small")
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Bar chart and pie chart
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            freq_table, 
            x='Multiplier Range', 
            y='Frequency',
            title='Multiplier Frequency Distribution',
            color='Frequency',
            color_continuous_scale='Viridis',
            text='Frequency'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45, height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        major_cats = recent_df_copy.copy()
        major_cats['category'] = pd.cut(
            major_cats['rate'], 
            bins=[1.0, 2.0, 5.0, 10.0, float('inf')], 
            labels=['Low (1-2x)', 'Medium (2-5x)', 'High (5-10x)', 'Extreme (10x+)'],
            right=False
        )
        pie_data = major_cats['category'].value_counts()
        
        fig2 = px.pie(
            values=pie_data.values, 
            names=pie_data.index,
            title='Multiplier Categories Distribution',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        fig2.update_layout(height=500)
        st.plotly_chart(fig2, use_container_width=True)

# ----- TAB 3: Recent History -----
with main_tab3:
    st.header("Recent Crash History")
    
    # Show last 50 rounds with formatting
    display_df = recent_df.tail(50)[['gameId', 'rate', 'endTime_dt', 'duration_ms', 'data_source']].copy()
    display_df = display_df[::-1].reset_index(drop=True)
    display_df.columns = ['Game ID', 'Multiplier', 'Time', 'Duration (ms)', 'Source']
    
    # Color function for multipliers
    def color_rate(val):
        if isinstance(val, (int, float)):
            if val < 1.5:
                return 'background-color: #2ecc71; color: white'
            elif val < 2.0:
                return 'background-color: #f39c12; color: white'
            elif val < 5.0:
                return 'background-color: #e67e22; color: white'
            elif val < 10.0:
                return 'background-color: #e74c3c; color: white'
            else:
                return 'background-color: #8e44ad; color: white'
        return ''
    
    def color_source(val):
        if val == 'manual':
            return 'background-color: #3498db; color: white'
        return ''
    
    styled_df = display_df.style.map(color_rate, subset=['Multiplier']).map(color_source, subset=['Source'])
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Time series chart
    st.subheader("Multiplier Time Series")
    
    manual_mask = recent_df['data_source'] == 'manual' if 'data_source' in recent_df.columns else pd.Series([False] * len(recent_df))
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=recent_df.index,
        y=recent_df['rate'],
        mode='lines+markers',
        name='All Rounds',
        line=dict(color='#3498db', width=2),
        marker=dict(size=4, color=recent_df['rate'], colorscale='Viridis', showscale=True)
    ))
    
    if manual_mask.any():
        manual_df = recent_df[manual_mask]
        fig.add_trace(go.Scatter(
            x=manual_df.index,
            y=manual_df['rate'],
            mode='markers',
            name='Manual Entries',
            marker=dict(size=10, color='red', symbol='star')
        ))
    
    fig.add_hline(y=2.0, line_dash="dash", line_color="orange", annotation_text="2x")
    fig.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="5x")
    fig.add_hline(y=10.0, line_dash="dash", line_color="purple", annotation_text="10x")
    
    fig.update_layout(
        title='Crash Multipliers Over Time',
        xaxis_title='Round Number',
        yaxis_title='Multiplier (x)',
        height=450,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Rolling statistics
    st.subheader("Rolling Statistics")
    recent_df['rolling_avg_10'] = recent_df['rate'].rolling(window=10).mean()
    recent_df['rolling_max_10'] = recent_df['rate'].rolling(window=10).max()
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=recent_df.index,
        y=recent_df['rate'],
        mode='lines',
        name='Actual',
        line=dict(color='lightgray', width=1),
        opacity=0.5
    ))
    fig2.add_trace(go.Scatter(
        x=recent_df.index,
        y=recent_df['rolling_avg_10'],
        mode='lines',
        name='10-Round Avg',
        line=dict(color='#3498db', width=2)
    ))
    fig2.add_trace(go.Scatter(
        x=recent_df.index,
        y=recent_df['rolling_max_10'],
        mode='lines',
        name='10-Round Max',
        line=dict(color='#e74c3c', width=2, dash='dot')
    ))
    
    fig2.update_layout(
        title='Rolling Average and Maximum (10-round window)',
        xaxis_title='Round Number',
        yaxis_title='Multiplier (x)',
        height=400
    )
    st.plotly_chart(fig2, use_container_width=True)

# ----- TAB 4: Statistics -----
with main_tab4:
    st.header("Statistical Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Basic Statistics")
        stats_df = pd.DataFrame({
            'Metric': ['Mean (Average)', 'Median', 'Mode', 'Standard Deviation', 
                      'Variance', 'Minimum', 'Maximum', '25th Percentile', 
                      '75th Percentile', 'Interquartile Range (IQR)'],
            'Value': [
                f"{recent_df['rate'].mean():.2f}x",
                f"{recent_df['rate'].median():.2f}x",
                f"{recent_df['rate'].mode().iloc[0]:.2f}x" if not recent_df['rate'].mode().empty else "N/A",
                f"{recent_df['rate'].std():.2f}",
                f"{recent_df['rate'].var():.2f}",
                f"{recent_df['rate'].min():.2f}x",
                f"{recent_df['rate'].max():.2f}x",
                f"{recent_df['rate'].quantile(0.25):.2f}x",
                f"{recent_df['rate'].quantile(0.75):.2f}x",
                f"{recent_df['rate'].quantile(0.75) - recent_df['rate'].quantile(0.25):.2f}x"
            ]
        })
        st.dataframe(stats_df, hide_index=True, use_container_width=True)
        
        st.subheader("📈 Distribution Shape")
        shape_df = pd.DataFrame({
            'Metric': ['Skewness', 'Kurtosis', 'Is Normal Distribution?'],
            'Value': [
                f"{recent_df['rate'].skew():.2f} (Positive = right-skewed)",
                f"{recent_df['rate'].kurtosis():.2f} (High = heavy tails)",
                'No (highly skewed)' if abs(recent_df['rate'].skew()) > 1 else 'Approximately'
            ]
        })
        st.dataframe(shape_df, hide_index=True, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Probability Analysis")
        
        targets = [1.5, 2.0, 2.5, 3.0, 5.0, 10.0, 20.0, 50.0]
        probs = []
        cumulative = []
        
        for target in targets:
            prob = (recent_df['rate'] >= target).mean() * 100
            prob_below = (recent_df['rate'] < target).mean() * 100
            probs.append(prob)
            cumulative.append(prob_below)
        
        prob_df = pd.DataFrame({
            'Cash-out Target': [f"{t}x" for t in targets],
            'Success Probability': [f"{p:.1f}%" for p in probs],
            'Crash Below Target': [f"{c:.1f}%" for c in cumulative]
        })
        st.dataframe(prob_df, hide_index=True, use_container_width=True)
        
        st.info("""
        **💡 Risk-Reward Insight:**
        
        - **Conservative (1.5-2x)**: High success rate (60-75%), low returns
        - **Moderate (2-5x)**: Medium success rate (15-40%), balanced risk
        - **Aggressive (5-10x)**: Low success rate (5-15%), high potential
        - **Extreme (10x+)**: Very low success rate (<5%), lottery-style bets
        """)
    
    # Distribution histogram
    st.subheader("📊 Multiplier Distribution Histogram")
    
    fig = px.histogram(
        recent_df,
        x='rate',
        nbins=50,
        title='Distribution of Crash Multipliers',
        labels={'rate': 'Multiplier (x)', 'count': 'Frequency'},
        color_discrete_sequence=['#3498db'],
        opacity=0.8
    )
    
    fig.add_vline(x=recent_df['rate'].mean(), line_dash="dash", line_color="red", 
                  annotation_text=f"Mean: {recent_df['rate'].mean():.2f}x")
    fig.add_vline(x=recent_df['rate'].median(), line_dash="dash", line_color="green",
                  annotation_text=f"Median: {recent_df['rate'].median():.2f}x")
    
    fig.update_layout(height=500, bargap=0.05)
    st.plotly_chart(fig, use_container_width=True)
    
    # Cumulative probability
    st.subheader("📈 Cumulative Probability Curve")
    sorted_rates = np.sort(recent_df['rate'])
    cumulative_prob = np.arange(1, len(sorted_rates) + 1) / len(sorted_rates)
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=sorted_rates,
        y=cumulative_prob * 100,
        mode='lines',
        name='Cumulative Probability',
        fill='tozeroy',
        line=dict(color='#3498db', width=2)
    ))
    
    fig2.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50%")
    fig2.add_vline(x=recent_df['rate'].median(), line_dash="dash", line_color="red", 
                   annotation_text=f"Median: {recent_df['rate'].median():.2f}x")
    
    fig2.update_layout(
        title='Probability of Crashing at or Below Given Multiplier',
        xaxis_title='Multiplier (x)',
        yaxis_title='Probability (%)',
        height=450,
        yaxis_range=[0, 100]
    )
    st.plotly_chart(fig2, use_container_width=True)

# Data Management in sidebar
with st.sidebar.expander("💾 Data Management", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Data", use_container_width=True):
            if st.session_state.df is not None:
                csv = st.session_state.df[['gameId', 'rate', 'beginTime', 'endTime', 'data_source']].to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"bc_crash_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_btn"
                )
    
    with col2:
        if st.button("🗑️ Clear Manual", use_container_width=True):
            st.session_state.manual_entries = []
            if st.session_state.data_source == "file":
                if uploaded_file:
                    df_loaded = load_data_from_json(uploaded_file)
                    if df_loaded is not None:
                        st.session_state.df = df_loaded
            else:
                st.session_state.df = None
            st.success("Manual entries cleared!")
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <small>⚠️ <strong>Disclaimer:</strong> This tool is for educational and entertainment purposes only. 
    Crash games are random by design. Past performance does not indicate future results. 
    Always gamble responsibly.</small><br>
    <small>🔄 Manual entries are stored in session memory only and will be lost when the page is refreshed.</small>
</div>
""", unsafe_allow_html=True)

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.info("""
**How to use:**
1. Choose data source (File/Manual/Both)
2. Add multipliers manually or upload JSON
3. View overdue predictions in left panel
4. Add new multipliers in right panel
5. No scrolling needed - everything visible!

**Quick Entry:**
- Single multiplier input
- Preset buttons (1x, 1.5x, 2x, 3x, 5x, 10x)
- Batch entry for multiple multipliers
""")

if st.session_state.manual_entries:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Quick Stats")
    st.sidebar.metric("Manual Count", len(st.session_state.manual_entries))
    
    last_3 = pd.DataFrame(st.session_state.manual_entries[-3:])
    if not last_3.empty:
        st.sidebar.caption("Last 3 entries:")
        for _, row in last_3.iterrows():
            st.sidebar.text(f"• {row['rate']}x")

st.sidebar.markdown("---")
st.sidebar.caption(f"🔄 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
