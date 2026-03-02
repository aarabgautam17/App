from google import genai
import streamlit as st

class CareerAI:
    def __init__(self, api_key):
        """
        Initializes the Gemini 2.0 Client.
        Pass st.secrets['GEMINI_API_KEY'] here.
        """
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash"

    def get_career_roadmap(self, grades_df, activities_df, user_query):
        # 1. Handle Empty Data (Prevents the AI from hallucinating or crashing)
        grades_str = grades_df.to_string() if not grades_df.empty else "No academic records yet."
        activities_str = activities_df.to_string() if not activities_df.empty else "No portfolio projects yet."
        
        # 2. Structured Prompt for High-Quality Output
        prompt = f"""
        Role: Senior Career Counselor & Academic Advisor.
        Student Name: {st.session_state.get('name', 'Student')}
        
        --- STUDENT DATA ---
        ACADEMIC PERFORMANCE:
        {grades_str}
        
        EXTRACURRICULAR PORTFOLIO:
        {activities_str}
        
        --- USER REQUEST ---
        "{user_query}"
        
        --- INSTRUCTIONS ---
        1. Analyze the correlation between their grades and their projects.
        2. Suggest 3 specific, modern career paths.
        3. Suggest 1 immediate technical or soft skill to learn based on their gaps.
        4. Use Markdown formatting (bolding, bullet points) for readability.
        """
        
        try:
            # 3. Call Gemini 2.0 Flash
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            if response and response.text:
                return response.text
            return "I'm analyzing your profile, but I couldn't generate a roadmap right now. Try asking about a specific interest!"

        except Exception as e:
            return f"⚠️ Career AI Error: {str(e)}"