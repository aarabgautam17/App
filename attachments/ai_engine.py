from google import genai
import streamlit as st

class CareerAI:
    def __init__(self, api_key):
        # Matches the EvidenceInterviewer client
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash"

    def get_career_roadmap(self, grades_df, activities_df, user_query):
        prompt = f"""
        Role: Senior Career Counselor.
        Student Name: {st.session_state.name}
        Academic Data: {grades_df.to_string()}
        Portfolio: {activities_df.to_string()}
        User Question: {user_query}
        
        Provide a strategic roadmap. Suggest 3 specific career paths and 1 immediate skill to learn.
        """
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt
        )
        return response.text