import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    confusion_matrix
)
import joblib
import os
import re


# ================================
#  Label Normalization
# ================================
def normalize_label(label):
    if not isinstance(label, str):
        return "Unknown"
    l = label.lower()
    if l.startswith("python"): return "PythonError"
    if l.startswith("ai"): return "AIError"
    if l.startswith("ml"): return "MLError"
    return "Unknown"


# ================================
#  Clean stack trace: Top 10 + Bottom 10
# ================================
def clean_stack_trace(trace):
    """
    Keep: first 10 lines + last 10 lines.
    If the trace is short, return full trace.
    """
    if not isinstance(trace, str):
        return ""

    lines = trace.strip().split("\n")
    if len(lines) <= 20:
        return trace.strip()

    top = lines[:10]
    bottom = lines[-10:]
    return "\n".join(top + ["...\n"] + bottom)


# ================================
#  Load Dataset
# ================================
df = pd.read_csv("data/error_dataset.csv").fillna("")
df["label"] = df["error_class"].apply(normalize_label)


# ============================================
# BALANCE CLASSES (DOWNSAMPLING)
# ============================================
print("\n===== BALANCING DATASET =====")

target_sizes = {
    "AIError": 200,
    "MLError": 200,
    "PythonError": 179
}

balanced_frames = []

for label, target_size in target_sizes.items():
    df_class = df[df["label"] == label]

    if len(df_class) >= target_size:
        df_sampled = df_class.sample(n=target_size, random_state=42)
    else:
        df_sampled = df_class.sample(n=target_size, random_state=42, replace=True)

    balanced_frames.append(df_sampled)

df = (
    pd.concat(balanced_frames)
    .sample(frac=1, random_state=42)
    .reset_index(drop=True)
)


# ============================================
# Clean & Combine Text
# ============================================
df["clean_trace"] = df["stack_trace"].apply(clean_stack_trace)
df["text"] = df["clean_trace"] + "\n" + df["code_snippets"]

print("\n===== CLASS DISTRIBUTION =====")
print(df["label"].value_counts())


# ================================
# EDA — Text Length
# ================================
df["len_trace"] = df["clean_trace"].str.len()
df["len_snip"] = df["code_snippets"].str.len()
df["len_text"] = df["text"].str.len()

print("\n===== TEXT LENGTH STATS =====")
print(df[["len_trace", "len_snip", "len_text"]].describe())


# ============================================================
# ADVANCED EDA (TEXT-ONLY — NO VISUALIZATION)
# ============================================================
print("\n===== ADVANCED EDA =====")


# ------------------------------------------------------------
# 1) Top TF-IDF keywords PER CLASS
# ------------------------------------------------------------
def top_tfidf_terms_per_class(vectorizer, X, y, top_n=20):
    feature_names = np.array(vectorizer.get_feature_names_out())
    classes = sorted(y.unique())

    for cls in classes:
        print(f"\n--- TOP {top_n} TERMS FOR {cls} ---")
        idx = np.where(y == cls)[0]
        class_matrix = X[idx]
        mean_tfidf = np.asarray(class_matrix.mean(axis=0)).ravel()
        top_indices = mean_tfidf.argsort()[-top_n:][::-1]

        for t in top_indices:
            print(f"{feature_names[t]:<30} {mean_tfidf[t]:.4f}")


# TF-IDF Vectorization
print("\nVectorizing text (TF-IDF)...")

vectorizer = TfidfVectorizer(
    max_features=8000,
    ngram_range=(1, 3),
    stop_words="english"
)

X = vectorizer.fit_transform(df["text"])
y = df["label"]

top_tfidf_terms_per_class(vectorizer, X, y, top_n=15)


# ------------------------------------------------------------
# 2) Exception type frequency
# ------------------------------------------------------------
print("\n===== EXCEPTION TYPES (Frequency) =====")

exception_counts = {}

for t in df["stack_trace"]:
    matches = re.findall(r"[A-Za-z]+Error", str(t))
    for m in matches:
        exception_counts[m] = exception_counts.get(m, 0) + 1

exception_counts = dict(
    sorted(exception_counts.items(), key=lambda x: x[1], reverse=True)
)

print("\nTop exception types:")
for err, count in list(exception_counts.items())[:15]:
    print(f"{err:<25} {count}")


# ------------------------------------------------------------
# 3) Duplicate detection
# ------------------------------------------------------------
print("\n===== DUPLICATE DETECTION =====")

dupe_count = df["text"].duplicated().sum()
trace_dupes = df["clean_trace"].duplicated().sum()

print(f"Duplicate full samples: {dupe_count}")
print(f"Duplicate traces:       {trace_dupes}")

print("\n===== ADVANCED EDA COMPLETE =====\n")


# ================================
# ML TRAINING
# ================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

print("\n===== TRAINING SVM =====")
svm_model = SVC(kernel="linear", probability=True)
svm_model.fit(X_train, y_train)
svm_pred = svm_model.predict(X_test)

print("\n=== SVM REPORT ===")
print(classification_report(y_test, svm_pred))
svm_acc = accuracy_score(y_test, svm_pred)
print("SVM Accuracy:", svm_acc)


print("\n===== TRAINING RANDOM FOREST =====")
rf_model = RandomForestClassifier(
    n_estimators=500,
    max_depth=None,
    random_state=7,
    n_jobs=-1
)
rf_model.fit(X_train, y_train)
rf_pred = rf_model.predict(X_test)

print("\n=== RANDOM FOREST REPORT ===")
print(classification_report(y_test, rf_pred))
rf_acc = accuracy_score(y_test, rf_pred)
print("Random Forest Accuracy:", rf_acc)


# ================================
# SAVE MODELS
# ================================
os.makedirs("model_output", exist_ok=True)
joblib.dump(svm_model, "model_output/svm_model.joblib")
joblib.dump(rf_model, "model_output/random_forest_model.joblib")
joblib.dump(vectorizer, "model_output/tfidf_vectorizer.joblib")

print("\nModels saved in model_output/")


print("\n===== FINAL COMPARISON =====")
print(f"SVM Accuracy:         {svm_acc:.4f}")
print(f"Random Forest Accuracy: {rf_acc:.4f}")

if svm_acc > rf_acc:
    print("\n🎯 BEST MODEL: SVM — performs better on your dataset.")
else:
    print("\n🎯 BEST MODEL: Random Forest — performs better on your dataset.")
