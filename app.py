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
    st.subheader("Import Chart of Accounts")
    st.write("Upload a CSV with a column named **account_name**")
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        import_df = pd.read_csv(uploaded_file)
        st.write("Preview of Upload:", import_df.head())
        
        if st.button("Confirm & Push to Database"):
            try:
                # Keep only relevant columns
                to_db = import_df[['account_name']]
                if 'account_type' in import_df.columns:
                    to_db = import_df[['account_name', 'account_type']]
                
                to_db.to_sql('chart_of_accounts', engine, if_exists='append', index=False)
                st.success(f"Successfully imported {len(to_db)} accounts!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e} (Check if account names already exist)")

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
