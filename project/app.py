import streamlit as st
import pandas as pd
import os
import csv

# --- Configuration ---
st.set_page_config(page_title="User System", layout="centered")

# Light theme styling
st.markdown("""
    <style>
        body {
            background-color: white;
            color: black;
        }
    </style>
""", unsafe_allow_html=True)

# --- Constants ---
CSV_FILE = 'users.csv'
FIELDNAMES = ['name', 'email', 'username', 'password']
LINKS_DIR = "user_links"
os.makedirs(LINKS_DIR, exist_ok=True)

# Ensure user file exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None

# --- Logout ---
if st.session_state.user and st.sidebar.button("🚪 Logout"):
    st.session_state.user = None
    st.success("You have been logged out.")
    st.rerun()

# --- Sidebar ---
st.sidebar.title("🔐 Menu")
if st.session_state.user:
    st.sidebar.write(f"👋 Logged in as: `{st.session_state.user}`")
    page = st.sidebar.selectbox("Go to", ["Links", "Profile"])
else:
    page = st.sidebar.selectbox("Go to", ["Login", "Register"])

# --- Register Page ---
if page == "Register":
    st.title("📝 Register")
    name = st.text_input("Name")
    email = st.text_input("Email")
    username = st.text_input("Username").lower().strip()
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        if not all([name, email, username, password]):
            st.error("All fields are required.")
        else:
            df = pd.read_csv(CSV_FILE)
            if username in df["username"].astype(str).str.lower().tolist():
                st.error("Username already exists.")
            else:
                with open(CSV_FILE, 'a', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                    writer.writerow({
                        'name': name.strip(),
                        'email': email.strip(),
                        'username': username,
                        'password': password
                    })
                st.success("Registration successful. You can now log in.")

# --- Login Page ---
if page == "Login":
    st.title("🔓 Login")
    login_user = st.text_input("Username").lower().strip()
    login_pass = st.text_input("Password", type="password").strip()

    if st.button("Login"):
        try:
            df = pd.read_csv(CSV_FILE)
            df["username"] = df["username"].astype(str).str.strip().str.lower()
            df["password"] = df["password"].astype(str).str.strip()

            if ((df["username"] == login_user) & (df["password"] == login_pass)).any():
                st.session_state.user = login_user
                st.success(f"Welcome back, {login_user}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
        except Exception as e:
            st.error(f"Error reading data: {e}")



    # --- Links Page ---
if page == "Links":
    st.title("🔗 Your Links")
    user = st.session_state.get("user", None)
    if not user:
        st.warning("Please login first.")
        st.stop()

    filepath = os.path.join(LINKS_DIR, f"{user}.csv")

    # Load links
    if "links" not in st.session_state:
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            st.session_state.links = df["link"].dropna().tolist()
        else:
            st.session_state.links = []

    # Delete handler
    def delete_link(index):
        st.session_state.links.pop(index)
        pd.DataFrame({"link": st.session_state.links}).to_csv(filepath, index=False)
        st.success("Link deleted!")
        st.rerun()

    # Show saved links with delete
    if st.session_state.links:
        st.subheader("Saved Links")
        for i, raw_link in enumerate(st.session_state.links):
            # Fix protocol
            fixed_link = raw_link.strip()
            if not fixed_link.startswith(("http://", "https://")):
                fixed_link = "https://" + fixed_link

            col1, col2 = st.columns([8, 1])
            with col1:
                st.markdown(
                    f"{i+1}. <a href='{fixed_link}' target='_blank' rel='noopener noreferrer'>🌐 {fixed_link}</a>",
                    unsafe_allow_html=True
                )
            with col2:
                if st.button("🗑️", key=f"delete_{i}"):
                    delete_link(i)

    # Add new link input
    if st.button("➕ Add New Link"):
        st.session_state.show_input = True

    if st.session_state.get("show_input", False):
        new_link = st.text_input("Enter link", key="new_link_input")
        if st.button("Save Link"):
            if new_link.strip():
                fixed_new_link = new_link.strip()
                if not fixed_new_link.startswith(("http://", "https://")):
                    fixed_new_link = "https://" + fixed_new_link
                st.session_state.links.append(fixed_new_link)
                pd.DataFrame({"link": st.session_state.links}).to_csv(filepath, index=False)
                st.success("Link saved!")
                st.rerun()
            else:
                st.warning("Please enter a valid link.")


# --- Profile Page ---
if page == "Profile":
    st.title("👤 Edit Profile")
    user = st.session_state.get("user", None)
    if not user:
        st.warning("Please login first.")
        st.stop()

    df = pd.read_csv(CSV_FILE)
    user_row = df[df["username"].str.lower() == user.lower()]

    if user_row.empty:
        st.error("User not found.")
        st.stop()

    idx = user_row.index[0]
    row = user_row.iloc[0]

    new_name = st.text_input("Name", row["name"])
    new_email = st.text_input("Email", row["email"])
    new_username = st.text_input("Username", row["username"])
    new_password = st.text_input("Password", row["password"], type="password")

    if st.button("Update Profile"):
        df.at[idx, "name"] = new_name
        df.at[idx, "email"] = new_email
        df.at[idx, "username"] = new_username
        df.at[idx, "password"] = new_password
        df.to_csv(CSV_FILE, index=False)

        # Rename link file if username changed
        old_path = os.path.join(LINKS_DIR, f"{user}.csv")
        new_path = os.path.join(LINKS_DIR, f"{new_username.lower().strip()}.csv")
        if user != new_username.lower().strip() and os.path.exists(old_path):
            os.rename(old_path, new_path)

        st.session_state.user = new_username.lower().strip()
        st.success("Profile updated!")
        st.rerun()
