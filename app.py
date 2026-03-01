import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

def generate_voucher_pdf(v_no, v_type, date, party, ref, desc, dr_acc, dr_amt, cr_acc, cr_amt):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- COMPANY BRANDING ---
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.1, 0.2, 0.5)  # Dark Blue color for the logo/name
    c.drawString(50, height - 50, "ETHICAL TEAS PRIVATE LTD.")
    
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)  # Grey for address
    c.drawString(50, height - 65, "153/B, Hulangamuwa Road")
    c.drawString(50, height - 75, "Matale, Sri Lanka | Tel: +9466 313 8467")
    c.drawString(50, height - 85, "Email: info@ethicteas.com")
    
    # Simple Graphic Logo (A blue square with 'E' for Company)
    c.rect(480, height - 85, 50, 50, fill=1)
    c.setFillColorRGB(1, 1, 1) # White text
    c.setFont("Helvetica-Bold", 30)
    c.drawString(492, height - 75, "C")
    
    # Divider Line
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(50, height - 100, 550, height - 100)

    # --- VOUCHER DETAILS ---
    c.setFillColorRGB(0, 0, 0) # Back to black
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2.0, height - 130, f"{v_type.upper()}")
    
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 160, f"Voucher No: {v_no}")
    c.drawString(400, height - 160, f"Date: {date}")
    c.drawString(50, height - 180, f"Reference: {ref}")
    c.drawString(50, height - 200, f"Party: {party}")

    # --- TABLE SECTION ---
    # Header Box
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(50, height - 230, 500, 20, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 225, "Account Description")
    c.drawRightString(440, height - 225, "Debit")
    c.drawRightString(540, height - 225, "Credit")
    
    # Table Content
    c.setFont("Helvetica", 10)
    # Row 1 (Debit)
    c.drawString(60, height - 250, f"{dr_acc}")
    c.drawRightString(440, height - 250, f"{dr_amt:,.2f}")
    c.drawRightString(540, height - 250, "0.00")
    
    # Row 2 (Credit)
    c.drawString(60, height - 270, f"{cr_acc}")
    c.drawRightString(440, height - 270, "0.00")
    c.drawRightString(540, height - 270, f"{cr_amt:,.2f}")

    # Total Box
    c.line(50, height - 280, 550, height - 280)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 295, "TOTAL")
    c.drawRightString(440, height - 295, f"{dr_amt:,.2f}")
    c.drawRightString(540, height - 295, f"{cr_amt:,.2f}")

    # --- NARRATION ---
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, height - 330, f"Narration: {desc}")

    # --- SIGNATURES ---
    c.setFont("Helvetica", 9)
    c.line(50, 150, 200, 150)
    c.drawString(50, 135, "Prepared By")
    
    c.line(350, 150, 500, 150)
    c.drawString(350, 135, "Authorized Signatory")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
# PAGE CONFIG
st.set_page_config(page_title="SQL ERP Pro", layout="wide")

# 1. DATABASE CONNECTION
try:
    DB_URL = st.secrets["connections"]["postgresql"]["url"]
    engine = create_engine(DB_URL)
except Exception as e:
    st.error("Database connection configuration missing!")
    st.stop()

# 2. DATA LOADERS
def load_ledger():
    try:
        # We order by ID desc to ensure the latest entries appear first
        return pd.read_sql("SELECT * FROM general_ledger ORDER BY tr_date DESC, id DESC", engine)
    except:
        return pd.DataFrame(columns=['voucher_no', 'tr_type', 'tr_date', 'party', 'ref_no', 'description', 'account_name', 'debit', 'credit'])

def load_accounts():
    try:
        df_accounts = pd.read_sql("SELECT account_name FROM chart_of_accounts ORDER BY account_name ASC", engine)
        return df_accounts['account_name'].tolist()
    except:
        return []

# Load initial data
df = load_ledger()
account_list = load_accounts()

# 3. VOUCHER GENERATOR LOGIC
def get_next_v(v_type):
    prefix_map = {"Payment Voucher": "PV", "Cash Receipt": "CR", "Sales Entry": "SJ", "Journal Entry": "JV"}
    prefix = prefix_map.get(v_type, "JV")
    
    if df.empty:
        return f"{prefix}-001"
    
    filtered = df[df['voucher_no'].str.startswith(prefix, na=False)]
    if filtered.empty:
        return f"{prefix}-001"
    
    try:
        # Extract number from the latest voucher (e.g., 'PV-005' -> 5)
        last_val = filtered['voucher_no'].iloc[0]
        last_num = int(last_val.split("-")[1])
        return f"{prefix}-{last_num + 1:03d}"
    except:
        return f"{prefix}-001"

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Main Menu", ["Entry Module", "General Ledger", "Trial Balance", "Settings / Import"])

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
            # Try standard UTF-8
            import_df = pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            # Fallback for Excel/Latin-1 encoding
            uploaded_file.seek(0)
            import_df = pd.read_csv(uploaded_file, encoding='latin-1')
        
        # Clean data
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
    st.title("⚖️ New Transaction")
    
    if not account_list:
        st.warning("⚠️ Please import your Chart of Accounts first.")
        st.stop()

    v_type = st.selectbox("Transaction Type", ["Payment Voucher", "Cash Receipt", "Sales Entry", "Journal Entry"])
    v_no = get_next_v(v_type)
    
    st.subheader(f"Document No: {v_no}")

    # 1. CREATE THE FORM
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        date = c1.date_input("Date", datetime.now())
        party = c1.text_input("Payee/Customer")
        ref = c2.text_input("Reference")
        desc = c2.text_area("Description")

        st.markdown("---")
        dr_acc = st.selectbox("Debit Account", options=account_list, index=None, placeholder="Search...")
        dr_amt = st.number_input("Debit Amount", min_value=0.0, format="%.2f")
        
        cr_acc = st.selectbox("Credit Account", options=account_list, index=None, placeholder="Search...")
        cr_amt = st.number_input("Credit Amount", min_value=0.0, format="%.2f")

        submit_button = st.form_submit_button("Post Entry")

    # 2. HANDLE SUBMISSION (Outside the form)
    if submit_button:
        if dr_amt == cr_amt and dr_amt > 0 and dr_acc and cr_acc:
            new_entries = pd.DataFrame([
                {'voucher_no': v_no, 'tr_type': v_type, 'tr_date': date, 'party': party, 'ref_no': ref, 'description': desc, 'account_name': dr_acc, 'debit': dr_amt, 'credit': 0.0},
                {'voucher_no': v_no, 'tr_type': v_type, 'tr_date': date, 'party': party, 'ref_no': ref, 'description': desc, 'account_name': cr_acc, 'debit': 0.0, 'credit': cr_amt}
            ])
            
            try:
                new_entries.to_sql('general_ledger', engine, if_exists='append', index=False)
                
                # We store the data in session_state so the button can use it
                st.session_state['last_post'] = {
                    'v_no': v_no, 'v_type': v_type, 'date': date, 'party': party, 
                    'ref': ref, 'desc': desc, 'dr_acc': dr_acc, 'dr_amt': dr_amt, 
                    'cr_acc': cr_acc, 'cr_amt': cr_amt
                }
                st.success(f"Successfully Posted {v_no}!")
            except Exception as e:
                st.error(f"Database Error: {e}")
        else:
            st.error("Error: Check balance and ensure accounts are selected.")

    # 3. SHOW DOWNLOAD BUTTON (Only if a post was successful)
    if 'last_post' in st.session_state:
        lp = st.session_state['last_post']
        pdf_data = generate_voucher_pdf(
            lp['v_no'], lp['v_type'], lp['date'], lp['party'], 
            lp['ref'], lp['desc'], lp['dr_acc'], lp['dr_amt'], 
            lp['cr_acc'], lp['cr_amt']
        )
        
        st.download_button(
            label=f"🖨️ Download Voucher {lp['v_no']}",
            data=pdf_data,
            file_name=f"Voucher_{lp['v_no']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        if st.button("Start New Entry"):
            del st.session_state['last_post']
            st.rerun()

# --- MODULE: GENERAL LEDGER ---
elif menu == "General Ledger":
    st.title("📖 General Ledger & Print History")
    
    if df.empty:
        st.info("The ledger is empty.")
    else:
        # Create a 'Select' column for checkboxes
        st.subheader("Select Vouchers to Print")
        
        # Get unique vouchers for the selection list
        unique_vouchers = df[['voucher_no', 'tr_date', 'party', 'tr_type']].drop_duplicates()
        
        # Display selection table
        selected_rows = st.data_editor(
            unique_vouchers,
            column_config={"Select": st.column_config.CheckboxColumn(default=False)},
            disabled=["voucher_no", "tr_date", "party", "tr_type"],
            use_container_width=True,
            key="bulk_print_editor"
        )
        
        # Filter for the ones the user checked (Data Editor returns the whole DF)
        # Note: We assume the user clicks the 'Select' column if you add it, 
        # but for simplicity, let's use a multi-select box:
        
        to_print = st.multiselect("Pick Vouchers to Export", options=unique_vouchers['voucher_no'].tolist())
        
        if st.button("🖨️ Generate Bulk PDF"):
            if not to_print:
                st.warning("Please select at least one voucher.")
            else:
                from PyPDF2 import PdfWriter, PdfReader
                combined_pdf = PdfWriter()
                
                for v_no in to_print:
                    # Get the data for this specific voucher
                    v_data = df[df['voucher_no'] == v_no]
                    # Since one voucher has two rows (DR/CR), we pick the details from the first row
                    row_dr = v_data[v_data['debit'] > 0].iloc[0]
                    row_cr = v_data[v_data['credit'] > 0].iloc[0]
                    
                    pdf_buffer = generate_voucher_pdf(
                        v_no=v_no,
                        v_type=row_dr['tr_type'],
                        date=row_dr['tr_date'],
                        party=row_dr['party'],
                        ref=row_dr['ref_no'],
                        desc=row_dr['description'],
                        dr_acc=row_dr['account_name'],
                        dr_amt=row_dr['debit'],
                        cr_acc=row_cr['account_name'],
                        cr_amt=row_cr['credit']
                    )
                    
                    reader = PdfReader(pdf_buffer)
                    combined_pdf.add_page(reader.pages[0])
                
                # Output the combined PDF
                final_buffer = io.BytesIO()
                combined_pdf.write(final_buffer)
                final_buffer.seek(0)
                
                st.download_button(
                    label=f"📥 Download {len(to_print)} Vouchers in One PDF",
                    data=final_buffer,
                    file_name="bulk_vouchers.pdf",
                    mime="application/pdf"
                )

        st.divider()
        st.subheader("Full Transaction History")
        st.dataframe(df, use_container_width=True)

# --- MODULE: TRIAL BALANCE ---
elif menu == "Trial Balance":
    st.title("📊 Trial Balance")
    if not df.empty:
        tb = df.groupby('account_name')[['debit', 'credit']].sum()
        tb['Net Balance'] = tb['debit'] - tb['credit']
        st.dataframe(tb, use_container_width=True)
        
        total_dr = tb['debit'].sum()
        total_cr = tb['credit'].sum()
        st.metric("Ledger Status", "Balanced" if total_dr == total_cr else "Out of Balance", delta=total_dr-total_cr)
    else:
        st.warning("No data found to generate Trial Balance.")
