"""
GTM Framework Agreements Dashboard - Database Module
Handles SQLite database operations, schema, and business logic
"""

import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class CustomerSegment(Enum):
    GOVERNMENT = "Government"
    SMART_CITY = "Smart City"
    ENTERPRISE = "Enterprise"
    SME = "SME"
    OTHER = "Other"

class AgreementType(Enum):
    FRAMEWORK = "Framework"
    MASTER_SERVICES = "Master Services"
    BLANKET_PO = "Blanket PO"
    OTHER = "Other"

class AgreementStatus(Enum):
    PIPELINE = "Pipeline"
    DRAFT = "Draft"
    LEGAL_REVIEW = "LegalReview"
    SIGNATURE_PENDING = "SignaturePending"
    SIGNED = "Signed"
    ACTIVE = "Active"
    EXPIRED = "Expired"
    TERMINATED = "Terminated"

class Currency(Enum):
    SAR = "SAR"
    USD = "USD"
    EUR = "EUR"

class RiskFlag(Enum):
    GREEN = "Green"
    AMBER = "Amber"
    RED = "Red"

class AgingBucket(Enum):
    LESS_30 = "<30d"
    DAYS_30_60 = "30-60d"
    DAYS_61_90 = "61-90d"
    MORE_90 = ">90d"

# Status transition rules
ALLOWED_STATUS_TRANSITIONS = {
    AgreementStatus.PIPELINE: [AgreementStatus.DRAFT, AgreementStatus.TERMINATED],
    AgreementStatus.DRAFT: [AgreementStatus.LEGAL_REVIEW, AgreementStatus.PIPELINE, AgreementStatus.TERMINATED],
    AgreementStatus.LEGAL_REVIEW: [AgreementStatus.SIGNATURE_PENDING, AgreementStatus.DRAFT, AgreementStatus.TERMINATED],
    AgreementStatus.SIGNATURE_PENDING: [AgreementStatus.SIGNED, AgreementStatus.LEGAL_REVIEW, AgreementStatus.TERMINATED],
    AgreementStatus.SIGNED: [AgreementStatus.ACTIVE, AgreementStatus.TERMINATED],
    AgreementStatus.ACTIVE: [AgreementStatus.EXPIRED, AgreementStatus.TERMINATED],
    AgreementStatus.EXPIRED: [],
    AgreementStatus.TERMINATED: [],
}

# FX Rates (base: SAR)
FX_RATES = {
    "SAR": 1.0,
    "USD": 3.75,
    "EUR": 4.05,
}

PRE_SIGNATURE_STATUSES = [
    AgreementStatus.PIPELINE,
    AgreementStatus.DRAFT,
    AgreementStatus.LEGAL_REVIEW,
    AgreementStatus.SIGNATURE_PENDING,
]

POST_SIGNATURE_STATUSES = [
    AgreementStatus.SIGNED,
    AgreementStatus.ACTIVE,
]

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE CONNECTION & SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

def get_connection(db_path: str = "gtm_dashboard.db") -> sqlite3.Connection:
    """Get database connection with row factory"""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database(db_path: str = "gtm_dashboard.db"):
    """Initialize database with schema"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Agreements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agreements (
            agreement_id TEXT PRIMARY KEY,
            agreement_name TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_segment TEXT NOT NULL,
            region TEXT,
            industry TEXT,
            agreement_type TEXT NOT NULL,
            start_date DATE,
            end_date DATE,
            agreement_value_ceiling REAL NOT NULL CHECK(agreement_value_ceiling > 0),
            currency TEXT NOT NULL DEFAULT 'SAR',
            status TEXT NOT NULL DEFAULT 'Pipeline',
            status_date DATE NOT NULL,
            account_manager TEXT NOT NULL,
            sales_owner TEXT,
            partnerships_vendors TEXT,
            probability_to_sign REAL CHECK(probability_to_sign >= 0 AND probability_to_sign <= 100),
            expected_signature_date DATE,
            signed_date DATE,
            renewal_terms TEXT,
            notes TEXT,
            attachments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # POs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pos (
            po_id TEXT PRIMARY KEY,
            agreement_id TEXT NOT NULL,
            po_number TEXT NOT NULL,
            po_date DATE NOT NULL,
            po_value REAL NOT NULL CHECK(po_value > 0),
            currency TEXT NOT NULL DEFAULT 'SAR',
            customer_name TEXT NOT NULL,
            account_manager TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agreement_id) REFERENCES agreements(agreement_id)
        )
    """)
    
    # Users table (optional)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'Viewer',
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Status history table for tracking transitions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agreement_id TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            changed_by TEXT,
            FOREIGN KEY (agreement_id) REFERENCES agreements(agreement_id)
        )
    """)
    
    # Sequence table for agreement ID generation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sequences (
            seq_name TEXT PRIMARY KEY,
            seq_value INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    # Initialize sequence if not exists
    cursor.execute("""
        INSERT OR IGNORE INTO sequences (seq_name, seq_value) VALUES ('agreement', 0)
    """)
    
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════════════════════
# ID GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_agreement_id(conn: sqlite3.Connection) -> str:
    """Generate unique agreement ID in format AGR-YYYY-0001"""
    cursor = conn.cursor()
    year = datetime.now().year
    
    cursor.execute("UPDATE sequences SET seq_value = seq_value + 1 WHERE seq_name = 'agreement'")
    cursor.execute("SELECT seq_value FROM sequences WHERE seq_name = 'agreement'")
    seq = cursor.fetchone()[0]
    
    return f"AGR-{year}-{seq:04d}"

def generate_po_id(conn: sqlite3.Connection, agreement_id: str) -> str:
    """Generate unique PO ID"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pos WHERE agreement_id = ?", (agreement_id,))
    count = cursor.fetchone()[0] + 1
    return f"PO-{agreement_id.replace('AGR-', '')}-{count:03d}"

# ═══════════════════════════════════════════════════════════════════════════════
# CURRENCY CONVERSION
# ═══════════════════════════════════════════════════════════════════════════════

def convert_to_sar(amount: float, currency: str) -> float:
    """Convert amount to SAR"""
    return amount * FX_RATES.get(currency, 1.0)

# ═══════════════════════════════════════════════════════════════════════════════
# CALCULATED FIELDS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_days_since_signature(signed_date: Optional[str]) -> Optional[int]:
    """Calculate days since signature"""
    if not signed_date:
        return None
    signed = datetime.strptime(signed_date, "%Y-%m-%d").date()
    return (date.today() - signed).days

def calculate_aging_bucket(days: Optional[int]) -> Optional[str]:
    """Determine aging bucket based on days since signature"""
    if days is None:
        return None
    if days < 30:
        return AgingBucket.LESS_30.value
    elif days <= 60:
        return AgingBucket.DAYS_30_60.value
    elif days <= 90:
        return AgingBucket.DAYS_61_90.value
    else:
        return AgingBucket.MORE_90.value

def calculate_risk_flag(status: str, days_since_signature: Optional[int], 
                        total_pos_value: float, utilization_percent: float) -> str:
    """Calculate risk flag based on business rules"""
    if status not in [AgreementStatus.SIGNED.value, AgreementStatus.ACTIVE.value]:
        return RiskFlag.GREEN.value
    
    if days_since_signature is None:
        return RiskFlag.GREEN.value
    
    # Red: Signed/Active AND >90 days AND no POs
    if days_since_signature > 90 and total_pos_value == 0:
        return RiskFlag.RED.value
    
    # Amber: 31-90 days AND no POs OR utilization < 10% after 60 days
    if (31 <= days_since_signature <= 90 and total_pos_value == 0) or \
       (days_since_signature > 60 and utilization_percent < 10):
        return RiskFlag.AMBER.value
    
    return RiskFlag.GREEN.value

def get_total_pos_value(conn: sqlite3.Connection, agreement_id: str) -> float:
    """Get total PO value for an agreement (converted to SAR)"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(po_value * 
            CASE currency 
                WHEN 'USD' THEN 3.75 
                WHEN 'EUR' THEN 4.05 
                ELSE 1.0 
            END), 0) as total
        FROM pos WHERE agreement_id = ?
    """, (agreement_id,))
    return cursor.fetchone()[0]

def calculate_utilization(total_pos_value: float, ceiling_value: float) -> float:
    """Calculate utilization percentage"""
    if ceiling_value <= 0:
        return 0.0
    return (total_pos_value / ceiling_value) * 100

# ═══════════════════════════════════════════════════════════════════════════════
# AGREEMENT CRUD OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_agreement(conn: sqlite3.Connection, data: Dict[str, Any]) -> str:
    """Create a new agreement"""
    cursor = conn.cursor()
    
    agreement_id = generate_agreement_id(conn)
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO agreements (
            agreement_id, agreement_name, customer_name, customer_segment,
            region, industry, agreement_type, start_date, end_date,
            agreement_value_ceiling, currency, status, status_date,
            account_manager, sales_owner, partnerships_vendors,
            probability_to_sign, expected_signature_date, signed_date,
            renewal_terms, notes, attachments, created_at, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        agreement_id,
        data.get('agreement_name'),
        data.get('customer_name'),
        data.get('customer_segment'),
        data.get('region'),
        data.get('industry'),
        data.get('agreement_type'),
        data.get('start_date'),
        data.get('end_date'),
        data.get('agreement_value_ceiling'),
        data.get('currency', 'SAR'),
        data.get('status', 'Pipeline'),
        data.get('status_date', date.today().isoformat()),
        data.get('account_manager'),
        data.get('sales_owner'),
        data.get('partnerships_vendors'),
        data.get('probability_to_sign'),
        data.get('expected_signature_date'),
        data.get('signed_date'),
        data.get('renewal_terms'),
        data.get('notes'),
        data.get('attachments'),
        now,
        now
    ))
    
    # Record status history
    cursor.execute("""
        INSERT INTO status_history (agreement_id, new_status, changed_at)
        VALUES (?, ?, ?)
    """, (agreement_id, data.get('status', 'Pipeline'), now))
    
    conn.commit()
    return agreement_id

def update_agreement(conn: sqlite3.Connection, agreement_id: str, data: Dict[str, Any]) -> bool:
    """Update an existing agreement"""
    cursor = conn.cursor()
    
    # Get current status for history tracking
    cursor.execute("SELECT status FROM agreements WHERE agreement_id = ?", (agreement_id,))
    row = cursor.fetchone()
    if not row:
        return False
    
    old_status = row['status']
    new_status = data.get('status', old_status)
    
    # Validate status transition if status is changing
    if old_status != new_status:
        old_status_enum = AgreementStatus(old_status)
        new_status_enum = AgreementStatus(new_status)
        
        if new_status_enum not in ALLOWED_STATUS_TRANSITIONS.get(old_status_enum, []):
            raise ValueError(f"Invalid status transition from {old_status} to {new_status}")
    
    # Build update query dynamically
    update_fields = []
    values = []
    
    for key, value in data.items():
        if key != 'agreement_id':
            update_fields.append(f"{key} = ?")
            values.append(value)
    
    update_fields.append("last_updated = ?")
    values.append(datetime.now().isoformat())
    values.append(agreement_id)
    
    query = f"UPDATE agreements SET {', '.join(update_fields)} WHERE agreement_id = ?"
    cursor.execute(query, values)
    
    # Record status change if applicable
    if old_status != new_status:
        cursor.execute("""
            INSERT INTO status_history (agreement_id, old_status, new_status, changed_at)
            VALUES (?, ?, ?, ?)
        """, (agreement_id, old_status, new_status, datetime.now().isoformat()))
    
    conn.commit()
    return True

def get_agreement(conn: sqlite3.Connection, agreement_id: str) -> Optional[Dict]:
    """Get a single agreement with calculated fields"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agreements WHERE agreement_id = ?", (agreement_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
    
    agreement = dict(row)
    
    # Add calculated fields
    total_pos = get_total_pos_value(conn, agreement_id)
    ceiling_sar = convert_to_sar(agreement['agreement_value_ceiling'], agreement['currency'])
    days_since = calculate_days_since_signature(agreement['signed_date'])
    utilization = calculate_utilization(total_pos, ceiling_sar)
    
    agreement['total_pos_value_to_date'] = total_pos
    agreement['is_monetizing'] = total_pos > 0
    agreement['utilization_percent'] = utilization
    agreement['days_since_signature'] = days_since
    agreement['aging_bucket'] = calculate_aging_bucket(days_since)
    agreement['risk_flag'] = calculate_risk_flag(
        agreement['status'], days_since, total_pos, utilization
    )
    
    return agreement

def get_all_agreements(conn: sqlite3.Connection, filters: Optional[Dict] = None) -> List[Dict]:
    """Get all agreements with optional filters and calculated fields"""
    cursor = conn.cursor()
    
    query = "SELECT * FROM agreements WHERE 1=1"
    params = []
    
    if filters:
        if filters.get('status'):
            query += " AND status = ?"
            params.append(filters['status'])
        if filters.get('account_manager'):
            query += " AND account_manager = ?"
            params.append(filters['account_manager'])
        if filters.get('customer_name'):
            query += " AND customer_name LIKE ?"
            params.append(f"%{filters['customer_name']}%")
        if filters.get('region'):
            query += " AND region = ?"
            params.append(filters['region'])
        if filters.get('industry'):
            query += " AND industry = ?"
            params.append(filters['industry'])
        if filters.get('customer_segment'):
            query += " AND customer_segment = ?"
            params.append(filters['customer_segment'])
    
    query += " ORDER BY last_updated DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    agreements = []
    for row in rows:
        agreement = dict(row)
        
        # Add calculated fields
        total_pos = get_total_pos_value(conn, agreement['agreement_id'])
        ceiling_sar = convert_to_sar(agreement['agreement_value_ceiling'], agreement['currency'])
        days_since = calculate_days_since_signature(agreement['signed_date'])
        utilization = calculate_utilization(total_pos, ceiling_sar)
        
        agreement['total_pos_value_to_date'] = total_pos
        agreement['is_monetizing'] = total_pos > 0
        agreement['utilization_percent'] = utilization
        agreement['days_since_signature'] = days_since
        agreement['aging_bucket'] = calculate_aging_bucket(days_since)
        agreement['risk_flag'] = calculate_risk_flag(
            agreement['status'], days_since, total_pos, utilization
        )
        
        agreements.append(agreement)
    
    return agreements

def delete_agreement(conn: sqlite3.Connection, agreement_id: str) -> bool:
    """Delete an agreement and associated POs"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pos WHERE agreement_id = ?", (agreement_id,))
    cursor.execute("DELETE FROM status_history WHERE agreement_id = ?", (agreement_id,))
    cursor.execute("DELETE FROM agreements WHERE agreement_id = ?", (agreement_id,))
    conn.commit()
    return cursor.rowcount > 0

# ═══════════════════════════════════════════════════════════════════════════════
# PO CRUD OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_po(conn: sqlite3.Connection, data: Dict[str, Any], override_ceiling: bool = False) -> str:
    """Create a new PO"""
    cursor = conn.cursor()
    
    agreement_id = data['agreement_id']
    
    # Get agreement info
    agreement = get_agreement(conn, agreement_id)
    if not agreement:
        raise ValueError(f"Agreement {agreement_id} not found")
    
    # Check ceiling
    new_po_value_sar = convert_to_sar(data['po_value'], data.get('currency', 'SAR'))
    current_total = agreement['total_pos_value_to_date']
    ceiling_sar = convert_to_sar(agreement['agreement_value_ceiling'], agreement['currency'])
    
    if (current_total + new_po_value_sar) > ceiling_sar and not override_ceiling:
        raise ValueError(
            f"Adding this PO would exceed the agreement ceiling. "
            f"Current: {current_total:,.2f} SAR, New PO: {new_po_value_sar:,.2f} SAR, "
            f"Ceiling: {ceiling_sar:,.2f} SAR"
        )
    
    po_id = generate_po_id(conn, agreement_id)
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO pos (
            po_id, agreement_id, po_number, po_date, po_value, currency,
            customer_name, account_manager, notes, created_at, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        po_id,
        agreement_id,
        data.get('po_number'),
        data.get('po_date'),
        data.get('po_value'),
        data.get('currency', 'SAR'),
        data.get('customer_name', agreement['customer_name']),
        data.get('account_manager', agreement['account_manager']),
        data.get('notes'),
        now,
        now
    ))
    
    conn.commit()
    return po_id

def get_pos_for_agreement(conn: sqlite3.Connection, agreement_id: str) -> List[Dict]:
    """Get all POs for an agreement"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM pos WHERE agreement_id = ? ORDER BY po_date DESC
    """, (agreement_id,))
    return [dict(row) for row in cursor.fetchall()]

def get_all_pos(conn: sqlite3.Connection) -> List[Dict]:
    """Get all POs"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pos ORDER BY po_date DESC")
    return [dict(row) for row in cursor.fetchall()]

def delete_po(conn: sqlite3.Connection, po_id: str) -> bool:
    """Delete a PO"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pos WHERE po_id = ?", (po_id,))
    conn.commit()
    return cursor.rowcount > 0

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS & KPIs
# ═══════════════════════════════════════════════════════════════════════════════

def get_pipeline_stats(conn: sqlite3.Connection) -> Dict:
    """Get pipeline overview statistics"""
    agreements = get_all_agreements(conn)
    
    pre_signature = [a for a in agreements if a['status'] in [s.value for s in PRE_SIGNATURE_STATUSES]]
    
    stats = {
        'total_count': len(pre_signature),
        'by_status': {},
        'total_potential_ceiling': 0,
        'avg_probability': 0,
        'weighted_value': 0,
    }
    
    probabilities = []
    
    for status in PRE_SIGNATURE_STATUSES:
        status_agreements = [a for a in pre_signature if a['status'] == status.value]
        stats['by_status'][status.value] = len(status_agreements)
        
        for a in status_agreements:
            ceiling_sar = convert_to_sar(a['agreement_value_ceiling'], a['currency'])
            stats['total_potential_ceiling'] += ceiling_sar
            
            prob = a.get('probability_to_sign') or 0
            probabilities.append(prob)
            stats['weighted_value'] += ceiling_sar * (prob / 100)
    
    stats['avg_probability'] = sum(probabilities) / len(probabilities) if probabilities else 0
    
    return stats

def get_monetization_stats(conn: sqlite3.Connection) -> Dict:
    """Get monetization statistics for signed agreements"""
    agreements = get_all_agreements(conn)
    
    signed = [a for a in agreements if a['status'] in [s.value for s in POST_SIGNATURE_STATUSES]]
    
    stats = {
        'total_signed_ceiling': 0,
        'total_monetized_value': 0,
        'overall_utilization': 0,
        'agreements_without_pos': 0,
        'agreements_count': len(signed),
        'by_risk': {'Green': 0, 'Amber': 0, 'Red': 0},
    }
    
    for a in signed:
        ceiling_sar = convert_to_sar(a['agreement_value_ceiling'], a['currency'])
        stats['total_signed_ceiling'] += ceiling_sar
        stats['total_monetized_value'] += a['total_pos_value_to_date']
        
        if not a['is_monetizing']:
            stats['agreements_without_pos'] += 1
        
        stats['by_risk'][a['risk_flag']] += 1
    
    if stats['total_signed_ceiling'] > 0:
        stats['overall_utilization'] = (stats['total_monetized_value'] / stats['total_signed_ceiling']) * 100
    
    return stats

def get_account_manager_stats(conn: sqlite3.Connection) -> List[Dict]:
    """Get performance statistics by account manager"""
    agreements = get_all_agreements(conn)
    
    am_stats = {}
    
    for a in agreements:
        am = a['account_manager']
        if am not in am_stats:
            am_stats[am] = {
                'account_manager': am,
                'total_agreements': 0,
                'signed_agreements': 0,
                'signed_value': 0,
                'monetized_value': 0,
                'utilization': 0,
                'avg_time_to_sign': [],
            }
        
        am_stats[am]['total_agreements'] += 1
        
        if a['status'] in [s.value for s in POST_SIGNATURE_STATUSES]:
            am_stats[am]['signed_agreements'] += 1
            ceiling_sar = convert_to_sar(a['agreement_value_ceiling'], a['currency'])
            am_stats[am]['signed_value'] += ceiling_sar
            am_stats[am]['monetized_value'] += a['total_pos_value_to_date']
    
    # Calculate utilization and format
    result = []
    for am, stats in am_stats.items():
        if stats['signed_value'] > 0:
            stats['utilization'] = (stats['monetized_value'] / stats['signed_value']) * 100
        result.append(stats)
    
    return sorted(result, key=lambda x: x['monetized_value'], reverse=True)

def get_aging_risk_matrix(conn: sqlite3.Connection) -> Dict:
    """Get aging vs risk heatmap data"""
    agreements = get_all_agreements(conn)
    signed = [a for a in agreements if a['status'] in [s.value for s in POST_SIGNATURE_STATUSES]]
    
    matrix = {}
    for bucket in AgingBucket:
        matrix[bucket.value] = {'Green': 0, 'Amber': 0, 'Red': 0}
    
    for a in signed:
        bucket = a.get('aging_bucket')
        risk = a.get('risk_flag', 'Green')
        if bucket and bucket in matrix:
            matrix[bucket][risk] += 1
    
    return matrix

def get_forecast_data(conn: sqlite3.Connection) -> Dict:
    """Get forecast data for pipeline and monetization"""
    agreements = get_all_agreements(conn)
    pos = get_all_pos(conn)
    
    # Pre-signature forecast
    pre_signature = [a for a in agreements if a['status'] in [s.value for s in PRE_SIGNATURE_STATUSES]]
    expected_value = sum(
        convert_to_sar(a['agreement_value_ceiling'], a['currency']) * (a.get('probability_to_sign') or 0) / 100
        for a in pre_signature
    )
    
    # Monthly PO trend
    monthly_pos = {}
    for po in pos:
        month = po['po_date'][:7] if po['po_date'] else None
        if month:
            if month not in monthly_pos:
                monthly_pos[month] = 0
            monthly_pos[month] += convert_to_sar(po['po_value'], po['currency'])
    
    return {
        'expected_pipeline_value': expected_value,
        'monthly_pos': monthly_pos,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# DATA IMPORT/EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_agreements_csv(conn: sqlite3.Connection) -> str:
    """Export agreements to CSV format"""
    import csv
    import io
    
    agreements = get_all_agreements(conn)
    
    if not agreements:
        return ""
    
    output = io.StringIO()
    fieldnames = [
        'agreement_id', 'agreement_name', 'customer_name', 'customer_segment',
        'region', 'industry', 'agreement_type', 'start_date', 'end_date',
        'agreement_value_ceiling', 'currency', 'status', 'status_date',
        'account_manager', 'sales_owner', 'partnerships_vendors',
        'probability_to_sign', 'expected_signature_date', 'signed_date',
        'total_pos_value_to_date', 'utilization_percent', 'risk_flag', 'notes'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for a in agreements:
        writer.writerow(a)
    
    return output.getvalue()

def export_pos_csv(conn: sqlite3.Connection) -> str:
    """Export POs to CSV format"""
    import csv
    import io
    
    pos = get_all_pos(conn)
    
    if not pos:
        return ""
    
    output = io.StringIO()
    fieldnames = [
        'po_id', 'agreement_id', 'po_number', 'po_date', 'po_value',
        'currency', 'customer_name', 'account_manager', 'notes'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for po in pos:
        writer.writerow(po)
    
    return output.getvalue()
