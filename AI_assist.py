
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

# CSV_PATH = os.path.join(scripts_dir, "data.csv")
# TARGET_CSV_PATH = os.path.join(scripts_dir, "AI_assist_data.csv")
# MODEL_PATH = os.path.join(scripts_dir, "multimodal_ai_bottleneck.pth")
# TEMP_IMG_PATH = os.path.join(scripts_dir, "temp_inference.png")

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

class AIASSIST_OT_boot_ai(bpy.types.Operator):
    bl_label = "Boot Up AI"
    bl_idname = "ai_assist.boot_up" 

    def execute(self, context):
        global scaler, model, image_transforms, feature_cols, device

        props = context.scene.ai_assist_props

        # =============================================================
        # 2. REBUILD THE SCALER FROM YOUR ORIGINAL DATA
        # =============================================================
        # The AI only understands scaled math. We must recreate the scaler.
        df = pd.read_csv(props.trained_data_path)
        df = df.dropna(subset=['valid']).reset_index(drop=True)
        df = df.drop(columns=['camera_target'])
        df = df.loc[:, df.nunique() > 1] # Drop zero-variance columns
        feature_cols = [col for col in df.columns if col not in ['valid', 'seed']]

        scaler = StandardScaler()
        scaler.fit(df[feature_cols]) # Relearn the mean and variance of your original dataset
#        print(f"Reconstructed Math Scaler for {len(feature_cols)} parameters.")

        # Load the AI Brain into RAM
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = FusionNet(tabular_input_dim=len(feature_cols)).to(device)
        model.load_state_dict(torch.load(props.ai_model_path, map_location=device))
        model.eval() # CRITICAL: Tells the AI it is taking a test, not studying. Turns off Dropout!

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

        self.report({'INFO'}, f"Booted up AI")
        return {'FINISHED'}

# =============================================================
# 4.5 GENERATE hg
# =============================================================


# =============================================================
# 5. BLENDER INTERACTION FUNCTIONS
# =============================================================

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
        bpy.context.scene.render.filepath = bpy.context.scene.ai_assist_props.temp_render_path
        
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

def start_hunting():
    global stop_requested
    stop_requested = False

    mod = bpy.data.objects["HexGridController"].modifiers["HexGrid"]
    node_group = bpy.data.node_groups['HexGridGroup']
    
    hg = HexGridParams(mod, node_group, 0)

    props = bpy.context.scene.ai_assist_props

    SEED_LIST = list(range(props.start, props.end))

    print("\nHunting for a Valid Scene...")

    with torch.no_grad(): # Tells PyTorch not to calculate gradients (saves massive memory)
        for seed in SEED_LIST:
            
            # 1. Scramble the scene
            # hg = HexGridParams(mod, node_group, seed)
            hg.seed = seed
            hg.rng = np.random.default_rng(seed)
            hg.csv_path = props.csv_export_path
            hg.set_params()
            
            hg.update()
            bpy.data.objects['Plane'].location[2] = hg.instance_scale
            
            props.seed = seed
            
            raw_params_dict = hg.save_params(props.csv_export_path)
            
            # 2. Format math parameters correctly
            # We must order the dictionary values exactly as feature_cols expects them
            ordered_params = [raw_params_dict[col] for col in feature_cols]
            scaled_params = scaler.transform(pd.DataFrame([ordered_params], columns=feature_cols))
            tensor_params = torch.tensor(scaled_params, dtype=torch.float32).to(device)
            
            # 3. Take screenshot and format image
            take_hidden_render()
            with Image.open(props.temp_render_path) as img:
                img_rgb = img.convert('RGB')
                tensor_img = image_transforms(img_rgb).unsqueeze(0).to(device)
            
            # 4. Ask the AI!
            output_logit = model(tensor_img, tensor_params)
            probability = torch.sigmoid(output_logit).item() * 100
            
            if probability >= 50.0:
                print(f"✅ SEED {seed}: SUCCESS! AI loves this scene ({probability:.1f}% confidence).")
                hg.save_params(props.csv_export_path,True)
                props.confidence = probability/100

                if not props.continuous:
                    break
            else:
                print(f"❌ SEED {seed}: AI rejected scene ({probability:.1f}% confidence). Rerolling...")
            
            if stop_requested:
                print(f"AI Process interrupted by user at seed {seed}!")
                return

    print("--- Hunt Finished ---")
    
    
class AIASSIST_OT_start_loop(bpy.types.Operator):
    bl_idname = "ai_assist.start_loop"
    bl_label = "Start Hunting"

    def execute(self, context):
        start_hunting()
        
        return {'FINISHED'}
    
class AIASSIST_OT_stop_loop(bpy.types.Operator):
    bl_idname = "ai_assist.stop_loop"
    bl_label = "Stop Hunting"

    def execute(self, context):
        stop_requested = True 
        return {'FINISHED'}



class AIASSIST_PT_subpanel(bpy.types.Panel):
    bl_label = "AI Assisted Validation"
    bl_idname = "AIASSIST_PT_subpanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    bl_parent_id = "MYADDON_PT_comprehensive_panel"
    
    # Optional: Add this line if you want the panel closed by default
    # bl_options = {'DEFAULT_CLOSED'} 

    def draw(self, context):
        layout = self.layout
        props = context.scene.ai_assist_props
        
        # We don't need layout.box() or booleans anymore, the sub-panel handles it
        row = layout.row()
        row.prop(props, "start")
        row.prop(props, "end")
        
        layout.prop(props, "continuous", toggle=True)
        
        box = layout.box()
        # Create a tight, aligned display block
        row = box.row(align=True)
        # Label side (takes up left space)
        row.label(text="Processing Seed:")
        # Data side (drawn inside a stylized text box, but set to locked)
        sub = row.row()
        sub.enabled = False # Completely locks interaction
        sub.prop(props, "seed", text="") # text="" hides duplicate label

        box.prop(props, "confidence", slider=True)
        
        layout.operator("ai_assist.boot_up", text="Reload AI Model & Scaler", icon='FILE_REFRESH')
        
        layout.separator()
        
        col = layout.column(align=True)
        col.prop(props, "trained_data_path", icon='DOCUMENTS')
        col.prop(props, "csv_export_path", icon='FILE_TEXT')
        col.prop(props, "ai_model_path", icon='SCRIPT')
        col.prop(props, "temp_render_path", icon='IMAGE_DATA')
        
        
        
class AIASSIST_Properties(bpy.types.PropertyGroup):
    continuous: bpy.props.BoolProperty(
        name="Continuous",
        description="The script will not stop after discovering the first valid seed",
        default=False
    )
    
    seed: bpy.props.IntProperty(
        name="Seed",
        description="Seed that is being displayed",
        default=0,
    )
    
    start: bpy.props.IntProperty(
        name="Start",
        description="Select start seed",
        default=2651,
    )
    
    end: bpy.props.IntProperty(
        name="End",
        description="Select end seed",
        default=3000,
    )
    
    trained_data_path: bpy.props.StringProperty(
        name="AI Trained Data",
        description="Path of the original data which was used to train the AI",
        default=os.path.join(scripts_dir, "data.csv"),
        maxlen=1024,
        subtype='FILE_PATH' # Magic flag that adds the native file explorer button
    )
    
    csv_export_path: bpy.props.StringProperty(
        name="CSV Storage Path",
        description="Path of the csv where the ai assited validation data will be stored",
        default=os.path.join(scripts_dir, "AI_assist_data.csv"),
        maxlen=1024,
        subtype='FILE_PATH' # Magic flag that adds the native file explorer button
    )
    
    ai_model_path: bpy.props.StringProperty(
        name="AI Model",
        description="Path of the AI model that will be used",
        default=os.path.join(scripts_dir, "multimodal_ai_bottleneck.pth"),
        maxlen=1024,
        subtype='FILE_PATH' # Magic flag that adds the native file explorer button
    )
    
    temp_render_path: bpy.props.StringProperty(
        name="Temporary render",
        description="Path of the temporary low res image that will be used for the CNN",
        default=os.path.join(scripts_dir, "temp_inference.png"),
        maxlen=1024,
        subtype='FILE_PATH' # Magic flag that adds the native file explorer button
    )
    
    confidence: bpy.props.FloatProperty(
        name="Confidence",
        description="How confident the AI is in its validity",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype='FACTOR' # This gives it the filled "progress bar" look
    )
        
classes = (
    AIASSIST_PT_subpanel,
    AIASSIST_OT_boot_ai,
    AIASSIST_Properties,
    AIASSIST_OT_start_loop,
    AIASSIST_OT_stop_loop,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.ai_assist_props = bpy.props.PointerProperty(type=AIASSIST_Properties)

    bpy.ops.ai_assist.boot_up()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.Scene.ai_assist_props