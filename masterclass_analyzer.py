import pandas as pd
import re
from datetime import datetime, timedelta
import json

class MasterclassAnalyzer:
    # ============================================
    # TEAM MEMBERS TO EXCLUDE FROM ANALYSIS
    # ============================================
    # Add any domain to exclude all emails from that domain
    EXCLUDED_DOMAINS = [
        '@iamironlady.com',
        '@ironlady.com',
    ]
    
    # Add specific personal emails of team members to exclude
    # (Add personal emails here if team members join from personal accounts)
    EXCLUDED_EMAILS = [
        'afreen786@gmail.com',
        'abhinayajanagama@gmail.com',
        'farhanaaz0416@gmail.com',
        'mghkhandelwal93@gmail.com',
        'sharanchhabra65@gmail.com',
    ]
    # ============================================
    
    def __init__(self):
        self.participants_data = None
        self.chat_data = None
        self.crm_data = None
        self.engagement_scores = []
        self.insights = {}
        self.excluded_count = 0  # Track how many team members were excluded
    
    def is_team_member(self, email):
        """Check if email belongs to a team member"""
        if pd.isna(email) or not email:
            return False
        
        email_lower = str(email).strip().lower()
        
        # Check excluded domains
        for domain in self.EXCLUDED_DOMAINS:
            if email_lower.endswith(domain.lower()):
                return True
        
        # Check specific excluded emails
        if email_lower in [e.lower() for e in self.EXCLUDED_EMAILS]:
            return True
        
        return False
    
    def filter_team_members(self, df, email_column='email'):
        """Remove team members from dataframe"""
        if df is None or df.empty:
            return df
        
        if email_column not in df.columns:
            return df
        
        original_count = len(df)
        
        # Create mask for non-team members
        is_team = df[email_column].apply(self.is_team_member)
        filtered_df = df[~is_team].copy()
        
        excluded = original_count - len(filtered_df)
        self.excluded_count += excluded
        
        if excluded > 0:
            print(f"  🏢 Excluded {excluded} team members (@iamironlady.com)")
            # Show who was excluded (for verification)
            excluded_emails = df[is_team][email_column].tolist()
            if len(excluded_emails) <= 5:
                for email in excluded_emails:
                    print(f"      - {email}")
            else:
                for email in excluded_emails[:3]:
                    print(f"      - {email}")
                print(f"      ... and {len(excluded_emails) - 3} more")
        
        return filtered_df
        
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
            
            # Find and convert duration column to numeric FIRST (before deduplication)
            duration_col = None
            for col in df.columns:
                if 'duration' in col and 'minute' in col:
                    duration_col = col
                    break
            
            if duration_col:
                # Convert duration to numeric (handle formats like "45 min", "45", or 45)
                df['duration_mins'] = pd.to_numeric(
                    df[duration_col].astype(str).str.extract(r'(\d+)')[0],
                    errors='coerce'
                ).fillna(0)
            else:
                print("  ⚠️ Warning: Could not find duration column")
                df['duration_mins'] = 0
            
            # Find email column
            email_col = 'email' if 'email' in df.columns else None
            
            if not email_col:
                print("  ⚠️ Warning: No email column found - cannot deduplicate")
            else:
                # Standardize email column
                df[email_col] = df[email_col].str.strip().str.lower()
                
                # Check for duplicates
                unique_emails = df[email_col].nunique()
                if unique_emails < original_count:
                    duplicate_count = original_count - unique_emails
                    print(f"  ⚠️  Found {duplicate_count} duplicate entries (people who left/rejoined)")
                    print(f"  📧 Deduplicating to {unique_emails} unique participants...")
                    
                    # Group by email and sum durations, keep first for other fields
                    agg_dict = {'duration_mins': 'sum'}  # Sum the numeric duration
                    
                    for col in df.columns:
                        if col not in [email_col, 'duration_mins', duration_col]:
                            agg_dict[col] = 'first'
                    
                    df = df.groupby(email_col, as_index=False).agg(agg_dict)
                    
                    print(f"  ✓ Deduplicated to {len(df)} unique participants")
                    print(f"  ✓ Total durations summed for each person")
            
            # Create standardized email column if not exists
            if 'email' not in df.columns and email_col:
                df['email'] = df[email_col]
            
            # Filter out team members (Iron Lady staff)
            df = self.filter_team_members(df, 'email')
            
            self.participants_data = df
            print(f"✓ Loaded {len(df)} unique participant(s) (excluding team)")
            print(f"  Columns available: {df.columns.tolist()}")
            return True
        except Exception as e:
            print(f"✗ Error loading participants: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_zoom_chat(self, file_path):
        """
        Load Zoom chat log (TXT or CSV)
        
        Handles Zoom chat format:
        "2025-11-29 17:03:48 From John Doe to Everyone:
        	Message text here"
        
        Note: Message is on the NEXT line, indented with tab
        """
        try:
            chat_records = []
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Split by the "From ... to Everyone:" pattern to get each message block
            # Pattern: date time From Name to Everyone:\n\tmessage
            import re
            
            # Pattern to match: "2025-11-29 17:03:48 From Name to Everyone:"
            pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+From\s+(.+?)\s+to\s+Everyone:'
            
            # Find all matches with their positions
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            
            print(f"  📄 Found {len(matches)} chat messages")
            
            for i, match in enumerate(matches):
                timestamp = match.group(1)
                sender = match.group(2).strip()
                
                # Get the message content (text between this match and the next)
                start_pos = match.end()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
                
                message_text = content[start_pos:end_pos].strip()
                
                # Clean up the message (remove leading tabs/newlines)
                message_text = message_text.strip('\t\n\r ')
                
                # Remove any trailing timestamp patterns from message
                message_text = re.sub(r'\n\s*\d{4}-\d{2}-\d{2}.*$', '', message_text, flags=re.DOTALL)
                message_text = message_text.strip()
                
                # Skip messages from Admin/Iron Lady team (promotional messages)
                if 'admin iron lady' in sender.lower() or sender.lower().endswith('@iamironlady.com'):
                    continue
                
                if message_text:
                    chat_records.append({
                        'timestamp': timestamp,
                        'sender': sender,
                        'recipient': 'Everyone',
                        'message': message_text,
                        'is_question': '?' in message_text
                    })
            
            self.chat_data = pd.DataFrame(chat_records)
            
            if len(chat_records) > 0:
                # Show sample parsed messages
                print(f"  ✓ Sample messages:")
                for msg in chat_records[:3]:
                    preview = msg['message'][:50] + '...' if len(msg['message']) > 50 else msg['message']
                    print(f"      {msg['sender']}: {preview}")
                
                # Count questions
                questions = sum(1 for r in chat_records if r['is_question'])
                print(f"  ❓ Found {questions} questions (messages with '?')")
            
            print(f"✓ Loaded {len(chat_records)} chat messages")
            return True
            
        except Exception as e:
            print(f"✗ Error loading chat: {e}")
            import traceback
            traceback.print_exc()
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
                elif 'experience' in col_lower or 'years' in col_lower:
                    column_mapping['experience'] = col
            
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
            
            # Handle Total Years of Experience
            if 'experience' in column_mapping:
                # Convert to numeric, handling empty values and strings
                df['experience_years'] = pd.to_numeric(df[column_mapping['experience']], errors='coerce')
                print(f"  Created 'experience_years' from '{column_mapping['experience']}'")
                
                # Create experience brackets for analysis
                def get_exp_bracket(years):
                    if pd.isna(years):
                        return 'Not Specified'
                    elif years <= 5:
                        return '0-5 years'
                    elif years <= 10:
                        return '6-10 years'
                    elif years <= 15:
                        return '11-15 years'
                    elif years <= 20:
                        return '16-20 years'
                    else:
                        return '20+ years'
                
                df['experience_bracket'] = df['experience_years'].apply(get_exp_bracket)
                print(f"  Created 'experience_bracket' column")
            
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
        
        # Use 'email' column (which is normalized lowercase) if it exists
        # Otherwise find any email column
        
        # Find email column in participants data
        if 'email' in self.participants_data.columns:
            participant_email_col = 'email'
        else:
            participant_email_col = None
            for col in self.participants_data.columns:
                if 'email' in col.lower():
                    participant_email_col = col
                    break
        
        if not participant_email_col:
            print("✗ Could not find email column in participants data")
            return False
        
        # Find email column in CRM data - prefer lowercase 'email' which is normalized
        if 'email' in self.crm_data.columns:
            crm_email_col = 'email'
        else:
            crm_email_col = None
            for col in self.crm_data.columns:
                if 'email' in col.lower():
                    crm_email_col = col
                    break
        
        if not crm_email_col:
            print("✗ Could not find email column in CRM data")
            return False
        
        print(f"  Merging on: participants[{participant_email_col}] = crm[{crm_email_col}]")
        
        # Normalize emails before merge
        self.participants_data['email_normalized'] = self.participants_data[participant_email_col].str.strip().str.lower()
        self.crm_data['email_normalized'] = self.crm_data[crm_email_col].str.strip().str.lower()
        
        # Debug: show sample emails
        print(f"  Sample participant emails: {self.participants_data['email_normalized'].head(3).tolist()}")
        print(f"  Sample CRM emails: {self.crm_data['email_normalized'].head(3).tolist()}")
        
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
        
        # Count matches by checking for a CRM-specific column
        crm_indicator_col = None
        for col in ['Record Id', 'rm_name', 'profile', 'experience_years']:
            if col in merged.columns:
                crm_indicator_col = col
                break
        
        if crm_indicator_col:
            matched_count = merged[crm_indicator_col].notna().sum()
        else:
            matched_count = 0
            
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
                # CRM fields - Profile & Experience
                'profile': row.get('profile', ''),
                'experience_years': row.get('experience_years', None),
                'experience_bracket': row.get('experience_bracket', 'Not Specified'),
                # Additional CRM fields if available
                'lead_name': row.get('lead_name', row.get('Last Name', '')),
            })
        
        self.engagement_scores = pd.DataFrame(scores)
        
        # Show CRM data availability
        if 'profile' in self.engagement_scores.columns:
            profile_count = self.engagement_scores['profile'].notna().sum()
            profile_count = len(self.engagement_scores[self.engagement_scores['profile'] != ''])
            if profile_count > 0:
                print(f"  📊 Profile data available for {profile_count} participants")
        
        if 'experience_years' in self.engagement_scores.columns:
            exp_count = self.engagement_scores['experience_years'].notna().sum()
            if exp_count > 0:
                print(f"  👔 Experience data available for {exp_count} participants")
        
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
        for col in ['profile', 'industry', 'profession', 'segment', 'category_name', 'Industry/Field of Work']:
            if col in self.engagement_scores.columns:
                profile_col = col
                break
        
        if profile_col is None:
            print("ℹ️  No profile/industry column found in data")
            return None
        
        # Filter out empty/NaN profiles
        valid_profiles = self.engagement_scores[
            self.engagement_scores[profile_col].notna() & 
            (self.engagement_scores[profile_col] != '') &
            (self.engagement_scores[profile_col] != 'Not Specified')
        ]
        
        if len(valid_profiles) == 0:
            print("ℹ️  No valid profile data found (all empty or Not Specified)")
            return None
        
        print(f"  📊 Analyzing {len(valid_profiles)} participants with profile data")
        
        # Group by profile
        profile_groups = valid_profiles.groupby(profile_col)
        
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
    
    def analyze_by_experience(self):
        """Analyze engagement patterns by years of experience"""
        if self.engagement_scores is None or len(self.engagement_scores) == 0:
            return None
        
        # Check if experience column exists
        exp_col = None
        for col in ['experience_bracket', 'experience_years', 'years_of_experience', 'Total Years Of Experience.']:
            if col in self.engagement_scores.columns:
                exp_col = col
                break
        
        if exp_col is None:
            print("ℹ️  No experience column found in data")
            print(f"     Available columns: {self.engagement_scores.columns.tolist()}")
            return None
        
        # If we have raw years, create brackets
        if exp_col in ['experience_years', 'years_of_experience', 'Total Years Of Experience.']:
            def get_exp_bracket(years):
                if pd.isna(years):
                    return 'Not Specified'
                try:
                    years = float(years)
                    if years <= 5:
                        return '0-5 years'
                    elif years <= 10:
                        return '6-10 years'
                    elif years <= 15:
                        return '11-15 years'
                    elif years <= 20:
                        return '16-20 years'
                    else:
                        return '20+ years'
                except:
                    return 'Not Specified'
            
            self.engagement_scores['experience_bracket'] = self.engagement_scores[exp_col].apply(get_exp_bracket)
            exp_col = 'experience_bracket'
        
        # Filter out completely empty experience data
        valid_exp = self.engagement_scores[
            self.engagement_scores[exp_col].notna() & 
            (self.engagement_scores[exp_col] != '')
        ]
        
        # Count how many have actual experience data (not "Not Specified")
        with_exp_data = valid_exp[valid_exp[exp_col] != 'Not Specified']
        
        if len(with_exp_data) == 0:
            print("ℹ️  No experience data found (all participants are 'Not Specified')")
            return None
        
        print(f"  👔 Analyzing {len(with_exp_data)} participants with experience data")
        
        # Group by experience bracket (include all for analysis)
        exp_groups = valid_exp.groupby(exp_col)
        
        experience_analysis = []
        for exp_level, group in exp_groups:
            if len(group) == 0:
                continue
            
            analysis = {
                'experience_level': exp_level,
                'total_count': len(group),
                'avg_score': round(group['total_score'].mean(), 1),
                'avg_duration': round(group['duration_mins'].mean(), 1),
                'hot_count': len(group[group['category'] == 'Hot']),
                'warm_count': len(group[group['category'] == 'Warm']),
                'cold_count': len(group[group['category'] == 'Cold']),
                'hot_percentage': round(len(group[group['category'] == 'Hot']) / len(group) * 100, 1),
                'stayed_60_plus': len(group[group['duration_mins'] >= 60]),
                'stayed_60_plus_pct': round(len(group[group['duration_mins'] >= 60]) / len(group) * 100, 1),
            }
            
            experience_analysis.append(analysis)
        
        # Define custom sort order for experience brackets
        exp_order = ['0-5 years', '6-10 years', '11-15 years', '16-20 years', '20+ years', 'Not Specified']
        experience_analysis = sorted(
            experience_analysis, 
            key=lambda x: exp_order.index(x['experience_level']) if x['experience_level'] in exp_order else 99
        )
        
        self.insights['experience_analysis'] = experience_analysis
        print(f"✓ Analyzed engagement across {len(experience_analysis)} experience levels")
        
        return experience_analysis
    
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