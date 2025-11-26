"""
Iron Lady Masterclass Analytics Dashboard
Complete System with robust file parsing
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import json
import os
import tempfile
import io

# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================
st.set_page_config(
    page_title="Masterclass Analytics",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    div[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# MASTERCLASS ANALYZER CLASS
# ============================================================================
class MasterclassAnalyzer:
    def __init__(self):
        self.participants_data = None
        self.chat_data = None
        self.crm_data = None
        self.engagement_scores = None
        self.insights = {}
    
    def load_zoom_participants(self, file_content):
        """
        Load Zoom participant report with automatic format detection
        Handles the Zoom export format with metadata rows
        """
        try:
            # Handle both file path and file content
            if isinstance(file_content, str):
                with open(file_content, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
            else:
                content = file_content.decode('utf-8-sig')
            
            # Split into lines
            lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            
            # Find the participant data header row (contains "Email" and "Duration")
            header_row_idx = None
            for i, line in enumerate(lines):
                if 'Email' in line and 'Duration' in line and 'Name' in line:
                    header_row_idx = i
                    break
            
            if header_row_idx is None:
                st.error("Could not find participant data header in Zoom file")
                return False
            
            # Extract participant data starting from header
            participant_lines = lines[header_row_idx:]
            participant_content = '\n'.join(participant_lines)
            
            # Parse as CSV
            df = pd.read_csv(io.StringIO(participant_content))
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Standardize column names for internal use
            col_mapping = {}
            for col in df.columns:
                col_lower = col.lower().replace(' ', '_').replace('(', '').replace(')', '')
                if 'email' in col_lower:
                    col_mapping[col] = 'email'
                elif 'name' in col_lower and 'original' in col_lower:
                    col_mapping[col] = 'name'
                elif 'duration' in col_lower and 'minute' in col_lower:
                    col_mapping[col] = 'duration_mins'
                elif 'join' in col_lower and 'time' in col_lower:
                    col_mapping[col] = 'join_time'
                elif 'leave' in col_lower and 'time' in col_lower:
                    col_mapping[col] = 'leave_time'
                elif 'waiting' in col_lower and 'room' in col_lower:
                    col_mapping[col] = 'in_waiting_room'
            
            df = df.rename(columns=col_mapping)
            
            # Convert duration to numeric
            if 'duration_mins' in df.columns:
                df['duration_mins'] = pd.to_numeric(df['duration_mins'], errors='coerce').fillna(0)
            else:
                # Try to find any duration column
                for col in df.columns:
                    if 'duration' in col.lower():
                        df['duration_mins'] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        break
                else:
                    df['duration_mins'] = 0
            
            # Normalize email
            if 'email' in df.columns:
                df['email'] = df['email'].astype(str).str.strip().str.lower()
                df = df[df['email'].notna() & (df['email'] != '') & (df['email'] != 'nan')]
            
            # Deduplicate by email - sum durations for people who rejoined
            if 'email' in df.columns:
                original_count = len(df)
                
                # Group by email and aggregate
                agg_dict = {'duration_mins': 'sum'}
                for col in df.columns:
                    if col not in ['email', 'duration_mins']:
                        agg_dict[col] = 'first'
                
                df = df.groupby('email', as_index=False).agg(agg_dict)
                
                if len(df) < original_count:
                    st.info(f"📧 Deduplicated {original_count} → {len(df)} unique participants")
            
            self.participants_data = df
            return True
            
        except Exception as e:
            st.error(f"Error loading participants: {e}")
            import traceback
            st.code(traceback.format_exc())
            return False
    
    def load_zoom_chat(self, file_content):
        """Load Zoom chat log with multiple format support"""
        try:
            # Handle both file path and file content
            if isinstance(file_content, str):
                with open(file_content, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
            else:
                content = file_content.decode('utf-8-sig')
            
            chat_records = []
            
            # Pattern 1: "2025-11-21 18:57:45 From Name to Everyone:"
            pattern1 = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+From\s+(.+?)\s+to\s+(.+?):\s*\n?\t*(.+?)(?=\n\d{4}-\d{2}-\d{2}|\Z)'
            matches1 = re.findall(pattern1, content, re.DOTALL | re.IGNORECASE)
            
            # Pattern 2: "10:30:45 From Name to Everyone:"
            pattern2 = r'(\d{2}:\d{2}:\d{2})\s+From\s+(.+?)\s+to\s+(.+?):\s*(.+?)(?=\n\d{2}:\d{2}:\d{2}|\Z)'
            matches2 = re.findall(pattern2, content, re.DOTALL | re.IGNORECASE)
            
            matches = matches1 if len(matches1) >= len(matches2) else matches2
            
            for match in matches:
                timestamp, sender, recipient, message = match
                msg_clean = message.strip()
                if msg_clean:  # Skip empty messages
                    chat_records.append({
                        'timestamp': timestamp.strip(),
                        'sender': sender.strip(),
                        'recipient': recipient.strip(),
                        'message': msg_clean,
                        'is_question': '?' in msg_clean
                    })
            
            self.chat_data = pd.DataFrame(chat_records) if chat_records else pd.DataFrame()
            return True
            
        except Exception as e:
            st.error(f"Error loading chat: {e}")
            return False
    
    def load_crm_data(self, file_content):
        """Load CRM data with flexible column detection"""
        try:
            # Handle both file path and file content
            if isinstance(file_content, str):
                df = pd.read_csv(file_content, encoding='utf-8-sig')
            else:
                df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8-sig')
            
            # Remove completely empty rows
            df = df.dropna(how='all')
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Find and map columns
            email_col = None
            rm_col = None
            profile_col = None
            name_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if col_lower == 'email':
                    email_col = col
                elif 'lead owner' in col_lower or 'rm' in col_lower or 'owner' in col_lower:
                    rm_col = col
                elif 'industry' in col_lower or 'field of work' in col_lower or 'profile' in col_lower:
                    profile_col = col
                elif 'last name' in col_lower or 'name' in col_lower:
                    if name_col is None:  # Take first name column found
                        name_col = col
            
            if email_col is None:
                st.error("CRM file must have an 'Email' column")
                return False
            
            # Create standardized columns
            df['email'] = df[email_col].astype(str).str.strip().str.lower()
            df = df[df['email'].notna() & (df['email'] != '') & (df['email'] != 'nan')]
            
            if rm_col:
                df['rm_name'] = df[rm_col].fillna('Unassigned')
            else:
                df['rm_name'] = 'Unassigned'
            
            if profile_col:
                df['profile'] = df[profile_col].fillna('Unknown')
            else:
                df['profile'] = 'Unknown'
            
            if name_col:
                df['lead_name'] = df[name_col].fillna('')
            
            self.crm_data = df
            return True
            
        except Exception as e:
            st.error(f"Error loading CRM data: {e}")
            import traceback
            st.code(traceback.format_exc())
            return False
    
    def match_participants_with_crm(self):
        """Match Zoom participants with CRM leads"""
        if self.participants_data is None or self.crm_data is None:
            return False
        
        if 'email' not in self.participants_data.columns or 'email' not in self.crm_data.columns:
            st.warning("Cannot match: missing email column")
            return False
        
        # Merge on email
        merged = self.participants_data.merge(
            self.crm_data[['email', 'rm_name', 'profile']].drop_duplicates(subset='email'),
            on='email',
            how='left'
        )
        
        # Fill missing values
        merged['rm_name'] = merged['rm_name'].fillna('Unassigned')
        merged['profile'] = merged['profile'].fillna('Unknown')
        
        matched_count = merged['rm_name'].ne('Unassigned').sum()
        st.info(f"🔗 Matched {matched_count}/{len(merged)} participants with CRM")
        
        self.participants_data = merged
        return True
    
    def calculate_engagement_scores(self, total_duration_mins=60):
        """Calculate engagement score for each participant"""
        if self.participants_data is None or len(self.participants_data) == 0:
            return False
        
        scores = []
        
        for idx, row in self.participants_data.iterrows():
            email = row.get('email', '')
            name = row.get('name', '') or ''
            duration = row.get('duration_mins', 0)
            
            # Ensure duration is numeric
            try:
                duration = float(duration)
            except:
                duration = 0
            
            # Component 1: Attendance Duration (40%)
            attendance_score = min((duration / total_duration_mins) * 40, 40)
            
            # Component 2: Chat Participation (30%)
            chat_score = 0
            message_count = 0
            question_count = 0
            
            if self.chat_data is not None and len(self.chat_data) > 0 and name:
                # Match by name (case-insensitive partial match)
                name_parts = str(name).lower().split()
                if name_parts:
                    first_name = name_parts[0]
                    participant_msgs = self.chat_data[
                        self.chat_data['sender'].str.lower().str.contains(first_name, na=False, regex=False)
                    ]
                    message_count = len(participant_msgs)
                    chat_score = min(message_count * 5, 30)  # 5 points per message, max 30
                    
                    # Component 3: Questions Asked (20%)
                    if 'is_question' in participant_msgs.columns:
                        question_count = participant_msgs['is_question'].sum()
            
            question_score = min(question_count * 10, 20)  # 10 points per question, max 20
            
            # Component 4: Stayed Till End (10%)
            stayed_till_end = duration >= (total_duration_mins * 0.8)
            end_score = 10 if stayed_till_end else 0
            
            # Total Score
            total_score = attendance_score + chat_score + question_score + end_score
            
            # Categorization
            if total_score >= 70:
                category = 'Hot'
            elif total_score >= 40:
                category = 'Warm'
            else:
                category = 'Cold'
            
            scores.append({
                'email': email,
                'name': name,
                'duration_mins': round(duration, 1),
                'attendance_score': round(attendance_score, 1),
                'chat_score': round(chat_score, 1),
                'question_score': round(question_score, 1),
                'end_score': round(end_score, 1),
                'total_score': round(total_score, 1),
                'category': category,
                'rm_name': str(row.get('rm_name', 'Unassigned')),
                'profile': str(row.get('profile', 'Unknown')),
                'message_count': message_count,
                'question_count': question_count
            })
        
        self.engagement_scores = pd.DataFrame(scores)
        return True
    
    def analyze_exit_timeline(self, total_duration_mins=60, interval_mins=5):
        """Analyze when participants dropped off"""
        if self.participants_data is None or len(self.participants_data) == 0:
            return None
        
        timeline = []
        total_participants = len(self.participants_data)
        
        for minute in range(0, total_duration_mins + 1, interval_mins):
            still_present = len(self.participants_data[
                self.participants_data['duration_mins'] >= minute
            ])
            percentage = (still_present / total_participants) * 100 if total_participants > 0 else 0
            
            timeline.append({
                'minute': minute,
                'attendees': still_present,
                'percentage': round(percentage, 1)
            })
        
        timeline_df = pd.DataFrame(timeline)
        
        # Find biggest drop-off points
        timeline_df['drop'] = timeline_df['attendees'].diff().fillna(0).abs()
        critical_moments = timeline_df.nlargest(5, 'drop')[['minute', 'drop', 'percentage']]
        
        self.insights['exit_timeline'] = timeline_df
        self.insights['critical_dropoff_moments'] = critical_moments
        
        # Exit stats
        left_0_5 = len(self.participants_data[self.participants_data['duration_mins'] <= 5])
        left_0_10 = len(self.participants_data[self.participants_data['duration_mins'] <= 10])
        stayed_60_plus = len(self.participants_data[self.participants_data['duration_mins'] >= 60])
        
        self.insights['exit_stats'] = {
            'total_participants': total_participants,
            'left_0_5': left_0_5,
            'left_0_5_pct': round((left_0_5 / total_participants) * 100, 1) if total_participants > 0 else 0,
            'left_0_10': left_0_10,
            'left_0_10_pct': round((left_0_10 / total_participants) * 100, 1) if total_participants > 0 else 0,
            'stayed_60_plus': stayed_60_plus,
            'stayed_60_plus_pct': round((stayed_60_plus / total_participants) * 100, 1) if total_participants > 0 else 0,
        }
        
        return timeline_df
    
    def get_inactive_leads_by_rm(self, min_score=40):
        """Get inactive/cold leads grouped by RM"""
        if self.engagement_scores is None or len(self.engagement_scores) == 0:
            return []
        
        inactive = self.engagement_scores[self.engagement_scores['total_score'] < min_score].copy()
        
        rm_follow_ups = []
        for rm in inactive['rm_name'].unique():
            rm_leads = inactive[inactive['rm_name'] == rm]
            rm_follow_ups.append({
                'rm_name': rm,
                'inactive_count': len(rm_leads),
                'leads_df': rm_leads
            })
        
        # Sort by inactive count descending
        rm_follow_ups.sort(key=lambda x: x['inactive_count'], reverse=True)
        
        self.insights['rm_follow_ups'] = rm_follow_ups
        return rm_follow_ups
    
    def analyze_by_profile(self):
        """Analyze engagement patterns by profile/industry"""
        if self.engagement_scores is None or len(self.engagement_scores) == 0:
            return None
        
        if 'profile' not in self.engagement_scores.columns:
            return None
        
        # Filter out Unknown profiles for better analysis
        valid_profiles = self.engagement_scores[self.engagement_scores['profile'] != 'Unknown']
        
        if len(valid_profiles) == 0:
            return None
        
        profile_analysis = []
        for profile in valid_profiles['profile'].unique():
            group = valid_profiles[valid_profiles['profile'] == profile]
            
            if len(group) == 0:
                continue
            
            analysis = {
                'profile': profile,
                'total_count': len(group),
                'avg_score': round(group['total_score'].mean(), 1),
                'avg_duration': round(group['duration_mins'].mean(), 1),
                'hot_count': len(group[group['category'] == 'Hot']),
                'warm_count': len(group[group['category'] == 'Warm']),
                'cold_count': len(group[group['category'] == 'Cold']),
                'hot_percentage': round(len(group[group['category'] == 'Hot']) / len(group) * 100, 1),
            }
            
            if analysis['avg_score'] >= 60:
                analysis['engagement_level'] = 'High'
            elif analysis['avg_score'] >= 40:
                analysis['engagement_level'] = 'Medium'
            else:
                analysis['engagement_level'] = 'Low'
            
            profile_analysis.append(analysis)
        
        # Sort by average score
        profile_analysis.sort(key=lambda x: x['avg_score'], reverse=True)
        
        self.insights['profile_analysis'] = profile_analysis
        return profile_analysis
    
    def get_profile_insights(self):
        """Generate actionable insights from profile analysis"""
        if 'profile_analysis' not in self.insights or not self.insights['profile_analysis']:
            return None
        
        profile_data = self.insights['profile_analysis']
        
        insights = {
            'best_profile': profile_data[0] if profile_data else None,
            'worst_profile': profile_data[-1] if profile_data else None,
            'high_engagement': [p for p in profile_data if p['avg_score'] >= 60],
            'low_engagement': [p for p in profile_data if p['avg_score'] < 40],
            'recommendations': []
        }
        
        for profile in profile_data:
            if profile['avg_score'] >= 60:
                insights['recommendations'].append({
                    'profile': profile['profile'],
                    'type': 'success',
                    'message': f"✅ {profile['profile']} shows strong engagement ({profile['avg_score']}/100). Great target segment!"
                })
            elif profile['avg_score'] < 40:
                if profile['avg_duration'] < 30:
                    insights['recommendations'].append({
                        'profile': profile['profile'],
                        'type': 'warning',
                        'message': f"⚠️ {profile['profile']} drops off early (avg {profile['avg_duration']} min). Add relevant content earlier."
                    })
                else:
                    insights['recommendations'].append({
                        'profile': profile['profile'],
                        'type': 'warning',
                        'message': f"⚠️ {profile['profile']} stays but doesn't engage. Use direct polls and questions."
                    })
        
        self.insights['profile_insights'] = insights
        return insights
    
    def generate_summary_stats(self):
        """Generate overall summary statistics"""
        if self.participants_data is None:
            return None
        
        total_participants = len(self.participants_data)
        avg_duration = self.participants_data['duration_mins'].mean() if 'duration_mins' in self.participants_data.columns else 0
        
        summary = {
            'total_participants': total_participants,
            'avg_duration_mins': round(avg_duration, 1),
            'hot_leads': 0,
            'warm_leads': 0,
            'cold_leads': 0,
            'avg_score': 0,
            'total_chat_messages': len(self.chat_data) if self.chat_data is not None else 0,
            'total_questions': 0
        }
        
        if self.engagement_scores is not None and len(self.engagement_scores) > 0:
            summary['hot_leads'] = len(self.engagement_scores[self.engagement_scores['category'] == 'Hot'])
            summary['warm_leads'] = len(self.engagement_scores[self.engagement_scores['category'] == 'Warm'])
            summary['cold_leads'] = len(self.engagement_scores[self.engagement_scores['category'] == 'Cold'])
            summary['avg_score'] = round(self.engagement_scores['total_score'].mean(), 1)
        
        if self.chat_data is not None and 'is_question' in self.chat_data.columns:
            summary['total_questions'] = int(self.chat_data['is_question'].sum())
        
        self.insights['summary'] = summary
        return summary


# ============================================================================
# EMAIL TEMPLATE GENERATOR
# ============================================================================
def generate_email_template(lead_row):
    """Generate personalized email template"""
    name = lead_row.get('name', 'there') or 'there'
    category = lead_row.get('category', 'Cold')
    duration = lead_row.get('duration_mins', 0)
    
    if category == 'Hot':
        subject = f"🔥 {name}, Your Leadership Journey Awaits!"
        body = f"""Hi {name},

Thank you for your incredible engagement during our masterclass! Your active participation shows you're ready to take your leadership to the next level.

You spent {duration:.0f} minutes with us and showed great interest. This tells me you're serious about growth.

I'd love to discuss how our Leadership Essentials Program can accelerate your journey. Are you available for a quick 15-minute call this week?

Looking forward to connecting!

Warm regards,
Iron Lady Team"""

    elif category == 'Warm':
        subject = f"{name}, Let's Continue Your Leadership Journey"
        body = f"""Hi {name},

Thank you for joining our masterclass! I noticed you were with us for {duration:.0f} minutes.

I understand you might have questions about how our programs can help you achieve your leadership goals.

Would you be open to a brief conversation to explore how we can support your growth?

Best regards,
Iron Lady Team"""

    else:
        subject = f"{name}, We Missed You at the Masterclass!"
        body = f"""Hi {name},

I noticed you joined our masterclass briefly. I understand life gets busy!

I'd love to share the key takeaways you might have missed and answer any questions.

Would you like me to send you the recording, or would a quick call work better?

Best regards,
Iron Lady Team"""
    
    return {'subject': subject, 'body': body}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def create_download_button(df, filename, label):
    """Create download button for dataframe"""
    csv = df.to_csv(index=False)
    return st.download_button(
        label=f"📥 {label}",
        data=csv,
        file_name=filename,
        mime='text/csv'
    )


# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    st.markdown('<h1 class="main-header">🎯 Masterclass Analytics Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Complete engagement analysis • Lead scoring • Profile insights • RM follow-ups</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Upload Files")
        
        participants_file = st.file_uploader(
            "zoom_participants.csv",
            type=['csv'],
            help="Zoom participant report export"
        )
        
        chat_file = st.file_uploader(
            "zoom_chat.txt",
            type=['txt'],
            help="Zoom chat log export"
        )
        
        leads_file = st.file_uploader(
            "crm_leads.csv",
            type=['csv'],
            help="CRM export with Lead Owner and Industry"
        )
        
        st.divider()
        
        masterclass_duration = st.number_input(
            "Masterclass Duration (minutes)",
            min_value=30,
            max_value=180,
            value=60,
            step=5
        )
        
        analyze_btn = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    # Main Content
    if participants_file and chat_file and leads_file and analyze_btn:
        with st.spinner("🔄 Processing masterclass data..."):
            # Initialize analyzer
            analyzer = MasterclassAnalyzer()
            
            # Load data from uploaded files
            success = True
            
            # Load participants
            if not analyzer.load_zoom_participants(participants_file.getvalue()):
                success = False
            
            # Load chat
            if success and not analyzer.load_zoom_chat(chat_file.getvalue()):
                success = False
            
            # Load CRM
            if success and not analyzer.load_crm_data(leads_file.getvalue()):
                success = False
            
            if not success:
                st.error("Failed to load one or more files. Please check formats above.")
                return
            
            # Match and analyze
            analyzer.match_participants_with_crm()
            analyzer.calculate_engagement_scores(total_duration_mins=masterclass_duration)
            analyzer.analyze_exit_timeline(total_duration_mins=masterclass_duration)
            analyzer.get_inactive_leads_by_rm(min_score=40)
            analyzer.analyze_by_profile()
            analyzer.get_profile_insights()
            summary = analyzer.generate_summary_stats()
        
        if summary is None:
            st.error("Failed to process data.")
            return
        
        st.success(f"✅ Successfully analyzed {summary['total_participants']} participants!")
        
        # ================================================================
        # SECTION 1: Overview Statistics
        # ================================================================
        st.header("📊 Overview Statistics")
        
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
        
        # Lead Distribution & Engagement Overview
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Lead Distribution")
            if analyzer.engagement_scores is not None and len(analyzer.engagement_scores) > 0:
                category_counts = analyzer.engagement_scores['category'].value_counts()
                fig = px.pie(
                    values=category_counts.values,
                    names=category_counts.index,
                    color=category_counts.index,
                    color_discrete_map={'Hot': '#10b981', 'Warm': '#f59e0b', 'Cold': '#ef4444'},
                    hole=0.4
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(showlegend=True, height=350)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🎤 Engagement Overview")
            engagement_metrics = pd.DataFrame({
                'Metric': ['Total Messages', 'Questions Asked', 'Avg Score'],
                'Value': [
                    summary['total_chat_messages'],
                    summary['total_questions'],
                    summary['avg_score']
                ]
            })
            st.dataframe(engagement_metrics, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # ================================================================
        # SECTION 2: Attendance Drop-off Curve
        # ================================================================
        st.header("📉 Attendance Drop-off Curve")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if 'exit_timeline' in analyzer.insights:
                timeline_df = analyzer.insights['exit_timeline']
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=timeline_df['minute'],
                    y=timeline_df['percentage'],
                    mode='lines+markers',
                    name='Attendance %',
                    line=dict(color='#3b82f6', width=3),
                    marker=dict(size=8)
                ))
                fig.update_layout(
                    title='Attendance Over Time',
                    xaxis_title='Time (minutes)',
                    yaxis_title='Attendance (%)',
                    yaxis=dict(range=[0, 105]),
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("⚠️ Critical Drop-off Moments")
            if 'critical_dropoff_moments' in analyzer.insights:
                st.dataframe(
                    analyzer.insights['critical_dropoff_moments'],
                    use_container_width=True,
                    hide_index=True
                )
            
            if 'exit_stats' in analyzer.insights:
                stats = analyzer.insights['exit_stats']
                st.markdown("**Quick Stats:**")
                st.write(f"• Left in 0-5 min: {stats['left_0_5']} ({stats['left_0_5_pct']}%)")
                st.write(f"• Stayed 60+ min: {stats['stayed_60_plus']} ({stats['stayed_60_plus_pct']}%)")
        
        st.divider()
        
        # ================================================================
        # SECTION 3: Profile Analysis
        # ================================================================
        st.header("👥 Participant Profile Analysis")
        
        if 'profile_analysis' in analyzer.insights and analyzer.insights['profile_analysis']:
            profile_df = pd.DataFrame(analyzer.insights['profile_analysis'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Average Engagement by Profile")
                fig = px.bar(
                    profile_df.head(15),
                    x='avg_score',
                    y='profile',
                    orientation='h',
                    color='avg_score',
                    color_continuous_scale=['#ef4444', '#f59e0b', '#10b981'],
                    labels={'avg_score': 'Avg Score', 'profile': 'Profile'}
                )
                fig.update_layout(height=450, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Hot Leads by Profile")
                fig = px.bar(
                    profile_df.head(15),
                    x='hot_count',
                    y='profile',
                    orientation='h',
                    color='hot_percentage',
                    color_continuous_scale=['#fecaca', '#10b981'],
                    labels={'hot_count': 'Hot Leads', 'profile': 'Profile'}
                )
                fig.update_layout(height=450, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Profile Insights
            st.subheader("📋 Profile Insights & Recommendations")
            
            if 'profile_insights' in analyzer.insights:
                insights = analyzer.insights['profile_insights']
                
                if insights.get('best_profile'):
                    best = insights['best_profile']
                    st.success(f"🏆 **Top Performing:** {best['profile']} (Avg Score: {best['avg_score']}, Hot Rate: {best['hot_percentage']}%)")
                
                if insights.get('high_engagement'):
                    profiles = [p['profile'] for p in insights['high_engagement']]
                    st.info(f"✅ **High Engagement (60+):** {', '.join(profiles)}")
                
                if insights.get('low_engagement'):
                    profiles = [p['profile'] for p in insights['low_engagement']]
                    st.warning(f"⚠️ **Low Engagement (<40):** {', '.join(profiles)}")
                
                if insights.get('recommendations'):
                    with st.expander("💡 Detailed Recommendations"):
                        for rec in insights['recommendations']:
                            st.write(rec['message'])
            
            create_download_button(profile_df, 'profile_analysis.csv', 'Download Profile Analysis')
        else:
            st.info("ℹ️ No profile data available. Add 'Industry/Field of Work' column to CRM for profile analysis.")
        
        st.divider()
        
        # ================================================================
        # SECTION 4: Detailed Engagement Scores
        # ================================================================
        st.header("📝 Detailed Engagement Scores")
        
        if analyzer.engagement_scores is not None and len(analyzer.engagement_scores) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                category_filter = st.multiselect(
                    "Filter by Category",
                    options=['Hot', 'Warm', 'Cold'],
                    default=['Hot', 'Warm', 'Cold']
                )
            
            with col2:
                rm_options = sorted(analyzer.engagement_scores['rm_name'].unique().tolist())
                rm_filter = st.multiselect(
                    "Filter by RM",
                    options=rm_options,
                    default=rm_options
                )
            
            filtered_df = analyzer.engagement_scores[
                (analyzer.engagement_scores['category'].isin(category_filter)) &
                (analyzer.engagement_scores['rm_name'].isin(rm_filter))
            ]
            
            display_cols = ['email', 'name', 'duration_mins', 'attendance_score', 'chat_score', 
                          'question_score', 'end_score', 'total_score', 'category', 'rm_name']
            
            st.dataframe(
                filtered_df[display_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'total_score': st.column_config.ProgressColumn(
                        'Total Score',
                        min_value=0,
                        max_value=100,
                        format='%.1f'
                    ),
                    'duration_mins': st.column_config.NumberColumn('Duration', format='%.1f')
                }
            )
            
            create_download_button(filtered_df, 'engagement_scores.csv', 'Download Filtered Results')
        
        st.divider()
        
        # ================================================================
        # SECTION 5: RM-wise Inactive Lead Follow-ups
        # ================================================================
        st.header("👤 RM-wise Inactive Lead Follow-ups")
        
        if 'rm_follow_ups' in analyzer.insights and analyzer.insights['rm_follow_ups']:
            for rm_data in analyzer.insights['rm_follow_ups']:
                rm_name = rm_data['rm_name']
                leads_df = rm_data['leads_df']
                
                with st.expander(f"⚠️ {rm_name} - {rm_data['inactive_count']} inactive leads"):
                    display_cols = ['email', 'name', 'duration_mins', 'total_score', 'category']
                    st.dataframe(leads_df[display_cols], use_container_width=True, hide_index=True)
                    
                    safe_name = rm_name.replace('@', '_').replace(' ', '_').replace('.', '_')
                    create_download_button(leads_df, f'followup_{safe_name}.csv', f'Download {rm_name} Follow-ups')
        else:
            st.success("🎉 No inactive leads requiring follow-up!")
        
        st.divider()
        
        # ================================================================
        # SECTION 6: Email Templates
        # ================================================================
        st.header("📧 Email Templates")
        
        if analyzer.engagement_scores is not None and len(analyzer.engagement_scores) > 0:
            selected_email = st.selectbox(
                "Select a participant to generate email",
                options=analyzer.engagement_scores['email'].tolist()
            )
            
            if selected_email:
                lead_row = analyzer.engagement_scores[
                    analyzer.engagement_scores['email'] == selected_email
                ].iloc[0].to_dict()
                template = generate_email_template(lead_row)
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown(f"**Name:** {lead_row.get('name', 'N/A')}")
                    st.markdown(f"**Category:** {lead_row.get('category', 'N/A')}")
                    st.markdown(f"**Score:** {lead_row.get('total_score', 0)}")
                    st.markdown(f"**Duration:** {lead_row.get('duration_mins', 0)} min")
                    st.markdown(f"**RM:** {lead_row.get('rm_name', 'N/A')}")
                
                with col2:
                    st.text_input("Subject", value=template['subject'])
                    st.text_area("Email Body", value=template['body'], height=300)
        
        st.divider()
        
        # ================================================================
        # SECTION 7: Export All Data
        # ================================================================
        st.header("💾 Export All Data")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if analyzer.engagement_scores is not None and len(analyzer.engagement_scores) > 0:
                create_download_button(analyzer.engagement_scores, 'all_engagement_scores.csv', 'All Scores')
        
        with col2:
            if 'exit_timeline' in analyzer.insights:
                create_download_button(analyzer.insights['exit_timeline'], 'exit_timeline.csv', 'Exit Timeline')
        
        with col3:
            if 'profile_analysis' in analyzer.insights and analyzer.insights['profile_analysis']:
                create_download_button(
                    pd.DataFrame(analyzer.insights['profile_analysis']),
                    'profile_analysis.csv',
                    'Profile Analysis'
                )
        
        with col4:
            st.download_button(
                label="📥 Summary (JSON)",
                data=json.dumps(summary, indent=2),
                file_name='summary_statistics.json',
                mime='application/json'
            )
    
    else:
        st.info("👆 Upload all three files in the sidebar and click **Analyze**")
        
        with st.expander("ℹ️ File Format Guide"):
            st.markdown("""
            ### Required Files
            
            **1. zoom_participants.csv** (Zoom Export)
            ```
            Name (original name), Email, Duration (minutes), ...
            ```
            - Export from Zoom meeting reports
            - Automatically deduplicates re-joins
            
            **2. zoom_chat.txt** (Zoom Chat Export)
            ```
            2025-11-21 18:57:45 From Name to Everyone:
                Message text here
            ```
            
            **3. crm_leads.csv** (CRM Export)
            ```
            Email, Last Name, Lead Owner, Industry/Field of Work
            ```
            - **Required:** Email column
            - **Optional:** Lead Owner (for RM grouping), Industry (for profile analysis)
            """)


if __name__ == "__main__":
    main()
