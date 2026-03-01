import streamlit as st
import pandas as pd
import os
import bcrypt
import sqlite3
import zipfile
import io
import plotly.express as px
from datetime import datetime
from database import DatabaseManager
from ai_interviewer import EvidenceInterviewer
from portfolio_manager import PortfolioManager
from fpdf import FPDF 

# --- PDF EXPORT FUNCTION ---
def export_portfolio_pdf(name, activities_df):
    """Generates a professional PDF report of student achievements."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Achievement Portfolio: {name}", ln=True, align='C')
    pdf.ln(10)
    
    for _, row in activities_df.iterrows():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, txt=f"Project: {row['title']}", ln=True)
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, txt=f"Date: {row['date']} | Grade: {row.get('grade_section', 'N/A')}", ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 8, txt=f"Summary: {row['summary']}")
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(
    page_title="EduTrack 360",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INITIALIZATION ---
@st.cache_resource
def init_system():
    db_mgr = DatabaseManager("school_portal.db")
    # It is recommended to move these to .streamlit/secrets.toml later
    GROQ_KEYS = [
        "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",
        "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"
    ]
    
    with db_mgr._get_connection() as conn:
        cols = [c[1] for c in conn.execute("PRAGMA table_info(activities)").fetchall()]
        if 'file_path' not in cols:
            conn.execute("ALTER TABLE activities ADD COLUMN file_path TEXT")
        if 'grade_section' not in cols:
            conn.execute("ALTER TABLE activities ADD COLUMN grade_section TEXT")
        conn.commit()
            
    return db_mgr, EvidenceInterviewer(GROQ_KEYS), PortfolioManager()

db, ai_core, pf_manager = init_system()

# --- 3. SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 
        'user': None, 
        'role': None, 
        'name': "", 
        'chat_history': [], 
        'interview_counter': -1, 
        'interview_complete': False,
        'pending_project': None, 
        'roadmap_chat': [], 
        'hobbies_set': False,
        'event_grade_context': "Grade 9"
    })

# --- 4. AUTHENTICATION ---
if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.title("🧭 EduTrack 360")
            sid = st.text_input("User ID")
            pwd = st.text_input("Password", type="password")
            if st.button("Sign In", width="stretch", type="primary"):
                user_data = db.verify_login(sid, pwd)
                if user_data:
                    st.session_state.update({
                        'logged_in': True, 'user': sid, 
                        'role': user_data['role'], 'name': user_data['name']
                    })
                    st.rerun()
                else:
                    st.error("Invalid ID or Password.")
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.success(f"User: {st.session_state.name}")
    st.caption(f"Role: {st.session_state.role}")
    st.divider()
    if st.button("Logout", width="stretch"):
        st.session_state.clear()
        st.rerun()

# --- 6. ADMIN DASHBOARD ---
if st.session_state.role == "Admin":
    st.title("🛡️ Admin Command Center")
    t_records, t_tagging, t_users, t_bulk, t_audit, t_gallery, t_insight = st.tabs([
        "📊 Academic Records", "🏷️ Mass Event Tagging", "👥 User Management", 
        "📤 Master Bulk Import", "🔍 Evidence Audit", "🖼️ Data Gallery", "🧠 AI Insights"
    ])
    
    with t_records:
        st.subheader("Academic Record Management")
        with db._get_connection() as conn:
            students = pd.read_sql("SELECT student_id, name FROM users WHERE role='Student'", conn)
        
        if not students.empty:
            target = st.selectbox("Select Student", options=students['student_id'], 
                                format_func=lambda x: f"{x} - {students[students['student_id']==x]['name'].values[0]}")
            
            with st.form("grade_entry", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                year = c1.number_input("Year", 2020, 2030, 2025)
                term = c2.selectbox("Term", ["Term 1", "Term 2", "Term 3", "Term 4"])
                subject = c3.text_input("Subject")
                mark = st.slider("Mark (%)", 0, 100, 75)
                if st.form_submit_button("Save Grade"):
                    db.update_grade(target, int(year), term, subject, mark)
                    st.success("Record Saved!")

            g_df, _ = db.get_student_profile(target)
            if not g_df.empty:
                st.divider()
                g_df['period'] = g_df['year'].astype(str) + " - " + g_df['term'].astype(str)
                fig = px.line(g_df, x='period', y='mark', color='subject', markers=True, title=f"Performance: {target}")
                st.plotly_chart(fig, use_container_width=True)

    with t_users:
        st.subheader("👥 User Management")
        col_create, col_roster = st.columns([1, 2])
        with col_create:
            with st.form("new_user_form"):
                n_id = st.text_input("User ID")
                n_name = st.text_input("Name")
                n_pw = st.text_input("Password", type="password")
                n_role = st.selectbox("Role", ["Student", "Admin"])
                if st.form_submit_button("Register"):
                    db.create_user(n_id, n_name, n_pw, n_role)
                    st.rerun()
        with col_roster:
            users_df, _, _ = db.get_all_data_for_export()
            st.dataframe(users_df, use_container_width=True)

    with t_audit:
        st.subheader("🔍 Pending Evidence Audit")
        with db._get_connection() as conn:
            pending = pd.read_sql("SELECT * FROM activities WHERE status='pending'", conn)
        for _, r in pending.iterrows():
            with st.container(border=True):
                st.write(f"**{r['student_id']}** - {r['title']}")
                if st.button("✅ Approve", key=f"app_{r['id']}"):
                    with db._get_connection() as conn:
                        conn.execute("UPDATE activities SET status='approved' WHERE id=?", (r['id'],))
                    st.rerun()

# --- 7. STUDENT VIEW ---
else:
    st.title(f"Student Portal")
    t_ai, t_port, t_road = st.tabs(["💬 Achievement Journalist", "📂 Portfolio", "🤖 Career Mentor"])

    with t_ai:
        if st.session_state.interview_counter == -1:
            st.session_state.event_grade_context = st.selectbox("Grade Level:", [f"Grade {i}" for i in range(1,13)])
        
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if not st.session_state.interview_complete:
            if p := st.chat_input("Log your success..."):
                st.session_state.interview_counter += 1
                st.session_state.chat_history.append({"role": "user", "content": p})
                res = ai_core.get_ai_response(p, st.session_state.chat_history, st.session_state.interview_counter)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                if "SAVE_DATA" in res:
                    data = res.split("SAVE_DATA")[1].strip(": ").split("|")
                    st.session_state.pending_project = {"title": data[1].strip(), "skills": data[2].strip(), "summary": data[3].strip()}
                    st.session_state.interview_complete = True
                st.rerun()
        else:
            with st.form("finalize"):
                up_img = st.file_uploader("Upload Evidence", type=['jpg','png','jpeg'])
                if st.form_submit_button("Save to Portfolio") and up_img:
                    path = pf_manager.save_evidence(st.session_state.user, up_img)
                    db.save_activity(st.session_state.user, st.session_state.pending_project['title'], 
                                     st.session_state.pending_project['summary'], st.session_state.pending_project['skills'], path)
                    st.session_state.update({'interview_complete': False, 'chat_history': [], 'interview_counter': -1})
                    st.rerun()

    with t_port:
        g_data, a_data = db.get_student_profile(st.session_state.user)
        
        # PDF DOWNLOAD SECTION
        if not a_data.empty:
            pdf_bytes = export_portfolio_pdf(st.session_state.name, a_data)
            st.download_button(label="📥 Export Portfolio (PDF)", data=pdf_bytes, 
                               file_name=f"{st.session_state.name}_Portfolio.pdf", mime="application/pdf")
            st.divider()

        for idx, row in a_data.iterrows():
            with st.container(border=True):
                st.subheader(row['title'])
                if row['file_path']: st.image(row['file_path'], width=300)
                st.write(row['summary'])
                if st.button("🗑️ Delete", key=f"del_{idx}"):
                    db.delete_activity(st.session_state.user, row['title'], row['date'])
                    st.rerun()

    with t_road:
        st.subheader("🤖 Career Mentor")
        for msg in st.session_state.roadmap_chat:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if q := st.chat_input("Ask about your future..."):
            st.session_state.roadmap_chat.append({"role": "user", "content": q})
            res = ai_core.get_career_roadmap(g_data, a_data, q)
            st.session_state.roadmap_chat.append({"role": "assistant", "content": res})
            st.rerun()