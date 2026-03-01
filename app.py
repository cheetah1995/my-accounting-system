import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from PyPDF2 import PdfWriter, PdfReader
# --- SIMPLE LOGIN SYSTEM ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Tharushi@951": # Change this to your secret password
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter Password to Access Ethical Teas ERP", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password Incorrect. Try again.", type="password", on_change=password_entered, key="password")
        return False
    else:
        return True

if not check_password():
    st.stop() # Stops the rest of the app from running until login

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
menu = st.sidebar.radio("Main Menu", ["Dashboard", "Entry Module", "Payroll Management", "General Ledger", "Trial Balance", "Profit & Loss", "Balance Sheet", "Account Statement", "Settings / Import"])
# ... (PDF function and database setup above) ...

# --- MODULE: SETTINGS / IMPORT ---
if menu == "Settings / Import":
    st.title("⚙️ Admin Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Download Template")
        template_data = pd.DataFrame({'account_name': ['Cash in Hand', 'Bank Account', 'Sales Revenue', 'Rent Expense'], 'account_type': ['Asset', 'Asset', 'Revenue', 'Expense']})
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
        except:
            import_df = pd.read_csv(uploaded_file, encoding='latin-1')
        
        if st.button("🚀 Push to Database"):
            import_df.to_sql('chart_of_accounts', engine, if_exists='append', index=False)
            st.success("Imported!")
            st.rerun()

    st.divider()
    st.subheader("💾 System Backup")
    if st.button("📦 Generate Full Backup"):
        try:
            backup_df = pd.read_sql("SELECT * FROM general_ledger", engine)
            st.download_button("⬇️ Download Backup (CSV)", data=backup_df.to_csv(index=False).encode('utf-8'), file_name=f"EthicalTeas_Backup_{datetime.now().date()}.csv", mime="text/csv")
            st.success("Backup Ready!")
        except Exception as e:
            st.error(f"Backup Error: {e}")
# --- MODULE: ENTRY MODULE ---
elif menu == "Entry Module":
    st.title("⚖️ Multi-Row Transaction Entry")
    
    if not account_list:
        st.warning("Please import Chart of Accounts first.")
        st.stop()

    # 1. GENERATE VOUCHER NUMBER (Always visible at top)
    v_type = st.selectbox("Transaction Type", ["Payment Voucher", "Cash Receipt", "Sales Entry", "Journal Entry"])
    v_no = get_next_v(v_type)
    
    st.subheader(f"Document No: {v_no}")

    # 2. RESET LOGIC FOR NEW ENTRIES
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0  # We use this to force-refresh the data_editor

    # Define default empty rows
    default_rows = [{"account": None, "description": "", "debit": 0.0, "credit": 0.0}] * 2

    # 3. HEADER FORM
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        date = c1.date_input("Date", datetime.now())
        party = c2.text_input("Payee/Customer", placeholder="e.g. Supplier Name")
        ref = c3.text_input("Reference/Ref", placeholder="e.g. Inv-001")
        desc = st.text_area("General Remarks", placeholder="Enter overall transaction details...")

    st.markdown("### Transaction Lines")
    
    # 4. DATA EDITOR (Using a dynamic key to allow clearing)
    edited_df = st.data_editor(
        default_rows, 
        column_config={
            "account": st.column_config.SelectboxColumn("Account", options=account_list, required=True),
            "debit": st.column_config.NumberColumn("Debit", min_value=0, format="%.2f"),
            "credit": st.column_config.NumberColumn("Credit", min_value=0, format="%.2f"),
            "description": st.column_config.TextColumn("Line Note")
        }, 
        num_rows="dynamic", 
        use_container_width=True, 
        key=f"editor_{st.session_state.editor_key}" # Changing this key wipes the table
    )

    lines_df = pd.DataFrame(edited_df)
    total_dr = lines_df['debit'].sum()
    total_cr = lines_df['credit'].sum()
    diff = round(total_dr - total_cr, 2)
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total DR", f"{total_dr:,.2f}")
    m2.metric("Total CR", f"{total_cr:,.2f}")
    m3.metric("Balance Status", "Balanced" if diff == 0 else "Out of Balance", delta=diff, delta_color="inverse")
    
    # 5. POSTING LOGIC
    if st.button("🚀 Post Transaction", use_container_width=True):
        if diff == 0 and total_dr > 0:
            final_entries = []
            for _, r in lines_df.iterrows():
                if (r['debit'] > 0 or r['credit'] > 0) and r['account'] is not None:
                    final_entries.append({
                        "tr_date": date,
                        "tr_type": v_type,
                        "voucher_no": v_no,
                        "party": party,
                        "description": r['description'] if r['description'] else desc,
                        "account_name": r['account'],
                        "debit": r['debit'],
                        "credit": r['credit'],
                        "created_by": "Admin", 
                        "created_at": datetime.now(),
                        "is_void": 0
                    })
            
            try:
                pd.DataFrame(final_entries).to_sql('general_ledger', engine, if_exists='append', index=False)
                st.session_state['last_post'] = {'v_no': v_no, 'v_type': v_type, 'date': date, 'party': party, 'ref': ref, 'desc': desc, 'lines': final_entries}
                st.success(f"Successfully Posted {v_no}!")
                st.rerun()
            except Exception as e:
                st.error(f"SQL Error: {e}")
        else:
            st.error("Cannot post: Check if accounts are selected and Debits = Credits.")

    # 6. DOWNLOAD & RESET BUTTONS
    if 'last_post' in st.session_state and st.session_state['last_post'] is not None:
        lp = st.session_state['last_post']
        
        pdf_file = generate_voucher_pdf(
            v_no=lp['v_no'], v_type=lp['v_type'], date=lp['date'], 
            party=lp['party'], ref=lp['ref'], desc=lp['desc'], 
            entries_list=lp['lines']
        )
        
        st.download_button(
            label=f"📥 Download Voucher {lp['v_no']} (PDF)", 
            data=pdf_file, 
            file_name=f"Voucher_{lp['v_no']}.pdf", 
            mime="application/pdf", 
            use_container_width=True
        )
        
        if st.button("➕ Create Another New Entry", type="primary"):
            # This is the "Clear" magic: 
            # 1. Change the key to reset the table
            # 2. Clear the last_post session state
            st.session_state.editor_key += 1 
            st.session_state['last_post'] = None
            st.rerun()
# --- MODULE: GENERAL LEDGER ---
# --- INSIDE GENERAL LEDGER MODULE ---
elif menu == "General Ledger":
    st.title("📖 General Ledger & Audit")

    # Fetch data including our new columns
    query = "SELECT * FROM general_ledger ORDER BY tr_date DESC, voucher_no DESC"
    df_ledger = pd.read_sql(query, engine)

    # Filter out voided transactions for the main view (Optional)
    show_voided = st.checkbox("Show Voided Transactions")
    if not show_voided:
        display_df = df_ledger[df_ledger['is_void'] == 0]
    else:
        display_df = df_ledger

    st.dataframe(display_df, use_container_width=True)

    # --- THE VOID LOGIC ---
    st.divider()
    st.subheader("🛠️ Transaction Actions")
    
    # Let user pick a voucher to void
    vouchers = display_df['voucher_no'].unique()
    selected_v = st.selectbox("Select Voucher to Void", options=vouchers)
    reason = st.text_input("Reason for Voiding", placeholder="e.g., Duplicate entry / Wrong amount")

    if st.button("🚫 Void Transaction", type="secondary"):
        if selected_v:
            try:
                with engine.connect() as conn:
                    # Update the record to is_void = 1
                    sql = text("UPDATE general_ledger SET is_void = 1, void_reason = :res WHERE voucher_no = :vouch")
                    conn.execute(sql, {"res": reason, "vouch": selected_v})
                    conn.commit()
                st.warning(f"Voucher {selected_v} has been successfully voided.")
                st.rerun()
            except Exception as e:
                st.error(f"Voiding failed: {e}")
elif menu == "General Ledger":
    st.title("📖 General Ledger Archive")
    
    # 1. FILTERS
    c1, c2 = st.columns(2)
    s_date = c1.date_input("From", value=datetime(datetime.now().year, datetime.now().month, 1))
    e_date = c2.date_input("To", value=datetime.now())
    
    df['tr_date'] = pd.to_datetime(df['tr_date']).dt.date
    filtered_df = df[(df['tr_date'] >= s_date) & (df['tr_date'] <= e_date)]
    
    # 2. BULK PRINT SECTION
    st.subheader("🖨️ Bulk Print & Export")
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

    # 3. DATA VIEW
    st.subheader("Transaction History")
    st.dataframe(filtered_df, use_container_width=True)

    # 4. DELETE SECTION (New Feature)
    st.divider()
    with st.expander("⚠️ Danger Zone: Delete Voucher"):
        st.warning("Deleting a voucher will remove all its debit and credit lines permanently.")
        v_to_delete = st.selectbox("Select Voucher ID to Delete", options=["None"] + list(vouchers))
        
        if v_to_delete != "None":
            # Show a preview of what's being deleted
            preview = filtered_df[filtered_df['voucher_no'] == v_to_delete]
            st.write("Reviewing entries for deletion:")
            st.table(preview[['account_name', 'debit', 'credit']])
            
            confirm = st.checkbox(f"I confirm I want to delete {v_to_delete}")
            
            if st.button("🗑️ Permanently Delete Voucher"):
                if confirm:
                    try:
                        with engine.connect() as conn:
                            # Use SQLAlchemy text to execute the delete
                            query = text("DELETE FROM general_ledger WHERE voucher_no = :v_no")
                            conn.execute(query, {"v_no": v_to_delete})
                            conn.commit()
                        st.success(f"Voucher {v_to_delete} has been erased.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting: {e}")
                else:
                    st.info("Please check the confirmation box first.")

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
# --- MODULE: PROFIT & LOSS ---
elif menu == "Profit & Loss":
    st.title("📈 Income Statement (Profit & Loss)")
    c1, c2 = st.columns(2)
    s_date = c1.date_input("Start Period", value=datetime(datetime.now().year, datetime.now().month, 1), key="pl_start")
    e_date = c2.date_input("End Period", value=datetime.now(), key="pl_end")
    
    try:
        query = text("""
            SELECT gl.*, coa.account_type 
            FROM general_ledger gl
            LEFT JOIN chart_of_accounts coa ON gl.account_name = coa.account_name
            WHERE gl.is_void = 0
        """)
        full_df = pd.read_sql(query, engine)
        full_df['tr_date'] = pd.to_datetime(full_df['tr_date']).dt.date
        mask = (full_df['tr_date'] >= s_date) & (full_df['tr_date'] <= e_date)
        report_df = full_df.loc[mask]
        
        if report_df.empty:
            st.warning("No transactions found.")
        else:
            rev_df = report_df[report_df['account_type'] == 'Revenue']
            exp_df = report_df[report_df['account_type'] == 'Expense']
            total_revenue = rev_df['credit'].sum() - rev_df['debit'].sum()
            total_expenses = exp_df['debit'].sum() - exp_df['credit'].sum()
            
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Revenue", f"LKR {total_revenue:,.2f}")
            m2.metric("Total Expenses", f"LKR {total_expenses:,.2f}")
            m3.metric("Net Profit", f"LKR {(total_revenue - total_expenses):,.2f}")
    except Exception as e:
        st.error(f"P&L Error: {e}")

# --- MODULE: BALANCE SHEET ---
elif menu == "Balance Sheet":
    st.title("🏦 Balance Sheet")
    as_of_date = st.date_input("As of Date", value=datetime.now(), key="bs_date")
    try:
        query = text("""
            SELECT gl.*, coa.account_type 
            FROM general_ledger gl
            LEFT JOIN chart_of_accounts coa ON gl.account_name = coa.account_name
            WHERE gl.is_void = 0
        """)
        report_df = pd.read_sql(query, engine)
        st.write("Balance Sheet Data Loaded Successfully")
        # (Insert your Balance Sheet category logic here)
    except Exception as e:
        st.error(f"Balance Sheet Error: {e}")

# --- MODULE: ACCOUNT STATEMENT ---
elif menu == "Account Statement":
    st.title("🔍 Account Statement")
    target_account = st.selectbox("Select Account", options=account_list)
    if target_account:
        st.write(f"Showing history for {target_account}")

# --- MODULE: DASHBOARD ---
elif menu == "Dashboard":
    st.title("📊 Executive Dashboard")
    st.write(f"Welcome to Ethical Teas ERP. Today is {datetime.now().strftime('%A, %d %B %Y')}")

# --- MODULE: PAYROLL ---
elif menu == "Payroll Management":
    st.title("👥 Payroll")
    st.info("Payroll module is active. Enter employee details below.")

    # --- COMPANY COST ---
    st.subheader("🏢 Employer Contributions")
    ce1, ce2 = st.columns(2)
    epf_employer = ce1.number_input("Employer EPF (12%)", value=basic_sal * 0.12, disabled=True)
    etf_employer = ce2.number_input("Employer ETF (3%)", value=basic_sal * 0.03, disabled=True)
    
    total_payroll_cost = gross_earnings + epf_employer + etf_employer
    st.success(f"**Total Cost to Company:** LKR {total_payroll_cost:,.2f}")

    st.divider()
    if st.button("🚀 Post Comprehensive Payroll", use_container_width=True):
        if net_salary > 0:
            v_no = get_next_v("Journal Entry")
            
            payroll_entries = [
                # 1. DEBIT: Total Gross Earnings (Includes 'Other Additions')
                {'voucher_no': v_no, 'tr_type': 'Journal Entry', 'tr_date': pay_date, 'party': emp_name,
                 'ref_no': 'PAYROLL', 'description': f'Gross Salary for {emp_name}',
                 'account_name': 'Salary Expense', 'debit': gross_earnings, 'credit': 0},

                # 2. DEBIT: Employer Statutory Cost
                {'voucher_no': v_no, 'tr_type': 'Journal Entry', 'tr_date': pay_date, 'party': 'Gov',
                 'ref_no': 'STAT_COST', 'description': 'Employer EPF/ETF Contribution',
                 'account_name': 'Salary Expense', 'debit': epf_employer + etf_employer, 'credit': 0},

                # 3. CREDIT: Combined EPF/ETF Liability
                {'voucher_no': v_no, 'tr_type': 'Journal Entry', 'tr_date': pay_date, 'party': 'Gov',
                 'ref_no': 'EPF_ETF_PAYABLE', 'description': 'EPF/ETF Liability',
                 'account_name': 'Accrued Expense', 'debit': 0, 'credit': epf_employee + epf_employer + etf_employer},

                # 4. CREDIT: Tax & Other Deductions (APIT, Stamp Duty, and 'Other')
                {'voucher_no': v_no, 'tr_type': 'Journal Entry', 'tr_date': pay_date, 'party': 'IRD/Misc',
                 'ref_no': 'TAX_OTHER_PAYABLE', 'description': 'Tax and Misc Deductions',
                 'account_name': 'Accrued Expense', 'debit': 0, 'credit': apit_tax + stamp_duty + other_ded},

                # 5. CREDIT: Net Cash Out
                {'voucher_no': v_no, 'tr_type': 'Journal Entry', 'tr_date': pay_date, 'party': emp_name,
                 'ref_no': 'BANK_PAYMENT', 'description': f'Net Pay for {emp_name}',
                 'account_name': 'Cash in Hand', 'debit': 0, 'credit': net_salary}
            ]
            
            try:
                pd.DataFrame(payroll_entries).to_sql('general_ledger', engine, if_exists='append', index=False)
                st.success(f"Payroll Posted! Voucher: {v_no}")
                st.rerun()
            except Exception as e:
                st.error(f"Post Failed: {e}")
# --- TEMPORARY DATABASE MIGRATION TOOL ---
if menu == "Settings / Import": # Put it inside your Settings menu
    st.divider()
    if st.button("🛠️ Upgrade Database to Commercial Grade"):
        try:
            with engine.connect() as conn:
                # SQLite commands to add columns
                conn.execute(text("ALTER TABLE general_ledger ADD COLUMN created_by TEXT DEFAULT 'Admin';"))
                conn.execute(text("ALTER TABLE general_ledger ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;"))
                conn.execute(text("ALTER TABLE general_ledger ADD COLUMN is_void INTEGER DEFAULT 0;"))
                conn.execute(text("ALTER TABLE general_ledger ADD COLUMN void_reason TEXT;"))
                conn.commit()
            st.success("Database Schema Updated! You can now remove this code block.")
        except Exception as e:
            st.info(f"Note: Some columns might already exist. Error: {e}")
