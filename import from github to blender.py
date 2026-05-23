import os
import subprocess
import bpy
from bpy.app.handlers import persistent

# Configuration
REPO_URL = "https://github.com/erdoy/Blender-validation-workflow.git"
LOCAL_DIR = os.path.join(os.path.expanduser("~"), "Documents", "BlenderScripts")
BLEND_FILE_NAME = "Terrain_random_perfeccionar.blend"

# 1. Clone the repo if it doesn't exist, or pull if it does
if not os.path.exists(LOCAL_DIR):
    subprocess.run(["git", "clone", REPO_URL, LOCAL_DIR])
else:
    subprocess.run(["git", "-C", LOCAL_DIR, "pull"])

# ---------------------------------------------------------
# Define the function that must survive the file-open wipe
# ---------------------------------------------------------
@persistent
def load_scripts_after_open(dummy):
    # 3. Automatically load all .py files into Blender Text Editor tabs
    for root, dirs, files in os.walk(LOCAL_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                
                # Check if already open
                if file not in bpy.data.texts:
                    bpy.data.texts.load(file_path)
                    
    print("\n✅ Setup complete! All scripts loaded into tabs. Edit freely.")
    
    # Clean up: Remove the handler so it doesn't run again if you open a different file manually
    if load_scripts_after_open in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_scripts_after_open)

# ---------------------------------------------------------
# 2. Open the .blend file safely
# ---------------------------------------------------------
blend_path = os.path.join(LOCAL_DIR, BLEND_FILE_NAME)

if os.path.exists(blend_path):
    # Put the loading function in Blender's "back pocket"
    bpy.app.handlers.load_post.append(load_scripts_after_open)
    
    # Nuke the memory and open the file (triggers the handler above when finished)
    bpy.ops.wm.open_This is a massive improvement. You completely solved both of the command-line traps that were breakingmainfile(filepath=blend_path)
else:
    print(f"[WARNING] Could not find {BLEND_FILE_NAME} in the repository. Opening default scene.")
    # If the file doesn't exist, just load the scripts into the empty default scene directly
    load_scripts_after_open( your previous workflow. 
