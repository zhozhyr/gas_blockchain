# Gas Blockchain Monitoring System

## Описание проекта

Данный проект представляет собой систему мониторинга расхода газа на компрессорной станции с использованием **FastAPI,
SQLAlchemy, Alembic, Blockchain**, а также мониторинга через **Grafana и Prometheus**. Система детектирует аномалии
потребления газа и фиксирует транзакции в блокчейне.

## Основные компоненты

- **FastAPI** – основное API сервиса
- **PostgreSQL** – база данных
- **SQLAlchemy + Alembic** – работа с БД и миграции
- **Blockchain** – хранение транзакций
- **Prometheus + Grafana** – мониторинг и визуализация метрик
- **Kubernetes + Helm** – развертывание в кластере

## Запуск проекта (Docker Compose)

1. Клонировать репозиторий:
   ```sh
   git clone https://github.com/your-repo/gas-blockchain.git
   cd gas-blockchain
   ```
2. Собрать и запустить контейнеры:
   ```sh
   docker-compose up --build
   ```

### Остановка контейнеров:

   ```sh
   docker-compose down
   ```

## Развертывание мониторинга

Мониторинг включает **Prometheus** и **Grafana**. Запуск:

```sh
docker-compose -f docker-compose.monitoring.yml up -d
```

После запуска:

- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3000`

## Развертывание в Kubernetes

1. Установить Helm:
   ```sh
   choco install kubernetes-helm  # для Windows
   sudo apt install helm           # для Linux
   ```
2. Создать Helm-чарт:
   ```sh
   helm install gas-monitoring ./helm
   ```
3. Проверить статус:
   ```sh
   kubectl get pods
   ```
4. Открыть веб-интерфейс Grafana:
   ```sh
   kubectl port-forward svc/grafana 3000:3000
   ```

## API эндпоинты

| Метод  | URL                        | Описание                                                  |
|--------|----------------------------|-----------------------------------------------------------|
| `POST` | `/transactions/`           | Добавить транзакцию                                       |
| `GET`  | `/blockchain/`             | Получить цепочку блокчейна                                |
| `GET`  | `/blockchain/{block_hash}` | Получить данные блока                                     |
| `POST` | `/metrics`                 | Метрики для Prometheus                                    |
| `POST` | `/detect_anomaly`          | Определяет, является ли переданная транзакция аномальной. |




