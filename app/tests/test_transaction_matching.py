from app.core.transaction_matcher import find_duplicate_payment_group, match_transaction
from app.schemas.request import Transaction
from app.schemas.response import CaseType


def tx(transaction_id, type_, amount, counterparty, status="completed", ts="2026-04-14T10:00:00Z"):
    return Transaction(transaction_id=transaction_id, timestamp=ts, type=type_, amount=amount, counterparty=counterparty, status=status)


def test_amount_type_counterparty_match_selects_transaction():
    transactions = [
        tx("TXN-1", "transfer", 5000, "+8801719876543"),
        tx("TXN-2", "cash_in", 10000, "AGENT-1"),
    ]
    match = match_transaction("I sent 5000 taka to wrong number 01719876543", transactions, CaseType.wrong_transfer)
    assert match.transaction is not None
    assert match.transaction.transaction_id == "TXN-1"
    assert "amount_match" in match.reason_codes


def test_weak_match_returns_null():
    transactions = [tx("TXN-1", "transfer", 5000, "+8801719876543")]
    match = match_transaction("Something is wrong with my money", transactions, CaseType.other)
    assert match.transaction is None
    assert "weak_transaction_match" in match.reason_codes


def test_ambiguous_equal_amount_transfers_return_null():
    transactions = [
        tx("TXN-1", "transfer", 1000, "+8801711111111", ts="2026-04-13T11:00:00Z"),
        tx("TXN-2", "transfer", 1000, "+8801822222222", ts="2026-04-13T12:00:00Z"),
    ]
    match = match_transaction("I sent 1000 yesterday but he did not get it", transactions, CaseType.wrong_transfer)
    assert match.transaction is None
    assert match.ambiguous is True


def test_duplicate_payment_group_selects_second_transaction():
    transactions = [
        tx("TXN-1", "payment", 850, "BILLER-DESCO", ts="2026-04-14T08:15:30Z"),
        tx("TXN-2", "payment", 850, "BILLER-DESCO", ts="2026-04-14T08:15:42Z"),
    ]
    group = find_duplicate_payment_group(transactions)
    assert [item.transaction_id for item in group] == ["TXN-1", "TXN-2"]
    match = match_transaction("It deducted twice 850 taka", transactions, CaseType.duplicate_payment)
    assert match.transaction.transaction_id == "TXN-2"
