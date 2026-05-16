# This is a CNN to study the best image classification based on images

import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_curve, auc

import matplotlib.pyplot as plt
import seaborn as sns

# Set random seed
torch.manual_seed(42)
np.random.seed(42)

# Auto-detect GPU for massive speedups
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Training on device: {device}")

# =============================================================
# 1. SETUP PATHS AND READ DATA
# =============================================================
scripts_dir = r"C:/Users/FABLAB/Documents/BlenderScripts"
CSV_PATH = os.path.join(scripts_dir, "data.csv")
IMG_DIR = os.path.join(scripts_dir, "low_res_renders")

# Read CSV and filter missing values
df = pd.read_csv(CSV_PATH, nrows=2504)

df = df.dropna(subset=['valid']).reset_index(drop=True)
df['valid'] = df['valid'].astype(int)

# Verify image files actually exist (in case Blender skipped some)
valid_rows = []
for idx, row in df.iterrows():
    seed = int(row['seed'])
    img_path = os.path.join(IMG_DIR, f"{seed}.png")
    if os.path.exists(img_path):
        valid_rows.append(row)

df = pd.DataFrame(valid_rows)
print(f"Found {len(df)} rows with perfectly matching image files.")

# Split data into Train and Test
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['valid'])

# =============================================================
# 2. DEFINE IMAGE TRANSFORMS (Data Augmentation)
# =============================================================
# Training gets random flips to artificially multiply our data
train_transforms = transforms.Compose([
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(degrees=15),
    transforms.ToTensor(), # Converts 0-255 pixels to 0.0-1.0 PyTorch Tensors
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]) # Standardizes colors
])

# Testing only gets standardized (no cheating with flips)
test_transforms = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
])

# =============================================================
# 3. BUILD THE CUSTOM DATASET
# =============================================================
class BlenderImageDataset(Dataset):
    def __init__(self, dataframe, img_dir, transform=None):
        self.dataframe = dataframe.reset_index(drop=True)
        self.img_dir = img_dir
        self.transform = transform

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        # Extract seed and label
        seed = int(self.dataframe.loc[idx, 'seed'])
        label = self.dataframe.loc[idx, 'valid']
        
        # Load image
        img_path = os.path.join(self.img_dir, f"{seed}.png")
        image = Image.open(img_path).convert('RGB') # Ensure it's 3-channel color
        
        # Apply visual augmentations
        if self.transform:
            image = self.transform(image)
            
        # Return image matrix and label
        return image, torch.tensor(label, dtype=torch.float32).unsqueeze(0)

# Initialize DataLoaders
train_dataset = BlenderImageDataset(train_df, IMG_DIR, transform=train_transforms)
test_dataset = BlenderImageDataset(test_df, IMG_DIR, transform=test_transforms)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

# =============================================================
# 4. DEFINE THE CNN ARCHITECTURE
# =============================================================
class VisualSceneClassifier(nn.Module):
    def __init__(self):
        super(VisualSceneClassifier, self).__init__()
        
        # Convolutional Feature Extractor
        self.features = nn.Sequential(
            # Layer 1: Takes 3 color channels, outputs 16 feature maps
            nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2), # Shrinks 128x128 to 64x64
            
            # Layer 2: Outputs 32 feature maps
            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2), # Shrinks to 32x32
            
            # Layer 3: Outputs 64 feature maps
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2), # Shrinks to 16x16
        )
        
        # Decision Maker (Fully Connected Layers)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 16 * 16, 128), # 64 channels * 16 height * 16 width
            nn.ReLU(),
            nn.Dropout(0.5), # Drops 50% of connections to prevent overfitting
            nn.Linear(128, 1) # Outputs a raw logit
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

model = VisualSceneClassifier().to(device)

# =============================================================
# 5. CLASS WEIGHTS & OPTIMIZER
# =============================================================
y_train = train_df['valid'].values
num_invalid = (y_train == 0).sum()
num_valid = (y_train == 1).sum()

class_weight = torch.tensor([num_invalid / num_valid], dtype=torch.float32).to(device)
criterion = nn.BCEWithLogitsLoss(pos_weight=class_weight)
optimizer = optim.Adam(model.parameters(), lr=0.001)

# =============================================================
# 6. TRAINING LOOP
# =============================================================
epochs = 25
history = {'loss': [], 'accuracy': []}

print("Training CNN and collecting epoch-by-epoch diagnostics...")

for epoch in range(epochs):
    model.train()
    epoch_loss = 0.0
    correct_train = 0
    
    for batch_images, batch_labels in train_loader:
        # Move data to GPU if available
        batch_images = batch_images.to(device)
        batch_labels = batch_labels.to(device)
        
        optimizer.zero_grad()
        predictions = model(batch_images)
        loss = criterion(predictions, batch_labels)
        loss.backward()
        optimizer.step()
        
        epoch_loss += loss.item() * batch_images.size(0)
        
        probs = torch.sigmoid(predictions)
        correct_train += ((probs >= 0.5).float() == batch_labels).sum().item()
        
    total_epoch_loss = epoch_loss / len(train_loader.dataset)
    total_epoch_acc = (correct_train / len(train_loader.dataset)) * 100
    history['loss'].append(total_epoch_loss)
    history['accuracy'].append(total_epoch_acc)
    
    if (epoch+1) % 5 == 0 or epoch == 0:
        print(f"Epoch {epoch+1:02d}/{epochs} | Loss: {total_epoch_loss:.4f} | Acc: {total_epoch_acc:.2f}%")

# =============================================================
# 7. PERFORMANCE EVALUATION
# =============================================================
model.eval()
test_probs_list = []
test_labels_list = []

with torch.no_grad():
    for batch_images, batch_labels in test_loader:
        batch_images = batch_images.to(device)
        test_logits = model(batch_images)
        probs = torch.sigmoid(test_logits).cpu().numpy()
        
        test_probs_list.extend(probs)
        test_labels_list.extend(batch_labels.numpy())

test_probabilities = np.array(test_probs_list).flatten()
y_test_eval = np.array(test_labels_list).flatten()
predicted_classes = (test_probabilities >= 0.5).astype(int)

precision = precision_score(y_test_eval, predicted_classes, zero_division=0)
recall = recall_score(y_test_eval, predicted_classes, zero_division=0)
f1 = f1_score(y_test_eval, predicted_classes, zero_division=0)

print("\n=============================================")
print("          CNN VISION MODEL STATISTICS        ")
print("=============================================")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")
print(f"F1-Score:  {f1:.4f}")
print("=============================================\n")
print(classification_report(y_test_eval, predicted_classes, target_names=['Invalid (0)', 'Valid (1)']))

# =============================================================
# 8. GENERATE DIAGNOSTIC CHARTS
# =============================================================
sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

axes[0].plot(range(1, epochs + 1), history['loss'], color='#d95f02', linewidth=2, label='Training Loss')
axes[0].set_ylabel('Loss', color='#d95f02')
ax2 = axes[0].twinx()
ax2.plot(range(1, epochs + 1), history['accuracy'], color='#1f77b4', linewidth=2, label='Training Accuracy')
ax2.set_ylabel('Accuracy (%)', color='#1f77b4')
axes[0].set_xlabel('Epochs')
axes[0].set_title('CNN Evolution vs. Epochs', fontweight='bold')

fpr, tpr, _ = roc_curve(y_test_eval, test_probabilities)
roc_auc = auc(fpr, tpr)

axes[1].plot(fpr, tpr, color='#2ca02c', linewidth=2, label=f'ROC Curve (AUC = {roc_auc:.4f})')
axes[1].plot([0, 1], [0, 1], color='gray', linestyle='--')
axes[1].set_title('ROC Curve (Visual Assessment)', fontweight='bold')
axes[1].legend(loc="lower right")

plt.tight_layout()
plt.savefig(os.path.join(scripts_dir, 'cnn_diagnostics.png'), dpi=150)
plt.close()

print("Vision training complete! Saved 'cnn_diagnostics.png'.")