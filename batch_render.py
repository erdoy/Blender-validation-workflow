
#Step 2: Run Blender in Background Mode
#Because rendering inside the heavy Blender user interface takes up unnecessary memory and processing power, you should execute this script using Blender's headless command line mode.

#Open your normal Windows PowerShell window (make sure you save your .blend file first) and run this command:

#PowerShell
#& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b "C:\Users\FABLAB\Documents\BlenderScripts\Terrain_random_perfeccionar.blend" -P "C:\Users\FABLAB\Documents\BlenderScripts\batch_render.py"
#Note: If your Blender installation is in a different path or you are using a different version (like Blender 4.3), adjust the first part of that path string to match your system.

#What the Command Flags Mean:
#-b: Tells Blender to run in the background (headless mode). No window will pop up, saving massive graphical overhead.

#-P: Orders Blender to run the specified Python script automatically as soon as the project file opens.



# IF YOU WANT TO EXIT THE PROGRAMME; JUST PRESS CTL +C ON CMD SO THAT ORIGINAL RENDERING SETTINGS ARE RESTORED


import sys, os, site, importlib

# -------------- IMPORT DEPENDENCIES -----------------#

# Get the path to where the --user flag installs packages
user_site_packages = site.getusersitepackages()
# 1. Define the path where your scripts live on this public PC
scripts_dir = os.path.join(os.path.expanduser("~"), "Documents", "BlenderScripts")

# Force Blender to look in this folder for modules
if user_site_packages not in sys.path:
    sys.path.append(user_site_packages)

# 2. Add that folder to Python's path if it isn't there already
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

# 3. Import your custom module!
import hexgrid_params

importlib.reload(hexgrid_params)

# ----------------------------------------------------#

from hexgrid_params import *
from helper_functions import inspect_mod_inputs, inspect_node, generate_distinct_colors

import pandas as pd
import bpy

# 1. Setup paths
CSV_PATH = r"C:/Users/FABLAB/Documents/BlenderScripts/data.csv"
OUTPUT_DIR = r"C:/Users/FABLAB/Documents/BlenderScripts/low_res_renders"

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)
df = df.dropna(subset=['valid'])
df = df.reset_index(drop=True)

print(f"Loaded {len(df)} rows that have a non-blank 'valid' status.")

scene = bpy.context.scene

# =============================================================
# 2. CACHE ORIGINAL USER SETTINGS
# =============================================================
original_settings = {
    "engine": scene.render.engine,
    "file_format": scene.render.image_settings.file_format,
    "color_mode": scene.render.image_settings.color_mode,
    "resolution_x": scene.render.resolution_x,
    "resolution_y": scene.render.resolution_y,
    "resolution_percentage": scene.render.resolution_percentage,
    "samples": None
}

# Safely cache EEVEE samples depending on your Blender version
if hasattr(scene, "eevee"):
    original_settings["samples"] = scene.eevee.taa_render_samples

# =============================================================
# 3. APPLY LOW-QUALITY OVERRIDES USING A TRY/FINALLY SAFEGUARD
# =============================================================
try:
    print("Applying ultra-low resolution overrides for speed...")
    scene.render.engine = 'BLENDER_EEVEE'  # Or 'BLENDER_EEVEE' depending on version
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.resolution_x = 128
    scene.render.resolution_y = 128
    scene.render.resolution_percentage = 100

    if original_settings["samples"] is not None:
        scene.eevee.taa_render_samples = 4

    obj = bpy.data.objects["HexGridController"]
    mod = bpy.data.objects["HexGridController"].modifiers["HexGrid"]
    node_group = bpy.data.node_groups['HexGridGroup']

    hg = HexGridParams(mod, node_group, 0)
    hg.csv_path = CSV_PATH

    print(f"Beginning batch render of {len(df)} scenes...")

    # 4. Loop through each row and render
    for idx, row in df.iterrows():
        seed = int(row['seed'])
        output_filename = os.path.join(OUTPUT_DIR, f"{seed}.png")
        
        # Skip if already rendered (allows you to resume if interrupted)
        if os.path.exists(output_filename):
            continue
            
        print(f"Rendering seed {seed} ({idx+1}/{len(df)})...")
        
        try:
            
            hg.load_params(seed,CSV_PATH)
            hg.update()
            bpy.data.objects['Plane'].location[2] = hg.instance_scale
                
            # --- RENDER AND SAVE ---
            scene.render.filepath = output_filename
            bpy.ops.render.render(write_still=True)
            
        except Exception as e:
            print(f"Error rendering seed {seed}: {e}")

finally:
    # =============================================================
    # 6. RESTORE ORIGINAL SETTINGS (Runs no matter what happens above)
    # =============================================================
    print("\nRestoring your original Blender rendering parameters...")
    scene.render.engine = original_settings["engine"]
    scene.render.image_settings.file_format = original_settings["file_format"]
    scene.render.image_settings.color_mode = original_settings["color_mode"]
    scene.render.resolution_x = original_settings["resolution_x"]
    scene.render.resolution_y = original_settings["resolution_y"]
    scene.render.resolution_percentage = original_settings["resolution_percentage"]
    
    if original_settings["samples"] is not None:
        scene.eevee.taa_render_samples = original_settings["samples"]
            
    print("Your project file settings have been completely reset to normal!")
    print("Batch processing complete.")









