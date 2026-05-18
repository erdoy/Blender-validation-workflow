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

import bpy
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# =============================================================
# 1. SETUP PATHS
# =============================================================

blend_file_path = bpy.data.filepath
scripts_dir = os.path.dirname(blend_file_path)
CSV_PATH = os.path.join(scripts_dir, "data.csv")
TARGET_CSV_PATH = os.path.join(scripts_dir, "AI_assist_data.csv")
MODEL_PATH = os.path.join(scripts_dir, "multimodal_ai_bottleneck.pth")
TEMP_IMG_PATH = os.path.join(scripts_dir, "temp_inference.png")

print("\n--- Booting AI Assistant ---")

# =============================================================
# 2. REBUILD THE SCALER FROM YOUR ORIGINAL DATA
# =============================================================
# The AI only understands scaled math. We must recreate the scaler.
df = pd.read_csv(CSV_PATH)
df = df.dropna(subset=['valid']).reset_index(drop=True)
df = df.drop(columns=['camera_target'], errors='ignore')
df = df.loc[:, df.nunique() > 1] # Drop zero-variance columns
feature_cols = [col for col in df.columns if col not in ['valid', 'seed', 'camera_target']]

scaler = StandardScaler()
scaler.fit(df[feature_cols]) # Relearn the mean and variance of your original dataset
print(f"Reconstructed Math Scaler for {len(feature_cols)} parameters.")

# =============================================================
# 3. DEFINE THE EXACT AI ARCHITECTURE (BOTTLENECK VERSION)
# =============================================================
class FusionNet(nn.Module):
    def __init__(self, tabular_input_dim):
        super(FusionNet, self).__init__()
        
        self.vision = models.resnet18(weights=None) # We don't need weights from MS, we have our own!
        num_ftrs = self.vision.fc.in_features
        self.vision.fc = nn.Sequential(
            nn.Linear(num_ftrs, 32),
            nn.ReLU()
        )
        
        self.tabular = nn.Sequential(
            nn.Linear(tabular_input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        
        self.fusion = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.3), 
            nn.Linear(32, 1) 
        )

    def forward(self, img_x, tab_x):
        vision_features = self.vision(img_x)   
        math_features = self.tabular(tab_x)    
        combined_features = torch.cat((vision_features, math_features), dim=1) 
        output = self.fusion(combined_features)
        return output

# Load the AI Brain into RAM
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = FusionNet(tabular_input_dim=len(feature_cols)).to(device)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.eval() # CRITICAL: Tells the AI it is taking a test, not studying. Turns off Dropout!
print("AI Brain loaded successfully.")

# =============================================================
# 4. IMAGE PRE-PROCESSING
# =============================================================
resnet_mean = [0.485, 0.456, 0.406]
resnet_std = [0.229, 0.224, 0.225]

image_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=resnet_mean, std=resnet_std)
])

# =============================================================
# 4.5 GENERATE hg
# =============================================================
obj = bpy.data.objects["HexGridController"]
mod = bpy.data.objects["HexGridController"].modifiers["HexGrid"]
node_group = bpy.data.node_groups['HexGridGroup']

hg = HexGridParams(mod, node_group, 0)
hg.csv_path = CSV_PATH

# =============================================================
# 5. BLENDER INTERACTION FUNCTIONS
# =============================================================
def randomize_and_get_parameters(seed):
    hg.seed = seed
    hg.set_params()
    
    data = hg.save_params()
    
    return data

def take_hidden_screenshot():
    """Renders the current viewport instantly to a temporary file."""
    
    
    
    scene = bpy.context.scene
    
    original_settings = {
        "engine": scene.render.engine,
        "file_format": scene.render.image_settings.file_format,
        "color_mode": scene.render.image_settings.color_mode,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "samples": None
    }

    if hasattr(scene, "eevee"):
        original_settings["samples"] = scene.eevee.taa_render_samples
    try:
#        print("Applying ultra-low resolution overrides for speed...")
        scene.render.engine = 'BLENDER_EEVEE'  
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.resolution_x = 128
        scene.render.resolution_y = 128
        scene.render.resolution_percentage = 100
        bpy.context.scene.render.filepath = TEMP_IMG_PATH
        
        bpy.ops.render.render(write_still=True)

        if original_settings["samples"] is not None:
            scene.eevee.taa_render_samples = 4
            
    finally:
#        print("\nRestoring your original Blender rendering parameters...")
        scene.render.engine = original_settings["engine"]
        scene.render.image_settings.file_format = original_settings["file_format"]
        scene.render.image_settings.color_mode = original_settings["color_mode"]
        scene.render.resolution_x = original_settings["resolution_x"]
        scene.render.resolution_y = original_settings["resolution_y"]
        scene.render.resolution_percentage = original_settings["resolution_percentage"]
        
        if original_settings["samples"] is not None:
            scene.eevee.taa_render_samples = original_settings["samples"]
            
            











# ==============================================================================
# 1. DEFINE PROPERTIES (The Data)
# ==============================================================================
class MyCustomProperties(bpy.types.PropertyGroup):
    """Group of properties representing the state of our UI"""
    
    my_string: bpy.props.StringProperty(
        name="Project Name",
        description="Enter a string",
        default="Untitled Project"
    )
    
    my_int: bpy.props.IntProperty(
        name="Iterations",
        description="An integer slider",
        default=5,
        min=1,
        max=100
    )
    
    my_float: bpy.props.FloatProperty(
        name="Intensity",
        description="A float slider",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype='FACTOR' # Renders as a slider without needing to drag
    )
    
    my_bool: bpy.props.BoolProperty(
        name="Enable Feature X",
        description="A simple checkbox",
        default=True
    )
    
    my_color: bpy.props.FloatVectorProperty(
        name="Theme Color",
        subtype='COLOR',
        default=(1.0, 0.0, 0.0, 1.0), # Red, Green, Blue, Alpha
        size=4,
        min=0.0,
        max=1.0,
        description="Color picker element"
    )
    
    my_enum: bpy.props.EnumProperty(
        name="Mode",
        description="A dropdown menu",
        items=[
            ('OP1', "Option 1", "Description for Option 1", 'MESH_CUBE', 1),
            ('OP2', "Option 2", "Description for Option 2", 'MESH_UVSPHERE', 2),
            ('OP3', "Option 3", "Description for Option 3", 'MESH_SUZANNE', 3)
        ]
    )

# ==============================================================================
# 2. DEFINE THE UI PANEL (The Visuals)
# ==============================================================================
class MYADDON_PT_comprehensive_panel(bpy.types.Panel):
    bl_label = "Hex Grid AI Validation Assist"
    bl_idname = "MYADDON_PT_comprehensive_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'     # The N-Panel Sidebar
    bl_context = "modifier"
    bl_category = "My Tools"  # The name of the tab

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Access our custom properties
        my_props = scene.my_custom_props

        # --- 1. Basic Text and Strings ---
        layout.label(text="Basic Inputs:", icon='INFO')
        layout.prop(my_props, "my_string", icon='TEXT')
        
        layout.separator() # Adds a small vertical gap

        # --- 2. Sliders and Numbers ---
        # A 'box' groups elements inside a visual bounding box
        box = layout.box()
        box.label(text="Numeric Parameters:")
        
        row = box.row()
        row.prop(my_props, "my_int")
        row.prop(my_props, "my_float")

        layout.separator()

        # --- 3. Toggles and Layout Alignments ---
        # align=True makes elements stick together without gaps
        row = layout.row(align=True) 
        row.prop(my_props, "my_bool", toggle=True) # toggle=True makes it a button instead of a checkbox
        row.operator("mesh.primitive_cube_add", text="Action!") # Native button
        
        # Standard checkbox
        layout.prop(my_props, "my_bool") 

        # --- 4. Dropdowns and Color Pickers ---
        layout.separator()
        layout.label(text="Visuals & Modes:")
        
        # Split divides the row into percentage-based columns (0.3 = 30% / 70%)
        split = layout.split(factor=0.3)
        split.label(text="Color:")
        split.prop(my_props, "my_color", text="") # text="" hides the label so just the picker shows
        
        layout.prop(my_props, "my_enum", expand=False) # expand=False = Dropdown. True = Row of buttons.

        # --- 5. Conditional UI (Displays only if conditions are met) ---
        layout.separator()
        if my_props.my_bool:
            col = layout.column()
            col.alert = True # Makes the UI element red to grab attention
            col.label(text="Feature X is currently ENABLED!")
            col.operator("render.render", icon='RENDER_STILL')
        else:
            layout.label(text="Check the box to reveal more options...", icon='RESTRICT_VIEW_ON')

# ==============================================================================
# 3. REGISTRATION
# ==============================================================================
classes = (
    MyCustomProperties,
    MYADDON_PT_comprehensive_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Attach our properties to the Scene so they are globally accessible
    bpy.types.Scene.my_custom_props = bpy.props.PointerProperty(type=MyCustomProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    # Clean up the properties when the script is unloaded
    del bpy.types.Scene.my_custom_props
    
    
    
    






    

# =============================================================
# 6. THE AI HUNT LOOP
# =============================================================
register()

SEED_LIST = list(range(2594, 3000))

print("\nHunting for a Valid Scene...")

with torch.no_grad(): # Tells PyTorch not to calculate gradients (saves massive memory)
    for seed in SEED_LIST:
        
        # 1. Scramble the scene
        hg = HexGridParams(mod, node_group, seed)
        hg.csv_path = CSV_PATH
        hg.set_params()
        
        hg.update()
        
        raw_params_dict = hg.save_params(TARGET_CSV_PATH)
        
        # 2. Format math parameters correctly
        # We must order the dictionary values exactly as feature_cols expects them
        ordered_params = [raw_params_dict[col] for col in feature_cols]
        scaled_params = scaler.transform(pd.DataFrame([ordered_params], columns=feature_cols))
        tensor_params = torch.tensor(scaled_params, dtype=torch.float32).to(device)
        
        # 3. Take screenshot and format image
        take_hidden_screenshot()
        img = Image.open(TEMP_IMG_PATH).convert('RGB')
        tensor_img = image_transforms(img).unsqueeze(0).to(device) # unsqueeze(0) adds a fake batch size of 1
        
        # 4. Ask the AI!
        output_logit = model(tensor_img, tensor_params)
        probability = torch.sigmoid(output_logit).item() * 100
        
        if probability >= 50.0:
            print(f"✅ SEED {seed}: SUCCESS! AI loves this scene ({probability:.1f}% confidence).")
            
            break
        else:
            print(f"❌ SEED {seed}: AI rejected scene ({probability:.1f}% confidence). Rerolling...")
            
    else:
        print("\n⚠️ Reached max attempts without finding a Valid scene. AI is being very picky!")

print("--- Assistant Finished ---")



#if __name__ == "__main__":
#    register()