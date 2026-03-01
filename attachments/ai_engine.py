from google import genai

class CareerAI:
    def __init__(self, api_key):
        # Initializing the new 2026-standard Client
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash" # Optimized for speed and logic

    def get_career_roadmap(self, academics_df, activities_df):
        """Analyzes data to predict the student's career path."""
        context = f"""
        Academic Performance:
        {academics_df.to_string()}
        
        Extracurricular Activities:
        {activities_df.to_string()}
        """
        
        prompt = f"""
        Analyze the following student data and provide a Career Roadmap:
        {context}
        
        Identify:
        1. Primary Strength (e.g., Technical, Creative, Leadership).
        2. Three recommended career paths.
        3. A 'Skill Gap' analysis (what they should learn next).
        """
        
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt
        )
        return response.text