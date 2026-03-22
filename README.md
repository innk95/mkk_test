# mkk_test

REST API на FastAPI + SQLAlchemy (async) + PostgreSQL.

## Стек

- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0** (asyncio) + **asyncpg** — асинхронная работа с БД
- **PostgreSQL** — база данных
- **Alembic** — миграции (использует psycopg2, sync)
- **Uvicorn** — ASGI-сервер

## Сервисы (Docker Compose)

| Сервис | Профиль | Описание |
|---|---|---|
| `api` | `prod`, `dev` | FastAPI-приложение (собирается из `Dockerfile`) |
| `postgres` | `prod`, `dev` | PostgreSQL, данные хранятся в volume `postgres_data` |
| `migrate` | `prod` | Накатывает миграции через `alembic upgrade head` |
| `seed` | `seed` | Заполняет БД тестовыми данными |

## Запуск

### Продакшн

```bash
docker compose --profile prod up --build
```

### Разработка

```bash
docker compose --profile dev up --build
```

Интерактивная документация: `http://localhost:8000/docs`
### X-API-KEY для тестирования:
> prod - your_api_key;
> dev - testkey


## API

| Метод | Путь | Описание |
|---|---|---|
| GET | `/healthcheck` | Проверка работоспособности |
| GET | `/buildings` | Список всех зданий |
| GET | `/buildings/{id}/organizations` | Организации в здании |
| GET | `/organizations` | Список организаций (фильтры: name, радиус, bbox) |
| GET | `/organizations/{id}` | Организация по ID |
| GET | `/activities/tree` | Дерево видов деятельности |
| GET | `/activities/{id}/organizations` | Организации по виду деятельности (включая подкатегории) |

### Query-параметры для `GET /organizations`

| Параметр | Описание |
|---|---|
| `name` | Поиск по названию (ILIKE) |
| `lat`, `lon`, `radius_km` | Фильтр по радиусу |
| `lat_min`, `lat_max`, `lon_min`, `lon_max` | Фильтр по прямоугольной области |

Параметры радиуса и bbox взаимоисключающие — радиус имеет приоритет.

## Миграции

```bash
# Применить миграции (локально)
alembic upgrade head

# Создать новую миграцию
alembic revision --autogenerate -m "description"
```

Через Docker:

```bash
docker compose --profile prod up migrate
```

## Наполнение БД тестовыми данными

> [!WARNING]
> Команда полностью очищает всю БД и добавляет новые тестовые записи

Если postgres уже запущен и миграции накатаны:

```bash
docker compose --profile prod --profile seed up seed
```

Если нужно всё с нуля (запустит postgres, migrate, seed и api):

```bash
docker compose --profile prod --profile seed up --build
```


## Остановка

```bash
docker compose down
```
