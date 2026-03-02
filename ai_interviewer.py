from google import genai 
import os

class EvidenceInterviewer:
    def __init__(self, api_key):
        """
        Initializes the Gemini 2.0 Client.
        The api_key should be passed from st.secrets['GEMINI_API_KEY']
        """
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash"

    def get_ai_response(self, user_input, history, counter):
        """
        Handles the 6-round achievement interview logic using Gemini.
        """
        is_final_round = (counter >= 5)
        
        # System instructions define the AI's behavior
        if not is_final_round:
            system_instruction = (
                "You are a professional Achievement Journalist. Tone: direct and factual. "
                "Ask ONE deep investigative question about the student's project. "
                "Do NOT ask for photos. Focus on technical hurdles and learning outcomes."
            )
        else:
            system_instruction = (
                "The interview is OVER. Summarize the achievement. "
                "You MUST end your response with this exact format: "
                "SAVE_DATA: [Grade] | [Title] | [Skills] | [Summary]"
            )

        # Gemini requires history to be in 'contents' format: [{'role': 'user', 'parts': [...]}]
        contents = []
        for msg in history:
            # Map Streamlit roles to Gemini roles ('assistant' becomes 'model')
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role, 
                "parts": [{"text": msg["content"]}]
            })

        try:
            # Generate the response
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.7 if not is_final_round else 0.2
                }
            )
            return response.text
        except Exception as e:
            return f"Gemini Connection Error: {str(e)}"

    def get_career_roadmap(self, grades_df, activities_df, context):
        """
        Uses Gemini to analyze student data and provide career mentorship or admin insights.
        """
        prompt = f"""
        Analyze the following student data for EduTrack 360.
        
        CONTEXT: {context}
        ACADEMIC GRADES: 
        {grades_df.to_string()}
        
        PORTFOLIO ACTIVITIES:
        {activities_df.to_string()}
        
        If this is for an Admin: Provide a strategic analysis (Strengths, Gaps, Intervention).
        If this is for a Student: Act as a friendly Career Mentor.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Mentor Error: {str(e)}"