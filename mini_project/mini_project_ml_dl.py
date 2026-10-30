"""
Mini project - Machine Learning & Deep Learning on SigecEdu
Early-warning of exam exclusion + detection of falsified attendance registers.

Author : Kouassi Kouame Daniel - UID 25MDA10119
Course : MBA Data Science & AI - Chandigarh University, India

Two problems, one script (about 1 minute):
  A. SUPERVISED + DEEP LEARNING : after 6 weeks of class, predict which students will fall below the 75 %
     attendance threshold in the NEXT 6 weeks (and so risk exclusion from the exam).
     Baseline, Logistic Regression, KNN, Decision Tree, Random Forest, SVM, Neural network (MLP).
  B. UNSUPERVISED : find attendance registers that look falsified (Isolation Forest) and group students
     into profiles (PCA + K-Means).

ALL DATA IS SIMULATED (no real school data is available). See README for the honest limits.
Run from the project root:   python3 mini_project/mini_project_ml_dl.py
Results go to:               mini_project/results/
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, ConfusionMatrixDisplay, f1_score, 
    precision_score, precision_recall_curve, recall_score, 
    roc_auc_score, roc_curve, silhouette_score
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore")
SEED = 42
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)
THRESHOLD = 75.0      # same exam-eligibility threshold as check_assiduite.py


def title(t: str) -> None:
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


# ── 1. Simulated school data ─────────────────────────────────────────────────
def simulate_students(n: int = 3000, seed: int = 7) -> pd.DataFrame:
    """12 weeks of weekly attendance (0-100 %) per student. Weeks 1-6 are observed, weeks 7-12 are the future."""
    rng = np.random.default_rng(seed)
    distance = rng.gamma(2.0, 2.0, n).clip(0.2, 25)               # km from home to school
    prior = np.clip(rng.normal(88, 9, n), 40, 100)                # last year's attendance rate (%)
    poverty = rng.beta(2, 3, n)                                   # 0 = comfortable, 1 = very poor household
    class_size = rng.integers(30, 90, n)
    teacher_abs = np.clip(rng.beta(1.5, 12, n), 0, 0.5)              # share of sessions the class teacher missed
    grade = rng.choice([6, 7, 8, 9], n)
    
    # latent "propensity to attend": higher = more regular
    z = (0.07 * (prior - 88) - 0.10 * distance - 1.6 * poverty - 2.5 * teacher_abs
         - 0.008 * (class_size - 55) + rng.normal(0, 0.7, n))
    base = 1 / (1 + np.exp(-(z + 3.6)))                           # base weekly attendance probability
    weeks = np.zeros((n, 12))
    shock = rng.random(n) < 0.18                                   # 18 % have a life event after week 6
    drop = np.where(shock, rng.uniform(0.15, 0.55, n), 0.0)          # (illness, work, family) -> attendance falls
    
    for w in range(12):
        p = base - (drop if w >= 6 else 0)
        sessions = 5
        weeks[:, w] = rng.binomial(sessions, np.clip(p, 0.02, 0.99)) / sessions * 100
        
    df = pd.DataFrame(weeks, columns=[f"w{i}" for i in range(1, 13)])
    obs = df[[f"w{i}" for i in range(1, 7)]]
    feats = pd.DataFrame({
        "rate_first6": obs.mean(axis=1),
        "rate_last2": obs[["w5", "w6"]].mean(axis=1),
        "trend": obs.apply(lambda r: np.polyfit(range(6), r.values, 1)[0], axis=1),
        "worst_week": obs.min(axis=1),
        "weeks_below_60": (obs < 60).sum(axis=1),
        "distance_km": distance, "prior_year_rate": prior, "poverty_index": poverty,
        "class_size": class_size, "teacher_absence": teacher_abs, "grade": grade
    })
    feats["future_rate"] = df[[f"w{i}" for i in range(7, 13)]].mean(axis=1)
    feats["at_risk"] = (feats["future_rate"] < THRESHOLD).astype(int)      # TARGET: below 75 % in weeks 7-12
    return feats


title("1. DATA")
data = simulate_students()
FEATURES = [c for c in data.columns if c not in ("future_rate", "at_risk")]
X, y = data[FEATURES], data["at_risk"]
print(f"{len(data)} simulated students, {len(FEATURES)} features known after 6 weeks")
print(f"Target = attendance below {THRESHOLD:.0f}% in weeks 7-12 -> {y.mean():.1%} of students are 'at risk'")
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=SEED, stratify=y)
print(f"Train = {len(X_tr)} | Test = {len(X_te)} (kept aside until the end)")

fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
ax[0].hist(data["rate_first6"], bins=40, color="#0A84FF")
ax[0].axvline(THRESHOLD, color="red", ls="--")
ax[0].set_title("Attendance rate, weeks 1-6 (red = 75 % threshold)")
ax[0].set_xlabel("%")
y.value_counts().sort_index().rename({0: "OK", 1: "at risk"}).plot.bar(ax=ax[1], color=["#30D158", "#FF453A"], rot=0)
ax[1].set_title("Target: attendance < 75 % in weeks 7-12")
ax[1].set_ylabel("students")
plt.tight_layout()
plt.savefig(OUT / "01_data.png", dpi=130)
plt.close()

# ── 2. Supervised learning ───────────────────────────────────────────────────
title("2. SUPERVISED LEARNING (5-fold cross-validation on the training set only)")
cv = StratifiedKFold(5, shuffle=True, random_state=SEED)


def pipe(model):
    return Pipeline([("scale", StandardScaler()), ("m", model)])


def tune(name, model, grid):
    gs = GridSearchCV(pipe(model), {f"m__{k}": v for k, v in grid.items()}, cv=cv,
                      scoring="average_precision", n_jobs=-1).fit(X_tr, y_tr)
    print(f"{name:<22} {({k[3:]: v for k, v in gs.best_params_.items()})}  CV average-precision = {gs.best_score_:.3f}")
    return gs.best_estimator_


m_log = tune("Logistic Regression", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED), {"C": [0.01, 0.1, 1, 10]})
m_knn = tune("KNN", KNeighborsClassifier(), {"n_neighbors": [5, 15, 31, 61, 101], "weights": ["uniform", "distance"]})
m_tree = tune("Decision Tree", DecisionTreeClassifier(class_weight="balanced", random_state=SEED), {"max_depth": [2, 3, 4, 6, 8]})
m_rf = tune("Random Forest", RandomForestClassifier(class_weight="balanced", random_state=SEED, n_jobs=-1),
            {"n_estimators": [200, 400], "max_depth": [4, 8, None], "min_samples_leaf": [1, 5, 20]})
m_svm = tune("SVM (RBF)", SVC(class_weight="balanced", probability=True, random_state=SEED), {"C": [0.5, 1, 5], "gamma": ["scale", 0.05]})

ks = [1, 5, 15, 31, 61, 101, 201]
kscores = [GridSearchCV(pipe(KNeighborsClassifier(n_neighbors=k)), {}, cv=cv, scoring="average_precision").fit(X_tr, y_tr).best_score_ for k in ks]
plt.figure(figsize=(6, 3.6))
plt.plot(ks, kscores, "o-", color="#0A84FF")
plt.xscale("log")
plt.xlabel("k (number of neighbours)")
plt.ylabel("CV average precision")
plt.title("KNN: choosing k")
plt.grid(alpha=.3)
plt.tight_layout()
plt.savefig(OUT / "02_knn_k.png", dpi=130)
plt.close()

# ── 3. Deep learning ─────────────────────────────────────────────────────────
title("3. DEEP LEARNING - Multi-Layer Perceptron")
m_mlp = pipe(MLPClassifier(hidden_layer_sizes=(32, 16), activation="relu", alpha=1e-2, max_iter=500, early_stopping=True,
                           validation_fraction=0.15, n_iter_no_change=25, random_state=SEED)).fit(X_tr, y_tr)
net = m_mlp.named_steps["m"]
n_weights = sum(w.size for w in net.coefs_) + sum(b.size for b in net.intercepts_)
print(f"Architecture: {len(FEATURES)} inputs -> Dense(32, ReLU) -> Dense(16, ReLU) -> Sigmoid(1) | {n_weights} weights | {net.n_iter_} epochs")
plt.figure(figsize=(6.5, 3.8))
plt.plot(net.loss_curve_, label="training loss", color="#0A84FF")
plt.plot(1 - np.array(net.validation_scores_), label="validation error (1 - accuracy)", color="#FF9F0A")
plt.xlabel("epoch")
plt.title("Neural network learning curves")
plt.legend()
plt.grid(alpha=.3)
plt.tight_layout()
plt.savefig(OUT / "03_mlp_learning_curve.png", dpi=130)
plt.close()

# ── 4. Comparison on the unseen test set ─────────────────────────────────────
title("4. FINAL COMPARISON ON THE UNSEEN TEST SET")
models = {
    "Logistic Regression": m_log, "KNN": m_knn, "Decision Tree": m_tree, 
    "Random Forest": m_rf, "SVM (RBF)": m_svm, "Neural network (MLP)": m_mlp
}
scores, preds = {}, {}

scores["Baseline A: nobody at risk"] = np.zeros(len(y_te))
scores["Baseline B: simple rule (rate < 75 %)"] = (100 - X_te["rate_first6"].values) / 100
preds["Baseline A: nobody at risk"] = np.zeros(len(y_te), dtype=int)
preds["Baseline B: simple rule (rate < 75 %)"] = (X_te["rate_first6"].values < THRESHOLD).astype(int)

for name, m in models.items():
    scores[name] = m.predict_proba(X_te)[:, 1]
    preds[name] = (scores[name] >= 0.5).astype(int)

rows = []
for name in scores:
    rows.append({
        "model": name, 
        "ROC_AUC": roc_auc_score(y_te, scores[name]),
        "avg_precision": average_precision_score(y_te, scores[name]),
        "precision": precision_score(y_te, preds[name], zero_division=0),
        "recall": recall_score(y_te, preds[name], zero_division=0),
        "F1": f1_score(y_te, preds[name], zero_division=0)
    })
res = pd.DataFrame(rows).set_index("model").round(3).sort_values("avg_precision", ascending=False)
print(res.to_string())
res.to_csv(OUT / "results.csv")

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for name in scores:
    if "A:" in name:
        continue
    fpr, tpr, _ = roc_curve(y_te, scores[name])
    ax[0].plot(fpr, tpr, label=name, lw=1.6)
    pr, rc, _ = precision_recall_curve(y_te, scores[name])
    ax[1].plot(rc, pr, label=name, lw=1.6)
ax[0].plot([0, 1], [0, 1], "k:")
ax[0].set_title("ROC curves")
ax[0].set_xlabel("false positive rate")
ax[0].set_ylabel("true positive rate")
ax[1].set_title("Precision-recall curves")
ax[1].set_xlabel("recall")
ax[1].set_ylabel("precision")
ax[1].legend(fontsize=7)
plt.tight_layout()
plt.savefig(OUT / "04_roc_pr.png", dpi=130)
plt.close()

plot_res = res.drop(index="Baseline A: nobody at risk")[["ROC_AUC", "avg_precision", "F1"]]
ax = plot_res.plot.barh(figsize=(8.5, 4.6), color=["#8E8E93", "#0A84FF", "#FF9F0A"])
ax.invert_yaxis()
ax.set_title("Models compared on the test set")
ax.grid(axis="x", alpha=.3)
ax.set_xlim(0, 1)
plt.tight_layout()
plt.savefig(OUT / "05_comparison.png", dpi=130)
plt.close()

best = res.drop(index=[i for i in res.index if i.startswith("Baseline")]).index[0]
fig, ax = plt.subplots(figsize=(4.4, 4))
ConfusionMatrixDisplay.from_predictions(y_te, preds[best], display_labels=["OK", "at risk"], ax=ax, cmap="Blues", colorbar=False)
ax.set_title(f"Confusion matrix - {best}")
plt.tight_layout()
plt.savefig(OUT / "06_confusion_matrix.png", dpi=130)
plt.close()

pi = permutation_importance(models[best] if best in models else m_rf, X_te, y_te, scoring="average_precision",
                            n_repeats=10, random_state=SEED, n_jobs=-1)
imp = pd.Series(pi.importances_mean, index=FEATURES).sort_values()
print("\nMost useful features for", best, ":", imp.sort_values(ascending=False).head(4).round(3).to_dict())
plt.figure(figsize=(6.5, 4))
imp.plot.barh(color="#0A84FF")
plt.title(f"Permutation importance - {best}")
plt.xlabel("drop in average precision when the feature is shuffled")
plt.tight_layout()
plt.savefig(OUT / "07_feature_importance.png", dpi=130)
plt.close()

# ── 5. Unsupervised A: falsified registers ───────────────────────────────────
title("5. UNSUPERVISED - detecting falsified attendance registers (Isolation Forest)")
rng = np.random.default_rng(3)
n_classes, n_fake = 150, 12
reg = []
for i in range(n_classes):
    fake = i < n_fake
    if fake:        # copied / invented register: almost perfect, almost no variation, many exact 100 % days
        daily = np.clip(rng.normal(98.5, 1.0, 60), 90, 100).round()
    else:           # honest register: lower, noisy, includes bad days
        daily = np.clip(rng.normal(rng.uniform(70, 92), rng.uniform(6, 14), 60), 20, 100).round()
    reg.append({
        "mean_rate": daily.mean(), "std_rate": daily.std(), "share_100": (daily == 100).mean(),
        "min_day": daily.min(), "share_round5": (daily % 5 == 0).mean(), "is_fake": int(fake)
    })
reg = pd.DataFrame(reg)
Z = StandardScaler().fit_transform(reg.drop(columns="is_fake"))
iso = IsolationForest(n_estimators=300, contamination=n_fake / n_classes, random_state=SEED).fit(Z)
anom = -iso.score_samples(Z)
print(f"{n_classes} simulated class registers, {n_fake} falsified (injected by me). No label used to train the detector.")
print(f"ROC-AUC = {roc_auc_score(reg['is_fake'], anom):.3f} | precision in the top {n_fake} = {reg['is_fake'].values[np.argsort(-anom)[:n_fake]].mean():.2f}")
plt.figure(figsize=(6.5, 3.8))
plt.hist(anom[reg.is_fake == 0], bins=25, alpha=.7, label="honest registers", color="#30D158")
plt.hist(anom[reg.is_fake == 1], bins=12, alpha=.8, label="falsified registers", color="#FF453A")
plt.xlabel("anomaly score (higher = more suspicious)")
plt.title("Isolation Forest")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "08_anomaly.png", dpi=130)
plt.close()

# ── 6. Unsupervised B: student profiles ──────────────────────────────────────
title("6. UNSUPERVISED - student profiles (PCA + K-Means, target not used)")
Zs = StandardScaler().fit_transform(X)
best_k, best_s = 2, -1
for k in range(2, 7):
    s = silhouette_score(Zs, KMeans(k, n_init=10, random_state=SEED).fit_predict(Zs), sample_size=1500, random_state=SEED)
    print(f"K-Means k={k}: silhouette = {s:.3f}")
    if s > best_s:
        best_k, best_s = k, s
groups = KMeans(best_k, n_init=10, random_state=SEED).fit_predict(Zs)
share = pd.Series(y.values).groupby(groups).mean().round(3)
print(f"-> best k = {best_k}; share of at-risk students per group: {share.to_dict()}")
P = PCA(2, random_state=SEED).fit_transform(Zs)
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].scatter(P[:, 0], P[:, 1], c=groups, s=5, cmap="tab10")
ax[0].set_title(f"K-Means groups (k={best_k}) on 2 PCA axes")
ax[1].scatter(P[:, 0], P[:, 1], c=np.where(y == 1, "#FF453A", "#30D158"), s=5)
ax[1].set_title("Same students coloured by true risk")
plt.tight_layout()
plt.savefig(OUT / "09_pca_kmeans.png", dpi=130)
plt.close()

title("DONE")
b = res.loc["Baseline B: simple rule (rate < 75 %)"]
print(f"Best model: {best} (avg precision {res.loc[best, 'avg_precision']:.3f}, ROC-AUC {res.loc[best, 'ROC_AUC']:.3f})")
print(f"Simple teacher rule: avg precision {b['avg_precision']:.3f}, ROC-AUC {b['ROC_AUC']:.3f}")
print(f"Figures and tables saved in {OUT}")
