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

# Upload entire backend folder to Space
print("Uploading backend to Hugging Face Space...")
api.upload_folder(
    folder_path="backend",
    repo_id="Asif-mp3/thara-backend",
    repo_type="space",
    commit_message="Deploy backend to HF Spaces"
)

print("✅ Upload complete!")
print("Your backend is now live at: https://asif-mp3-thara-backend.hf.space")
