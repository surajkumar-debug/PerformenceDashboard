import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from io import StringIO
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
SHEET_ID   = "1J9_5oxXYv4QAyWbsLWkuiA4UNJpHDaP5FOAqNdVSJWc"
TAB_NAME   = "Data"
CSV_URL    = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={TAB_NAME}"

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Invoice Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .main { background: #0f1117; }
    .block-container { padding: 1rem 2rem; max-width: 100%; }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #1e2130 0%, #252840 100%);
        border: 1px solid #2d3250;
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .kpi-card:hover { transform: translateY(-3px); }
    .kpi-title { font-size: 12px; font-weight: 600; color: #8892a4; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #ffffff; margin-bottom: 4px; }
    .kpi-delta-pos { font-size: 13px; color: #10b981; font-weight: 600; }
    .kpi-delta-neg { font-size: 13px; color: #ef4444; font-weight: 600; }
    .kpi-delta-neu { font-size: 13px; color: #8892a4; font-weight: 600; }

    /* Section Headers */
    .section-header {
        background: linear-gradient(135deg, #1e40af, #0f766e);
        color: white;
        padding: 12px 20px;
        border-radius: 12px;
        font-size: 16px;
        font-weight: 700;
        margin: 20px 0 16px 0;
        letter-spacing: 0.5px;
    }

    /* Header Banner */
    .header-banner {
        background: linear-gradient(135deg, #1e40af 0%, #0f766e 50%, #7c3aed 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Sidebar */
    .css-1d391kg { background: #1a1d2e; }
    [data-testid="stSidebar"] { background: #1a1d2e; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #1e2130;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #8892a4;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af, #0f766e) !important;
        color: white !important;
    }

    /* Metric */
    [data-testid="metric-container"] {
        background: #1e2130;
        border: 1px solid #2d3250;
        border-radius: 12px;
        padding: 16px;
    }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* DataFrames */
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    /* Info box */
    .info-box {
        background: #1a2744;
        border-left: 4px solid #3b82f6;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        font-size: 14px;
        color: #93c5fd;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING & CACHING
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)  # Cache 5 minutes
def load_data():
    try:
        r = requests.get(CSV_URL, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        return df, None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# AUTO COLUMN DETECTION
# ─────────────────────────────────────────────
def auto_detect_columns(df):
    """Auto detect date, amount, user, and category columns"""
    detected = {
        'date_cols':    [],
        'amount_cols':  [],
        'user_cols':    [],
        'cat_cols':     [],
        'text_cols':    [],
        'num_cols':     []
    }

    date_keywords    = ['date','dt','time','submission','invoice_date','submitted']
    amount_keywords  = ['amount','value','total','invoice','gst','tds','payment','cost','price','sum','subtotal','pending']
    user_keywords    = ['user','by','name','employee','staff','submitted_by','person','submitter','agent']
    cat_keywords     = ['category','type','status','vertical','zone','voucher','mode','class','segment','project','vendor']

    for col in df.columns:
        col_lower = col.lower().replace(' ','_').replace('-','_')

        # Try date parse
        if any(k in col_lower for k in date_keywords):
            try:
                pd.to_datetime(df[col].dropna().head(10))
                detected['date_cols'].append(col)
                continue
            except:
                pass

        # Check if numeric
        numeric_data = pd.to_numeric(df[col], errors='coerce')
        pct_numeric  = numeric_data.notna().mean()

        if pct_numeric > 0.7:
            if any(k in col_lower for k in amount_keywords):
                detected['amount_cols'].append(col)
            else:
                detected['num_cols'].append(col)
        else:
            if any(k in col_lower for k in user_keywords):
                detected['user_cols'].append(col)
            elif any(k in col_lower for k in cat_keywords):
                detected['cat_cols'].append(col)
            else:
                unique_ratio = df[col].nunique() / max(len(df), 1)
                if unique_ratio < 0.3:
                    detected['cat_cols'].append(col)
                else:
                    detected['text_cols'].append(col)

    return detected

# ─────────────────────────────────────────────
# DATA PREPROCESSING
# ─────────────────────────────────────────────
def preprocess(df, detected):
    df = df.copy()

    # Convert date columns
    for col in detected['date_cols']:
        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

    # Convert amount columns
    for col in detected['amount_cols']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Convert num columns
    for col in detected['num_cols']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Add time features from first date column
    if detected['date_cols']:
        dcol = detected['date_cols'][0]
        df = df[df[dcol].notna()].copy()
        df['_date']    = df[dcol]
        df['_year']    = df[dcol].dt.year
        df['_month']   = df[dcol].dt.to_period('M').astype(str)
        df['_month_num'] = df[dcol].dt.month
        df['_week']    = df[dcol].dt.to_period('W').astype(str)
        df['_week_num'] = df[dcol].dt.isocalendar().week.astype(int)
        df['_quarter'] = df[dcol].dt.to_period('Q').astype(str)
        df['_day']     = df[dcol].dt.date
        df['_weekday'] = df[dcol].dt.day_name()

    return df

# ─────────────────────────────────────────────
# HELPER: Format numbers
# ─────────────────────────────────────────────
def fmt_inr(val):
    if pd.isna(val) or val == 0:
        return "₹0"
    if abs(val) >= 1e7:
        return f"₹{val/1e7:.2f}Cr"
    elif abs(val) >= 1e5:
        return f"₹{val/1e5:.2f}L"
    elif abs(val) >= 1e3:
        return f"₹{val/1e3:.1f}K"
    return f"₹{val:,.0f}"

def delta_arrow(curr, prev):
    if prev == 0:
        return "🆕 New", "kpi-delta-pos"
    pct = ((curr - prev) / abs(prev)) * 100
    if pct > 0:
        return f"▲ {pct:.1f}% vs prev", "kpi-delta-pos"
    elif pct < 0:
        return f"▼ {abs(pct):.1f}% vs prev", "kpi-delta-neg"
    return "→ No change", "kpi-delta-neu"

# ─────────────────────────────────────────────
# PLOT THEME
# ─────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#e2e8f0', family='Inter'),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor='rgba(30,33,48,0.8)', bordercolor='#2d3250', borderwidth=1),
    xaxis=dict(gridcolor='#1e2130', linecolor='#2d3250'),
    yaxis=dict(gridcolor='#1e2130', linecolor='#2d3250')
)
COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#84cc16','#ec4899','#14b8a6']

# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────
def main():

    # ── HEADER ──────────────────────────────
    st.markdown("""
    <div class="header-banner">
        <div>
            <div style="font-size:28px; font-weight:800; margin-bottom:4px;">📊 Invoice Performance Dashboard</div>
            <div style="font-size:14px; opacity:0.85;">Live • Auto-Refresh Every 5 Min • User & Time Intelligence</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:13px; opacity:0.8;">Last Updated</div>
            <div style="font-size:16px; font-weight:700;">""" + datetime.now().strftime("%d %b %Y, %H:%M") + """</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── LOAD DATA ───────────────────────────
    with st.spinner("🔄 Loading live data from Google Sheets..."):
        df_raw, err = load_data()

    if err or df_raw is None:
        st.error(f"❌ Could not load data: {err}")
        st.info("💡 Make sure sheet is shared as 'Anyone with link - Viewer'")
        st.code(CSV_URL)
        return

    if df_raw.empty:
        st.warning("⚠️ Sheet is empty!")
        return

    # ── AUTO DETECT ─────────────────────────
    detected = auto_detect_columns(df_raw)
    df = preprocess(df_raw, detected)

    # ── SIDEBAR ─────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Dashboard Controls")
        st.markdown("---")

        # Auto-refresh
        auto_refresh = st.checkbox("🔄 Auto Refresh (5 min)", value=True)
        if auto_refresh:
            st.markdown('<div class="info-box">Data refreshes every 5 minutes automatically</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📅 Date Filter")

        if '_date' in df.columns and not df['_date'].isna().all():
            min_d = df['_date'].min().date()
            max_d = df['_date'].max().date()
            date_range = st.date_input(
                "Select Range",
                value=(min_d, max_d),
                min_value=min_d,
                max_value=max_d
            )
            if len(date_range) == 2:
                df = df[(df['_date'].dt.date >= date_range[0]) & (df['_date'].dt.date <= date_range[1])]

        st.markdown("---")
        st.markdown("### 👤 User Filter")
        if detected['user_cols']:
            ucol = detected['user_cols'][0]
            users = ['All Users'] + sorted(df[ucol].dropna().unique().tolist())
            sel_user = st.selectbox("Select User", users)
            if sel_user != 'All Users':
                df = df[df[ucol] == sel_user]

        if detected['cat_cols']:
            st.markdown("---")
            st.markdown("### 🏷️ Category Filters")
            for cc in detected['cat_cols'][:3]:
                vals = ['All'] + sorted(df[cc].dropna().astype(str).unique().tolist())
                sel = st.selectbox(f"{cc}", vals)
                if sel != 'All':
                    df = df[df[cc].astype(str) == sel]

        st.markdown("---")
        st.markdown("### 🔍 Detected Columns")
        if detected['date_cols']:
            st.success(f"📅 Date: {', '.join(detected['date_cols'][:2])}")
        if detected['amount_cols']:
            st.info(f"💰 Amount: {', '.join(detected['amount_cols'][:3])}")
        if detected['user_cols']:
            st.warning(f"👤 User: {', '.join(detected['user_cols'][:2])}")

        st.markdown("---")
        st.caption(f"📊 {len(df):,} rows | {len(df.columns)} columns")

    if df.empty:
        st.warning("No data after filters!")
        return

    # ── TABS ────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Overview",
        "👤 User Performance",
        "📅 Time Analysis",
        "🔄 Comparison",
        "🔎 Raw Data"
    ])

    # ════════════════════════════════════════
    # TAB 1: OVERVIEW
    # ════════════════════════════════════════
    with tab1:
        st.markdown('<div class="section-header">📈 Key Performance Indicators</div>', unsafe_allow_html=True)

        # Get primary amount col
        amt_col = detected['amount_cols'][0] if detected['amount_cols'] else None
        usr_col = detected['user_cols'][0]   if detected['user_cols']   else None

        # KPIs
        now = datetime.now()
        curr_month = df[df['_month'] == now.strftime('%Y-%m')] if '_month' in df.columns else df
        prev_month_str = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        prev_month = df[df['_month'] == prev_month_str] if '_month' in df.columns else pd.DataFrame()

        c1, c2, c3, c4, c5 = st.columns(5)

        total_entries = len(df)
        curr_entries  = len(curr_month)
        prev_entries  = len(prev_month)
        d1, cl1 = delta_arrow(curr_entries, prev_entries)

        with c1:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-title">Total Entries</div>
                <div class="kpi-value">{total_entries:,}</div>
                <div class="{cl1}">{d1}</div>
            </div>""", unsafe_allow_html=True)

        if amt_col:
            total_val = df[amt_col].sum()
            curr_val  = curr_month[amt_col].sum() if not curr_month.empty else 0
            prev_val  = prev_month[amt_col].sum() if not prev_month.empty else 0
            d2, cl2   = delta_arrow(curr_val, prev_val)

            with c2:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-title">Total Value</div>
                    <div class="kpi-value">{fmt_inr(total_val)}</div>
                    <div class="{cl2}">{d2}</div>
                </div>""", unsafe_allow_html=True)

            with c3:
                avg_val = df[amt_col].mean()
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-title">Avg per Entry</div>
                    <div class="kpi-value">{fmt_inr(avg_val)}</div>
                    <div class="kpi-delta-neu">across all entries</div>
                </div>""", unsafe_allow_html=True)

        if usr_col:
            total_users = df[usr_col].nunique()
            active_this_month = curr_month[usr_col].nunique() if not curr_month.empty else 0

            with c4:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-title">Total Users</div>
                    <div class="kpi-value">{total_users}</div>
                    <div class="kpi-delta-pos">active in system</div>
                </div>""", unsafe_allow_html=True)

            with c5:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-title">Active This Month</div>
                    <div class="kpi-value">{active_this_month}</div>
                    <div class="kpi-delta-pos">users submitting</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">📊 Overview Charts</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        # Monthly Trend
        with col1:
            if '_month' in df.columns and amt_col:
                monthly = df.groupby('_month').agg(
                    Total=(amt_col, 'sum'),
                    Count=(amt_col, 'count')
                ).reset_index().sort_values('_month')

                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Bar(
                    x=monthly['_month'], y=monthly['Total'],
                    name='Total Value', marker_color='#3b82f6',
                    opacity=0.8
                ), secondary_y=False)
                fig.add_trace(go.Scatter(
                    x=monthly['_month'], y=monthly['Count'],
                    name='Count', line=dict(color='#f59e0b', width=2),
                    mode='lines+markers'
                ), secondary_y=True)
                fig.update_layout(title='📅 Monthly Trend', **PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        # User Distribution
        with col2:
            if usr_col and amt_col:
                user_sum = df.groupby(usr_col)[amt_col].sum().sort_values(ascending=False).head(10)
                fig = px.bar(
                    x=user_sum.values, y=user_sum.index,
                    orientation='h',
                    title='👤 Top 10 Users by Value',
                    color=user_sum.values,
                    color_continuous_scale='Blues',
                    labels={'x': 'Total Value', 'y': 'User'}
                )
                fig.update_layout(**PLOT_LAYOUT)
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(fig, use_container_width=True)

        # Category distribution
        if detected['cat_cols']:
            st.markdown('<div class="section-header">🏷️ Category Breakdown</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(detected['cat_cols'][:4]), 4))
            for idx, cc in enumerate(detected['cat_cols'][:4]):
                with cols[idx]:
                    vc = df[cc].value_counts().head(8)
                    fig = px.pie(
                        values=vc.values, names=vc.index,
                        title=f'{cc}',
                        color_discrete_sequence=COLORS,
                        hole=0.4
                    )
                    fig.update_layout(**PLOT_LAYOUT, margin=dict(l=5, r=5, t=40, b=5))
                    st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    # TAB 2: USER PERFORMANCE
    # ════════════════════════════════════════
    with tab2:
        st.markdown('<div class="section-header">👤 User-wise Performance Analysis</div>', unsafe_allow_html=True)

        if not detected['user_cols']:
            st.warning("No user column detected in data!")
        else:
            usr_col = detected['user_cols'][0]
            amt_col = detected['amount_cols'][0] if detected['amount_cols'] else None

            # User Summary Table
            agg_dict = {'Entries': (usr_col, 'count')}
            if amt_col:
                agg_dict['Total_Value']  = (amt_col, 'sum')
                agg_dict['Avg_Value']    = (amt_col, 'mean')
                agg_dict['Max_Value']    = (amt_col, 'max')

            user_summary = df.groupby(usr_col).agg(**agg_dict).reset_index()
            if amt_col:
                user_summary = user_summary.sort_values('Total_Value', ascending=False)

            col1, col2 = st.columns([1.5, 1])

            with col1:
                if amt_col:
                    fig = px.bar(
                        user_summary.head(15),
                        x='Total_Value', y=usr_col,
                        orientation='h',
                        title='💰 Total Value by User',
                        color='Total_Value',
                        color_continuous_scale='Viridis',
                        text='Total_Value'
                    )
                    fig.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
                    fig.update_layout(**PLOT_LAYOUT)
                    fig.update_coloraxes(showscale=False)
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Entry count pie
                fig = px.pie(
                    user_summary.head(10),
                    values='Entries', names=usr_col,
                    title='📊 Entry Share by User',
                    color_discrete_sequence=COLORS,
                    hole=0.35
                )
                fig.update_layout(**PLOT_LAYOUT, margin=dict(l=5, r=5, t=40, b=5))
                st.plotly_chart(fig, use_container_width=True)

            # Monthly heatmap
            if '_month' in df.columns and amt_col:
                st.markdown('<div class="section-header">🗓️ User × Month Heatmap</div>', unsafe_allow_html=True)
                pivot = df.pivot_table(
                    index=usr_col, columns='_month',
                    values=amt_col, aggfunc='sum', fill_value=0
                )
                fig = px.imshow(
                    pivot,
                    aspect='auto',
                    color_continuous_scale='Blues',
                    title='User Performance Heatmap (Monthly)',
                    labels=dict(x='Month', y='User', color='Value')
                )
                fig.update_layout(**PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            # User Summary Table
            st.markdown('<div class="section-header">📋 User Summary Table</div>', unsafe_allow_html=True)
            display_df = user_summary.copy()
            if amt_col:
                display_df['Total_Value'] = display_df['Total_Value'].apply(fmt_inr)
                display_df['Avg_Value']   = display_df['Avg_Value'].apply(fmt_inr)
                display_df['Max_Value']   = display_df['Max_Value'].apply(fmt_inr)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════
    # TAB 3: TIME ANALYSIS
    # ════════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-header">📅 Time-based Performance Analysis</div>', unsafe_allow_html=True)

        amt_col = detected['amount_cols'][0] if detected['amount_cols'] else None

        # Time granularity selector
        gran = st.radio(
            "Select Time Granularity",
            ["📅 Monthly", "📆 Weekly", "📊 Quarterly", "📈 Daily"],
            horizontal=True
        )

        period_col = {
            "📅 Monthly":    '_month',
            "📆 Weekly":     '_week',
            "📊 Quarterly":  '_quarter',
            "📈 Daily":      '_day'
        }.get(gran, '_month')

        if period_col not in df.columns:
            st.warning("Date column not detected!")
        else:
            if amt_col:
                trend = df.groupby(period_col).agg(
                    Total=(amt_col, 'sum'),
                    Count=(amt_col, 'count'),
                    Avg=(amt_col, 'mean')
                ).reset_index().sort_values(period_col)

                # Trend Chart
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    row_heights=[0.7, 0.3],
                    vertical_spacing=0.08
                )
                fig.add_trace(go.Bar(
                    x=trend[period_col].astype(str), y=trend['Total'],
                    name='Total Value', marker_color='#3b82f6', opacity=0.8
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=trend[period_col].astype(str), y=trend['Total'],
                    name='Trend Line', line=dict(color='#f59e0b', width=2, dash='dot'),
                    mode='lines'
                ), row=1, col=1)
                fig.add_trace(go.Bar(
                    x=trend[period_col].astype(str), y=trend['Count'],
                    name='Count', marker_color='#10b981', opacity=0.7
                ), row=2, col=1)
                fig.update_layout(
                    title=f"📈 {gran.split(' ')[1]} Performance Trend",
                    height=500,
                    **PLOT_LAYOUT
                )
                st.plotly_chart(fig, use_container_width=True)

            # Weekday Analysis
            if '_weekday' in df.columns:
                st.markdown('<div class="section-header">📆 Day of Week Analysis</div>', unsafe_allow_html=True)
                day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
                day_data  = df.groupby('_weekday').size().reindex(day_order, fill_value=0).reset_index()
                day_data.columns = ['Day', 'Count']

                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(
                        day_data, x='Day', y='Count',
                        title='📊 Submissions by Weekday',
                        color='Count',
                        color_continuous_scale='Blues'
                    )
                    fig.update_layout(**PLOT_LAYOUT)
                    fig.update_coloraxes(showscale=False)
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    if amt_col:
                        day_amt = df.groupby('_weekday')[amt_col].sum().reindex(day_order, fill_value=0).reset_index()
                        day_amt.columns = ['Day', 'Total']
                        fig = px.line_polar(
                            day_amt, r='Total', theta='Day',
                            title='🎯 Value Radar by Weekday',
                            line_close=True,
                            color_discrete_sequence=['#3b82f6']
                        )
                        fig.update_layout(**PLOT_LAYOUT, paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    # TAB 4: COMPARISON
    # ════════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-header">🔄 Period-over-Period Comparison</div>', unsafe_allow_html=True)

        amt_col = detected['amount_cols'][0] if detected['amount_cols'] else None
        usr_col = detected['user_cols'][0]   if detected['user_cols']   else None

        now         = datetime.now()
        curr_m_str  = now.strftime('%Y-%m')
        prev_m_str  = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

        curr_month_df = df[df['_month'] == curr_m_str]  if '_month' in df.columns else pd.DataFrame()
        prev_month_df = df[df['_month'] == prev_m_str]  if '_month' in df.columns else pd.DataFrame()

        # Current vs Last week
        curr_week = df[df['_week_num'] == now.isocalendar()[1]] if '_week_num' in df.columns else pd.DataFrame()
        prev_week = df[df['_week_num'] == now.isocalendar()[1]-1] if '_week_num' in df.columns else pd.DataFrame()

        # ── MONTH COMPARISON ────────────────
        st.markdown("#### 📅 Current Month vs Last Month")

        c1, c2, c3, c4 = st.columns(4)

        def compare_metric(col, curr_df, prev_df, label, prefix=""):
            curr_v = curr_df[col].sum() if col and not curr_df.empty else 0
            prev_v = prev_df[col].sum() if col and not prev_df.empty else 0
            delta  = curr_v - prev_v
            pct    = ((curr_v - prev_v) / abs(prev_v) * 100) if prev_v != 0 else 0
            return curr_v, prev_v, delta, pct

        def compare_count(curr_df, prev_df):
            curr_v = len(curr_df)
            prev_v = len(prev_df)
            pct    = ((curr_v - prev_v) / abs(prev_v) * 100) if prev_v != 0 else 0
            return curr_v, prev_v, pct

        c_cnt, p_cnt, pct_cnt = compare_count(curr_month_df, prev_month_df)
        with c1:
            st.metric(
                "📝 Entries",
                f"{c_cnt:,}",
                f"{c_cnt-p_cnt:+,} ({pct_cnt:+.1f}%)"
            )

        if amt_col:
            c_val, p_val, delta, pct = compare_metric(amt_col, curr_month_df, prev_month_df, "Value")
            with c2:
                st.metric("💰 Total Value", fmt_inr(c_val), f"{fmt_inr(delta)} ({pct:+.1f}%)")

        if usr_col:
            c_u = curr_month_df[usr_col].nunique() if not curr_month_df.empty else 0
            p_u = prev_month_df[usr_col].nunique() if not prev_month_df.empty else 0
            with c3:
                st.metric("👤 Active Users", c_u, f"{c_u-p_u:+,}")

        if amt_col:
            c_avg = curr_month_df[amt_col].mean() if not curr_month_df.empty else 0
            p_avg = prev_month_df[amt_col].mean() if not prev_month_df.empty else 0
            with c4:
                st.metric("📊 Avg Value", fmt_inr(c_avg), f"{fmt_inr(c_avg-p_avg)}")

        # Month Comparison Chart
        if amt_col and not curr_month_df.empty and not prev_month_df.empty and usr_col:
            col1, col2 = st.columns(2)

            with col1:
                # Side-by-side bar: curr vs prev month by user
                curr_u = curr_month_df.groupby(usr_col)[amt_col].sum().reset_index()
                curr_u['Period'] = f'Current ({curr_m_str})'
                prev_u = prev_month_df.groupby(usr_col)[amt_col].sum().reset_index()
                prev_u['Period'] = f'Previous ({prev_m_str})'
                combined = pd.concat([curr_u, prev_u])

                fig = px.bar(
                    combined, x=usr_col, y=amt_col, color='Period',
                    barmode='group',
                    title='📊 User Performance: Current vs Last Month',
                    color_discrete_sequence=['#3b82f6','#94a3b8']
                )
                fig.update_layout(**PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Waterfall change chart
                curr_total = curr_month_df[amt_col].sum()
                prev_total = prev_month_df[amt_col].sum()
                change     = curr_total - prev_total
                fig = go.Figure(go.Waterfall(
                    name="Change",
                    orientation="v",
                    measure=["absolute","relative","total"],
                    x=[f"Last Month\n({prev_m_str})", "Change", f"Current Month\n({curr_m_str})"],
                    y=[prev_total, change, curr_total],
                    connector={"line": {"color": "#2d3250"}},
                    decreasing={"marker": {"color": "#ef4444"}},
                    increasing={"marker": {"color": "#10b981"}},
                    totals={"marker": {"color": "#3b82f6"}}
                ))
                fig.update_layout(title="💧 Month-over-Month Waterfall", **PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        # ── WEEK COMPARISON ─────────────────
        st.markdown("---")
        st.markdown("#### 📆 Current Week vs Last Week")

        c1, c2, c3 = st.columns(3)

        cw_cnt, pw_cnt, pct_w = compare_count(curr_week, prev_week)
        with c1:
            st.metric("📝 Entries", f"{cw_cnt:,}", f"{cw_cnt-pw_cnt:+,} ({pct_w:+.1f}%)")

        if amt_col:
            cw_v, pw_v, dw, pctw = compare_metric(amt_col, curr_week, prev_week, "Value")
            with c2:
                st.metric("💰 Total Value", fmt_inr(cw_v), f"{fmt_inr(dw)} ({pctw:+.1f}%)")
            if usr_col:
                cw_u = curr_week[usr_col].nunique() if not curr_week.empty else 0
                pw_u = prev_week[usr_col].nunique() if not prev_week.empty else 0
                with c3:
                    st.metric("👤 Active Users", cw_u, f"{cw_u-pw_u:+,}")

        # Weekly bar chart
        if amt_col and not curr_week.empty and not prev_week.empty and usr_col:
            curr_w_u = curr_week.groupby(usr_col)[amt_col].sum().reset_index()
            curr_w_u['Period'] = 'Current Week'
            prev_w_u = prev_week.groupby(usr_col)[amt_col].sum().reset_index()
            prev_w_u['Period'] = 'Last Week'
            wk_combined = pd.concat([curr_w_u, prev_w_u])

            fig = px.bar(
                wk_combined, x=usr_col, y=amt_col, color='Period',
                barmode='group',
                title='📊 User Performance: Current vs Last Week',
                color_discrete_sequence=['#10b981','#94a3b8']
            )
            fig.update_layout(**PLOT_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    # TAB 5: RAW DATA
    # ════════════════════════════════════════
    with tab5:
        st.markdown('<div class="section-header">🔎 Raw Data Explorer</div>', unsafe_allow_html=True)

        # Search
        search = st.text_input("🔍 Search in any column...", placeholder="Type to filter rows...")

        display_cols = [c for c in df.columns if not c.startswith('_')]
        display_df   = df[display_cols].copy()

        if search:
            mask = display_df.astype(str).apply(
                lambda x: x.str.contains(search, case=False, na=False)
            ).any(axis=1)
            display_df = display_df[mask]

        st.caption(f"Showing {len(display_df):,} rows | {len(display_df.columns)} columns")
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)

        # Download
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ Download Filtered Data as CSV",
            csv,
            "invoice_data.csv",
            "text/csv"
        )

    # ── FOOTER ──────────────────────────────
    st.markdown("""
    <div style="text-align:center; color:#4a5568; font-size:12px; margin-top:40px; padding:16px; border-top:1px solid #2d3250;">
        📊 Invoice Performance Dashboard • Built with Streamlit + Plotly • Auto-refreshes every 5 minutes
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
