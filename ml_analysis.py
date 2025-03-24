import numpy as np
import joblib
import os
import pandas as pd
import asyncio
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest

app = FastAPI()

MODEL_PATH = "anomaly_model.pkl"
DATA_PATH = "gas_data.csv"


async def generate_realistic_data():
    """Асинхронное создание и сохранение синтетических данных."""
    normal_data = []
    anomalies = []

    for _ in range(500):  # Нормальные случаи
        input_gas = np.random.uniform(5000, 10000)
        output_gas = input_gas * np.random.uniform(0.97, 0.99)  # Потери 1-3%
        self_consumption = np.random.uniform(50, 200)
        normal_data.append([input_gas, output_gas, self_consumption, 0])  # 0 = нормальное состояние

    for _ in range(10):  # Аномалии
        anomaly_type = np.random.choice(["low_output", "high_self_consumption", "negative_balance"])

        if anomaly_type == "low_output":
            input_gas = np.random.uniform(5000, 10000)
            output_gas = input_gas * np.random.uniform(0.5, 0.8)  # Слишком большие потери
            self_consumption = np.random.uniform(50, 200)

        elif anomaly_type == "high_self_consumption":
            input_gas = np.random.uniform(5000, 10000)
            output_gas = input_gas * np.random.uniform(0.97, 0.99)
            self_consumption = np.random.uniform(1000, 3000)  # Чрезмерный расход

        else:  # negative_balance
            input_gas = np.random.uniform(5000, 10000)
            output_gas = input_gas * np.random.uniform(1.01, 1.05)  # Ошибка учета
            self_consumption = np.random.uniform(50, 200)

        anomalies.append([input_gas, output_gas, self_consumption, 1])  # 1 = аномалия

    data = normal_data + anomalies

    df = pd.DataFrame(data, columns=["input_gas", "output_gas", "self_consumption", "is_anomaly"])

    # Асинхронная запись в CSV
    await asyncio.to_thread(df.to_csv, DATA_PATH, index=False)
    print(f"✅ Данные сохранены в {DATA_PATH}")


async def load_data():
    """Асинхронная загрузка данных из CSV."""
    if not os.path.exists(DATA_PATH):
        print("⚠️ Данных нет, создаем тестовый датасет...")
        await generate_realistic_data()

    df = await asyncio.to_thread(pd.read_csv, DATA_PATH)
    return df[["input_gas", "output_gas", "self_consumption"]].values


async def train_model():
    """Асинхронное обучение модели и сохранение в файл."""
    data = await load_data()
    model = IsolationForest(contamination=0.02, random_state=42)

    await asyncio.to_thread(model.fit, data)
    await asyncio.to_thread(joblib.dump, model, MODEL_PATH)

    print(f"✅ Модель обучена и сохранена в {MODEL_PATH}")


async def load_model():
    """Асинхронная загрузка модели."""
    if not os.path.exists(MODEL_PATH):
        await train_model()  # Если модели нет – обучаем

    return await asyncio.to_thread(joblib.load, MODEL_PATH)


async def detect_anomaly(input_data):
    """Асинхронная проверка данных на аномалии."""
    model = await load_model()
    data = np.array([input_data])
    result = await asyncio.to_thread(model.predict, data)  # -1 = аномалия, 1 = нормально
    return bool(result[0] == -1)


async def verify_token():
    """Фиктивная проверка токена (замени на реальную логику)."""
    await asyncio.sleep(0.1)  # Симуляция проверки
    return True
