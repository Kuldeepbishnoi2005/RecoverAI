from typing import List, Dict, Any

AMBIGUITY_TEST_CASES: List[Dict[str, Any]] = [
    {
        "id": "case_1",
        "description": "High-value successful payment",
        "event": {
            "transaction_status": "successful",
            "failure_code": None,
            "amount": 49999.0,
            "retry_count": 0,
            "previous_success_rate": 0.95,
            "customer_lifetime_value": 85000.0,
            "subscription_status": "active",
            "card_expiry_status": "valid",
            "days_since_last_success": 2,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_2",
        "description": "Low-value failed payment",
        "event": {
            "transaction_status": "failed",
            "failure_code": "insufficient_funds",
            "amount": 199.0,
            "retry_count": 1,
            "previous_success_rate": 0.80,
            "customer_lifetime_value": 800.0,
            "subscription_status": "none",
            "card_expiry_status": "valid",
            "days_since_last_success": 10,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "upi",
            "payment_gateway": "razorpay"
        }
    },
    {
        "id": "case_3",
        "description": "Temporary failure + excellent customer history",
        "event": {
            "transaction_status": "failed",
            "failure_code": "network_timeout",
            "amount": 2500.0,
            "retry_count": 1,
            "previous_success_rate": 0.98,
            "customer_lifetime_value": 25000.0,
            "subscription_status": "active",
            "card_expiry_status": "valid",
            "days_since_last_success": 1,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_4",
        "description": "Temporary failure + poor customer history",
        "event": {
            "transaction_status": "failed",
            "failure_code": "network_timeout",
            "amount": 2500.0,
            "retry_count": 4,
            "previous_success_rate": 0.20,
            "customer_lifetime_value": 500.0,
            "subscription_status": "canceled",
            "card_expiry_status": "expiring_soon",
            "days_since_last_success": 60,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "payu"
        }
    },
    {
        "id": "case_5",
        "description": "Expired card + high LTV",
        "event": {
            "transaction_status": "failed",
            "failure_code": "expired_card",
            "amount": 15000.0,
            "retry_count": 1,
            "previous_success_rate": 0.92,
            "customer_lifetime_value": 45000.0,
            "subscription_status": "active",
            "card_expiry_status": "expired",
            "days_since_last_success": 5,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_6",
        "description": "Expired card + low LTV",
        "event": {
            "transaction_status": "failed",
            "failure_code": "expired_card",
            "amount": 299.0,
            "retry_count": 3,
            "previous_success_rate": 0.15,
            "customer_lifetime_value": 299.0,
            "subscription_status": "none",
            "card_expiry_status": "expired",
            "days_since_last_success": 85,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "razorpay"
        }
    },
    {
        "id": "case_7",
        "description": "Repeated temporary failures",
        "event": {
            "transaction_status": "failed",
            "failure_code": "insufficient_funds",
            "amount": 4990.0,
            "retry_count": 4,
            "previous_success_rate": 0.75,
            "customer_lifetime_value": 12000.0,
            "subscription_status": "past_due",
            "card_expiry_status": "valid",
            "days_since_last_success": 14,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "auto_debit",
            "payment_gateway": "razorpay"
        }
    },
    {
        "id": "case_8",
        "description": "Single temporary failure",
        "event": {
            "transaction_status": "failed",
            "failure_code": "gateway_error",
            "amount": 1200.0,
            "retry_count": 1,
            "previous_success_rate": 0.88,
            "customer_lifetime_value": 8500.0,
            "subscription_status": "active",
            "card_expiry_status": "valid",
            "days_since_last_success": 4,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "netbanking",
            "payment_gateway": "payu"
        }
    },
    {
        "id": "case_9",
        "description": "Abandoned cart + high value",
        "event": {
            "transaction_status": "abandoned",
            "failure_code": "checkout_abandoned",
            "amount": 35000.0,
            "retry_count": 0,
            "previous_success_rate": 0.90,
            "customer_lifetime_value": 60000.0,
            "subscription_status": "active",
            "card_expiry_status": "valid",
            "days_since_last_success": 3,
            "checkout_completed": False,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_10",
        "description": "Abandoned cart + low value",
        "event": {
            "transaction_status": "abandoned",
            "failure_code": "checkout_abandoned",
            "amount": 299.0,
            "retry_count": 0,
            "previous_success_rate": 0.30,
            "customer_lifetime_value": 299.0,
            "subscription_status": "none",
            "card_expiry_status": "valid",
            "days_since_last_success": 50,
            "checkout_completed": False,
            "dispute_status": "none",
            "payment_method": "upi",
            "payment_gateway": "razorpay"
        }
    },
    {
        "id": "case_11",
        "description": "Disputed transaction",
        "event": {
            "transaction_status": "disputed",
            "failure_code": "chargeback_notice",
            "amount": 8500.0,
            "retry_count": 0,
            "previous_success_rate": 0.85,
            "customer_lifetime_value": 18000.0,
            "subscription_status": "canceled",
            "card_expiry_status": "valid",
            "days_since_last_success": 45,
            "checkout_completed": True,
            "dispute_status": "chargeback_opened",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_12",
        "description": "Resolved dispute",
        "event": {
            "transaction_status": "disputed",
            "failure_code": "chargeback_notice",
            "amount": 4200.0,
            "retry_count": 0,
            "previous_success_rate": 0.94,
            "customer_lifetime_value": 32000.0,
            "subscription_status": "active",
            "card_expiry_status": "valid",
            "days_since_last_success": 10,
            "checkout_completed": True,
            "dispute_status": "in_review",
            "payment_method": "card",
            "payment_gateway": "razorpay"
        }
    },
    {
        "id": "case_13",
        "description": "Subscription failure (active sub)",
        "event": {
            "transaction_status": "failed",
            "failure_code": "insufficient_funds",
            "amount": 1499.0,
            "retry_count": 1,
            "previous_success_rate": 0.95,
            "customer_lifetime_value": 18000.0,
            "subscription_status": "active",
            "card_expiry_status": "valid",
            "days_since_last_success": 30,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "auto_debit",
            "payment_gateway": "razorpay"
        }
    },
    {
        "id": "case_14",
        "description": "Non-subscription failure",
        "event": {
            "transaction_status": "failed",
            "failure_code": "authentication_failed",
            "amount": 3499.0,
            "retry_count": 2,
            "previous_success_rate": 0.60,
            "customer_lifetime_value": 3499.0,
            "subscription_status": "none",
            "card_expiry_status": "valid",
            "days_since_last_success": 15,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_15",
        "description": "Long period since last success (>60 days)",
        "event": {
            "transaction_status": "failed",
            "failure_code": "insufficient_funds",
            "amount": 2200.0,
            "retry_count": 3,
            "previous_success_rate": 0.45,
            "customer_lifetime_value": 2200.0,
            "subscription_status": "canceled",
            "card_expiry_status": "valid",
            "days_since_last_success": 75,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "payu"
        }
    },
    {
        "id": "case_16",
        "description": "Recent successful payment (<2 days)",
        "event": {
            "transaction_status": "failed",
            "failure_code": "network_timeout",
            "amount": 1999.0,
            "retry_count": 1,
            "previous_success_rate": 0.96,
            "customer_lifetime_value": 24000.0,
            "subscription_status": "active",
            "card_expiry_status": "valid",
            "days_since_last_success": 1,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "upi",
            "payment_gateway": "razorpay"
        }
    },
    {
        "id": "case_17",
        "description": "High retry velocity (4+ retries)",
        "event": {
            "transaction_status": "failed",
            "failure_code": "network_timeout",
            "amount": 8900.0,
            "retry_count": 4,
            "previous_success_rate": 0.65,
            "customer_lifetime_value": 15000.0,
            "subscription_status": "past_due",
            "card_expiry_status": "valid",
            "days_since_last_success": 20,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_18",
        "description": "Low retry velocity (1 retry)",
        "event": {
            "transaction_status": "failed",
            "failure_code": "network_timeout",
            "amount": 8900.0,
            "retry_count": 1,
            "previous_success_rate": 0.92,
            "customer_lifetime_value": 28000.0,
            "subscription_status": "active",
            "card_expiry_status": "valid",
            "days_since_last_success": 3,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_19",
        "description": "Conflicting signals (high LTV but do_not_honor & past_due sub)",
        "event": {
            "transaction_status": "failed",
            "failure_code": "do_not_honor",
            "amount": 12500.0,
            "retry_count": 3,
            "previous_success_rate": 0.70,
            "customer_lifetime_value": 35000.0,
            "subscription_status": "past_due",
            "card_expiry_status": "expiring_soon",
            "days_since_last_success": 35,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "stripe"
        }
    },
    {
        "id": "case_20",
        "description": "Borderline probability case (near 0.40 threshold)",
        "event": {
            "transaction_status": "failed",
            "failure_code": "do_not_honor",
            "amount": 3500.0,
            "retry_count": 2,
            "previous_success_rate": 0.65,
            "customer_lifetime_value": 4500.0,
            "subscription_status": "none",
            "card_expiry_status": "valid",
            "days_since_last_success": 25,
            "checkout_completed": True,
            "dispute_status": "none",
            "payment_method": "card",
            "payment_gateway": "payu"
        }
    }
]
