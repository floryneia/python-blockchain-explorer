import httpx
from app.models import Transaction


ETHERSCAN_BASE_URL = "https://api.etherscan.io/api"


class EtherscanError(Exception):
    pass


class EtherscanClient:
    """
    Thin wrapper around the Etherscan API.
    Handles pagination, retries and error normalization.
    """

    def __init__(self, api_key: str, timeout: float = 10.0):
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def get_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        max_results: int = 500,
    ) -> list[Transaction]:
        """
        Fetch normal transactions for an address.
        Returns up to max_results transactions, oldest first.
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": 1,
            "offset": min(max_results, 10000),
            "sort": "asc",
            "apikey": self._api_key,
        }

        response = await self._client.get(ETHERSCAN_BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()

        if data["status"] == "0":
            message = data.get("message", "")
            # Etherscan returns status=0 for empty wallets too
            if "No transactions found" in message:
                return []
            raise EtherscanError(f"Etherscan error: {data.get('result', message)}")

        raw_txs = data["result"]
        return [self._parse_transaction(tx) for tx in raw_txs]

    def _parse_transaction(self, raw: dict) -> Transaction:
        return Transaction(
            hash=raw["hash"],
            block_number=raw["blockNumber"],
            timestamp=raw["timeStamp"],
            from_address=raw["from"],
            to_address=raw.get("to") or None,
            value_wei=raw["value"],
            gas_used=raw["gasUsed"],
            is_error=raw["isError"],
            contract_address=raw.get("contractAddress") or None,
        )
