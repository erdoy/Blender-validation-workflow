




# TO-DO
# the idea is to generate a script to just batch generate the csv data without the valid parameter.

# selection criteria: if NaN in row > 2













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

# === CONFIG ===
CSV_PATH = os.path.join(scripts_dir, "data.csv")
SEED_LIST = list(range(2002, 3000)) 

df = pd.read_csv(CSV_PATH)

