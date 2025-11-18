#!/usr/bin/env python3
"""
Complete Workflow Script: Analysis + Email Templates
Combines analysis with automatic email template generation
"""

from masterclass_analyzer import MasterclassAnalyzer
from email_templates import generate_email_template, generate_bulk_email_report
import os
import json
from datetime import datetime

def run_complete_analysis(
    participants_file,
    chat_file=None,
    crm_file=None,
    duration=60,
    min_score=40,
    output_dir='./output'
):
    """
    Run complete analysis workflow with email generation
    """
    
    print("="*80)
    print("🚀 COMPLETE MASTERCLASS ANALYSIS WORKFLOW")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize analyzer
    analyzer = MasterclassAnalyzer()
    
    # Step 1: Load data
    print("📥 STEP 1: Loading Data...")
    print("-"*80)
    
    if not analyzer.load_zoom_participants(participants_file):
        print("❌ FAILED: Could not load participants file")
        return False
    
    if chat_file and os.path.exists(chat_file):
        analyzer.load_zoom_chat(chat_file)
    else:
        print("⚠️  No chat file provided or found - continuing without chat data")
    
    if crm_file and os.path.exists(crm_file):
        analyzer.load_crm_data(crm_file)
        analyzer.match_participants_with_crm()
    else:
        print("⚠️  No CRM file provided or found - continuing without CRM matching")
    
    # Step 2: Run analysis
    print("\n🔍 STEP 2: Running Analysis...")
    print("-"*80)
    
    analyzer.calculate_engagement_scores(total_duration_mins=duration)
    analyzer.analyze_exit_timeline(total_duration_mins=duration)
    analyzer.get_inactive_leads_by_rm(min_score=min_score)
    analyzer.analyze_by_profile()  # Profile analysis
    analyzer.get_profile_insights()  # Profile insights
    summary = analyzer.generate_summary_stats()
    
    # Step 3: Generate insights
    print("\n📊 STEP 3: Summary Statistics")
    print("-"*80)
    print(f"Total Participants: {summary['total_participants']}")
    print(f"Average Duration: {summary['avg_duration_mins']} minutes")
    print(f"🔥 Hot Leads: {summary['hot_leads']}")
    print(f"🌡️  Warm Leads: {summary['warm_leads']}")
    print(f"❄️  Cold Leads: {summary['cold_leads']}")
    print(f"💬 Total Chat Messages: {summary['total_chat_messages']}")
    print(f"❓ Total Questions: {summary['total_questions']}")
    
    # Step 4: Export results
    print("\n💾 STEP 4: Exporting Results...")
    print("-"*80)
    
    os.makedirs(output_dir, exist_ok=True)
    analyzer.export_results(output_dir)
    
    # Step 5: Generate email templates
    print("\n✉️  STEP 5: Generating Email Templates...")
    print("-"*80)
    
    if 'rm_follow_ups' in analyzer.insights and analyzer.insights['rm_follow_ups']:
        email_file = os.path.join(output_dir, 'email_templates.txt')
        generate_bulk_email_report(analyzer.insights['rm_follow_ups'], email_file)
        print(f"✅ Email templates saved to: {email_file}")
    else:
        print("ℹ️  No inactive leads found - no email templates generated")
    
    # Step 6: Generate actionable insights
    print("\n💡 STEP 6: Actionable Insights")
    print("-"*80)
    
    # Hot leads requiring immediate action
    if analyzer.engagement_scores is not None:
        hot_leads = analyzer.engagement_scores[
            analyzer.engagement_scores['category'] == 'Hot'
        ]
        if len(hot_leads) > 0:
            print(f"🎯 PRIORITY ACTION: {len(hot_leads)} hot leads need immediate follow-up!")
            print("   Recommended: Call within 24 hours")
            
            hot_file = os.path.join(output_dir, 'HOT_LEADS_PRIORITY.csv')
            hot_leads.to_csv(hot_file, index=False)
            print(f"   Priority list saved to: {hot_file}")
    
    # Profile-based insights
    if 'profile_insights' in analyzer.insights and analyzer.insights['profile_insights']:
        print(f"\n👥 PROFILE INSIGHTS:")
        insights = analyzer.insights['profile_insights']
        
        if insights['best_performing_profile']:
            best = insights['best_performing_profile']
            print(f"   🏆 Top Profile: {best['profile']} (Avg: {best['avg_score']}/100, {best['hot_percentage']:.1f}% hot leads)")
        
        if insights['recommendations']:
            print(f"\n   📋 Key Recommendations:")
            for i, rec in enumerate(insights['recommendations'][:3], 1):  # Show top 3
                print(f"   {i}. {rec['profile']}: {rec['message'][:100]}...")
    
    # Exit timeline insights
    if 'critical_dropoff_moments' in analyzer.insights:
        critical = analyzer.insights['critical_dropoff_moments']
        if len(critical) > 0:
            print(f"\n⚠️  CONTENT REVIEW NEEDED:")
            for idx, row in critical.iterrows():
                print(f"   - Major drop-off at {row['minute']} minutes ({row['drop']:.1f}% decline)")
            print("   Recommended: Review recording at these timestamps")
    
    # RM workload distribution
    if analyzer.engagement_scores is not None and 'rm_name' in analyzer.engagement_scores.columns:
        rm_counts = analyzer.engagement_scores['rm_name'].value_counts()
        print(f"\n👥 RM WORKLOAD DISTRIBUTION:")
        for rm, count in rm_counts.items():
            print(f"   {rm}: {count} leads")
    
    # Final summary
    print("\n" + "="*80)
    print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
    print("="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n📁 All results saved to: {output_dir}")
    print("\n📋 Next Steps:")
    print("   1. Review hot leads priority list")
    print("   2. Send email templates to RMs")
    print("   3. Review exit timeline for content improvements")
    print("   4. Schedule follow-up calls with hot leads")
    print("="*80)
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Complete masterclass analysis workflow with email generation'
    )
    
    parser.add_argument(
        '--participants',
        required=True,
        help='Path to Zoom participants CSV'
    )
    
    parser.add_argument(
        '--chat',
        help='Path to Zoom chat TXT (optional)'
    )
    
    parser.add_argument(
        '--crm',
        help='Path to CRM leads CSV (optional)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Masterclass duration in minutes (default: 60)'
    )
    
    parser.add_argument(
        '--min-score',
        type=int,
        default=40,
        help='Minimum score for inactive classification (default: 40)'
    )
    
    parser.add_argument(
        '--output',
        default='./output',
        help='Output directory (default: ./output)'
    )
    
    args = parser.parse_args()
    
    success = run_complete_analysis(
        participants_file=args.participants,
        chat_file=args.chat,
        crm_file=args.crm,
        duration=args.duration,
        min_score=args.min_score,
        output_dir=args.output
    )
    
    exit(0 if success else 1)