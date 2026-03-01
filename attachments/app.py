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
from fpdf import FPDF # Add this to your imports

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
    page_title="Scholar Stream",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)
# --- 2. INITIALIZATION ---
@st.cache_resource
def init_system():
    db_mgr = DatabaseManager("school_portal.db")
    # Using your provided Groq Keys
    GROQ_KEYS = [
        "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",
        "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",
        ""
    ]
    
    # DB Maintenance: Ensure all new columns exist
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
# --- SESSION STATE INITIALIZATION ---
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
            st.title("Scholar Stream")
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
    st.success(f"{st.session_state.name}")
    st.caption(f"Role: {st.session_state.role}")
    st.divider()
    if st.button("Logout", width="stretch"):
        st.session_state.clear()
        st.rerun()

# --- 6. ADMIN DASHBOARD (Extended) ---
if st.session_state.role == "Admin":
    st.title(" Admin Command Center")
    
    t_records, t_tagging, t_users, t_bulk, t_audit, t_gallery, t_insight = st.tabs([
        "📊 Academic Records", 
        "🏷️ Mass Event Tagging",
        "👥 User Management", 
        "📤 Master Bulk Import", 
        "🔍 Evidence Audit",
        "🖼️ Data Gallery",
        "🔍 Students AI Insights"

    ])
    
    # --- TAB 1: ACADEMIC RECORDS ---
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
                term_order = ["Term 1", "Term 2", "Term 3", "Term 4"]
                g_df['term'] = pd.Categorical(g_df['term'], categories=term_order, ordered=True)
                g_df = g_df.sort_values(['year', 'term'])
                
                fig = px.line(g_df, x='period', y='mark', color='subject', markers=True,
                            title=f"Performance History: {target}")
                fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Pass Mark")
                st.plotly_chart(fig, width="stretch")


        st.subheader("📊 Database Management")
        excel_data = db.export_to_excel()
        st.download_button(
            label="📥 Export Full Database to Excel",
            data=excel_data,
            file_name=f"school_backup_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch"
        )
    
    #--- Tab 3: Students Management System ---
    with t_users:
        st.subheader("👥 User Management Center")
        st.write("Create new accounts, reset forgotten passwords, or manage the current roster.")
        
        col_create, col_roster = st.columns([1, 2])
        
        # --- COLUMN 1: CREATE NEW USERS ---
        with col_create:
            with st.container(border=True):
                st.markdown("### ➕ Create Account")
                with st.form("new_user_form", clear_on_submit=True):
                    new_id = st.text_input("User ID (e.g., Student Roll No.)")
                    new_name = st.text_input("Full Name")
                    new_pw = st.text_input("Initial Password", type="password")
                    new_role = st.selectbox("System Role", ["Student", "Admin"])
                    
                    submit_user = st.form_submit_button("Register User", width="stretch", type="primary")
                    
                    if submit_user:
                        if new_id and new_name and new_pw:
                            success, msg = db.create_user(new_id, new_name, new_pw, new_role)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.warning("All fields are required to create an account.")

        # --- COLUMN 2: MANAGE EXISTING USERS ---
        with col_roster:
            st.markdown("### 📋 System Roster")
            
            # 1. Fetch data
            users_df, _, _ = db.get_all_data_for_export()
            
            # 2. Search & Filter
            search_query = st.text_input("🔍 Search by Name or ID", placeholder="Type to filter...")
            if search_query:
                users_df = users_df[
                    users_df['name'].str.contains(search_query, case=False) | 
                    users_df['student_id'].str.contains(search_query, case=False)
                ]

            # 3. User Cards
            if users_df.empty:
                st.info("No users match your search.")
            else:
                for idx, row in users_df.iterrows():
                    with st.container(border=True):
                        c_info, c_actions = st.columns([2, 1])
                        
                        with c_info:
                            st.markdown(f"**{row['name']}**")
                            st.caption(f"ID: {row['student_id']} | Role: {row['role']}")
                        
                        with c_actions:
                            # Prevent self-deletion
                            if row['student_id'] == st.session_state.user:
                                st.button("✅ Currently Active", disabled=True, width="stretch")
                            else:
                                # Delete Button
                                if st.button("🗑️ Delete", key=f"del_{row['student_id']}", width="stretch"):
                                    db.delete_user(row['student_id'])
                                    st.success(f"User {row['student_id']} removed.")
                                    st.rerun()
                        
                        # 4. Nested Password Reset (Hidden by default)
                        with st.expander("🔑 Password Reset"):
                            r_col1, r_col2 = st.columns([2, 1])
                            reset_pw = r_col1.text_input("New Secure Password", type="password", key=f"input_pw_{row['student_id']}")
                            if r_col2.button("Update", key=f"btn_pw_{row['student_id']}", width="stretch"):
                                if reset_pw:
                                    s, m = db.reset_password(row['student_id'], reset_pw)
                                    if s: st.success("Updated!")
                                    else: st.error("Failed.")
                                else:
                                    st.warning("Empty password.")
        
    # --- TAB 2: MASS EVENT TAGGING (NEW) ---
    with t_tagging:
        st.subheader("Mass Event Portfolio Sync")
        st.info("Tag multiple students in one school event to auto-populate their portfolios.")
        with st.form("event_sync"):
            e_title = st.text_input("Event Name (e.g., Annual Sports Meet 2025)")
            e_desc = st.text_area("Official Description/Achievement")
            e_skills = st.text_input("Skills Learned (e.g., Leadership, Teamwork)")
            e_grade = st.text_input("Academic Grade/Batch")
            
            selected_students = st.multiselect("Select Students involved", options=students['student_id'],
                                             format_func=lambda x: f"{x} - {students[students['student_id']==x]['name'].values[0]}")
            
            if st.form_submit_button("🚀 Sync to Selected Portfolios"):
                if e_title and selected_students:
                    for s_id in selected_students:
                        db.save_activity(s_id, e_title, e_desc, e_skills, None)
                        # Manually update grade_section for bulk entries
                        with db._get_connection() as conn:
                            conn.execute("UPDATE activities SET grade_section=? WHERE student_id=? AND title=?", 
                                         (e_grade, s_id, e_title))
                            conn.commit()
                    st.success(f"Portfolios updated for {len(selected_students)} students!")
                else:
                    st.error("Please provide an event title and select at least one student.")

    # --- TAB 5: EVIDENCE AUDIT (NEW) ---
    with t_audit:
        st.subheader("🛡️ Evidence Verification Queue")
        with db._get_connection() as conn:
            # ONLY fetch pending items for the audit
            all_a = pd.read_sql("SELECT * FROM activities WHERE status='pending' ORDER BY date DESC", conn)
        
        if not all_a.empty:
            for idx, r in all_a.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1.2])
                    with c1:
                        st.write(f"**Student:** {r['student_id']} | **Event:** {r['title']}")
                        st.write(f"**Summary:** {r['summary']}")
                        st.caption(f"Date: {r['date']}")
                    with c2:
                        if r['file_path'] and os.path.exists(str(r['file_path'])):
                            st.image(r['file_path'], width=200)
                        else:
                            st.caption("No image evidence.")
                    with c3:
                        # APPROVE BUTTON
                        if st.button("✅ Approve", key=f"app_{idx}", width="stretch"):
                            with db._get_connection() as conn:
                                conn.execute("UPDATE activities SET status='approved' WHERE student_id=? AND title=? AND date=?", 
                                            (r['student_id'], r['title'], r['date']))
                                conn.commit()
                            st.success("Moved to Gallery!")
                            st.rerun()
                        
                        # DELETE BUTTON
                        if st.button("🗑️ Reject/Delete", key=f"audit_del_{idx}", width="stretch"):
                            with db._get_connection() as conn:
                                conn.execute("DELETE FROM activities WHERE student_id=? AND title=? AND date=?", 
                                            (r['student_id'], r['title'], r['date']))
                                conn.commit()
                            st.rerun()
        else:
            st.info("Queue clear! No pending evidence to verify.")

        # --- TAB 3: MASTER BULK IMPORT ---
    with t_bulk:
            st.subheader("Bulk Operations")
            st.info("Use CSV files to update the system in seconds.")
            
            col_u, col_g = st.columns(2)
            
            with col_u:
                with st.container(border=True):
                    st.write("### 👥 Bulk User Import")
                    st.caption("CSV Headers: student_id, password, role, name")
                    u_file = st.file_uploader("Upload Users", type="csv", key="bulk_u")
                    if u_file and st.button("Confirm User Import"):
                        df = pd.read_csv(u_file)
                        for _, r in df.iterrows():
                            hp = bcrypt.hashpw(str(r['password']).encode(), bcrypt.gensalt())
                            with db._get_connection() as conn:
                                conn.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", 
                                            (str(r['student_id']), hp, r['role'], r['name']))
                        st.success(f"Imported {len(df)} users!")

            with col_g:
                with st.container(border=True):
                    st.write("### 📈 Bulk Grade Import")
                    st.caption("CSV Headers: student_id, year, term, subject, mark")
                    g_file = st.file_uploader("Upload Grades", type="csv", key="bulk_g")
                    if g_file and st.button("Confirm Grade Import"):
                        df = pd.read_csv(g_file)
                        count = 0
                        for _, r in df.iterrows():
                            db.update_grade(str(r['student_id']), int(r['year']), str(r['term']), str(r['subject']), int(r['mark']))
                            count += 1
                        st.success(f"Imported {count} academic records!")

    with t_gallery:
        st.subheader("🖼️ Global Evidence Gallery")
        st.caption("Showing verified student achievements.")
        
        with db._get_connection() as conn:
            # ONLY fetch approved items for the gallery
            approved_a = pd.read_sql("SELECT * FROM activities WHERE status='approved' ORDER BY date DESC", conn)
            
        if not approved_a.empty:
            # Create a grid layout for a better gallery look
            cols = st.columns(2) 
            for idx, r in approved_a.iterrows():
                with cols[idx % 2]: # Alternate between columns
                    with st.container(border=True):
                        st.write(f"**{r['student_id']}** - {r['title']}")
                        if r.get('file_path') and os.path.exists(str(r['file_path'])):
                            st.image(r['file_path'], width="stretch")
                        st.write(f"*{r['summary']}*")
        else:
            st.info("No verified evidence in the gallery yet.")
        
        #students portfolio
        with t_insight:
            st.subheader("🧠 Student Strategic Analysis")
            st.info("AI-generated perspectives based on academic performance, projects, and personal interests.")
            
            target_insight = st.selectbox("Select Student to Analyze", options=students['student_id'], key="insight_sel",
                                        format_func=lambda x: f"{x} - {students[students['student_id']==x]['name'].values[0]}")
            
            if st.button("Generate Administrative Insight", type="primary"):
                g_data, a_data = db.get_student_profile(target_insight)
                
                # Formulating a high-level admin prompt
                admin_prompt = f"""
                Analyze this student for the administration:
                - Grades: {g_data.to_string()}
                - Portfolio: {a_data.to_string()}
                
                Provide:
                1. FUTURE PERSPECTIVE: What career path is this student naturally gravitating toward?
                2. AREAS TO IMPROVE: Based on grades or project gaps, what should they work on?
                3. HELP NEEDED: Where should teachers/parents intervene to support them?
                """
                
                with st.spinner("AI is analyzing student potential..."):
                    try:
                        # Reusing the roadmap logic for administrative insight
                        analysis = ai_core.get_career_roadmap(g_data, a_data, "General Administrative Assessment")
                        
                        st.divider()
                        c1, c2, c3 = st.columns(3)
                        
                        # We display the analysis in a clean "3-Pillar" layout
                        with st.container(border=True):
                            st.markdown(analysis)
                    except:
                        st.error("Could not generate insight. Ensure student has enough data.")


# --- 7. STUDENT VIEW ---
else:
    st.title(f"Student Portal")
    t_ai, t_port, t_road, t_export = st.tabs(["💬 Achievement Journalist", "📂 Portfolio & Manual Entry", "🤖 Career Mentor", "📤 Export"])

    # --- TAB 1: AI INTERVIEWER (6 ROUNDS) ---
    with t_ai:
        col_h, col_r = st.columns([3, 1])
        col_h.subheader("💬 Log Your Success")
        if col_r.button("🔄 Redo Interview", width="stretch"):
            st.session_state.update({'interview_complete': False, 'chat_history': [], 'interview_counter': -1, 'pending_project': None})
            st.rerun()

        # Phase A: Initial Grade Context
        if st.session_state.interview_counter == -1:
            st.session_state.event_grade_context = st.selectbox(
                "Which grade level does this achievement belong to?",
                ["Grade 1","Grade 2","Grade 3","Grade 4","Grade 5","Grade 6","Grade 7","Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "University"]
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
                st.write(f"**Skills:** {st.session_state.pending_project['skills']}")
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
                    else: 
                        st.error("Can't proceed without evidence; upload a photo")

    # --- TAB 2: PORTFOLIO & MANUAL ENTRY ---
    with t_port:
        c_list, c_man = st.columns([2, 1])
        
        with c_man:
            with st.form("manual_entry_form", clear_on_submit=True):
                st.subheader("📝 Manual Entry")
                m_title = st.text_input("Project Title")
                m_grade = st.selectbox("Grade Level", ["Grade 1","Grade 2","Grade 3","Grade 4","Grade 5","Grade 6","Grade 7","Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"])
                m_skills = st.text_input("Skills (e.g. Coding, Leadership)")
                m_desc = st.text_area("Summary of Event")
                m_img = st.file_uploader("Evidence Image", type=['jpg','png','jpeg'])
                
                if st.form_submit_button("Add Manually"):
                    if m_title and m_img:
                        # Use a spinner to show the app is processing
                        with st.spinner("Uploading evidence and saving to portfolio..."):
                            try:
                                # Extract the ID to prevent __conform__ errors
                                u_id = st.session_state.user['id'] if isinstance(st.session_state.user, dict) else st.session_state.user

                                # 1. Save the file
                                path = pf_manager.save_evidence(u_id, m_img)
                                
                                # 2. Save to database
                                db.save_activity(u_id, m_title, m_desc, m_skills, path)
                                
                                # 3. Update the grade section
                                with db._get_connection() as conn:
                                    conn.execute(
                                        "UPDATE activities SET grade_section=? WHERE student_id=? AND title=?", 
                                        (m_grade, u_id, m_title)
                                    )
                                
                                st.success("Achievement saved successfully!")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Database Error: {e}")
                    else:
                        st.error("Title and Evidences are mandatory")

                        # Insert this right before the loop that displays the projects
if not a_data.empty:
    pdf_data = export_portfolio_pdf(st.session_state.name, a_data)
    st.download_button(
        label="📥 Download Portfolio (PDF)",
        data=pdf_data,
        file_name=f"{st.session_state.name}_Portfolio.pdf",
        mime="application/pdf",
        width="stretch"
    )
    st.divider()

        with c_list:
            st.subheader("📂 Your Portfolio")
            g_data, a_data = db.get_student_profile(st.session_state.user)
            if not a_data.empty:
                for idx, row in a_data.iterrows():
                    with st.container(border=True):
                        st.markdown(f"### {row['title']}")
                        st.caption(f"Grade: {row.get('grade_section', 'N/A')} | Date: {row['date']}")
                        if row['file_path']: st.image(row['file_path'], width="stretch")
                        st.write(row['summary'])
                        with st.popover("🗑️ Delete"):
                            st.error("This action cannot be undone!")
                            if st.button("Delete Project", key=f"std_del_{idx}"):
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

                
    
    
    )
    