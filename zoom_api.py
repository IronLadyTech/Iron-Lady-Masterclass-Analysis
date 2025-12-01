"""
Zoom API Integration
Pulls meeting participant data directly from Zoom

Setup:
1. Go to https://marketplace.zoom.us/
2. Create a Server-to-Server OAuth app
3. Get Account ID, Client ID, Client Secret
4. Add scopes: report:read:admin, meeting:read:admin
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import base64


class ZoomAPI:
    """
    Zoom API client to pull meeting data directly
    
    Usage:
        zoom = ZoomAPI(account_id, client_id, client_secret)
        participants = zoom.get_meeting_participants(meeting_id)
    """
    
    def __init__(self, account_id=None, client_id=None, client_secret=None):
        """
        Initialize Zoom API client
        
        Get credentials from: https://marketplace.zoom.us/
        Create a "Server-to-Server OAuth" app
        """
        self.account_id = account_id or os.getenv('ZOOM_ACCOUNT_ID')
        self.client_id = client_id or os.getenv('ZOOM_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('ZOOM_CLIENT_SECRET')
        self.access_token = None
        self.base_url = 'https://api.zoom.us/v2'
    
    def get_access_token(self):
        """Get OAuth access token using Server-to-Server OAuth"""
        url = f'https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}'
        
        # Create Basic Auth header
        credentials = f'{self.client_id}:{self.client_secret}'
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get('access_token')
            print(f"✓ Connected to Zoom API")
            return self.access_token
        except Exception as e:
            print(f"✗ Error connecting to Zoom: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"  Response: {e.response.text}")
            return None
    
    def _get_headers(self):
        """Get headers with auth token"""
        if not self.access_token:
            self.get_access_token()
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_meeting_participants(self, meeting_id, deduplicate=True):
        """
        Get all participants from a meeting
        
        Args:
            meeting_id: Zoom meeting ID (e.g., 84405604610 or "853 9764 7279")
            deduplicate: If True, sum durations for same email (default: True)
        
        Returns:
            DataFrame with participant data
        """
        # Clean meeting ID - remove spaces and convert to string
        meeting_id = str(meeting_id).replace(' ', '').replace('-', '')
        
        print(f"\n📊 Fetching participants for meeting {meeting_id}...")
        
        url = f'{self.base_url}/report/meetings/{meeting_id}/participants'
        
        all_participants = []
        next_page_token = ''
        page = 1
        
        while True:
            params = {'page_size': 300}
            if next_page_token:
                params['next_page_token'] = next_page_token
            
            try:
                response = requests.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()
                data = response.json()
                
                participants = data.get('participants', [])
                all_participants.extend(participants)
                
                print(f"  Page {page}: {len(participants)} participants")
                
                next_page_token = data.get('next_page_token', '')
                if not next_page_token:
                    break
                
                page += 1
                
            except Exception as e:
                print(f"✗ Error fetching participants: {e}")
                if hasattr(e, 'response') and e.response:
                    print(f"  Response: {e.response.text}")
                break
        
        if not all_participants:
            print("⚠️ No participants found")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_participants)
        
        print(f"\n✓ Fetched {len(df)} raw participant records")
        
        # Standardize columns
        column_mapping = {
            'user_email': 'email',
            'name': 'name',
            'duration': 'duration_mins',  # Zoom returns duration in seconds!
            'join_time': 'join_time',
            'leave_time': 'leave_time',
            'status': 'status'
        }
        
        # Rename columns that exist
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        # Convert duration from seconds to minutes
        if 'duration_mins' in df.columns:
            df['duration_mins'] = df['duration_mins'] / 60
        
        # Standardize email
        if 'email' in df.columns:
            df['email'] = df['email'].str.strip().str.lower()
        
        # Deduplicate if requested
        if deduplicate and 'email' in df.columns:
            original_count = len(df)
            unique_emails = df['email'].nunique()
            
            if unique_emails < original_count:
                print(f"\n⚠️ Found {original_count - unique_emails} duplicate entries")
                print(f"📧 Deduplicating to {unique_emails} unique participants...")
                
                # Group by email and sum durations
                agg_dict = {'duration_mins': 'sum'}
                for col in df.columns:
                    if col not in ['email', 'duration_mins']:
                        agg_dict[col] = 'first'
                
                df = df.groupby('email', as_index=False).agg(agg_dict)
                print(f"✓ Deduplicated to {len(df)} unique participants")
        
        # Filter out team members (Iron Lady staff)
        if 'email' in df.columns:
            excluded_domains = ['@iamironlady.com', '@ironlady.com']
            excluded_emails = [
                'afreen786@gmail.com',
                'abhinayajanagama@gmail.com',
                'farhanaaz0416@gmail.com',
                'mghkhandelwal93@gmail.com',
                'sharanchhabra65@gmail.com',
            ]
            original_count = len(df)
            
            def is_team_member(email):
                if pd.isna(email):
                    return False
                email_lower = str(email).lower().strip()
                # Check domains
                if any(email_lower.endswith(domain) for domain in excluded_domains):
                    return True
                # Check specific emails
                if email_lower in [e.lower() for e in excluded_emails]:
                    return True
                return False
            
            df = df[~df['email'].apply(is_team_member)]
            excluded = original_count - len(df)
            
            if excluded > 0:
                print(f"🏢 Excluded {excluded} team members")
        
        print(f"\n✓ Final: {len(df)} participants (excluding team)")
        print(f"  Average duration: {df['duration_mins'].mean():.1f} minutes")
        
        return df
    
    def get_users(self):
        """Get list of users in the account"""
        url = f'{self.base_url}/users'
        
        try:
            response = requests.get(url, headers=self._get_headers(), params={'page_size': 300})
            response.raise_for_status()
            data = response.json()
            return data.get('users', [])
        except Exception as e:
            print(f"✗ Error fetching users: {e}")
            return []
    
    def get_past_meetings(self, user_id=None, from_date=None, to_date=None):
        """
        Get list of past meetings for a user
        
        Args:
            user_id: Zoom user ID (if None, will try to find first user)
            from_date: Start date (datetime or string YYYY-MM-DD)
            to_date: End date (datetime or string YYYY-MM-DD)
        
        Returns:
            List of meetings with their IDs
        """
        # For Server-to-Server OAuth, 'me' doesn't work - need actual user ID
        if not user_id:
            print("  Finding users in account...")
            users = self.get_users()
            if users:
                user_id = users[0].get('id')
                print(f"  Using user: {users[0].get('email', user_id)}")
            else:
                print("✗ No users found in account")
                return []
        
        url = f'{self.base_url}/report/users/{user_id}/meetings'
        
        # Default to last 30 days
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            'from': from_date,
            'to': to_date,
            'page_size': 300,
            'type': 'past'
        }
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            
            meetings = data.get('meetings', [])
            print(f"✓ Found {len(meetings)} meetings from {from_date} to {to_date}")
            
            return meetings
            
        except Exception as e:
            print(f"✗ Error fetching meetings: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text[:200]}")
            return []
    
    def get_all_meetings(self, from_date=None, to_date=None):
        """
        Get all meetings from all users in the account
        
        Returns:
            List of all meetings
        """
        all_meetings = []
        users = self.get_users()
        
        print(f"  Found {len(users)} users in account")
        
        for user in users:
            user_id = user.get('id')
            user_email = user.get('email', 'Unknown')
            
            meetings = self.get_past_meetings(user_id, from_date, to_date)
            if meetings:
                print(f"    {user_email}: {len(meetings)} meetings")
                all_meetings.extend(meetings)
        
        return all_meetings
    
    def get_meeting_details(self, meeting_id):
        """Get details for a specific meeting"""
        # Clean meeting ID - remove spaces and dashes
        meeting_id = str(meeting_id).replace(' ', '').replace('-', '')
        
        url = f'{self.base_url}/meetings/{meeting_id}'
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"✗ Error fetching meeting details: {e}")
            return None
    
    def export_participants_to_csv(self, meeting_id, output_file=None):
        """
        Fetch participants and save to CSV
        
        Args:
            meeting_id: Zoom meeting ID
            output_file: Output file path (default: zoom_participants_{meeting_id}.csv)
        """
        df = self.get_meeting_participants(meeting_id)
        
        if df.empty:
            print("⚠️ No data to export")
            return None
        
        if not output_file:
            output_file = f'zoom_participants_{meeting_id}.csv'
        
        df.to_csv(output_file, index=False)
        print(f"\n✓ Exported {len(df)} participants to {output_file}")
        
        return output_file


# Quick usage function
def pull_zoom_participants(meeting_id, deduplicate=True):
    """
    Quick function to pull Zoom participants
    
    Usage:
        df = pull_zoom_participants(84405604610)
    """
    zoom = ZoomAPI()
    return zoom.get_meeting_participants(meeting_id, deduplicate=deduplicate)


# Example usage
if __name__ == "__main__":
    print("="*60)
    print("  ZOOM API INTEGRATION")
    print("="*60)
    
    # Initialize
    zoom = ZoomAPI()
    
    # Get past meetings
    print("\n📅 Recent Meetings:")
    meetings = zoom.get_past_meetings()
    for m in meetings[:5]:
        print(f"  - {m.get('topic')}: ID {m.get('id')} ({m.get('start_time')})")
    
    # Get participants for a specific meeting
    if meetings:
        meeting_id = meetings[0].get('id')
        print(f"\n👥 Participants for meeting {meeting_id}:")
        df = zoom.get_meeting_participants(meeting_id)
        print(df.head())