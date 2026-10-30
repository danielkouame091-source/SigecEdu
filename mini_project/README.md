# 🤖 Mini Project — Machine Learning & Deep Learning on SigecEdu
### Early warning of exam exclusion and detection of falsified attendance registers

**Author:** Kouassi Kouame Daniel · **UID:** 25MDA10119
**Programme:** MBA Data Science & AI · Chandigarh University, India

---

## 📌 1. Project overview and problem
SigecEdu is a back-end that records student attendance in Côte d'Ivoire and decides who may sit the exam (rule: at least **75 %** attendance, see `check_assiduite.py`). This mini project adds the **intelligence** on top of those records, with two questions:

| | Question | Type of learning |
|---|---|---|
| **A** | After 6 weeks of class, which students will fall **below 75 %** in the next 6 weeks, and so risk exclusion? (a warning early enough to act) | Supervised classification + deep learning |
| **B** | Which class registers look **falsified** (too perfect to be true)? (the anti-corruption side of SigecEdu) | Unsupervised anomaly detection |
| **C** | Do students form natural **profiles**? | Unsupervised clustering (PCA + K-Means) |

## 🎯 Objectives

- Predict, after 6 weeks, which students will fall below 75 % attendance.
- Compare classical machine learning with a neural network, against honest baselines.
- Detect falsified attendance registers without labels.
- Find natural student profiles (clustering).

## 🛠️ Technologies used

Python · Scikit-learn (Logistic Regression, KNN, Decision Tree, Random Forest, SVM, MLP neural network, Isolation Forest, PCA, K-Means) · Pandas and NumPy · Matplotlib.

## 2. Data — and its main limit
No real school data is available, so everything is **simulated** by `simulate_students()` in the script: 3,000 students, 12 weeks of weekly attendance, and 11 features known after week 6: attendance rate, last-2-weeks rate, trend, worst week, number of weeks below 60 %, distance to school, last year's rate, household poverty index, class size, teacher-absence rate, grade.
18 % of students get a random "life event" after week 6 (illness, work, family) that lowers their attendance: this part is **unpredictable by design**.
**Target:** attendance below 75 % in weeks 7–12 (about 30 % of students). Using the *future* weeks as target avoids leakage: the model never sees the weeks it must predict.
Because I wrote the generator, the models can only rediscover the relationships I put in. The results show that the **method works**, not what happens in real schools.

## 3. Method
- **Split:** 75 % training / 25 % test (stratified). The test set is used once, at the end.
- **Tuning:** 5-fold cross-validation on the training set only, metric = average precision (suited to a minority class). Scaling is inside a pipeline, so nothing leaks from the test set.
- **Two baselines:** (A) nobody is at risk; (B) **the rule a teacher would use**: "rate in weeks 1–6 below 75 %". Beating B is the real test.
- **Models:** Logistic Regression, KNN, Decision Tree, Random Forest, SVM (RBF), and a **neural network** (Multi-Layer Perceptron: 11 inputs → 32 ReLU → 16 ReLU → sigmoid, 929 weights, early stopping).
- **Metrics:** ROC-AUC, average precision, and precision / recall / F1 on the "at risk" class.

## 4. Results on the test set (750 students)
| Model | ROC-AUC | Avg. precision | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.750 | **0.666** | 0.515 | 0.622 | 0.563 |
| Neural network (MLP) | 0.730 | 0.648 | 0.658 | 0.432 | 0.522 |
| Random Forest | 0.729 | 0.647 | 0.535 | 0.586 | 0.559 |
| *Baseline B: simple rule* | *0.761* | *0.647* | *0.691* | *0.464* | *0.555* |
| KNN | 0.716 | 0.643 | 0.843 | 0.338 | 0.482 |
| SVM (RBF) | 0.737 | 0.608 | 0.613 | 0.500 | 0.551 |
| Decision Tree | 0.738 | 0.592 | 0.540 | 0.550 | 0.545 |
| *Baseline A: nobody at risk* | *0.500* | *0.296* | 0 | 0 | 0 |

Figures are in `results/` (data, KNN k, learning curve, ROC and PR curves, comparison, confusion matrix, feature importance, anomaly scores, PCA/K-Means).

**Anti-corruption detector (B).** 150 simulated registers, 12 of them falsified by me (near-perfect rates, almost no variation, many exact 100 % days). The Isolation Forest, trained **without labels**, reaches **ROC-AUC 0.96**; 50 % of its 12 most suspicious registers are really falsified.
**Profiles (C).** K-Means finds 2 groups (silhouette 0.32): one with 21 % at-risk students, the other 68 %, without ever seeing the target.

## 5. Discussion
1. **All models clearly beat "nobody at risk"** (average precision 0.59–0.67 against 0.30).
2. **The simple teacher rule is very hard to beat.** The best model (logistic regression) improves average precision by only 0.02 and has a *lower* ROC-AUC than the rule (0.750 vs 0.761). With a single dominant feature (`rate_first6`, by far the most important in permutation importance), a complex model has little to add. This is an honest and useful result: **machine learning is not always worth its cost**.
3. **Where ML helps.** The logistic regression finds more at-risk students (recall 0.62 against 0.46 for the rule), at the price of more false alarms. Choosing the decision threshold is a business choice: a school that wants to help every pupil at risk prefers high recall.
4. **The neural network does not win on this tabular data.** With 2,250 training rows and 11 inputs it performs like the classical models (average precision 0.648). Deep learning shines on images, text and very large datasets.
5. **KNN has the highest precision (0.84) but the lowest recall (0.34)**: it flags few students, but nearly all are correct.
6. **Ceiling.** 18 % of students change behaviour after week 6 for reasons no feature contains, so no model can reach perfect scores.
7. **Differences between models are small** (one split of 750 students). I do not claim any ranking among the top four; repeated cross-validation would be needed.

## 6. Limits and ethics
- Simulated data: no claim about real schools.
- A prediction is a **warning to help a student**, never a reason to exclude one. A real deployment needs human review and a fairness check (e.g. by region or poverty level), because errors would fall on the most vulnerable students.
- The falsified registers are injected by me, so 0.96 AUC is optimistic; real fraud is subtler.
- The neural network is a small scikit-learn model; a PyTorch version or an LSTM on the weekly time series is a natural extension.

## 7. How to run
```bash
cd ~/SigecEdu
pip install numpy pandas scikit-learn matplotlib
python3 mini_project/mini_project_ml_dl.py      # about 1 minute
```
Outputs: `mini_project/results/results.csv` and 9 PNG figures. Random seed: 42.

## 📁 8. Repository structure
```
mini_project/
├── README.md                  ← this report
├── mini_project_ml_dl.py      ← the whole experiment, one script
└── results/                   ← results.csv + figures 01…09
```
