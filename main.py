import flet as ft
import os
import csv
import base64
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Env config
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
BRANCH = os.getenv("BRANCH", "main")
USERS_CSV = os.getenv("USERS_CSV", "users.csv")
LOCAL_DIR = os.getenv("LOCAL_DIR", "local_backup")

os.makedirs(LOCAL_DIR, exist_ok=True)
if not os.path.exists(USERS_CSV):
    with open(USERS_CSV, "w", newline='') as f:
        csv.writer(f).writerow(["username", "password", "recovery_hint"])


def load_users():
    users = {}
    with open(USERS_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users[row["username"]] = {
                "password": row["password"],
                "recovery_hint": row["recovery_hint"]
            }
    return users

def save_user(username, password, hint):
    with open(USERS_CSV, "a", newline='') as f:
        csv.writer(f).writerow([username, password, hint])

def save_to_github(user, file_name, content_bytes, target_path="saving"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6]
    path = f"{target_path}/{user}/uploads/{timestamp}_{unique_id}_{file_name}"
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    encoded = base64.b64encode(content_bytes).decode("utf-8")

    payload = {
        "message": f"Upload by {user}",
        "content": encoded,
        "branch": BRANCH
    }

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.put(url, json=payload, headers=headers)
    if response.status_code in [200, 201]:
        return True, response.json()["content"]["path"]
    else:
        return False, response.json()

def main(page: ft.Page):
    page.title = "Flet File Saver"
    page.scroll = "auto"

    users = load_users()
    github_path = ft.TextField(label="GitHub Folder Path", value="saving", expand=True)
    message = ft.Text()
    current_user = {"name": None}

    def logout():
        current_user["name"] = None
        page.session.clear()
        page.clean()
        login_register_ui()

    def login_register_ui():
        login_username = ft.TextField(label="Username")
        login_password = ft.TextField(label="Password", password=True)

        register_username = ft.TextField(label="New Username")
        register_password = ft.TextField(label="New Password", password=True)
        register_hint = ft.TextField(label="Recovery Hint")

        login_msg = ft.Text()
        register_msg = ft.Text()

        def do_login(e):
            u, p = login_username.value, login_password.value
            if u in users and users[u]["password"] == p:
                current_user["name"] = u
                page.clean()
                app_ui(u)
            else:
                login_msg.value = "❌ Invalid login credentials"
                page.update()

        def do_register(e):
            u, p, h = register_username.value, register_password.value, register_hint.value
            if not u or not p or not h:
                register_msg.value = "⚠️ Fill all fields"
            elif u in users:
                register_msg.value = "⚠️ Username already exists"
            else:
                save_user(u, p, h)
                register_msg.value = "✅ Registered! Now login."
            page.update()

        tabs = ft.Tabs(
            selected_index=0,
            expand=True,
            tabs=[
                ft.Tab(
                    text="Login",
                    content=ft.Column([
                        login_username,
                        login_password,
                        ft.ElevatedButton("Login", on_click=do_login),
                        login_msg
                    ])
                ),
                ft.Tab(
                    text="Register",
                    content=ft.Column([
                        register_username,
                        register_password,
                        register_hint,
                        ft.ElevatedButton("Register", on_click=do_register),
                        register_msg
                    ])
                ),
            ]
        )
        page.add(ft.Text("🔐 Welcome to File Saver", size=24), tabs)

    def app_ui(user):
        page.clean()

        selected_file = {"name": None, "path": None, "bytes": None}

        def file_picker_result(e: ft.FilePickerResultEvent):
            if e.files:
                file = e.files[0]
                selected_file["name"] = file.name
                selected_file["path"] = file.path
                with open(file.path, "rb") as f:
                    selected_file["bytes"] = f.read()
                message.value = f"Selected file: {file.name}"
                page.update()

        def upload_local(e):
            if not selected_file["bytes"]:
                message.value = "No file selected!"
                page.update()
                return
            user_dir = os.path.join(LOCAL_DIR, user)
            os.makedirs(user_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_name = f"{timestamp}_{selected_file['name']}"
            local_path = os.path.join(user_dir, local_name)
            with open(local_path, "wb") as f:
                f.write(selected_file["bytes"])
            message.value = f"✅ File saved locally: {local_name}"
            app_ui(user)

        def upload_github(e):
            if not selected_file["bytes"]:
                message.value = "No file selected!"
                page.update()
                return
            success, result = save_to_github(user, selected_file["name"], selected_file["bytes"], github_path.value)
            if success:
                message.value = f"✅ Uploaded to GitHub: {result}"
            else:
                message.value = f"❌ GitHub error: {result}"
            app_ui(user)

        def list_github_files():
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{github_path.value}/{user}/uploads"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                return r.json()
            return []

        def delete_github_file(path):
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            get_resp = requests.get(url, headers=headers)
            if get_resp.status_code != 200:
                message.value = "File not found on GitHub."
                page.update()
                return
            sha = get_resp.json()["sha"]
            delete_payload = {
                "message": f"Delete by {user}",
                "sha": sha,
                "branch": BRANCH
            }
            delete_resp = requests.delete(url, json=delete_payload, headers=headers)
            if delete_resp.status_code == 200:
                message.value = f"✅ Deleted from GitHub: {path}"
                app_ui(user)
            else:
                message.value = f"❌ GitHub deletion failed"
            page.update()

        def delete_local(path):
            try:
                os.remove(path)
                message.value = f"🗑️ Deleted: {os.path.basename(path)}"
                app_ui(user)
            except Exception as ex:
                message.value = f"Error deleting: {ex}"
            page.update()

        upload_picker = ft.FilePicker(on_result=file_picker_result)
        page.overlay.append(upload_picker)

        page.add(
            ft.Row([
                ft.Text(f"📋 Logged in as: {user}", expand=1),
                ft.ElevatedButton("Logout", on_click=lambda e: logout())
            ]),
            github_path,
            ft.Row([
                ft.ElevatedButton("📂 Select File", on_click=lambda _: upload_picker.pick_files()),
                ft.ElevatedButton("⬆️ Upload to Local", on_click=upload_local),
                ft.ElevatedButton("☁️ Upload to GitHub", on_click=upload_github)
            ]),
            message,
            ft.Divider(),

            ft.Text("📁 Local Files", size=20, weight="bold")
        )

        # List local files
        user_dir = os.path.join(LOCAL_DIR, user)
        if os.path.exists(user_dir):
            files = sorted(os.listdir(user_dir))
            for file in files:
                fpath = os.path.join(user_dir, file)
                with open(fpath, "rb") as f:
                    data = f.read()
                row = ft.Row([
                    ft.Text(file, expand=1),
                    ft.ElevatedButton("⬇️ Download", on_click=lambda e, d=data: page.launch_url(f"data:application/octet-stream;base64,{base64.b64encode(d).decode()}")),
                    ft.IconButton(icon=ft.icons.DELETE, on_click=lambda e, p=fpath: delete_local(p))
                ])
                page.add(row)
        else:
            page.add(ft.Text("No local files found."))

        # GitHub Files
        page.add(ft.Divider(), ft.Text("☁️ GitHub Files", size=20, weight="bold"))
        github_files = list_github_files()
        if github_files:
            for f in github_files:
                row = ft.Row([
                    ft.Text(f["name"], expand=1),
                    ft.TextButton("🌐 Open", url=f["html_url"]),
                    ft.IconButton(icon=ft.icons.DELETE, on_click=lambda e, p=f["path"]: delete_github_file(p))
                ])
                page.add(row)
        else:
            page.add(ft.Text("No GitHub files found."))

    login_register_ui()

ft.app(target=main)
