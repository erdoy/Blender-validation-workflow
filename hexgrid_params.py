import bpy
import numpy as np
import pandas as pd
import os
from mathutils import Vector, Euler
from helper_functions import generate_distinct_colors, camera_move_and_cull


class HexGridParams:
    def __init__(self, mod, node_group, seed):
        self.seed = seed
        self.rng = np.random.default_rng(seed=self.seed)

        self.mod = mod
        self.node_group = node_group
        self.nodes = self.node_group.nodes

        self.n_colors = 3
        self.colors = None
        self.offset = None
        self.scale = None
        self.detail = None
        self.roughness = None
        self.lacunarity = None
        self.distortion = None
        self.instance_scale = None
        
        self.light_altitude = None
        self.light_azimuth = None
        
        self.camera_dist = None
        self.camera_azimuth = None
        self.camera_polar = None
        self.camera_target = None
        self.camera_scale = None
        
        self.csv_path = None
        
#    def sync_color_ramp(self,keys,scene=None):

#        try:
#            color_ramp = self.nodes["Color Ramp"]
#            for i, col in enumerate(self.colors):
#                color_ramp.color_ramp.elements[i].color = (*col, 1.0)
#                self.mod[keys[i]] = (*col, 1.0)

#        except Exception as e:
#            print("Color Ramp Sync Error:", e)

    # Register handler to run on depsgraph update
#        bpy.app.handlers.depsgraph_update_post.clear()
#        bpy.app.handlers.depsgraph_update_post.append(sync_color_ramp)

    def set_params(self):
        self.colors = generate_distinct_colors(self.rng, self.n_colors)
        
        self.offset = self.rng.uniform(-999999, 999999, 3)
        self.scale = self.rng.normal(0, .1)
        self.detail = self.rng.uniform(0, 15)
        self.roughness = self.rng.random()
        self.lacunarity = self.rng.uniform(0, 2)
        self.distortion = self.rng.uniform(0, 4)
        self.instance_scale = self.rng.uniform(6, 16)
        
        self.light_altitude = self.rng.uniform(0.2, 1.0)
        self.light_azimuth = self.rng.uniform(0, 2*np.pi)
        
        self.camera_dist = 200
        self.camera_azimuth = self.rng.uniform(0, 2*np.pi) 
        self.camera_polar = self.rng.uniform(1/9*np.pi, np.pi/3)
        self.camera_target = Vector((0, 0, 0))
        self.camera_scale = self.rng.uniform(30, 150)

    def update(self):
        ids = [i[0] for i in self.mod.items() if "attribute" not in i[0]]
        names = ["Rows", "Cols", "Seed", "Offset", "Scale", "Detail", "Roughness", "Lacunarity", "Distortion", "Height", "Color 1", "Color 2", "Color 3"]
        d = dict(zip(names, ids))

#        self.mod[d["Rows"]] = self.rows
#        self.mod[d["Cols"]] = self.cols
        self.mod[d["Seed"]] = self.seed
        self.mod[d["Offset"]] = self.offset
        self.mod[d["Scale"]] = self.scale
        self.mod[d["Detail"]] = self.detail
        self.mod[d["Roughness"]] = self.roughness
        self.mod[d["Lacunarity"]] = self.lacunarity
        self.mod[d["Distortion"]] = self.distortion
        self.mod[d["Height"]] = self.instance_scale
        
        color_ramp = self.nodes["Color Ramp"]
        for i, col in enumerate(self.colors):
            color_ramp.color_ramp.elements[i].color = (*col, 1.0)
            self.mod[d[f"Color {1+i}"]] = (*col, 1.0)
            
        sun = bpy.data.objects.get("Sun")
        if sun and sun.type == "LIGHT" and sun.data.type == "SUN":
            sun.rotation_euler = (self.light_altitude, 0, self.light_azimuth)
            
        cam = bpy.data.objects.get("Camera")
        cont = bpy.data.objects.get("Camera_culler")
        
        cam.data.ortho_scale = self.camera_scale
        camera_move_and_cull(cam, cont, self.camera_dist, self.camera_azimuth, self.camera_polar, self.camera_target, .2)

        bpy.context.view_layer.update()
        self.mod.show_viewport = True
        
    def load_params(self,seed,path=None):
        if path is None:
            path = self.csv_path
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV file not found at: {path}")
        
        df = pd.read_csv(path)
        
        if seed not in df["seed"].values:
            raise ValueError(f"Seed {seed} not found in CSV.")

        self.seed = seed
        self.rng = np.random.default_rng(seed=self.seed)

        row = df.loc[df["seed"] == seed].iloc[0]
        
        self.scale = row["scale"]
        self.detail = row["detail"]
        self.roughness = row["roughness"]
        self.lacunarity = row["lacunarity"]
        self.distortion = row["distortion"]
        self.instance_scale = row["instance_scale"]
        self.light_altitude = row["light_altitude"]
        self.light_azimuth = row["light_azimuth"]
        self.camera_dist = row["camera_dist"]
        self.camera_azimuth = row["camera_azimuth"]
        self.camera_polar = row["camera_polar"]
        self.camera_target = row["camera_target"]
        self.camera_scale = row["camera_scale"]

        colors = []
        for i in range(self.n_colors):
            colors.append([
                row[f"color_{i}_r"],
                row[f"color_{i}_g"],
                row[f"color_{i}_b"]
            ])
        self.colors = np.array(colors)
        
        self.offset = np.array([row["offset_x"],row["offset_y"],row["offset_z"]])
        
        self.csv_path = path

    def save_params(self, path=None, valid=None):
        if path is None:
            path = self.csv_path
            
        data = {
            "seed": self.seed,
            "scale": self.scale,
            "detail": self.detail,
            "roughness": self.roughness,
            "lacunarity": self.lacunarity,
            "distortion": self.distortion,
            "instance_scale": self.instance_scale,
            "light_altitude": self.light_altitude,
            "light_azimuth": self.light_azimuth,
            "camera_dist": self.camera_dist,
            "camera_azimuth": self.camera_azimuth,
            "camera_polar": self.camera_polar,
            "camera_target": self.camera_target,
            "camera_scale": self.camera_scale,
            "valid": valid
        }
        for i in range(self.n_colors):
            data[f"color_{i}_r"] = self.colors[i, 0]
            data[f"color_{i}_g"] = self.colors[i, 1]
            data[f"color_{i}_b"] = self.colors[i, 2]
            
        for i in range(self.n_colors):
            data["offset_x"] = self.offset[0]
            data["offset_y"] = self.offset[1]
            data["offset_z"] = self.offset[2]

        df_new = pd.DataFrame([data])

        if os.path.exists(path):
            df_existing = pd.read_csv(path)
            
            if self.seed in df_existing["seed"].values:
                idx = df_existing.index[df_existing["seed"] == self.seed][0]
                for col in df_new.columns:
                    df_existing.at[idx, col] = df_new.at[0, col]
            else:
                df_existing = pd.concat([df_existing, df_new], ignore_index=True)
            df_existing.to_csv(path, index=False)
        else:
            df_new.to_csv(path, mode="w", header=True, index=False)
            
        self.csv_path = path
        
#    def complete_params(self, path, cols, valid = None):
#        if path is None:
#            path = self.csv_path
#            
#        data = {
#            "seed": self.seed,
#            "scale": self.scale,
#            "detail": self.detail,
#            "roughness": self.roughness,
#            "lacunarity": self.lacunarity,
#            "distortion": self.distortion,
#            "instance_scale": self.instance_scale,
#            "light_altitude": self.light_altitude,
#            "light_azimuth": self.light_azimuth,
#            "camera_dist": self.camera_dist,
#            "camera_azimuth": self.camera_azimuth,
#            "camera_polar": self.camera_polar,
#            "camera_target": self.camera_target,
#            "camera_scale": self.camera_scale,
#            "valid": valid
#        }
#        for i in range(self.n_colors):
#            data[f"color_{i}_r"] = self.colors[i, 0]
#            data[f"color_{i}_g"] = self.colors[i, 1]
#            data[f"color_{i}_b"] = self.colors[i, 2]
#            
#        for i in range(self.n_colors):
#            data["offset_x"] = self.offset[0]
#            data["offset_y"] = self.offset[1]
#            data["offset_z"] = self.offset[2]

#        df_new = pd.DataFrame([data])

#        if os.path.exists(path):
#            df_existing = pd.read_csv(path)
#            
#            if self.seed in df_existing["seed"].values:
#                idx = df_existing.index[df_existing["seed"] == self.seed][0]
#                for col in cols:
#                    if col not in df_existing.columns:
#                        df_existing['offset'] = None
#                    else:
#                        df_existing.at[idx, col] = df_new.at[0, col]
#            else:
#                df_existing = pd.concat([df_existing, df_new], ignore_index=True)
#            df_existing.to_csv(path, index=False)
#        else:
#            df_new.to_csv(path, mode="w", header=True, index=False)
#            
#        self.csv_path = path
        

