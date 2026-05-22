from hexgrid_params import *

CSV_PATH = os.path.join(scripts_dir, "data.csv")

mod = bpy.data.objects["HexGridController"].modifiers["HexGrid"]
node_group = bpy.data.node_groups['HexGridGroup']
hg = HexGridParams(mod,node_group,0)

df = pd.read_csv(CSV_PATH)

df_valid = df[df['valid'] == True]
seed_valid = df_valid["seed"].astype(int).reset_index(drop=True).tolist()

# Global variables for loop control
iteration = 0
loop_running = False

def run_loop():
    global iteration, loop_running
    if not loop_running or iteration >= len(seed_valid) or iteration < 0:
        running = False
        print("Seed loop stopped.")
        return None

    hg.load_params(seed_valid[iteration],CSV_PATH)
    hg.update()
    bpy.data.objects['Plane'].location[2] = hg.instance_scale
    
    print(f"Iteration: {iteration}\nSeed: {seed_valid[iteration]}")
    
    return None 

# Panel UI to start/stop the loop
class REV_VAL_PT_panel(bpy.types.Panel):
    bl_label = "Review Validated"
    bl_idname = "REV_VAL_PT_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_category = "HexGrid"
    bl_parent_id = "MYADDON_PT_comprehensive_panel"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

#        layout.prop(scene, "hexgrid_csv_path")
        row = layout.row()
        if loop_running:
            row.operator("rev_val.stop_loop", text="Stop Loop", icon='PAUSE')
            
            layout.separator()
            layout.label(text="View iteration:")
            nav_row = layout.row()
            
            nav_row.operator("rev_val.previous", text="Previous", icon='EVENT_LEFT_ARROW')
            nav_row.operator("rev_val.next", text="Next", icon='EVENT_RIGHT_ARROW')
        else:
            row.operator("rev_val.start_loop", text="Start Loop", icon='PLAY')

class REV_VAL_OT_start_loop(bpy.types.Operator):
    bl_idname = "rev_val.start_loop"
    bl_label = "Start HexGrid Loop"

    def execute(self, context):
        global loop_running, iteration
        if not loop_running:
            loop_running = True
            iteration = 0
            bpy.app.timers.register(run_loop)
            print("Started loop")
        return {'FINISHED'}
    
class REV_VAL_OT_next(bpy.types.Operator):
    bl_idname = "rev_val.next"
    bl_label = "Next"

    def execute(self, context):
        global loop_running, iteration
        if loop_running:
            loop_running = True
            iteration += 1
            bpy.app.timers.register(run_loop)
        return {'FINISHED'}
    
class REV_VAL_OT_previous(bpy.types.Operator):
    bl_idname = "rev_val.previous"
    bl_label = "Previous"

    def execute(self, context):
        global loop_running, iteration
        if loop_running:
            loop_running = True
            iteration -= 1
            bpy.app.timers.register(run_loop)
        return {'FINISHED'}

class REV_VAL_OT_stop_loop(bpy.types.Operator):
    bl_idname = "rev_val.stop_loop"
    bl_label = "Stop HexGrid Loop"

    def execute(self, context):
        global loop_running
        loop_running = False
        print("Stopped loop")
        return {'FINISHED'}


classes = (REV_VAL_PT_panel, REV_VAL_OT_start_loop, REV_VAL_OT_stop_loop, REV_VAL_OT_next, REV_VAL_OT_previous)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass  # class not registered

def register():
    unregister()
    for cls in classes:
        bpy.utils.register_class(cls)

#if __name__ == "__main__":
#    register()