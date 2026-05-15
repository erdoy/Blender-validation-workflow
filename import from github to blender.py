import os
import subprocess
import bpy

# Configuration
REPO_URL = "https://github.com/erdoy/Blender-validation-workflow.git"
LOCAL_DIR = os.path.join(os.path.expanduser("~"), "Documents", "BlenderScripts")
BLEND_FILE_NAME = "Terrain_random_perfeccionar.blend"

# 1. Clone the repo if it doesn't exist, or pull if it does
if not os.path.exists(LOCAL_DIR):
    subprocess.run(["git", "clone", REPO_URL, LOCAL_DIR])
else:
    subprocess.run(["git", "-C", LOCAL_DIR, "pull"])

# 2. CRITICAL: Open the .blend file FIRST before loading text tabs
blend_path = os.path.join(LOCAL_DIR, BLEND_FILE_NAME)
if os.path.exists(blend_path):
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    print(f"Successfully opened {BLEND_FILE_NAME}")
else:
    print(f"[WARNING] Could not find {BLEND_FILE_NAME} in the repository. Opening default scene.")
    
# 3. Automatically load all .py files into Blender Text Editor tabs
for root, dirs, files in os.walk(LOCAL_DIR):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            
            # Check if already open
            if file not in bpy.data.texts:
                bpy.data.texts.load(file_path)

print("Setup complete! Edit freely. Use Alt+S to save scripts to disk.")

print("All scripts loaded into tabs! Edit freely. Use Alt+S to save to disk.")
