# AI_balanced_threshold.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve, precision_recall_curve
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

# -----------------------------
# 1. Load the data
# -----------------------------
df = pd.read_csv("data.csv")
df = df[df['valid'].notnull()]  # only keep rows with valid defined
print("Class distribution:\n", df['valid'].value_counts())

# -----------------------------
# 2. Preprocess features
# -----------------------------
X = df.drop(columns=["valid", "camera_target", "seed", "camera_dist"])
y = df["valid"].astype(int)

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scale features
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# -----------------------------
# 3. Handle class imbalance with SMOTE
# -----------------------------
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
print("\nResampled class distribution:\n", pd.Series(y_train_res).value_counts())

# -----------------------------
# 4. Train XGBoost classifier
# -----------------------------
clf = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.1,
    use_label_encoder=False,
    eval_metric="logloss",
    random_state=42
)
clf.fit(X_train_res, y_train_res)

# -----------------------------
# 5. Predict probabilities
# -----------------------------
y_proba = clf.predict_proba(X_test)[:, 1]

# -----------------------------
# 6. Determine optimal threshold
# -----------------------------
precision, recall, thresholds = precision_recall_curve(y_test, y_proba)
f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
best_idx = np.argmax(f1_scores)
optimal_threshold = thresholds[best_idx]
print(f"\nOptimal probability threshold (F1-maximized): {optimal_threshold:.2f}")

# Predict using optimal threshold
y_pred = (y_proba >= optimal_threshold).astype(int)

# -----------------------------
# 7. Evaluate model
# -----------------------------
print("\nClassification Report:\n", classification_report(y_test, y_pred))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
roc_auc = roc_auc_score(y_test, y_proba)
print(f"ROC-AUC: {roc_auc:.4f}")

# -----------------------------
# 8. Plot ROC curve
# -----------------------------
fpr, tpr, _ = roc_curve(y_test, y_proba)
plt.figure()
plt.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.2f})', linewidth=2)
plt.plot([0, 1], [0, 1], 'k--', linewidth=1)
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve')
plt.legend(loc='lower right')
plt.grid(True)
plt.savefig("roc_curve.png")
plt.close()

# -----------------------------
# 9. Feature importance
# -----------------------------
importances = clf.feature_importances_
indices = np.argsort(importances)[::-1]

print("\nTop 10 features:")
for i in range(10):
    print(f"{X.columns[indices[i]]}: {importances[indices[i]]:.3f}")

plt.figure(figsize=(10,6))
plt.bar(range(10), importances[indices[:10]], align='center')
plt.xticks(range(10), [X.columns[i] for i in indices[:10]], rotation=45)
plt.title("Top 10 Feature Importances")
plt.tight_layout()
plt.savefig("feature_importance.png")
plt.close()

# -----------------------------
# 10. Plot Precision-Recall curve
# -----------------------------
from sklearn.metrics import average_precision_score

avg_precision = average_precision_score(y_test, y_proba)

plt.figure()
plt.plot(recall, precision, label=f'PR curve (AP = {avg_precision:.2f})', linewidth=2)
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')
plt.legend(loc='upper right')
plt.grid(True)
plt.savefig("precision_recall.png")
plt.close()