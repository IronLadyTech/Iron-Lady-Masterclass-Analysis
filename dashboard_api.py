"""
Masterclass Analytics Dashboard
With integrated Zoom & Zoho CRM API support
Updated with Experience Analysis and Improved Visualizations

Features:
- Pull data directly from Zoom API
- Pull data directly from Zoho CRM API
- Or upload CSV files manually
- Automatic deduplication
- Experience-based analysis
- Easy-to-read drop-off charts
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our modules
from masterclass_analyzer import MasterclassAnalyzer

# Check if API modules are available
API_AVAILABLE = False
try:
    from zoom_api import ZoomAPI
    from zoho_crm_api import ZohoCRMAPI
    API_AVAILABLE = True
except ImportError:
    pass

# Page config
st.set_page_config(
    page_title="Masterclass Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Masterclass Analytics Dashboard")

# Sidebar for data source selection
st.sidebar.header("⚙️ Data Source")

data_source = st.sidebar.radio(
    "Choose how to load data:",
    ["📁 Upload CSV Files", "🔌 Pull from APIs"],
    index=0
)

# Initialize session state
if 'participants_data' not in st.session_state:
    st.session_state.participants_data = None
if 'crm_data' not in st.session_state:
    st.session_state.crm_data = None
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = None

# ============================================
# DATA SOURCE: UPLOAD CSV FILES
# ============================================
if data_source == "📁 Upload CSV Files":
    st.sidebar.markdown("---")
    st.sidebar.subheader("📤 Upload Files")
    
    # File uploaders
    zoom_file = st.sidebar.file_uploader(
        "Zoom Participants CSV",
        type=['csv'],
        help="Export from Zoom Reports → Usage Reports → Meeting"
    )
    
    crm_file = st.sidebar.file_uploader(
        "Zoho CRM Export CSV (Optional)",
        type=['csv'],
        help="Export leads from Zoho CRM with Email, Industry, Experience fields"
    )
    
    chat_file = st.sidebar.file_uploader(
        "Zoom Chat File (Optional)",
        type=['txt'],
        help="Chat log from Zoom meeting"
    )
    
    masterclass_duration = st.sidebar.number_input(
        "Masterclass Duration (minutes)",
        min_value=30,
        max_value=300,
        value=120,
        help="Total duration of the masterclass"
    )
    
    if st.sidebar.button("🚀 Run Analysis", type="primary", use_container_width=True):
        if zoom_file is None:
            st.error("Please upload Zoom Participants CSV file")
        else:
            with st.spinner("Analyzing data..."):
                # Initialize analyzer
                analyzer = MasterclassAnalyzer()
                
                # Save uploaded file temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                    tmp.write(zoom_file.getvalue())
                    tmp_path = tmp.name
                
                # Load participants
                analyzer.load_zoom_participants(tmp_path)
                os.unlink(tmp_path)
                
                # Load CRM if provided
                if crm_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                        tmp.write(crm_file.getvalue())
                        tmp_path = tmp.name
                    analyzer.load_crm_data(tmp_path)
                    analyzer.match_participants_with_crm()
                    os.unlink(tmp_path)
                
                # Load chat if provided
                if chat_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
                        tmp.write(chat_file.getvalue())
                        tmp_path = tmp.name
                    analyzer.load_zoom_chat(tmp_path)
                    os.unlink(tmp_path)
                
                # Run analysis
                analyzer.calculate_engagement_scores(masterclass_duration)
                analyzer.analyze_exit_timeline(masterclass_duration)
                analyzer.analyze_by_profile()
                analyzer.analyze_by_experience()  # New!
                
                st.session_state.analyzer = analyzer
                st.success("✅ Analysis complete!")

# ============================================
# DATA SOURCE: PULL FROM APIs
# ============================================
elif data_source == "🔌 Pull from APIs":
    st.sidebar.markdown("---")
    
    if not API_AVAILABLE:
        st.sidebar.error("⚠️ API modules not found!")
        st.sidebar.markdown("""
        Make sure these files are in the same folder:
        - `zoom_api.py`
        - `zoho_crm_api.py`
        """)
    else:
        # Check credentials
        zoom_configured = all([
            os.getenv('ZOOM_ACCOUNT_ID'),
            os.getenv('ZOOM_CLIENT_ID'),
            os.getenv('ZOOM_CLIENT_SECRET')
        ])
        
        zoho_configured = all([
            os.getenv('ZOHO_CLIENT_ID'),
            os.getenv('ZOHO_CLIENT_SECRET'),
            os.getenv('ZOHO_REFRESH_TOKEN')
        ])
        
        st.sidebar.subheader("🔑 API Status")
        st.sidebar.markdown(f"📹 Zoom API: {'✅ Configured' if zoom_configured else '❌ Not configured'}")
        st.sidebar.markdown(f"📋 Zoho CRM: {'✅ Configured' if zoho_configured else '❌ Not configured'}")
        
        if not zoom_configured:
            st.sidebar.warning("Add Zoom credentials to .env file")
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📹 Zoom Meeting")
        
        # Option to list meetings or enter ID
        zoom_option = st.sidebar.radio(
            "Select meeting:",
            ["Enter Meeting ID", "Choose from Recent Meetings"]
        )
        
        meeting_id = None
        
        if zoom_option == "Enter Meeting ID":
            meeting_id = st.sidebar.text_input(
                "Meeting ID",
                placeholder="84405604610",
                help="Find this in Zoom meeting URL or reports"
            )
        else:
            if zoom_configured:
                if st.sidebar.button("🔄 Load Recent Meetings"):
                    with st.spinner("Fetching meetings from Zoom..."):
                        try:
                            zoom = ZoomAPI()
                            meetings = zoom.get_past_meetings()
                            st.session_state.zoom_meetings = meetings
                        except Exception as e:
                            st.sidebar.error(f"Error: {e}")
                
                if 'zoom_meetings' in st.session_state and st.session_state.zoom_meetings:
                    meeting_options = {
                        f"{m.get('topic', 'Untitled')} ({m.get('start_time', '')[:10]})": m.get('id')
                        for m in st.session_state.zoom_meetings[:20]
                    }
                    selected = st.sidebar.selectbox("Select meeting:", list(meeting_options.keys()))
                    if selected:
                        meeting_id = meeting_options[selected]
            else:
                st.sidebar.info("Configure Zoom API to list meetings")
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📋 Zoho CRM")
        
        include_crm = st.sidebar.checkbox(
            "Pull lead data from Zoho CRM",
            value=zoho_configured,
            disabled=not zoho_configured
        )
        
        st.sidebar.markdown("---")
        
        masterclass_duration = st.sidebar.number_input(
            "Masterclass Duration (minutes)",
            min_value=30,
            max_value=300,
            value=120
        )
        
        if st.sidebar.button("🚀 Pull & Analyze Data", type="primary", use_container_width=True):
            if not meeting_id:
                st.error("Please enter or select a Zoom Meeting ID")
            elif not zoom_configured:
                st.error("Zoom API credentials not configured in .env file")
            else:
                with st.spinner("Pulling data from APIs..."):
                    try:
                        # Initialize analyzer
                        analyzer = MasterclassAnalyzer()
                        
                        # Pull from Zoom
                        st.info("📹 Pulling participants from Zoom...")
                        zoom = ZoomAPI()
                        participants_df = zoom.get_meeting_participants(meeting_id, deduplicate=True)
                        
                        if participants_df.empty:
                            st.error("No participants found for this meeting")
                        else:
                            # Load into analyzer
                            analyzer.participants_data = participants_df
                            st.success(f"✅ Loaded {len(participants_df)} participants from Zoom")
                            
                            # Pull from Zoho if requested
                            if include_crm and zoho_configured:
                                st.info("📋 Pulling lead data from Zoho CRM...")
                                zoho = ZohoCRMAPI()
                                
                                # Get leads matching participant emails
                                emails = participants_df['email'].dropna().unique().tolist()
                                crm_df = zoho.get_leads_by_email(emails)
                                
                                if not crm_df.empty:
                                    analyzer.crm_data = crm_df
                                    analyzer.match_participants_with_crm()
                                    st.success(f"✅ Matched {len(crm_df)} leads from Zoho CRM")
                                else:
                                    st.warning("No matching leads found in Zoho CRM")
                            
                            # Run analysis
                            analyzer.calculate_engagement_scores(masterclass_duration)
                            analyzer.analyze_exit_timeline(masterclass_duration)
                            analyzer.analyze_by_profile()
                            analyzer.analyze_by_experience()  # New!
                            
                            st.session_state.analyzer = analyzer
                            st.success("✅ Analysis complete!")
                            
                    except Exception as e:
                        st.error(f"Error: {e}")
                        import traceback
                        st.code(traceback.format_exc())

# ============================================
# DISPLAY ANALYSIS RESULTS
# ============================================
if st.session_state.analyzer is not None:
    analyzer = st.session_state.analyzer
    
    st.markdown("---")
    
    # Summary Stats
    st.header("📈 Overview Statistics")
    
    summary = analyzer.generate_summary_stats()
    
    if summary:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Participants", summary['total_participants'])
        with col2:
            st.metric("Avg Duration", f"{summary['avg_duration_mins']} min")
        with col3:
            st.metric("🔥 Hot Leads", summary['hot_leads'])
        with col4:
            st.metric("🌡️ Warm Leads", summary['warm_leads'])
        with col5:
            st.metric("❄️ Cold Leads", summary['cold_leads'])
    
    st.markdown("---")
    
    # ============================================
    # EXIT TIMELINE ANALYSIS - IMPROVED CHARTS
    # ============================================
    st.header("⏰ Attendance Analysis")
    
    if 'exit_stats' in analyzer.insights:
        exit_stats = analyzer.insights['exit_stats']
        
        # Show warning if waiting room detected
        if exit_stats.get('has_waiting_room_data') and exit_stats.get('waiting_room_count', 0) > 0:
            st.warning(f"""
            ⚠️ **Waiting Room Alert:** {exit_stats['waiting_room_count']} people were stuck in the waiting room 
            and may not have attended the masterclass!
            """)
        
        # Key Retention Metrics - Easy to understand
        st.subheader("📊 Key Retention Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Use inverse color - low is good for early exits
            early_exit_pct = exit_stats['left_0_5_pct']
            st.metric(
                "❌ Left Early (< 5 min)",
                f"{exit_stats['left_0_5']} people",
                f"{early_exit_pct:.1f}%",
                delta_color="inverse"
            )
        with col2:
            st.metric(
                "⚠️ Left in 10 min",
                f"{exit_stats['left_0_10']} people",
                f"{exit_stats['left_0_10_pct']:.1f}%",
                delta_color="inverse"
            )
        with col3:
            st.metric(
                "✅ Stayed Full Hour",
                f"{exit_stats['stayed_60_plus']} people",
                f"{exit_stats['stayed_60_plus_pct']:.1f}%"
            )
        with col4:
            st.metric(
                "🌟 Super Engaged (100+ min)",
                f"{exit_stats['stayed_100_plus']} people",
                f"{exit_stats['stayed_100_plus_pct']:.1f}%"
            )
        
        # Visual Summary Bar - Easy to understand
        st.subheader("📈 Audience Retention Summary")
        
        # Create a simple horizontal bar showing retention
        retention_data = pd.DataFrame({
            'Status': ['Left in 5 min', 'Left in 5-10 min', 'Left in 10-60 min', 'Stayed 60+ min'],
            'Count': [
                exit_stats['left_0_5'],
                exit_stats['left_0_10'] - exit_stats['left_0_5'],
                exit_stats['total_participants'] - exit_stats['stayed_60_plus'] - exit_stats['left_0_10'],
                exit_stats['stayed_60_plus']
            ],
            'Color': ['#ff4444', '#ffaa00', '#ffcc00', '#44aa44']
        })
        
        fig_retention = go.Figure(go.Bar(
            x=retention_data['Count'],
            y=retention_data['Status'],
            orientation='h',
            marker_color=['#ff4444', '#ff8844', '#ffcc44', '#44bb44'],
            text=retention_data['Count'],
            textposition='auto',
        ))
        
        fig_retention.update_layout(
            title="How long did people stay?",
            xaxis_title="Number of People",
            yaxis_title="",
            height=250,
            showlegend=False,
            yaxis={'categoryorder': 'array', 'categoryarray': ['Stayed 60+ min', 'Left in 10-60 min', 'Left in 5-10 min', 'Left in 5 min']}
        )
        
        st.plotly_chart(fig_retention, use_container_width=True)
        
        # Success Rate Gauge
        col1, col2 = st.columns(2)
        
        with col1:
            # Retention Rate Gauge - Easy to understand
            retention_rate = exit_stats['stayed_60_plus_pct']
            
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=retention_rate,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Retention Rate (stayed 60+ min)", 'font': {'size': 18}},
                delta={'reference': 40, 'suffix': '% vs avg'},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1},
                    'bar': {'color': "#44bb44" if retention_rate >= 50 else "#ffaa00"},
                    'steps': [
                        {'range': [0, 30], 'color': '#ffcccc'},
                        {'range': [30, 50], 'color': '#fff3cd'},
                        {'range': [50, 100], 'color': '#d4edda'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 40
                    }
                }
            ))
            
            fig_gauge.update_layout(height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            # Interpretation
            if retention_rate >= 70:
                st.success("🎉 **Excellent!** Your retention is outstanding!")
            elif retention_rate >= 50:
                st.success("✅ **Good!** Above industry average of 40%")
            elif retention_rate >= 40:
                st.info("📊 **Average** - Meeting industry standard")
            else:
                st.warning("⚠️ **Below Average** - Consider improving content or timing")
        
        with col2:
            # Pie chart - Easy to understand
            pie_data = pd.DataFrame({
                'Category': ['Stayed Full Session (60+ min)', 'Left Early (< 60 min)'],
                'Count': [exit_stats['stayed_60_plus'], exit_stats['total_participants'] - exit_stats['stayed_60_plus']]
            })
            
            fig_pie = px.pie(
                pie_data,
                values='Count',
                names='Category',
                title="Overall Retention",
                color='Category',
                color_discrete_map={
                    'Stayed Full Session (60+ min)': '#44bb44',
                    'Left Early (< 60 min)': '#ff8844'
                },
                hole=0.4
            )
            
            fig_pie.update_traces(textposition='outside', textinfo='percent+label')
            fig_pie.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Detailed Drop-off Timeline (Collapsible)
    with st.expander("📉 Detailed Drop-off Timeline (Click to expand)"):
        if 'exit_timeline' in analyzer.insights:
            timeline_df = analyzer.insights['exit_timeline']
            
            # Create area chart - easier to read than line
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=timeline_df['minute'],
                y=timeline_df['percentage'],
                mode='lines',
                name='Attendance %',
                line=dict(color='#4c78a8', width=3),
                fill='tozeroy',
                fillcolor='rgba(76, 120, 168, 0.3)'
            ))
            
            # Add key milestone markers
            fig.add_hline(y=50, line_dash="dash", line_color="orange", 
                         annotation_text="50% mark", annotation_position="right")
            
            fig.update_layout(
                title="Audience Remaining Over Time",
                xaxis_title="Minutes into Masterclass",
                yaxis_title="% of Audience Still Watching",
                height=400,
                hovermode='x unified',
                yaxis=dict(range=[0, 105])
            )
            
            # Add annotations for key points
            fig.add_annotation(x=5, y=timeline_df[timeline_df['minute']==5]['percentage'].values[0] if 5 in timeline_df['minute'].values else 95,
                             text="5 min mark", showarrow=True, arrowhead=2)
            fig.add_annotation(x=60, y=timeline_df[timeline_df['minute']==60]['percentage'].values[0] if 60 in timeline_df['minute'].values else 70,
                             text="1 hour mark", showarrow=True, arrowhead=2)
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption("📖 **How to read:** The graph shows what percentage of attendees were still watching at each minute. Higher is better!")
    
    st.markdown("---")
    
    # ============================================
    # EXPERIENCE-BASED ANALYSIS - NEW!
    # ============================================
    if 'experience_analysis' in analyzer.insights and analyzer.insights['experience_analysis']:
        st.header("👔 Analysis by Years of Experience")
        
        exp_data = analyzer.insights['experience_analysis']
        exp_df = pd.DataFrame(exp_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart of counts by experience
            fig_exp_count = px.bar(
                exp_df,
                x='experience_level',
                y='total_count',
                title="Participants by Experience Level",
                color='avg_score',
                color_continuous_scale='Viridis',
                labels={'experience_level': 'Experience', 'total_count': 'Number of People'}
            )
            fig_exp_count.update_layout(height=350)
            st.plotly_chart(fig_exp_count, use_container_width=True)
        
        with col2:
            # Engagement score by experience
            fig_exp_score = px.bar(
                exp_df,
                x='experience_level',
                y='avg_score',
                title="Engagement Score by Experience",
                color='hot_percentage',
                color_continuous_scale='Reds',
                labels={'experience_level': 'Experience', 'avg_score': 'Avg Engagement Score'}
            )
            fig_exp_score.update_layout(height=350)
            st.plotly_chart(fig_exp_score, use_container_width=True)
        
        # Experience insights table
        st.subheader("📊 Detailed Experience Breakdown")
        
        # Format for display
        display_exp_df = exp_df.copy()
        display_exp_df = display_exp_df.rename(columns={
            'experience_level': 'Experience Level',
            'total_count': 'Total',
            'avg_score': 'Avg Score',
            'avg_duration': 'Avg Duration (min)',
            'hot_count': '🔥 Hot',
            'warm_count': '🌡️ Warm',
            'cold_count': '❄️ Cold',
            'hot_percentage': 'Hot %',
            'stayed_60_plus_pct': 'Stayed 60+ min %'
        })
        
        st.dataframe(
            display_exp_df[['Experience Level', 'Total', 'Avg Score', 'Avg Duration (min)', 
                           '🔥 Hot', '🌡️ Warm', '❄️ Cold', 'Hot %', 'Stayed 60+ min %']],
            hide_index=True,
            use_container_width=True
        )
        
        # Key insight
        if len(exp_df) > 1:
            best_exp = exp_df.loc[exp_df['avg_score'].idxmax()]
            st.info(f"💡 **Key Insight:** People with **{best_exp['experience_level']}** experience showed the highest engagement (score: {best_exp['avg_score']})")
    
    st.markdown("---")
    
    # ============================================
    # ENGAGEMENT SCORES
    # ============================================
    st.header("🎯 Engagement Analysis")
    
    if analyzer.engagement_scores is not None and len(analyzer.engagement_scores) > 0:
        # Category distribution
        col1, col2 = st.columns(2)
        
        with col1:
            category_counts = analyzer.engagement_scores['category'].value_counts()
            fig = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                title="Lead Category Distribution",
                color=category_counts.index,
                color_discrete_map={'Hot': '#ff4444', 'Warm': '#ffaa00', 'Cold': '#4444ff'}
            )
            fig.update_traces(textposition='outside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.histogram(
                analyzer.engagement_scores,
                x='total_score',
                nbins=20,
                title="Engagement Score Distribution",
                labels={'total_score': 'Engagement Score'},
                color_discrete_sequence=['#4c78a8']
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # Top engaged participants
        st.subheader("🔥 Top Engaged Participants")
        top_engaged = analyzer.engagement_scores.nlargest(10, 'total_score')
        display_cols = ['email', 'name', 'total_score', 'category', 'duration_mins']
        if 'rm_name' in top_engaged.columns:
            display_cols.append('rm_name')
        if 'experience_years' in top_engaged.columns:
            display_cols.append('experience_years')
        if 'profile' in top_engaged.columns:
            display_cols.append('profile')
        
        available_cols = [c for c in display_cols if c in top_engaged.columns]
        st.dataframe(top_engaged[available_cols], hide_index=True, use_container_width=True)
    
    st.markdown("---")
    
    # ============================================
    # PROFILE ANALYSIS
    # ============================================
    if 'profile_analysis' in analyzer.insights and analyzer.insights['profile_analysis']:
        st.header("👥 Analysis by Industry/Profile")
        
        profile_data = analyzer.insights['profile_analysis']
        profile_df = pd.DataFrame(profile_data)
        
        if len(profile_df) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    profile_df.head(10),
                    x='profile',
                    y='avg_score',
                    color='hot_percentage',
                    color_continuous_scale='Reds',
                    title="Top 10 Profiles by Engagement"
                )
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    profile_df.head(10),
                    x='profile',
                    y='total_count',
                    color='avg_duration',
                    color_continuous_scale='Viridis',
                    title="Participation by Profile"
                )
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Profile insights table
            st.dataframe(
                profile_df[['profile', 'total_count', 'avg_score', 'avg_duration', 'hot_count', 'warm_count', 'cold_count']].head(15),
                hide_index=True,
                use_container_width=True
            )
    
    st.markdown("---")
    
    # ============================================
    # DOWNLOAD SECTION
    # ============================================
    st.header("📥 Download Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if analyzer.engagement_scores is not None:
            csv = analyzer.engagement_scores.to_csv(index=False)
            st.download_button(
                "📊 Download Engagement Scores (CSV)",
                csv,
                "engagement_scores.csv",
                "text/csv",
                use_container_width=True
            )
    
    with col2:
        if analyzer.engagement_scores is not None:
            # Create Excel with multiple sheets
            import io
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                analyzer.engagement_scores.to_excel(writer, sheet_name='Engagement Scores', index=False)
                
                if 'exit_timeline' in analyzer.insights:
                    analyzer.insights['exit_timeline'].to_excel(writer, sheet_name='Exit Timeline', index=False)
                
                if 'profile_analysis' in analyzer.insights and analyzer.insights['profile_analysis']:
                    pd.DataFrame(analyzer.insights['profile_analysis']).to_excel(
                        writer, sheet_name='Profile Analysis', index=False
                    )
                
                if 'experience_analysis' in analyzer.insights and analyzer.insights['experience_analysis']:
                    pd.DataFrame(analyzer.insights['experience_analysis']).to_excel(
                        writer, sheet_name='Experience Analysis', index=False
                    )
            
            st.download_button(
                "📑 Download Full Report (Excel)",
                buffer.getvalue(),
                "masterclass_report.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    with col3:
        # Summary text report
        if 'exit_stats' in analyzer.insights:
            exit_stats = analyzer.insights['exit_stats']
            summary_text = f"""
MASTERCLASS ANALYTICS SUMMARY
=============================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

OVERVIEW
--------
Total Participants: {exit_stats['total_participants']}
Average Duration: {analyzer.engagement_scores['duration_mins'].mean():.1f} minutes

RETENTION METRICS
-----------------
Left in 5 minutes: {exit_stats['left_0_5']} ({exit_stats['left_0_5_pct']:.1f}%)
Left in 10 minutes: {exit_stats['left_0_10']} ({exit_stats['left_0_10_pct']:.1f}%)
Stayed 60+ minutes: {exit_stats['stayed_60_plus']} ({exit_stats['stayed_60_plus_pct']:.1f}%)
Stayed 100+ minutes: {exit_stats['stayed_100_plus']} ({exit_stats['stayed_100_plus_pct']:.1f}%)

LEAD CATEGORIES
---------------
Hot Leads: {len(analyzer.engagement_scores[analyzer.engagement_scores['category'] == 'Hot'])}
Warm Leads: {len(analyzer.engagement_scores[analyzer.engagement_scores['category'] == 'Warm'])}
Cold Leads: {len(analyzer.engagement_scores[analyzer.engagement_scores['category'] == 'Cold'])}

INTERPRETATION
--------------
"""
            if exit_stats['stayed_60_plus_pct'] >= 70:
                summary_text += "🎉 EXCELLENT retention! Well above industry average."
            elif exit_stats['stayed_60_plus_pct'] >= 50:
                summary_text += "✅ GOOD retention - above industry average of 40%."
            else:
                summary_text += "⚠️ Below average retention - consider content improvements."
            
            st.download_button(
                "📝 Download Summary (Text)",
                summary_text,
                "masterclass_summary.txt",
                "text/plain",
                use_container_width=True
            )

else:
    # Show instructions when no data loaded
    st.info("👈 Select a data source and load data to see analysis")
    
    st.markdown("""
    ### 📚 How to Use This Dashboard
    
    **Option 1: Upload CSV Files**
    1. Export participant report from Zoom
    2. Optionally export leads from Zoho CRM (with Email, Industry, Experience fields)
    3. Upload files and click "Run Analysis"
    
    **Option 2: Pull from APIs**
    1. Configure API credentials in `.env` file
    2. Enter Zoom Meeting ID or select from list
    3. Click "Pull & Analyze Data"
    
    ### 📊 What You'll Get
    - Easy-to-read retention metrics
    - Experience-based engagement analysis (NEW!)
    - Industry/Profile insights
    - Hot/Warm/Cold lead categorization
    - Downloadable reports
    
    ### 📋 Zoho CRM Fields Used
    - **Email** - For matching with Zoom
    - **Lead Owner** - RM assignment
    - **Industry/Field of Work** - Profile analysis
    - **Total Years Of Experience.** - Experience analysis (NEW!)
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Iron Lady Masterclass Analytics | Built with Streamlit</div>",
    unsafe_allow_html=True
)