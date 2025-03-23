from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ValidationError
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from database import BlockReference, get_db
from ml_analysis import detect_anomaly
from sqlalchemy.orm import Session
from blockchain import Blockchain
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="Gas Balance Blockchain API",
    description="API для учета газового баланса с использованием блокчейна",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API Token")


# Эндпоинт для Prometheus
@app.get(
    "/metrics/",
    dependencies=[Depends(verify_token)],
    tags=["Metrics"],
    summary="Получить метрику для Prometheus",
    description="Получить метрику для Prometheus "
)
def get_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class Transaction(BaseModel):
    station_id: str
    input_gas: float
    output_gas: float
    self_consumption: float


@app.post(
    "/transactions/",
    dependencies=[Depends(verify_token)],
    tags=["Transactions"],
    summary="Добавить новую транзакцию",
    description="Записывает новую транзакцию в блокчейн и сохраняет её хэш в БД."
)
def add_transaction(transaction: Transaction, db: Session = Depends(get_db)):
    try:
        if transaction.input_gas < 0 or transaction.output_gas < 0 or transaction.self_consumption < 0:
            logging.error("Invalid transaction data: negative gas values")
            raise HTTPException(status_code=400, detail="Gas values must be non-negative")

        is_anomaly = detect_anomaly([transaction.input_gas, transaction.output_gas, transaction.self_consumption])

        new_block = blockchain.add_block({
            "station_id": transaction.station_id,
            "input_gas": transaction.input_gas,
            "output_gas": transaction.output_gas,
            "self_consumption": transaction.self_consumption,
            "is_anomaly": is_anomaly
        })

        block_ref = BlockReference(block_hash=new_block.hash)
        db.add(block_ref)
        db.commit()

        logging.info(f"Transaction added for station {transaction.station_id}")
        return {"message": "Transaction added and recorded in blockchain successfully", "block_hash": new_block.hash}
    except ValidationError as e:
        logging.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.critical(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get(
    "/blockchain/",
    dependencies=[Depends(verify_token)],
    tags=["Blockchain"],
    summary="Получить текущий блокчейн",
    description="Возвращает список хэшей блоков, хранящихся в БД."
)
def get_blockchain(db: Session = Depends(get_db)):
    try:
        block_references = db.query(BlockReference).all()
        logging.info("Blockchain data retrieved")
        return block_references
    except Exception as e:
        logging.critical(f"Error fetching blockchain: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get(
    "/blockchain/{block_hash}",
    dependencies=[Depends(verify_token)],
    tags=["Blockchain"],
    summary="Получить данные блока",
    description="Возвращает данные блока по его хэшу."
)
def get_block(block_hash: str, db: Session = Depends(get_db)):
    try:
        block = blockchain.get_block_by_hash(block_hash)
        if block:
            # Блок найден в блокчейне — возвращаем все данные
            return {
                "block_hash": block.hash,
                "timestamp": block.timestamp,
                "station_id": block.data["station_id"],
                "input_gas": block.data["input_gas"],
                "output_gas": block.data["output_gas"],
                "self_consumption": block.data["self_consumption"],
                "gas_difference": block.data["input_gas"] - (block.data["output_gas"] + block.data["self_consumption"])
            }

        # Если блока нет в блокчейне, но есть в БД
        block_ref = db.query(BlockReference).filter(BlockReference.block_hash == block_hash).first()
        if not block_ref:
            raise HTTPException(status_code=404, detail="Block not found")

        return {
            "block_hash": block_ref.block_hash,
            "timestamp": block_ref.timestamp,
            "message": "Block stored in DB but no gas data available"
        }

    except Exception as e:
        logging.critical(f"Error fetching block: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.post(
    "/detect_anomaly/",
    dependencies=[Depends(verify_token)],
    tags=["Anomaly Detection"],
    summary="Проверка данных на аномалии",
    description="Определяет, является ли переданная транзакция аномальной."
)
def check_anomaly(transaction: Transaction):
    is_anomaly = detect_anomaly([transaction.input_gas, transaction.output_gas, transaction.self_consumption])
    return {"station_id": transaction.station_id, "is_anomaly": is_anomaly}


@app.get(
    "/",
    tags=["General"],
    summary="Статус API",
    description="Возвращает сообщение о работоспособности API."
)
def root():
    return {"message": "Gas Balance Blockchain API"}
