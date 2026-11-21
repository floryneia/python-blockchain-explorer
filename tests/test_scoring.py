from datetime import datetime, timedelta
import pytest

from app.models import Transaction
from app.scoring import WalletRiskScorer

ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"


def make_tx(
    *,
    days_ago: int = 100,
    from_addr: str = ADDRESS,
    to_addr: str = "0xContractA",
    is_error: bool = False,
    index: int = 0,
) -> Transaction:
    ts = datetime.now() - timedelta(days=days_ago) + timedelta(seconds=index)
    return Transaction(
        hash=f"0xhash{index:04d}",
        block_number=1000000 + index,
        timestamp=ts,
        from_address=from_addr,
        to_address=to_addr,
        value_wei=1_000_000_000_000_000_000,  # 1 ETH
        gas_used=21000,
        is_error=is_error,
        contract_address=None,
    )


scorer = WalletRiskScorer()


class TestEmptyWallet:
    def test_score_is_zero(self):
        result = scorer.score(ADDRESS, [])
        assert result.score == 0

    def test_label_is_unknown(self):
        result = scorer.score(ADDRESS, [])
        assert result.label == "unknown"

    def test_no_transaction_reason(self):
        result = scorer.score(ADDRESS, [])
        assert any("No transaction" in r for r in result.reasons)


class TestNewWallet:
    def setup_method(self):
        txs = [make_tx(days_ago=5, index=i) for i in range(3)]
        self.result = scorer.score(ADDRESS, txs)

    def test_low_score(self):
        assert self.result.score < 30

    def test_new_wallet_reason(self):
        assert any("New wallet" in r for r in self.result.reasons)

    def test_low_activity_reason(self):
        assert any("Low activity" in r for r in self.result.reasons)


class TestEstablishedWallet:
    def setup_method(self):
        contracts = ["0xContractA", "0xContractB", "0xContractC", "0xContractD", "0xContractE"]
        txs = [
            make_tx(days_ago=400 - i, to_addr=contracts[i % len(contracts)], index=i)
            for i in range(120)
        ]
        self.result = scorer.score(ADDRESS, txs)

    def test_high_score(self):
        assert self.result.score >= 60

    def test_label_is_low_risk(self):
        assert self.result.label == "low"

    def test_established_reason(self):
        assert any("Established" in r for r in self.result.reasons)


class TestHighErrorRate:
    def setup_method(self):
        txs = [make_tx(days_ago=200, is_error=(i % 3 == 0), index=i) for i in range(30)]
        self.result = scorer.score(ADDRESS, txs)

    def test_error_rate_in_summary(self):
        assert self.result.summary.error_rate > 0.2

    def test_error_reason_present(self):
        assert any("error rate" in r for r in self.result.reasons)


class TestScoreComponents:
    def test_score_bounded_0_100(self):
        txs = [make_tx(days_ago=1000, index=i) for i in range(200)]
        result = scorer.score(ADDRESS, txs)
        assert 0 <= result.score <= 100

    def test_contract_diversity_adds_points(self):
        few_contracts = [make_tx(days_ago=200, to_addr="0xSameContract", index=i) for i in range(10)]
        many_contracts = [
            make_tx(days_ago=200, to_addr=f"0xContract{i}", index=i) for i in range(10)
        ]
        score_few = scorer.score(ADDRESS, few_contracts).score
        score_many = scorer.score(ADDRESS, many_contracts).score
        assert score_many > score_few
