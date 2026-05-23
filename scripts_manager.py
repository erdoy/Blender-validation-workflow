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
    
    script_selector: bpy.props.EnumProperty(
        name="Script",
        description="Choose which script to execute",
        items=[
            ('AI_assist', "AI Assisted Validation", "Run AI_assist.py", '', 1),
            ('Manual_validation', "Manual Validation", "Run Manual_validation.py", '', 2),
            ('review_validated', "Review Valid", "Run review_validated.py", '', 3),
        ],
        default='AI_assist'
    )
    
# ==============================================================================
# 1.5 DEFINE SCRIPT OPERATORS
# ==============================================================================
class MYADDON_OT_run_script(bpy.types.Operator):
    bl_label = "Run Script"
    bl_idname = "my_script.run_script" 
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        selection = context.scene.my_custom_props.script_selector
        
        RUN_MAP = {
            'AI_assist': "ai_assist.start_loop",
            'Manual_validation': "hexgrid.start_loop",
            'review_validated': "rev_val.start_loop"
        }
        
        
        if selection not in RUN_MAP:
            self.report({'ERROR'}, f"Unknown script selection: {selection}")
            return {'CANCELLED'}
            
        operator_idname = RUN_MAP[selection]
            
        try:
            
            # Split "ai_assist.start_hunting" into "ai_assist" and "start_hunting"
            category, name = operator_idname.split('.')

            # Navigate Blender's API: bpy.ops -> ai_assist -> start_hunting
            operator_func = getattr(getattr(bpy.ops, category), name)

            # Execute the operator!
            operator_func()
            
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
        
        selection = context.scene.my_custom_props.script_selector
        
        STOP_MAP = {
            'AI_assist': "ai_assist.stop_loop", 
            'Manual_validation': "hexgrid.stop_loop",
            'review_validated': "review_validated.stop_loop"
        }
        
        if selection not in STOP_MAP:
            return {'CANCELLED'}
            
        operator_idname = STOP_MAP[selection]
        
        try:
            print(f"Routing stop signal to operator: {operator_idname}")
            
            # Split "ai_assist.start_hunting" into "ai_assist" and "start_hunting"
            category, name = operator_idname.split('.')

            # Navigate Blender's API: bpy.ops -> ai_assist -> start_hunting
            operator_func = getattr(getattr(bpy.ops, category), name)

            # Execute the operator!
            operator_func()
                
        except Exception as e:
            self.report({'ERROR'}, f"Failed to stop script: {str(e)}")
            return {'CANCELLED'}
        
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


# ==============================================================================
# 3. REGISTRATION
# ==============================================================================
classes = (
    MyCustomProperties,
    MYADDON_PT_comprehensive_panel,
    MYADDON_OT_run_script,
    MYADDON_OT_stop_script,
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
    import Manual_validation, review_validated, AI_assist
    
    sub_modules = [
        Manual_validation,
        review_validated,
        AI_assist
    ]

    # 1. UNREGISTER FIRST (Reverse order is best practice)
    # We must unregister the old cached versions before we reload the files
    for mod in reversed(sub_modules):
        try:
            mod.unregister()
        except Exception:
            pass
            
    try:
        unregister() # Unregister the main file's classes
    except Exception:
        pass

    # 2. RELOAD MEMORY
    # Forces Blender to read the physical text files from the hard drive again
    for mod in sub_modules:
        importlib.reload(mod)

    # 3. REGISTER EVERYTHING
    register() # Register main file
    
    for mod in sub_modules:
        mod.register()
        
    print("✅ All modules successfully reloaded and registered!")