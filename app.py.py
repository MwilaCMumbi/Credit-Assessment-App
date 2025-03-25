import streamlit as st
import sqlite3

# Set page title and icon
st.set_page_config(
    page_title="VZ Credit Score App",
    page_icon="📊",
)

# Initialize session state
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.customer_name = ""
    st.session_state.is_new_customer = False
    st.session_state.credit_history = 0
    st.session_state.income_stability = 0
    st.session_state.location = 0
    st.session_state.banking_access = 0
    st.session_state.referral = 0

# Database setup
def init_db():
    conn = sqlite3.connect("credit_scores.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS credit_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            credit_score REAL,
            risk_category TEXT,
            recommended_products TEXT
        )"""
    )
    conn.commit()
    conn.close()

def save_to_db(customer_name, credit_score, risk_category, recommended_products):
    conn = sqlite3.connect("credit_scores.db")
    c = conn.cursor()
    c.execute(
        """INSERT INTO credit_assessments (customer_name, credit_score, risk_category, recommended_products)
        VALUES (?, ?, ?, ?)""",
        (customer_name, credit_score, risk_category, recommended_products),
    )
    conn.commit()
    conn.close()

def get_credit_history_score(is_new_customer):
    if is_new_customer:
        options = {
            "Regular inflows and outflows, consistent savings, and no loans.": 10,
            "Regular inflows and outflows, no savings, and no loans.": 9,
            "Regular inflows and outflows, no savings, with loans.": 8,
            "Moderate transaction activity, consistent savings, and no loans.": 7,
            "Moderate transaction activity, no savings, and no loans.": 6,
            "Moderate transaction activity, no savings, with loans.": 5,
            "Irregular transactions, consistent savings, and no loans.": 4,
            "Irregular transactions, no savings, and no loans.": 3,
            "Irregular transactions, no savings, with loans.": 2,
            "No credit history data.": 1,
        }
    else:
        options = {
            "100% Collections Rate": 10,
            "90% Collections Rate": 9,
            "80% Collections Rate": 8,
            "70% Collections Rate": 7,
            "60% Collections Rate": 6,
            "50% Collections Rate": 5,
            "40% Collections Rate": 4,
            "30% Collections Rate": 3,
            "20% Collections Rate": 2,
            "10% Collections Rate": 1,
        }
    choice = st.selectbox(f"Select Credit History ({'New' if is_new_customer else 'Existing'} Customer):", list(options.keys()))
    return options[choice]

def get_income_stability_score():
    options = {
        "Stable salary (e.g., government job) - Above 10,000 ZMW": 10,
        "Stable salary (e.g., government job) - 7,000 - 10,000 ZMW": 9,
        "Stable salary (e.g., government job) - 5,000 - 6,999 ZMW": 8,
        "Regular business income (e.g., small shop) - 3,000 - 4,999 ZMW": 7,
        "Regular business income (e.g., small shop) - 2,000 - 2,999 ZMW": 6,
        "Seasonal income (e.g., farming) - 1,000 - 1,999 ZMW": 5,
        "Seasonal income (e.g., farming) - 500 - 999 ZMW": 4,
        "Irregular income (e.g., casual labor) - 300 - 499 ZMW": 3,
        "Irregular income (e.g., casual labor) - 100 - 299 ZMW": 2,
        "Irregular income (e.g., casual labor) - Below 100 ZMW": 1,
    }
    choice = st.selectbox("Select Income Type and Range:", list(options.keys()))
    return options[choice]

def get_location_score():
    options = {
        "Less than 1 km": 10,
        "1 - 5 km": 9,
        "5 - 10 km": 8,
        "10 - 20 km": 7,
        "20 - 30 km": 6,
        "30 - 50 km": 5,
        "50 - 70 km": 4,
        "70 - 100 km": 3,
        "100 - 150 km": 2,
        "More than 150 km": 1,
    }
    choice = st.selectbox("Select Distance from Nearest Agent/Service Center:", list(options.keys()))
    return options[choice]

def get_banking_access_score():
    options = {
        "Access to all financial services (traditional banking, mobile money, agent networks, SACCOs, etc.).": 10,
        "Access to traditional banking services, mobile money platforms, and agent networks.": 9,
        "Access to traditional banking services and mobile money platforms.": 8,
        "Access to traditional banking services (e.g., bank account)": 7,
        "Access to mobile money platforms, agent networks, and SACCOs.": 6,
        "Access to mobile money platforms, agent networks, and informal savings groups.": 5,
        "Access to mobile money platforms and agent banking networks.": 4,
        "Access to mobile money platforms only (e.g., Airtel Money, MTN Mobile Money).": 3,
        "Access to mobile money agents only.": 2,
        "No access to any financial services.": 1,
    }
    choice = st.selectbox("Select Access to Banking/Financial Services:", list(options.keys()))
    return options[choice]

def get_referral_score():
    options = {
        "Sales Agent/Staff (VITALITE)": 10,
        "Existing Customer (good repayment history)": 9,
        "Employer (formal employment)": 8,
        "Commissioner of Oaths (legal authority)": 7,
        "Community Leader (e.g., village head, pastor)": 6,
        "Next of Kin (immediate family member)": 5,
        "Local Business Owner (established business)": 4,
        "Teacher/Educator (recognized professional)": 3,
        "Neighbor (known to the customer)": 2,
        "No Referral/Guarantor": 1,
    }
    choice = st.selectbox("Select Referral/Guarantor Type:", list(options.keys()))
    return options[choice]

def calculate_credit_score(credit_history, income_stability, location, banking_access, referral):
    return (
        (credit_history * 0.30) +
        (income_stability * 0.25) +
        (location * 0.15) +
        (banking_access * 0.20) +
        (referral * 0.10)
    )

def get_risk_category(credit_score):
    if credit_score > 8:
        return "Low Risk"
    elif credit_score >= 5:
        return "Medium Risk"
    elif credit_score >= 3:
        return "High Risk"
    else:
        return "Rejected"

def get_recommended_products(risk_category):
    return {
        "Low Risk": "All Products",
        "Medium Risk": "Mid Value Products",
        "High Risk": "Low Value Products",
        "Rejected": "Rejected (No Products Recommended)"
    }[risk_category]

def main():
    st.title("VZ Credit Score App")
    init_db()

    if st.session_state.step == 1:
        st.subheader("Step 1: Customer Details")
        st.session_state.customer_name = st.text_input("Enter Customer Name:")
        st.session_state.is_new_customer = st.radio("Is the customer new?", ("Yes", "No")) == "Yes"
        
        if st.button("Next"):
            st.session_state.step = 2
            st.rerun()

    elif st.session_state.step == 2:
        st.subheader("Step 2: Credit History")
        st.session_state.credit_history = get_credit_history_score(st.session_state.is_new_customer)
        
        if st.button("Next"):
            st.session_state.step = 3
            st.rerun()

    elif st.session_state.step == 3:
        st.subheader("Step 3: Income Stability")
        st.session_state.income_stability = get_income_stability_score()
        
        if st.button("Next"):
            st.session_state.step = 4
            st.rerun()

    elif st.session_state.step == 4:
        st.subheader("Step 4: Location")
        st.session_state.location = get_location_score()
        
        if st.button("Next"):
            st.session_state.step = 5
            st.rerun()

    elif st.session_state.step == 5:
        st.subheader("Step 5: Banking Access")
        st.session_state.banking_access = get_banking_access_score()
        
        if st.button("Next"):
            st.session_state.step = 6
            st.rerun()

    elif st.session_state.step == 6:
        st.subheader("Step 6: Referral")
        st.session_state.referral = get_referral_score()
        
        if st.button("Next"):
            st.session_state.step = 7
            st.rerun()

    elif st.session_state.step == 7:
        st.subheader("Step 7: Results")
        credit_score = calculate_credit_score(
            st.session_state.credit_history,
            st.session_state.income_stability,
            st.session_state.location,
            st.session_state.banking_access,
            st.session_state.referral,
        )
        risk_category = get_risk_category(credit_score)
        
        st.write(f"Customer Name: {st.session_state.customer_name}")
        st.write(f"Credit Score: {credit_score:.2f}")
        st.write(f"Risk Category: {risk_category}")
        st.write(f"Recommended Products: {get_recommended_products(risk_category)}")
        
        st.subheader("Score Breakdown")
        st.write(f"Credit History (30%): {st.session_state.credit_history} → {st.session_state.credit_history * 0.30:.2f}")
        st.write(f"Income Stability (25%): {st.session_state.income_stability} → {st.session_state.income_stability * 0.25:.2f}")
        st.write(f"Location (15%): {st.session_state.location} → {st.session_state.location * 0.15:.2f}")
        st.write(f"Banking Access (20%): {st.session_state.banking_access} → {st.session_state.banking_access * 0.20:.2f}")
        st.write(f"Referral (10%): {st.session_state.referral} → {st.session_state.referral * 0.10:.2f}")
        
        if st.button("Save Assessment"):
            save_to_db(
                st.session_state.customer_name,
                credit_score,
                risk_category,
                get_recommended_products(risk_category),
            )
            st.success("Assessment saved to database!")
        
        if st.button("Start New Assessment"):
            st.session_state.step = 1
            st.rerun()

if __name__ == "__main__":
    main()