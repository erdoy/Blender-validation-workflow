import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_curve, auc

import matplotlib.pyplot as plt
import seaborn as sns

# Set random seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# =============================================================
# 1. DATA PREPROCESSING
# =============================================================
file_path = 'C:/Users/FABLAB/Documents/BlenderScripts/data.csv'
df = pd.read_csv(file_path, nrows=2504)

# Handle NaNs and format target
df = df.dropna(subset=['valid'])
df['valid'] = df['valid'].astype(int)

# FIX: Parse camera_target vector strings into distinct numeric columns before dropping
vector_regex = r'<Vector \(([^,]+),\s*([^,]+),\s*([^>]+)\)>'
df[['camera_target_x', 'camera_target_y', 'camera_target_z']] = df['camera_target'].str.extract(vector_regex).astype(float)
df = df.drop(columns=['camera_target', 'seed'], errors='ignore')

# Drop any static zero-variance columns
df = df.loc[:, df.nunique() > 1]

# Split features and target
X = df.drop(columns=['valid'])
y = df['valid'].values

# Train / Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Standardize feature ranges
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# =============================================================
# 2. CONVERT DATA TO PYTORCH TENSORS
# =============================================================
X_train_tensor = torch.tensor(X_train_scaled, dtype=torch.float32)
y_train_tensor = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1) 

X_test_tensor = torch.tensor(X_test_scaled, dtype=torch.float32)
y_test_tensor = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1)

# Package tensors into PyTorch DataLoaders for easy batching
train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

# =============================================================
# 3. DEFINE THE NEURAL NETWORK ARCHITECTURE
# =============================================================
class SceneClassifier(nn.Module):
    def __init__(self, input_dim):
        super(SceneClassifier, self).__init__()
        self.layer1 = nn.Linear(input_dim, 64)
        self.layer2 = nn.Linear(64, 32)
        self.output_layer = nn.Linear(32, 1) # Outputs a raw logit [batch_size, 1]
        self.relu = nn.ReLU()         
        
    def forward(self, x):
        x = self.relu(self.layer1(x))
        x = self.relu(self.layer2(x))
        x = self.output_layer(x) # FIX: Added missing output layer calculation
        return x

# Instantiate the model using the exact number of incoming features
input_dimensions = X_train_scaled.shape[1]
model = SceneClassifier(input_dim=input_dimensions)

# =============================================================
# 4. DEFINE LOSS & OPTIMIZER
# =============================================================
num_invalid = (y_train == 0).sum()
num_valid = (y_train == 1).sum()
class_weight = torch.tensor([num_invalid / num_valid], dtype=torch.float32)

criterion = nn.BCEWithLogitsLoss(pos_weight=class_weight)
optimizer = optim.Adam(model.parameters(), lr=0.005) 

# =============================================================
# 5. TRAINING WITH HISTORICAL TRACKING
# =============================================================
epochs = 40
history = {'loss': [], 'accuracy': []}

print("Training weighted model and collecting epoch-by-epoch diagnostics...")

for epoch in range(epochs):
    model.train()
    epoch_loss = 0.0
    correct_train = 0
    
    for batch_X, batch_y in train_loader:
        optimizer.zero_grad()
        predictions = model(batch_X)
        loss = criterion(predictions, batch_y)
        loss.backward()
        optimizer.step()
        
        epoch_loss += loss.item() * batch_X.size(0)
        
        # FIX: Apply sigmoid to predictions before checking threshold for accuracy tracking
        probs = torch.sigmoid(predictions)
        correct_train += ((probs >= 0.5).float() == batch_y).sum().item()
        
    # Store metrics for this epoch
    total_epoch_loss = epoch_loss / len(train_loader.dataset)
    total_epoch_acc = (correct_train / len(train_loader.dataset)) * 100
    history['loss'].append(total_epoch_loss)
    history['accuracy'].append(total_epoch_acc)

# =============================================================
# 6. ADVANCED PERFORMANCE EVALUATION
# =============================================================
model.eval()
with torch.no_grad():
    # FIX: Map logits to probabilities via sigmoid for performance metrics
    test_logits = model(X_test_tensor)
    test_probabilities = torch.sigmoid(test_logits).numpy()
    predicted_classes = (test_probabilities >= 0.5).astype(int)

# Calculate advanced metrics
precision = precision_score(y_test, predicted_classes)
recall = recall_score(y_test, predicted_classes)
f1 = f1_score(y_test, predicted_classes)

print("\n=============================================")
print("          ADVANCED MODEL STATISTICS          ")
print("=============================================")
print(f"Precision: {precision:.4f}  <- (When it claims a scene is valid, how often is it right?)")
print(f"Recall:    {recall:.4f}  <- (Out of all scenes you actually liked, how many did it catch?)")
print(f"F1-Score:  {f1:.4f}  <- (The balanced harmonic mean of Precision and Recall)")
print("=============================================\n")

print("Detailed Classification Report:")
print(classification_report(y_test, predicted_classes, target_names=['Invalid (0)', 'Valid (1)']))

# =============================================================
# 7. GENERATE DIAGNOSTIC CHARTS
# =============================================================
sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Plot 1: History vs Epochs
axes[0].plot(range(1, epochs + 1), history['loss'], color='#d95f02', linewidth=2, label='Training Loss')
axes[0].set_ylabel('Loss', color='#d95f02', fontsize=12)
axes[0].tick_params(axis='y', labelcolor='#d95f02')

ax2 = axes[0].twinx()
ax2.plot(range(1, epochs + 1), history['accuracy'], color='#1f77b4', linewidth=2, label='Training Accuracy')
ax2.set_ylabel('Accuracy (%)', color='#1f77b4', fontsize=12)
ax2.tick_params(axis='y', labelcolor='#1f77b4')

axes[0].set_xlabel('Epochs', fontsize=12)
axes[0].set_title('Evolution of Statistics vs. Epochs', fontsize=14, fontweight='bold')

# Plot 2: ROC Curve
fpr, tpr, thresholds = roc_curve(y_test, test_probabilities)
roc_auc = auc(fpr, tpr)

axes[1].plot(fpr, tpr, color='#2ca02c', linewidth=2, label=f'ROC Curve (AUC = {roc_auc:.4f})')
axes[1].plot([0, 1], [0, 1], color='gray', linestyle='--') 
axes[1].set_xlim([0.0, 1.0])
axes[1].set_ylim([0.0, 1.05])
axes[1].set_xlabel('False Positive Rate (Type I Error)', fontsize=12)
axes[1].set_ylabel('True Positive Rate (Sensitivity / Recall)', fontsize=12)
axes[1].set_title('Receiver Operating Characteristic (ROC) Curve', fontsize=14, fontweight='bold')
axes[1].legend(loc="lower right")

plt.tight_layout()
output_chart = 'C:/Users/FABLAB/Documents/BlenderScripts/model_diagnostics.png'
plt.savefig(output_chart, dpi=150)
plt.close()

print(f"Diagnostic graphs saved to: {output_chart}")
