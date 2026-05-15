import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set up clean styling for our charts
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# 1. Load the data
file_path = 'C:/Users/FABLAB/Documents/BlenderScripts/data.csv'
df = pd.read_csv(file_path, nrows=2504)

# 2. Basic Cleaning (Keep 'camera_target' parsing out for simple visualization)
df = df.drop(columns=['seed', 'camera_target'], errors='ignore')
df['valid'] = df['valid'].astype(int)

# Drop completely static columns so they don't clog up our charts
df = df.loc[:, df.nunique() > 1]

print("Generating visualizations...")

# -------------------------------------------------------------
# CHART 1: Data Balance (How many Valid vs Invalid scenes?)
# -------------------------------------------------------------
plt.figure(figsize=(6, 5))
valid_counts = df['valid'].value_counts()
plt.pie(valid_counts, labels=['Invalid (0)', 'Valid (1)'], autopct='%1.1f%%', colors=['#ff9999','#6bc183'], startangle=90)
plt.title('Proportion of Valid vs Invalid Scenes')
plt.tight_layout()
plt.savefig('1_scene_balance.png')
plt.close()

# -------------------------------------------------------------
# CHART 2: Correlation Bar Chart (Which parameters matter most?)
# -------------------------------------------------------------
plt.figure(figsize=(12, 6))
# Calculate how each column correlates with the 'valid' status
correlations = df.corr()['valid'].drop('valid').sort_values()

# Plot the bars
colors = ['#d95f02' if x < 0 else '#1f77b4' for x in correlations]
correlations.plot(kind='barh', color=colors)
plt.axvline(x=0, color='black', linestyle='--', linewidth=1)
plt.title('Which Parameters Impact Scene Validity the Most?', fontsize=14, fontweight='bold')
plt.xlabel('Correlation with "Valid" Status (Higher Absolute Value = More Important)')
plt.ylabel('Parameters')
plt.tight_layout()
plt.savefig('2_parameter_importance.png')
plt.close()

# -------------------------------------------------------------
# CHART 3: Parameter Ranges (Boxplots for top 3 parameters)
# -------------------------------------------------------------
# Find the top 3 absolute highest correlating parameters to look at closely
top_features = correlations.abs().sort_values(ascending=False).head(3).index.tolist()

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle('Ideal Numerical Ranges for Your Top 3 Most Important Parameters', fontsize=14, fontweight='bold')

for i, feature in enumerate(top_features):
    # Creating boxplots to show the spread, median, and ranges of the parameters
    sns.boxplot(ax=axes[i], x='valid', y=feature, data=df, palette=['#ff9999','#6bc183'], hue='valid', legend=False)
    axes[i].set_title(f'{feature} Distribution')
    axes[i].set_xlabel('Scene Status (0=Invalid, 1=Valid)')
    axes[i].set_ylabel('Parameter Value')

plt.tight_layout()
plt.savefig('3_parameter_ranges.png')
plt.close()

print("\n--- Visualizations Exported Successfully! ---")
print("Check your folder for these 3 new images:")
print("1. 1_scene_balance.png")
print("2. 2_parameter_importance.png")
print("3. 3_parameter_ranges.png")