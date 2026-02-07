"""
Upload backend to Hugging Face Space using huggingface_hub API
"""
from huggingface_hub import HfApi, login
import os

# Login with token from environment variable
# Set HF_TOKEN environment variable before running this script
token = os.getenv("HF_TOKEN")
if not token:
    raise ValueError("HF_TOKEN environment variable not set")
login(token=token)

# Initialize API
api = HfApi()

# Upload entire backend folder to Space (v2)
print("Uploading backend to Hugging Face Space v2...")
api.upload_folder(
    folder_path="backend",
    repo_id="Asif-mp3/Thara-Backend-v2",  # Updated to v2
    repo_type="space",
    commit_message="Deploy backend to HF Spaces v2"
)

print("✅ Upload complete!")
print("Your backend is now live at: https://asif-mp3-thara-backend-v2.hf.space")
