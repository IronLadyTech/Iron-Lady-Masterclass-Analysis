"""
Email Template Generator for RM Follow-ups
Generates personalized email templates based on lead engagement
"""

def generate_email_template(lead_data, masterclass_info=None):
    """Generate personalized email template for a lead"""
    
    name = lead_data.get('name', 'there')
    duration = lead_data.get('duration_mins', 0)
    category = lead_data.get('category', 'Cold')
    total_score = lead_data.get('total_score', 0)
    
    # Determine engagement context
    if duration < 15:
        engagement_note = "briefly joined"
    elif duration < 30:
        engagement_note = "attended the initial part"
    elif duration < 45:
        engagement_note = "stayed for a good portion"
    else:
        engagement_note = "attended most of the session"
    
    # Template based on category
    if category == 'Cold' and duration < 20:
        # Early drop-off
        template = f"""Subject: Quick follow-up on yesterday's masterclass

Hi {name},

I noticed you {engagement_note} of our leadership masterclass yesterday. I understand that timing or other commitments might have pulled you away.

Would you be interested in:
- A quick 10-minute call to discuss the key takeaways you missed?
- Access to the session recording?
- Information about our upcoming sessions?

I'd love to understand what would work best for you.

Best regards,
[Your Name]
Relationship Manager, Iron Lady"""
    
    elif category == 'Cold':
        # Low engagement
        template = f"""Subject: Following up on the leadership masterclass

Hi {name},

Thank you for attending our masterclass yesterday. I noticed you were there for {duration} minutes, and I wanted to check in.

Sometimes the content or timing might not align perfectly with immediate needs. I'd appreciate your honest feedback:
- Was there a specific section that didn't resonate?
- Would a different format (smaller group, 1-on-1) be more helpful?
- Are there specific topics you'd like us to cover?

Your feedback helps us improve. If you're open to a brief chat, I'm available this week.

Warm regards,
[Your Name]
Relationship Manager, Iron Lady"""
    
    elif category == 'Warm':
        # Moderate engagement
        template = f"""Subject: Great having you at the masterclass!

Hi {name},

It was wonderful having you at our leadership masterclass yesterday! I saw you stayed for {duration} minutes and hope you found valuable takeaways.

I'd love to understand:
- Which parts resonated most with you?
- Any questions that came up after the session?
- Whether you'd like to explore how our programs could support your leadership journey?

I'm happy to schedule a quick 15-minute call this week to discuss next steps or answer any questions.

Looking forward to connecting!

Best regards,
[Your Name]
Relationship Manager, Iron Lady"""
    
    else:  # Hot
        # High engagement
        template = f"""Subject: Thank you for your engagement yesterday!

Hi {name},

Thank you for being such an engaged participant in yesterday's masterclass! Your questions and involvement ({duration} minutes of active participation) really enriched the discussion.

Given your strong interest, I'd love to:
1. Schedule a personalized consultation to discuss your specific leadership goals
2. Share detailed information about our Leadership Essentials Program
3. Explore early registration benefits for our upcoming batch

When would be a good time for a 20-30 minute call? I have slots available:
- [Time Option 1]
- [Time Option 2]
- [Time Option 3]

Excited to continue this conversation!

Warm regards,
[Your Name]
Relationship Manager, Iron Lady"""
    
    return template

def generate_bulk_email_report(rm_follow_ups, output_file='email_templates.txt'):
    """Generate bulk email templates for all RM follow-ups"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("EMAIL TEMPLATES FOR RM FOLLOW-UPS\n")
        f.write("="*80 + "\n\n")
        
        for rm_data in rm_follow_ups:
            rm_name = rm_data['rm_name']
            leads = rm_data['leads']
            
            f.write(f"\n{'='*80}\n")
            f.write(f"RM: {rm_name}\n")
            f.write(f"Total Inactive Leads: {len(leads)}\n")
            f.write(f"{'='*80}\n\n")
            
            for idx, lead in enumerate(leads, 1):
                f.write(f"\n--- Lead #{idx}: {lead['name']} ({lead['email']}) ---\n")
                f.write(f"Category: {lead['category']} | Score: {lead['total_score']}\n")
                f.write(f"Duration: {lead['duration_mins']} minutes\n\n")
                
                template = generate_email_template(lead)
                f.write(template)
                f.write("\n\n" + "-"*80 + "\n")
    
    print(f"✅ Email templates exported to: {output_file}")

# Example usage
if __name__ == "__main__":
    # Sample lead data
    sample_lead = {
        'name': 'Dr. Priya Sharma',
        'email': 'priya.sharma@email.com',
        'duration_mins': 25,
        'category': 'Cold',
        'total_score': 35
    }
    
    print("Sample Email Template:")
    print("="*80)
    print(generate_email_template(sample_lead))
    print("="*80)