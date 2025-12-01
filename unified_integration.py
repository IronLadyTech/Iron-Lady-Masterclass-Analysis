"""
Unified Masterclass Data Integration
Pulls data directly from both Zoom and Zoho CRM APIs

This combines:
- Zoom participant data (attendance, duration)
- Zoho CRM lead data (Lead Owner, status, profile)
- Automatic matching by email
- Attendance sync back to Zoho
"""

import pandas as pd
from datetime import datetime
import os
from zoom_api import ZoomAPI
from zoho_crm_api import ZohoCRMAPI


class MasterclassDataIntegration:
    """
    Unified integration for pulling masterclass data from Zoom and Zoho CRM
    
    Usage:
        integration = MasterclassDataIntegration()
        data = integration.pull_masterclass_data(zoom_meeting_id)
        integration.sync_attendance_to_zoho(day_number=1)
    """
    
    def __init__(self):
        """Initialize both API clients"""
        self.zoom = ZoomAPI()
        self.zoho = ZohoCRMAPI()
        
        self.participants_data = None
        self.crm_data = None
        self.merged_data = None
    
    def pull_zoom_participants(self, meeting_id, deduplicate=True):
        """
        Pull participant data from Zoom
        
        Args:
            meeting_id: Zoom meeting ID
            deduplicate: Sum durations for same person (default: True)
        """
        print("\n" + "="*60)
        print("📹 PULLING ZOOM DATA")
        print("="*60)
        
        self.participants_data = self.zoom.get_meeting_participants(meeting_id, deduplicate)
        
        if self.participants_data.empty:
            print("⚠️ No participants found")
            return None
        
        return self.participants_data
    
    def pull_zoho_leads(self, only_matching=True):
        """
        Pull lead data from Zoho CRM
        
        Args:
            only_matching: If True, only fetch leads that match Zoom participants
        """
        print("\n" + "="*60)
        print("📋 PULLING ZOHO CRM DATA")
        print("="*60)
        
        if only_matching and self.participants_data is not None:
            # Only fetch leads that match Zoom participants
            emails = self.participants_data['email'].dropna().unique().tolist()
            self.crm_data = self.zoho.get_leads_by_email(emails)
        else:
            # Fetch all leads
            self.crm_data = self.zoho.get_all_leads()
        
        if self.crm_data.empty:
            print("⚠️ No CRM data found")
            return None
        
        return self.crm_data
    
    def merge_data(self):
        """
        Merge Zoom participants with Zoho CRM data
        """
        if self.participants_data is None:
            print("⚠️ No Zoom data to merge")
            return None
        
        if self.crm_data is None:
            print("⚠️ No CRM data to merge - using Zoom data only")
            self.merged_data = self.participants_data.copy()
            return self.merged_data
        
        print("\n" + "="*60)
        print("🔗 MERGING DATA")
        print("="*60)
        
        # Merge on email
        self.merged_data = self.participants_data.merge(
            self.crm_data,
            on='email',
            how='left',
            suffixes=('_zoom', '_crm')
        )
        
        # Count matches
        crm_match_col = 'Email' if 'Email' in self.crm_data.columns else 'id'
        if crm_match_col in self.merged_data.columns:
            matched = self.merged_data[crm_match_col].notna().sum()
        else:
            matched = 0
        
        print(f"✓ Merged {len(self.participants_data)} Zoom participants with CRM data")
        print(f"  Matched with CRM: {matched}")
        print(f"  Not in CRM: {len(self.participants_data) - matched}")
        
        return self.merged_data
    
    def pull_masterclass_data(self, zoom_meeting_id, include_crm=True, crm_only_matching=True):
        """
        Complete workflow: Pull Zoom data, pull CRM data, merge
        
        Args:
            zoom_meeting_id: Zoom meeting ID
            include_crm: Whether to pull CRM data (default: True)
            crm_only_matching: Only fetch matching CRM leads (default: True)
        
        Returns:
            Merged DataFrame
        """
        print("\n" + "="*60)
        print("🚀 PULLING MASTERCLASS DATA")
        print("="*60)
        
        # Step 1: Pull Zoom data
        self.pull_zoom_participants(zoom_meeting_id)
        
        # Step 2: Pull CRM data
        if include_crm:
            self.pull_zoho_leads(only_matching=crm_only_matching)
        
        # Step 3: Merge
        self.merge_data()
        
        # Summary
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        
        if self.merged_data is not None and not self.merged_data.empty:
            print(f"Total unique participants: {len(self.merged_data)}")
            print(f"Average duration: {self.merged_data['duration_mins'].mean():.1f} minutes")
            
            if 'Lead_Owner' in self.merged_data.columns:
                owner_counts = self.merged_data['Lead_Owner'].value_counts()
                print(f"\nBy Lead Owner:")
                for owner, count in owner_counts.head(5).items():
                    print(f"  {owner}: {count} participants")
        
        return self.merged_data
    
    def sync_attendance_to_zoho(self, day_number=1, min_duration_mins=5):
        """
        Sync attendance back to Zoho CRM
        
        Args:
            day_number: Which day (1, 2, 3, etc.)
            min_duration_mins: Minimum minutes to count as attended
        """
        if self.merged_data is None or self.merged_data.empty:
            print("⚠️ No data to sync")
            return
        
        print("\n" + "="*60)
        print(f"🔄 SYNCING DAY {day_number} ATTENDANCE TO ZOHO")
        print("="*60)
        
        # Prepare updates
        updates = []
        field_name = f'Day_{day_number}_Attendance'
        
        for idx, row in self.merged_data.iterrows():
            lead_id = row.get('id')
            if not lead_id:
                continue
            
            attended = row['duration_mins'] >= min_duration_mins
            updates.append({
                'id': lead_id,
                field_name: 'Yes' if attended else 'No'
            })
        
        if not updates:
            print("⚠️ No leads to update")
            return
        
        print(f"Updating {len(updates)} leads...")
        
        # Bulk update
        result = self.zoho.bulk_update_leads(updates)
        
        print(f"\n✓ Updated: {result['updated']}")
        print(f"✗ Failed: {result['failed']}")
        
        return result
    
    def export_to_csv(self, output_file=None):
        """Export merged data to CSV"""
        if self.merged_data is None or self.merged_data.empty:
            print("⚠️ No data to export")
            return None
        
        if not output_file:
            output_file = f'masterclass_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        self.merged_data.to_csv(output_file, index=False)
        print(f"✓ Exported {len(self.merged_data)} records to {output_file}")
        
        return output_file
    
    def get_attendance_stats(self):
        """Get attendance statistics"""
        if self.merged_data is None or self.merged_data.empty:
            return None
        
        df = self.merged_data
        total = len(df)
        
        stats = {
            'total_participants': total,
            'avg_duration': df['duration_mins'].mean(),
            'left_0_5': len(df[df['duration_mins'] <= 5]),
            'left_0_10': len(df[df['duration_mins'] <= 10]),
            'stayed_60_plus': len(df[df['duration_mins'] >= 60]),
            'stayed_100_plus': len(df[df['duration_mins'] >= 100]),
        }
        
        # Add percentages
        stats['left_0_5_pct'] = (stats['left_0_5'] / total) * 100
        stats['left_0_10_pct'] = (stats['left_0_10'] / total) * 100
        stats['stayed_60_plus_pct'] = (stats['stayed_60_plus'] / total) * 100
        stats['stayed_100_plus_pct'] = (stats['stayed_100_plus'] / total) * 100
        
        return stats


def quick_pull(zoom_meeting_id, include_crm=True):
    """
    Quick function to pull masterclass data
    
    Usage:
        data = quick_pull(84405604610)
        data = quick_pull(84405604610, include_crm=False)  # Zoom only
    """
    integration = MasterclassDataIntegration()
    return integration.pull_masterclass_data(zoom_meeting_id, include_crm=include_crm)


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("  MASTERCLASS DATA INTEGRATION")
    print("="*70)
    
    # Example: Pull data for a specific meeting
    # integration = MasterclassDataIntegration()
    # data = integration.pull_masterclass_data(zoom_meeting_id=84405604610)
    # stats = integration.get_attendance_stats()
    # print(stats)
    
    # To sync attendance:
    # integration.sync_attendance_to_zoho(day_number=1)
    
    print("\nUsage:")
    print("  from unified_integration import MasterclassDataIntegration")
    print("  ")
    print("  integration = MasterclassDataIntegration()")
    print("  data = integration.pull_masterclass_data(84405604610)")
    print("  integration.sync_attendance_to_zoho(day_number=1)")