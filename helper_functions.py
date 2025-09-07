import bpy
import numpy as np
import colorsys
from mathutils import Vector, Euler

def inspect_mod_inputs(mod):

    if mod and mod.type == 'NODES':
        # The inputs are stored directly in the modifier's ["Input_#"] custom properties
        group_input_node = mod.node_group.nodes.get("Group Input")
        
        if group_input_node:
            for i, socket in enumerate(group_input_node.outputs):
                if socket.is_output and socket.name != "":
                    print(f"{i}: {socket.identifier} ({socket.name}) = {socket.default_value}")
                    
generic_props = {p.identifier for p in bpy.types.Node.bl_rna.properties}

def inspect_node(node):
    print(f"\nInspecting node: {node.name} ({node.bl_idname})")

    # Properties
    print("\nProperties:")
    specific_props = [
        p
        for p in node.bl_rna.properties
        if p.identifier not in generic_props and not p.is_readonly
    ]
    for i, prop in enumerate(specific_props):
        print(f"Property {i} - {prop.identifier}: {getattr(node, prop.identifier)}")
        
        if hasattr(prop, "enum_items") and prop.enum_items:
            options = [item.identifier for item in prop.enum_items]
            print(f"    Dropdown options: {options}")

    # Inputs
    print("\nInputs:")
    for i, socket in enumerate(node.inputs):
        if hasattr(socket, "default_value"):
            print(f"Input {i} - {socket.name}: {socket.default_value}")

    # Outputs
    print("\nOutputs:")
    for i, socket in enumerate(node.outputs):
        print(f"Output {i} - {socket.name}")

def generate_distinct_colors(rng, n_colors):
    colors = []
    for i in range(n_colors):
        h = rng.random()
        s = rng.random()
        v = rng.random()
        rgb = colorsys.hsv_to_rgb(h, s, v)
        colors.append(rgb)
    return np.array(colors)

def camera_move_and_cull(cam, cont, r, phi, theta, target, margin):
    # Convert spherical → Cartesian
    x = r * np.sin(theta) * np.cos(phi)
    y = r * np.sin(theta) * np.sin(phi)
    z = r * np.cos(theta)

    cam.location = Vector((x, y, z))

    # Make camera look at origin
    target = Vector((0, 0, 0))
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    resx = bpy.data.scenes["Scene"].render.resolution_x
    resy = bpy.data.scenes["Scene"].render.resolution_y
    ortho_scale = cam.data.ortho_scale
    
    if resx >= resy:
        
        fac = 1/(np.power(resx/resy,2))

        cont.scale[0] = ortho_scale * fac * (margin + 1) * resx/resy
        cont.scale[1] = ortho_scale * fac * (margin + 1)
        cont.scale[2] = ortho_scale * fac * 1000

        cont.rotation_euler = cam.rotation_euler
        
    else:
        
        fac = 1/(np.power(resy/resx,2))

        cont.scale[0] = ortho_scale * fac * (margin + 1) 
        cont.scale[1] = ortho_scale * fac * (margin + 1) * resy/resx
        cont.scale[2] = ortho_scale * fac * 1000

        cont.rotation_euler = cam.rotation_euler