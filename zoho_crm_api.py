"""
Zoho CRM API Integration
Pulls lead data directly from Zoho CRM

Setup:
1. Go to https://api-console.zoho.com/
2. Create a Server-based Application
3. Get Client ID, Client Secret
4. Generate Refresh Token with scopes: ZohoCRM.modules.ALL
"""

import requests
import pandas as pd
import os
from datetime import datetime


class ZohoCRMAPI:
    """
    Zoho CRM API client to pull lead data directly
    
    Usage:
        zoho = ZohoCRMAPI(client_id, client_secret, refresh_token)
        leads = zoho.get_all_leads()
    """
    
    def __init__(self, client_id=None, client_secret=None, refresh_token=None, domain='com'):
        """
        Initialize Zoho CRM API client
        
        Get credentials from: https://api-console.zoho.com/
        Create a "Server-based Application"
        
        Args:
            domain: 'com' (US), 'eu' (Europe), 'in' (India), 'com.au' (Australia), 'jp' (Japan)
        """
        self.client_id = client_id or os.getenv('ZOHO_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('ZOHO_CLIENT_SECRET')
        self.refresh_token = refresh_token or os.getenv('ZOHO_REFRESH_TOKEN')
        self.domain = domain
        self.access_token = None
        self.api_url = f'https://www.zohoapis.{domain}/crm/v3'
        self.accounts_url = f'https://accounts.zoho.{domain}'
    
    def get_access_token(self):
        """Get OAuth access token using refresh token"""
        url = f'{self.accounts_url}/oauth/v2/token'
        
        params = {
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get('access_token')
            print(f"✓ Connected to Zoho CRM API")
            return self.access_token
        except Exception as e:
            print(f"✗ Error connecting to Zoho: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"  Response: {e.response.text}")
            return None
    
    def _get_headers(self):
        """Get headers with auth token"""
        if not self.access_token:
            self.get_access_token()
        return {
            'Authorization': f'Zoho-oauthtoken {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_all_leads(self, fields=None, criteria=None, max_records=None):
        """
        Get all leads from Zoho CRM
        
        Args:
            fields: List of fields to retrieve (default: common fields)
            criteria: Filter criteria (e.g., "(Lead_Status:equals:Hot)")
            max_records: Maximum records to fetch (default: all)
        
        Returns:
            DataFrame with lead data
        """
        print(f"\n📊 Fetching leads from Zoho CRM...")
        
        if not self.access_token:
            print("  Getting access token first...")
            if not self.get_access_token():
                print("✗ Failed to get access token")
                return pd.DataFrame()
        
        if not fields:
            fields = [
                'id', 'Email', 'First_Name', 'Last_Name', 'Full_Name',
                'Owner', 'Lead_Status', 'Lead_Source',
                'Industry', 'Company', 'Phone', 'Mobile',
                'Created_Time', 'Modified_Time'
            ]
        
        url = f'{self.api_url}/Leads'
        
        all_leads = []
        page = 1
        per_page = 200
        more_records = True
        
        while more_records:
            params = {
                'fields': ','.join(fields),
                'per_page': per_page,
                'page': page
            }
            
            if criteria:
                params['criteria'] = criteria
            
            try:
                response = requests.get(url, headers=self._get_headers(), params=params)
                
                # Handle different status codes
                if response.status_code == 200:
                    data = response.json()
                    leads = data.get('data', [])
                    all_leads.extend(leads)
                    print(f"  Page {page}: {len(leads)} leads")
                    
                    # Check if more records
                    info = data.get('info', {})
                    more_records = info.get('more_records', False)
                    
                elif response.status_code == 204:
                    # No content - no more records
                    print(f"  Page {page}: No records")
                    more_records = False
                    
                elif response.status_code == 401:
                    print(f"✗ Authentication failed - refreshing token...")
                    self.access_token = None
                    if self.get_access_token():
                        continue  # Retry with new token
                    else:
                        more_records = False
                        
                else:
                    print(f"✗ Error {response.status_code}: {response.text[:200]}")
                    more_records = False
                
                if max_records and len(all_leads) >= max_records:
                    all_leads = all_leads[:max_records]
                    more_records = False
                
                page += 1
                
            except Exception as e:
                print(f"✗ Error fetching leads: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"  Response: {e.response.text[:200]}")
                break
        
        if not all_leads:
            print("⚠️ No leads found")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_leads)
        
        # Extract Owner name from nested dict
        if 'Owner' in df.columns:
            df['Lead_Owner'] = df['Owner'].apply(
                lambda x: x.get('name', '') if isinstance(x, dict) else str(x)
            )
        
        # Standardize email
        if 'Email' in df.columns:
            df['email'] = df['Email'].str.strip().str.lower()
        
        print(f"\n✓ Fetched {len(df)} leads from Zoho CRM")
        
        return df
    
    def get_leads_by_email(self, emails):
        """
        Get specific leads by their email addresses
        
        Args:
            emails: List of email addresses
        
        Returns:
            DataFrame with matching leads
        """
        print(f"\n🔍 Searching for {len(emails)} emails in Zoho CRM...")
        
        all_leads = []
        batch_size = 10  # Zoho search limit
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            
            # Build criteria (Email:equals:email1 OR Email:equals:email2 ...)
            criteria_parts = [f"(Email:equals:{email})" for email in batch]
            criteria = '(' + ' or '.join(criteria_parts) + ')'
            
            url = f'{self.api_url}/Leads/search'
            params = {'criteria': criteria}
            
            try:
                response = requests.get(url, headers=self._get_headers(), params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    leads = data.get('data', [])
                    all_leads.extend(leads)
                    print(f"  Batch {i//batch_size + 1}: Found {len(leads)} leads")
                elif response.status_code == 204:
                    print(f"  Batch {i//batch_size + 1}: No matches")
                else:
                    print(f"  Batch {i//batch_size + 1}: Error {response.status_code}")
                    
            except Exception as e:
                print(f"✗ Error searching: {e}")
        
        if not all_leads:
            print("⚠️ No matching leads found")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_leads)
        
        # Extract Owner name
        if 'Lead_Owner' in df.columns:
            df['Lead_Owner'] = df['Lead_Owner'].apply(
                lambda x: x.get('name', '') if isinstance(x, dict) else x
            )
        
        if 'Email' in df.columns:
            df['email'] = df['Email'].str.strip().str.lower()
        
        print(f"\n✓ Found {len(df)} matching leads")
        
        return df
    
    def get_lead_by_email(self, email):
        """Get a single lead by email"""
        url = f'{self.api_url}/Leads/search'
        params = {'criteria': f'(Email:equals:{email})'}
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code == 200:
                data = response.json()
                leads = data.get('data', [])
                if leads:
                    return leads[0]
            return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None
    
    def update_lead(self, lead_id, data):
        """
        Update a lead in Zoho CRM
        
        Args:
            lead_id: Zoho lead ID
            data: Dict of fields to update
        """
        url = f'{self.api_url}/Leads/{lead_id}'
        
        payload = {'data': [data]}
        
        try:
            response = requests.put(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get('data') and result['data'][0].get('code') == 'SUCCESS':
                return True
            return False
        except Exception as e:
            print(f"✗ Error updating lead: {e}")
            return False
    
    def bulk_update_leads(self, updates):
        """
        Bulk update multiple leads
        
        Args:
            updates: List of dicts with 'id' and fields to update
        
        Returns:
            Dict with success/failure counts
        """
        url = f'{self.api_url}/Leads'
        
        total_updated = 0
        total_failed = 0
        batch_size = 100  # Zoho limit
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            payload = {'data': batch}
            
            try:
                response = requests.put(url, headers=self._get_headers(), json=payload)
                response.raise_for_status()
                result = response.json()
                
                for item in result.get('data', []):
                    if item.get('code') == 'SUCCESS':
                        total_updated += 1
                    else:
                        total_failed += 1
                        
            except Exception as e:
                print(f"✗ Batch error: {e}")
                total_failed += len(batch)
        
        return {'updated': total_updated, 'failed': total_failed}
    
    def export_leads_to_csv(self, output_file=None, criteria=None):
        """
        Fetch all leads and save to CSV
        
        Args:
            output_file: Output file path
            criteria: Filter criteria
        """
        df = self.get_all_leads(criteria=criteria)
        
        if df.empty:
            print("⚠️ No data to export")
            return None
        
        if not output_file:
            output_file = f'zoho_leads_{datetime.now().strftime("%Y%m%d")}.csv'
        
        df.to_csv(output_file, index=False)
        print(f"\n✓ Exported {len(df)} leads to {output_file}")
        
        return output_file


# Quick usage functions
def pull_zoho_leads(criteria=None):
    """
    Quick function to pull Zoho CRM leads
    
    Usage:
        df = pull_zoho_leads()
        df = pull_zoho_leads("(Lead_Status:equals:Hot)")
    """
    zoho = ZohoCRMAPI()
    return zoho.get_all_leads(criteria=criteria)


def find_leads_by_emails(emails):
    """
    Quick function to find leads by email list
    
    Usage:
        df = find_leads_by_emails(['john@example.com', 'jane@example.com'])
    """
    zoho = ZohoCRMAPI()
    return zoho.get_leads_by_email(emails)


# Example usage
if __name__ == "__main__":
    print("="*60)
    print("  ZOHO CRM API INTEGRATION")
    print("="*60)
    
    # Initialize
    zoho = ZohoCRMAPI()
    
    # Get all leads
    print("\n📋 All Leads:")
    df = zoho.get_all_leads(max_records=10)
    if not df.empty:
        print(df[['Email', 'Full_Name', 'Lead_Owner', 'Lead_Status']].head())
    
    # Search for specific emails
    # df = zoho.get_leads_by_email(['john@example.com'])