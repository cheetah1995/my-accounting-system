import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Universal Accounting System", layout="wide")

# --- SIMPLIFIED CONNECTION ---
# Replace the ID below with your actual Google Sheet ID
SHEET_ID = "YOUR_ACTUAL_ID_HERE" 
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

try:
    df = pd.read_csv(SHEET_URL)
except Exception as e:
    st.error("Cannot connect to Google Sheets. Please ensure the sheet is shared as 'Anyone with the link can view'.")
    df = pd.DataFrame(columns=['Voucher_No', 'Type', 'Date', 'Party', 'Ref_No', 'Description', 'Account', 'Debit', 'Credit'])
# -----------------------------

# ... (The rest of your code for get_next_voucher and the forms remains the same)

# 2. ENHANCED AUTO-GENERATION LOGIC
def get_next_voucher(df, prefix):
    if df.empty or 'Voucher_No' not in df.columns:
        return f"{prefix}-001"
    
    # Filter for the specific type (e.g., only PVs)
    filtered = df[df['Voucher_No'].str.startswith(prefix, na=False)]
    if filtered.empty:
        return f"{prefix}-001"
    
    last_val = str(filtered['Voucher_No'].iloc[-1])
    try:
        last_num = int(last_val.split("-")[1])
        return f"{prefix}-{last_num + 1:03d}"
    except:
        return f"{prefix}-001"

# NAVIGATION
menu = st.sidebar.radio("Main Menu", ["Data Entry", "General Ledger", "Financial Reports"])

if menu == "Data Entry":
    st.title("📝 Universal Entry Module")
    
    # TYPE SELECTOR
    v_type = st.selectbox("Select Transaction Type", 
                          ["Payment Voucher", "Cash Receipt", "Sales Entry", "Journal Entry"])
    
    # MAP PREFIXES
    prefix_map = {
        "Payment Voucher": "PV",
        "Cash Receipt": "CR",
        "Sales Entry": "SJ",
        "Journal Entry": "JV"
    }
    prefix = prefix_map[v_type]
    v_no = get_next_voucher(df, prefix)
    
    st.subheader(f"Document Number: {v_no}")

    with st.form("universal_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.now())
            # Dynamic Labeling
            party_label = "Received From / Customer" if v_type in ["Cash Receipt", "Sales Entry"] else "Paid To / Bearer"
            party = st.text_input(party_label)
            ref_no = st.text_input("Cheque / Reference Number")
        
        with col2:
            description = st.text_area("Narration / Remarks")

        st.markdown("---")
        st.markdown("### Ledger Posting")
        
        row1, row2 = st.columns(2)
        with row1:
            dr_acc = st.text_input("Debit Account")
            dr_amt = st.number_input("Debit Amount", min_value=0.0, format="%.2f")
        with row2:
            cr_acc = st.text_input("Credit Account")
            cr_amt = st.number_input("Credit Amount", min_value=0.0, format="%.2f")

        if st.form_submit_button("Post to Cloud"):
            if dr_amt != cr_amt or dr_amt == 0:
                st.error("Transaction must balance and be greater than zero.")
            else:
                new_entries = pd.DataFrame([
                    {'Voucher_No': v_no, 'Type': v_type, 'Date': str(date), 'Party': party, 'Ref_No': ref_no, 
                     'Description': description, 'Account': dr_acc, 'Debit': dr_amt, 'Credit': 0.0},
                    {'Voucher_No': v_no, 'Type': v_type, 'Date': str(date), 'Party': party, 'Ref_No': ref_no, 
                     'Description': description, 'Account': cr_acc, 'Debit': 0.0, 'Credit': cr_amt}
                ])
                
                updated_df = pd.concat([df, new_entries], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"{v_type} {v_no} Saved Successfully!")

elif menu == "General Ledger":
    st.title("📖 Live Transaction History")
    # Add a filter so you can see just PVs or just CRs
    filter_type = st.multiselect("Filter by Type", df['Type'].unique() if not df.empty else [])
    display_df = df[df['Type'].isin(filter_type)] if filter_type else df
    st.dataframe(display_df, use_container_width=True)
