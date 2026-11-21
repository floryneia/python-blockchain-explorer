import pytest
import httpx
from pytest_httpx import HTTPXMock

from app.etherscan import EtherscanClient, EtherscanError


ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

SAMPLE_TX = {
    "hash": "0xabc123",
    "blockNumber": "18000000",
    "timeStamp": "1700000000",
    "from": ADDRESS,
    "to": "0xContractA",
    "value": "1000000000000000000",
    "gasUsed": "21000",
    "isError": "0",
    "contractAddress": "",
}


@pytest.fixture
async def client():
    c = EtherscanClient(api_key="test_key")
    yield c
    await c.close()


@pytest.mark.asyncio
async def test_get_transactions_success(httpx_mock: HTTPXMock, client):
    httpx_mock.add_response(
        json={"status": "1", "message": "OK", "result": [SAMPLE_TX]}
    )
    txs = await client.get_transactions(ADDRESS)
    assert len(txs) == 1
    assert txs[0].hash == "0xabc123"
    assert txs[0].value_wei == 1_000_000_000_000_000_000
    assert txs[0].is_error is False


@pytest.mark.asyncio
async def test_get_transactions_empty_wallet(httpx_mock: HTTPXMock, client):
    httpx_mock.add_response(
        json={"status": "0", "message": "No transactions found", "result": []}
    )
    txs = await client.get_transactions(ADDRESS)
    assert txs == []


@pytest.mark.asyncio
async def test_get_transactions_api_error(httpx_mock: HTTPXMock, client):
    httpx_mock.add_response(
        json={"status": "0", "message": "NOTOK", "result": "Invalid API Key"}
    )
    with pytest.raises(EtherscanError, match="Invalid API Key"):
        await client.get_transactions(ADDRESS)


@pytest.mark.asyncio
async def test_transaction_parsing(httpx_mock: HTTPXMock, client):
    tx_with_error = {**SAMPLE_TX, "isError": "1", "hash": "0xfailed"}
    httpx_mock.add_response(
        json={"status": "1", "message": "OK", "result": [tx_with_error]}
    )
    txs = await client.get_transactions(ADDRESS)
    assert txs[0].is_error is True


@pytest.mark.asyncio
async def test_contract_creation_tx(httpx_mock: HTTPXMock, client):
    contract_tx = {**SAMPLE_TX, "to": "", "contractAddress": "0xNewContract"}
    httpx_mock.add_response(
        json={"status": "1", "message": "OK", "result": [contract_tx]}
    )
    txs = await client.get_transactions(ADDRESS)
    assert txs[0].to_address is None
    assert txs[0].contract_address == "0xNewContract"
