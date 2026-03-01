import os
from datetime import datetime
from ai_interviewer import EvidenceInterviewer

class PortfolioManager:
    def __init__(self, storage_dir="student_evidence"):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def save_evidence(self, student_id, uploaded_file):
        """Saves physical file to a student-specific folder."""
        student_path = os.path.join(self.storage_dir, str(student_id))
        if not os.path.exists(student_path):
            os.makedirs(student_path)
            
        file_ext = uploaded_file.name.split('.')[-1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        file_name = f"evidence_{timestamp}.{file_ext}"
        full_path = os.path.join(student_path, file_name)
        
        with open(full_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return full_path