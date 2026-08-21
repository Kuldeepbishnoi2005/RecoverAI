import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Fixed random seed for 100% reproducible dataset generation
DEFAULT_SEED = 42
BENCHMARK_MERCHANT_ID = "00000000-0000-0000-0000-000000000001"

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
    Computes deterministic ground-truth labels for a transaction event.
    No LLMs or random noise used; strict rule-based benchmark truth.
    """
    status = data["transaction_status"]
    code = data.get("failure_code")
    amount = float(data["amount"])
    expiry = data["card_expiry_status"]
    checkout = data["checkout_completed"]
    prev_success = float(data["previous_success_rate"])
    sub_status = data["subscription_status"]

    if status == "successful":
        return {
            "is_recovery_opportunity": False,
            "true_risk_level": "none",
            "recoverability": "none",
            "expected_recovery_amount": 0.0,
            "recommended_recovery_strategy": "no_action"
        }

    if status == "abandoned" or not checkout:
        return {
            "is_recovery_opportunity": True,
            "true_risk_level": "medium",
            "recoverability": "medium",
            "expected_recovery_amount": round(amount * 0.40, 2),
            "recommended_recovery_strategy": "checkout_abandonment_reminder"
        }

    if status == "disputed":
        return {
            "is_recovery_opportunity": True,
            "true_risk_level": "high",
            "recoverability": "low",
            "expected_recovery_amount": round(amount * 0.20, 2),
            "recommended_recovery_strategy": "manual_review"
        }

    # Failed status
    if code in ["network_timeout", "gateway_error"]:
        return {
            "is_recovery_opportunity": True,
            "true_risk_level": "medium",
            "recoverability": "high",
            "expected_recovery_amount": round(amount * 0.85, 2),
            "recommended_recovery_strategy": "smart_retry"
        }

    if code in ["insufficient_funds", "authentication_failed"]:
        if prev_success >= 0.70:
            return {
                "is_recovery_opportunity": True,
                "true_risk_level": "medium",
                "recoverability": "high",
                "expected_recovery_amount": round(amount * 0.75, 2),
                "recommended_recovery_strategy": "smart_retry"
            }
        else:
            return {
                "is_recovery_opportunity": True,
                "true_risk_level": "high",
                "recoverability": "medium",
                "expected_recovery_amount": round(amount * 0.50, 2),
                "recommended_recovery_strategy": "personalized_dunning"
            }

    if code == "expired_card" or expiry == "expired":
        if sub_status == "active":
            return {
                "is_recovery_opportunity": True,
                "true_risk_level": "high",
                "recoverability": "high",
                "expected_recovery_amount": round(amount * 0.70, 2),
                "recommended_recovery_strategy": "payment_method_update"
            }
        else:
            return {
                "is_recovery_opportunity": True,
                "true_risk_level": "medium",
                "recoverability": "medium",
                "expected_recovery_amount": round(amount * 0.40, 2),
                "recommended_recovery_strategy": "payment_method_update"
            }

    if code == "do_not_honor":
        return {
            "is_recovery_opportunity": True,
            "true_risk_level": "high",
            "recoverability": "low",
            "expected_recovery_amount": round(amount * 0.25, 2),
            "recommended_recovery_strategy": "personalized_dunning"
        }

    if code in ["stolen_card", "invalid_card"]:
        return {
            "is_recovery_opportunity": False,  # Hard decline; non-recoverable
            "true_risk_level": "critical",
            "recoverability": "unrecoverable",
            "expected_recovery_amount": 0.0,
            "recommended_recovery_strategy": "no_action"
        }

    # Fallback
    return {
        "is_recovery_opportunity": True,
        "true_risk_level": "medium",
        "recoverability": "medium",
        "expected_recovery_amount": round(amount * 0.50, 2),
        "recommended_recovery_strategy": "smart_retry"
    }

def generate_synthetic_dataset(
    count: int = 10000,
    seed: int = DEFAULT_SEED,
    merchant_id: str = BENCHMARK_MERCHANT_ID
) -> List[Dict[str, Any]]:
    """
    Generates a deterministic synthetic payment dataset of `count` records.
    Uses a fixed random seed for 100% reproducibility.
    """
    rng = random.Random(seed)

    # Pre-generate 2,000 customers
    customers = []
    for i in range(2000):
        c_id = str(uuid.UUID(int=rng.getrandbits(128)))
        orders_cnt = rng.randint(1, 40)
        spent = round(orders_cnt * rng.uniform(499.0, 4999.0), 2)
        success_rate = round(rng.betavariate(5, 1), 2) # Skewed towards high success (0.7-0.99)
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

    dataset = []
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(count):
        t_id = str(uuid.UUID(int=rng.getrandbits(128)))
        cust = rng.choice(customers)

        # Distribute occurred_at over 90 days
        offset_seconds = rng.randint(0, 90 * 86400)
        t_timestamp = (base_time + timedelta(seconds=offset_seconds)).isoformat()

        # Gateway & method
        gw = rng.choice(GATEWAYS)
        pm = rng.choice(PAYMENT_METHODS)

        # Amount: realistic log-normal distribution in INR (₹199 to ₹49,999)
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

            # Pick failure code
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
            "event_type": event_type
        }

        # Compute ground truth
        record["ground_truth"] = compute_ground_truth(record)
        dataset.append(record)

    return dataset
