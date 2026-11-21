from pydantic import BaseModel, field_validator
from datetime import datetime


class Transaction(BaseModel):
    hash: str
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: str | None
    value_wei: int
    gas_used: int
    is_error: bool
    contract_address: str | None  # non-null = contract creation

    @property
    def value_eth(self) -> float:
        return self.value_wei / 1e18

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_unix_timestamp(cls, v):
        if isinstance(v, (int, str)):
            return datetime.fromtimestamp(int(v))
        return v

    @field_validator("value_wei", "gas_used", "block_number", mode="before")
    @classmethod
    def coerce_int(cls, v):
        return int(v)

    @field_validator("is_error", mode="before")
    @classmethod
    def coerce_bool(cls, v):
        if isinstance(v, bool):
            return v
        return str(v) == "1"


class WalletSummary(BaseModel):
    address: str
    first_seen: datetime
    last_seen: datetime
    tx_count: int
    unique_contracts: int
    error_rate: float  # 0.0 to 1.0
    age_days: int


class RiskScore(BaseModel):
    address: str
    score: int  # 0 (risky) to 100 (trustworthy)
    label: str  # "low", "medium", "high"
    reasons: list[str]
    summary: WalletSummary
