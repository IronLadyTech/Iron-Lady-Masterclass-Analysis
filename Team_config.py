# ============================================
# TEAM MEMBERS CONFIGURATION
# ============================================
# This file contains emails to exclude from analysis
# These are Iron Lady team members who join masterclasses
# but should not be counted as participants
#
# HOW TO USE:
# 1. Add domain patterns (like @iamironlady.com)
# 2. Add specific personal emails if team joins from personal accounts
# ============================================

# Domains to exclude (all emails ending with these will be excluded)
EXCLUDED_DOMAINS = [
    "@iamironlady.com",
    "@ironlady.com",
]

# Specific emails to exclude (for team members using personal emails)
# Add personal emails of team members here
EXCLUDED_EMAILS = [
    # Personal emails of Iron Lady team members
    "afreen786@gmail.com",           # Shaik Afreen
    "abhinayajanagama@gmail.com",    # Janagama Abhinaya
    "farhanaaz0416@gmail.com",       # Farha naaz
    "mghkhandelwal93@gmail.com",     # Megha Khandelwal
    "sharanchhabra65@gmail.com",     # Sharan Chhabra
]

# ============================================
# TEAM MEMBER REFERENCE (from your image)
# ============================================
# First Name    | Last Name      | Primary Email                  | Secondary Email
# --------------|----------------|--------------------------------|------------------
# Soumya        | Bidnal         | connect18@iamironlady.com      |
# Shriprabha    | Singh          | connect10@iamironlady.com      |
# Shivani       |                | connect3@iamironlady.com       |
# Sharan        | Chhabra        | connect14@iamironlady.com      |
# Shaik         | Afreen         | support@iamironlady.com        | prerna@iamironlady.com
# Sakshi        | Mishra         | connect4@iamironlady.com       |
# Rashmi        | Shetty         | connect7@iamironlady.com       |
# Priyanka      | Bhushan More   | connect1@iamironlady.com       |
# Pooja         | Singh          | connect15@iamironlady.com      |
# Nzanbeni      | Khuvung        | connect8@iamironlady.com       |
# Megha         | Khandelwal     | megha@iamironlady.com          |
# Kajal         | Shukla         | connect5@iamironlady.com       |
# Kaarti        | S              | connect17@iamironlady.com      |
# Janagama      | Abhinaya       | connect11@iamironlady.com      |
# IRON          | LADY           | admin@iamironlady.com          | rahul@iamironlady.com
# Ghazala       | Firdausi       | ghazala@iamironlady.com        |
# Farha         | naaz           | connect6@iamironlady.com       | nikhat@iamironlady.com
# Divya         | Lakshmi        | connect9@iamironlady.com       |
# Brunda        | B              | brunda@iamironlady.com         |
# Anam          | Ghanchi        | connect19@iamironlady.com      |
# Akansha       | Rawat          | connect20@iamironlady.com      |
# ============================================

def load_exclusion_config():
    """Load exclusion configuration"""
    return {
        'domains': EXCLUDED_DOMAINS,
        'emails': EXCLUDED_EMAILS
    }