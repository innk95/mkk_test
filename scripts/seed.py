"""
Скрипт наполнения БД тестовыми данными.
ВНИМАНИЕ!!!
Перед каждым запуском очищает все таблицы и создаёт записи заново.
ВНИМАНИЕ!!!

Запуск:
    python -m scripts.seed
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.activity import Activity
from app.models.building import Building
from app.models.organization import (
    Organization,
    OrganizationPhone,
    organization_activity,
)

_DB_URL = (
    os.getenv("DATABASE_URL", "postgresql://mkk_user:mkk_password@localhost:5432/mkk")
    # Alembic и seed используют синхронный движок — убираем async-драйвер если он есть
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("postgresql+aiopg://", "postgresql://")
)

engine = create_engine(_DB_URL)
SessionLocal = sessionmaker(engine)

# ---------------------------------------------------------------------------
# Тестовые данные
# ---------------------------------------------------------------------------

# Трёхуровневое дерево: { категория: { подкатегория: [конкретный вид] } }
ACTIVITY_TREE: dict[str, dict[str, list[str]]] = {
    "Продукты питания": {
        "Молочная продукция": ["Молоко и сливки", "Сыры", "Йогурты и кефир"],
        "Мясная продукция": ["Говядина и телятина", "Свинина", "Птица"],
        "Хлебобулочные изделия": ["Хлеб", "Выпечка и торты"],
        "Напитки": ["Безалкогольные напитки", "Алкогольная продукция"],
    },
    "Транспорт": {
        "Грузовые перевозки": ["Межгородские грузоперевозки", "Городская доставка"],
        "Пассажирские перевозки": ["Такси", "Автобусные маршруты"],
        "Автосервис": ["Шиномонтаж", "Кузовной ремонт", "Техническое обслуживание"],
    },
    "Образование": {
        "Дошкольное образование": ["Ясли", "Детские сады"],
        "Среднее образование": ["Общеобразовательные школы", "Лицеи и гимназии"],
        "Дополнительное образование": ["Курсы иностранных языков", "IT-курсы", "Спортивные секции"],
    },
    "Медицина и здоровье": {
        "Стоматология": ["Терапевтическая стоматология", "Ортодонтия", "Имплантация"],
        "Поликлиники": ["Терапия", "Педиатрия", "Хирургия"],
        "Аптеки и оптика": ["Аптеки", "Оптические салоны"],
    },
    "IT и технологии": {
        "Разработка ПО": ["Веб-разработка", "Мобильная разработка", "Корпоративные системы"],
        "Техническая поддержка": ["Обслуживание ПК", "Сетевое администрирование"],
        "Продажа и ремонт техники": ["Продажа электроники", "Ремонт смартфонов"],
    },
}

BUILDINGS_DATA = [
    ("г. Москва, ул. Ленина, 1", 55.7558, 37.6173),
    ("г. Москва, ул. Арбат, 12", 55.7520, 37.5920),
    ("г. Москва, Тверская ул., 7", 55.7640, 37.6055),
    ("г. Москва, ул. Пречистенка, 3", 55.7455, 37.5973),
    ("г. Москва, Проспект Мира, 54", 55.7870, 37.6370),
    ("г. Санкт-Петербург, Невский просп., 28", 59.9342, 30.3351),
    ("г. Санкт-Петербург, ул. Рубинштейна, 15", 59.9293, 30.3445),
    ("г. Санкт-Петербург, Лиговский просп., 40", 59.9263, 30.3602),
    ("г. Екатеринбург, ул. Малышева, 51", 56.8366, 60.6122),
    ("г. Екатеринбург, просп. Ленина, 24/8", 56.8352, 60.5957),
    ("г. Новосибирск, Красный просп., 17", 55.0283, 82.9210),
    ("г. Новосибирск, ул. Депутатская, 46", 55.0421, 82.9478),
    ("г. Казань, ул. Баумана, 9", 55.7961, 49.1082),
    ("г. Казань, просп. Победы, 5", 55.8023, 49.1234),
    ("г. Нижний Новгород, ул. Большая Покровская, 13", 56.3257, 44.0060),
    ("г. Нижний Новгород, просп. Ленина, 25", 56.3187, 43.9924),
    ("г. Челябинск, ул. Кирова, 88", 55.1598, 61.4022),
    ("г. Самара, ул. Куйбышева, 112", 53.1870, 50.1168),
    ("г. Ростов-на-Дону, просп. Будённовский, 2", 47.2355, 39.7015),
    ("г. Уфа, просп. Октября, 132/3", 54.7388, 55.9721),
    ("г. Красноярск, просп. Мира, 10", 56.0153, 92.8932),
    ("г. Пермь, ул. Ленина, 58", 58.0105, 56.2502),
    ("г. Воронеж, просп. Революции, 30", 51.6755, 39.2089),
    ("г. Омск, ул. Ленина, 3", 54.9885, 73.3682),
    ("г. Волгоград, просп. Ленина, 15", 48.7071, 44.5170),
]

ORGANIZATION_NAMES = [
    'ООО "Рога и Копыта"', 'АО "ТехноСтрой"', 'ИП Иванов А.В.',
    'ООО "МегаФуд"', 'ЗАО "АвтоЛайн"', 'ООО "ЭдуПлюс"',
    'ООО "МедЦентр"', 'АО "СтройМастер"', 'ООО "ДигиТех"',
    'ООО "ФинансГрупп"', 'ИП Петрова М.С.', 'ООО "ТоргХаус"',
    'АО "ПродуктMart"', 'ООО "ТрансЛогик"', 'ООО "АкадемияЗнаний"',
    'ООО "ВитаМед"', 'АО "РемонтПрофи"', 'ООО "КодСтудия"',
    'ООО "СтрахБезопасность"', 'ИП Сидоров К.Д.', 'ООО "МаркетПлюс"',
    'АО "ГрузоВоз"', 'ООО "ДетскийМир"', 'ООО "АптекаПлюс"',
    'ООО "ДизайнБюро"',
]

PHONE_PREFIXES = [
    "8-800", "8-900", "8-905", "8-910", "8-916", "8-921",
    "8-923", "8-950", "8-960", "8-963",
]


def random_phone() -> str:
    prefix = random.choice(PHONE_PREFIXES)
    part1 = random.randint(100, 999)
    part2 = random.randint(10, 99)
    part3 = random.randint(10, 99)
    return f"{prefix}-{part1}-{part2}-{part3}"


# ---------------------------------------------------------------------------
# Очистка
# ---------------------------------------------------------------------------

def truncate_all(session: Session) -> None:
    session.execute(text(
        "TRUNCATE organization_activity, organization_phones, "
        "organizations, buildings, activities RESTART IDENTITY CASCADE"
    ))
    session.commit()
    print("Таблицы очищены.")


# ---------------------------------------------------------------------------
# Создание записей
# ---------------------------------------------------------------------------

def seed_activities(session: Session) -> list[Activity]:
    """Создаёт трёхуровневое дерево активностей. path проставляется триггером."""
    all_activities: list[Activity] = []

    for root_name, subcategories in ACTIVITY_TREE.items():
        # Уровень 1 - корневая категория
        root = Activity(name=root_name)
        session.add(root)
        session.flush()  # получаем id → триггер проставит path

        for sub_name, leaves in subcategories.items():
            # Уровень 2 - подкатегория
            sub = Activity(name=sub_name, parent_id=root.id)
            session.add(sub)
            session.flush()  # триггер: path = root.path || sub.id

            for leaf_name in leaves:
                # Уровень 3 - конкретный вид деятельности
                leaf = Activity(name=leaf_name, parent_id=sub.id)
                session.add(leaf)
                all_activities.append(leaf)

            all_activities.append(sub)
        all_activities.append(root)

    session.flush()  # триггер проставит path для всех листьев
    print(f"Активности: {len(all_activities)} записей (3 уровня вложенности).")
    return all_activities


def seed_buildings(session: Session) -> list[Building]:
    buildings = []
    for address, lat, lng in BUILDINGS_DATA:
        b = Building(
            address=address,
            latitude=round(lat + random.uniform(-0.005, 0.005), 6),
            longitude=round(lng + random.uniform(-0.005, 0.005), 6),
        )
        session.add(b)
        buildings.append(b)

    session.flush()
    print(f"Здания: {len(buildings)} записей.")
    return buildings


def seed_organizations(
    session: Session,
    buildings: list[Building],
    activities: list[Activity],
) -> None:
    total_phones = 0

    for i, name in enumerate(ORGANIZATION_NAMES):
        org = Organization(
            name=name, building_id=buildings[i % len(buildings)].id
        )
        session.add(org)
        session.flush()

        phone_count = random.randint(2, 4)
        for _ in range(phone_count):
            session.add(
                OrganizationPhone(organization_id=org.id, phone=random_phone())
            )
        total_phones += phone_count

        org_activities = random.sample(activities, k=random.randint(2, 4))
        session.execute(
            organization_activity.insert(),
            [
                {"organization_id": org.id, "activity_id": a.id}
                for a in org_activities
            ],
        )

    session.flush()
    print(f"Организации: {len(ORGANIZATION_NAMES)} записей.")
    print(f"Телефоны: {total_phones} записей.")


def main() -> None:
    random.seed(42)
    with SessionLocal() as session:
        try:
            truncate_all(session)
            activities = seed_activities(session)
            buildings = seed_buildings(session)
            seed_organizations(session, buildings, activities)
            session.commit()
            print("База данных успешно заполнена.")
        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    main()
