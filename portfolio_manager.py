import os
import re
from datetime import datetime

class PortfolioManager:
    def __init__(self, storage_dir="student_evidence"):
        self.storage_dir = storage_dir
        # Ensure the base directory exists
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def save_evidence(self, student_id, uploaded_file):
        """Saves physical file to a student-specific folder with sanitized naming."""
        
        # 1. Create student-specific subdirectory
        # Using string conversion to handle numeric IDs safely
        student_folder = os.path.join(self.storage_dir, str(student_id))
        if not os.path.exists(student_folder):
            os.makedirs(student_folder)
            
        # 2. Sanitize original extension and create unique filename
        # We use a timestamp to prevent overwriting files uploaded at the same time
        file_ext = uploaded_file.name.split('.')[-1].lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean the student ID for the filename just in case it has weird characters
        clean_id = re.sub(r'[^a-zA-Z0-9]', '', str(student_id))
        file_name = f"{clean_id}_{timestamp}.{file_ext}"
        
        full_path = os.path.join(student_folder, file_name)
        
        # 3. Write the file to disk
        try:
            with open(full_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Return the path using forward slashes (standard for web/database)
            return full_path.replace("\\", "/")
        except Exception as e:
            print(f"Error saving file: {e}")
            return None

    def delete_evidence(self, file_path):
        """Safely removes a file from the server if it exists."""
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False