#Multimodal
import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_curve, auc
import matplotlib.pyplot as plt
import seaborn as sns

# Set seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Auto-detect GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Training Multimodal Fusion AI on device: {device}")

# =============================================================
# 1. SETUP PATHS AND PREPARE DATA (Combining Image & Tabular Rules)
# =============================================================
scripts_dir = r"C:/Users/FABLAB/Documents/BlenderScripts"
CSV_PATH = os.path.join(scripts_dir, "data.csv")
IMG_DIR = os.path.join(scripts_dir, "low_res_renders")

# Read CSV and drop missing validations
df = pd.read_csv(CSV_PATH)
df = df.dropna(subset=['valid']).reset_index(drop=True)
df['valid'] = df['valid'].astype(int)

# Drop unused/string columns (like camera_target) but KEEP 'seed' for now to find images
df = df.drop(columns=['camera_target'], errors='ignore')
df = df.loc[:, df.nunique() > 1] # Drop zero-variance columns

# Verify image files actually exist before we build the dataset
valid_rows = []
for idx, row in df.iterrows():
    seed = int(row['seed'])
    img_path = os.path.join(IMG_DIR, f"{seed}.png")
    if os.path.exists(img_path):
        valid_rows.append(row)

# Rebuild dataframe with only valid rows and reset index (critical for the DataLoader)
df = pd.DataFrame(valid_rows).reset_index(drop=True)
print(f"Found {len(df)} rows with perfectly matching tabular data and image files.")

# Identify the Tabular Feature Columns (Everything except 'valid' and 'seed')
feature_cols = [col for col in df.columns if col not in ['valid', 'seed']]
print(f"Detected {len(feature_cols)} tabular parameters for the math network: {feature_cols}")

# Train / Test Split
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['valid'])

# Standardize the Tabular Features (Fit on train, transform on test)
scaler = StandardScaler()
train_df.loc[:, feature_cols] = scaler.fit_transform(train_df[feature_cols])
test_df.loc[:, feature_cols] = scaler.transform(test_df[feature_cols])

# Reset indices so the Custom Dataset can iterate cleanly from 0
train_df = train_df.reset_index(drop=True)
test_df = test_df.reset_index(drop=True)

# =============================================================
# 2. IMAGE TRANSFORMS FOR PRE-TRAINED RESNET
# =============================================================
resnet_mean = [0.485, 0.456, 0.406]
resnet_std = [0.229, 0.224, 0.225]

train_transforms = transforms.Compose([
    transforms.Resize((224, 224)), 
    transforms.RandomHorizontalFlip(p=0.5), 
    transforms.RandomRotation(degrees=15),
    transforms.ToTensor(),
    transforms.Normalize(mean=resnet_mean, std=resnet_std)
])

test_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=resnet_mean, std=resnet_std)
])

# =============================================================
# 3. MULTIMODAL CUSTOM DATASET
# =============================================================
class MultimodalDataset(Dataset):
    def __init__(self, dataframe, feature_cols, img_dir, transform=None):
        self.dataframe = dataframe
        self.feature_cols = feature_cols
        self.img_dir = img_dir
        self.transform = transform

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        # 1. Get Label
        label = self.dataframe.loc[idx, 'valid']
        
        # 2. Get Tabular Math Features (from the scaled dataframe)
        tabular_data = self.dataframe.loc[idx, self.feature_cols].values.astype(np.float32)
        
        # 3. Get Image Data
        seed = int(self.dataframe.loc[idx, 'seed'])
        img_path = os.path.join(self.img_dir, f"{seed}.png")
        image = Image.open(img_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
            
        return image, torch.tensor(tabular_data), torch.tensor(label, dtype=torch.float32).unsqueeze(0)

train_loader = DataLoader(MultimodalDataset(train_df, feature_cols, IMG_DIR, train_transforms), batch_size=32, shuffle=True)
test_loader = DataLoader(MultimodalDataset(test_df, feature_cols, IMG_DIR, test_transforms), batch_size=32, shuffle=False)

# =============================================================
# 4. MULTIMODAL LATE-FUSION ARCHITECTURE (BOTTLENECK VERSION)
# =============================================================
class FusionNet(nn.Module):
    def __init__(self, tabular_input_dim):
        super(FusionNet, self).__init__()
        
        # --- TRACK A: VISION (Pre-trained ResNet-18) ---
        self.vision = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        num_ftrs = self.vision.fc.in_features
        # Compress the 512 vision features down to exactly 32!
        self.vision.fc = nn.Sequential(
            nn.Linear(num_ftrs, 32),
            nn.ReLU()
        )
        
        # --- TRACK B: TABULAR MATH ---
        self.tabular = nn.Sequential(
            nn.Linear(tabular_input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        
        # --- TRACK C: THE FUSION BODY (Perfectly Balanced) ---
        # 32 Vision + 32 Math = 64 Total Features
        self.fusion = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.5), # Lowered dropout so we don't accidentally blindfold the math track
            nn.Linear(32, 1) # Final single output
        )

    def forward(self, img_x, tab_x):
        vision_features = self.vision(img_x)   
        math_features = self.tabular(tab_x)    
        
        combined_features = torch.cat((vision_features, math_features), dim=1) 
        output = self.fusion(combined_features)
        return output

model = FusionNet(tabular_input_dim=len(feature_cols)).to(device)

# =============================================================
# 5. LOSS AND OPTIMIZER
# =============================================================
y_train = train_df['valid'].values
num_invalid = (y_train == 0).sum()
num_valid = (y_train == 1).sum()

class_weight = torch.tensor([num_invalid / num_valid], dtype=torch.float32).to(device)
criterion = nn.BCEWithLogitsLoss(pos_weight=class_weight)

# We use Differential Learning Rates!
# ResNet gets a slow rate (0.0001) because it's already smart.
# Tabular and Fusion get a fast rate (0.005) because they are starting from scratch.
optimizer = optim.Adam([
    {'params': model.vision.parameters(), 'lr': 0.0001},
    {'params': model.tabular.parameters(), 'lr': 0.005},
    {'params': model.fusion.parameters(), 'lr': 0.005}
])

# =============================================================
# 6. TRAINING LOOP
# =============================================================
epochs = 20
history = {'loss': [], 'accuracy': []}

print("\nBeginning Multimodal Fusion Training...")

for epoch in range(epochs):
    model.train()
    epoch_loss = 0.0
    correct_train = 0
    
    for batch_imgs, batch_tabs, batch_labels in train_loader:
        # Move everything to GPU/CPU
        batch_imgs = batch_imgs.to(device)
        batch_tabs = batch_tabs.to(device)
        batch_labels = batch_labels.to(device)
        
        optimizer.zero_grad()
        
        # Pass BOTH image and tabular math into the model
        predictions = model(batch_imgs, batch_tabs)
        
        loss = criterion(predictions, batch_labels)
        loss.backward()
        optimizer.step()
        
        epoch_loss += loss.item() * batch_imgs.size(0)
        probs = torch.sigmoid(predictions)
        correct_train += ((probs >= 0.5).float() == batch_labels).sum().item()
        
    total_epoch_loss = epoch_loss / len(train_loader.dataset)
    total_epoch_acc = (correct_train / len(train_loader.dataset)) * 100
    history['loss'].append(total_epoch_loss)
    history['accuracy'].append(total_epoch_acc)
    
    print(f"Epoch {epoch+1:02d}/{epochs} | Loss: {total_epoch_loss:.4f} | Acc: {total_epoch_acc:.2f}%")

# =============================================================
# 7. EVALUATION
# =============================================================
model.eval()
test_probs_list = []
test_labels_list = []

with torch.no_grad():
    for batch_imgs, batch_tabs, batch_labels in test_loader:
        batch_imgs = batch_imgs.to(device)
        batch_tabs = batch_tabs.to(device)
        
        # Pass BOTH inputs during evaluation
        test_logits = model(batch_imgs, batch_tabs)
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
print("      MULTIMODAL FUSION STATISTICS           ")
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
axes[0].set_title('Fusion Evolution vs. Epochs', fontweight='bold')

fpr, tpr, _ = roc_curve(y_test_eval, test_probabilities)
roc_auc = auc(fpr, tpr)

axes[1].plot(fpr, tpr, color='#2ca02c', linewidth=2, label=f'ROC Curve (AUC = {roc_auc:.4f})')
axes[1].plot([0, 1], [0, 1], color='gray', linestyle='--')
axes[1].set_title('ROC Curve (Multimodal Assessment)', fontweight='bold')
axes[1].legend(loc="lower right")

plt.tight_layout()
plt.savefig(os.path.join(scripts_dir, 'multimodal_diagnostics.png'), dpi=150)
plt.close()

print("Multimodal training complete! Saved 'multimodal_diagnostics.png'.")

# =============================================================
# 9. SAVE THE TRAINED MODEL
# =============================================================
model_save_path = os.path.join(scripts_dir, 'multimodal_ai_bottleneck.pth')
torch.save(model.state_dict(), model_save_path)
print(f"Successfully saved trained AI model to: {model_save_path}")