import streamlit as st
import os
import base64
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
TARGET_PATH = os.getenv("TARGET_PATH", "uploads")
BRANCH = os.getenv("BRANCH", "main")
LOCAL_BACKUP_DIR = "local_backups"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

st.set_page_config(page_title="Save to GitHub", page_icon="💾")
st.title("📁 Save Files to GitHub with Backup")

if 'user' not in st.session_state:
    st.session_state.user = None

# Login/logout UI
if st.session_state.user:
    st.sidebar.write(f"Logged in as: {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
else:
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username and password:
            st.session_state.user = username
            st.success("Logged in!")
            st.rerun()
        else:
            st.error("Please enter credentials")

if st.session_state.user:
    st.subheader("Choose Save Path in Repository")
    custom_path = st.text_input("Enter GitHub folder path", value=f"{TARGET_PATH}/{st.session_state.user}")

    st.subheader("Upload your file")
    uploaded_file = st.file_uploader("Choose a file to upload")
    if uploaded_file:
        file_content = uploaded_file.read()
        file_name = uploaded_file.name
        target_path = f"{custom_path.strip().strip('/')}/{file_name}"

        # Save button to control push
    if st.button("💾 Save to GitHub"):
            # Local backup
            local_user_dir = os.path.join(LOCAL_BACKUP_DIR, st.session_state.user)
            os.makedirs(local_user_dir, exist_ok=True)
            local_file_path = os.path.join(local_user_dir, file_name)
            with open(local_file_path, "wb") as f:
                f.write(file_content)

            st.info(f"✅ File also saved locally at: {local_file_path}")

            # Check if file already exists to get SHA
            sha = None
            check_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{target_path}?ref={BRANCH}"
            res = requests.get(check_url, headers=headers)
            if res.status_code == 200:
                sha = res.json().get("sha")

            encoded_content = base64.b64encode(file_content).decode("utf-8")

            data = {
                "message": f"Upload {file_name} by {st.session_state.user} on {datetime.utcnow().isoformat()} UTC",
                "content": encoded_content,
                "branch": BRANCH
            }
            if sha:
                data["sha"] = sha

            upload_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{target_path}"
            response = requests.put(upload_url, headers=headers, json=data)

            if response.status_code in (200, 201):
                st.success("✅ File saved to GitHub!")
                st.code(response.json().get("content", {}).get("path", ""))

                # Display Java file content
                if file_name.endswith(".java"):
                    st.subheader("📄 Java File Preview")
                    st.code(file_content.decode("utf-8"), language="java")

                # Show open file button
                raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{target_path}"
                st.markdown(f"[📂 Open File]({raw_url})", unsafe_allow_html=True)
                st.download_button("⬇️ Download File", file_content, file_name)
            else:
                st.error(f"❌ GitHub error: {response.status_code}")
                st.json(response.json())

    # List existing files for this user
    st.subheader("📜 Your Saved Files")
    user_dir_path = f"{TARGET_PATH}/{st.session_state.user}"
    list_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{user_dir_path}?ref={BRANCH}"
    list_response = requests.get(list_url, headers=headers)

    if list_response.status_code == 200:
        for file_info in list_response.json():
            file_name = file_info.get("name")
            file_path = file_info.get("path")
            raw_file_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{file_path}"
            st.markdown(f"📄 [{file_name}]({raw_file_url})", unsafe_allow_html=True)
            st.markdown(f"<a href='{raw_file_url}' download='{file_name}'><button>⬇️ Download</button></a>", unsafe_allow_html=True)
    elif list_response.status_code == 404:
        st.info("No files saved yet.")
    else:
        st.warning("Could not load saved files list.")
