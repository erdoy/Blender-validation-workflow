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
        # Check if there are any changes to commit first
        status_result = subprocess.run(
            ["git", "-C", LOCAL_DIR, "status", "--porcelain"], 
            capture_output=True, text=True, check=True
        )
        
        # If the output is empty, there's nothing to commit
        if not status_result.stdout.strip():
            print("No changes detected. Skipping commit and push.")
        else:
            # 1. Stage all changes
            subprocess.run(["git", "-C", LOCAL_DIR, "add", "."], check=True)
            
            # 2. Commit changes
            commit_message = "Edits made from public PC session"
            subprocess.run(["git", "-C", LOCAL_DIR, "commit", "-m", commit_message], check=True)
            
            # 3. Push to GitHub
            print("Pushing to GitHub... (You may be prompted for your Personal Access Token)")
            subprocess.run(["git", "-C", LOCAL_DIR, "push", "origin", "main"], check=True)
            print("Successfully pushed all changes to GitHub!")

        # Move Step 2 inside the try block so it runs if the push succeeds OR if skipped
        print("\n--- Step 2: Wiping local data from computer ---")
        # shutil.rmtree forcibly deletes a directory and everything inside it
        shutil.rmtree(LOCAL_DIR)
        print(f"Successfully deleted {LOCAL_DIR} and all its contents.")
        print("Your data is safe and the public PC is clean!")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Git operation failed: {e}")
        print("CRITICAL: Check your network or GitHub token. DO NOT delete the folder yet if you want to save your work!")
        choice = input("Do you want to force delete the files anyway? (y/n): ")
        if choice.lower() == 'y':
            shutil.rmtree(LOCAL_DIR)
            print("Directory force deleted.")
            
    except Exception as e:
        print(f"[ERROR] Could not delete directory: {e}")
        print("Please delete the 'BlenderScripts' folder manually from the Documents folder and empty the Recycle Bin.")

if __name__ == "__main__":
    cleanup_and_push()
