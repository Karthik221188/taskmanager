import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from io import BytesIO
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="South Task Tower",
    layout="wide"
)

# ---------------- BRANDING ----------------
if os.path.exists("meesho_logo.png"):
    st.image("meesho_logo.png", width=160)
st.title("📌 South Area Manager Task Management Tower")

# ---------------- FILES ----------------
USERS_FILE = "users.xlsx"
TASK_FILE = "tasks.xlsx"
DEFAULT_PASSWORD = "Task@2026"

STATUS_LIST = [
    "In Progress",
    "Completed",
    "Partially Completed",
    "Need Assistance"
]

# ---------------- LOAD USERS ----------------
users = pd.read_excel(USERS_FILE)
users.columns = users.columns.str.lower().str.strip()

if "password" not in users.columns:
    users["password"] = DEFAULT_PASSWORD
    users.to_excel(USERS_FILE, index=False)

# ---------------- INIT TASK FILE ----------------
if not os.path.exists(TASK_FILE):
    pd.DataFrame(columns=[
        "Task_ID",
        "Task_Given_Date",
        "Task_Name",
        "Email_Subject",
        "Sort_Centre",
        "Task_Given",
        "Priority",
        "Due_Date",
        "Assigned_To",
        "Status",
        "Completion_Remarks",
        "Created_By",
        "Reminder"
    ]).to_excel(TASK_FILE, index=False)

# ---------------- SESSION ----------------
if "login" not in st.session_state:
    st.session_state.login = False

# ---------------- LOGIN ----------------
if not st.session_state.login:
    st.subheader("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if email in users["email"].values:
            stored_pwd = users.loc[users["email"] == email, "password"].values[0]
            if password == stored_pwd:
                st.session_state.login = True
                st.session_state.email = email
                st.session_state.role = users.loc[
                    users["email"] == email, "role"
                ].values[0]
                st.rerun()
            else:
                st.error("Incorrect password")
        else:
            st.error("Unauthorized email")

    st.stop()

# ---------------- MAIN APP ----------------
st.success(f"Logged in as {st.session_state.email} ({st.session_state.role})")

df = pd.read_excel(TASK_FILE)

# ---------------- SAFE COLUMNS ----------------
safe_columns = {
    "Created_By": "",
    "Email_Subject": "",
    "Task_Given": "",
    "Completion_Remarks": "",
    "Reminder": "No"
}
for col, default in safe_columns.items():
    if col not in df.columns:
        df[col] = default

# ---------------- DATE NORMALIZATION ----------------
df["Task_Given_Date"] = pd.to_datetime(df["Task_Given_Date"], errors="coerce").dt.date
df["Due_Date"] = pd.to_datetime(df["Due_Date"], errors="coerce").dt.date

# ---------------- 90 DAY FILTER ----------------
cutoff_date = date.today() - timedelta(days=90)
df = df[df["Task_Given_Date"] >= cutoff_date]

# ---------------- CREATE TASK ----------------
with st.expander("➕ Create New Task"):
    c1, c2, c3 = st.columns(3)
    task_name = c1.text_input("Task Name")
    email_subject = c2.text_input("Email Subject")
    priority = c3.selectbox("Priority", ["Low", "Medium", "High"])

    sort_centre = st.text_input("Sort Centre")
    task_given = st.text_area("Task Given")
    due_date = st.date_input("Due Date", min_value=date.today())

    assign_to = st.selectbox(
        "Assign To",
        ["everyone@task.com"] + users["email"].tolist()
    )

    if st.button("Create Task"):
        new = {
            "Task_ID": len(df) + 1,
            "Task_Given_Date": date.today(),
            "Task_Name": task_name,
            "Email_Subject": email_subject,
            "Sort_Centre": sort_centre,
            "Task_Given": task_given,
            "Priority": priority,
            "Due_Date": due_date,
            "Assigned_To": assign_to,
            "Status": "In Progress",
            "Completion_Remarks": "",
            "Created_By": st.session_state.email,
            "Reminder": "No"
        }
        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
        df.to_excel(TASK_FILE, index=False)
        st.success("Task Created")
        st.rerun()

# ---------------- ROLE VIEW ----------------
if st.session_state.role == "admin":
    df_view = df.copy()
else:
    df_view = df[
        (df["Assigned_To"] == st.session_state.email) |
        (df["Created_By"] == st.session_state.email) |
        (df["Assigned_To"] == "everyone@task.com")
    ]

# ---------------- METRICS ----------------
st.subheader("📊 Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total", len(df_view))
c2.metric("In Progress", (df_view["Status"] == "In Progress").sum())
c3.metric("Completed", (df_view["Status"] == "Completed").sum())
c4.metric("Need Assistance", (df_view["Status"] == "Need Assistance").sum())

# ---------------- ADMIN TABLE ----------------
if st.session_state.role == "admin":
    st.subheader("🧾 Admin Control Panel")
    edited = st.data_editor(
        df_view,
        use_container_width=True,
        disabled=["Task_ID", "Task_Given_Date"],
        num_rows="dynamic"
    )
    if st.button("💾 Save Admin Updates"):
        edited.to_excel(TASK_FILE, index=False)
        st.success("Saved")
        st.rerun()

# ---------------- TASK DETAILS ----------------
st.subheader("📋 Task Details")

for i, row in df_view.iterrows():
    with st.expander(f"{row['Task_Name']} | Due: {row['Due_Date']}"):
        st.write("📨 Email Subject:", row["Email_Subject"])
        st.write("👤 Given By:", row["Created_By"])
        st.write("👥 Assigned To:", row["Assigned_To"])
        st.write("🏢 Sort Centre:", row["Sort_Centre"])
        st.write("📝 Task Given:", row["Task_Given"])
        st.write("⚡ Priority:", row["Priority"])

        if st.session_state.role != "admin":
            status = st.selectbox(
                "Update Status",
                STATUS_LIST,
                index=STATUS_LIST.index(row["Status"]),
                key=f"s_{i}"
            )
            remark = st.text_input(
                "Completion Remarks",
                value=row["Completion_Remarks"],
                key=f"r_{i}"
            )
            if st.button("Update Task", key=f"u_{i}"):
                df.loc[i, "Status"] = status
                df.loc[i, "Completion_Remarks"] = remark
                df.to_excel(TASK_FILE, index=False)
                st.rerun()

        if st.session_state.role == "admin":
            if st.button("🔔 Send Reminder", key=f"rem_{i}"):
                df.loc[i, "Reminder"] = "Yes"
                df.to_excel(TASK_FILE, index=False)
                st.success("Reminder Sent")
                st.rerun()

# ---------------- AGING ----------------
st.subheader("⏳ Task Aging")
df_view["Aging_Days"] = df_view["Due_Date"].apply(
    lambda x: (date.today() - x).days if pd.notna(x) else 0
)
st.dataframe(df_view[["Task_Name", "Assigned_To", "Aging_Days"]])

# ---------------- PERFORMANCE ----------------
st.subheader("🏆 User Performance")
perf = df.groupby(["Assigned_To", "Status"]).size().reset_index(name="Count")
st.plotly_chart(px.bar(perf, x="Assigned_To", y="Count", color="Status"),
                use_container_width=True)

# ---------------- EXPORT ----------------
if st.session_state.role == "admin":
    output = BytesIO()
    df_view.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        "📥 Export Excel",
        output,
        "task_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------- PASSWORD CHANGE ----------------
with st.expander("🔑 Change Password"):
    new_pwd = st.text_input("New Password", type="password")
    if st.button("Update Password"):
        users.loc[users["email"] == st.session_state.email, "password"] = new_pwd
        users.to_excel(USERS_FILE, index=False)
        st.success("Password Updated")

# ---------------- LOGOUT ----------------
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()

