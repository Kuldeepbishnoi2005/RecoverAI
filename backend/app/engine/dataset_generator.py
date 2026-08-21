import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Fixed random seed for 100% reproducible dataset generation
DEFAULT_SEED = 42
BENCHMARK_MERCHANT_ID = "00000000-0000-0000-0000-000000000001"
BENCHMARK_VERSION = "v2.1"


GATEWAYS = ["stripe", "razorpay", "payu"]
PAYMENT_METHODS = ["card", "upi", "netbanking", "auto_debit", "wallet"]
SUBSCRIPTION_STATUSES = ["active", "none", "past_due", "canceled"]
EVENT_TYPES = ["recurring_subscription", "one_time_payment", "installment"]
CARD_EXPIRY_STATUSES = ["valid", "expiring_soon", "expired", "not_applicable"]

FAILURE_CODES = [
    ("insufficient_funds", "Account balance insufficient for authorization", 0.30),
    ("network_timeout", "Bank gateway network connection timed out", 0.20),
    ("gateway_error", "Upstream payment processing gateway error", 0.15),
    ("expired_card", "Payment instrument card has expired", 0.12),
    ("authentication_failed", "3D-Secure authentication failed or timed out", 0.10),
    ("do_not_honor", "Issuing bank declined transaction without detail", 0.08),
    ("stolen_card", "Card reported stolen or lost by cardholder", 0.03),
    ("invalid_card", "Card number or CVV invalid", 0.02)
]

def compute_ground_truth(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes multi-factor ground-truth labels for a transaction event.
    Ground-truth recoverability represents true business recoverability derived
    from payment status, failure severity, customer history, LTV, retry count,
    subscription state, recency, and transaction amount.
    """
    status = data.get("transaction_status", "failed")
    code = data.get("failure_code")
    amount = float(data.get("amount", 0.0))
    prev_success = float(data.get("previous_success_rate", 0.80))
    ltv = float(data.get("customer_lifetime_value", 0.0))
    retries = int(data.get("retry_count", 0))
    sub_status = data.get("subscription_status", "none")
    days_since_success = int(data.get("days_since_last_success", 0))
    expiry = data.get("card_expiry_status", "valid")
    checkout = data.get("checkout_completed", True)

    # 1. Successful payments are not risk events / opportunities
    if status == "successful":
        return {
            "is_recovery_opportunity": False,
            "true_risk_level": "none",
            "recoverability": "none",
            "ground_truth_score": 0.0,
            "ground_truth_probability": 0.0,
            "expected_recovery_amount": 0.0,
            "recommended_recovery_strategy": "no_action"
        }

    # 2. Hard declines (stolen or invalid cards) are unrecoverable
    if code in ["stolen_card", "invalid_card"]:
        return {
            "is_recovery_opportunity": False,
            "true_risk_level": "critical",
            "recoverability": "unrecoverable",
            "ground_truth_score": 0.0,
            "ground_truth_probability": 0.0,
            "expected_recovery_amount": 0.0,
            "recommended_recovery_strategy": "no_action"
        }

    # 3. Base Ground-Truth Score by status/failure type
    if code in ["network_timeout", "gateway_error"]:
        base_score = 75.0
        base_strategy = "smart_retry"
    elif code in ["insufficient_funds", "authentication_failed"]:
        base_score = 60.0
        base_strategy = "smart_retry" if prev_success >= 0.70 else "personalized_dunning"
    elif code == "expired_card" or expiry == "expired":
        base_score = 55.0
        base_strategy = "payment_method_update"
    elif code == "do_not_honor":
        base_score = 35.0
        base_strategy = "personalized_dunning"
    elif status == "abandoned" or not checkout:
        base_score = 45.0
        base_strategy = "checkout_abandonment_reminder"
    elif status == "disputed":
        base_score = 25.0
        base_strategy = "manual_review"
    else:
        base_score = 50.0
        base_strategy = "smart_retry"

    # 4. Multi-factor Ground-Truth Adjustments
    adjust = 0.0

    # Customer success history
    if prev_success >= 0.85:
        adjust += 12.0
    elif prev_success >= 0.65:
        adjust += 4.0
    elif prev_success < 0.40:
        adjust -= 15.0

    # Customer LTV
    if ltv >= 15000.0:
        adjust += 8.0
    elif ltv >= 5000.0:
        adjust += 4.0
    elif ltv < 1000.0:
        adjust -= 5.0

    # Retry count penalty
    if retries == 0 or retries == 1:
        adjust += 4.0
    elif retries == 3:
        adjust -= 8.0
    elif retries >= 4:
        adjust -= 18.0

    # Subscription status
    if sub_status == "active":
        adjust += 8.0
    elif sub_status == "past_due":
        adjust -= 5.0
    elif sub_status == "canceled":
        adjust -= 12.0

    # Recency (days since last success)
    if days_since_success <= 7:
        adjust += 4.0
    elif days_since_success > 45:
        adjust -= 10.0

    # Transaction amount factor
    if amount < 300.0:
        adjust -= 5.0
    elif amount > 10000.0:
        adjust += 4.0

    # Calculate final ground truth score and probability
    gt_score = round(min(100.0, max(0.0, base_score + adjust)), 2)
    gt_prob = round(gt_score / 100.0, 4)

    # Opportunity decision threshold: gt_prob >= 0.40
    is_opp = bool(gt_prob >= 0.40)

    # Risk level classification
    if gt_score < 25.0:
        risk_lvl = "low"
        rec_lvl = "low"
    elif gt_score < 50.0:
        risk_lvl = "medium"
        rec_lvl = "medium"
    elif gt_score < 75.0:
        risk_lvl = "high"
        rec_lvl = "high"
    else:
        risk_lvl = "critical"
        rec_lvl = "very_high"

    exp_recovery = round(amount * gt_prob, 2)

    return {
        "is_recovery_opportunity": is_opp,
        "true_risk_level": risk_lvl,
        "recoverability": rec_lvl,
        "ground_truth_score": gt_score,
        "ground_truth_probability": gt_prob,
        "expected_recovery_amount": exp_recovery,
        "recommended_recovery_strategy": base_strategy
    }

def generate_synthetic_dataset(
    count: int = 10000,
    seed: int = DEFAULT_SEED,
    merchant_id: str = BENCHMARK_MERCHANT_ID,
    benchmark_version: str = BENCHMARK_VERSION
) -> List[Dict[str, Any]]:
    """
    Generates a deterministic synthetic payment dataset of `count` records.
    Uses a fixed random seed for 100% reproducibility.
    Includes deterministic train (60%), validation (20%), and test (20%) splits.
    """
    rng = random.Random(seed)

    # Pre-generate 2,000 customers
    customers = []
    for i in range(2000):
        c_id = str(uuid.UUID(int=rng.getrandbits(128)))
        orders_cnt = rng.randint(1, 40)
        spent = round(orders_cnt * rng.uniform(499.0, 4999.0), 2)
        success_rate = round(rng.betavariate(5, 1), 2)
        days_last = rng.randint(0, 90)
        sub_stat = rng.choice(SUBSCRIPTION_STATUSES)
        customers.append({
            "customer_id": c_id,
            "name": f"Customer {i+1}",
            "email": f"customer_{i+1}@example.com",
            "customer_history": {"total_orders": orders_cnt, "total_spent": spent},
            "customer_lifetime_value": spent,
            "subscription_status": sub_stat,
            "days_since_last_success": days_last,
            "previous_success_rate": success_rate
        })

    # Assign customer-disjoint splits (60% train / 20% validation / 20% test)
    cust_train_cutoff = int(len(customers) * 0.60)
    cust_val_cutoff = int(len(customers) * 0.80)

    customer_split_map = {}
    for idx, cust in enumerate(customers):
        if idx < cust_train_cutoff:
            customer_split_map[cust["customer_id"]] = "train"
        elif idx < cust_val_cutoff:
            customer_split_map[cust["customer_id"]] = "validation"
        else:
            customer_split_map[cust["customer_id"]] = "test"

    dataset = []
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(count):
        t_id = str(uuid.UUID(int=rng.getrandbits(128)))
        cust = rng.choice(customers)

        # Customer-disjoint split assignment
        split_tag = customer_split_map[cust["customer_id"]]


        # Distribute occurred_at over 90 days
        offset_seconds = rng.randint(0, 90 * 86400)
        t_timestamp = (base_time + timedelta(seconds=offset_seconds)).isoformat()

        # Gateway & method
        gw = rng.choice(GATEWAYS)
        pm = rng.choice(PAYMENT_METHODS)

        # Amount: log-normal distribution in INR (₹199 to ₹49,999)
        amount = round(rng.lognormvariate(7.5, 0.8), 2)
        amount = max(199.0, min(49999.0, amount))

        # Status distribution (~73% successful, ~19% failed, ~5% abandoned, ~3% disputed)
        status_rand = rng.random()
        if status_rand < 0.73:
            status = "successful"
            checkout = True
            dispute = "none"
            failure_code = None
            failure_reason = None
            retry_cnt = 0
            card_expiry = "valid" if pm == "card" else "not_applicable"
        elif status_rand < 0.92:
            status = "failed"
            checkout = True
            dispute = "none"

            fc_rand = rng.random()
            cum = 0.0
            chosen_fc = FAILURE_CODES[0]
            for fc, desc, weight in FAILURE_CODES:
                cum += weight
                if fc_rand <= cum:
                    chosen_fc = (fc, desc, weight)
                    break
            failure_code = chosen_fc[0]
            failure_reason = chosen_fc[1]
            retry_cnt = rng.randint(1, 4)
            if failure_code == "expired_card":
                card_expiry = "expired"
            elif pm == "card":
                card_expiry = rng.choice(["valid", "expiring_soon", "valid"])
            else:
                card_expiry = "not_applicable"
        elif status_rand < 0.97:
            status = "abandoned"
            checkout = False
            dispute = "none"
            failure_code = "checkout_abandoned"
            failure_reason = "Customer closed checkout session prior to payment authorization"
            retry_cnt = 0
            card_expiry = "valid" if pm == "card" else "not_applicable"
        else:
            status = "disputed"
            checkout = True
            dispute = rng.choice(["chargeback_opened", "in_review"])
            failure_code = "chargeback_notice"
            failure_reason = "Cardholder disputed charge with issuing bank"
            retry_cnt = 0
            card_expiry = "valid" if pm == "card" else "not_applicable"

        event_type = rng.choice(EVENT_TYPES)

        record = {
            "transaction_id": t_id,
            "merchant_id": merchant_id,
            "customer_id": cust["customer_id"],
            "payment_gateway": gw,
            "amount": amount,
            "currency": "INR",
            "transaction_timestamp": t_timestamp,
            "payment_method": pm,
            "transaction_status": status,
            "failure_code": failure_code,
            "failure_reason": failure_reason,
            "retry_count": retry_cnt,
            "customer_history": cust["customer_history"],
            "customer_lifetime_value": cust["customer_lifetime_value"],
            "subscription_status": cust["subscription_status"],
            "days_since_last_success": cust["days_since_last_success"],
            "previous_success_rate": cust["previous_success_rate"],
            "card_expiry_status": card_expiry,
            "dispute_status": dispute,
            "checkout_completed": checkout,
            "event_type": event_type,
            "benchmark_version": benchmark_version,
            "dataset_split": split_tag
        }

        # Compute multi-factor ground truth
        record["ground_truth"] = compute_ground_truth(record)
        dataset.append(record)

    return dataset
