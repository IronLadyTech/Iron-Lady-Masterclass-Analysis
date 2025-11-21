import pandas as pd
import re
from datetime import datetime, timedelta
import json

class MasterclassAnalyzer:
    def __init__(self):
        self.participants_data = None
        self.chat_data = None
        self.crm_data = None
        self.engagement_scores = []
        self.insights = {}
        
    def load_zoom_participants(self, file_path):
        """
        Load Zoom participant report CSV with automatic deduplication
        
        Zoom creates multiple rows when people leave and rejoin.
        This method automatically:
        1. Detects duplicates by email
        2. Groups by email
        3. Sums total duration for each unique person
        """
        try:
            # Zoom participant report typically has: Name, Email, Join Time, Leave Time, Duration (Minutes)
            df = pd.read_csv(file_path)
            
            original_count = len(df)
            print(f"  Raw Zoom data: {original_count} rows")
            
            # Standardize column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Find email column before deduplication
            email_col = 'email' if 'email' in df.columns else None
            
            if not email_col:
                print("  ⚠️ Warning: No email column found - cannot deduplicate")
            else:
                # Check for duplicates
                unique_emails = df[email_col].nunique()
                if unique_emails < original_count:
                    duplicate_count = original_count - unique_emails
                    print(f"  ⚠️  Found {duplicate_count} duplicate entries (people who left/rejoined)")
                    print(f"  📧 Deduplicating to {unique_emails} unique participants...")
                    
                    # Find duration column
                    duration_col = None
                    for col in df.columns:
                        if 'duration' in col and 'minute' in col:
                            duration_col = col
                            break
                    
                    if duration_col:
                        # Clean and convert duration to numeric first
                        df['duration_numeric'] = pd.to_numeric(
                            df[duration_col].astype(str).str.extract(r'(\d+)')[0],
                            errors='coerce'
                        ).fillna(0)
                        
                        # Group by email and sum durations, keep first for other fields
                        agg_dict = {'duration_numeric': 'sum'}
                        for col in df.columns:
                            if col not in [email_col, duration_col, 'duration_numeric']:
                                agg_dict[col] = 'first'
                        
                        df = df.groupby(email_col, as_index=False).agg(agg_dict)
                        
                        # Replace duration column with summed values
                        df[duration_col] = df['duration_numeric']
                        df = df.drop('duration_numeric', axis=1)
                        
                        print(f"  ✓ Deduplicated to {len(df)} unique participants")
                    else:
                        print("  ⚠️ Warning: Could not find duration column to sum")
            
            # Convert duration to numeric (handle formats like "45 min" or just "45")
            if 'duration_(minutes)' in df.columns:
                df['duration_mins'] = pd.to_numeric(
                    df['duration_(minutes)'].astype(str).str.extract(r'(\d+)')[0],
                    errors='coerce'
                ).fillna(0)
            elif 'duration' in df.columns:
                df['duration_mins'] = pd.to_numeric(
                    df['duration'].astype(str).str.extract(r'(\d+)')[0],
                    errors='coerce'
                ).fillna(0)
            
            # Standardize email column
            if 'email' in df.columns:
                df['email'] = df['email'].str.strip().str.lower()
            
            self.participants_data = df
            print(f"✓ Loaded {len(df)} unique participant(s)")
            return True
        except Exception as e:
            print(f"✗ Error loading participants: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_zoom_chat(self, file_path):
        """Load Zoom chat log (TXT or CSV)"""
        try:
            # Zoom chat format: Timestamp | Name | Message
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            chat_records = []
            for line in lines:
                # Parse chat line (format: "10:30:45 From John Doe to Everyone: Hello")
                match = re.match(r'(\d{2}:\d{2}:\d{2})\s+From\s+(.+?)\s+(?:to|To)\s+(.+?):\s*(.+)', line)
                if match:
                    timestamp, sender, recipient, message = match.groups()
                    chat_records.append({
                        'timestamp': timestamp,
                        'sender': sender.strip(),
                        'recipient': recipient.strip(),
                        'message': message.strip(),
                        'is_question': '?' in message
                    })
            
            self.chat_data = pd.DataFrame(chat_records)
            print(f"✓ Loaded {len(chat_records)} chat messages")
            return True
        except Exception as e:
            print(f"✗ Error loading chat: {e}")
            return False
    
    def load_crm_data(self, file_path):
        """
        Load CRM data with actual Zoho field names
        
        Expected Zoho CRM Export columns:
        - Record Id
        - First Name, Last Name
        - Email (this is the Lead's email address - used to match with Zoom)
        - Lead Owner (RM name)
        - Lead Status
        - Lead Source
        - Industry/Field of Work (optional)
        """
        try:
            df = pd.read_csv(file_path)
            
            # Print original columns for debugging
            original_cols = df.columns.tolist()
            print(f"  CRM original columns: {original_cols}")
            
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()
            
            # Build column mapping (before normalization)
            column_mapping = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower == 'email':  # This is the Lead's email
                    column_mapping['email_col'] = col
                elif 'lead owner' in col_lower:
                    column_mapping['lead_owner'] = col
                elif col_lower in ['first name', 'firstname']:
                    column_mapping['first_name'] = col
                elif col_lower in ['last name', 'lastname']:
                    column_mapping['last_name'] = col
                elif 'lead status' in col_lower:
                    column_mapping['lead_status'] = col
                elif 'lead source' in col_lower:
                    column_mapping['lead_source'] = col
                elif 'industry' in col_lower or 'field of work' in col_lower:
                    column_mapping['industry'] = col
                elif col_lower in ['record id', 'recordid']:
                    column_mapping['record_id'] = col
            
            # Create standardized columns for matching
            if 'email_col' in column_mapping:
                # Store normalized email in 'email' column (lowercase for matching)
                df['email'] = df[column_mapping['email_col']].str.strip().str.lower()
                print(f"  Created 'email' column from '{column_mapping['email_col']}'")
            
            if 'lead_owner' in column_mapping:
                df['rm_name'] = df[column_mapping['lead_owner']]
            
            if 'lead_status' in column_mapping:
                df['status'] = df[column_mapping['lead_status']]
            
            if 'industry' in column_mapping:
                df['profile'] = df[column_mapping['industry']]
            
            # Don't normalize column names - keep them as-is
            # This prevents conflicts with the 'email' column we just created
            
            self.crm_data = df
            print(f"✓ Loaded {len(df)} CRM records")
            print(f"  Final columns: {df.columns.tolist()[:10]}...")  # Show first 10
            return True
        except Exception as e:
            print(f"✗ Error loading CRM data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def match_participants_with_crm(self):
        """Match Zoom participants with CRM leads"""
        if self.participants_data is None or self.crm_data is None:
            print("✗ Missing participant or CRM data")
            return False
        
        print(f"  Participant columns: {self.participants_data.columns.tolist()}")
        print(f"  CRM columns: {self.crm_data.columns.tolist()}")
        
        # Find email column in participants data
        participant_email_col = None
        for col in self.participants_data.columns:
            if col.lower() in ['email', 'user_email', 'email_address']:
                participant_email_col = col
                break
        
        if not participant_email_col:
            print("✗ Could not find email column in participants data")
            return False
        
        # Find email column in CRM data
        crm_email_col = None
        for col in self.crm_data.columns:
            if col.lower() in ['email', 'lead_email', 'email_address']:
                crm_email_col = col
                break
        
        if not crm_email_col:
            print("✗ Could not find email column in CRM data")
            return False
        
        print(f"  Merging on: participants[{participant_email_col}] = crm[{crm_email_col}]")
        
        # Normalize emails before merge
        self.participants_data['email_normalized'] = self.participants_data[participant_email_col].str.strip().str.lower()
        self.crm_data['email_normalized'] = self.crm_data[crm_email_col].str.strip().str.lower()
        
        # Merge on normalized email
        merged = self.participants_data.merge(
            self.crm_data,
            left_on='email_normalized',
            right_on='email_normalized',
            how='left',
            suffixes=('', '_crm')
        )
        
        # Keep the original email column from participants
        if 'email' not in merged.columns and participant_email_col != 'email':
            merged['email'] = merged[participant_email_col]
        
        self.participants_data = merged
        matched_count = merged[crm_email_col].notna().sum()
        print(f"✓ Matched {matched_count}/{len(merged)} participants with CRM")
        return True
    
    def calculate_engagement_scores(self, total_duration_mins=60):
        """Calculate engagement score for each participant"""
        if self.participants_data is None:
            return False
        
        scores = []
        
        for idx, row in self.participants_data.iterrows():
            email = row.get('email') or row.get('user_email', '')
            name = row.get('name') or row.get('user_name', '')
            duration = row.get('duration_mins', 0)
            
            # Component 1: Attendance Duration (40%)
            attendance_score = min((duration / total_duration_mins) * 40, 40)
            
            # Component 2: Chat Participation (30%)
            chat_score = 0
            participant_messages = pd.DataFrame()  # Initialize empty
            
            if self.chat_data is not None and len(self.chat_data) > 0 and 'sender' in self.chat_data.columns:
                participant_messages = self.chat_data[
                    self.chat_data['sender'].str.contains(name, case=False, na=False)
                ]
                message_count = len(participant_messages)
                chat_score = min(message_count * 5, 30)  # 5 points per message, max 30
            
            # Component 3: Questions Asked (20%)
            question_score = 0
            if len(participant_messages) > 0 and 'is_question' in participant_messages.columns:
                questions = participant_messages[participant_messages['is_question'] == True]
                question_count = len(questions)
                question_score = min(question_count * 10, 20)  # 10 points per question, max 20
            
            # Component 4: Stayed Till End (10%)
            stayed_till_end = duration >= (total_duration_mins * 0.8)  # 80% threshold
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
                'duration_mins': duration,
                'attendance_score': round(attendance_score, 1),
                'chat_score': round(chat_score, 1),
                'question_score': round(question_score, 1),
                'end_score': end_score,
                'total_score': round(total_score, 1),
                'category': category,
                'rm_name': row.get('rm_name', 'Unassigned'),
                'rm_email': row.get('rm_email', ''),
            })
        
        self.engagement_scores = pd.DataFrame(scores)
        print(f"✓ Calculated engagement scores for {len(scores)} participants")
        return True
    
    def analyze_exit_timeline(self, total_duration_mins=60, interval_mins=5):
        """Analyze when participants dropped off with comprehensive statistics"""
        if self.participants_data is None:
            return None
        
        timeline = []
        
        for minute in range(0, total_duration_mins + 1, interval_mins):
            still_present = len(self.participants_data[
                self.participants_data['duration_mins'] >= minute
            ])
            percentage = (still_present / len(self.participants_data)) * 100
            
            timeline.append({
                'minute': minute,
                'attendees': still_present,
                'percentage': round(percentage, 1)
            })
        
        timeline_df = pd.DataFrame(timeline)
        
        # Find biggest drop-off points
        timeline_df['drop'] = timeline_df['percentage'].diff().fillna(0).abs()
        critical_moments = timeline_df.nlargest(3, 'drop')[['minute', 'drop', 'percentage']]
        
        self.insights['exit_timeline'] = timeline_df
        self.insights['critical_dropoff_moments'] = critical_moments
        
        # Calculate comprehensive statistics
        total_participants = len(self.participants_data)
        
        # Check for waiting room column
        has_waiting_room = 'in_waiting_room' in self.participants_data.columns
        if has_waiting_room:
            waiting_room_count = len(self.participants_data[
                self.participants_data['in_waiting_room'].astype(str).str.lower() == 'yes'
            ])
            actual_attendees = total_participants - waiting_room_count
        else:
            waiting_room_count = 0
            actual_attendees = total_participants
        
        # Duration buckets - Overall
        left_0_5 = len(self.participants_data[self.participants_data['duration_mins'] <= 5])
        left_0_10 = len(self.participants_data[self.participants_data['duration_mins'] <= 10])
        stayed_60_plus = len(self.participants_data[self.participants_data['duration_mins'] >= 60])
        stayed_100_plus = len(self.participants_data[self.participants_data['duration_mins'] >= 100])
        
        # Calculate for actual attendees (excluding waiting room)
        if has_waiting_room and actual_attendees > 0:
            admitted = self.participants_data[
                self.participants_data['in_waiting_room'].astype(str).str.lower() != 'yes'
            ]
            left_0_5_admitted = len(admitted[admitted['duration_mins'] <= 5])
            left_0_10_admitted = len(admitted[admitted['duration_mins'] <= 10])
            stayed_60_plus_admitted = len(admitted[admitted['duration_mins'] >= 60])
            stayed_100_plus_admitted = len(admitted[admitted['duration_mins'] >= 100])
            avg_duration_admitted = admitted['duration_mins'].mean()
        else:
            left_0_5_admitted = left_0_5
            left_0_10_admitted = left_0_10
            stayed_60_plus_admitted = stayed_60_plus
            stayed_100_plus_admitted = stayed_100_plus
            avg_duration_admitted = self.participants_data['duration_mins'].mean()
        
        exit_stats = {
            'total_participants': total_participants,
            'waiting_room_count': waiting_room_count,
            'actual_attendees': actual_attendees,
            'has_waiting_room_data': has_waiting_room,
            
            # Overall stats (including waiting room)
            'left_0_5': left_0_5,
            'left_0_5_pct': round((left_0_5 / total_participants) * 100, 1) if total_participants > 0 else 0,
            'left_0_10': left_0_10,
            'left_0_10_pct': round((left_0_10 / total_participants) * 100, 1) if total_participants > 0 else 0,
            'stayed_60_plus': stayed_60_plus,
            'stayed_60_plus_pct': round((stayed_60_plus / total_participants) * 100, 1) if total_participants > 0 else 0,
            'stayed_100_plus': stayed_100_plus,
            'stayed_100_plus_pct': round((stayed_100_plus / total_participants) * 100, 1) if total_participants > 0 else 0,
            
            # Admitted attendees stats (excluding waiting room)
            'left_0_5_admitted': left_0_5_admitted,
            'left_0_5_admitted_pct': round((left_0_5_admitted / actual_attendees) * 100, 1) if actual_attendees > 0 else 0,
            'left_0_10_admitted': left_0_10_admitted,
            'left_0_10_admitted_pct': round((left_0_10_admitted / actual_attendees) * 100, 1) if actual_attendees > 0 else 0,
            'stayed_60_plus_admitted': stayed_60_plus_admitted,
            'stayed_60_plus_admitted_pct': round((stayed_60_plus_admitted / actual_attendees) * 100, 1) if actual_attendees > 0 else 0,
            'stayed_100_plus_admitted': stayed_100_plus_admitted,
            'stayed_100_plus_admitted_pct': round((stayed_100_plus_admitted / actual_attendees) * 100, 1) if actual_attendees > 0 else 0,
            'avg_duration_admitted': round(avg_duration_admitted, 1)
        }
        
        self.insights['exit_stats'] = exit_stats
        
        print(f"✓ Analyzed exit timeline with {len(timeline)} data points")
        return timeline_df
    
    def get_inactive_leads_by_rm(self, min_score=40):
        """Get inactive/cold leads grouped by RM"""
        if self.engagement_scores is None or len(self.engagement_scores) == 0:
            return None
        
        inactive = self.engagement_scores[self.engagement_scores['total_score'] < min_score].copy()
        
        # Group by RM
        rm_groups = inactive.groupby('rm_name')
        
        rm_follow_ups = []
        for rm, group in rm_groups:
            rm_follow_ups.append({
                'rm_name': rm,
                'inactive_count': len(group),
                'leads': group.to_dict('records')
            })
        
        self.insights['rm_follow_ups'] = rm_follow_ups
        print(f"✓ Identified {len(inactive)} inactive leads across {len(rm_follow_ups)} RMs")
        return rm_follow_ups
    
    def analyze_by_profile(self):
        """Analyze engagement patterns by participant profile/industry"""
        if self.engagement_scores is None or len(self.engagement_scores) == 0:
            return None
        
        # Check if profile/industry column exists
        profile_col = None
        for col in ['profile', 'industry', 'profession', 'segment', 'category_name']:
            if col in self.engagement_scores.columns:
                profile_col = col
                break
        
        if profile_col is None:
            print("ℹ️  No profile/industry column found in data")
            return None
        
        # Group by profile
        profile_groups = self.engagement_scores.groupby(profile_col)
        
        profile_analysis = []
        for profile, group in profile_groups:
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
                'avg_attendance_score': round(group['attendance_score'].mean(), 1),
                'avg_chat_score': round(group['chat_score'].mean(), 1),
                'avg_question_score': round(group['question_score'].mean(), 1),
            }
            
            # Determine engagement level for profile
            if analysis['avg_score'] >= 70:
                analysis['profile_engagement_level'] = 'High'
            elif analysis['avg_score'] >= 40:
                analysis['profile_engagement_level'] = 'Medium'
            else:
                analysis['profile_engagement_level'] = 'Low'
            
            profile_analysis.append(analysis)
        
        # Sort by average score (highest first)
        profile_analysis = sorted(profile_analysis, key=lambda x: x['avg_score'], reverse=True)
        
        self.insights['profile_analysis'] = profile_analysis
        print(f"✓ Analyzed engagement across {len(profile_analysis)} profiles")
        
        return profile_analysis
    
    def get_profile_insights(self):
        """Generate actionable insights based on profile analysis"""
        if 'profile_analysis' not in self.insights:
            return None
        
        profile_data = self.insights['profile_analysis']
        
        if not profile_data or len(profile_data) == 0:
            return None
        
        insights = {
            'best_performing_profile': None,
            'worst_performing_profile': None,
            'most_engaged_profiles': [],
            'least_engaged_profiles': [],
            'recommendations': []
        }
        
        # Best and worst performing
        insights['best_performing_profile'] = profile_data[0]
        insights['worst_performing_profile'] = profile_data[-1]
        
        # High engagement profiles (avg score >= 60)
        insights['most_engaged_profiles'] = [p for p in profile_data if p['avg_score'] >= 60]
        
        # Low engagement profiles (avg score < 40)
        insights['least_engaged_profiles'] = [p for p in profile_data if p['avg_score'] < 40]
        
        # Generate recommendations
        for profile in profile_data:
            if profile['avg_score'] >= 70:
                insights['recommendations'].append({
                    'profile': profile['profile'],
                    'type': 'success',
                    'message': f"Great fit! {profile['profile']} shows strong engagement ({profile['avg_score']}/100). Consider creating more content for this segment."
                })
            elif profile['avg_score'] < 40:
                # Analyze what's causing low engagement
                if profile['avg_duration'] < 30:
                    insights['recommendations'].append({
                        'profile': profile['profile'],
                        'type': 'content_mismatch',
                        'message': f"{profile['profile']} drops off early (avg {profile['avg_duration']} mins). Consider: 1) More relevant examples for this segment, 2) Address their specific pain points earlier, 3) Shorten intro for this audience."
                    })
                elif profile['avg_chat_score'] < 10:
                    insights['recommendations'].append({
                        'profile': profile['profile'],
                        'type': 'low_interaction',
                        'message': f"{profile['profile']} stays but doesn't engage ({profile['avg_chat_score']}/30 chat score). Consider: 1) Direct questions to this segment, 2) Use polls, 3) Share segment-specific case studies."
                    })
        
        self.insights['profile_insights'] = insights
        return insights
    
    def generate_summary_stats(self):
        """Generate overall summary statistics"""
        if self.participants_data is None:
            return None
        
        total_participants = len(self.participants_data)
        avg_duration = self.participants_data['duration_mins'].mean()
        
        if self.engagement_scores is not None and len(self.engagement_scores) > 0:
            hot_leads = len(self.engagement_scores[self.engagement_scores['category'] == 'Hot'])
            warm_leads = len(self.engagement_scores[self.engagement_scores['category'] == 'Warm'])
            cold_leads = len(self.engagement_scores[self.engagement_scores['category'] == 'Cold'])
        else:
            hot_leads = warm_leads = cold_leads = 0
        
        chat_messages = len(self.chat_data) if self.chat_data is not None else 0
        
        # Handle questions - check if column exists
        if self.chat_data is not None and 'is_question' in self.chat_data.columns:
            questions_asked = len(self.chat_data[self.chat_data['is_question']])
        else:
            questions_asked = 0
        
        summary = {
            'total_participants': total_participants,
            'avg_duration_mins': round(avg_duration, 1),
            'hot_leads': hot_leads,
            'warm_leads': warm_leads,
            'cold_leads': cold_leads,
            'total_chat_messages': chat_messages,
            'total_questions': questions_asked,
        }
        
        self.insights['summary'] = summary
        return summary
    
    def export_results(self, output_dir='./output'):
        """Export all analysis results"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Export engagement scores
        if self.engagement_scores is not None and len(self.engagement_scores) > 0:
            self.engagement_scores.to_csv(f'{output_dir}/engagement_scores.csv', index=False)
            print(f"✓ Exported engagement scores")
        
        # Export RM follow-ups
        if 'rm_follow_ups' in self.insights:
            for rm_data in self.insights['rm_follow_ups']:
                rm_name = rm_data['rm_name'].replace(' ', '_')
                leads_df = pd.DataFrame(rm_data['leads'])
                leads_df.to_csv(f'{output_dir}/followup_{rm_name}.csv', index=False)
            print(f"✓ Exported RM follow-up lists")
        
        # Export summary
        if 'summary' in self.insights:
            with open(f'{output_dir}/summary.json', 'w') as f:
                json.dump(self.insights['summary'], f, indent=2)
            print(f"✓ Exported summary statistics")
        
        # Export exit timeline
        if 'exit_timeline' in self.insights:
            self.insights['exit_timeline'].to_csv(f'{output_dir}/exit_timeline.csv', index=False)
            print(f"✓ Exported exit timeline")
        
        # Export profile analysis
        if 'profile_analysis' in self.insights:
            profile_df = pd.DataFrame(self.insights['profile_analysis'])
            profile_df.to_csv(f'{output_dir}/profile_analysis.csv', index=False)
            print(f"✓ Exported profile analysis")
        
        # Export profile insights
        if 'profile_insights' in self.insights:
            with open(f'{output_dir}/profile_insights.json', 'w') as f:
                json.dump(self.insights['profile_insights'], f, indent=2, default=str)
            print(f"✓ Exported profile insights")
        
        return True


# Example usage
if __name__ == "__main__":
    analyzer = MasterclassAnalyzer()
    
    # Load data
    analyzer.load_zoom_participants('zoom_participants.csv')
    analyzer.load_zoom_chat('zoom_chat.txt')
    analyzer.load_crm_data('crm_leads.csv')
    
    # Match and analyze
    analyzer.match_participants_with_crm()
    analyzer.calculate_engagement_scores(total_duration_mins=60)
    analyzer.analyze_exit_timeline(total_duration_mins=60)
    analyzer.get_inactive_leads_by_rm(min_score=40)
    analyzer.analyze_by_profile()  # NEW: Profile analysis
    analyzer.get_profile_insights()  # NEW: Profile insights
    analyzer.generate_summary_stats()
    
    # Export results
    analyzer.export_results()
