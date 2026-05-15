import os
import shutil
import subprocess

# Configuration (Must match your original script)
LOCAL_DIR = os.path.join(os.path.expanduser("~"), "Documents", "BlenderScripts")

def cleanup_and_push():
    if not os.path.exists(LOCAL_DIR):
        print(f"Directory {LOCAL_DIR} not found. Nothing to clean up.")
        return

    print("--- Step 1: Syncing changes to GitHub ---")
    try:
        # 1. Stage all changes
        subprocess.run(["git", "-C", LOCAL_DIR, "add", "."], check=True)
        
        # 2. Commit changes
        commit_message = "Edits made from public PC session"
        subprocess.run(["git", "-C", LOCAL_DIR, "commit", "-m", commit_message], check=True)
        
        # 3. Push to GitHub
        print("Pushing to GitHub... (You may be prompted for your Personal Access Token)")
        subprocess.run(["git", "-C", LOCAL_DIR, "push", "origin", "main"], check=True)
        print("Successfully pushed all changes to GitHub!")

        print("\n--- Step 2: Wiping local data from computer ---")
        try:
            # shutil.rmtree forcibly deletes a directory and everything inside it
            shutil.rmtree(LOCAL_DIR)
            print(f"Successfully deleted {LOCAL_DIR} and all its contents.")
            print("Your data is safe and the public PC is clean!")
        except Exception as e:
            print(f"[ERROR] Could not delete directory: {e}")
            print("Please delete the 'BlenderScripts' folder manually from the Desktop and empty the Recycle Bin.")
    
            
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Git operation failed: {e}")
        print("CRITICAL: Check your network or GitHub token. DO NOT delete the folder yet if you want to save your work!")
        choice = input("Do you want to force delete the files anyway? (y/n): ")
        if choice.lower() != 'y':
            return

    
if __name__ == "__main__":
    cleanup_and_push()
