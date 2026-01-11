# GTM Framework Agreements Dashboard

A comprehensive Streamlit-based dashboard for tracking framework agreements through their lifecycle, from pipeline to monetization via Purchase Orders (POs).

![Dashboard Overview](assets/dashboard-preview.png)

## 🎯 Features

### Pipeline Management
- Track agreements through all lifecycle stages: Pipeline → Draft → Legal Review → Signature Pending → Signed → Active → Expired/Terminated
- Weighted pipeline value calculations based on probability to sign
- Funnel visualization of pipeline progression

### Monetization Tracking
- Link Purchase Orders (POs) to signed agreements
- Automatic utilization percentage calculation
- Ceiling value tracking with override capability
- Multi-currency support (SAR, USD, EUR) with automatic conversion

### Risk & Aging Analysis
- **Red Risk**: Signed/Active agreements >90 days without POs
- **Amber Risk**: 31-90 days without POs or <10% utilization after 60 days
- **Green Risk**: Healthy agreements
- Aging bucket classification (<30d, 30-60d, 61-90d, >90d)

### Account Manager Performance
- Leaderboard view by monetization
- Individual performance metrics
- Portfolio breakdown by AM

### Forecasting
- Weighted pipeline forecast
- Monthly PO trend analysis
- Probability distribution visualization

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# Clone or extract the dashboard
cd gtm-dashboard

# Install dependencies
pip install -r requirements.txt

# Initialize database and generate sample data
python sample_data.py

# Run the dashboard
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
gtm-dashboard/
├── app.py                 # Main Streamlit application
├── database.py            # Database models, CRUD operations, calculations
├── sample_data.py         # Sample data generator
├── requirements.txt       # Python dependencies
├── gtm_dashboard.db       # SQLite database (auto-created)
├── templates/
│   ├── agreements_template.csv
│   └── pos_template.csv
├── tests/
│   └── test_calculations.py
└── README.md
```

## 📊 Data Model

### Agreements Table
| Field | Type | Description |
|-------|------|-------------|
| agreement_id | TEXT | Unique ID (AGR-YYYY-NNNN) |
| agreement_name | TEXT | Name of the agreement |
| customer_name | TEXT | Customer organization |
| customer_segment | ENUM | Government, Smart City, Enterprise, SME, Other |
| region | TEXT | Central, Western, Eastern, etc. |
| industry | TEXT | Industry vertical |
| agreement_type | ENUM | Framework, Master Services, Blanket PO, Other |
| start_date | DATE | Agreement start date |
| end_date | DATE | Agreement end date |
| agreement_value_ceiling | REAL | Maximum agreement value |
| currency | ENUM | SAR, USD, EUR |
| status | ENUM | Pipeline through Terminated |
| account_manager | TEXT | Responsible AM |
| probability_to_sign | REAL | 0-100% (pre-signature only) |
| signed_date | DATE | Date of signature |

### Purchase Orders Table
| Field | Type | Description |
|-------|------|-------------|
| po_id | TEXT | Unique PO ID |
| agreement_id | TEXT | FK to agreements |
| po_number | TEXT | Customer PO number |
| po_date | DATE | PO date |
| po_value | REAL | PO amount |
| currency | ENUM | SAR, USD, EUR |

### Calculated Fields (Runtime)
- `total_pos_value_to_date`: Sum of all POs (converted to SAR)
- `is_monetizing`: TRUE if any POs exist
- `utilization_percent`: POs value / ceiling value × 100
- `days_since_signature`: Days since signed_date
- `aging_bucket`: <30d, 30-60d, 61-90d, >90d
- `risk_flag`: Green, Amber, Red

## 🔧 Business Rules

### Status Transitions
```
Pipeline → Draft → LegalReview → SignaturePending → Signed → Active → Expired
                                                                    ↓
                                                              Terminated
```
Any status can transition to Terminated (Admin only for Expired/Terminated).

### Risk Flag Logic
```python
if status in (Signed, Active) and days_since_signature > 90 and total_pos = 0:
    risk = RED
elif (days_since_signature 31-90 and total_pos = 0) or (days > 60 and utilization < 10%):
    risk = AMBER
else:
    risk = GREEN
```

### Ceiling Enforcement
- PO creation is blocked if it would exceed the agreement ceiling
- Admin override available for exceptional cases
- Multi-currency values converted to SAR for comparison

## 📈 Dashboard Views

### 1. Overview
- Key metrics: Total agreements, pipeline value, signed value, monetization
- Status distribution pie chart
- Risk distribution bar chart
- Recent agreements table

### 2. Pipeline
- Pre-signature KPIs
- Funnel visualization
- Pipeline table with probability and expected dates

### 3. Monetization
- Signed agreements KPIs
- Utilization by agreement chart
- Utilization by AM chart
- Detailed signed agreements table

### 4. Account Managers
- Performance leaderboard
- Agreements by AM chart
- Monetization distribution

### 5. Aging & Risk
- Risk summary cards
- Aging vs Risk heatmap
- Risk alerts with recommended actions

### 6. Forecast
- Pipeline probability distribution
- Monthly PO trend with trendline
- Expected vs actual analysis

### 7. Agreements
- Full CRUD operations
- Create/Edit forms with validation
- Status transition controls

### 8. Purchase Orders
- PO creation linked to signed agreements
- Ceiling check with remaining capacity display
- PO listing and management

### 9. Import/Export
- CSV export for agreements and POs
- CSV import with validation
- Sample data generation

## 🧪 Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_calculations.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Coverage
- Calculation functions (utilization, aging, risk)
- Currency conversion
- Status transition validation
- CRUD operations
- Ceiling enforcement

## 💱 Currency Conversion

Fixed exchange rates (configurable in database.py):
- SAR: 1.0 (base)
- USD: 3.75
- EUR: 4.05

All calculations use SAR as the base currency.

## 🔄 Import Data

### Agreements CSV Format
```csv
agreement_name,customer_name,customer_segment,...
"AI Services Framework","Ministry of Interior","Government",...
```

### POs CSV Format
```csv
agreement_id,po_number,po_date,po_value,currency,customer_name
AGR-2025-0001,PO-001,2025-01-15,2500000,SAR,Ministry of Interior
```

## 🛠 Configuration

### Database
- Default: `gtm_dashboard.db` (SQLite)
- Change in `app.py`: `DB_PATH = "your_database.db"`

### Exchange Rates
Update in `database.py`:
```python
FX_RATES = {
    "SAR": 1.0,
    "USD": 3.75,  # Update as needed
    "EUR": 4.05,
}
```

## 📋 Assumptions & Limitations

1. **Single user**: No authentication/authorization (add for production)
2. **Fixed FX rates**: No real-time currency conversion
3. **Local SQLite**: For production, consider PostgreSQL
4. **No email alerts**: Implement via Streamlit Cloud + SendGrid for notifications

## 🚧 Future Enhancements

- [ ] Multi-user authentication with role-based access
- [ ] CRM integration (Salesforce, HubSpot)
- [ ] Automated email alerts for risk thresholds
- [ ] API endpoints for external integrations
- [ ] Advanced forecasting (ML-based predictions)
- [ ] Attachment storage (AWS S3 integration)
- [ ] Audit trail for all changes
- [ ] Custom report builder

## 📞 Support

For issues or feature requests, contact the GTM Operations team.

---

**Built for HUMAIN GTM Team** | Version 1.0.0
