import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# PAGE CONFIG
st.set_page_config(page_title="Professional SQL Ledger", layout="wide")

# 1. DATABASE CONNECTION
# This pulls the 'url' from your Streamlit Secrets
try:
    DB_URL = st.secrets["connections"]["postgresql"]["url"]
    engine = create_engine(DB_URL)
except Exception as e:
    st.error("Database connection string missing in Secrets!")
    st.stop()

# 2. DATA LOADING LOGIC
def load_data():
    query = "SELECT * FROM general_ledger ORDER BY tr_date DESC, id DESC"
    try:
        return pd.read_sql(query, engine)
    except Exception:
        # If the table doesn't exist yet, return an empty dataframe
        return pd.DataFrame(columns=['voucher_no', 'tr_type', 'tr_date', 'party', 'ref_no', 'description', 'account_name', 'debit', 'credit'])

df = load_data()

# 3. VOUCHER NUMBER GENERATOR
def get_next_v(prefix):
    if df.empty:
        return f"{prefix}-001"
    # Filter for the specific type (e.g., PV)
    filtered = df[df['voucher_no'].str.startswith(prefix, na=False)]
    if filtered.empty:
        return f"{prefix}-001"
    
    # Extract number from 'PV-001' -> 1
    try:
        last_val = filtered['voucher_no'].iloc[0] # Get latest because of DESC order
        last_num = int(last_val.split("-")[1])
        return f"{prefix}-{last_num + 1:03d}"
    except:
        return f"{prefix}-001"

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("ERP Modules")
menu = st.sidebar.radio("Go to", ["Entry Module", "General Ledger", "Trial Balance"])

# --- MAIN LOGIC FLOW ---
if menu == "Entry Module":
    st.title("⚖️ Double-Entry Posting")
    v_type = st.selectbox("Transaction Type", ["Payment Voucher", "Cash Receipt", "Sales Entry", "Journal Entry"])
    
    prefix_map = {"Payment Voucher": "PV", "Cash Receipt": "CR", "Sales Entry": "SJ", "Journal Entry": "JV"}
    prefix = prefix_map[v_type]
    v_no = get_next_v(prefix)
    
    st.subheader(f"New Document: {v_no}")

    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Transaction Date", datetime.now())
            party = st.text_input("Payee / Customer Name")
        with c2:
            ref = st.text_input("Ref / Cheque Number")
            desc = st.text_area("Narration")

        st.markdown("---")
        col_acc, col_dr, col_cr = st.columns([2, 1, 1])
        
        dr_acc = col_acc.text_input("Debit Account")
        dr_amt = col_dr.number_input("Debit Amount", min_value=0.0, step=0.01, key="dr")
        
        cr_acc = col_acc.text_input("Credit Account")
        cr_amt = col_cr.number_input("Credit Amount", min_value=0.0, step=0.01, key="cr")

        submit = st.form_submit_button("Post to Cloud Ledger")

        if submit:
            if dr_amt != cr_amt or dr_amt == 0:
                st.error(f"Entry does not balance! Difference: {abs(dr_amt-cr_amt)}")
            else:
                new_entries = pd.DataFrame([
                    {'voucher_no': v_no, 'tr_type': v_type, 'tr_date': date, 'party': party, 'ref_no': ref, 
                     'description': desc, 'account_name': dr_acc, 'debit': dr_amt, 'credit': 0.0},
                    {'voucher_no': v_no, 'tr_type': v_type, 'tr_date': date, 'party': party, 'ref_no': ref, 
                     'description': desc, 'account_name': cr_acc, 'debit': 0.0, 'credit': cr_amt}
                ])
                try:
                    new_entries.to_sql('general_ledger', engine, if_exists='append', index=False)
                    st.success(f"Successfully Posted {v_no}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {e}")

elif menu == "General Ledger":
    st.title("📖 General Ledger")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("The ledger is empty.")

elif menu == "Trial Balance":
    st.title("📊 Trial Balance")
    if not df.empty:
        tb = df.groupby('account_name')[['debit', 'credit']].sum()
        st.table(tb)
    else:
        st.warning("No data found.")
