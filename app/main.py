from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.etherscan import EtherscanClient, EtherscanError
from app.models import RiskScore, Transaction
from app.scoring import WalletRiskScorer


class Settings(BaseSettings):
    etherscan_api_key: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
etherscan = EtherscanClient(api_key=settings.etherscan_api_key)
scorer = WalletRiskScorer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await etherscan.close()


app = FastAPI(
    title="Blockchain Explorer API",
    description="Read and analyse Ethereum wallet activity via Etherscan.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/transactions/{address}", response_model=list[Transaction])
async def get_transactions(
    address: str,
    max_results: int = Query(default=100, ge=1, le=500),
):
    """
    Return the transaction history of an Ethereum address.
    """
    try:
        return await etherscan.get_transactions(address, max_results=max_results)
    except EtherscanError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/wallet/{address}/risk", response_model=RiskScore)
async def get_wallet_risk(address: str):
    """
    Score the risk profile of an Ethereum wallet based on its on-chain activity.
    """
    try:
        transactions = await etherscan.get_transactions(address, max_results=500)
    except EtherscanError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return scorer.score(address, transactions)


@app.get("/health")
async def health():
    return {"status": "ok"}
