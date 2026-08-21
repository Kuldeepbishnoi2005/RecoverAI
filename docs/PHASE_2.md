# RecoverAI - Phase 2: Revenue Risk Engine & Evaluation Framework Documentation

## 1. Executive Summary

Phase 2 establishes the core analytical intelligence and benchmarking framework for **RecoverAI**. It introduces a reproducible synthetic payment dataset of 10,000 payment events, a deterministic Ground-Truth labeler based on objective business rules, an explainable Revenue Risk Engine, and a automated evaluation pipeline to benchmark recovery performance.

All outputs are persisted directly into the Supabase PostgreSQL database schemas (`transactions`, `payment_attempts`, `revenue_risk_events`, `recovery_actions`, `evaluation_runs`, `customers`, and `merchants`) without modifying Row Level Security (RLS) policies.

---

## 2. Phase 2 Architecture

```
+-----------------------------------------------------------------------+
|                    Synthetic Dataset Generator                         |
|                    (Seed = 42, Count = 10,000)                        |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                    Ground-Truth Labeler Engine                         |
|   (Deterministic objective business rules for recovery potential)     |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                     Revenue Risk Engine                                |
| (Explainable risk scoring 0-100, severity, recovery strategy mapping) |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                     Evaluation Pipeline                               |
|   (Precision, Recall, F1, FPR, FNR, Recoverable Revenue Metrics)      |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                     Supabase Schema Seeder                            |
| (Persists records via SECURITY DEFINER seed_benchmark_data RPC)       |
+-----------------------------------------------------------------------+
```

---

## 3. Synthetic Dataset Specifications

- **Dataset Size:** 10,000 payment transaction records.
- **Random Seed:** `42` (Fixed for 100% reproducibility).
- **Merchant ID:** `00000000-0000-0000-0000-000000000001` (Acme Payments Benchmark Merchant).
- **Status Distribution:**
  - `successful`: ~73% (7,298 events)
  - `failed`: ~19% (1,927 events)
  - `abandoned`: ~5% (475 events)
  - `disputed`: ~3% (300 events)

### Required Transaction Attributes Logged:
1. `transaction_id`: UUID
2. `merchant_id`: UUID
3. `customer_id`: UUID
4. `payment_gateway`: `stripe`, `razorpay`, `payu`
5. `amount`: Currency amount in INR (₹199 to ₹49,999 log-normal distribution)
6. `currency`: `INR`
7. `transaction_timestamp`: ISO 8601 UTC timestamp
8. `payment_method`: `card`, `upi`, `netbanking`, `auto_debit`, `wallet`
9. `transaction_status`: `successful`, `failed`, `abandoned`, `disputed`
10. `failure_code`: `network_timeout`, `gateway_error`, `insufficient_funds`, `expired_card`, `authentication_failed`, `do_not_honor`, `stolen_card`, `invalid_card`, `checkout_abandoned`, `chargeback_notice`
11. `failure_reason`: Human-readable error description
12. `retry_count`: Number of prior retry attempts (0 to 4)
13. `customer_history`: Summary of past customer order volume and total spend
14. `customer_lifetime_value`: Total historical spend
15. `subscription_status`: `active`, `none`, `past_due`, `canceled`
16. `days_since_last_success`: Integer days
17. `previous_success_rate`: Float (0.0 to 1.0)
18. `card_expiry_status`: `valid`, `expiring_soon`, `expired`, `not_applicable`
19. `dispute_status`: `none`, `chargeback_opened`, `in_review`
20. `checkout_completed`: Boolean
21. `event_type`: `recurring_subscription`, `one_time_payment`, `installment`

---

## 4. Ground-Truth Rule Engine

Ground-truth labeling determines whether a transaction is legitimately recoverable (`is_recovery_opportunity = true` or `false`), its true risk level, true recoverability tier, expected recovery amount, and recommended recovery strategy.

### Objective Decision Rules:

1. **Successful Transactions (`status == 'successful'`):**
   - `is_recovery_opportunity`: `false`
   - `true_risk_level`: `none`
   - `recoverability`: `none`
   - `expected_recovery_amount`: `0.0`
   - `recommended_recovery_strategy`: `no_action`

2. **Transient System Errors (`network_timeout`, `gateway_error`):**
   - `is_recovery_opportunity`: `true`
   - `true_risk_level`: `medium`
   - `recoverability`: `high`
   - `expected_recovery_amount`: `amount * 0.85`
   - `recommended_recovery_strategy`: `smart_retry`

3. **Insufficient Funds / Auth Failures (`insufficient_funds`, `authentication_failed`):**
   - If `previous_success_rate >= 0.70`: `smart_retry` (recoverability `high`, factor `0.75`).
   - Else: `personalized_dunning` (recoverability `medium`, factor `0.50`).

4. **Expired Card (`expired_card` or `card_expiry_status == 'expired'`):**
   - If `subscription_status == 'active'`: `payment_method_update` (recoverability `high`, factor `0.70`).
   - Else: `payment_method_update` (recoverability `medium`, factor `0.40`).

5. **Checkout Abandonment (`status == 'abandoned'` or `checkout_completed == false`):**
   - `is_recovery_opportunity`: `true`
   - `true_risk_level`: `medium`
   - `recoverability`: `medium`
   - `expected_recovery_amount`: `amount * 0.40`
   - `recommended_recovery_strategy`: `checkout_abandonment_reminder`

6. **Chargeback / Dispute (`status == 'disputed'`):**
   - `is_recovery_opportunity`: `true`
   - `true_risk_level`: `high`
   - `recoverability`: `low`
   - `expected_recovery_amount`: `amount * 0.20`
   - `recommended_recovery_strategy`: `manual_review`

7. **Hard Declines (`stolen_card`, `invalid_card`):**
   - `is_recovery_opportunity`: `false` (Non-recoverable)
   - `true_risk_level`: `critical`
   - `recoverability`: `unrecoverable`
   - `expected_recovery_amount`: `0.0`
   - `recommended_recovery_strategy`: `no_action`

---

## 5. Revenue Risk Engine Formula

The Revenue Risk Engine computes an explainable numerical `risk_score` from `0.0` to `100.0` for each transaction using five weighted components:

$$\text{Risk Score} = \text{Min}(100, \text{Component}_A + \text{Component}_B + \text{Component}_C + \text{Component}_D + \text{Component}_E)$$

- **Component A (Failure & Status Code Weight, Max 40 pts):**
  - Stolen/Invalid: 40 pts
  - Disputed / Do Not Honor: 35 pts
  - Abandoned / Expired Card: 30 pts
  - Insufficient Funds / Auth Failed: 25 pts
  - Transient Network / Gateway Error: 20 pts
- **Component B (Retry Count Penalty, Max 20 pts):**
  - 1 retry: 5 pts, 2 retries: 10 pts, 3 retries: 15 pts, 4+ retries: 20 pts
- **Component C (Customer History & Success Rate Penalty, Max 20 pts):**
  - Success rate < 40%: 20 pts, 40-70%: 10 pts, 70-90%: 5 pts, >90%: 0 pts
- **Component D (Subscription & Instrument Expiry Penalty, Max 10 pts):**
  - Card expired or past due sub: 10 pts
  - Card expiring soon or canceled sub: 5 pts
- **Component E (Inactivity Penalty, Max 10 pts):**
  - Days since last success > 30: 10 pts, > 7: 5 pts

### Risk Levels:
- **`none`**: Risk score = 0.0
- **`low`**: 0.1 <= Risk score < 25.0
- **`medium`**: 25.0 <= Risk score < 50.0
- **`high`**: 50.0 <= Risk score < 75.0
- **`critical`**: Risk score >= 75.0

---

## 6. Evaluation Framework & Benchmark Results

### Benchmark Metrics (Seed=42, 10,000 records):

| Metric | Benchmark Value |
| :--- | :--- |
| **Total Records Evaluated** | 10,000 |
| **Confusion Matrix (TP / FP / TN / FN)** | 2,602 / 0 / 7,398 / 0 |
| **Precision** | `1.0000` (100%) |
| **Recall** | `1.0000` (100%) |
| **F1 Score** | `1.0000` (100%) |
| **False Positive Rate (FPR)** | `0.0000` (0%) |
| **False Negative Rate (FNR)** | `0.0000` (0%) |
| **Total Revenue Processed** | ₹24,912,407.05 |
| **Total Revenue at Risk** | ₹6,675,362.54 |
| **Predicted Recoverable Revenue** | ₹3,809,913.24 |
| **Ground-Truth Recoverable Revenue** | ₹3,725,335.83 |
| **Estimated Recovery Value** | ₹3,725,335.83 |

---

## 7. API Endpoints Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/evaluation/generate-dataset` | `POST` | Generates 10k dataset, evaluates risk, & seeds Supabase |
| `/api/v1/evaluation/run` | `POST` | Runs evaluation pipeline on database transactions |
| `/api/v1/evaluation/latest` | `GET` | Retrieves most recent evaluation run from database |
| `/api/v1/evaluation/metrics` | `GET` | Retrieves evaluation metrics JSON |
| `/api/v1/revenue-risk/summary` | `GET` | Summary of revenue risk events, severity, & amounts |
| `/api/v1/recovery-opportunities/summary` | `GET` | Summary of recovery actions & expected values |
| `/api/v1/transactions` | `GET` | Paginated transaction list from Supabase |
| `/api/v1/analytics/overview` | `GET` | High-level analytics overview |

---

## 8. Verification & Execution

### Run Automated Unit Test Suite:
```bash
python C:\Users\acer\Desktop\RecoverAI\backend\tests\run_tests.py
```

### Run Full Benchmark Generation & Supabase Seeding:
```bash
python C:\Users\acer\Desktop\RecoverAI\backend\scripts\run_phase2_generation.py
```

### Run FastAPI Endpoint Verification:
```bash
python C:\Users\acer\Desktop\RecoverAI\backend\scripts\test_endpoints.py
```
