import bpy
import os
import site
import sys

blend_file_path = bpy.data.filepath
scripts_dir = os.path.dirname(blend_file_path)
user_site_packages = site.getusersitepackages()

if user_site_packages not in sys.path:
    sys.path.append(user_site_packages)

if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)
    
import importlib
    

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
        default=0,
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
    
    continuous: bpy.props.BoolProperty(
        name="Continuous",
        description="The script will not stop after discovering the first valid seed",
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
    
    confidence: bpy.props.FloatProperty(
        name="Confidence",
        description="How confident the AI is in its validity",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype='FACTOR' # This gives it the filled "progress bar" look
    )
    
    show_seed_box: bpy.props.BoolProperty(
        name="Seed Range",
        default=True # Set to False if you want it closed by default
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
    
    script_selector: bpy.props.EnumProperty(
        name="Script",
        description="Choose which script to execute",
        items=[
            ('ASSIST_VALID', "AI Assisted Validation", "Run AI_assist.py", '', 1),
            ('MANUAL_VALID', "Manual Validation", "Run Human_in_the_middle_validation.py", '', 2),
            ('REVIEW_VALID', "Review Valid", "Run review_validated.py", '', 3),
        ],
        default='ASSIST_VALID'
    )
    
# ==============================================================================
# 1.5 DEFINE SCRIPT OPERATORS
# ==============================================================================
class MYADDON_OT_run_script(bpy.types.Operator):
    bl_label = "Run Script"
    bl_idname = "my_script.run_script" 
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        props = context.scene.my_custom_props
        
        SCRIPT_MAP = {
            'ASSIST_VALID': ("AI_assist", "start_hunting", True),
            'MANUAL_VALID': ("Human_in_the_middle_validation", "register", False),
            'REVIEW_VALID': ("review_validated", "register", False)
        }
        
        selection = props.script_selector
        if selection not in SCRIPT_MAP:
            self.report({'ERROR'}, f"Unknown script selection: {selection}")
            return {'CANCELLED'}
            
        module_name, func_name, uses_seeds = SCRIPT_MAP[selection]
            
        try:
            module = importlib.import_module(module_name)
            importlib.reload(module)
            
            # 4. Run the function you defined inside your script
            run_func = getattr(module, func_name)
            
            run_func(props.start, props.end, context, props.continuous)
            
#            AI_assist.start_hunting(props.start,props.end,context,props.continuous)
            
            self.report({'INFO'}, f"Executed script: {selection}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Script failed: {str(e)}")
            import traceback
            traceback.print_exc() # Prints the full error to the system console
            return {'CANCELLED'}

        return {'FINISHED'}
    
class MYADDON_OT_stop_script(bpy.types.Operator):
    bl_label = "Stop Script"
    bl_idname = "my_script.stop_script" 

    def execute(self, context):
        # Trigger the kill switch!
        # Notice we do NOT reload() here, because we want to modify 
        # the exact instance that is currently running.
        AI_assist.stop_requested = True 
        
        self.report({'WARNING'}, "Sent stop signal to AI!")
        return {'FINISHED'}

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
        props = scene.my_custom_props

        # --- 1. Basic Text and Strings ---
#        layout.label(text="Basic Inputs:", icon='INFO')
#        layout.prop(props, "my_string", icon='TEXT')
        
#        layout.separator() # Adds a small vertical gap
        
        layout.prop(props, "script_selector")
        
        row = layout.row(align=True) 
        row.operator("my_script.run_script", text="Run Script", icon='PLAY')
        row.operator("my_script.stop_script", text="Stop Script", icon='PAUSE')
        
#        layout.separator() # Adds a small vertical gap
        

#        layout.separator()

#        # --- 3. Toggles and Layout Alignments ---
#        # align=True makes elements stick together without gaps
#        row = layout.row(align=True) 
#        row.prop(props, "my_bool", toggle=True) # toggle=True makes it a button instead of a checkbox
#        row.operator("mesh.primitive_cube_add", text="Action!") # Native button
#        
#        # Standard checkbox
#        layout.prop(props, "my_bool") 

#        # --- 4. Dropdowns and Color Pickers ---
#        layout.separator()
#        layout.label(text="Visuals & Modes:")
#        
#        # Split divides the row into percentage-based columns (0.3 = 30% / 70%)
#        split = layout.split(factor=0.3)
#        split.label(text="Color:")
#        split.prop(props, "my_color", text="") # text="" hides the label so just the picker shows
#        
#        layout.prop(props, "my_enum", expand=False) # expand=False = Dropdown. True = Row of buttons.

#        # --- 5. Conditional UI (Displays only if conditions are met) ---
#        layout.separator()
#        if props.my_bool:
#            col = layout.column()
#            col.alert = True # Makes the UI element red to grab attention
#            col.label(text="Feature X is currently ENABLED!")
#            col.operator("render.render", icon='RENDER_STILL')
#        else:
#            layout.label(text="Check the box to reveal more options...", icon='RESTRICT_VIEW_ON')

class MYADDON_PT_AI_assist_subpanel(bpy.types.Panel):
    bl_label = "AI Assisted Validation"
    bl_idname = "MYADDON_PT_AI_assist_subpanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    
    # THIS is the magic line that makes it a subsection of the panel above
    bl_parent_id = "MYADDON_PT_comprehensive_panel"
    
    # Optional: Add this line if you want the panel closed by default
    # bl_options = {'DEFAULT_CLOSED'} 

    def draw(self, context):
        layout = self.layout
        props = context.scene.my_custom_props
        
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

#import Human_in_the_middle_validation
#from Human_in_the_middle_validation import *

# ==============================================================================
# 3. REGISTRATION
# ==============================================================================
classes = (
    MyCustomProperties,
    MYADDON_PT_comprehensive_panel,
    MYADDON_OT_run_script,
    MYADDON_OT_stop_script,
    MYADDON_PT_AI_assist_subpanel,
#    HEXGRID_PT_panel,
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
    
if __name__ == "__main__":
    import Human_in_the_middle_validation, review_validated
    classes = classes + Human_in_the_middle_validation.classes + tuple(review_validated.classes)
    
    try:
        unregister()
    except Exception:
        pass
    
    register()