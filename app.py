import streamlit as st
import pandas as pd

st.set_page_config(page_title="Professional Ledger", layout="wide")

# 1. SETUP DATA STORAGE
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=['Date', 'Description', 'Account', 'Debit', 'Credit'])

# 2. THE ACCOUNTANT'S FORM
st.sidebar.title("Navigation")
page = st.sidebar.radio("Menu", ["Entry Form", "Trial Balance", "General Ledger"])

if page == "Entry Form":
    st.title("⚖️ Balanced Journal Entry")
    with st.form("entry"):
        date = st.date_input("Date")
        desc = st.text_input("Description")
        
        c1, c2 = st.columns(2)
        with c1:
            dr_acc = st.text_input("Debit Account (e.g., Cash)")
            dr_amt = st.number_input("Debit Amount", min_value=0.0)
        with c2:
            cr_acc = st.text_input("Credit Account (e.g., Revenue)")
            cr_amt = st.number_input("Credit Amount", min_value=0.0)
            
        if st.form_submit_button("Post to Books"):
            if dr_amt != cr_amt:
                st.error(f"Does not balance! Difference: {abs(dr_amt-cr_amt)}")
            elif dr_amt == 0:
                st.error("Amount must be > 0")
            else:
                new_data = pd.DataFrame([
                    {'Date': date, 'Description': desc, 'Account': dr_acc, 'Debit': dr_amt, 'Credit': 0.0},
                    {'Date': date, 'Description': desc, 'Account': cr_acc, 'Debit': 0.0, 'Credit': cr_amt}
                ])
                st.session_state.ledger = pd.concat([st.session_state.ledger, new_data], ignore_index=True)
                st.success("Balanced Entry Posted!")

elif page == "Trial Balance":
    st.title("📊 Trial Balance")
    tb = st.session_state.ledger.groupby('Account')[['Debit', 'Credit']].sum()
    st.table(tb)
    st.metric("Total Debits", f"${st.session_state.ledger.Debit.sum():,.2f}")
    st.metric("Total Credits", f"${st.session_state.ledger.Credit.sum():,.2f}")

else:
    st.title("📖 General Ledger")
    st.dataframe(st.session_state.ledger)
