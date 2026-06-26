from app.schemas.response import CaseType, Department, EvidenceVerdict, Severity


def route_department(case_type: CaseType, evidence_verdict: EvidenceVerdict | None = None, severity: Severity | None = None) -> Department:
    if case_type == CaseType.wrong_transfer:
        return Department.dispute_resolution
    if case_type == CaseType.refund_request:
        if severity == Severity.low and evidence_verdict == EvidenceVerdict.consistent:
            return Department.customer_support
        return Department.dispute_resolution
    if case_type in {CaseType.payment_failed, CaseType.duplicate_payment}:
        return Department.payments_ops
    if case_type == CaseType.merchant_settlement_delay:
        return Department.merchant_operations
    if case_type == CaseType.agent_cash_in_issue:
        return Department.agent_operations
    if case_type == CaseType.phishing_or_social_engineering:
        return Department.fraud_risk
    return Department.customer_support
