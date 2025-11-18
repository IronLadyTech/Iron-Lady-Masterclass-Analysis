#!/usr/bin/env python3
"""
Command-line interface for batch processing masterclass analysis
Useful for automation and scheduled tasks
"""

import argparse
import sys
from masterclass_analyzer import MasterclassAnalyzer

def main():
    parser = argparse.ArgumentParser(
        description='Masterclass Analytics CLI - Batch process masterclass data'
    )
    
    parser.add_argument(
        '--participants',
        required=True,
        help='Path to Zoom participants CSV file'
    )
    
    parser.add_argument(
        '--chat',
        help='Path to Zoom chat log TXT file (optional)'
    )
    
    parser.add_argument(
        '--crm',
        help='Path to CRM leads CSV file (optional)'
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
        help='Minimum engagement score threshold for inactive leads (default: 40)'
    )
    
    parser.add_argument(
        '--output',
        default='./output',
        help='Output directory for results (default: ./output)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output messages'
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = MasterclassAnalyzer()
    
    if not args.quiet:
        print("="*60)
        print("📊 Masterclass Analytics - Batch Processing")
        print("="*60)
    
    # Load data
    if not analyzer.load_zoom_participants(args.participants):
        print("❌ Failed to load participants file", file=sys.stderr)
        sys.exit(1)
    
    if args.chat:
        if not analyzer.load_zoom_chat(args.chat):
            print("⚠️  Warning: Failed to load chat file, continuing without chat data", file=sys.stderr)
    
    if args.crm:
        if not analyzer.load_crm_data(args.crm):
            print("⚠️  Warning: Failed to load CRM file, continuing without CRM data", file=sys.stderr)
        else:
            analyzer.match_participants_with_crm()
    
    # Run analysis
    if not args.quiet:
        print("\n🔄 Running analysis...")
    
    analyzer.calculate_engagement_scores(total_duration_mins=args.duration)
    analyzer.analyze_exit_timeline(total_duration_mins=args.duration)
    analyzer.get_inactive_leads_by_rm(min_score=args.min_score)
    summary = analyzer.generate_summary_stats()
    
    # Export results
    analyzer.export_results(args.output)
    
    if not args.quiet:
        print("\n📊 Analysis Complete!")
        print(f"   Total Participants: {summary['total_participants']}")
        print(f"   Hot Leads: {summary['hot_leads']}")
        print(f"   Warm Leads: {summary['warm_leads']}")
        print(f"   Cold Leads: {summary['cold_leads']}")
        print(f"\n💾 Results exported to: {args.output}")
        print("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())