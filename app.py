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

# ── Auto Refresh (safe import) ───────────────
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
SHEET_ID = "1J9_5oxXYv4QAyWbsLWkuiA4UNJpHDaP5FOAqNdVSJWc"
TAB_NAME = "Data"
# FIX 1: gviz format - more reliable for named tabs
CSV_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}"

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
    .kpi-card {
        background: linear-gradient(135deg, #1e2130 0%, #252840 100%);
        border: 1px solid #2d3250; border-radius: 16px;
        padding: 20px 24px; text-align: center;
        transition: transform 0.2s ease;
    }
    .kpi-card:hover { transform: translateY(-3px); }
    .kpi-title { font-size: 12px; font-weight: 600; color: #8892a4; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #ffffff; margin-bottom: 4px; }
    .kpi-delta-pos { font-size: 13px; color: #10b981; font-weight: 600; }
    .kpi-delta-neg { font-size: 13px; color: #ef4444; font-weight: 600; }
    .kpi-delta-neu { font-size: 13px; color: #8892a4; font-weight: 600; }
    .section-header {
        background: linear-gradient(135deg, #1e40af, #0f766e);
        color: white; padding: 12px 20px; border-radius: 12px;
        font-size: 16px; font-weight: 700; margin: 20px 0 16px 0; letter-spacing: 0.5px;
    }
    .header-banner {
        background: linear-gradient(135deg, #1e40af 0%, #0f766e 50%, #7c3aed 100%);
        color: white; padding: 24px 32px; border-radius: 20px; margin-bottom: 24px;
    }
    [data-testid="stSidebar"] { background: #1a1d2e; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    .stTabs [data-baseweb="tab-list"] { background: #1e2130; border-radius: 12px; padding: 4px; gap: 4px; }
    .stTabs [data-baseweb="tab"] { background: transparent; color: #8892a4; border-radius: 8px; font-weight: 600; padding: 8px 20px; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #1e40af, #0f766e) !important; color: white !important; }
    [data-testid="metric-container"] { background: #1e2130; border: 1px solid #2d3250; border-radius: 12px; padding: 16px; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
    .info-box { background: #1a2744; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 0 8px 8px 0; font-size: 14px; color: #93c5fd; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    try:
        r = requests.get(CSV_URL, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        # Remove completely empty rows
        df = df.dropna(how='all')
        return df, None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# AUTO COLUMN DETECTION
# ─────────────────────────────────────────────
def auto_detect_columns(df):
    detected = {
        'date_cols': [], 'amount_cols': [],
        'user_cols': [], 'cat_cols': [],
        'text_cols': [], 'num_cols': []
    }
    date_kw   = ['date','dt','time','submission','invoice_date','submitted']
    amount_kw = ['amount','value','total','invoice','gst','tds','payment','cost','price','sum','subtotal','pending']
    user_kw   = ['user','by','name','employee','staff','submitted_by','person','submitter','agent']
    cat_kw    = ['category','type','status','vertical','zone','voucher','mode','class','segment','project','vendor']

    for col in df.columns:
        cl = col.lower().replace(' ','_').replace('-','_')
        if any(k in cl for k in date_kw):
            try:
                pd.to_datetime(df[col].dropna().head(20), dayfirst=True)
                detected['date_cols'].append(col)
                continue
            except:
                pass
        num = pd.to_numeric(df[col], errors='coerce')
        pct = num.notna().mean()
        if pct > 0.7:
            if any(k in cl for k in amount_kw):
                detected['amount_cols'].append(col)
            else:
                detected['num_cols'].append(col)
        else:
            if any(k in cl for k in user_kw):
                detected['user_cols'].append(col)
            elif any(k in cl for k in cat_kw):
                detected['cat_cols'].append(col)
            else:
                ratio = df[col].nunique() / max(len(df), 1)
                detected['cat_cols' if ratio < 0.3 else 'text_cols'].append(col)
    return detected

# ─────────────────────────────────────────────
# PREPROCESSING
# ─────────────────────────────────────────────
def preprocess(df, detected):
    df = df.copy()
    for col in detected['date_cols']:
        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    for col in detected['amount_cols']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    for col in detected['num_cols']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    if detected['date_cols']:
        dcol = detected['date_cols'][0]
        df   = df[df[dcol].notna()].copy()
        df['_date']      = df[dcol]
        df['_year']      = df[dcol].dt.year
        df['_month']     = df[dcol].dt.to_period('M').astype(str)
        df['_month_num'] = df[dcol].dt.month
        df['_week']      = df[dcol].dt.to_period('W').astype(str)
        # FIX 4: Use year+week for correct week filtering
        iso = df[dcol].dt.isocalendar()
        df['_iso_year']  = iso['year'].astype(int)
        df['_week_num']  = iso['week'].astype(int)
        df['_quarter']   = df[dcol].dt.to_period('Q').astype(str)
        # FIX 3: Convert _day to string to avoid plot issues
        df['_day']       = df[dcol].dt.strftime('%Y-%m-%d')
        df['_weekday']   = df[dcol].dt.day_name()
    return df

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fmt_inr(val):
    try:
        val = float(val)
        if pd.isna(val): return "₹0"
        if abs(val) >= 1e7:  return f"₹{val/1e7:.2f}Cr"
        if abs(val) >= 1e5:  return f"₹{val/1e5:.2f}L"
        if abs(val) >= 1e3:  return f"₹{val/1e3:.1f}K"
        return f"₹{val:,.0f}"
    except:
        return "₹0"

def delta_arrow(curr, prev):
    if prev == 0: return "🆕 New", "kpi-delta-pos"
    pct = ((curr - prev) / abs(prev)) * 100
    if pct > 0:   return f"▲ {pct:.1f}% vs prev", "kpi-delta-pos"
    if pct < 0:   return f"▼ {abs(pct):.1f}% vs prev", "kpi-delta-neg"
    return "→ No change", "kpi-delta-neu"

# FIX 5: Safe column access on possibly empty DataFrames
def safe_sum(df, col):
    if df is None or df.empty or col not in df.columns: return 0
    return df[col].sum()

def safe_mean(df, col):
    if df is None or df.empty or col not in df.columns: return 0
    return df[col].mean()

def safe_nunique(df, col):
    if df is None or df.empty or col not in df.columns: return 0
    return df[col].nunique()

# ─────────────────────────────────────────────
# PLOT THEME
# ─────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#e2e8f0', family='Inter'),
    legend=dict(bgcolor='rgba(30,33,48,0.8)', bordercolor='#2d3250', borderwidth=1),
    xaxis=dict(gridcolor='#1e2130', linecolor='#2d3250'),
    yaxis=dict(gridcolor='#1e2130', linecolor='#2d3250')
)
# Default margins - use separately
MARGIN_DEFAULT = dict(l=10, r=10, t=40, b=10)
MARGIN_COMPACT = dict(l=5,  r=5,  t=40, b=5)
COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#84cc16','#ec4899','#14b8a6']

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():

    # ── HEADER ──────────────────────────────
    now = datetime.now()
    st.markdown(f"""
    <div class="header-banner">
        <div>
            <div style="font-size:28px;font-weight:800;margin-bottom:4px;">📊 Invoice Performance Dashboard</div>
            <div style="font-size:14px;opacity:0.85;">Live • Auto-Refresh Every 5 Min • User & Time Intelligence</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:13px;opacity:0.8;">Last Updated</div>
            <div style="font-size:16px;font-weight:700;">{now.strftime("%d %b %Y, %H:%M")}</div>
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

    detected = auto_detect_columns(df_raw)
    df       = preprocess(df_raw, detected)

    # ── SIDEBAR ─────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Dashboard Controls")
        st.markdown("---")

        # FIX 2: Real auto-refresh
        auto_refresh = st.checkbox("🔄 Auto Refresh (5 min)", value=True)
        if auto_refresh:
            if AUTOREFRESH_AVAILABLE:
                st_autorefresh(interval=300000, key="autorefresh")
                st.markdown('<div class="info-box">✅ Auto-refresh active every 5 min</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="info-box">⚠️ Manual refresh needed (F5)</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📅 Date Filter")

        if '_date' in df.columns and not df['_date'].isna().all():
            min_d = df['_date'].min().date()
            max_d = df['_date'].max().date()
            date_range = st.date_input("Select Range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
            if len(date_range) == 2:
                df = df[(df['_date'].dt.date >= date_range[0]) & (df['_date'].dt.date <= date_range[1])]

        st.markdown("---")
        st.markdown("### 👤 User Filter")
        if detected['user_cols']:
            ucol  = detected['user_cols'][0]
            users = ['All Users'] + sorted(df[ucol].dropna().unique().tolist())
            sel_user = st.selectbox("Select User", users)
            if sel_user != 'All Users':
                df = df[df[ucol] == sel_user]

        if detected['cat_cols']:
            st.markdown("---")
            st.markdown("### 🏷️ Category Filters")
            for cc in detected['cat_cols'][:3]:
                vals = ['All'] + sorted(df[cc].dropna().astype(str).unique().tolist())
                sel  = st.selectbox(cc, vals)
                if sel != 'All':
                    df = df[df[cc].astype(str) == sel]

        st.markdown("---")
        st.markdown("### 🔍 Detected Columns")
        if detected['date_cols']:   st.success(f"📅 Date: {', '.join(detected['date_cols'][:2])}")
        if detected['amount_cols']: st.info(f"💰 Amount: {', '.join(detected['amount_cols'][:3])}")
        if detected['user_cols']:   st.warning(f"👤 User: {', '.join(detected['user_cols'][:2])}")
        st.markdown("---")
        st.caption(f"📊 {len(df):,} rows | {len(df.columns)} columns")

    if df.empty:
        st.warning("No data after applying filters!")
        return

    # ── TABS ────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Overview", "👤 User Performance",
        "📅 Time Analysis", "🔄 Comparison", "🔎 Raw Data"
    ])

    amt_col = detected['amount_cols'][0] if detected['amount_cols'] else None
    usr_col = detected['user_cols'][0]   if detected['user_cols']   else None

    # FIX 6: Year-aware week filtering
    curr_y, curr_w = now.isocalendar()[0], now.isocalendar()[1]
    prev_w = curr_w - 1
    prev_w_year = curr_y if curr_w > 1 else curr_y - 1

    curr_m_str = now.strftime('%Y-%m')
    prev_m_str = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    curr_month_df = df[df['_month'] == curr_m_str] if '_month' in df.columns else pd.DataFrame(columns=df.columns)
    prev_month_df = df[df['_month'] == prev_m_str] if '_month' in df.columns else pd.DataFrame(columns=df.columns)

    if '_week_num' in df.columns and '_iso_year' in df.columns:
        curr_week = df[(df['_iso_year'] == curr_y) & (df['_week_num'] == curr_w)]
        prev_week = df[(df['_iso_year'] == prev_w_year) & (df['_week_num'] == prev_w)]
    else:
        curr_week = pd.DataFrame(columns=df.columns)
        prev_week = pd.DataFrame(columns=df.columns)

    # ════════════════════════════════════════
    # TAB 1: OVERVIEW
    # ════════════════════════════════════════
    with tab1:
        st.markdown('<div class="section-header">📈 Key Performance Indicators</div>', unsafe_allow_html=True)

        total_entries = len(df)
        curr_entries  = len(curr_month_df)
        prev_entries  = len(prev_month_df)
        d1, cl1 = delta_arrow(curr_entries, prev_entries)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-title">Total Entries</div>
                <div class="kpi-value">{total_entries:,}</div>
                <div class="{cl1}">{d1}</div>
            </div>""", unsafe_allow_html=True)

        if amt_col:
            total_val = df[amt_col].sum()
            curr_val  = safe_sum(curr_month_df, amt_col)
            prev_val  = safe_sum(prev_month_df, amt_col)
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
            active_now  = safe_nunique(curr_month_df, usr_col)
            with c4:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-title">Total Users</div>
                    <div class="kpi-value">{total_users}</div>
                    <div class="kpi-delta-pos">active in system</div>
                </div>""", unsafe_allow_html=True)
            with c5:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-title">Active This Month</div>
                    <div class="kpi-value">{active_now}</div>
                    <div class="kpi-delta-pos">users submitting</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">📊 Overview Charts</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            if '_month' in df.columns and amt_col:
                monthly = df.groupby('_month').agg(Total=(amt_col,'sum'), Count=(amt_col,'count')).reset_index().sort_values('_month')
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Bar(x=monthly['_month'], y=monthly['Total'], name='Total Value', marker_color='#3b82f6', opacity=0.8), secondary_y=False)
                fig.add_trace(go.Scatter(x=monthly['_month'], y=monthly['Count'], name='Count', line=dict(color='#f59e0b', width=2), mode='lines+markers'), secondary_y=True)
                fig.update_layout(title='📅 Monthly Trend', margin=MARGIN_DEFAULT, **PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            if usr_col and amt_col:
                user_sum = df.groupby(usr_col)[amt_col].sum().sort_values(ascending=False).head(10)
                fig = px.bar(x=user_sum.values, y=user_sum.index, orientation='h',
                             title='👤 Top 10 Users by Value', color=user_sum.values,
                             color_continuous_scale='Blues', labels={'x':'Total Value','y':'User'})
                fig.update_layout(margin=MARGIN_DEFAULT, **PLOT_LAYOUT)
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(fig, use_container_width=True)

        if detected['cat_cols']:
            st.markdown('<div class="section-header">🏷️ Category Breakdown</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(detected['cat_cols'][:4]), 4))
            for idx, cc in enumerate(detected['cat_cols'][:4]):
                with cols[idx]:
                    vc  = df[cc].value_counts().head(8)
                    fig = px.pie(values=vc.values, names=vc.index, title=cc, color_discrete_sequence=COLORS, hole=0.4)
                    fig.update_layout(**PLOT_LAYOUT, margin=dict(l=5,r=5,t=40,b=5))
                    st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    # TAB 2: USER PERFORMANCE
    # ════════════════════════════════════════
    with tab2:
        st.markdown('<div class="section-header">👤 User-wise Performance Analysis</div>', unsafe_allow_html=True)
        if not usr_col:
            st.warning("No user column detected!")
        else:
            agg_dict = {'Entries': (usr_col, 'count')}
            if amt_col:
                agg_dict.update({'Total_Value':(amt_col,'sum'), 'Avg_Value':(amt_col,'mean'), 'Max_Value':(amt_col,'max')})
            user_summary = df.groupby(usr_col).agg(**agg_dict).reset_index()
            if amt_col:
                user_summary = user_summary.sort_values('Total_Value', ascending=False)

            col1, col2 = st.columns([1.5, 1])
            with col1:
                if amt_col:
                    fig = px.bar(user_summary.head(15), x='Total_Value', y=usr_col, orientation='h',
                                 title='💰 Total Value by User', color='Total_Value', color_continuous_scale='Viridis', text='Total_Value')
                    fig.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
                    fig.update_layout(**PLOT_LAYOUT)
                    fig.update_coloraxes(showscale=False)
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.pie(user_summary.head(10), values='Entries', names=usr_col,
                             title='📊 Entry Share by User', color_discrete_sequence=COLORS, hole=0.35)
                fig.update_layout(**PLOT_LAYOUT, margin=dict(l=5,r=5,t=40,b=5))
                st.plotly_chart(fig, use_container_width=True)

            if '_month' in df.columns and amt_col:
                st.markdown('<div class="section-header">🗓️ User × Month Heatmap</div>', unsafe_allow_html=True)
                pivot = df.pivot_table(index=usr_col, columns='_month', values=amt_col, aggfunc='sum', fill_value=0)
                fig = px.imshow(pivot, aspect='auto', color_continuous_scale='Blues',
                                title='User Performance Heatmap (Monthly)', labels=dict(x='Month', y='User', color='Value'))
                fig.update_layout(margin=MARGIN_DEFAULT, **PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown('<div class="section-header">📋 User Summary Table</div>', unsafe_allow_html=True)
            disp = user_summary.copy()
            if amt_col:
                for c in ['Total_Value','Avg_Value','Max_Value']:
                    if c in disp.columns:
                        disp[c] = disp[c].apply(fmt_inr)
            st.dataframe(disp, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════
    # TAB 3: TIME ANALYSIS
    # ════════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-header">📅 Time-based Performance Analysis</div>', unsafe_allow_html=True)
        gran = st.radio("Select Time Granularity", ["📅 Monthly","📆 Weekly","📊 Quarterly","📈 Daily"], horizontal=True)
        period_col = {"📅 Monthly":'_month',"📆 Weekly":'_week',"📊 Quarterly":'_quarter',"📈 Daily":'_day'}.get(gran,'_month')
        # FIX: Safe title extraction
        gran_label = gran.split(' ')[-1] if ' ' in gran else gran

        if period_col not in df.columns:
            st.warning("Date column not detected!")
        elif amt_col:
            trend = df.groupby(period_col).agg(Total=(amt_col,'sum'), Count=(amt_col,'count'), Avg=(amt_col,'mean')).reset_index().sort_values(period_col)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3], vertical_spacing=0.08)
            fig.add_trace(go.Bar(x=trend[period_col].astype(str), y=trend['Total'], name='Total Value', marker_color='#3b82f6', opacity=0.8), row=1, col=1)
            fig.add_trace(go.Scatter(x=trend[period_col].astype(str), y=trend['Total'], name='Trend', line=dict(color='#f59e0b', width=2, dash='dot'), mode='lines'), row=1, col=1)
            fig.add_trace(go.Bar(x=trend[period_col].astype(str), y=trend['Count'], name='Count', marker_color='#10b981', opacity=0.7), row=2, col=1)
                            fig.update_layout(title=f"📈 {gran_label} Performance Trend", height=500, margin=MARGIN_DEFAULT, **PLOT_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

        if '_weekday' in df.columns:
            st.markdown('<div class="section-header">📆 Day of Week Analysis</div>', unsafe_allow_html=True)
            day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            day_data  = df.groupby('_weekday').size().reindex(day_order, fill_value=0).reset_index()
            day_data.columns = ['Day','Count']
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(day_data, x='Day', y='Count', title='📊 Submissions by Weekday', color='Count', color_continuous_scale='Blues')
                fig.update_layout(**PLOT_LAYOUT)
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                if amt_col:
                    day_amt = df.groupby('_weekday')[amt_col].sum().reindex(day_order, fill_value=0).reset_index()
                    day_amt.columns = ['Day','Total']
                    fig = px.line_polar(day_amt, r='Total', theta='Day', title='🎯 Value Radar by Weekday', line_close=True, color_discrete_sequence=['#3b82f6'])
                    fig.update_layout(**PLOT_LAYOUT)
                    st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    # TAB 4: COMPARISON
    # ════════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-header">🔄 Period-over-Period Comparison</div>', unsafe_allow_html=True)

        st.markdown("#### 📅 Current Month vs Last Month")
        c1, c2, c3, c4 = st.columns(4)

        c_cnt, p_cnt = len(curr_month_df), len(prev_month_df)
        pct_cnt = ((c_cnt - p_cnt) / abs(p_cnt) * 100) if p_cnt else 0
        with c1: st.metric("📝 Entries", f"{c_cnt:,}", f"{c_cnt-p_cnt:+,} ({pct_cnt:+.1f}%)")

        if amt_col:
            c_val = safe_sum(curr_month_df, amt_col)
            p_val = safe_sum(prev_month_df, amt_col)
            delta = c_val - p_val
            pct   = ((delta / abs(p_val)) * 100) if p_val else 0
            with c2: st.metric("💰 Total Value", fmt_inr(c_val), f"{fmt_inr(delta)} ({pct:+.1f}%)")

        if usr_col:
            c_u = safe_nunique(curr_month_df, usr_col)
            p_u = safe_nunique(prev_month_df, usr_col)
            with c3: st.metric("👤 Active Users", c_u, f"{c_u-p_u:+,}")

        if amt_col:
            c_avg = safe_mean(curr_month_df, amt_col)
            p_avg = safe_mean(prev_month_df, amt_col)
            with c4: st.metric("📊 Avg Value", fmt_inr(c_avg), f"{fmt_inr(c_avg-p_avg)}")

        if amt_col and usr_col and not curr_month_df.empty and not prev_month_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                curr_u = curr_month_df.groupby(usr_col)[amt_col].sum().reset_index()
                curr_u['Period'] = f'Current ({curr_m_str})'
                prev_u = prev_month_df.groupby(usr_col)[amt_col].sum().reset_index()
                prev_u['Period'] = f'Previous ({prev_m_str})'
                fig = px.bar(pd.concat([curr_u, prev_u]), x=usr_col, y=amt_col, color='Period',
                             barmode='group', title='📊 User: Current vs Last Month', color_discrete_sequence=['#3b82f6','#94a3b8'])
                fig.update_layout(margin=MARGIN_DEFAULT, **PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                curr_t = safe_sum(curr_month_df, amt_col)
                prev_t = safe_sum(prev_month_df, amt_col)
                change = curr_t - prev_t
                fig = go.Figure(go.Waterfall(
                    orientation="v", measure=["absolute","relative","total"],
                    x=[f"Last Month\n({prev_m_str})","Change",f"Current\n({curr_m_str})"],
                    y=[prev_t, change, curr_t],
                    connector={"line":{"color":"#2d3250"}},
                    decreasing={"marker":{"color":"#ef4444"}},
                    increasing={"marker":{"color":"#10b981"}},
                    totals={"marker":{"color":"#3b82f6"}}
                ))
                fig.update_layout(title="💧 Month-over-Month Waterfall", margin=MARGIN_DEFAULT, **PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📆 Current Week vs Last Week")
        c1, c2, c3 = st.columns(3)
        cw_cnt, pw_cnt = len(curr_week), len(prev_week)
        pct_w = ((cw_cnt - pw_cnt) / abs(pw_cnt) * 100) if pw_cnt else 0
        with c1: st.metric("📝 Entries", f"{cw_cnt:,}", f"{cw_cnt-pw_cnt:+,} ({pct_w:+.1f}%)")

        if amt_col:
            cw_v = safe_sum(curr_week, amt_col)
            pw_v = safe_sum(prev_week, amt_col)
            dw   = cw_v - pw_v
            pctw = ((dw / abs(pw_v)) * 100) if pw_v else 0
            with c2: st.metric("💰 Total Value", fmt_inr(cw_v), f"{fmt_inr(dw)} ({pctw:+.1f}%)")
            if usr_col:
                cw_u = safe_nunique(curr_week, usr_col)
                pw_u = safe_nunique(prev_week, usr_col)
                with c3: st.metric("👤 Active Users", cw_u, f"{cw_u-pw_u:+,}")

        if amt_col and usr_col and not curr_week.empty and not prev_week.empty:
            cw_u_df = curr_week.groupby(usr_col)[amt_col].sum().reset_index()
            cw_u_df['Period'] = 'Current Week'
            pw_u_df = prev_week.groupby(usr_col)[amt_col].sum().reset_index()
            pw_u_df['Period'] = 'Last Week'
            fig = px.bar(pd.concat([cw_u_df, pw_u_df]), x=usr_col, y=amt_col, color='Period',
                         barmode='group', title='📊 User: Current vs Last Week', color_discrete_sequence=['#10b981','#94a3b8'])
            fig.update_layout(margin=MARGIN_DEFAULT, **PLOT_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    # TAB 5: RAW DATA
    # ════════════════════════════════════════
    with tab5:
        st.markdown('<div class="section-header">🔎 Raw Data Explorer</div>', unsafe_allow_html=True)
        search = st.text_input("🔍 Search in any column...", placeholder="Type to filter rows...")
        display_cols = [c for c in df.columns if not c.startswith('_')]
        display_df   = df[display_cols].copy()
        if search:
            mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
            display_df = display_df[mask]
        st.caption(f"Showing {len(display_df):,} rows | {len(display_df.columns)} columns")
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)
        csv_dl = display_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download Filtered Data as CSV", csv_dl, "invoice_data.csv", "text/csv")

    st.markdown("""
    <div style="text-align:center;color:#4a5568;font-size:12px;margin-top:40px;padding:16px;border-top:1px solid #2d3250;">
        📊 Invoice Performance Dashboard • Built with Streamlit + Plotly • Live Data from Google Sheets
    </div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
