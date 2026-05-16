# ResNet
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
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_curve, auc
import matplotlib.pyplot as plt
import seaborn as sns

# Set seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Auto-detect GPU for massive speedups
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Training ResNet Vision-Only AI on device: {device}")

# =============================================================
# 1. SETUP PATHS AND PREPARE DATA
# =============================================================
scripts_dir = r"C:/Users/FABLAB/Documents/BlenderScripts"
CSV_PATH = os.path.join(scripts_dir, "data.csv")
IMG_DIR = os.path.join(scripts_dir, "low_res_renders")

# Read CSV and filter missing values
df = pd.read_csv(CSV_PATH)
df = df.dropna(subset=['valid']).reset_index(drop=True)
df['valid'] = df['valid'].astype(int)

# Verify image files actually exist
valid_rows = []
for idx, row in df.iterrows():
    seed = int(row['seed'])
    img_path = os.path.join(IMG_DIR, f"{seed}.png")
    if os.path.exists(img_path):
        valid_rows.append(row)

df = pd.DataFrame(valid_rows).reset_index(drop=True)
print(f"Found {len(df)} rows with perfectly matching image files.")

# Split data into Train and Test
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['valid'])

# =============================================================
# 2. IMAGE TRANSFORMS FOR PRE-TRAINED RESNET
# =============================================================
# ResNet expects images to be normalized with exactly these values
resnet_mean = [0.485, 0.456, 0.406]
resnet_std = [0.229, 0.224, 0.225]

train_transforms = transforms.Compose([
    transforms.Resize((224, 224)), # ResNet's native resolution
    transforms.RandomHorizontalFlip(p=0.5), # Safe augmentation
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
# 3. VISION-ONLY DATASET
# =============================================================
class ImageOnlyDataset(Dataset):
    def __init__(self, dataframe, img_dir, transform=None):
        self.dataframe = dataframe.reset_index(drop=True)
        self.img_dir = img_dir
        self.transform = transform

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        label = self.dataframe.loc[idx, 'valid']
        seed = int(self.dataframe.loc[idx, 'seed'])
        img_path = os.path.join(self.img_dir, f"{seed}.png")
        
        image = Image.open(img_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
            
        return image, torch.tensor(label, dtype=torch.float32).unsqueeze(0)

train_loader = DataLoader(ImageOnlyDataset(train_df, IMG_DIR, train_transforms), batch_size=32, shuffle=True)
test_loader = DataLoader(ImageOnlyDataset(test_df, IMG_DIR, test_transforms), batch_size=32, shuffle=False)

# =============================================================
# 4. RESNET-18 ARCHITECTURE MODIFICATION
# =============================================================
# 1. Download pre-trained brain
model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)

# 2. Find out how many features the final layer outputs (it's 512 for ResNet18)
num_ftrs = model.fc.in_features

# 3. Replace the 1,000-class output with a single output (Valid/Invalid)
# We add a Dropout layer here to help prevent overfitting since you only have 17 valid images!
model.fc = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(num_ftrs, 1)
)

model = model.to(device)

# =============================================================
# 5. LOSS AND OPTIMIZER
# =============================================================
y_train = train_df['valid'].values
num_invalid = (y_train == 0).sum()
num_valid = (y_train == 1).sum()

class_weight = torch.tensor([num_invalid / num_valid], dtype=torch.float32).to(device)
criterion = nn.BCEWithLogitsLoss(pos_weight=class_weight)

# We use a very small learning rate (0.0001 instead of 0.001) 
# because ResNet already knows how to see. We just want to fine-tune it.
optimizer = optim.Adam(model.parameters(), lr=0.0001)

# =============================================================
# 6. TRAINING LOOP
# =============================================================
epochs = 15 # Because it's pre-trained, it learns much faster!
history = {'loss': [], 'accuracy': []}

print("\nBeginning ResNet Vision-Only Training...")

for epoch in range(epochs):
    model.train()
    epoch_loss = 0.0
    correct_train = 0
    
    for batch_imgs, batch_labels in train_loader:
        batch_imgs = batch_imgs.to(device)
        batch_labels = batch_labels.to(device)
        
        optimizer.zero_grad()
        predictions = model(batch_imgs)
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
    for batch_imgs, batch_labels in test_loader:
        batch_imgs = batch_imgs.to(device)
        
        test_logits = model(batch_imgs)
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
print("      RESNET VISION-ONLY STATISTICS          ")
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
axes[0].set_title('ResNet Evolution vs. Epochs', fontweight='bold')

fpr, tpr, _ = roc_curve(y_test_eval, test_probabilities)
roc_auc = auc(fpr, tpr)

axes[1].plot(fpr, tpr, color='#2ca02c', linewidth=2, label=f'ROC Curve (AUC = {roc_auc:.4f})')
axes[1].plot([0, 1], [0, 1], color='gray', linestyle='--')
axes[1].set_title('ROC Curve (ResNet Vision Assessment)', fontweight='bold')
axes[1].legend(loc="lower right")

plt.tight_layout()
plt.savefig(os.path.join(scripts_dir, 'resnet_diagnostics.png'), dpi=150)
plt.close()

print("ResNet training complete! Saved 'resnet_diagnostics.png'.")

# =============================================================
# 9. SAVE THE TRAINED MODEL
# =============================================================
model_save_path = os.path.join(scripts_dir, 'ResNet18_model.pth')
torch.save(model.state_dict(), model_save_path)
print(f"Successfully saved trained AI model to: {model_save_path}")