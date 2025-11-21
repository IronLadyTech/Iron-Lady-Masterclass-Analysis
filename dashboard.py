import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from masterclass_analyzer import MasterclassAnalyzer
import json
import os

st.set_page_config(page_title="Masterclass Analytics", layout="wide", page_icon="📊")

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .hot { color: #28a745; font-weight: bold; }
    .warm { color: #ffc107; font-weight: bold; }
    .cold { color: #dc3545; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Masterclass Deep Analysis Dashboard")
st.markdown("---")

# Sidebar for file uploads
st.sidebar.header("📁 Upload Data Files")

zoom_participants = st.sidebar.file_uploader("Upload Zoom Participants CSV", type=['csv'])
zoom_chat = st.sidebar.file_uploader("Upload Zoom Chat Log (TXT)", type=['txt'])
crm_data = st.sidebar.file_uploader("Upload CRM Leads CSV", type=['csv'])

masterclass_duration = st.sidebar.number_input("Masterclass Duration (minutes)", value=60, min_value=10, max_value=180)

analyze_button = st.sidebar.button("🚀 Analyze", type="primary")

# Initialize analyzer
analyzer = MasterclassAnalyzer()

if analyze_button:
    if zoom_participants is None:
        st.error("❌ Please upload Zoom Participants file")
    else:
        with st.spinner("Processing data..."):
            # Save uploaded files temporarily
            os.makedirs('./temp', exist_ok=True)
            
            # Save participants file
            with open('./temp/participants.csv', 'wb') as f:
                f.write(zoom_participants.getbuffer())
            analyzer.load_zoom_participants('./temp/participants.csv')
            
            # Save chat file if provided
            if zoom_chat:
                with open('./temp/chat.txt', 'wb') as f:
                    f.write(zoom_chat.getbuffer())
                analyzer.load_zoom_chat('./temp/chat.txt')
            
            # Save CRM file if provided
            if crm_data:
                with open('./temp/crm.csv', 'wb') as f:
                    f.write(crm_data.getbuffer())
                analyzer.load_crm_data('./temp/crm.csv')
                analyzer.match_participants_with_crm()
            
            # Run analysis
            analyzer.calculate_engagement_scores(total_duration_mins=masterclass_duration)
            analyzer.analyze_exit_timeline(total_duration_mins=masterclass_duration)
            analyzer.get_inactive_leads_by_rm(min_score=40)
            analyzer.analyze_by_profile()  # Profile analysis
            analyzer.get_profile_insights()  # Profile insights
            summary = analyzer.generate_summary_stats()
            
            # Store in session state
            st.session_state['analyzer'] = analyzer
            st.session_state['analyzed'] = True
            
            st.success("✅ Analysis complete!")

# Display results if analysis is done
if st.session_state.get('analyzed', False):
    analyzer = st.session_state['analyzer']
    summary = analyzer.insights.get('summary', {})
    
    # Summary Stats
    st.header("📈 Overview Statistics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Participants", summary.get('total_participants', 0))
    with col2:
        st.metric("Avg Duration", f"{summary.get('avg_duration_mins', 0)} min")
    with col3:
        st.metric("🔥 Hot Leads", summary.get('hot_leads', 0), delta_color="normal")
    with col4:
        st.metric("🌡️ Warm Leads", summary.get('warm_leads', 0))
    with col5:
        st.metric("❄️ Cold Leads", summary.get('cold_leads', 0), delta_color="inverse")
    
    st.markdown("---")
    
    # Lead Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Lead Distribution")
        if analyzer.engagement_scores is not None and len(analyzer.engagement_scores) > 0:
            category_counts = analyzer.engagement_scores['category'].value_counts()
            
            fig = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                color=category_counts.index,
                color_discrete_map={'Hot': '#28a745', 'Warm': '#ffc107', 'Cold': '#dc3545'},
                hole=0.4
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💬 Engagement Overview")
        engagement_data = {
            'Metric': ['Total Messages', 'Questions Asked', 'Avg Score'],
            'Value': [
                summary.get('total_chat_messages', 0),
                summary.get('total_questions', 0),
                round(analyzer.engagement_scores['total_score'].mean(), 1) if analyzer.engagement_scores is not None else 0
            ]
        }
        st.dataframe(engagement_data, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    
    # Exit Timeline
    st.header("⏰ Exit Timeline Analysis")
    if 'exit_timeline' in analyzer.insights:
        timeline_df = analyzer.insights['exit_timeline']
        exit_stats = analyzer.insights.get('exit_stats', {})
        
        # Overall Statistics Section
        if exit_stats:
            st.subheader("📊 Overall Attendance Statistics")
            
            # Show warning if waiting room data exists
            if exit_stats.get('has_waiting_room_data') and exit_stats.get('waiting_room_count', 0) > 0:
                st.warning(f"""
                ⚠️ **Waiting Room Alert:** {exit_stats['waiting_room_count']} people ({round(exit_stats['waiting_room_count']/exit_stats['total_participants']*100, 1)}%) 
                were stuck in the waiting room and never admitted to the masterclass!
                
                Statistics below show data for **all {exit_stats['total_participants']} participants** (including waiting room).
                Scroll down to see data for **actual attendees only** ({exit_stats['actual_attendees']} people).
                """)
                st.markdown("---")
            
            # All Participants Stats (including waiting room if any)
            st.markdown(f"### 📈 All Participants ({exit_stats['total_participants']} people)")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Left in First 5 Minutes",
                    value=f"{exit_stats['left_0_5']} people",
                    delta=f"-{exit_stats['left_0_5_pct']}%",
                    delta_color="inverse"
                )
            
            with col2:
                st.metric(
                    label="Left in First 10 Minutes",
                    value=f"{exit_stats['left_0_10']} people",
                    delta=f"-{exit_stats['left_0_10_pct']}%",
                    delta_color="inverse"
                )
            
            with col3:
                st.metric(
                    label="Stayed 60+ Minutes",
                    value=f"{exit_stats['stayed_60_plus']} people",
                    delta=f"+{exit_stats['stayed_60_plus_pct']}%",
                    delta_color="normal"
                )
            
            with col4:
                st.metric(
                    label="Stayed 100+ Minutes",
                    value=f"{exit_stats['stayed_100_plus']} people",
                    delta=f"+{exit_stats['stayed_100_plus_pct']}%",
                    delta_color="normal"
                )
            
            # Actual Attendees Stats (excluding waiting room)
            if exit_stats.get('has_waiting_room_data') and exit_stats.get('waiting_room_count', 0) > 0:
                st.markdown("---")
                st.markdown(f"### ✅ Actual Attendees Only ({exit_stats['actual_attendees']} people)")
                st.info(f"""
                These statistics **exclude** the {exit_stats['waiting_room_count']} people stuck in waiting room.
                This shows TRUE engagement from people who were actually admitted to the masterclass.
                
                **Average Duration (Admitted):** {exit_stats['avg_duration_admitted']} minutes
                """)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        label="Left in First 5 Minutes",
                        value=f"{exit_stats['left_0_5_admitted']} people",
                        delta=f"-{exit_stats['left_0_5_admitted_pct']}%",
                        delta_color="inverse"
                    )
                
                with col2:
                    st.metric(
                        label="Left in First 10 Minutes",
                        value=f"{exit_stats['left_0_10_admitted']} people",
                        delta=f"-{exit_stats['left_0_10_admitted_pct']}%",
                        delta_color="inverse"
                    )
                
                with col3:
                    st.metric(
                        label="Stayed 60+ Minutes",
                        value=f"{exit_stats['stayed_60_plus_admitted']} people",
                        delta=f"+{exit_stats['stayed_60_plus_admitted_pct']}%",
                        delta_color="normal"
                    )
                
                with col4:
                    st.metric(
                        label="Stayed 100+ Minutes",
                        value=f"{exit_stats['stayed_100_plus_admitted']} people",
                        delta=f"+{exit_stats['stayed_100_plus_admitted_pct']}%",
                        delta_color="normal"
                    )
        
        st.markdown("---")
        
        # Drop-off Curve
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timeline_df['minute'],
            y=timeline_df['percentage'],
            mode='lines+markers',
            name='Attendance %',
            line=dict(color='#4c78a8', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title="Attendance Drop-off Curve",
            xaxis_title="Time (minutes)",
            yaxis_title="Attendance (%)",
            height=400,
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Critical moments
        st.subheader("⚠️ Critical Drop-off Moments")
        if 'critical_dropoff_moments' in analyzer.insights:
            critical = analyzer.insights['critical_dropoff_moments']
            st.dataframe(critical, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    
    # Profile Analysis Section
    st.header("👥 Participant Profile Analysis")
    
    if 'profile_analysis' in analyzer.insights and analyzer.insights['profile_analysis']:
        profile_data = analyzer.insights['profile_analysis']
        profile_df = pd.DataFrame(profile_data)
        
        # Profile comparison charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Average Engagement by Profile")
            fig = px.bar(
                profile_df,
                x='profile',
                y='avg_score',
                color='avg_score',
                color_continuous_scale=['#dc3545', '#ffc107', '#28a745'],
                text='avg_score',
                labels={'avg_score': 'Avg Score', 'profile': 'Profile'}
            )
            fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig.update_layout(
                height=400,
                showlegend=False,
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🎯 Hot Leads by Profile")
            fig = px.bar(
                profile_df,
                x='profile',
                y='hot_percentage',
                color='hot_percentage',
                color_continuous_scale='Reds',
                text='hot_count',
                labels={'hot_percentage': 'Hot %', 'profile': 'Profile'}
            )
            fig.update_traces(texttemplate='%{text} leads<br>(%{y:.1f}%)', textposition='outside')
            fig.update_layout(
                height=400,
                showlegend=False,
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Profile engagement breakdown
        st.subheader("📋 Detailed Profile Breakdown")
        
        # Format the dataframe for display
        display_df = profile_df[[
            'profile', 'total_count', 'avg_score', 'avg_duration',
            'hot_count', 'warm_count', 'cold_count', 'profile_engagement_level'
        ]].copy()
        
        display_df.columns = [
            'Profile', 'Total', 'Avg Score', 'Avg Duration (min)',
            'Hot', 'Warm', 'Cold', 'Engagement Level'
        ]
        
        # Style the dataframe
        def color_engagement_level(val):
            if val == 'High':
                return 'background-color: #d4edda'
            elif val == 'Medium':
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #f8d7da'
        
        styled_df = display_df.style.applymap(
            color_engagement_level, 
            subset=['Engagement Level']
        )
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
        # Profile Insights & Recommendations
        if 'profile_insights' in analyzer.insights and analyzer.insights['profile_insights']:
            st.subheader("💡 Profile Insights & Recommendations")
            
            insights = analyzer.insights['profile_insights']
            
            # Best performing
            if insights['best_performing_profile']:
                best = insights['best_performing_profile']
                st.success(f"🏆 **Top Performing Profile:** {best['profile']} (Avg Score: {best['avg_score']}/100)")
            
            # Recommendations
            if insights['recommendations']:
                st.markdown("**📌 Action Items:**")
                for rec in insights['recommendations']:
                    if rec['type'] == 'success':
                        st.success(f"**{rec['profile']}:** {rec['message']}")
                    elif rec['type'] == 'content_mismatch':
                        st.warning(f"**{rec['profile']}:** {rec['message']}")
                    elif rec['type'] == 'low_interaction':
                        st.info(f"**{rec['profile']}:** {rec['message']}")
            
            # Most engaged profiles
            if insights['most_engaged_profiles']:
                with st.expander(f"✅ High Engagement Profiles ({len(insights['most_engaged_profiles'])})"):
                    for profile in insights['most_engaged_profiles']:
                        st.write(f"- **{profile['profile']}**: {profile['avg_score']}/100 avg score, {profile['hot_percentage']:.1f}% hot leads")
            
            # Least engaged profiles
            if insights['least_engaged_profiles']:
                with st.expander(f"⚠️ Low Engagement Profiles ({len(insights['least_engaged_profiles'])})"):
                    for profile in insights['least_engaged_profiles']:
                        st.write(f"- **{profile['profile']}**: {profile['avg_score']}/100 avg score, {profile['avg_duration']:.0f} min avg duration")
        
        # Download profile analysis
        csv = profile_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Profile Analysis",
            data=csv,
            file_name="profile_analysis.csv",
            mime="text/csv"
        )
    else:
        st.info("ℹ️  Profile analysis not available. Ensure your CRM data includes a 'Profile', 'Industry', 'Profession', or 'Segment' column.")
    
    st.markdown("---")
    
    # Engagement Scores Table
    st.header("📋 Detailed Engagement Scores")
    if analyzer.engagement_scores is not None and len(analyzer.engagement_scores) > 0:
        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            category_filter = st.multiselect(
                "Filter by Category",
                options=['Hot', 'Warm', 'Cold'],
                default=['Hot', 'Warm', 'Cold']
            )
        with col2:
            rm_filter = st.multiselect(
                "Filter by RM",
                options=analyzer.engagement_scores['rm_name'].unique().tolist(),
                default=analyzer.engagement_scores['rm_name'].unique().tolist()
            )
        
        filtered_df = analyzer.engagement_scores[
            (analyzer.engagement_scores['category'].isin(category_filter)) &
            (analyzer.engagement_scores['rm_name'].isin(rm_filter))
        ]
        
        # Display with color coding
        def color_category(val):
            if val == 'Hot':
                return 'background-color: #d4edda'
            elif val == 'Warm':
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #f8d7da'
        
        styled_df = filtered_df.style.applymap(color_category, subset=['category'])
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Results",
            data=csv,
            file_name="engagement_scores.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    
    # RM Follow-ups
    st.header("👥 RM-wise Inactive Lead Follow-ups")
    if 'rm_follow_ups' in analyzer.insights:
        rm_follow_ups = analyzer.insights['rm_follow_ups']
        
        for rm_data in rm_follow_ups:
            with st.expander(f"🔔 {rm_data['rm_name']} - {rm_data['inactive_count']} inactive leads"):
                leads_df = pd.DataFrame(rm_data['leads'])
                st.dataframe(leads_df, hide_index=True, use_container_width=True)
                
                # Download button for this RM
                csv = leads_df.to_csv(index=False)
                st.download_button(
                    label=f"📥 Download {rm_data['rm_name']} Follow-ups",
                    data=csv,
                    file_name=f"followup_{rm_data['rm_name']}.csv",
                    mime="text/csv",
                    key=rm_data['rm_name']
                )
    
    st.markdown("---")
    
    # Export All Results
    st.header("💾 Export Complete Analysis")
    if st.button("📦 Export All Results"):
        analyzer.export_results('./output')
        st.success("✅ All results exported to './output' folder")
        
        # Provide download links
        with open('./output/summary.json', 'r') as f:
            summary_json = f.read()
        st.download_button(
            label="📄 Download Summary JSON",
            data=summary_json,
            file_name="masterclass_summary.json",
            mime="application/json"
        )

else:
    # Initial state - show instructions
    st.info("👆 Upload your files in the sidebar and click 'Analyze' to get started")
    
    st.markdown("""
    ## 📝 Required File Formats:
    
    ### 1. Zoom Participants CSV
    Must contain columns:
    - `Name` or `User Name`
    - `Email` or `User Email`
    - `Duration (Minutes)` or `Duration`
    
    ### 2. Zoom Chat Log (TXT)
    Format: `HH:MM:SS From [Name] to [Recipient]: [Message]`
    
    Example:
    ```
    10:30:45 From John Doe to Everyone: Great session!
    10:32:12 From Jane Smith to Everyone: Can you explain the pricing?
    ```
    
    ### 3. CRM Leads CSV (Optional but recommended)
    Must contain columns:
    - `Email` or `Lead Email`
    - `RM Name` (Relationship Manager name)
    - `RM Email` (Optional)
    
    ---
    
    ## 🎯 What You'll Get:
    - **Engagement Scores** for each participant (0-100 scale)
    - **Lead Categorization** (Hot/Warm/Cold)
    - **Exit Timeline** showing when people dropped off
    - **RM-wise Follow-up Lists** for inactive leads
    - **Downloadable Reports** for your team
    """)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ for Iron Lady | Powered by Streamlit")
