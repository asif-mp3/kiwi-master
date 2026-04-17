"""
Deploy backend to Hugging Face Space
Run: python deploy_to_hf.py
"""

import os
import sys

# Set encoding to avoid Unicode errors on Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

from huggingface_hub import HfApi, login
from utils.logger import get_logger

logger = get_logger("deploy_to_hf")

SPACE_ID = "Asif-mp3/Thara-Backend-v2"


def main():
    logger.info("=" * 50)
    logger.info("Thara Backend -> Hugging Face Deployer")
    logger.info("=" * 50)

    # Check if already logged in
    api = HfApi()
    try:
        user_info = api.whoami()
        logger.info("Logged in as: %s", user_info['name'])
    except Exception:
        logger.info("Not logged in. Please enter your Hugging Face token.")
        logger.info("Get your token from: https://huggingface.co/settings/tokens")
        logger.info("(Token should have 'Write' permission)")
        token = input("Enter your HF token: ").strip()
        if not token:
            logger.warning("No token provided. Exiting.")
            return
        login(token=token, add_to_git_credential=True)
        logger.info("Login successful!")

    logger.info("Uploading to: %s", SPACE_ID)
    logger.info("This may take a moment...")

    # Get current directory (should be backend folder)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # Try direct upload first
        api.upload_folder(
            folder_path=current_dir,
            repo_id=SPACE_ID,
            repo_type="space",
            ignore_patterns=[
                "*.pyc", "__pycache__", ".git", "*.egg-info",
                "deploy_to_hf.py", ".env",
                "*.db", "*.duckdb", "*.duckdb.wal",
                "data_sources/snapshots/**", "data_sources/cache/**",
                "venv", "venv/**", ".venv", ".venv/**",
                "scripts/**",
                "test_*.py", "TEST_REPORT.md", "test_results*.json"
            ]
        )
        logger.info("=" * 50)
        logger.info("Upload complete!")
        logger.info("Check your Space: https://huggingface.co/spaces/%s", SPACE_ID)
        logger.info("=" * 50)
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            logger.error("=" * 50)
            logger.error("Token doesn't have write permission!")
            logger.error("=" * 50)
            logger.error("To fix this:")
            logger.error("1. Go to: https://huggingface.co/settings/tokens")
            logger.error("2. Click 'New token'")
            logger.error("3. Name: 'thara-deploy'")
            logger.error("4. Type: 'Write' (NOT 'Read')")
            logger.error("5. Copy the new token")
            logger.error("6. Run this command to login with new token:")
            logger.error("   python -c \"from huggingface_hub import login; login()\"")
            logger.error("Or delete old token and re-run this script.")
        else:
            logger.error("Error: %s", e)

if __name__ == "__main__":
    main()
