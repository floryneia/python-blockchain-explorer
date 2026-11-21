from datetime import datetime, timezone
from app.models import Transaction, WalletSummary, RiskScore


class WalletRiskScorer:
    """
    Scores a wallet's trustworthiness based on its transaction history.
    Rules are explicit and inspectable (no ML).

    Scoring breakdown (100 points total):
      - Age             : up to 30 pts  (older = safer)
      - Volume          : up to 25 pts  (more txs = established)
      - Contracts       : up to 25 pts  (diverse interactions = active user)
      - Error rate      : up to 20 pts  (fewer failed txs = lower risk)
    """

    def score(self, address: str, transactions: list[Transaction]) -> RiskScore:
        if not transactions:
            return RiskScore(
                address=address,
                score=0,
                label="unknown",
                reasons=["No transaction history found."],
                summary=self._empty_summary(address),
            )

        summary = self._build_summary(address, transactions)
        points, reasons = self._compute_points(summary)
        label = self._label(points)

        return RiskScore(
            address=address,
            score=points,
            label=label,
            reasons=reasons,
            summary=summary,
        )

    def _build_summary(self, address: str, txs: list[Transaction]) -> WalletSummary:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        first_seen = min(tx.timestamp for tx in txs)
        last_seen = max(tx.timestamp for tx in txs)
        age_days = (now - first_seen).days

        outgoing = [tx for tx in txs if tx.from_address.lower() == address.lower()]
        contracts = {
            tx.to_address
            for tx in outgoing
            if tx.to_address and tx.contract_address is None
        }
        error_count = sum(1 for tx in outgoing if tx.is_error)
        error_rate = error_count / len(outgoing) if outgoing else 0.0

        return WalletSummary(
            address=address,
            first_seen=first_seen,
            last_seen=last_seen,
            tx_count=len(txs),
            unique_contracts=len(contracts),
            error_rate=round(error_rate, 4),
            age_days=age_days,
        )

    def _compute_points(self, s: WalletSummary) -> tuple[int, list[str]]:
        points = 0
        reasons = []

        # Age (0-30)
        age_pts = min(30, s.age_days // 12)  # 1 pt per 12 days, max 30 (= ~1 year)
        points += age_pts
        if s.age_days < 30:
            reasons.append(f"New wallet ({s.age_days} days old).")
        elif s.age_days >= 365:
            reasons.append(f"Established wallet ({s.age_days // 365}y old).")

        # Volume (0-25)
        volume_pts = min(25, s.tx_count // 4)  # 1 pt per 4 txs, max 25 (= 100 txs)
        points += volume_pts
        if s.tx_count < 10:
            reasons.append(f"Low activity ({s.tx_count} transactions).")
        elif s.tx_count >= 100:
            reasons.append(f"High activity ({s.tx_count} transactions).")

        # Contract diversity (0-25)
        contract_pts = min(25, s.unique_contracts * 5)  # 5 pts per unique contract
        points += contract_pts
        if s.unique_contracts == 0:
            reasons.append("No contract interactions detected.")
        elif s.unique_contracts >= 5:
            reasons.append(f"Diverse on-chain activity ({s.unique_contracts} contracts).")

        # Error rate (0-20)
        error_pts = round(20 * (1 - s.error_rate))
        points += error_pts
        if s.error_rate > 0.2:
            reasons.append(f"High error rate ({s.error_rate:.0%} of outgoing txs failed).")

        return points, reasons

    def _label(self, score: int) -> str:
        if score >= 60:
            return "low"
        if score >= 30:
            return "medium"
        return "high"

    def _empty_summary(self, address: str) -> WalletSummary:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return WalletSummary(
            address=address,
            first_seen=now,
            last_seen=now,
            tx_count=0,
            unique_contracts=0,
            error_rate=0.0,
            age_days=0,
        )
