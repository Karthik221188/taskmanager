import streamlit as st
import pandas as pd
from datetime import datetime, date
from io import BytesIO
import os
import plotly.express as px

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Task Manager", layout="wide")

TASK_FILE = "tasks.xlsx"
ADMIN_EMAIL = "admin@task.com"

STATUS_LIST = [
    "In Progress",
    "Completed",
    "Partially Completed",
    "Need Assistance"
]

# ---------------- INIT TASK FILE ----------------
if not os.path.exists(TASK_FILE):
    df_init = pd.DataFrame(columns=[
        "Task_Given_Date",
        "Task_Name",
        "Sort_Centre",
        "Task_Remarks",
        "Priority",
        "Due_Date",
        "Assigned_To",
        "Status",
        "Completion_Remarks",
        "Created_By"
    ])
    df_init.to_excel(TASK_FILE, index=False)

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:
    st.title("🔐 Task Manager Login")
    email = st.text_input("Email")
    if st.button("Login"):
        if "@task.com" in email:
            st.session_state.logged_in = True
            st.session_state.user = email
            st.session_state.role = "admin" if email == ADMIN_EMAIL else "user"
            st.rerun()
        else:
            st.error("Use company email (@task.com)")

# ---------------- MAIN APP ----------------
else:
    st.success(f"Logged in as {st.session_state.user} ({st.session_state.role})")

    df = pd.read_excel(TASK_FILE)
    df["Due_Date"] = pd.to_datetime(df["Due_Date"], errors="coerce").dt.date
    df["Task_Given_Date"] = pd.to_datetime(df["Task_Given_Date"], errors="coerce").dt.date

    # ---------------- CREATE TASK ----------------
    with st.expander("➕ Create New Task"):
        c1, c2, c3 = st.columns(3)
        task_name = c1.text_input("Task Name")
        sort_centre = c2.text_input("Sort Centre")
        priority = c3.selectbox("Priority", ["Low", "Medium", "High"])

        remarks = st.text_area("Task Remarks")
        due_date = st.date_input("Due Date", min_value=date.today())
        assigned_to = st.text_input("Assign To (email or everyone@task.com)")

        if st.button("Create Task"):
            new_task = {
                "Task_Given_Date": date.today(),
                "Task_Name": task_name,
                "Sort_Centre": sort_centre,
                "Task_Remarks": remarks,
                "Priority": priority,
                "Due_Date": due_date,
                "Assigned_To": assigned_to,
                "Status": "In Progress",
                "Completion_Remarks": "",
                "Created_By": st.session_state.user
            }
            df = pd.concat([df, pd.DataFrame([new_task])], ignore_index=True)
            df.to_excel(TASK_FILE, index=False)
            st.success("Task Created")
            st.rerun()

    # ---------------- FILTER VIEW ----------------
    if st.session_state.role == "admin":
        df_view = df.copy()
    else:
        df_view = df[
            (df["Assigned_To"] == st.session_state.user) |
            (df["Assigned_To"] == "everyone@task.com")
        ]

    # ---------------- KPIs ----------------
    st.subheader("📊 Task Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(df_view))
    c2.metric("In Progress", (df_view["Status"] == "In Progress").sum())
    c3.metric("Completed", (df_view["Status"] == "Completed").sum())
    c4.metric("Need Assistance", (df_view["Status"] == "Need Assistance").sum())

    # ---------------- TASK TABLE ----------------
    st.subheader("📋 Task Details")

    for i, row in df_view.iterrows():
        with st.expander(f"{row['Task_Name']} | Due: {row['Due_Date']}"):
            st.write("**Assigned To:**", row["Assigned_To"])
            st.write("**Priority:**", row["Priority"])
            st.write("**Remarks:**", row["Task_Remarks"])

            new_status = st.selectbox(
                "Update Status",
                STATUS_LIST,
                index=STATUS_LIST.index(row["Status"]),
                key=f"status_{i}"
            )

            completion_remark = st.text_input(
                "Completion Remarks",
                value=row["Completion_Remarks"],
                key=f"remark_{i}"
            )

            if st.button("Update", key=f"update_{i}"):
                df.loc[i, "Status"] = new_status
                df.loc[i, "Completion_Remarks"] = completion_remark
                df.to_excel(TASK_FILE, index=False)
                st.success("Updated")
                st.rerun()

            # Admin Reassign
            if st.session_state.role == "admin":
                new_user = st.text_input(
                    "Reassign Task",
                    value=row["Assigned_To"],
                    key=f"reassign_{i}"
                )
                if st.button("Reassign", key=f"rebtn_{i}"):
                    df.loc[i, "Assigned_To"] = new_user
                    df.to_excel(TASK_FILE, index=False)
                    st.success("Reassigned")
                    st.rerun()

    # ---------------- AGING ----------------
    st.subheader("⏳ Task Aging")
    df_view["Aging_Days"] = df_view["Due_Date"].apply(
        lambda x: (date.today() - x).days if pd.notna(x) else 0
    )
    st.dataframe(df_view[["Task_Name", "Assigned_To", "Aging_Days"]])

    # ---------------- USER PERFORMANCE ----------------
    st.subheader("📊 User-wise Performance")
    perf = df.groupby(["Assigned_To", "Status"]).size().reset_index(name="Count")
    fig = px.bar(perf, x="Assigned_To", y="Count", color="Status")
    st.plotly_chart(fig, use_container_width=True)

    # ---------------- EXPORT ----------------
    st.subheader("📥 Export")
    output = BytesIO()
    df_view.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    st.download_button(
        "Download Excel",
        data=output,
        file_name="tasks_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ---------------- LOGOUT ----------------
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()
