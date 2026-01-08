import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# ---------------- CONFIG ----------------
PASSWORD = "Task@2026"
USERS_FILE = "users.xlsx"
TASK_FILE = "tasks.xlsx"

st.set_page_config("Task Control Tower", layout="wide")

# ---------------- LOAD USERS ----------------
users = pd.read_excel(USERS_FILE)
users.columns = users.columns.str.lower().str.strip()

# ---------------- SESSION ----------------
if "login" not in st.session_state:
    st.session_state.login = False

# ---------------- LOGIN ----------------
if not st.session_state.login:
    st.title("🔐 Task Control Tower")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if email in users["email"].values and password == PASSWORD:
            st.session_state.login = True
            st.session_state.email = email
            st.session_state.role = users.loc[
                users["email"] == email, "role"
            ].values[0]
            st.rerun()
        else:
            st.error("Invalid login")

# ---------------- MAIN APP ----------------
else:
    st.success(f"Logged in as {st.session_state.email} ({st.session_state.role})")

    # -------- INIT TASK FILE --------
    if not os.path.exists(TASK_FILE):
        pd.DataFrame(columns=[
            "Task_ID","Task_Given_Date","Task_Name","Sort_Centre",
            "Task_Remarks","Priority","Due_Date","Assigned_To",
            "Status","Completion_Remarks","Last_Updated","Reminder"
        ]).to_excel(TASK_FILE, index=False)

    df = pd.read_excel(TASK_FILE)

    # -------- DATE NORMALIZATION --------
    df["Task_Given_Date"] = pd.to_datetime(df["Task_Given_Date"], errors="coerce")
    df["Due_Date"] = pd.to_datetime(df["Due_Date"], errors="coerce")
    df["Last_Updated"] = pd.to_datetime(df["Last_Updated"], errors="coerce")

    # -------- AGING DAYS (FIXED) --------
    today = pd.to_datetime(datetime.now().date())
    df["Aging_Days"] = (today - df["Due_Date"]).dt.days

    # ---------------- CREATE TASK (ADMIN + USER) ----------------
    st.header("➕ Create Task")

    c1, c2, c3 = st.columns(3)
    task = c1.text_input("Task Name")
    centre = c2.text_input("Sort Centre")
    assign_to = c3.selectbox("Assign To", users["email"].unique())

    c4, c5, c6 = st.columns(3)
    remarks = c4.text_input("Why task given")
    priority = c5.selectbox("Priority", ["Low","Medium","High"])
    due = c6.date_input("Due Date")

    if st.button("Create Task"):
        new = {
            "Task_ID": len(df) + 1,
            "Task_Given_Date": datetime.now(),
            "Task_Name": task,
            "Sort_Centre": centre,
            "Task_Remarks": remarks,
            "Priority": priority,
            "Due_Date": due,
            "Assigned_To": assign_to,
            "Status": "In Progress",
            "Completion_Remarks": "",
            "Last_Updated": datetime.now(),
            "Reminder": "No"
        }
        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
        df.to_excel(TASK_FILE, index=False)
        st.success("Task created")
        st.rerun()

    # ---------------- FILTER VIEW ----------------
    if st.session_state.role == "user":
        df_view = df[df["Assigned_To"].isin([st.session_state.email, "everyone@task.com"])]
    else:
        df_view = df.copy()

    # ---------------- DASHBOARD METRICS ----------------
    st.header("📊 Overview")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", len(df_view))
    m2.metric("In Progress", len(df_view[df_view["Status"]=="In Progress"]))
    m3.metric("Completed", len(df_view[df_view["Status"]=="Task Completed"]))
    m4.metric("Partial", len(df_view[df_view["Status"]=="Partially Completed"]))
    m5.metric("Need Help", len(df_view[df_view["Status"]=="Need Assistance"]))

    # ---------------- ADMIN TABLE ----------------
    if st.session_state.role == "admin":
        st.header("🧾 Admin Control Table")

        admin_df = st.data_editor(
            df_view,
            use_container_width=True,
            disabled=["Task_ID","Task_Given_Date"],
            num_rows="dynamic"
        )

        if st.button("💾 Save Admin Updates"):
            admin_df.to_excel(TASK_FILE, index=False)
            st.success("Admin changes saved")
            st.rerun()

    # ---------------- KANBAN BOARD ----------------
    st.header("📌 Kanban Board")

    cols = st.columns(4)
    statuses = ["In Progress","Task Completed","Partially Completed","Need Assistance"]

    for col, status in zip(cols, statuses):
        with col:
            st.subheader(status)
            for _, r in df_view[df_view["Status"]==status].iterrows():
                st.markdown(f"""
                **{r['Task_Name']}**  
                Assigned: {r['Assigned_To']}  
                Due: {r['Due_Date'].date() if pd.notna(r['Due_Date']) else "-"}  
                ⏳ Aging: {r['Aging_Days']} days  
                🔔 Reminder: {r['Reminder']}
                """)

                if st.session_state.role == "admin":
                    if st.button("🔔 Reminder", key=f"rem_{r['Task_ID']}"):
                        df.loc[df["Task_ID"]==r["Task_ID"],"Reminder"]="Yes"
                        df.to_excel(TASK_FILE, index=False)
                        st.rerun()

    # ---------------- PERFORMANCE RANKING ----------------
    st.header("🏆 User Performance Ranking")

    rank = df[df["Status"]=="Task Completed"].groupby("Assigned_To").size().reset_index(name="Completed")
    st.plotly_chart(px.bar(rank, x="Assigned_To", y="Completed"), use_container_width=True)

    # ---------------- EXPORT ----------------
    if st.session_state.role == "admin":
        st.download_button(
            "📥 Export to Excel",
            df_view.to_excel(index=False),
            "task_export.xlsx"
        )

    # ---------------- LOGOUT ----------------
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()
