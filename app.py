import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from PyPDF2 import PdfWriter, PdfReader

# --- 1. PDF GENERATOR ENGINE (RESTORED BRANDING & MULTI-ROW) ---
def generate_voucher_pdf(v_no, v_type, date, party, ref, desc, entries_list):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- COMPANY BRANDING (RESTORED) ---
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.1, 0.2, 0.5)
    c.drawString(50, height - 50, "ETHICAL TEAS PRIVATE LTD.")
    
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(50, height - 65, "153/B, Hulangamuwa Road")
    c.drawString(50, height - 75, "Matale, Sri Lanka | Tel: +9466 313 8467")
    c.drawString(50, height - 85, "Email: info@ethicteas.com")
    
    # Graphic Logo
    c.rect(480, height - 85, 50, 50, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(492, height - 75, "E")
    
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(50, height - 100, 550, height - 100)

    # --- VOUCHER HEADER ---
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
    c.drawString(60, y - 10, "Account Name & Description")
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
        
        # Line-level description
        if entry.get('description'):
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

# Database Connection
try:
    DB_URL = st.secrets["connections"]["postgresql"]["url"]
    engine = create_engine(DB_URL)
except Exception as e:
    st.error("Database Connection Failed!")
    st.stop()

# Helper Functions
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
        last_val = filtered['voucher_no'].iloc[0]
        last_num = int(last_val.split("-")[1])
        return f"{prefix}-{last_num + 1:03d}"
    except: return f"{prefix}-001"

# Load Data
df = load_ledger()
account_list = load_accounts()

# --- 3. NAVIGATION ---
menu = st.sidebar.radio("Main Menu", ["Entry Module", "General Ledger", "Trial Balance", "Settings / Import"])

# ... (PDF function and database setup above) ...

# --- MODULE: SETTINGS / IMPORT ---
if menu == "Settings / Import":
    st.title("⚙️ Admin Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Download Template")
        template_data = pd.DataFrame({
            'account_name': ['Cash in Hand', 'Bank Account', 'Sales Revenue', 'Rent Expense'],
            'account_type': ['Asset', 'Asset', 'Revenue', 'Expense']
        })
        template_csv = template_data.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV Template", data=template_csv, file_name="coa_template.csv", mime="text/csv")
    
    with col2:
        st.subheader("2. Reset Database")
        if st.button("🗑️ Clear All Accounts"):
            with engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE chart_of_accounts RESTART IDENTITY CASCADE"))
                conn.commit()
            st.warning("Chart of Accounts cleared!")
            st.rerun()

    st.divider()
    st.subheader("3. Upload Chart of Accounts")
    uploaded_file = st.file_uploader("Choose your formatted CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            import_df = pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            import_df = pd.read_csv(uploaded_file, encoding='latin-1')
        
        import_df = import_df.dropna(subset=['account_name'])
        st.write("Preview:", import_df.head())
        
        if st.button("🚀 Push to Database"):
            try:
                import_df.to_sql('chart_of_accounts', engine, if_exists='append', index=False)
                st.success(f"Imported {len(import_df)} accounts!")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed. Duplicate names might be present.")

# --- MODULE: ENTRY MODULE ---
elif menu == "Entry Module":
    st.title("⚖️ Multi-Row Transaction Entry")
    # ... rest of your entry module code ...
    if not account_list:
        st.warning("Please import Chart of Accounts first.")
        st.stop()

    v_type = st.selectbox("Transaction Type", ["Payment Voucher", "Cash Receipt", "Sales Entry", "Journal Entry"])
    v_no = get_next_v(v_type)
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        date = c1.date_input("Date", datetime.now())
        party = c2.text_input("Payee/Customer")
        ref = c3.text_input("Reference/Ref")
        desc = st.text_area("General Remarks")

    st.markdown("### Transaction Lines")
    # Initial setup for the data editor
    if "editor_rows" not in st.session_state:
        st.session_state.editor_rows = [{"account": None, "description": "", "debit": 0.0, "credit": 0.0}] * 2

    edited_df = st.data_editor(
        st.session_state.editor_rows, 
        column_config={
            "account": st.column_config.SelectboxColumn("Account", options=account_list, required=True),
            "debit": st.column_config.NumberColumn("Debit", min_value=0, format="%.2f"),
            "credit": st.column_config.NumberColumn("Credit", min_value=0, format="%.2f"),
            "description": st.column_config.TextColumn("Line Note")
        }, 
        num_rows="dynamic", 
        use_container_width=True, 
        key="ed_form"
    )

    lines_df = pd.DataFrame(edited_df)
    total_dr = lines_df['debit'].sum()
    total_cr = lines_df['credit'].sum()
    diff = round(total_dr - total_cr, 2)
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total DR", f"{total_dr:,.2f}")
    m2.metric("Total CR", f"{total_cr:,.2f}")
    m3.metric("Balance", f"{diff:,.2f}", delta=diff, delta_color="inverse")
    
    if st.button("🚀 Post Transaction"):
        if diff == 0 and total_dr > 0:
            final_entries = []
            for _, r in lines_df.iterrows():
                if (r['debit'] > 0 or r['credit'] > 0) and r['account'] is not None:
                    final_entries.append({
                        'voucher_no': v_no, 
                        'tr_type': v_type, 
                        'tr_date': date, 
                        'party': party,
                        'ref_no': ref, 
                        'description': r['description'] if r['description'] else desc,
                        'account_name': r['account'], 
                        'debit': r['debit'], 
                        'credit': r['credit']
                    })
            
            try:
                pd.DataFrame(final_entries).to_sql('general_ledger', engine, if_exists='append', index=False)
                # Store data for the PDF generator
                st.session_state['last_post'] = {
                    'v_no': v_no, 'v_type': v_type, 'date': date, 
                    'party': party, 'ref': ref, 'desc': desc, 
                    'lines': final_entries
                }
                st.success(f"Voucher {v_no} Posted Successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"SQL Error: {e}")
        else:
            st.error("Entry is out of balance or missing account names.")

    # Show PDF button after posting
    if 'last_post' in st.session_state and st.session_state['last_post'] is not None:
        lp = st.session_state['last_post']
        
        pdf_file = generate_voucher_pdf(
            v_no=lp['v_no'], 
            v_type=lp['v_type'], 
            date=lp['date'], 
            party=lp['party'], 
            ref=lp['ref'], 
            desc=lp['desc'], 
            entries_list=lp['lines']
        )
        
        st.download_button(
            label=f"🖨️ Download Voucher {lp['v_no']}", 
            data=pdf_file, 
            file_name=f"Voucher_{lp['v_no']}.pdf", 
            mime="application/pdf", 
            use_container_width=True
        )
        
        if st.button("New Entry"):
            st.session_state['last_post'] = None
            st.rerun()
# --- MODULE: GENERAL LEDGER ---
elif menu == "General Ledger":
    st.title("📖 General Ledger Archive")
    c1, c2 = st.columns(2)
    s_date = c1.date_input("From", value=datetime(datetime.now().year, datetime.now().month, 1))
    e_date = c2.date_input("To", value=datetime.now())
    
    # Filtering
    df['tr_date'] = pd.to_datetime(df['tr_date']).dt.date
    filtered_df = df[(df['tr_date'] >= s_date) & (df['tr_date'] <= e_date)]
    
    st.subheader("Bulk Print Selection")
    vouchers = filtered_df['voucher_no'].unique()
    to_print = st.multiselect("Select Vouchers to Export", vouchers)
    
    if st.button("Generate Combined PDF") and to_print:
        writer = PdfWriter()
        for v in to_print:
            v_data = filtered_df[filtered_df['voucher_no'] == v]
            meta = v_data.iloc[0]
            entries = v_data[['account_name', 'debit', 'credit', 'description']].to_dict('records')
            pdf_b = generate_voucher_pdf(v, meta['tr_type'], meta['tr_date'], meta['party'], meta['ref_no'], meta['description'], entries)
            writer.add_page(PdfReader(pdf_b).pages[0])
        
        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        st.download_button("📥 Download Combined PDF", out, "bulk_vouchers.pdf", "application/pdf")

    st.divider()
    st.dataframe(filtered_df, use_container_width=True)

# --- MODULE: TRIAL BALANCE ---
elif menu == "Trial Balance":
    st.title("📊 Trial Balance")
    if not df.empty:
        tb = df.groupby('account_name')[['debit', 'credit']].sum()
        tb['Net Balance'] = tb['debit'] - tb['credit']
        st.dataframe(tb, use_container_width=True)
        
        dr_sum, cr_sum = tb['debit'].sum(), tb['credit'].sum()
        st.metric("Ledger Balance Status", "Balanced" if round(dr_sum,2) == round(cr_sum,2) else "Imbalanced", delta=round(dr_sum-cr_sum,2))
    else: st.warning("No data.")

# --- MODULE: SETTINGS ---
elif menu == "Settings / Import":
    st.title("⚙️ Administration")
    
    with st.expander("Dangerous: Database Reset"):
        if st.button("🗑️ Wipe All Chart of Accounts"):
            with engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE chart_of_accounts RESTART IDENTITY CASCADE"))
                conn.commit()
            st.rerun()

    st.subheader("Import Chart of Accounts")
    up_file = st.file_uploader("Upload CSV", type="csv")
    if up_file:
        import_df = pd.read_csv(up_file).dropna(subset=['account_name'])
        st.dataframe(import_df.head())
        if st.button("🚀 Confirm Upload"):
            import_df.to_sql('chart_of_accounts', engine, if_exists='append', index=False)
            st.success("Accounts Added!")
