import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
from datetime import datetime, timedelta

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="PK NOODLE SHOP Dashboard",
    page_icon="logo.png" if os.path.exists("logo.png") else "🍜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
    }
    .metric-card {
        background-color: #FFFFFF;
        padding: 18px 25px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
        text-align: center;
        border: 1px solid #E2E8F0;
    }
    .metric-title {
        color: #64748B;
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 5px;
    }
    .metric-value {
        color: #1E293B;
        font-size: 28px;
        font-weight: 700;
    }
    .trick-banner {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 10px 18px;
        border-radius: 8px;
        font-size: 14px;
        margin-bottom: 20px;
        border-left: 5px solid #0284C7;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. COLOR MAP & HELPER FUNCTIONS
# ==========================================
branch_color_map = {
    'ศรีเมือง': '#EF4444',  # สีแดง
    'ทุ่งปอ': '#3B82F6',   # สีฟ้า
    'เจ้าพรหม': '#A855F7',  # สีม่วง
    'บ้านไร่': '#10B981',   # สีเขียว
    'เทศบาล': '#EAB308',  # สีเหลือง
    'บ้านโป่ง': '#EC4899'   # สีชมพู
}

def clean_numeric(series):
    """ทำความสะอาดข้อมูลตัวเลข ลบจุลภาค (,), ฿, ช่องว่าง และแปลงเป็น float"""
    if series is None:
        return pd.Series(0.0)
    
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0.0).astype(float)
        
    s = series.astype(str).str.strip()
    s = s.str.replace('\ufeff', '', regex=False)
    s = s.str.replace('\xa0', '', regex=False)
    s = s.str.replace(',', '', regex=False)
    s = s.str.replace('฿', '', regex=False)
    s = s.str.replace('THB', '', regex=False, case=False)
    s = s.str.replace(' ', '', regex=False)
    s = s.str.replace(r'^\((.*)\)$', r'-\1', regex=True)
    
    return pd.to_numeric(s, errors='coerce').fillna(0.0)

def get_sales_amount_series(df):
    """ค้นหาคอลัมน์ยอดขายอย่างฉลาดและดึงข้อมูลออกมา"""
    candidates = [
        'TRD_B_AMT', 'TRD_B_AMNT', 'TRD_AMOUNT', 'TRD_AMT', 'TRD_NET', 'TRD_VAL', 'TRD_G_AMT',
        'DI_AMOUNT', 'DI_NET_VAL', 'DI_AMOUNT_NET', 'DI_TOTAL',
        'NET_VAL', 'NET_AMT', 'NET_AMOUNT', 'NETVAL', 'NET_BAHT', 'NET',
        'TOTAL_NET', 'TOTAL_AMT', 'TOTAL_AMOUNT', 'TOTAL_VAL', 'TOTAL_PRICE', 'TOTAL',
        'GRANDTOTAL', 'GRAND_TOTAL', 'SUM_AMOUNT', 'SUM_AMT', 'SUM_VAL',
        'AMOUNT', 'AMOUNT_TH', 'AMOUNT_BAHT', 'VAL', 'VALUE', 'PRICE',
        'ยอดขาย', 'ยอดเงิน', 'จำนวนเงิน', 'จำนวนเงินรวม', 'มูลค่า', 'ราคารวม', 'ยอดรวม', 'ยอดรวมทั้งสิ้น'
    ]
    
    df_cols_upper = {str(c).strip().replace('\ufeff', '').upper(): c for c in df.columns}
    
    # 1. ค้นหาแบบตรงกับคำค้นหา
    for col in candidates:
        col_u = col.upper()
        if col_u in df_cols_upper:
            real_col = df_cols_upper[col_u]
            s = clean_numeric(df[real_col])
            if s.abs().sum() > 0:
                return s

    # 2. ค้นหาแบบบางส่วนของชื่อคอลัมน์
    keywords = ['AMT', 'AMOUNT', 'VAL', 'NET', 'TOTAL', 'PRICE', 'ยอด', 'เงิน', 'ราคา', 'มูลค่า']
    for col_u, real_col in df_cols_upper.items():
        if any(kw in col_u for kw in keywords):
            if any(skip in col_u for skip in ['QTY', 'QUANTITY', 'DATE', 'TIME', 'YEAR', 'MONTH', 'DAY', 'ID', 'NO', 'NUM', 'CODE', 'RATE', 'PERCENT', 'DISC', 'TAX', 'VAT']):
                continue
            s = clean_numeric(df[real_col])
            if s.abs().sum() > 0:
                return s

    # 3. ค้นหาจากคอลัมน์ทั้งหมดที่มีตัวเลขยอดรวมสูงสุด
    best_series = None
    max_sum = 0
    for real_col in df.columns:
        col_u = str(real_col).strip().replace('\ufeff', '').upper()
        if any(skip in col_u for skip in ['QTY', 'QUANTITY', 'DATE', 'TIME', 'YEAR', 'MONTH', 'DAY', 'ID', 'NO', 'NUM', 'CODE', 'BRANCH', 'NAME', 'สาขา', 'วันที่']):
            continue
        s = clean_numeric(df[real_col])
        current_sum = s.abs().sum()
        if current_sum > max_sum:
            max_sum = current_sum
            best_series = s

    if best_series is not None and max_sum > 0:
        return best_series

    return pd.Series(0.0, index=df.index)

def get_branch_series(df):
    """ค้นหาคอลัมน์ชื่อสาขา"""
    branch_candidates = [
        'NAME', 'BRANCH', 'BRANCH_NAME', 'NAME_TH', 'DI_BRANCH', 'BRANCHNAME',
        'สาขา', 'ชื่อสาขา', 'สถานี', 'SHOP', 'SHOP_NAME', 'STORE'
    ]
    df_cols_upper = {str(c).strip().replace('\ufeff', '').upper(): c for c in df.columns}
    
    for col in branch_candidates:
        col_u = col.upper()
        if col_u in df_cols_upper:
            real_col = df_cols_upper[col_u]
            return df[real_col].astype(str).str.strip()
            
    for col_u, real_col in df_cols_upper.items():
        if 'BRANCH' in col_u or 'สาขา' in col_u or 'SHOP' in col_u:
            return df[real_col].astype(str).str.strip()
            
    return pd.Series('ไม่ระบุสาขา', index=df.index)

def parse_date_column(df):
    """แปลงคอลัมน์วันที่ รองรับทั้ง พ.ศ. และ ค.ศ."""
    date_cols = [
        'DOC_DATE', 'DATE', 'DOCDATE', 'DOC_DT', 'DOC_TIME', 
        'TRAN_DATE', 'TRD_DATE', 'DI_DATE', 'วันที่', 'วัน/เดือน/ปี', 'DATE_TIME', 'CREATED_AT'
    ]
    cols_map = {str(c).strip().replace('\ufeff', '').upper(): c for c in df.columns}
    
    found_col = None
    for c in date_cols:
        if c in cols_map:
            found_col = cols_map[c]
            break
            
    if not found_col:
        for c_u, real_c in cols_map.items():
            if 'DATE' in c_u or 'วัน' in c_u or 'TIME' in c_u:
                found_col = real_c
                break
                
    if found_col:
        s_date = df[found_col].astype(str).str.strip()
        
        def convert_be_to_ce(val):
            if pd.isna(val) or str(val).lower() in ['nan', 'none', 'nat', '']:
                return None
            val_str = str(val)
            m = re.search(r'\b(24\d{2}|25\d{2}|26\d{2})\b', val_str)
            if m:
                be_year = int(m.group(1))
                ce_year = be_year - 543
                val_str = val_str.replace(str(be_year), str(ce_year))
            return val_str

        converted_dates = s_date.apply(convert_be_to_ce)
        df['Parsed_Date'] = pd.to_datetime(converted_dates, errors='coerce', dayfirst=True)
        
        mask_nat = df['Parsed_Date'].isna()
        if mask_nat.any():
            df.loc[mask_nat, 'Parsed_Date'] = pd.to_datetime(df.loc[mask_nat, found_col], errors='coerce')

        df['Year_BE'] = df['Parsed_Date'].dt.year.apply(lambda y: int(y + 543) if pd.notnull(y) and not pd.isna(y) else None)
    else:
        df['Parsed_Date'] = pd.NaT
        df['Year_BE'] = None
    return df

def process_product_dataframe(df):
    """ทำความสะอาดข้อมูลสินค้า BPLUS"""
    df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
    df = parse_date_column(df)
    df['NAME'] = get_branch_series(df)
    df['GRANDTOTAL'] = get_sales_amount_series(df)
    
    # QTY
    qty_candidates = ['TRD_QTY', 'DI_QTY', 'QTY', 'QUANTITY', 'AMOUNT_QTY', 'TOTAL_QTY', 'จำนวน']
    df_cols_upper = {str(c).strip().replace('\ufeff', '').upper(): c for c in df.columns}
    df['QTY'] = 1.0
    for col in qty_candidates:
        col_u = col.upper()
        if col_u in df_cols_upper:
            df['QTY'] = clean_numeric(df[df_cols_upper[col_u]])
            break

    return df

def load_all_sales_data():
    """โหลดข้อมูลยอดขายหลักจากไฟล์ในโฟลเดอร์ปัจจุบัน"""
    folder_path = "."
    if not os.path.exists(folder_path):
        return pd.DataFrame()
    
    files = os.listdir(folder_path)
    all_data_files = [f for f in files if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
    
    if not all_data_files:
        return pd.DataFrame()
        
    sales_files = [f for f in all_data_files if 'product' not in f.lower() and 'bplus' not in f.lower()]
    if not sales_files:
        sales_files = all_data_files

    dfs = []
    for f in sales_files:
        file_path = os.path.join(folder_path, f)
        try:
            if f.lower().endswith('.csv'):
                try: df = pd.read_csv(file_path, encoding='utf-8-sig', low_memory=False)
                except:
                    try: df = pd.read_csv(file_path, encoding='tis-620', low_memory=False)
                    except: df = pd.read_csv(file_path, encoding='cp838', low_memory=False)
            else:
                df = pd.read_excel(file_path)
            
            df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
            df = parse_date_column(df)
            df['GRANDTOTAL'] = get_sales_amount_series(df)
            df['NAME'] = get_branch_series(df)
            df['FILE_SOURCE'] = f
            
            dfs.append(df)
        except Exception:
            continue
            
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def load_bplus_data_from_folder():
    """โหลดข้อมูลสำหรับ Tab สินค้าขายดี"""
    folder_path = "."
    if not os.path.exists(folder_path):
        return pd.DataFrame()
    
    files = os.listdir(folder_path)
    bplus_files = [f for f in files if 'bplus' in f.lower() and f.lower().endswith(('.csv', '.xlsx', '.xls'))]
    
    if not bplus_files:
        return pd.DataFrame()
    
    dfs = []
    for f in bplus_files:
        file_path = os.path.join(folder_path, f)
        try:
            if f.lower().endswith('.csv'):
                try: df = pd.read_csv(file_path, encoding='utf-8-sig', low_memory=False)
                except: df = pd.read_csv(file_path, encoding='tis-620', low_memory=False)
            else:
                df = pd.read_excel(file_path)
            
            df = process_product_dataframe(df)
            dfs.append(df)
        except Exception:
            continue
            
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

# ==========================================
# 3. HEADER & TOP LOGO
# ==========================================
col_header, col_space = st.columns([2.5, 1.5])

with col_header:
    col_img, col_txt = st.columns([1, 4])
    with col_img:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=100)
        else:
            st.markdown("### 🍜")
    with col_txt:
        st.markdown(
            """
            <div style="display: flex; align-items: center; height: 100%; padding-top: 12px;">
                <h2 style="color: #2b9e3e; font-weight: 800; font-size: 26px; margin: 0; line-height: 1.2;">
                    PK NOODLE SHOP COMPANY LIMITED
                </h2>
            </div>
            """, 
            unsafe_allow_html=True
        )

st.markdown('<div class="trick-banner">🧮 <b>ทริค:</b> เมนูกรองข้อมูลอยู่ด้านซ้ายมือ (หากซ่อนอยู่ให้กดปุ่ม > เพื่อเปิด)</div>', unsafe_allow_html=True)

# ==========================================
# 4. LOAD & FILTER MAIN DATA
# ==========================================
df_sales = load_all_sales_data()

# --- SIDEBAR FILTERS ---
st.sidebar.markdown("### 🔍 เมนูกรองข้อมูล")

# 1. กรองปี
available_years = sorted([int(y) for y in df_sales['Year_BE'].dropna().unique()], reverse=True) if not df_sales.empty and 'Year_BE' in df_sales.columns and df_sales['Year_BE'].notna().any() else [2569, 2568]
selected_years = st.sidebar.multiselect("📅 เลือกปี พ.ศ.:", options=available_years, default=available_years)

# 2. กรองช่วงเวลาด่วน
quick_time = st.sidebar.selectbox("เลือกช่วงเวลาแบบด่วน:", ["ดูข้อมูลทั้งหมด", "วันนี้", "เมื่อวาน", "7 วันล่าสุด", "30 วันล่าสุด", "เดือนนี้", "กำหนดเอง (เลือกปฏิทิน)"])
start_date, end_date = None, None
if quick_time == "กำหนดเอง (เลือกปฏิทิน)":
    date_range = st.sidebar.date_input("เลือกช่วงวันที่:", [])
    if len(date_range) == 2:
        start_date, end_date = date_range[0], date_range[1]

# 3. กรองสาขา
available_branches = sorted(list(df_sales['NAME'].dropna().unique())) if not df_sales.empty and 'NAME' in df_sales.columns else []
selected_branches = st.sidebar.multiselect("🏪 เลือกสาขา:", options=available_branches, default=available_branches)

# ประมวลผลการกรองข้อมูล
df_filtered = df_sales.copy()

if not df_filtered.empty:
    if selected_years and 'Year_BE' in df_filtered.columns and df_filtered['Year_BE'].notna().any():
        df_filtered = df_filtered[df_filtered['Year_BE'].isin(selected_years)]
    if selected_branches and 'NAME' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['NAME'].isin(selected_branches)]
    
    if quick_time != "ดูข้อมูลทั้งหมด" and 'Parsed_Date' in df_filtered.columns and not df_filtered['Parsed_Date'].isna().all():
        current_time_th = datetime.utcnow() + timedelta(hours=7)
        today_date = current_time_th.date()
        if quick_time == "วันนี้":
            df_filtered = df_filtered[df_filtered['Parsed_Date'].dt.date == today_date]
        elif quick_time == "เมื่อวาน":
            df_filtered = df_filtered[df_filtered['Parsed_Date'].dt.date == (today_date - timedelta(days=1))]
        elif quick_time == "7 วันล่าสุด":
            df_filtered = df_filtered[df_filtered['Parsed_Date'].dt.date >= (today_date - timedelta(days=7))]
        elif quick_time == "30 วันล่าสุด":
            df_filtered = df_filtered[df_filtered['Parsed_Date'].dt.date >= (today_date - timedelta(days=30))]
        elif quick_time == "เดือนนี้":
            df_filtered = df_filtered[(df_filtered['Parsed_Date'].dt.month == today_date.month) & (df_filtered['Parsed_Date'].dt.year == today_date.year)]
        elif quick_time == "กำหนดเอง (เลือกปฏิทิน)" and start_date and end_date:
            df_filtered = df_filtered[(df_filtered['Parsed_Date'].dt.date >= start_date) & (df_filtered['Parsed_Date'].dt.date <= end_date)]

# ==========================================
# 5. MAIN METRICS DISPLAY
# ==========================================
total_sales = df_filtered['GRANDTOTAL'].sum() if not df_filtered.empty else 0.0
total_bills = len(df_filtered) if not df_filtered.empty else 0
avg_per_bill = total_sales / total_bills if total_bills > 0 else 0.0

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">ยอดขายรวมทั้งหมด (บาท)</div><div class="metric-value">฿{total_sales:,.2f}</div></div>', unsafe_allow_html=True)
with col_m2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">จำนวนรายการ (บิล)</div><div class="metric-value">{total_bills:,.0f}</div></div>', unsafe_allow_html=True)
with col_m3:
    st.markdown(f'<div class="metric-card"><div class="metric-title">ยอดเฉลี่ยต่อบิล (บาท)</div><div class="metric-value">฿{avg_per_bill:,.2f}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 6. VISUALIZATION FUNCTIONS
# ==========================================
def render_branch_visualizations(df_source):
    """วาดกราฟแท่งและกราฟโดนัทประจำสาขา"""
    if df_source.empty or df_source['GRANDTOTAL'].sum() == 0:
        st.info("ไม่พบข้อมูลยอดขาย หรือยอดขายเป็น 0.00 (โปรดตรวจสอบไฟล์ข้อมูล)")
        return

    branch_summary = df_source.groupby('NAME')['GRANDTOTAL'].sum().reset_index()
    branch_summary = branch_summary[branch_summary['GRANDTOTAL'] > 0]
    branch_summary = branch_summary.sort_values(by='GRANDTOTAL', ascending=False)
    
    if branch_summary.empty:
        st.info("ไม่พบข้อมูลยอดขายสำหรับสาขาที่เลือก")
        return

    c_bar, c_donut = st.columns([1.2, 1])
    
    with c_bar:
        st.markdown("##### ยอดขาย (กราฟแท่ง)")
        fig_bar = px.bar(
            branch_summary, 
            x='NAME', 
            y='GRANDTOTAL', 
            color='NAME', 
            text='GRANDTOTAL', 
            color_discrete_map=branch_color_map
        )
        fig_bar.update_traces(texttemplate='฿%{text:,.2f}', textposition='outside', cliponaxis=False)
        fig_bar.update_layout(
            xaxis_title="", 
            yaxis_title="ยอดขาย (บาท)", 
            showlegend=False, 
            height=400, 
            margin=dict(l=20, r=20, t=30, b=20), 
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with c_donut:
        st.markdown("##### สัดส่วนยอดขาย (กราฟโดนัท)")
        fig_donut = px.pie(
            branch_summary, 
            values='GRANDTOTAL', 
            names='NAME', 
            color='NAME',
            hole=0.5, 
            color_discrete_map=branch_color_map
        )
        fig_donut.update_traces(textinfo='percent+label', insidetextorientation='radial')
        fig_donut.update_layout(
            showlegend=True, 
            height=400, 
            margin=dict(l=20, r=20, t=30, b=20), 
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_donut, use_container_width=True)

# ==========================================
# 7. TABS NAVIGATION
# ==========================================
tab_branch, tab_trend, tab_table, tab_bestseller = st.tabs([
    "🏢 ยอดรวมสาขา", 
    "📈 เทรนด์รายวัน", 
    "📋 ตารางตัวเลข", 
    "🍜 สินค้าขายดี"
])

# --- TAB 1: ยอดรวมสาขา ---
with tab_branch:
    if not df_filtered.empty:
        render_branch_visualizations(df_filtered)
    else:
        st.info("ไม่พบข้อมูลยอดขาย (ภายใต้เงื่อนไขการกรองปัจจุบัน)")

# --- TAB 2: เทรนด์รายวัน ---
with tab_trend:
    st.markdown("##### 📈 แนวโน้มยอดขายรายวัน")
    if not df_filtered.empty and 'Parsed_Date' in df_filtered.columns and not df_filtered['Parsed_Date'].isna().all():
        valid_dates = df_filtered[df_filtered['Parsed_Date'].notna()]
        daily_sales = valid_dates.groupby(valid_dates['Parsed_Date'].dt.date)['GRANDTOTAL'].sum().reset_index()
        daily_sales.columns = ['วันที่', 'ยอดขาย']
        daily_sales = daily_sales.sort_values('วันที่')
        
        fig_line = px.line(daily_sales, x='วันที่', y='ยอดขาย', markers=True, line_shape='linear')
        fig_line.update_traces(line_color='#2b9e3e', line_width=3)
        fig_line.update_layout(height=400, xaxis_title="วันที่", yaxis_title="ยอดขาย (บาท)", plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลวันที่ในการประมวลผลเทรนด์รายวัน")

# --- TAB 3: ตารางตัวเลข ---
with tab_table:
    st.markdown("##### 📋 ตารางสรุปยอดขายแยกตามสาขา")
    if not df_filtered.empty:
        branch_table = df_filtered.groupby('NAME').agg(
            ยอดขายรวม=('GRANDTOTAL', 'sum'),
            จำนวนบิล=('GRANDTOTAL', 'count')
        ).reset_index()
        
        branch_table['ยอดเฉลี่ยต่อบิล'] = branch_table.apply(
            lambda r: r['ยอดขายรวม'] / r['จำนวนบิล'] if r['จำนวนบิล'] > 0 else 0.0, axis=1
        )
        branch_table = branch_table.sort_values(by='ยอดขายรวม', ascending=False)
        branch_table.columns = ['สาขา', 'ยอดขายรวม (บาท)', 'จำนวนบิล', 'ยอดเฉลี่ยต่อบิล (บาท)']
        
        st.dataframe(
            branch_table.style.format({
                'ยอดขายรวม (บาท)': '฿{:,.2f}',
                'จำนวนบิล': '{:,.0f}',
                'ยอดเฉลี่ยต่อบิล (บาท)': '฿{:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("ไม่พบข้อมูลสำหรับการแสดงตาราง")

# --- TAB 4: สินค้าขายดี ---
with tab_bestseller:
    st.markdown("##### 🍜 รายงานสินค้าขายดี")
    
    df_product = load_bplus_data_from_folder()
    
    if df_product.empty:
        st.info("💡 หากไม่พบไฟล์ BPLUS ในระบบ สามารถเลือกอัปโหลดไฟล์ BPLUS (.csv หรือ .xlsx) ตรงนี้เพื่อประมวลผลทันทีได้ครับ")
        uploaded_pfile = st.file_uploader(
            "📂 เลือกอัปโหลดไฟล์ BPLUS (.csv หรือ .xlsx):", 
            type=['csv', 'xlsx', 'xls'],
            key="bplus_file_uploader"
        )
        if uploaded_pfile is not None:
            try:
                if uploaded_pfile.name.lower().endswith('.csv'):
                    try: df_raw = pd.read_csv(uploaded_pfile, encoding='utf-8-sig', low_memory=False)
                    except: df_raw = pd.read_csv(uploaded_pfile, encoding='tis-620', low_memory=False)
                else:
                    df_raw = pd.read_excel(uploaded_pfile)
                df_product = process_product_dataframe(df_raw)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

    if not df_product.empty:
        df_p_filtered = df_product.copy()
        
        if selected_branches and 'NAME' in df_p_filtered.columns:
            matched_p = df_p_filtered[df_p_filtered['NAME'].isin(selected_branches)]
            if not matched_p.empty:
                df_p_filtered = matched_p
        
        if selected_years and 'Year_BE' in df_p_filtered.columns and not df_p_filtered['Year_BE'].isna().all():
            matched_y = df_p_filtered[df_p_filtered['Year_BE'].isin(selected_years)]
            if not matched_y.empty:
                df_p_filtered = matched_y

        possible_p_cols = [
            'TRD_SH_NAME', 'DI_PRD_NAME', 'GOODS_NAME', 'DI_NAME', 'PRD_NAME', 'GOODSNAME', 
            'GOODS_DESC', 'ARTICLE_NAME', 'SHOW_NAME', 'PDATA_NAME', 'PRODUCT_NAME', 
            'P_NAME', 'NAME_1', 'ชื่อสินค้า', 'PRODUCT', 'ITEM_NAME', 'DESCR', 
            'ITEMNAME', 'DESCRIPTION', 'TITLE', 'สินค้า', 'รายการ', 'ชื่อรายการ', 'NAME_TH'
        ]
        p_col = next((c for c in possible_p_cols if c in df_p_filtered.columns), None)

        if not p_col:
            str_cols = [c for c in df_p_filtered.columns if c not in ['GRANDTOTAL', 'QTY', 'Year_BE', 'Parsed_Date', 'HAS_BRANCH_COL']]
            if str_cols:
                p_col = str_cols[0]

        if p_col and not df_p_filtered.empty:
            top_products = df_p_filtered.groupby(p_col).agg(
                total_sales=('GRANDTOTAL', 'sum'),
                total_qty=('QTY', 'sum')
            ).reset_index()
            top_products.columns = ['ชื่อสินค้า', 'ยอดขายรวม', 'จำนวนที่ขาย']
            top_products = top_products[top_products['ยอดขายรวม'] > 0]
            
            top_products = top_products.sort_values(by='จำนวนที่ขาย', ascending=False).head(20).reset_index(drop=True)
            top_products.insert(0, 'ลำดับ', range(1, len(top_products) + 1))
            
            if not top_products.empty:
                col_b1, col_b2 = st.columns([1.3, 1])
                with col_b1:
                    st.markdown("###### Top 10 สินค้าขายดีที่สุด (ยอดขาย)")
                    
                    df_top10_chart = top_products.sort_values(by='ยอดขายรวม', ascending=True).tail(10)
                    max_sales = df_top10_chart['ยอดขายรวม'].max()
                    
                    fig_pbar = px.bar(
                        df_top10_chart,
                        y='ชื่อสินค้า',
                        x='ยอดขายรวม',
                        orientation='h',
                        text='ยอดขายรวม',
                        color='ชื่อสินค้า',
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    
                    fig_pbar.update_traces(
                        texttemplate='฿%{text:,.2f}', 
                        textposition='outside', 
                        cliponaxis=False
                    )
                    
                    fig_pbar.update_layout(
                        xaxis_title="ยอดขาย (บาท)", 
                        yaxis_title="", 
                        height=430, 
                        margin=dict(l=10, r=90, t=20, b=20), 
                        showlegend=False,
                        plot_bgcolor='rgba(0,0,0,0)', 
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    
                    fig_pbar.update_xaxes(range=[0, max_sales * 1.25])
                    st.plotly_chart(fig_pbar, use_container_width=True)

                with col_b2:
                    st.markdown("###### ตารางรายละเอียดสินค้าขายดี 20 อันดับแรก")
                    
                    st.dataframe(
                        top_products.style.format({'ยอดขายรวม': '฿{:,.2f}', 'จำนวนที่ขาย': '{:,.0f}'}),
                        use_container_width=True, 
                        height=430,
                        hide_index=True
                    )
            else:
                st.info("ไม่พบรายการสินค้าที่มียอดขายมากกว่า 0 บาท")
        else:
            st.info("ไม่พบข้อมูลสินค้าในการประมวลผล")
