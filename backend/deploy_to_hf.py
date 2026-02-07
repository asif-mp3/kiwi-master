"""
Deploy backend to Hugging Face Space
Run: python deploy_to_hf.py
"""

import os
import sys

# Set encoding to avoid Unicode errors on Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

from huggingface_hub import HfApi, login

SPACE_ID = "Asif-mp3/Thara-Backend-v2"

def main():
    print("=" * 50)
    print("Thara Backend -> Hugging Face Deployer")
    print("=" * 50)

    # Check if already logged in
    api = HfApi()
    try:
        user_info = api.whoami()
        print(f"Logged in as: {user_info['name']}")
    except Exception:
        print("\nNot logged in. Please enter your Hugging Face token.")
        print("Get your token from: https://huggingface.co/settings/tokens")
        print("(Token should have 'Write' permission)")
        print()
        token = input("Enter your HF token: ").strip()
        if not token:
            print("No token provided. Exiting.")
            return
        login(token=token, add_to_git_credential=True)
        print("Login successful!")

    print(f"\nUploading to: {SPACE_ID}")
    print("This may take a moment...")

    # Get current directory (should be backend folder)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # Try direct upload first
        api.upload_folder(
            folder_path=current_dir,
            repo_id=SPACE_ID,
            repo_type="space",
            ignore_patterns=["*.pyc", "__pycache__", ".git", "*.egg-info", "deploy_to_hf.py", ".env", "*.db", "venv", "venv/**", ".venv", ".venv/**", "scripts/**", "test_*.py"]
        )
        print("\n" + "=" * 50)
        print("Upload complete!")
        print(f"Check your Space: https://huggingface.co/spaces/{SPACE_ID}")
        print("=" * 50)
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            print("\n" + "=" * 50)
            print("ERROR: Token doesn't have write permission!")
            print("=" * 50)
            print("\nTo fix this:")
            print("1. Go to: https://huggingface.co/settings/tokens")
            print("2. Click 'New token'")
            print("3. Name: 'thara-deploy'")
            print("4. Type: 'Write' (NOT 'Read')")
            print("5. Copy the new token")
            print("6. Run this command to login with new token:")
            print("   python -c \"from huggingface_hub import login; login()\"")
            print("\nOr delete old token and re-run this script.")
        else:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
