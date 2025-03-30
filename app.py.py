import streamlit as st
import hashlib
import sqlite3
import pandas as pd
from datetime import datetime
import time
from io import BytesIO

# Set page title and icon
st.set_page_config(
    page_title="VZ Credit Score App",
    page_icon="📊",
    layout="wide"
)

# Initialize database
def init_db():
    conn = sqlite3.connect('credit_app.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  full_name TEXT NOT NULL,
                  role TEXT NOT NULL CHECK(role IN ('admin', 'user', 'viewer')),
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Audit log table
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action TEXT NOT NULL,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  details TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Assessments table
    c.execute('''CREATE TABLE IF NOT EXISTS assessments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  customer_name TEXT NOT NULL,
                  is_new_customer BOOLEAN NOT NULL,
                  credit_history INTEGER NOT NULL,
                  income_stability INTEGER NOT NULL,
                  location INTEGER NOT NULL,
                  banking_access INTEGER NOT NULL,
                  referral INTEGER NOT NULL,
                  credit_score REAL NOT NULL,
                  risk_category TEXT NOT NULL,
                  recommended_products TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Add default admin user if not exists
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                  ('admin', password_hash, 'Administrator', 'admin'))
    
    conn.commit()
    conn.close()

init_db()

# Database helper functions
def get_db_connection():
    return sqlite3.connect('credit_app.db')

def log_audit_action(user_id, action, details=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO audit_log (user_id, action, details) VALUES (?, ?, ?)",
              (user_id, action, details))
    conn.commit()
    conn.close()

# Security functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed_password):
    return hash_password(password) == hashed_password

def verify_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, full_name, role FROM users WHERE username = ?", (username,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data and verify_password(password, user_data[2]):
        return {
            "id": user_data[0],
            "username": user_data[1],
            "full_name": user_data[3],
            "role": user_data[4]
        }
    return None

def get_current_user():
    return st.session_state.get("user")

def is_admin():
    user = get_current_user()
    return user and user.get("role") == "admin"

def is_user():
    user = get_current_user()
    return user and user.get("role") in ["admin", "user"]

def is_viewer():
    user = get_current_user()
    return user and user.get("role") in ["admin", "user", "viewer"]

def logout():
    if "user" in st.session_state:
        log_audit_action(st.session_state.user["id"], "logout")
        del st.session_state["user"]
    st.session_state.step = 1
    st.rerun()

# UI Helpers
def show_toast(message, type="success"):
    if type == "success":
        st.toast(f"✅ {message}")
    elif type == "error":
        st.toast(f"❌ {message}")
    elif type == "warning":
        st.toast(f"⚠️ {message}")
    else:
        st.toast(message)

def show_spinner(message):
    return st.spinner(message)

# User Management
def user_management():
    st.subheader("User Management")
    tab1, tab2, tab3 = st.tabs(["Add User", "Edit Users", "Delete Users"])
    
    with tab1:
        with st.form("add_user_form"):
            st.write("### Add New User")
            new_username = st.text_input("Username", key="new_username")
            new_password = st.text_input("Password", type="password", key="new_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            new_full_name = st.text_input("Full Name", key="new_full_name")
            new_role = st.selectbox("Role", ["admin", "user", "viewer"], key="new_role")
            
            if st.form_submit_button("Add User"):
                if not new_username or not new_password or not new_full_name:
                    show_toast("All fields are required!", "error")
                elif new_password != confirm_password:
                    show_toast("Passwords don't match!", "error")
                elif len(new_password) < 8:
                    show_toast("Password must be at least 8 characters!", "error")
                else:
                    conn = get_db_connection()
                    c = conn.cursor()
                    try:
                        password_hash = hash_password(new_password)
                        c.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                                  (new_username, password_hash, new_full_name, new_role))
                        conn.commit()
                        log_audit_action(st.session_state.user["id"], "add_user", f"Added user {new_username}")
                        show_toast(f"User {new_username} added successfully!", "success")
                    except sqlite3.IntegrityError:
                        show_toast("Username already exists!", "error")
                    finally:
                        conn.close()
    
    with tab2:
        st.write("### Edit Existing Users")
        conn = get_db_connection()
        users = pd.read_sql("SELECT id, username, full_name, role FROM users ORDER BY username", conn)
        conn.close()
        
        if not users.empty:
            edited_users = st.data_editor(
                users,
                column_config={
                    "id": None,
                    "username": "Username",
                    "full_name": "Full Name",
                    "role": st.column_config.SelectboxColumn(
                        "Role",
                        options=["admin", "user", "viewer"],
                        required=True
                    )
                },
                key="users_editor",
                num_rows="dynamic"
            )
            
            if st.button("Save Changes"):
                conn = get_db_connection()
                c = conn.cursor()
                changes_made = False
                
                for _, row in edited_users.iterrows():
                    c.execute("UPDATE users SET full_name = ?, role = ? WHERE id = ?",
                              (row["full_name"], row["role"], row["id"]))
                    changes_made = True
                
                if changes_made:
                    conn.commit()
                    log_audit_action(st.session_state.user["id"], "edit_users", "Updated user records")
                    show_toast("User changes saved successfully!", "success")
                conn.close()
        else:
            st.warning("No users found in the database.")
    
    with tab3:
        st.write("### Delete Users")
        conn = get_db_connection()
        users = pd.read_sql("SELECT id, username, full_name, role FROM users WHERE username != 'admin' ORDER BY username", conn)
        conn.close()
        
        if not users.empty:
            selected_users = st.multiselect("Select users to delete", users["username"].tolist())
            
            if st.button("Delete Selected Users", type="primary"):
                if selected_users:
                    conn = get_db_connection()
                    c = conn.cursor()
                    for username in selected_users:
                        c.execute("DELETE FROM users WHERE username = ?", (username,))
                    conn.commit()
                    log_audit_action(st.session_state.user["id"], "delete_users", f"Deleted users: {', '.join(selected_users)}")
                    show_toast(f"Deleted {len(selected_users)} user(s) successfully!", "success")
                    st.rerun()
                else:
                    show_toast("Please select at least one user to delete", "error")
        else:
            st.warning("No deletable users found in the database.")

def reset_password():
    st.subheader("Password Reset")
    
    if is_admin():
        conn = get_db_connection()
        users = pd.read_sql("SELECT id, username, full_name FROM users ORDER BY username", conn)
        conn.close()
        
        selected_user = st.selectbox("Select User", users["username"].tolist())
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.button("Reset Password"):
            if not new_password or not confirm_password:
                show_toast("Both password fields are required!", "error")
            elif new_password != confirm_password:
                show_toast("Passwords don't match!", "error")
            elif len(new_password) < 8:
                show_toast("Password must be at least 8 characters!", "error")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                password_hash = hash_password(new_password)
                c.execute("UPDATE users SET password_hash = ? WHERE username = ?",
                          (password_hash, selected_user))
                conn.commit()
                conn.close()
                log_audit_action(st.session_state.user["id"], "reset_password", f"Reset password for {selected_user}")
                show_toast(f"Password for {selected_user} reset successfully!", "success")
    else:
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.button("Change Password"):
            if not current_password or not new_password or not confirm_password:
                show_toast("All fields are required!", "error")
            elif new_password != confirm_password:
                show_toast("New passwords don't match!", "error")
            elif len(new_password) < 8:
                show_toast("Password must be at least 8 characters!", "error")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT password_hash FROM users WHERE id = ?", (st.session_state.user["id"],))
                current_hash = c.fetchone()[0]
                
                if not verify_password(current_password, current_hash):
                    show_toast("Current password is incorrect!", "error")
                else:
                    new_hash = hash_password(new_password)
                    c.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                              (new_hash, st.session_state.user["id"]))
                    conn.commit()
                    conn.close()
                    log_audit_action(st.session_state.user["id"], "change_password", "User changed their password")
                    show_toast("Password changed successfully!", "success")

# Data Export Functions
def export_assessments():
    st.subheader("Export Assessments")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        end_date = st.date_input("End Date")
    
    # Format dates for SQL query
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Get assessments data
    conn = get_db_connection()
    query = f"""
        SELECT a.customer_name, a.is_new_customer, a.credit_score, a.risk_category, 
               a.recommended_products, a.created_at, u.full_name as assessed_by
        FROM assessments a
        JOIN users u ON a.user_id = u.id
        WHERE date(a.created_at) BETWEEN '{start_date_str}' AND '{end_date_str}'
        ORDER BY a.created_at DESC
    """
    assessments = pd.read_sql(query, conn)
    conn.close()
    
    if assessments.empty:
        st.warning("No assessments found for the selected date range.")
        return
    
    st.write(f"Found {len(assessments)} assessments between {start_date_str} and {end_date_str}")
    
    # Export options
    export_format = st.radio("Export Format", ["CSV", "Excel"])
    
    if export_format == "CSV":
        csv = assessments.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"assessments_{start_date_str}_to_{end_date_str}.csv",
            mime="text/csv"
        )
    else:  # Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            assessments.to_excel(writer, index=False, sheet_name='Assessments')
        excel_data = output.getvalue()
        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name=f"assessments_{start_date_str}_to_{end_date_str}.xlsx",
            mime="application/vnd.ms-excel"
        )

# Audit Log View
def view_audit_log():
    st.subheader("Audit Log")
    
    conn = get_db_connection()
    audit_log = pd.read_sql("""
        SELECT l.timestamp, u.username, l.action, l.details 
        FROM audit_log l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.timestamp DESC
        LIMIT 500
    """, conn)
    conn.close()
    
    if not audit_log.empty:
        st.dataframe(audit_log)
        
        # Export audit log
        if st.button("Export Audit Log to CSV"):
            csv = audit_log.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="audit_log.csv",
                mime="text/csv",
                key="audit_log_download"
            )
    else:
        st.warning("No audit log entries found.")

# Credit scoring functions (unchanged from your original)
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

def save_assessment():
    credit_score = calculate_credit_score(
        st.session_state.credit_history,
        st.session_state.income_stability,
        st.session_state.location,
        st.session_state.banking_access,
        st.session_state.referral,
    )
    risk_category = get_risk_category(credit_score)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO assessments 
        (user_id, customer_name, is_new_customer, credit_history, income_stability, 
         location, banking_access, referral, credit_score, risk_category, recommended_products)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        st.session_state.user["id"],
        st.session_state.customer_name,
        st.session_state.is_new_customer,
        st.session_state.credit_history,
        st.session_state.income_stability,
        st.session_state.location,
        st.session_state.banking_access,
        st.session_state.referral,
        credit_score,
        risk_category,
        get_recommended_products(risk_category)
    ))
    conn.commit()
    conn.close()
    log_audit_action(st.session_state.user["id"], "save_assessment", f"Saved assessment for {st.session_state.customer_name}")

# Login page
def login_page():
    st.title("VZ Credit Score App - Login")
    
    # Login attempts tracking
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if st.session_state.login_attempts >= 3:
                show_toast("Too many failed attempts. Please try again later.", "error")
                time.sleep(2)  # Small delay to prevent brute force
            else:
                user = verify_user(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.login_attempts = 0
                    st.session_state.step = 1  # Reset to first step
                    log_audit_action(user["id"], "login")
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    remaining_attempts = 3 - st.session_state.login_attempts
                    show_toast(f"Invalid username or password. {remaining_attempts} attempts remaining.", "error")
                    time.sleep(1)  # Small delay to prevent brute force

# Main app function
def main():
    if "user" not in st.session_state:
        login_page()
        return
    
    # Initialize session state for the assessment steps
    if "step" not in st.session_state:
        st.session_state.step = 1
        st.session_state.customer_name = ""
        st.session_state.is_new_customer = False
        st.session_state.credit_history = 0
        st.session_state.income_stability = 0
        st.session_state.location = 0
        st.session_state.banking_access = 0
        st.session_state.referral = 0
    
    # Add logout button to sidebar
    st.sidebar.title(f"Welcome, {st.session_state.user.get('full_name', 'User')}")
    
    # Dark mode toggle
    dark_mode = st.sidebar.toggle("Dark Mode", value=False)
    if dark_mode:
        st.markdown("""
        <style>
            .stApp {
                background-color: #0E1117;
                color: white;
            }
            .css-1d391kg, .css-1v3fvcr, .css-1y4p8pa {
                background-color: #0E1117 !important;
            }
        </style>
        """, unsafe_allow_html=True)
    
    if st.sidebar.button("Logout"):
        logout()
    
    # Sidebar navigation
    st.sidebar.subheader("Navigation")
    if is_admin():
        menu_options = ["New Assessment", "View Assessments", "User Management", "Password Reset", "Audit Log"]
    elif is_user():
        menu_options = ["New Assessment", "View Assessments", "Password Reset"]
    else:  # Viewer
        menu_options = ["View Assessments"]
    
    selected_menu = st.sidebar.radio("Go to", menu_options)
    
    # Main content area
    if selected_menu == "New Assessment" and is_user():
        st.title("New Credit Assessment")
        
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
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Assessment"):
                    with show_spinner("Saving assessment..."):
                        save_assessment()
                        show_toast("Assessment saved successfully!", "success")
            with col2:
                if st.button("Start New Assessment"):
                    st.session_state.step = 1
                    st.rerun()
    
    elif selected_menu == "View Assessments" and is_viewer():
        export_assessments()
    
    elif selected_menu == "User Management" and is_admin():
        user_management()
    
    elif selected_menu == "Password Reset":
        reset_password()
    
    elif selected_menu == "Audit Log" and is_admin():
        view_audit_log()

if __name__ == "__main__":
    main()