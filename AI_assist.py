
# # -------------- IMPORT DEPENDENCIES -----------------#

# # Get the path to where the --user flag installs packages
# user_site_packages = site.getusersitepackages()
# # 1. Define the path where your scripts live on this public PC
# scripts_dir = os.path.join(os.path.expanduser("~"), "Documents", "BlenderScripts")

# # Force Blender to look in this folder for modules
# if user_site_packages not in sys.path:
#     sys.path.append(user_site_packages)

# # 2. Add that folder to Python's path if it isn't there already
# if scripts_dir not in sys.path:
#     sys.path.append(scripts_dir)

# # 3. Import your custom module!
# import hexgrid_params

# importlib.reload(hexgrid_params)

# # ----------------------------------------------------#

from hexgrid_params import *
from helper_functions import inspect_mod_inputs, inspect_node, generate_distinct_colors

import os
import bpy
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import pandas as pd
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
df = df.drop(columns=['camera_target'])
df = df.loc[:, df.nunique() > 1] # Drop zero-variance columns
feature_cols = [col for col in df.columns if col not in ['valid', 'seed']]

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

def take_hidden_render():
    scene = bpy.context.scene
    
    original_settings = {
        "engine": scene.render.engine,
        "file_format": scene.render.image_settings.file_format,
        "color_mode": scene.render.image_settings.color_mode,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "samples": getattr(scene.eevee, "taa_render_samples", None) if hasattr(scene, "eevee") else None
    }

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

# =============================================================
# 6. THE AI HUNT LOOP
# =============================================================
stop_requested = False

def start_hunting(start, end, context,continuous=True):
    global stop_requested
    stop_requested = False

    SEED_LIST = list(range(start, end))

    print("\nHunting for a Valid Scene...")

    with torch.no_grad(): # Tells PyTorch not to calculate gradients (saves massive memory)
        for seed in SEED_LIST:
            
            # 1. Scramble the scene
            hg = HexGridParams(mod, node_group, seed)
            hg.csv_path = CSV_PATH
            hg.set_params()
            
            hg.update()
            bpy.data.objects['Plane'].location[2] = hg.instance_scale
            
            raw_params_dict = hg.save_params(TARGET_CSV_PATH)
            
            # 2. Format math parameters correctly
            # We must order the dictionary values exactly as feature_cols expects them
            ordered_params = [raw_params_dict[col] for col in feature_cols]
            scaled_params = scaler.transform(pd.DataFrame([ordered_params], columns=feature_cols))
            tensor_params = torch.tensor(scaled_params, dtype=torch.float32).to(device)
            
            # 3. Take screenshot and format image
            take_hidden_render()
            with Image.open(TEMP_IMG_PATH) as img:
                img_rgb = img.convert('RGB')
                tensor_img = image_transforms(img_rgb).unsqueeze(0).to(device)
            
            # 4. Ask the AI!
            output_logit = model(tensor_img, tensor_params)
            probability = torch.sigmoid(output_logit).item() * 100
            
            if probability >= 50.0:
                print(f"✅ SEED {seed}: SUCCESS! AI loves this scene ({probability:.1f}% confidence).")
                hg.save_params(TARGET_CSV_PATH,True)
                context.scene.my_custom_props.confidence = probability/100
                if not continuous:
                    break
            else:
                print(f"❌ SEED {seed}: AI rejected scene ({probability:.1f}% confidence). Rerolling...")
            
            if stop_requested:
                print(f"AI Process interrupted by user at seed {seed}!")
                return

    print("--- Hunt Finished ---")



