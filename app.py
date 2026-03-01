import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from PyPDF2 import PdfWriter, PdfReader

# --- 1. PDF GENERATOR ENGINE (MULTI-ROW VERSION) ---
def generate_voucher_pdf(v_no, v_type, date, party, ref, desc, entries_list):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- COMPANY BRANDING ---
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.1, 0.2, 0.5)
    c.drawString(50, height - 50, "ETHICAL TEAS PRIVATE LTD.")
    
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(50, height - 65, "153/B, Hulangamuwa Road")
    c.drawString(50, height - 75, "Matale, Sri Lanka | Tel: +9466 313 8467")
    c.drawString(50, height - 85, "Email: info@ethicteas.com")
    
    # Simple Graphic Logo
    c.rect(480, height - 85, 50, 50, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(492, height - 75, "E")
    
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(50, height - 100, 550, height - 100)

    # --- VOUCHER DETAILS ---
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2.0, height - 120, f"{v_type.upper()}")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 145, f"Voucher No: {v_no}")
    c.drawString(400, height - 145, f"Date: {date}")
    c.drawString(50, height - 160, f"Party: {party}")
    c.drawString(400, height - 160, f"Ref: {ref}")

    # --- DYNAMIC TABLE ---
    y = height - 190
    c.setFont("Helvetica-Bold", 10)
    c.line(50, y + 5, 550, y + 5)
    c.drawString(60, y - 10, "Account Name & Line Description")
    c.drawRightString(440, y - 10, "Debit")
    c.drawRightString(540, y - 10, "Credit")
    c.line(50, y - 15, 550, y - 15)
    
    y -= 30
    total_dr, total_cr = 0, 0

    c.setFont("Helvetica", 9)
    for entry in entries_list:
        if y < 150:
            c.showPage()
            y = height - 50
        
        c.drawString(60, y, f"{entry['account_name']}")
        c.drawRightString(440, y, f"{entry['debit']:,.2f}")
        c.drawRightString(540, y, f"{entry['credit']:,.2f}")
        
        if entry.get('description') and entry['description'] != "":
            y -= 12
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(70, y, f"- {entry['description']}")
            c.setFont("Helvetica", 9)

        total_dr += entry['debit']
        total_cr += entry['credit']
        y -= 20

    # TOTALS
    c.line(50, y, 550, y)
    c.setFont("Helvetica-Bold", 10)
    y -= 15
    c.drawString(60, y, "TOTAL (LKR)")
    c.drawRightString(440, y, f"{total_dr:,.2f}")
    c.drawRightString(540, y, f"{total_cr:,.2f}")

    # FOOTER
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 150, f"Remarks: {desc}")
    c.line(50, 80, 200, 80)
    c.drawString(50, 65, "Prepared By")
    c.line(350, 80, 500, 80)
    c.drawString(350, 65, "Authorized Signatory")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- 2. CORE APP SETUP ---
st.set_page_config(page_title="Ethical Teas ERP", layout="wide")

try:
    DB_URL = st.secrets["connections"]["postgresql"]["url"]
    engine = create_engine(DB_URL)
except Exception as e:
    st.error("Database Connection Failed!")
    st.stop()

def load_ledger():
    try:
        return pd.read_sql("SELECT * FROM general_ledger ORDER BY tr_date DESC, id DESC", engine)
    except:
        return pd.DataFrame(columns=['voucher_no', 'tr_type', 'tr_date', 'party', 'ref_no', 'description', 'account_name', 'debit', 'credit'])

def load_accounts():
    try:
        return pd.read_sql("SELECT account_name FROM chart_of_accounts ORDER BY account_name ASC", engine)['account_name'].tolist()
    except:
        return []

def get_next_v(v_type):
    df_v = load_ledger()
    prefix = {"Payment Voucher": "PV", "Cash Receipt": "CR", "Sales Entry": "SJ", "Journal Entry": "JV"}.get(v_type, "JV")
    if df_v.empty: return f"{prefix}-001"
    filtered = df_v[df_v['voucher_no'].str.startswith(prefix, na=False)]
    if filtered.empty: return f"{prefix}-001"
    try:
        last_num = int(filtered['voucher_no'].iloc[0].split("-")[1])
        return f"{prefix}-{last_num + 1:03d}"
    except: return f"{prefix}-001"

df = load_ledger()
account_list = load_accounts()

# --- 3. NAVIGATION ---
menu = st.sidebar.radio("Main Menu", ["Entry Module", "General Ledger", "Trial Balance", "Settings / Import"])

# --- MODULE: ENTRY ---
if menu == "Entry Module":
    st.title("⚖️ New Transaction")
    if not account_list:
        st.warning("Import Chart of Accounts first!")
        st.stop()

    v_type = st.selectbox("Type", ["Payment Voucher", "Cash Receipt", "Sales Entry", "Journal Entry"])
    v_no = get_next_v(v_type)
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        date = c1.date_input("Date", datetime.now())
        party = c2.text_input("Payee/Customer")
        ref = c3.text_input("Reference/Ref")
        desc = st.text_area("General Remarks")

    st.markdown("### Ledger Lines")
    init_data = [{"account": None, "description": "", "debit": 0.0, "credit": 0.0}] * 2
    edited_df = st.data_editor(init_data, column_config={
        "account": st.column_config.SelectboxColumn("Account", options=account_list, required=True),
        "debit": st.column_config.NumberColumn("Debit", min_value=0, format="%.2f"),
        "credit": st.column_config.NumberColumn("Credit", min_value=0, format="%.2f")
    }, num_rows="dynamic", use_container_width=True, key="ed")

    lines = pd.DataFrame(edited_df)
    diff = round(lines['debit'].sum() - lines['credit'].sum(), 2)
    
    col_t1, col_t2 = st.columns(2)
    col_t1.metric("Difference", f"{diff:,.2f}", delta=diff, delta_color="inverse")
    
    if st.button("🚀 Post Transaction"):
        if diff == 0 and lines['debit'].sum() > 0:
            final_entries = []
            for _, r in lines.iterrows():
                if r['debit'] > 0 or r['credit'] > 0:
                    final_entries.append({
                        'voucher_no': v_no, 'tr_type': v_type, 'tr_date': date, 'party': party,
                        'ref_no': ref, 'description': r['description'] if r['description'] else desc,
                        'account_name': r['account'], 'debit': r['debit'], 'credit': r['credit']
                    })
            try:
                pd.DataFrame(final_entries).to_sql('general_ledger', engine, if_exists='append', index=False)
                st.session_state['last_post'] = {'meta': (v_no, v_type, date, party, ref, desc), 'lines': final_entries}
                st.success(f"Posted {v_no}")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
        else: st.error("Out of balance or empty!")

    if 'last_post' in st.session_state:
        lp = st.session_state['last_post']
        pdf = generate_voucher_pdf(*lp['meta'], lp['lines'])
        st.download_button("🖨️ Download Last Voucher", pdf, f"{lp['meta'][0]}.pdf", "application/pdf", use_container_width=True)

# --- MODULE: LEDGER ---
elif menu == "General Ledger":
    st.title("📖 General Ledger")
    c1, c2 = st.columns(2)
    s_d = c1.date_input("Start", datetime(datetime.now().year, datetime.now().month, 1))
    e_d = c2.date_input("End", datetime.now())
    
    df['tr_date'] = pd.to_datetime(df['tr_date']).dt.date
    f_df = df[(df['tr_date'] >= s_d) & (df['tr_date'] <= e_d)]
    
    vouchers = f_df['voucher_no'].unique()
    to_print = st.multiselect("Select Vouchers for Bulk Print", vouchers)
    
    if st.button("Generate Bulk PDF") and to_print:
        writer = PdfWriter()
        for v in to_print:
            v_rows = f_df[f_df['voucher_no'] == v]
            m = v_rows.iloc[0]
            entries = v_rows[['account_name', 'debit', 'credit', 'description']].to_dict('records')
            pdf_b = generate_voucher_pdf(v, m['tr_type'], m['tr_date'], m['party'], m['ref_no'], m['description'], entries)
            writer.add_page(PdfReader(pdf_b).pages[0])
        
        combined = io.BytesIO()
        writer.write(combined)
        combined.seek(0)
        st.download_button("📥 Download Bulk PDF", combined, "bulk.pdf", "application/pdf")

    st.dataframe(f_df, use_container_width=True)

# --- MODULE: TRIAL BALANCE ---
elif menu == "Trial Balance":
    st.title("📊 Trial Balance")
    if not df.empty:
        tb = df.groupby('account_name')[['debit', 'credit']].sum()
        tb['Net'] = tb['debit'] - tb['credit']
        st.dataframe(tb, use_container_width=True)
        st.metric("Status", "Balanced" if round(tb['debit'].sum(),2) == round(tb['credit'].sum(),2) else "Error")

# --- MODULE: SETTINGS ---
elif menu == "Settings / Import":
    st.title("⚙️ Settings")
    if st.button("🗑️ Clear Chart of Accounts"):
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE chart_of_accounts RESTART IDENTITY CASCADE"))
            conn.commit()
        st.rerun()
    
    up = st.file_uploader("Upload COA CSV", type="csv")
    if up:
        idf = pd.read_csv(up).dropna(subset=['account_name'])
        if st.button("Push to DB"):
            idf.to_sql('chart_of_accounts', engine, if_exists='append', index=False)
            st.success("Done!")
