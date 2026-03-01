import streamlit as st
import pandas as pd
import os
import bcrypt
import plotly.express as px
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
    db_mgr = DatabaseManager("school_portal.db")
    # Replace with your actual Groq Keys
    GROQ_KEYS = [
        "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",
        "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"
    ]
    
    # Auto-migration for required database columns
    with db_mgr._get_connection() as conn:
        cols = [c[1] for c in conn.execute("PRAGMA table_info(activities)").fetchall()]
        required_cols = [
            ('file_path', 'TEXT'), ('grade_section', 'TEXT'),
            ('future_perspective', 'TEXT'), ('areas_to_improve', 'TEXT'), ('help_needed', 'TEXT')
        ]
        for col_name, col_type in required_cols:
            if col_name not in cols:
                conn.execute(f"ALTER TABLE activities ADD COLUMN {col_name} {col_type}")
        conn.commit()
            
    return db_mgr, EvidenceInterviewer(GROQ_KEYS), PortfolioManager()

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

    with db._get_connection() as conn:
        students = pd.read_sql("SELECT student_id, name FROM users WHERE role='Student'", conn)

    with t_insight:
        target = st.selectbox("Select Student for Analysis", options=students['student_id'], 
                              format_func=lambda x: f"{x} - {students[students['student_id']==x]['name'].values[0]}")
        if st.button("Generate Strategic Report", type="primary"):
            g_data, a_data = db.get_student_profile(target)
            with st.spinner("Synthesizing student trajectory..."):
                report = ai_core.get_career_roadmap(g_data, a_data, "ADMIN_MODE: FUTURE PERSPECTIVE | AREAS TO IMPROVE | HELP NEEDED")
                st.markdown("---")
                st.markdown(report)

    with t_audit:
        with db._get_connection() as conn:
            all_a = pd.read_sql("SELECT * FROM activities ORDER BY date DESC", conn)
        for idx, r in all_a.iterrows():
            with st.container(border=True):
                ca, cb = st.columns([4, 1])
                ca.write(f"**Student:** {r['student_id']} | **Project:** {r['title']}")
                if r['file_path']: ca.image(r['file_path'], width=300)
                if cb.button("🗑️ Delete", key=f"aud_del_{idx}"):
                    db.delete_activity(r['student_id'], r['title'], r['date'])
                    st.rerun()

# --- 7. STUDENT VIEW ---
else:
    st.title(f"🚀 Student Portal")
    t_ai, t_port, t_road = st.tabs(["💬 Achievement Journalist", "📂 Portfolio & Manual Entry", "🤖 Career Mentor"])

    # --- TAB 1: AI INTERVIEWER (6 ROUNDS) ---
    with t_ai:
        col_h, col_r = st.columns([3, 1])
        col_h.subheader("💬 Log Your Success")
        if col_r.button("🔄 Redo Interview", use_container_width=True):
            st.session_state.update({'interview_complete': False, 'chat_history': [], 'interview_counter': -1, 'pending_project': None})
            st.rerun()

        # Phase A: Initial Grade Context
        if st.session_state.interview_counter == -1:
            st.session_state.event_grade_context = st.selectbox(
                "Which grade level does this achievement belong to?",
                ["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "University"]
            )
            st.info("Start the conversation below by mentioning your achievement.")

        # Display Chat History
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        # Phase B: The 6-Round Conversation
        if not st.session_state.interview_complete:
            # Visual Progress Bar
            progress_val = min((st.session_state.interview_counter + 2) / 6, 1.0)
            st.progress(progress_val, text=f"Interview Depth: {int(progress_val*100)}%")

            if p := st.chat_input("Tell me what you did..."):
                st.session_state.interview_counter += 1
                st.session_state.chat_history.append({"role": "user", "content": p})
                
                with st.spinner("Journalist is typing..."):
                    # Logic note: ai_interviewer should trigger SAVE_DATA at counter == 5
                    res = ai_core.get_ai_response(p, st.session_state.chat_history, st.session_state.interview_counter)
                
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                
                if "SAVE_DATA" in res:
                    try:
                        data = res.split("SAVE_DATA")[1].strip(": ").split("|")
                        st.session_state.pending_project = {
                            "grade": st.session_state.event_grade_context,
                            "title": data[1].strip(), 
                            "skills": data[2].strip(), "summary": data[3].strip()
                        }
                        st.session_state.interview_complete = True
                    except: st.error("AI Error. Please reply one more time.")
                st.rerun()

        # Phase C: The Evidence BBox
        else:
            with st.container(border=True):
                st.success("📝 Report Ready!")
                st.markdown(f"**Project:** {st.session_state.pending_project['title']} ({st.session_state.event_grade_context})")
                st.write(f"**Draft Summary:** {st.session_state.pending_project['summary']}")
                
                with st.form("finalize_ai_entry"):
                    up_img = st.file_uploader("Upload Image Proof (Mandatory)", type=['jpg','png','jpeg'])
                    if st.form_submit_button("🚀 Finalize & Save to Portfolio") and up_img:
                        path = pf_manager.save_evidence(st.session_state.user, up_img)
                        db.save_activity(st.session_state.user, st.session_state.pending_project['title'], 
                                         st.session_state.pending_project['summary'], 
                                         st.session_state.pending_project['skills'], path)
                        
                        # Apply Grade Selection
                        with db._get_connection() as conn:
                            conn.execute("UPDATE activities SET grade_section=? WHERE student_id=? AND title=?", 
                                         (st.session_state.event_grade_context, st.session_state.user, st.session_state.pending_project['title']))
                        
                        st.session_state.update({'interview_complete': False, 'chat_history': [], 'interview_counter': -1})
                        st.rerun()

    # --- TAB 2: PORTFOLIO & MANUAL ENTRY ---
    with t_port:
        c_list, c_man = st.columns([2, 1])
        
        with c_man:
            with st.form("manual_entry_form", clear_on_submit=True):
                st.subheader("📝 Manual Entry")
                m_title = st.text_input("Project Title")
                m_grade = st.selectbox("Grade Level", ["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"])
                m_skills = st.text_input("Skills (e.g. Coding, Leadership)")
                m_desc = st.text_area("Summary of Event")
                m_img = st.file_uploader("Evidence Image", type=['jpg','png','jpeg'])
                if st.form_submit_button("Add Manually"):
                    path = pf_manager.save_evidence(st.session_state.user, m_img) if m_img else None
                    db.save_activity(st.session_state.user, m_title, m_desc, m_skills, path)
                    with db._get_connection() as conn:
                        conn.execute("UPDATE activities SET grade_section=? WHERE student_id=? AND title=?", 
                                     (m_grade, st.session_state.user, m_title))
                    st.rerun()

        with c_list:
            st.subheader("📂 Your Portfolio")
            g_data, a_data = db.get_student_profile(st.session_state.user)
            if not a_data.empty:
                for idx, row in a_data.iterrows():
                    with st.container(border=True):
                        st.markdown(f"### {row['title']}")
                        st.caption(f"Grade: {row.get('grade_section', 'N/A')} | Date: {row['date']}")
                        if row['file_path']: st.image(row['file_path'], use_container_width=True)
                        st.write(row['summary'])
                        if st.button("🗑️ Delete", key=f"std_del_{idx}"):
                            db.delete_activity(st.session_state.user, row['title'], row['date'])
                            st.rerun()

    # --- TAB 3: CAREER MENTOR CHATBOT ---
    with t_road:
        st.subheader("🤖 Career Mentor")
        if not st.session_state.hobbies_set:
            h = st.text_area("Tell the AI your hobbies and dream jobs:")
            if st.button("Initialize Mentor"):
                st.session_state.update({'hobbies_set': True, 'roadmap_chat': [{"role": "assistant", "content": "Ready! Ask me anything about your future path."}]})
                st.rerun()
        else:
            for msg in st.session_state.roadmap_chat:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
            if q := st.chat_input("Ask about your career..."):
                st.session_state.roadmap_chat.append({"role": "user", "content": q})
                res = ai_core.get_career_roadmap(g_data, a_data, f"Chat Context: {st.session_state.roadmap_chat}. User Question: {q}")
                st.session_state.roadmap_chat.append({"role": "assistant", "content": res})
                st.rerun()