import streamlit as st
import pandas as pd
import os
import bcrypt
from database import DatabaseManager
from ai_interviewer import EvidenceInterviewer
from portfolio_manager import PortfolioManager

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(
    page_title="Scholar Stream",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INITIALIZATION ---
@st.cache_resource
def init_system():
    # Make sure to set your GEMINI_API_KEY in .streamlit/secrets.toml
    api_key = st.secrets.get("GEMINI_API_KEY", "your_fallback_key_here")
    db_mgr = DatabaseManager("school_portal.db")
    return db_mgr, EvidenceInterviewer(api_key), PortfolioManager()

db, ai_core, pf_manager = init_system()

# --- 3. SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 'user': None, 'role': None, 'name': "", 
        'chat_history': [], 'interview_counter': -1, 'interview_complete': False,
        'pending_project': None, 'roadmap_chat': [], 'hobbies_set': False,
        'event_grade_context': "Grade 10"
    })

# --- 4. AUTHENTICATION ---
if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.title("🔐 Secure Login")
            sid = st.text_input("User ID")
            pwd = st.text_input("Password", type="password")
            if st.button("Enter Portal", use_container_width=True, type="primary"):
                user_data = db.verify_login(sid, pwd)
                if user_data:
                    st.session_state.update({
                        'logged_in': True, 'user': sid, 
                        'role': user_data['role'], 'name': user_data['name']
                    })
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.success(f"👤 {st.session_state.name}")
    st.caption(f"Role: {st.session_state.role}")
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 6. ADMIN DASHBOARD ---
if st.session_state.role == "Admin":
    st.title("🛡️ Admin Strategic Command")
    t_records, t_insight, t_audit = st.tabs(["📊 Records", "🧠 AI Strategic Insights", "🔍 Audit Queue"])

    with t_insight:
        # Load students for the selector
        with db._get_connection() as conn:
            students = pd.read_sql("SELECT student_id, name FROM users WHERE role='Student'", conn)
        
        if not students.empty:
            target = st.selectbox("Select Student for Analysis", options=students['student_id'], 
                                 format_func=lambda x: f"{x} - {students[students['student_id']==x]['name'].values[0]}")
            
            if st.button("Generate Strategic Report", type="primary"):
                g_data, a_data = db.get_student_profile(target)
                with st.spinner("Synthesizing student trajectory..."):
                    report = ai_core.get_career_roadmap(g_data, a_data, "ADMIN_MODE: FUTURE PERSPECTIVE | AREAS TO IMPROVE")
                    st.markdown("---")
                    st.markdown(report)
        else:
            st.info("No students found in database.")

    with t_audit:
        with db._get_connection() as conn:
            all_a = pd.read_sql("SELECT * FROM activities ORDER BY date DESC", conn)
        
        for idx, r in all_a.iterrows():
            with st.container(border=True):
                ca, cb = st.columns([4, 1])
                ca.write(f"**Student:** {r['student_id']} | **Project:** {r['title']}")
                if r['file_path'] and os.path.exists(r['file_path']): 
                    ca.image(r['file_path'], width=200)
                if cb.button("🗑️ Delete", key=f"aud_del_{idx}"):
                    pf_manager.delete_evidence(r['file_path']) # Delete file too!
                    db.delete_activity(r['student_id'], r['title'], r['date'])
                    st.rerun()

# --- 7. STUDENT VIEW ---
else:
    st.title(f"🚀 Student Portal")
    t_ai, t_port, t_road = st.tabs(["💬 Achievement Journalist", "📂 Portfolio & Entry", "🤖 Career Mentor"])

    with t_ai:
        col_h, col_r = st.columns([3, 1])
        col_h.subheader("💬 Log Your Success")
        if col_r.button("🔄 Redo Interview", use_container_width=True):
            st.session_state.update({'interview_complete': False, 'chat_history': [], 'interview_counter': -1})
            st.rerun()

        if st.session_state.interview_counter == -1:
            st.session_state.event_grade_context = st.selectbox("Grade level for this achievement:", ["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"])

        for m in st.session_state.chat_history:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if not st.session_state.interview_complete:
            if p := st.chat_input("Tell me what you did..."):
                st.session_state.interview_counter += 1
                st.session_state.chat_history.append({"role": "user", "content": p})
                res = ai_core.get_ai_response(p, st.session_state.chat_history, st.session_state.interview_counter)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                
                if "SAVE_DATA" in res:
                    try:
                        data = res.split("SAVE_DATA")[1].strip(": ").split("|")
                        st.session_state.pending_project = {"title": data[1].strip(), "skills": data[2].strip(), "summary": data[3].strip()}
                        st.session_state.interview_complete = True
                    except: st.error("AI format error. Keep talking.")
                st.rerun()
        else:
            with st.form("save_ai"):
                st.success("Draft Generated!")
                st.write(f"**Title:** {st.session_state.pending_project['title']}")
                up = st.file_uploader("Evidence", type=['jpg','png'])
                if st.form_submit_button("Save to Portfolio") and up:
                    path = pf_manager.save_evidence(st.session_state.user, up)
                    db.save_activity(st.session_state.user, st.session_state.pending_project['title'], 
                                     st.session_state.pending_project['summary'], 
                                     st.session_state.pending_project['skills'], path)
                    st.session_state.update({'interview_complete': False, 'chat_history': [], 'interview_counter': -1})
                    st.rerun()

    with t_port:
        c_list, c_man = st.columns([2, 1])
        with c_man:
            with st.form("manual"):
                st.subheader("📝 Manual Entry")
                mt = st.text_input("Title")
                ms = st.text_input("Skills")
                md = st.text_area("Summary")
                mi = st.file_uploader("Image", type=['jpg','png'])
                if st.form_submit_button("Save"):
                    path = pf_manager.save_evidence(st.session_state.user, mi) if mi else None
                    db.save_activity(st.session_state.user, mt, md, ms, path)
                    st.rerun()

        with c_list:
            g_data, a_data = db.get_student_profile(st.session_state.user)
            for idx, row in a_data.iterrows():
                with st.container(border=True):
                    st.subheader(row['title'])
                    if row['file_path'] and os.path.exists(row['file_path']): 
                        st.image(row['file_path'], use_container_width=True)
                    st.write(row['summary'])
                    if st.button("🗑️", key=f"del_{idx}"):
                        pf_manager.delete_evidence(row['file_path'])
                        db.delete_activity(st.session_state.user, row['title'], row['date'])
                        st.rerun()

    with t_road:
        st.subheader("🤖 Career Mentor")
        if st.button("Clear Chat"): st.session_state.roadmap_chat = []; st.rerun()
        for msg in st.session_state.roadmap_chat:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if q := st.chat_input("Ask me about your career path..."):
            st.session_state.roadmap_chat.append({"role": "user", "content": q})
            res = ai_core.get_career_roadmap(g_data, a_data, q)
            st.session_state.roadmap_chat.append({"role": "assistant", "content": res})
            st.rerun()