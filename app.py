import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Pro Ledger: Voucher Edition", layout="wide")

# 1. DATABASE INITIALIZATION
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=[
        'Voucher_No', 'Date', 'Payee', 'Ref_No', 'Description', 'Account', 'Debit', 'Credit'
    ])

# 2. AUTO-GENERATION LOGIC
def get_next_voucher():
    if len(st.session_state.ledger) == 0:
        return "PV-001"
    # Get the last Voucher number and increment it
    last_val = st.session_state.ledger['Voucher_No'].iloc[-1]
    last_num = int(last_val.split("-")[1])
    return f"PV-{last_num + 1:03d}"

# NAVIGATION
menu = st.sidebar.radio("Navigation", ["Payment Voucher", "View Ledger"])

if menu == "Payment Voucher":
    st.title("💸 Payment Voucher Entry")
    
    # Auto-generate number
    v_no = get_next_voucher()
    st.subheader(f"Voucher Number: {v_no}")

    with st.form("pv_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.now())
            payee = st.text_input("Bearer of Cheque / Payee")
            ref_no = st.text_input("Reference / Cheque Number")
        
        with col2:
            description = st.text_area("Description / Narration")

        st.divider()
        st.markdown("### Double Entry Posting")
        row1_col1, row1_col2, row1_col3 = st.columns([2, 1, 1])
        
        # Line 1: Usually the Expense (Debit)
        dr_acc = row1_col1.text_input("Debit Account (e.g., Rent Expense)")
        dr_amt = row1_col2.number_input("Debit Amount", min_value=0.0, step=0.01)
        
        # Line 2: Usually the Bank/Cash (Credit)
        cr_acc = row1_col1.text_input("Credit Account (e.g., Bank Account)")
        cr_amt = row1_col3.number_input("Credit Amount", min_value=0.0, step=0.01)

        submit = st.form_submit_button("Generate & Post Voucher")

        if submit:
            if dr_amt != cr_amt:
                st.error(f"Voucher Unbalanced! Difference: {abs(dr_amt-cr_amt)}")
            elif dr_amt == 0:
                st.error("Amount must be greater than zero.")
            else:
                # Add two rows for the double entry
                new_entries = pd.DataFrame([
                    {'Voucher_No': v_no, 'Date': date, 'Payee': payee, 'Ref_No': ref_no, 
                     'Description': description, 'Account': dr_acc, 'Debit': dr_amt, 'Credit': 0.0},
                    {'Voucher_No': v_no, 'Date': date, 'Payee': payee, 'Ref_No': ref_no, 
                     'Description': description, 'Account': cr_acc, 'Debit': 0.0, 'Credit': cr_amt}
                ])
                st.session_state.ledger = pd.concat([st.session_state.ledger, new_entries], ignore_index=True)
                st.success(f"Voucher {v_no} posted successfully!")

elif menu == "View Ledger":
    st.title("📖 General Ledger & Voucher History")
    st.dataframe(st.session_state.ledger, use_container_width=True)
