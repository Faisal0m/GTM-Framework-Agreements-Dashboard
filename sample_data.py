"""
GTM Framework Agreements Dashboard - Sample Data
Generates realistic sample data for testing and demonstration
"""

from datetime import date, timedelta
import random
from database import (
    init_database, get_connection, create_agreement, create_po,
    AgreementStatus, CustomerSegment, AgreementType, Currency
)

# ═══════════════════════════════════════════════════════════════════════════════
# SAMPLE DATA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

CUSTOMERS = [
    {"name": "Ministry of Interior", "segment": "Government", "industry": "Public Sector", "region": "Central"},
    {"name": "NEOM", "segment": "Smart City", "industry": "Megaprojects", "region": "Western"},
    {"name": "Saudi Aramco", "segment": "Enterprise", "industry": "Oil & Gas", "region": "Eastern"},
    {"name": "ROSHN", "segment": "Enterprise", "industry": "Real Estate", "region": "Central"},
    {"name": "Ministry of Health", "segment": "Government", "industry": "Healthcare", "region": "Central"},
    {"name": "Red Sea Global", "segment": "Smart City", "industry": "Tourism", "region": "Western"},
    {"name": "STC", "segment": "Enterprise", "industry": "Telecommunications", "region": "Central"},
    {"name": "SABIC", "segment": "Enterprise", "industry": "Chemicals", "region": "Eastern"},
    {"name": "Riyadh Municipality", "segment": "Government", "industry": "Public Sector", "region": "Central"},
    {"name": "King Faisal Specialist Hospital", "segment": "Enterprise", "industry": "Healthcare", "region": "Central"},
]

ACCOUNT_MANAGERS = [
    "Abdullah Al-Rashid",
    "Fatima Al-Dosari",
    "Mohammed Al-Shehri",
    "Sara Al-Mutairi",
    "Khaled Al-Zahrani",
]

SALES_OWNERS = [
    "Ahmed Al-Harbi",
    "Noura Al-Otaibi",
    "Faisal Al-Qahtani",
]

AGREEMENT_NAMES = [
    "AI Infrastructure Services Framework",
    "Digital Transformation Master Agreement",
    "Cloud Migration & Support Contract",
    "Data Analytics Platform Agreement",
    "Smart City Solutions Framework",
    "Enterprise AI Solutions Package",
    "Cybersecurity Services Framework",
    "IT Managed Services Agreement",
    "Innovation Lab Partnership",
    "Digital Workspace Solutions",
]

# ═══════════════════════════════════════════════════════════════════════════════
# SAMPLE DATA GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_sample_data(db_path: str = "gtm_dashboard.db"):
    """Generate sample agreements and POs"""
    
    init_database(db_path)
    conn = get_connection(db_path)
    
    today = date.today()
    
    # Sample Agreements (10 total with various statuses)
    sample_agreements = [
        # Pipeline agreements
        {
            "customer": CUSTOMERS[0],
            "name": "AI Infrastructure Services Framework",
            "type": AgreementType.FRAMEWORK.value,
            "status": AgreementStatus.PIPELINE.value,
            "value": 15000000,
            "probability": 40,
            "expected_sign": today + timedelta(days=90),
            "am": ACCOUNT_MANAGERS[0],
        },
        # Draft
        {
            "customer": CUSTOMERS[1],
            "name": "NEOM Smart City Digital Twin",
            "type": AgreementType.MASTER_SERVICES.value,
            "status": AgreementStatus.DRAFT.value,
            "value": 45000000,
            "probability": 55,
            "expected_sign": today + timedelta(days=60),
            "am": ACCOUNT_MANAGERS[1],
        },
        # Legal Review
        {
            "customer": CUSTOMERS[2],
            "name": "Aramco AI Analytics Platform",
            "type": AgreementType.FRAMEWORK.value,
            "status": AgreementStatus.LEGAL_REVIEW.value,
            "value": 28000000,
            "probability": 70,
            "expected_sign": today + timedelta(days=30),
            "am": ACCOUNT_MANAGERS[2],
        },
        # Signature Pending
        {
            "customer": CUSTOMERS[3],
            "name": "ROSHN Smart Living Solutions",
            "type": AgreementType.FRAMEWORK.value,
            "status": AgreementStatus.SIGNATURE_PENDING.value,
            "value": 12000000,
            "probability": 90,
            "expected_sign": today + timedelta(days=7),
            "am": ACCOUNT_MANAGERS[3],
        },
        # Signed - with POs (healthy)
        {
            "customer": CUSTOMERS[4],
            "name": "MOH Healthcare AI Framework",
            "type": AgreementType.FRAMEWORK.value,
            "status": AgreementStatus.SIGNED.value,
            "value": 35000000,
            "signed_date": today - timedelta(days=45),
            "am": ACCOUNT_MANAGERS[0],
            "pos": [
                {"value": 5000000, "date": today - timedelta(days=40)},
                {"value": 8000000, "date": today - timedelta(days=20)},
            ]
        },
        # Signed - no POs (amber risk - 45 days)
        {
            "customer": CUSTOMERS[5],
            "name": "Red Sea Tourism Analytics",
            "type": AgreementType.MASTER_SERVICES.value,
            "status": AgreementStatus.SIGNED.value,
            "value": 22000000,
            "signed_date": today - timedelta(days=55),
            "am": ACCOUNT_MANAGERS[1],
            "pos": []
        },
        # Active - with POs (good utilization)
        {
            "customer": CUSTOMERS[6],
            "name": "STC Network Intelligence Suite",
            "type": AgreementType.FRAMEWORK.value,
            "status": AgreementStatus.ACTIVE.value,
            "value": 50000000,
            "signed_date": today - timedelta(days=180),
            "am": ACCOUNT_MANAGERS[2],
            "pos": [
                {"value": 12000000, "date": today - timedelta(days=150)},
                {"value": 15000000, "date": today - timedelta(days=90)},
                {"value": 8000000, "date": today - timedelta(days=30)},
            ]
        },
        # Active - no POs (red risk - >90 days)
        {
            "customer": CUSTOMERS[7],
            "name": "SABIC Industrial AI Platform",
            "type": AgreementType.BLANKET_PO.value,
            "status": AgreementStatus.ACTIVE.value,
            "value": 18000000,
            "signed_date": today - timedelta(days=120),
            "am": ACCOUNT_MANAGERS[3],
            "pos": []
        },
        # Active - low utilization (amber)
        {
            "customer": CUSTOMERS[8],
            "name": "Riyadh Municipality Smart City",
            "type": AgreementType.FRAMEWORK.value,
            "status": AgreementStatus.ACTIVE.value,
            "value": 40000000,
            "signed_date": today - timedelta(days=100),
            "am": ACCOUNT_MANAGERS[4],
            "pos": [
                {"value": 2000000, "date": today - timedelta(days=80)},
            ]
        },
        # Signed - good monetization
        {
            "customer": CUSTOMERS[9],
            "name": "KFSH Clinical AI Solutions",
            "type": AgreementType.MASTER_SERVICES.value,
            "status": AgreementStatus.SIGNED.value,
            "value": 25000000,
            "signed_date": today - timedelta(days=75),
            "am": ACCOUNT_MANAGERS[0],
            "pos": [
                {"value": 7000000, "date": today - timedelta(days=60)},
                {"value": 5000000, "date": today - timedelta(days=30)},
                {"value": 4000000, "date": today - timedelta(days=10)},
            ]
        },
    ]
    
    created_agreements = []
    
    for i, agr in enumerate(sample_agreements):
        customer = agr["customer"]
        start_date = today - timedelta(days=random.randint(30, 180))
        end_date = start_date + timedelta(days=365 * 2)
        
        agreement_data = {
            "agreement_name": agr["name"],
            "customer_name": customer["name"],
            "customer_segment": customer["segment"],
            "region": customer["region"],
            "industry": customer["industry"],
            "agreement_type": agr["type"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "agreement_value_ceiling": agr["value"],
            "currency": "SAR",
            "status": agr["status"],
            "status_date": today.isoformat(),
            "account_manager": agr["am"],
            "sales_owner": random.choice(SALES_OWNERS),
            "probability_to_sign": agr.get("probability"),
            "expected_signature_date": agr.get("expected_sign", "").isoformat() if agr.get("expected_sign") else None,
            "signed_date": agr.get("signed_date", "").isoformat() if agr.get("signed_date") else None,
            "notes": f"Sample agreement #{i+1} for testing purposes",
        }
        
        agreement_id = create_agreement(conn, agreement_data)
        created_agreements.append(agreement_id)
        print(f"Created agreement: {agreement_id} - {agr['name']}")
        
        # Create POs if specified
        for j, po in enumerate(agr.get("pos", [])):
            po_data = {
                "agreement_id": agreement_id,
                "po_number": f"PO-{customer['name'][:3].upper()}-{today.year}-{j+1:03d}",
                "po_date": po["date"].isoformat(),
                "po_value": po["value"],
                "currency": "SAR",
                "customer_name": customer["name"],
                "account_manager": agr["am"],
                "notes": f"Purchase order for {agr['name']}",
            }
            
            try:
                po_id = create_po(conn, po_data)
                print(f"  Created PO: {po_id} - {po['value']:,.0f} SAR")
            except Exception as e:
                print(f"  Error creating PO: {e}")
    
    conn.close()
    print(f"\n✓ Created {len(created_agreements)} agreements with associated POs")
    return created_agreements


def clear_all_data(db_path: str = "gtm_dashboard.db"):
    """Clear all data from the database"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM pos")
    cursor.execute("DELETE FROM status_history")
    cursor.execute("DELETE FROM agreements")
    cursor.execute("UPDATE sequences SET seq_value = 0 WHERE seq_name = 'agreement'")
    
    conn.commit()
    conn.close()
    print("✓ All data cleared")


if __name__ == "__main__":
    print("Generating sample data...")
    generate_sample_data()
