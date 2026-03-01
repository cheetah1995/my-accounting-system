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
    st.title("⚖️ Multi-Row Transaction Entry")
    
    if not account_list:
        st.warning("⚠️ Please import your Chart of Accounts first.")
        st.stop()

    v_type = st.selectbox("Transaction Type", ["Payment Voucher", "Cash Receipt", "Sales Entry", "Journal Entry"])
    v_no = get_next_v(v_type)
    
    # Header Info
    c1, c2, c3 = st.columns(3)
    date = c1.date_input("Date", datetime.now())
    party = c2.text_input("Payee/Customer")
    ref = c3.text_input("Reference/Cheque #")
    desc = st.text_area("General Narration")

    st.markdown("### Transaction Lines")
    st.info("Add rows for VAT, multiple expenses, or split payments. Ensure Total Difference is 0.00")

    # Initialize a empty table for the user to fill
    init_data = [
        {"account": None, "description": "", "debit": 0.0, "credit": 0.0},
        {"account": None, "description": "", "debit": 0.0, "credit": 0.0}
    ]
    
    # The Data Editor
    edited_df = st.data_editor(
        init_data,
        column_config={
            "account": st.column_config.SelectboxColumn(
                "Account Name",
                options=account_list,
                required=True,
            ),
            "debit": st.column_config.NumberColumn("Debit", min_value=0, format="%.2f"),
            "credit": st.column_config.NumberColumn("Credit", min_value=0, format="%.2f"),
            "description": st.column_config.TextColumn("Line Description (Optional)")
        },
        num_rows="dynamic",
        use_container_width=True,
        key="journal_editor"
    )

    # Validation Calculations
    lines_df = pd.DataFrame(edited_df)
    total_debit = lines_df['debit'].sum()
    total_credit = lines_df['credit'].sum()
    difference = round(total_debit - total_credit, 2)

    # Footer Totals
    f1, f2, f3 = st.columns(3)
    f1.metric("Total Debit", f"{total_debit:,.2f}")
    f2.metric("Total Credit", f"{total_credit:,.2f}")
    f3.metric("Difference", f"{difference:,.2f}", delta=difference, delta_color="inverse")

    if st.button("🚀 Post Multi-Entry Voucher"):
        if difference != 0:
            st.error(f"Entry is out of balance by {difference}. Please adjust rows.")
        elif total_debit == 0:
            st.error("Transaction amount cannot be zero.")
        elif lines_df['account'].isnull().any():
            st.error("Please select an account for all lines.")
        else:
            # Prepare for SQL
            final_entries = []
            for _, row in lines_df.iterrows():
                if row['debit'] > 0 or row['credit'] > 0:
                    final_entries.append({
                        'voucher_no': v_no,
                        'tr_type': v_type,
                        'tr_date': date,
                        'party': party,
                        'ref_no': ref,
                        'description': row['description'] if row['description'] else desc,
                        'account_name': row['account'],
                        'debit': row['debit'],
                        'credit': row['credit']
                    })
            
            try:
                pd.DataFrame(final_entries).to_sql('general_ledger', engine, if_exists='append', index=False)
                st.success(f"Successfully Posted {v_no} with {len(final_entries)} lines!")
                
                # Update session state for printing (We take the first DR and first CR for the simple print template)
                # Note: For complex prints, we'd need to update the PDF function to handle multiple rows.
                st.session_state['last_post'] = final_entries[0] # Placeholder for simple print
                st.balloons()
            except Exception as e:
                st.error(f"Database Error: {e}")

    # (Keep your Download Button logic here)
# --- MODULE: GENERAL LEDGER ---
elif menu == "General Ledger":
    st.title("📖 General Ledger & Bulk Print")
    
    if df.empty:
        st.info("The ledger is empty.")
    else:
        # --- DATE FILTERS ---
        st.subheader("Filter by Period")
        c1, c2 = st.columns(2)
        
        # Default to the current month's range
        start_date = c1.date_input("Start Date", value=datetime(datetime.now().year, datetime.now().month, 1))
        end_date = c2.date_input("End Date", value=datetime.now())

        # Filter the main dataframe based on user selection
        # Note: Ensure tr_date is in datetime format for comparison
        df['tr_date'] = pd.to_datetime(df['tr_date']).dt.date
        mask = (df['tr_date'] >= start_date) & (df['tr_date'] <= end_date)
        filtered_df = df.loc[mask]

        if filtered_df.empty:
            st.warning("No transactions found for this date range.")
        else:
            # --- BULK PRINT SECTION ---
            unique_vouchers = filtered_df[['voucher_no', 'tr_date', 'party', 'tr_type']].drop_duplicates()
            
            st.markdown("---")
            st.subheader("🖨️ Bulk Export")
            to_print = st.multiselect(
                f"Select Vouchers to Print ({len(unique_vouchers)} found in range)", 
                options=unique_vouchers['voucher_no'].tolist()
            )
            
            if st.button("Generate Combined PDF"):
                if not to_print:
                    st.warning("Please select at least one voucher.")
                else:
                    from PyPDF2 import PdfWriter, PdfReader
                    combined_pdf = PdfWriter()
                    
                    for v_no in to_print:
                        v_data = filtered_df[filtered_df['voucher_no'] == v_no]
                        
                        # Extract DR and CR rows
                        dr_rows = v_data[v_data['debit'] > 0]
                        cr_rows = v_data[v_data['credit'] > 0]
                        
                        if not dr_rows.empty and not cr_rows.empty:
                            row_dr = dr_rows.iloc[0]
                            row_cr = cr_rows.iloc[0]
                            
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
                    
                    final_buffer = io.BytesIO()
                    combined_pdf.write(final_buffer)
                    final_buffer.seek(0)
                    
                    st.download_button(
                        label=f"📥 Download {len(to_print)} Vouchers (PDF)",
                        data=final_buffer,
                        file_name=f"Vouchers_{start_date}_to_{end_date}.pdf",
                        mime="application/pdf"
                    )

            st.markdown("---")
            st.subheader("Filtered Ledger View")
            st.dataframe(filtered_df, use_container_width=True)
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
