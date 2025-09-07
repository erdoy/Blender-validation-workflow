import sys
sys.path.append(r"C:\Users\1234\Documents\Obsidian\Blender\Terrain_random_perfeccionar")
from hexgrid_params import *
from helper_functions import inspect_mod_inputs, inspect_node, generate_distinct_colors

# === CONFIG ===
CSV_PATH = r"C:\Users\1234\Documents\Obsidian\Blender\Terrain_random_perfeccionar\data.csv"
SEED_LIST = list(range(0, 201)) 

running = False
current_seed_index = 0
pending_review = False

obj = bpy.data.objects["HexGridController"]
mod = bpy.data.objects["HexGridController"].modifiers["HexGrid"]
node_group = bpy.data.node_groups['HexGridGroup']
           
#nodes = node_group.nodes

#node_id = [(node.name, node.bl_idname) for node in nodes]
#for i,name_id in enumerate(node_id):
#    print(i,name_id) 
#            
#inspect_mod_inputs(mod)
#inspect_node(nodes[6])


# === Loop logic ===
def process_next_seed():
    global current_seed_index, running, pending_review
    if not running or current_seed_index >= len(SEED_LIST):
        running = False
        pending_review = False
        print("Seed loop stopped.")
        return None

    seed = SEED_LIST[current_seed_index]
    print(f"Generating seed {seed}...")

    
    hg = HexGridParams(mod, node_group, seed)
    hg.set_params()
    hg.update()#modifying
    bpy.data.objects['Plane'].location[2] = hg.instance_scale

    bpy.types.Scene.hexgrid_current_hg = hg
    pending_review = True

    # Switch to camera view
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'

    bpy.context.view_layer.update()

    print("Waiting for user validation (Y/N)...")
    return None


# --- Operators for marking valid/invalid ---
class HEXGRID_OT_mark_valid(bpy.types.Operator):
    bl_idname = "hexgrid.mark_valid"
    bl_label = "Mark Valid"

    def execute(self, context):
        global current_seed_index, pending_review
        hg = bpy.types.Scene.hexgrid_current_hg
        hg.save_params(CSV_PATH, valid=True)
        pending_review = False
        current_seed_index += 1
        bpy.app.timers.register(process_next_seed, first_interval=0.01)
        return {'FINISHED'}


class HEXGRID_OT_mark_invalid(bpy.types.Operator):
    bl_idname = "hexgrid.mark_invalid"
    bl_label = "Mark Invalid"

    def execute(self, context):
        global current_seed_index, pending_review
        hg = bpy.types.Scene.hexgrid_current_hg
        hg.save_params(CSV_PATH, valid=False)
        pending_review = False
        current_seed_index += 1
        bpy.app.timers.register(process_next_seed, first_interval=0.01)
        return {'FINISHED'}


# --- Operators for start/stop ---
class HEXGRID_OT_start_loop(bpy.types.Operator):
    bl_idname = "hexgrid.start_loop"
    bl_label = "Start Seed Loop"

    def execute(self, context):
        global running, current_seed_index
        running = True
        current_seed_index = 0
        bpy.app.timers.register(process_next_seed, first_interval=0.01)
        print("Seed loop started.")
        return {'FINISHED'}


class HEXGRID_OT_stop_loop(bpy.types.Operator):
    bl_idname = "hexgrid.stop_loop"
    bl_label = "Stop Seed Loop"

    def execute(self, context):
        global running
        running = False
        print("Seed loop stopped by user.")
        return {'FINISHED'}


# --- Keypress handler for Y/N ---
class HEXGRID_OT_keypress_handler(bpy.types.Operator):
    bl_idname = "hexgrid.keypress_handler"
    bl_label = "HexGrid Keypress Handler"
    bl_options = {'REGISTER'}

    def modal(self, context, event):
        global pending_review
        if not pending_review:
            return {'PASS_THROUGH'}

        if event.type == 'Y' and event.value == 'PRESS':
            bpy.ops.hexgrid.mark_valid()
            print("Marked as VALID by keypress Y.")
            return {'RUNNING_MODAL'}
        elif event.type == 'N' and event.value == 'PRESS':
            bpy.ops.hexgrid.mark_invalid()
            print("Marked as INVALID by keypress N.")
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        print("Keypress handler started. Press Y or N to validate current seed.")
        return {'RUNNING_MODAL'}


# --- UI Panel ---
class HEXGRID_PT_panel(bpy.types.Panel):
    bl_label = "HexGrid Control"
    bl_idname = "HEXGRID_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'HexGrid'

    def draw(self, context):
        layout = self.layout
        layout.operator("hexgrid.start_loop", text="Start Seed Loop")
        layout.operator("hexgrid.stop_loop", text="Stop Seed Loop")
        layout.separator()
        layout.label(text="Review (buttons or keys):")
        layout.operator("hexgrid.mark_valid", text="Valid (Button)")
        layout.operator("hexgrid.mark_invalid", text="Invalid (Button)")
        layout.operator("hexgrid.keypress_handler", text="Enable Keypress Validation")


# --- Registration ---
classes = (
    HEXGRID_OT_start_loop,
    HEXGRID_OT_stop_loop,
    HEXGRID_OT_mark_valid,
    HEXGRID_OT_mark_invalid,
    HEXGRID_OT_keypress_handler,
    HEXGRID_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print("HexGrid Addon Registered.")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("HexGrid Addon Unregistered.")

if __name__ == "__main__":
    register()
    
