FROM python:3.12-slim

ARG REQUIREMENTS_FILE=requirements.txt

WORKDIR /app


COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r ${REQUIREMENTS_FILE}

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY app/ ./app/
# чтоб на prod можно было загрузить тестовые данные
COPY scripts/ ./scripts/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
