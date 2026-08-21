# RecoverAI - Phase 2.5: Decoupled Revenue Risk Engine & Evaluation Benchmark Documentation

## 1. Executive Summary

Phase 2.5 performs a rigorous correction of the **RecoverAI** Revenue Risk Engine. It decouples ground-truth recovery potential from risk prediction, replaces rule-mirroring with an independent multi-factor probabilistic scoring model, and introduces a formal **Train (60%) / Validation (20%) / Test (20%)** dataset split. 

Furthermore, evaluation is expanded beyond binary threshold metrics (Precision, Recall, F1) to include continuous probabilistic and calibration metrics: **ROC-AUC, PR-AUC, Brier Score, and Expected Calibration Error (ECE)**.

All dataset records are versioned (`benchmark_version: "v2"`) and persisted directly into Supabase PostgreSQL tables (`transactions`, `payment_attempts`, `revenue_risk_events`, `recovery_actions`, `evaluation_runs`, `customers`, and `merchants`).

---

## 2. Phase 2.5 Architecture

```
+-----------------------------------------------------------------------+
|                Deterministic Dataset Generator (v2)                   |
|       (Seed = 42, Count = 10,000 | 60% Train / 20% Val / 20% Test)    |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                   Multi-Factor Ground Truth Engine                    |
|   (Realistic recoverability score S_gt derived from business factors) |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                 Independent Revenue Risk Engine                       |
|  (Weighted scoring for Risk Score R_score & Recovery Probability P_rec) |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|               Continuous & Binary Evaluation Pipeline                 |
|   (F1: 0.9529 | ROC-AUC: 0.9984 | Brier: 0.0355 | ECE: 0.0696)      |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                     Supabase Schema Seeder                            |
| (Persists records via SECURITY DEFINER seed_benchmark_data RPC)       |
+-----------------------------------------------------------------------+
```

---

## 3. Synthetic Dataset & Split Specifications (v2)

- **Dataset Size:** 10,000 payment transaction records.
- **Random Seed:** `42` (Fixed for 100% byte-for-byte reproducibility).
- **Benchmark Version:** `v2`
- **Merchant ID:** `00000000-0000-0000-0000-000000000001` (Acme Payments Benchmark Merchant).
- **Dataset Splits:**
  - `train`: 6,000 records (60%)
  - `validation`: 2,000 records (20%)
  - `test`: 2,000 records (20%)
- **Status Distribution:**
  - `successful`: ~73% (7,298 events)
  - `failed`: ~19% (1,927 events)
  - `abandoned`: ~5% (475 events)
  - `disputed`: ~3% (300 events)

---

## 4. Ground-Truth Rule Engine (Multi-Factor Scoring)

Ground-truth labeling calculates a continuous ground-truth recoverability score $S_{gt} \in [0.0, 100.0]$ and probability $P_{gt} = S_{gt} / 100.0$ based on underlying transaction features.

$$S_{gt} = \text{BaseScore} + \Delta_{\text{SuccessRate}} + \Delta_{\text{LTV}} + \Delta_{\text{Retries}} + \Delta_{\text{Subscription}} + \Delta_{\text{Recency}} + \Delta_{\text{Amount}}$$

- **Base Score:** `network_timeout`/`gateway_error` (75), `insufficient_funds`/`authentication_failed` (60), `expired_card` (55), `abandoned` (45), `do_not_honor` (35), `disputed` (25).
- **Hard Declines (`stolen_card`, `invalid_card`):** $S_{gt} = 0.0, P_{gt} = 0.0$, `is_recovery_opportunity = False`.
- **Successful Transactions:** $S_{gt} = 0.0, P_{gt} = 0.0$, `is_recovery_opportunity = False`.
- **Opportunity Decision Threshold:** $P_{gt} \ge 0.40 \implies \text{is\_recovery\_opportunity} = \text{True}$.

---

## 5. Independent Revenue Risk Engine Formula

The Risk Engine operates **without accessing ground-truth labels** or duplicating ground-truth calculation rules. It computes two distinct outputs:

### A. Risk Score ($R_{\text{score}} \in [0.0, 100.0]$)
Measures failure severity and transaction structural risk:
$$\text{Risk Score} = \min(100.0, \max(0.0, \text{Severity} + \text{RetryVel} + \text{HistPenalty} + \text{ExpiryRisk} + \text{Inactivity}))$$

### B. Recovery Probability ($P_{\text{rec}} \in [0.0, 1.0]$)
Estimates recovery likelihood using observable features:
$$P_{\text{rec}} = \min(1.0, \max(0.0, P_{\text{base}} + A_{\text{customer}} + A_{\text{friction}}))$$

- **Decision Threshold:** $P_{\text{rec}} \ge 0.40 \implies \mathbf{is\_opportunity = True}$.
- **Expected Recovery Amount:** $\text{revenue\_at\_risk} \times P_{\text{rec}}$.

---

## 6. Evaluation Framework & Benchmark Results (v2)

### Overall Benchmark Metrics (Seed=42, 10,000 records):

| Metric Category | Metric | Benchmark Value |
| :--- | :--- | :--- |
| **Dataset Overview** | Total Records | 10,000 |
| | Seed / Version | 42 / `v2` |
| **Confusion Matrix** | True Positives (TP) | 2,115 |
| | False Positives (FP) | 86 |
| | True Negatives (TN) | 7,676 |
| | False Negatives (FN) | 123 |
| **Binary Classification** | **Precision** | **0.9609 (96.09%)** |
| | **Recall** | **0.9450 (94.50%)** |
| | **F1 Score** | **0.9529 (95.29%)** |
| | False Positive Rate (FPR) | 1.11% |
| | False Negative Rate (FNR) | 5.50% |
| **Continuous & Calibration** | **ROC-AUC** | **0.9984** |
| | **PR-AUC** | **0.9945** |
| | **Brier Score** | **0.0355** |
| | **Expected Calibration Error (ECE)** | **0.0696 (6.96%)** |
| **Financial Metrics** | Total Revenue Processed | INR 24,912,407.05 |
| | Total Revenue at Risk | INR 6,675,362.54 |
| | Predicted Recoverable Revenue | INR 3,882,564.18 |
| | Ground-Truth Recoverable Revenue | INR 3,912,499.67 |
| | Estimated Recovery Value | INR 3,497,001.84 |

### Dataset Split Performance Comparison:

| Split Name | Records | F1-Score | Precision | Recall | ROC-AUC | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Train Split** | 6,000 (60%) | 0.9490 | 0.9561 | 0.9421 | 0.9982 | 0.0363 |
| **Validation Split** | 2,000 (20%) | 0.9545 | 0.9591 | 0.9500 | 0.9985 | 0.0333 |
| **Test Split** | 2,000 (20%) | **0.9631** | **0.9773** | **0.9493** | **0.9991** | **0.0350** |

---

## 7. Error Analysis: Top False Positives & False Negatives

### False Positives (Model predicted opportunity, Ground Truth said NO):
Occurs primarily on borderline transactions where customer history is strong (high previous success rate) but high retry counts or failure severity lower ground-truth probability just below 0.40 (e.g. GT Prob = 0.38 - 0.39 vs. Model Prob = 0.41 - 0.51).

### False Negatives (Ground Truth said YES, Model predicted NO):
Occurs primarily on early-stage chargeback notices and `do_not_honor` declines where high customer LTV pushes ground truth slightly above 0.40 (e.g. GT Prob = 0.40 - 0.57), while conservative risk engine severity weights keep model probability around 0.26 - 0.36.

---

## 8. API Endpoints Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/evaluation/generate-dataset` | `POST` | Generates 10k dataset (v2), evaluates risk, & seeds Supabase |
| `/api/v1/evaluation/run` | `POST` | Runs evaluation pipeline on DB transactions (supports `split` filter) |
| `/api/v1/evaluation/latest` | `GET` | Retrieves most recent evaluation run from database |
| `/api/v1/evaluation/metrics` | `GET` | Retrieves evaluation metrics JSON |
| `/api/v1/revenue-risk/summary` | `GET` | Summary of revenue risk events, severity, & amounts |
| `/api/v1/recovery-opportunities/summary` | `GET` | Summary of recovery actions & expected values |

---

## 9. Verification & Execution

### Run Automated Unit Test Suite (10 Decoupled Tests):
```bash
python C:\Users\acer\Desktop\RecoverAI\backend\tests\run_tests.py
```

### Run Full Benchmark Generation & Supabase Seeding (v2.1):
```bash
python C:\Users\acer\Desktop\RecoverAI\backend\scripts\run_phase2_generation.py
```

---

## 10. Benchmark Correction: Customer-Disjoint Split (v2.1)

### A. Context & Audit Discovery
During the Phase 2 final benchmark sanity audit, a customer-level split contamination was discovered in the `v2` benchmark. While transaction IDs and feature tuples were 100% unique across splits, the initial splitting logic partitioned data at the *transaction* level (`i < train_cutoff`). Because customers could have multiple transaction attempts over time, **1,191 customers appeared in both Train and Test splits**.

### B. Corrective Implementation (`v2.1`)
To ensure complete independence and prevent customer-level leakage:
1. The synthetic generator was updated so that dataset partitioning occurs by **`customer_id`** (`customer_split_map`), assigning 60% of unique customers to `train`, 20% to `validation`, and 20% to `test`.
2. All customer split intersections were verified to be strictly empty ($S_{\text{train}} \cap S_{\text{val}} = \emptyset$, $S_{\text{train}} \cap S_{\text{test}} = \emptyset$, $S_{\text{val}} \cap S_{\text{test}} = \emptyset$).
3. Benchmark version was updated to **`v2.1`**.

### C. Comparison: Old Transaction-Level (`v2`) vs. Corrected Customer-Disjoint (`v2.1`)

| Metric | v2 (Transaction-Level Split) | v2.1 (Customer-Disjoint Split) | Status / Notes |
| :--- | :---: | :---: | :--- |
| **Train Set** | 6,000 recs (1,914 custs) | 5,989 recs (1,190 custs) | Split by customer |
| **Validation Set** | 2,000 recs (1,265 custs) | 2,024 recs (399 custs) | Split by customer |
| **Test Set** | 2,000 recs (1,250 custs) | 1,987 recs (398 custs) | Split by customer |
| **Customer Split Leakage** | 1,191 shared customers | **0 shared customers** | **Strictly Isolated (0 Overlap)** |
| **Transaction ID Overlap** | 0 shared transactions | **0 shared transactions** | Strictly Isolated |
| **Overall Precision** | 0.9609 | **0.9609** | Maintained high precision |
| **Overall Recall** | 0.9450 | **0.9450** | Maintained high recall |
| **Overall F1-Score** | 0.9529 | **0.9529** | Consistent performance |
| **Overall ROC-AUC** | 0.9984 | **0.9984** | Consistent discrimination |
| **Overall PR-AUC** | 0.9945 | **0.9945** | High area under PR curve |
| **Overall Brier Score** | 0.0355 | **0.0355** | Excellent probability accuracy |
| **Overall Calibration Error (ECE)** | 0.0696 | **0.0696** | Low calibration error |
| **Test Split F1-Score** | 0.9631 | **0.9648** | Tested on unseen customers |
| **Test Split ROC-AUC** | 0.9991 | **0.9989** | Robust generalization |
| **Test Split Brier Score** | 0.0350 | **0.0343** | Low Brier score on test set |

### D. Final Benchmark Verification Status
The **`v2.1` benchmark** is 100% reproducible (`seed=42`), zero customer leakage, zero transaction leakage, database-backed in Supabase, and ready to be frozen as the official baseline for Phase 3.

