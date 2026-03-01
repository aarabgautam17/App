import groq
import os

class EvidenceInterviewer:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.client = groq.Groq(api_key=self.api_keys[self.current_key_index])

    def get_ai_response(self, user_input, history, counter):
        """
        counter 0-4: Investigative Journalist Mode
        counter 5: Final Summary Mode (No more questions)
        """
        
        # Determine if we are at the finish line
        is_final_round = (counter >= 5)

        if not is_final_round:
            system_content = (
                "You are a professional Achievement Journalist. Your tone is direct and factual. "
                "STRICT RULE: Do not invent details. If the student provides vague info or gibberish (like '...', 'asdf', or symbols), "
                "do NOT move to the next topic. Instead, say: 'Please provide the specific information I asked for. I cannot document dots or gibberish.' "
                "If their reply is helpful, ask ONE deep, investigative question about the project. "
                "Focus only on technical hurdles, their specific role, or what they learned. "
                "NEVER ask about photos, medals, or evidence. "
                "Do NOT mention that you are an AI or that this is an interview. "
                "Stay strictly to the facts provided. If no facts are present, do not proceed with the story."
            )
        else:
            system_content = (
               "The interview is OVER. Do not be polite. Do not congratulate them."
                "Provide a 1-sentence factual summary of what was discussed."
                "If the user provided gibberish, dots, or symbols, the summary must be: 'No valid data provided.'"
                "Immediately provide the data tag in this EXACT format:"
                "\n\nSAVE_DATA: [Grade] | [Project Title] | [Key Skills] | [Detailed Summary]"
                "\n\nSTRICT RULE: If a field was not explicitly described with real words, "
                "you MUST enter 'N/A' for that field. Do NOT use filler words like 'Expertise' or 'Problem-Solving'."
                            )

        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7 if not is_final_round else 0.3 # Lower temp for the final tag for accuracy
            )
            return response.choices[0].message.content

        except Exception:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self.client = groq.Groq(api_key=self.api_keys[self.current_key_index])
            return "I've processed that detail. Please tell me a bit more so I can wrap this up."

    def get_career_roadmap(self, grades_df, activities_df, context):
        # Admin Insight & Career Mentor Logic
        prompt = f"""
        CONTEXT: {context}
        GRADES: {grades_df.to_string()}
        PORTFOLIO: {activities_df.to_string()}
        
        If context contains 'ADMIN_MODE':
        Provide exactly three sections:
        🔭 FUTURE PERSPECTIVE: (Analyze career trajectory)
        🎯 AREAS TO IMPROVE: (Identify gaps)
        🆘 HELP NEEDED: (Specify teacher/parent support)
        
        If context is a student question:
        Answer as a friendly Career Mentor. Be specific about job roles and skills.
        """
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6
            )
            return response.choices[0].message.content
        except:
            return "Mentor is currently offline. Please try again in a moment."