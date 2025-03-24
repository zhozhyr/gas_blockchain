from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ValidationError
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from database import BlockReference, get_db
from ml_analysis import detect_anomaly
from blockchain import Blockchain, Transaction as BlockchainTransaction
from collections import defaultdict
import os
import logging
import asyncio
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="Gas Balance Blockchain API",
    description="API для учета газового баланса с использованием блокчейна",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Инициализация блокчейна
blockchain = Blockchain()
security = HTTPBearer()

API_TOKEN = os.getenv("API_TOKEN", "securetoken")

# Метрики
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["endpoint"])


# Middleware для логирования запросов
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
        with REQUEST_LATENCY.labels(endpoint=request.url.path).time():
            response = await call_next(request)
        return response


app.add_middleware(MetricsMiddleware)


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API Token")


# Модель для API
class APITransaction(BaseModel):
    station_id: str
    input_gas: float
    output_gas: float
    self_consumption: float


# Эндпоинты
@app.get("/metrics/", dependencies=[Depends(verify_token)], tags=["Metrics"])
async def get_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/transactions/", dependencies=[Depends(verify_token)], tags=["Transactions"])
async def add_transaction(transaction: APITransaction, db: AsyncSession = Depends(get_db)):
    try:
        logging.info(f"Received transaction: {transaction}")

        # Добавляем корректные данные в блокчейн
        blockchain.pending_transactions.append(
            BlockchainTransaction(
                sender=transaction.station_id,
                receiver="blockchain",
                amount=transaction.input_gas + transaction.output_gas + transaction.self_consumption,
                input_gas=transaction.input_gas,
                output_gas=transaction.output_gas,
                self_consumption=transaction.self_consumption,
                signature=None
            )
        )

        # Майним блок с накопленными транзакциями
        new_block = await blockchain.add_block()

        # Записываем в базу данных
        block_ref = BlockReference(block_hash=new_block.hash)
        db.add(block_ref)
        await db.commit()

        logging.info(f"New block created: {new_block.hash}")

        return {"message": "Transaction added successfully", "block_hash": new_block.hash}

    except Exception as e:
        logging.critical(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get("/blockchain/", dependencies=[Depends(verify_token)])
async def get_blockchain():
    return {"chain_length": len(blockchain.chain), "blocks": [block.hash for block in blockchain.chain]}


@app.get(
    "/blockchain/{block_hash}",
    dependencies=[Depends(verify_token)],
    tags=["Blockchain"],
    summary="Получить данные блока",
    description="Возвращает данные блока по его хэшу."
)
async def get_block(block_hash: str):
    try:
        block = next((b for b in blockchain.chain if b.hash == block_hash), None)
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")

        logging.info(f"Fetching block: {block_hash}")

        # Логируем все транзакции в блоке
        for tx in block.transactions:
            logging.info(
                f"TX: sender={tx.sender}, input={getattr(tx, 'input_gas', 0)}, "
                f"output={getattr(tx, 'output_gas', 0)}, "
                f"self={getattr(tx, 'self_consumption', 0)}")

        # Агрегируем данные по station_id
        station_data = defaultdict(lambda: {"input_gas": 0, "output_gas": 0, "self_consumption": 0})
        for tx in block.transactions:
            station_data[tx.sender]["input_gas"] += getattr(tx, "input_gas", 0)
            station_data[tx.sender]["output_gas"] += getattr(tx, "output_gas", 0)
            station_data[tx.sender]["self_consumption"] += getattr(tx, "self_consumption", 0)

        logging.info(f"Aggregated transactions: {station_data}")

        return {
            "index": block.index,
            "timestamp": block.timestamp,
            "transactions": [
                {"station_id": station, **data} for station, data in station_data.items()
            ],
            "hash": block.hash,
            "previous_hash": block.previous_hash
        }
    except Exception as e:
        logging.critical(f"Error fetching block: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


class GasData(BaseModel):
    input_gas: float
    output_gas: float
    self_consumption: float


@app.post("/detect_anomaly/", dependencies=[Depends(verify_token)], tags=["Anomaly Detection"])
async def detect_anomaly_endpoint(data: GasData):
    """Эндпоинт для обнаружения аномалий."""
    result = await detect_anomaly([data.input_gas, data.output_gas, data.self_consumption])
    return {"is_anomaly": result}


@app.get("/", tags=["General"])
async def root():
    return {"message": "Gas Balance Blockchain API", "status": "running"}
