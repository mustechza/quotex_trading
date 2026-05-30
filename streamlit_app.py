import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import json
from collections import Counter
import io

# Page configuration
st.set_page_config(
    page_title="BC.Game Crash Analyzer",
    page_icon="🎲",
    layout="wide"
)

# Title and description
st.title("🎲 BC.Game Crash Multiplier Tracker")
st.markdown("""
This app analyzes crash multipliers from BC.Game JSON data to identify patterns and predict **most overdue multipliers** 
based on historical frequency of occurrence.
""")

# Sidebar controls
st.sidebar.header("⚙️ Settings")

def load_data_from_json(file):
    """Load and process BC.Game crash JSON data"""
    try:
        # Read JSON file
        data = json.load(file)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Convert rate to float (it might be stored as string)
        df['rate'] = df['rate'].astype(float)
        
        # Convert timestamps to datetime
        df['beginTime_dt'] = pd.to_datetime(df['beginTime'], unit='ms')
        df['endTime_dt'] = pd.to_datetime(df['endTime'], unit='ms')
        df['prepareTime_dt'] = pd.to_datetime(df['prepareTime'], unit='ms')
        df['fetchedAt_dt'] = pd.to_datetime(df['fetchedAt'])
        
        # Calculate game duration
        df['duration_ms'] = df['endTime'] - df['beginTime']
        
        # Sort by endTime (most recent last)
        df = df.sort_values('endTime', ascending=True).reset_index(drop=True)
        
        return df
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

# File upload
uploaded_file = st.sidebar.file_uploader("Upload BC.Game JSON file", type=['json'])

if uploaded_file is not None:
    df = load_data_from_json(uploaded_file)
    if df is None:
        st.stop()
    st.sidebar.success(f"✅ Loaded {len(df)} rounds successfully!")
else:
    st.warning("⚠️ Please upload a BC.Game crash JSON file to begin analysis")
    st.info("📁 Expected format: JSON array with fields: gameId, hash, beginTime, endTime, rate, etc.")
    
    # Show example of expected format
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
    st.stop()

# Get last N rounds
n_rounds = st.sidebar.slider("Number of recent rounds to analyze", 50, min(500, len(df)), min(100, len(df)))
recent_df = df.tail(n_rounds).copy()
recent_df = recent_df.reset_index(drop=True)

# Display basic stats
col1, col2, col3, col4, col5 = st.columns(5)
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

# Game info
st.caption(f"📅 Data range: {df['endTime_dt'].min().strftime('%Y-%m-%d %H:%M:%S')} to {df['endTime_dt'].max().strftime('%Y-%m-%d %H:%M:%S')}")

# Define multiplier ranges
bins = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0, 15.0, 25.0, 50.0, 100.0, float('inf')]
labels = ['1.00-1.50', '1.51-2.00', '2.01-2.50', '2.51-3.00', '3.01-4.00', 
          '4.01-5.00', '5.01-7.50', '7.51-10.00', '10.01-15.00', 
          '15.01-25.00', '25.01-50.00', '50.01-100.00', '100.00+']

# Tab layout
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Frequency Table", "🎯 Most Overdue", "📈 Recent History", "📉 Statistics", "📋 Raw Data"])

# ----- TAB 1: Multiplier Frequency Table -----
with tab1:
    st.header("Multiplier Frequency Distribution")
    
    # Add range column
    recent_df_copy = recent_df.copy()
    recent_df_copy['range'] = pd.cut(recent_df_copy['rate'], bins=bins, labels=labels, right=False)
    
    # Create frequency table
    freq_table = recent_df_copy['range'].value_counts().sort_index().reset_index()
    freq_table.columns = ['Multiplier Range', 'Frequency']
    freq_table['Percentage'] = (freq_table['Frequency'] / len(recent_df) * 100).round(1)
    
    # Add cumulative percentage
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
    
    # Bar chart
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
        # Pie chart for major categories
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

# ----- TAB 2: Most Overdue Multipliers -----
with tab2:
    st.header("🎯 Most Overdue Multipliers")
    st.markdown("""
    Based on **historical frequency from all data**, these multiplier ranges are **"overdue"** - meaning they've appeared 
    less frequently than expected in recent rounds.
    """)
    
    # Calculate expected frequency based on FULL historical data
    full_df_copy = df.copy()
    full_df_copy['range'] = pd.cut(full_df_copy['rate'], bins=bins, labels=labels, right=False)
    historical_freq = full_df_copy['range'].value_counts(normalize=True)
    
    # Calculate current frequency in recent rounds
    current_freq = recent_df_copy['range'].value_counts(normalize=True)
    
    # Calculate overdue score (expected - actual)
    overdue_scores = {}
    for label in labels:
        expected = historical_freq.get(label, 0)
        actual = current_freq.get(label, 0)
        # If expected > actual, it's overdue
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
    overdue_df = overdue_df.sort_values('Overdue Score', ascending=False).head(10)
    
    # Highlight top overdue
    col1, col2 = st.columns([2, 1])
    
    with col1:
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
            use_container_width=True
        )
    
    with col2:
        if len(overdue_df) > 0:
            top_overdue = overdue_df.iloc[0]['Range']
            top_score = overdue_df.iloc[0]['Overdue Score']
            st.success(f"### 🔥 Most Overdue\n\n**{top_overdue}**\n\nOverdue by **{top_score:.1f}%**")
            
            if len(overdue_df) > 1:
                st.info(f"### 🥈 Runner Up\n\n**{overdue_df.iloc[1]['Range']}**\n\nOverdue by **{overdue_df.iloc[1]['Overdue Score']:.1f}%**")
    
    # Visualize top overdue
    fig = px.bar(
        overdue_df.head(7),
        x='Range',
        y='Overdue Score',
        title='Top 7 Most Overdue Multiplier Ranges',
        color='Overdue Score',
        color_continuous_scale='Reds',
        text='Overdue Score'
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(xaxis_tickangle=-45, height=450)
    st.plotly_chart(fig, use_container_width=True)
    
    # Explanation
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

# ----- TAB 3: Recent History -----
with tab3:
    st.header("Recent Crash History")
    
    # Show last 50 rounds with formatting
    display_df = recent_df.tail(50)[['gameId', 'rate', 'endTime_dt', 'duration_ms']].copy()
    display_df = display_df[::-1].reset_index(drop=True)  # Reverse for chronological order
    display_df.columns = ['Game ID', 'Multiplier', 'Time', 'Duration (ms)']
    
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
    
    styled_df = display_df.style.map(color_rate, subset=['Multiplier'])
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Time series chart
    st.subheader("Multiplier Time Series (Last 100 Rounds)")
    
    fig = go.Figure()
    
    # Add line
    fig.add_trace(go.Scatter(
        x=recent_df.index,
        y=recent_df['rate'],
        mode='lines+markers',
        name='Multiplier',
        line=dict(color='#3498db', width=2),
        marker=dict(size=4, color=recent_df['rate'], colorscale='Viridis', showscale=True)
    ))
    
    # Add horizontal lines
    fig.add_hline(y=2.0, line_dash="dash", line_color="orange", annotation_text="2x", annotation_position="top right")
    fig.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="5x", annotation_position="top right")
    fig.add_hline(y=10.0, line_dash="dash", line_color="purple", annotation_text="10x", annotation_position="top right")
    
    fig.update_layout(
        title='Crash Multipliers Over Time',
        xaxis_title='Round Number (recent to oldest)',
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
with tab4:
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
        
        # Skewness and Kurtosis
        from scipy import stats
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
        
        # Calculate probabilities for different cash-out targets
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
        
        # Risk insight
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
    
    # Add vertical lines for mean and median
    fig.add_vline(x=recent_df['rate'].mean(), line_dash="dash", line_color="red", 
                  annotation_text=f"Mean: {recent_df['rate'].mean():.2f}x", annotation_position="top")
    fig.add_vline(x=recent_df['rate'].median(), line_dash="dash", line_color="green",
                  annotation_text=f"Median: {recent_df['rate'].median():.2f}x", annotation_position="bottom")
    
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
    
    # Add reference lines
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

# ----- TAB 5: Raw Data -----
with tab5:
    st.header("Raw Data Export")
    
    # Show recent data
    st.subheader(f"Last {len(recent_df)} Rounds")
    raw_display = recent_df[['gameId', 'rate', 'endTime_dt', 'beginTime_dt', 'duration_ms']].copy()
    raw_display.columns = ['Game ID', 'Multiplier', 'End Time', 'Start Time', 'Duration (ms)']
    
    st.dataframe(raw_display, use_container_width=True, height=400)
    
    # Export options
    st.subheader("Export Data")
    col1, col2 = st.columns(2)
    
    with col1:
        # Export to CSV
        csv = recent_df[['gameId', 'rate', 'beginTime', 'endTime']].to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"bc_crash_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Summary statistics export
        summary = recent_df['rate'].describe().to_frame()
        summary.columns = ['Value']
        summary_csv = summary.to_csv()
        st.download_button(
            label="📊 Download Summary Stats",
            data=summary_csv,
            file_name=f"bc_crash_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # File info
    with st.expander("ℹ️ Data Source Information"):
        st.json({
            "Total Rounds": len(df),
            "Time Range": {
                "Start": df['endTime_dt'].min().isoformat(),
                "End": df['endTime_dt'].max().isoformat()
            },
            "File Uploaded": uploaded_file.name if uploaded_file else "None",
            "Analysis Date": datetime.now().isoformat()
        })

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <small>⚠️ <strong>Disclaimer:</strong> This tool is for educational and entertainment purposes only. 
    Crash games are random by design. Past performance does not indicate future results. 
    Always gamble responsibly.</small>
</div>
""", unsafe_allow_html=True)

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.info("""
**How to use:**
1. Upload your BC.Game crash JSON file
2. Adjust the number of rounds to analyze
3. Check frequency distribution
4. Find most overdue multipliers
5. Analyze statistics and probabilities

**File format:** JSON array with game objects containing `rate`, `gameId`, `beginTime`, `endTime`, etc.
""")

st.sidebar.markdown("---")
st.sidebar.caption(f"🔄 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
