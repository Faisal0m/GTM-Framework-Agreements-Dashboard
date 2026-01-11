"""
GTM Framework Agreements Dashboard
Main Streamlit Application
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
import os

from database import (
    init_database, get_connection, 
    create_agreement, update_agreement, get_agreement, get_all_agreements, delete_agreement,
    create_po, get_pos_for_agreement, get_all_pos, delete_po,
    get_pipeline_stats, get_monetization_stats, get_account_manager_stats,
    get_aging_risk_matrix, get_forecast_data,
    export_agreements_csv, export_pos_csv,
    AgreementStatus, CustomerSegment, AgreementType, Currency, RiskFlag,
    PRE_SIGNATURE_STATUSES, POST_SIGNATURE_STATUSES, ALLOWED_STATUS_TRANSITIONS,
    convert_to_sar
)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLING
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="GTM Framework Agreements Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    div[data-testid="metric-container"] label {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }
    
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #e2e8f0 !important;
        font-weight: 600;
    }
    
    /* Risk badge colors */
    .risk-green { 
        background-color: #10b981; 
        color: white; 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-size: 0.8rem;
        font-weight: 600;
    }
    .risk-amber { 
        background-color: #f59e0b; 
        color: white; 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-size: 0.8rem;
        font-weight: 600;
    }
    .risk-red { 
        background-color: #ef4444; 
        color: white; 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    /* Status badges */
    .status-pipeline { background-color: #6366f1; }
    .status-draft { background-color: #8b5cf6; }
    .status-legal { background-color: #ec4899; }
    .status-pending { background-color: #f97316; }
    .status-signed { background-color: #10b981; }
    .status-active { background-color: #06b6d4; }
    .status-expired { background-color: #6b7280; }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #3b82f6;
    }
    
    /* Cards */
    .info-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #334155;
    }
    
    /* Tables */
    .dataframe {
        font-size: 0.85rem !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    section[data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
    }
    
    /* Form styling */
    .stForm {
        background: #1e293b;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #334155;
    }
    
    /* Button styling */
    .stButton button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 8px 8px 0 0;
        color: #94a3b8;
        border: 1px solid #334155;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    /* Alert boxes */
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_PATH = "gtm_dashboard.db"

@st.cache_resource
def init_db():
    init_database(DB_PATH)
    return True

init_db()

def get_db():
    return get_connection(DB_PATH)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def format_currency(value, currency="SAR"):
    """Format currency value"""
    if value is None:
        return "-"
    return f"{value:,.0f} {currency}"

def format_percentage(value):
    """Format percentage value"""
    if value is None:
        return "-"
    return f"{value:.1f}%"

def get_risk_badge(risk):
    """Get HTML badge for risk flag"""
    colors = {
        "Green": "risk-green",
        "Amber": "risk-amber", 
        "Red": "risk-red"
    }
    return f'<span class="{colors.get(risk, "risk-green")}">{risk}</span>'

def get_status_color(status):
    """Get color for status"""
    colors = {
        "Pipeline": "#6366f1",
        "Draft": "#8b5cf6",
        "LegalReview": "#ec4899",
        "SignaturePending": "#f97316",
        "Signed": "#10b981",
        "Active": "#06b6d4",
        "Expired": "#6b7280",
        "Terminated": "#ef4444",
    }
    return colors.get(status, "#6b7280")

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem;">
        <h1 style="color: #3b82f6; font-size: 1.5rem; margin: 0;">📊 GTM Dashboard</h1>
        <p style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.5rem;">Framework Agreements Tracker</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Overview",
        "📈 Pipeline",
        "💰 Monetization",
        "👤 Account Managers",
        "⚠️ Aging & Risk",
        "📊 Forecast",
        "📝 Agreements",
        "🧾 Purchase Orders",
        "📤 Import/Export"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

# Global Filters
st.sidebar.markdown("### 🔍 Filters")

conn = get_db()
all_agreements = get_all_agreements(conn)

# Get unique values for filters
all_statuses = list(set(a['status'] for a in all_agreements)) if all_agreements else []
all_ams = list(set(a['account_manager'] for a in all_agreements if a['account_manager'])) if all_agreements else []
all_regions = list(set(a['region'] for a in all_agreements if a['region'])) if all_agreements else []
all_segments = list(set(a['customer_segment'] for a in all_agreements if a['customer_segment'])) if all_agreements else []

filter_status = st.sidebar.multiselect("Status", all_statuses)
filter_am = st.sidebar.multiselect("Account Manager", all_ams)
filter_region = st.sidebar.multiselect("Region", all_regions)
filter_segment = st.sidebar.multiselect("Customer Segment", all_segments)

# Apply filters
def apply_filters(agreements):
    filtered = agreements
    if filter_status:
        filtered = [a for a in filtered if a['status'] in filter_status]
    if filter_am:
        filtered = [a for a in filtered if a['account_manager'] in filter_am]
    if filter_region:
        filtered = [a for a in filtered if a['region'] in filter_region]
    if filter_segment:
        filtered = [a for a in filtered if a['customer_segment'] in filter_segment]
    return filtered

filtered_agreements = apply_filters(all_agreements)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

if page == "🏠 Overview":
    st.markdown("## 🏠 Dashboard Overview")
    st.markdown("Real-time visibility into your framework agreements pipeline and monetization performance.")
    
    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    pipeline_stats = get_pipeline_stats(conn)
    monetization_stats = get_monetization_stats(conn)
    
    with col1:
        st.metric(
            "Total Agreements",
            len(all_agreements),
            help="Total number of agreements in the system"
        )
    
    with col2:
        st.metric(
            "Pipeline Value",
            format_currency(pipeline_stats['total_potential_ceiling']),
            help="Total ceiling value of pre-signature agreements"
        )
    
    with col3:
        st.metric(
            "Signed Value",
            format_currency(monetization_stats['total_signed_ceiling']),
            help="Total ceiling value of signed/active agreements"
        )
    
    with col4:
        st.metric(
            "Monetized",
            format_currency(monetization_stats['total_monetized_value']),
            help="Total value of POs against signed agreements"
        )
    
    with col5:
        st.metric(
            "Utilization",
            format_percentage(monetization_stats['overall_utilization']),
            help="Overall monetization vs ceiling"
        )
    
    st.markdown("---")
    
    # Two column layout for charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Agreements by Status")
        
        status_counts = {}
        for a in all_agreements:
            status = a['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            fig = go.Figure(data=[go.Pie(
                labels=list(status_counts.keys()),
                values=list(status_counts.values()),
                hole=0.4,
                marker_colors=[get_status_color(s) for s in status_counts.keys()],
                textinfo='label+value',
                textposition='outside'
            )])
            fig.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                height=400,
                margin=dict(t=20, b=80),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No agreements to display")
    
    with col2:
        st.markdown("### 🎯 Risk Distribution")
        
        risk_counts = monetization_stats['by_risk']
        
        fig = go.Figure(data=[go.Bar(
            x=list(risk_counts.keys()),
            y=list(risk_counts.values()),
            marker_color=['#10b981', '#f59e0b', '#ef4444'],
            text=list(risk_counts.values()),
            textposition='auto'
        )])
        fig.update_layout(
            xaxis_title="Risk Level",
            yaxis_title="Count",
            height=400,
            margin=dict(t=20, b=40),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0'),
            xaxis=dict(gridcolor='#334155'),
            yaxis=dict(gridcolor='#334155')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent Activity Table
    st.markdown("### 📋 Recent Agreements")
    
    if filtered_agreements:
        recent_df = pd.DataFrame(filtered_agreements[:10])
        display_cols = ['agreement_id', 'agreement_name', 'customer_name', 'status', 
                       'agreement_value_ceiling', 'currency', 'utilization_percent', 'risk_flag']
        
        if all(col in recent_df.columns for col in display_cols):
            display_df = recent_df[display_cols].copy()
            display_df['agreement_value_ceiling'] = display_df.apply(
                lambda x: format_currency(x['agreement_value_ceiling'], x['currency']), axis=1
            )
            display_df['utilization_percent'] = display_df['utilization_percent'].apply(format_percentage)
            display_df.columns = ['ID', 'Agreement', 'Customer', 'Status', 'Ceiling', 'Currency', 'Utilization', 'Risk']
            st.dataframe(display_df.drop(columns=['Currency']), use_container_width=True, hide_index=True)
    else:
        st.info("No agreements found. Add some agreements to get started!")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📈 Pipeline":
    st.markdown("## 📈 Pipeline Overview")
    st.markdown("Track pre-signature agreements through the sales cycle.")
    
    pipeline_stats = get_pipeline_stats(conn)
    
    # Pipeline KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Pipeline", pipeline_stats['total_count'])
    with col2:
        st.metric("Potential Value", format_currency(pipeline_stats['total_potential_ceiling']))
    with col3:
        st.metric("Avg Probability", format_percentage(pipeline_stats['avg_probability']))
    with col4:
        st.metric("Weighted Value", format_currency(pipeline_stats['weighted_value']))
    
    st.markdown("---")
    
    # Funnel Chart
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🔄 Pipeline Funnel")
        
        funnel_data = []
        for status in PRE_SIGNATURE_STATUSES:
            count = pipeline_stats['by_status'].get(status.value, 0)
            funnel_data.append({"Stage": status.value, "Count": count})
        
        if any(d['Count'] > 0 for d in funnel_data):
            fig = go.Figure(go.Funnel(
                y=[d['Stage'] for d in funnel_data],
                x=[d['Count'] for d in funnel_data],
                textinfo="value+percent initial",
                marker_color=['#6366f1', '#8b5cf6', '#ec4899', '#f97316']
            ))
            fig.update_layout(
                height=350,
                margin=dict(t=20, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pipeline agreements to display")
    
    with col2:
        st.markdown("### 📊 By Status")
        for status in PRE_SIGNATURE_STATUSES:
            count = pipeline_stats['by_status'].get(status.value, 0)
            st.metric(status.value, count)
    
    # Pipeline Table
    st.markdown("### 📋 Pipeline Agreements")
    
    pipeline_agreements = [a for a in filtered_agreements 
                         if a['status'] in [s.value for s in PRE_SIGNATURE_STATUSES]]
    
    if pipeline_agreements:
        df = pd.DataFrame(pipeline_agreements)
        display_cols = ['agreement_id', 'agreement_name', 'customer_name', 'status',
                       'agreement_value_ceiling', 'probability_to_sign', 'expected_signature_date', 'account_manager']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df['agreement_value_ceiling'] = display_df['agreement_value_ceiling'].apply(
                lambda x: format_currency(x) if x else "-"
            )
            display_df['probability_to_sign'] = display_df['probability_to_sign'].apply(
                lambda x: format_percentage(x) if x else "-"
            )
            display_df.columns = ['ID', 'Agreement', 'Customer', 'Status', 'Ceiling', 'Probability', 'Expected Sign', 'AM']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No pipeline agreements found")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MONETIZATION
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "💰 Monetization":
    st.markdown("## 💰 Signed & Monetization")
    st.markdown("Track monetization performance of signed and active agreements.")
    
    monetization_stats = get_monetization_stats(conn)
    
    # Monetization KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Signed Ceiling", format_currency(monetization_stats['total_signed_ceiling']))
    with col2:
        st.metric("Monetized Value", format_currency(monetization_stats['total_monetized_value']))
    with col3:
        st.metric("Utilization", format_percentage(monetization_stats['overall_utilization']))
    with col4:
        st.metric("Without POs", monetization_stats['agreements_without_pos'])
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    signed_agreements = [a for a in filtered_agreements 
                        if a['status'] in [s.value for s in POST_SIGNATURE_STATUSES]]
    
    with col1:
        st.markdown("### 📊 Utilization by Agreement")
        
        if signed_agreements:
            util_data = [{
                'Agreement': a['agreement_name'][:30] + '...' if len(a['agreement_name']) > 30 else a['agreement_name'],
                'Utilization': a['utilization_percent'],
                'Risk': a['risk_flag']
            } for a in signed_agreements]
            
            df = pd.DataFrame(util_data)
            
            fig = px.bar(
                df, x='Agreement', y='Utilization',
                color='Risk',
                color_discrete_map={'Green': '#10b981', 'Amber': '#f59e0b', 'Red': '#ef4444'}
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                height=400,
                margin=dict(t=20, b=100),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                xaxis=dict(gridcolor='#334155'),
                yaxis=dict(gridcolor='#334155', title='Utilization %')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No signed agreements to display")
    
    with col2:
        st.markdown("### 👤 Utilization by Account Manager")
        
        am_stats = get_account_manager_stats(conn)
        
        if am_stats:
            am_data = [{
                'AM': stat['account_manager'],
                'Signed Value': stat['signed_value'],
                'Monetized': stat['monetized_value']
            } for stat in am_stats if stat['signed_value'] > 0]
            
            if am_data:
                df = pd.DataFrame(am_data)
                
                fig = go.Figure(data=[
                    go.Bar(name='Signed Value', x=df['AM'], y=df['Signed Value'], marker_color='#3b82f6'),
                    go.Bar(name='Monetized', x=df['AM'], y=df['Monetized'], marker_color='#10b981')
                ])
                fig.update_layout(
                    barmode='group',
                    xaxis_tickangle=-45,
                    height=400,
                    margin=dict(t=20, b=100),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    xaxis=dict(gridcolor='#334155'),
                    yaxis=dict(gridcolor='#334155', title='Value (SAR)')
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
        else:
            st.info("No data available")
    
    # Signed Agreements Table
    st.markdown("### 📋 Signed Agreements Detail")
    
    if signed_agreements:
        df = pd.DataFrame(signed_agreements)
        display_cols = ['agreement_id', 'agreement_name', 'customer_name', 'status',
                       'agreement_value_ceiling', 'total_pos_value_to_date', 'utilization_percent',
                       'days_since_signature', 'risk_flag']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df['agreement_value_ceiling'] = display_df['agreement_value_ceiling'].apply(
                lambda x: format_currency(x) if x else "-"
            )
            display_df['total_pos_value_to_date'] = display_df['total_pos_value_to_date'].apply(
                lambda x: format_currency(x) if x else "-"
            )
            display_df['utilization_percent'] = display_df['utilization_percent'].apply(format_percentage)
            display_df.columns = ['ID', 'Agreement', 'Customer', 'Status', 'Ceiling', 'POs Value', 'Utilization', 'Days Since Sign', 'Risk']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No signed agreements found")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ACCOUNT MANAGERS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "👤 Account Managers":
    st.markdown("## 👤 Account Manager Performance")
    st.markdown("Track individual performance metrics by account manager.")
    
    am_stats = get_account_manager_stats(conn)
    
    if am_stats:
        # Leaderboard
        st.markdown("### 🏆 Leaderboard")
        
        df = pd.DataFrame(am_stats)
        df['signed_value'] = df['signed_value'].apply(format_currency)
        df['monetized_value'] = df['monetized_value'].apply(format_currency)
        df['utilization'] = df['utilization'].apply(format_percentage)
        
        df.columns = ['Account Manager', 'Total Agreements', 'Signed', 'Signed Value', 
                     'Monetized Value', 'Utilization', 'Avg Time to Sign']
        
        st.dataframe(df.drop(columns=['Avg Time to Sign']), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Agreements by AM")
            
            am_data = get_account_manager_stats(conn)
            fig = px.bar(
                x=[a['account_manager'] for a in am_data],
                y=[a['total_agreements'] for a in am_data],
                color=[a['signed_agreements'] for a in am_data],
                labels={'x': 'Account Manager', 'y': 'Total Agreements', 'color': 'Signed'}
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                height=350,
                margin=dict(t=20, b=100),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 💰 Monetization by AM")
            
            fig = go.Figure(data=[go.Pie(
                labels=[a['account_manager'] for a in am_data if a['monetized_value'] > 0],
                values=[a['monetized_value'] for a in am_data if a['monetized_value'] > 0],
                hole=0.4,
                textinfo='label+percent'
            )])
            fig.update_layout(
                height=350,
                margin=dict(t=20, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No account manager data available")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: AGING & RISK
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "⚠️ Aging & Risk":
    st.markdown("## ⚠️ Aging & Risk Analysis")
    st.markdown("Identify at-risk agreements requiring attention.")
    
    # Risk Summary
    monetization_stats = get_monetization_stats(conn)
    risk_counts = monetization_stats['by_risk']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #065f46 0%, #047857 100%); 
                        padding: 1.5rem; border-radius: 12px; text-align: center;">
                <h3 style="color: #10b981; margin: 0;">🟢 Green</h3>
                <p style="font-size: 2rem; font-weight: bold; color: white; margin: 0.5rem 0;">{risk_counts['Green']}</p>
                <p style="color: #a7f3d0; margin: 0;">Healthy agreements</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #92400e 0%, #b45309 100%); 
                        padding: 1.5rem; border-radius: 12px; text-align: center;">
                <h3 style="color: #fbbf24; margin: 0;">🟡 Amber</h3>
                <p style="font-size: 2rem; font-weight: bold; color: white; margin: 0.5rem 0;">{risk_counts['Amber']}</p>
                <p style="color: #fde68a; margin: 0;">Needs attention</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%); 
                        padding: 1.5rem; border-radius: 12px; text-align: center;">
                <h3 style="color: #fca5a5; margin: 0;">🔴 Red</h3>
                <p style="font-size: 2rem; font-weight: bold; color: white; margin: 0.5rem 0;">{risk_counts['Red']}</p>
                <p style="color: #fecaca; margin: 0;">Critical - Act now</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Aging vs Risk Heatmap
    st.markdown("### 🗓️ Aging vs Risk Matrix")
    
    matrix = get_aging_risk_matrix(conn)
    
    # Create heatmap data
    buckets = ['<30d', '30-60d', '61-90d', '>90d']
    risks = ['Green', 'Amber', 'Red']
    
    z_data = [[matrix.get(bucket, {}).get(risk, 0) for risk in risks] for bucket in buckets]
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=risks,
        y=buckets,
        colorscale=[[0, '#1e293b'], [0.5, '#f59e0b'], [1, '#ef4444']],
        text=z_data,
        texttemplate='%{text}',
        textfont={"size": 16},
        hoverongaps=False
    ))
    fig.update_layout(
        xaxis_title="Risk Level",
        yaxis_title="Days Since Signature",
        height=350,
        margin=dict(t=20, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0')
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Risk Alerts
    st.markdown("### 🚨 Risk Alerts")
    
    signed_agreements = [a for a in filtered_agreements 
                        if a['status'] in [s.value for s in POST_SIGNATURE_STATUSES]]
    
    red_risks = [a for a in signed_agreements if a['risk_flag'] == 'Red']
    amber_risks = [a for a in signed_agreements if a['risk_flag'] == 'Amber']
    
    if red_risks:
        st.markdown("#### 🔴 Critical (Red)")
        for a in red_risks:
            with st.expander(f"⚠️ {a['agreement_name']} - {a['customer_name']}"):
                st.markdown(f"""
                    **Agreement ID:** {a['agreement_id']}  
                    **Days Since Signature:** {a['days_since_signature']}  
                    **Ceiling:** {format_currency(a['agreement_value_ceiling'], a['currency'])}  
                    **POs Value:** {format_currency(a['total_pos_value_to_date'])}  
                    **Account Manager:** {a['account_manager']}
                    
                    **🎯 Recommended Action:** Schedule urgent customer meeting to develop monetization plan.
                """)
    
    if amber_risks:
        st.markdown("#### 🟡 Warning (Amber)")
        for a in amber_risks:
            with st.expander(f"⚡ {a['agreement_name']} - {a['customer_name']}"):
                st.markdown(f"""
                    **Agreement ID:** {a['agreement_id']}  
                    **Days Since Signature:** {a['days_since_signature']}  
                    **Utilization:** {format_percentage(a['utilization_percent'])}  
                    **Account Manager:** {a['account_manager']}
                    
                    **🎯 Recommended Action:** Follow up with customer on project timeline and potential orders.
                """)
    
    if not red_risks and not amber_risks:
        st.success("✅ No at-risk agreements! All signed agreements are performing well.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: FORECAST
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📊 Forecast":
    st.markdown("## 📊 Forecast & Projections")
    st.markdown("Pipeline forecast and monetization trends.")
    
    forecast_data = get_forecast_data(conn)
    pipeline_stats = get_pipeline_stats(conn)
    monetization_stats = get_monetization_stats(conn)
    
    # Forecast KPIs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Expected Pipeline Value", 
                 format_currency(forecast_data['expected_pipeline_value']),
                 help="Weighted pipeline value (ceiling × probability)")
    
    with col2:
        st.metric("Pipeline Total", 
                 format_currency(pipeline_stats['total_potential_ceiling']))
    
    with col3:
        st.metric("Current Monetized",
                 format_currency(monetization_stats['total_monetized_value']))
    
    st.markdown("---")
    
    # Pipeline Probability Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Pipeline by Probability")
        
        pipeline_agreements = [a for a in filtered_agreements 
                              if a['status'] in [s.value for s in PRE_SIGNATURE_STATUSES]]
        
        if pipeline_agreements:
            prob_data = []
            for a in pipeline_agreements:
                prob = a.get('probability_to_sign') or 0
                ceiling = convert_to_sar(a['agreement_value_ceiling'], a['currency'])
                prob_data.append({
                    'Agreement': a['agreement_name'][:25] + '...' if len(a['agreement_name']) > 25 else a['agreement_name'],
                    'Probability': prob,
                    'Value': ceiling,
                    'Weighted': ceiling * prob / 100
                })
            
            df = pd.DataFrame(prob_data)
            
            fig = px.scatter(
                df, x='Probability', y='Value', size='Weighted',
                hover_name='Agreement',
                color='Probability',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(
                height=400,
                margin=dict(t=20, b=40),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                xaxis=dict(gridcolor='#334155', title='Probability (%)'),
                yaxis=dict(gridcolor='#334155', title='Value (SAR)')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pipeline agreements to display")
    
    with col2:
        st.markdown("### 📊 Monthly PO Trend")
        
        monthly_pos = forecast_data['monthly_pos']
        
        if monthly_pos:
            months = sorted(monthly_pos.keys())
            values = [monthly_pos[m] for m in months]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=months, y=values,
                marker_color='#3b82f6',
                name='PO Value'
            ))
            
            # Add trend line
            if len(values) > 1:
                import numpy as np
                x_numeric = list(range(len(months)))
                z = np.polyfit(x_numeric, values, 1)
                p = np.poly1d(z)
                fig.add_trace(go.Scatter(
                    x=months, y=[p(x) for x in x_numeric],
                    mode='lines',
                    line=dict(color='#f59e0b', width=2, dash='dash'),
                    name='Trend'
                ))
            
            fig.update_layout(
                height=400,
                margin=dict(t=20, b=40),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                xaxis=dict(gridcolor='#334155', title='Month'),
                yaxis=dict(gridcolor='#334155', title='PO Value (SAR)')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No PO data to display")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: AGREEMENTS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📝 Agreements":
    st.markdown("## 📝 Agreement Management")
    
    tab1, tab2, tab3 = st.tabs(["📋 All Agreements", "➕ Create New", "✏️ Edit/View"])
    
    with tab1:
        st.markdown("### All Agreements")
        
        if filtered_agreements:
            df = pd.DataFrame(filtered_agreements)
            display_cols = ['agreement_id', 'agreement_name', 'customer_name', 'customer_segment',
                           'status', 'agreement_value_ceiling', 'currency', 'account_manager',
                           'utilization_percent', 'risk_flag']
            
            if all(col in df.columns for col in display_cols):
                display_df = df[display_cols].copy()
                display_df['agreement_value_ceiling'] = display_df.apply(
                    lambda x: format_currency(x['agreement_value_ceiling'], x['currency']), axis=1
                )
                display_df['utilization_percent'] = display_df['utilization_percent'].apply(format_percentage)
                display_df.columns = ['ID', 'Agreement', 'Customer', 'Segment', 'Status', 
                                     'Ceiling', 'Currency', 'AM', 'Utilization', 'Risk']
                st.dataframe(display_df.drop(columns=['Currency']), use_container_width=True, hide_index=True)
        else:
            st.info("No agreements found")
    
    with tab2:
        st.markdown("### Create New Agreement")
        
        with st.form("create_agreement_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                agreement_name = st.text_input("Agreement Name*", placeholder="e.g., AI Services Framework")
                customer_name = st.text_input("Customer Name*", placeholder="e.g., Ministry of Interior")
                customer_segment = st.selectbox("Customer Segment*", [s.value for s in CustomerSegment])
                region = st.selectbox("Region", ["Central", "Western", "Eastern", "Northern", "Southern"])
                industry = st.text_input("Industry", placeholder="e.g., Public Sector")
                agreement_type = st.selectbox("Agreement Type*", [t.value for t in AgreementType])
            
            with col2:
                agreement_value = st.number_input("Agreement Value Ceiling*", min_value=1.0, value=1000000.0)
                currency = st.selectbox("Currency", [c.value for c in Currency])
                status = st.selectbox("Initial Status", [s.value for s in AgreementStatus 
                                                        if s in PRE_SIGNATURE_STATUSES])
                account_manager = st.text_input("Account Manager*", placeholder="e.g., Mohammed Al-Shehri")
                sales_owner = st.text_input("Sales Owner", placeholder="e.g., Ahmed Al-Harbi")
                probability = st.slider("Probability to Sign (%)", 0, 100, 50)
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=date.today())
            with col2:
                end_date = st.date_input("End Date", value=date.today() + timedelta(days=365))
            
            expected_sign = st.date_input("Expected Signature Date", value=date.today() + timedelta(days=30))
            notes = st.text_area("Notes", placeholder="Additional details...")
            
            submitted = st.form_submit_button("Create Agreement", use_container_width=True)
            
            if submitted:
                if not agreement_name or not customer_name or not account_manager:
                    st.error("Please fill in all required fields (*)")
                else:
                    try:
                        agreement_data = {
                            "agreement_name": agreement_name,
                            "customer_name": customer_name,
                            "customer_segment": customer_segment,
                            "region": region,
                            "industry": industry,
                            "agreement_type": agreement_type,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "agreement_value_ceiling": agreement_value,
                            "currency": currency,
                            "status": status,
                            "status_date": date.today().isoformat(),
                            "account_manager": account_manager,
                            "sales_owner": sales_owner,
                            "probability_to_sign": probability,
                            "expected_signature_date": expected_sign.isoformat(),
                            "notes": notes,
                        }
                        
                        agreement_id = create_agreement(conn, agreement_data)
                        st.success(f"✅ Agreement created successfully! ID: {agreement_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating agreement: {e}")
    
    with tab3:
        st.markdown("### Edit/View Agreement")
        
        agreement_ids = [a['agreement_id'] for a in all_agreements]
        
        if agreement_ids:
            selected_id = st.selectbox("Select Agreement", agreement_ids)
            
            if selected_id:
                agreement = get_agreement(conn, selected_id)
                
                if agreement:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Status", agreement['status'])
                    with col2:
                        st.metric("Utilization", format_percentage(agreement['utilization_percent']))
                    with col3:
                        st.metric("Risk", agreement['risk_flag'])
                    
                    st.markdown("---")
                    
                    with st.form("edit_agreement_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_name = st.text_input("Agreement Name", value=agreement['agreement_name'])
                            edit_customer = st.text_input("Customer Name", value=agreement['customer_name'])
                            
                            current_status = AgreementStatus(agreement['status'])
                            allowed_next = ALLOWED_STATUS_TRANSITIONS.get(current_status, [])
                            status_options = [current_status.value] + [s.value for s in allowed_next]
                            edit_status = st.selectbox("Status", status_options)
                            
                            edit_am = st.text_input("Account Manager", value=agreement['account_manager'] or "")
                        
                        with col2:
                            edit_value = st.number_input("Value Ceiling", 
                                                        value=float(agreement['agreement_value_ceiling']))
                            edit_currency = st.selectbox("Currency", 
                                                        [c.value for c in Currency],
                                                        index=[c.value for c in Currency].index(agreement['currency']))
                            
                            if edit_status in [AgreementStatus.SIGNED.value, AgreementStatus.ACTIVE.value]:
                                default_signed = datetime.strptime(agreement['signed_date'], "%Y-%m-%d").date() if agreement['signed_date'] else date.today()
                                edit_signed_date = st.date_input("Signed Date", value=default_signed)
                            else:
                                edit_signed_date = None
                                edit_prob = st.slider("Probability (%)", 0, 100, 
                                                     int(agreement['probability_to_sign'] or 50))
                        
                        edit_notes = st.text_area("Notes", value=agreement['notes'] or "")
                        
                        update_submitted = st.form_submit_button("Update Agreement", use_container_width=True)
                        
                        if update_submitted:
                            try:
                                update_data = {
                                    "agreement_name": edit_name,
                                    "customer_name": edit_customer,
                                    "status": edit_status,
                                    "status_date": date.today().isoformat(),
                                    "account_manager": edit_am,
                                    "agreement_value_ceiling": edit_value,
                                    "currency": edit_currency,
                                    "notes": edit_notes,
                                }
                                
                                if edit_signed_date:
                                    update_data["signed_date"] = edit_signed_date.isoformat()
                                elif 'edit_prob' in dir():
                                    update_data["probability_to_sign"] = edit_prob
                                
                                update_agreement(conn, selected_id, update_data)
                                st.success("✅ Agreement updated successfully!")
                                st.rerun()
                            except ValueError as e:
                                st.error(f"Error: {e}")
                            except Exception as e:
                                st.error(f"Error updating agreement: {e}")
                    
                    # Delete button
                    st.markdown("---")
                    if st.button("🗑️ Delete Agreement", type="secondary"):
                        if delete_agreement(conn, selected_id):
                            st.success("Agreement deleted!")
                            st.rerun()
        else:
            st.info("No agreements to edit")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PURCHASE ORDERS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "🧾 Purchase Orders":
    st.markdown("## 🧾 Purchase Orders")
    
    tab1, tab2 = st.tabs(["📋 All POs", "➕ Create PO"])
    
    with tab1:
        st.markdown("### All Purchase Orders")
        
        all_pos = get_all_pos(conn)
        
        if all_pos:
            df = pd.DataFrame(all_pos)
            display_df = df[['po_id', 'agreement_id', 'po_number', 'po_date', 
                           'po_value', 'currency', 'customer_name', 'account_manager']].copy()
            display_df['po_value'] = display_df.apply(
                lambda x: format_currency(x['po_value'], x['currency']), axis=1
            )
            display_df.columns = ['PO ID', 'Agreement', 'PO Number', 'Date', 
                                 'Value', 'Currency', 'Customer', 'AM']
            st.dataframe(display_df.drop(columns=['Currency']), use_container_width=True, hide_index=True)
        else:
            st.info("No purchase orders found")
    
    with tab2:
        st.markdown("### Create Purchase Order")
        
        # Only show signed/active agreements
        signed_agreements = [a for a in all_agreements 
                           if a['status'] in [s.value for s in POST_SIGNATURE_STATUSES]]
        
        if signed_agreements:
            with st.form("create_po_form"):
                agreement_options = {f"{a['agreement_id']} - {a['customer_name']}": a['agreement_id'] 
                                    for a in signed_agreements}
                selected_agreement = st.selectbox("Select Agreement*", list(agreement_options.keys()))
                agreement_id = agreement_options[selected_agreement]
                
                # Show agreement info
                agreement = get_agreement(conn, agreement_id)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"Ceiling: {format_currency(agreement['agreement_value_ceiling'], agreement['currency'])}")
                with col2:
                    st.info(f"Current POs: {format_currency(agreement['total_pos_value_to_date'])}")
                with col3:
                    remaining = agreement['agreement_value_ceiling'] - agreement['total_pos_value_to_date']
                    st.info(f"Remaining: {format_currency(remaining, agreement['currency'])}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    po_number = st.text_input("PO Number*", placeholder="e.g., PO-2025-001")
                    po_value = st.number_input("PO Value*", min_value=1.0, value=100000.0)
                    po_currency = st.selectbox("Currency", [c.value for c in Currency])
                
                with col2:
                    po_date = st.date_input("PO Date", value=date.today())
                    customer_name = st.text_input("Customer Name", value=agreement['customer_name'])
                    account_manager = st.text_input("Account Manager", value=agreement['account_manager'] or "")
                
                po_notes = st.text_area("Notes", placeholder="Additional details...")
                override = st.checkbox("Override ceiling check (Admin only)")
                
                po_submitted = st.form_submit_button("Create PO", use_container_width=True)
                
                if po_submitted:
                    if not po_number:
                        st.error("Please provide a PO number")
                    else:
                        try:
                            po_data = {
                                "agreement_id": agreement_id,
                                "po_number": po_number,
                                "po_date": po_date.isoformat(),
                                "po_value": po_value,
                                "currency": po_currency,
                                "customer_name": customer_name,
                                "account_manager": account_manager,
                                "notes": po_notes,
                            }
                            
                            po_id = create_po(conn, po_data, override_ceiling=override)
                            st.success(f"✅ PO created successfully! ID: {po_id}")
                            st.rerun()
                        except ValueError as e:
                            st.error(f"Error: {e}")
                        except Exception as e:
                            st.error(f"Error creating PO: {e}")
        else:
            st.warning("No signed/active agreements available. Create and sign an agreement first.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: IMPORT/EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📤 Import/Export":
    st.markdown("## 📤 Import/Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📥 Export Data")
        
        st.markdown("#### Agreements")
        agreements_csv = export_agreements_csv(conn)
        if agreements_csv:
            st.download_button(
                label="📥 Download Agreements CSV",
                data=agreements_csv,
                file_name=f"agreements_{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No agreements to export")
        
        st.markdown("#### Purchase Orders")
        pos_csv = export_pos_csv(conn)
        if pos_csv:
            st.download_button(
                label="📥 Download POs CSV",
                data=pos_csv,
                file_name=f"purchase_orders_{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No POs to export")
    
    with col2:
        st.markdown("### 📤 Import Data")
        
        st.markdown("#### Import Agreements")
        agreements_file = st.file_uploader("Upload Agreements CSV", type=['csv'], key='agreements_upload')
        
        if agreements_file:
            try:
                df = pd.read_csv(agreements_file)
                st.dataframe(df.head(), use_container_width=True)
                
                if st.button("Import Agreements", use_container_width=True):
                    success_count = 0
                    error_count = 0
                    
                    for _, row in df.iterrows():
                        try:
                            data = row.to_dict()
                            # Clean NaN values
                            data = {k: (v if pd.notna(v) else None) for k, v in data.items()}
                            create_agreement(conn, data)
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            st.warning(f"Error importing row: {e}")
                    
                    st.success(f"Imported {success_count} agreements. {error_count} errors.")
                    st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")
        
        st.markdown("#### Import POs")
        pos_file = st.file_uploader("Upload POs CSV", type=['csv'], key='pos_upload')
        
        if pos_file:
            try:
                df = pd.read_csv(pos_file)
                st.dataframe(df.head(), use_container_width=True)
                
                if st.button("Import POs", use_container_width=True):
                    success_count = 0
                    error_count = 0
                    
                    for _, row in df.iterrows():
                        try:
                            data = row.to_dict()
                            data = {k: (v if pd.notna(v) else None) for k, v in data.items()}
                            create_po(conn, data, override_ceiling=True)
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                    
                    st.success(f"Imported {success_count} POs. {error_count} errors.")
                    st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    st.markdown("---")
    
    # Sample Data Generation
    st.markdown("### 🔄 Sample Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎲 Generate Sample Data", use_container_width=True):
            from sample_data import generate_sample_data, clear_all_data
            clear_all_data(DB_PATH)
            generate_sample_data(DB_PATH)
            st.success("✅ Sample data generated!")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True):
            from sample_data import clear_all_data
            clear_all_data(DB_PATH)
            st.success("✅ All data cleared!")
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.sidebar.markdown("---")
st.sidebar.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.75rem;">
        <p>GTM Framework Agreements Dashboard</p>
        <p>Built for HUMAIN GTM Team</p>
        <p>v1.0.0</p>
    </div>
""", unsafe_allow_html=True)
