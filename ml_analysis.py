import numpy as np
import joblib
import os
import pandas as pd
from sklearn.ensemble import IsolationForest

MODEL_PATH = "anomaly_model.pkl"
DATA_PATH = "gas_data.csv"


def generate_realistic_data():
    """Создает синтетические данные и сохраняет их в CSV."""
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

    # Сохраняем в CSV
    df = pd.DataFrame(data, columns=["input_gas", "output_gas", "self_consumption", "is_anomaly"])
    df.to_csv(DATA_PATH, index=False)
    print(f"✅ Данные сохранены в {DATA_PATH}")


def load_data():
    """Загружает данные из CSV-файла, если он есть, иначе генерирует."""
    if not os.path.exists(DATA_PATH):
        print("⚠️ Данных нет, создаем тестовый датасет...")
        generate_realistic_data()

    df = pd.read_csv(DATA_PATH)
    return df[["input_gas", "output_gas", "self_consumption"]].values


def train_model():
    """Обучает и сохраняет модель на данных из файла."""
    data = load_data()
    model = IsolationForest(contamination=0.02, random_state=42)
    model.fit(data)
    joblib.dump(model, MODEL_PATH)
    print(f"✅ Модель обучена и сохранена в {MODEL_PATH}")


def load_model():
    """Загружает модель из файла."""
    if not os.path.exists(MODEL_PATH):
        train_model()  # Если модели нет – обучаем
    return joblib.load(MODEL_PATH)


def detect_anomaly(input_data):
    """Проверяет данные на аномалии и возвращает bool."""
    model = load_model()
    result = model.predict([input_data])  # -1 = аномалия, 1 = нормально
    return bool(result[0] == -1)  # Преобразуем numpy.bool_ в стандартный bool
