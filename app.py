import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# PAGE CONFIG
st.set_page_config(page_title="SQL ERP Pro", layout="wide")

# 1. DATABASE CONNECTION
DB_URL = st.secrets["connections"]["postgresql"]["url"]
engine = create_engine(DB_URL)

# 2. DATA LOADERS
def load_ledger():
    try:
        return pd.read_sql("SELECT * FROM general_ledger ORDER BY tr_date DESC, id DESC", engine)
    except:
        return pd.DataFrame()

def load_accounts():
    try:
        df_accounts = pd.read_sql("SELECT account_name FROM chart_of_accounts ORDER BY account_name ASC", engine)
        return df_accounts['account_name'].tolist()
    except:
        return []

df = load_ledger()
account_list = load_accounts()

# --- SIDEBAR NAVIGATION ---
menu = st.sidebar.radio("Main Menu", ["Entry Module", "General Ledger", "Trial Balance", "Settings / Import"])

if menu == "Settings / Import":
    st.title("⚙️ Admin Settings")
    
    # --- TEMPLATE SECTION ---
    st.subheader("1. Download Import Template")
    st.write("Use this template to format your Chart of Accounts correctly.")
    
    # Create a simple template dataframe
    template_data = pd.DataFrame({
        'account_name': ['Cash in Hand', 'Bank Account', 'Sales Revenue', 'Rent Expense'],
        'account_type': ['Asset', 'Asset', 'Revenue', 'Expense']
    })
    
    # Convert to CSV
    template_csv = template_data.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Download CSV Template",
        data=template_csv,
        file_name="coa_template.csv",
        mime="text/csv",
    )
    
    st.divider()

    # --- UPLOAD SECTION ---
    st.subheader("2. Upload Chart of Accounts")
    st.info("Ensure your file has a column named **account_name**.")
    
    uploaded_file = st.file_uploader("Choose your formatted CSV file", type="csv")
    
    if uploaded_file is not None:
        import_df = pd.read_csv(uploaded_file)
        
        # Data Cleaning: Remove empty rows and duplicates
        import_df = import_df.dropna(subset=['account_name'])
        
        st.write("Preview of data to be imported:")
        st.dataframe(import_df.head(), use_container_width=True)
        
        if st.button("🚀 Push to Database"):
            try:
                # We use a 'try' block because the 'account_name' must be UNIQUE in SQL
                import_df.to_sql('chart_of_accounts', engine, if_exists='append', index=False)
                st.success(f"Successfully imported {len(import_df)} new accounts!")
                st.rerun()
            except Exception as e:
                st.error("Error: It looks like some of these accounts already exist in the database.")

elif menu == "Entry Module":
    st.title("⚖️ New Transaction")
    
    if not account_list:
        st.warning("⚠️ No accounts found! Go to 'Settings' to import your Chart of Accounts first.")
        st.stop()

    v_type = st.selectbox("Type", ["Payment Voucher", "Cash Receipt", "Sales Entry", "Journal Entry"])
    
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        date = c1.date_input("Date", datetime.now())
        party = c1.text_input("Payee/Customer")
        ref = c2.text_input("Reference")
        desc = c2.text_area("Description")

        st.markdown("---")
        # SEARCHABLE SELECT BOXES
        dr_acc = st.selectbox("Debit Account", options=account_list, index=None, placeholder="Search accounts...")
        dr_amt = st.number_input("Debit Amount", min_value=0.0, format="%.2f")
        
        cr_acc = st.selectbox("Credit Account", options=account_list, index=None, placeholder="Search accounts...")
        cr_amt = st.number_input("Credit Amount", min_value=0.0, format="%.2f")

        if st.form_submit_button("Post Entry"):
            if dr_amt == cr_amt and dr_amt > 0 and dr_acc and cr_acc:
                # (Same logic as before to create new_entries DataFrame)
                new_entries = pd.DataFrame([
                    {'voucher_no': 'AUTO', 'tr_type': v_type, 'tr_date': date, 'party': party, 'ref_no': ref, 'description': desc, 'account_name': dr_acc, 'debit': dr_amt, 'credit': 0.0},
                    {'voucher_no': 'AUTO', 'tr_type': v_type, 'tr_date': date, 'party': party, 'ref_no': ref, 'description': desc, 'account_name': cr_acc, 'debit': 0.0, 'credit': cr_amt}
                ])
                new_entries.to_sql('general_ledger', engine, if_exists='append', index=False)
                st.success("Entry Posted!")
                st.rerun()
            else:
                st.error("Check balance and ensure accounts are selected.")

# (Keep General Ledger and Trial Balance code here...)
        tb = df.groupby('account_name')[['debit', 'credit']].sum()
        st.table(tb)
    else:
        st.warning("No data found.")
