# Информационная система управления котельными установками

Учебный проект — полноценная серверная часть для диспетчеризации котельных: мониторинг телеметрии в реальном времени, управление заявками и нарядами, кадровый учёт, складское хозяйство, регламентированная отчётность и интеграция с внешними системами (1С, ЭДО).

## Архитектура

```
BoilerManagementSystem/
├── backend/                     # FastAPI REST API (Python 3.11)
├── simulator/                   # Симулятор телеметрии 15 котельных
├── mock-services/
│   ├── onec-mock/               # Mock-сервер 1С (порт 8080)
│   └── edo-mock/                # Mock оператора ЭДО (порт 8081)
└── database/                    # SQL-скрипты (SQL Server / SQL Server Express)
```

## Стек технологий

| Компонент | Технологии |
|---|---|
| Backend | Python 3.11, FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 (async) |
| База данных | Microsoft SQL Server / SQL Server Express |
| Драйвер БД | aioodbc + pyodbc + ODBC Driver 18 for SQL Server |
| Аутентификация | JWT (python-jose), bcrypt (passlib), RBAC — 9 ролей |
| Интеграция | httpx, tenacity (retry с экспоненциальным откатом) |
| Отчётность | Jinja2-шаблоны XML, lxml (КНД-форматы ФНС) |
| Симулятор | asyncio, httpx, pydantic-settings |
| Mock-сервисы | FastAPI, API Key аутентификация |

## Быстрый старт

### 1. База данных

Запустите скрипты по порядку в SQL Server Management Studio или через `sqlcmd`:

```powershell
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -i database/01_CreateDatabase.sql
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -i database/02_CreateLogins.sql
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -d BoilerManagementDB -i database/03_CreateSchema.sql
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -d BoilerManagementDB -i database/04_CreateIndexes.sql
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -d BoilerManagementDB -i database/05_InsertTestData.sql
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -d BoilerManagementDB -i database/06_CreateAdminUser.sql
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -d BoilerManagementDB -i database/07_AddMonitoringIndex.sql
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -d BoilerManagementDB -i database/08_ExtendStatusConstraints.sql
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<пароль>" -C -d BoilerManagementDB -i database/09_AddRegulatoryReportsTable.sql
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # и заполните секреты
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

### 3. Симулятор телеметрии

```powershell
cd simulator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main --boilers 15 --interval 30
```

### 4. Mock-сервисы (опционально)

**Mock 1С** (порт 8080):
```powershell
cd mock-services/onec-mock
pip install -r requirements.txt
uvicorn app.main:app --port 8080
```

**Mock ЭДО** (порт 8081):
```powershell
cd mock-services/edo-mock
pip install -r requirements.txt
uvicorn app.main:app --port 8081
```

## API — основные разделы

| Тег | Префикс | Описание |
|---|---|---|
| auth | `/api/auth` | Логин, обновление токена, выход, профиль |
| boilers | `/api/v1/boilers` | Котельные и оборудование (CRUD) |
| telemetry | `/api/v1/telemetry` | Приём телеметрии, история, текущие показания |
| monitoring | `/api/v1/monitoring` | Статусы котельных, активные аварии, пороговые значения |
| requests | `/api/v1/requests` | Заявки на обслуживание (CRUD + смена статуса) |
| work-orders | `/api/v1/work-orders` | Наряды, старт/завершение, фото, чек-лист |
| maintenance | `/api/v1/maintenance` | Типы ТО, регламенты, расписания, план |
| warehouse | `/api/v1/warehouse` | Материалы, склады, движения, заявки на закупку |
| personnel | `/api/v1/personnel` | Сотрудники, бригады, квалификации, табель |
| customers | `/api/v1/customers` | Клиенты (CRUD) |
| reporting | `/api/v1/reporting` | Генерация XML-отчётов (6-НДФЛ, РСВ, 4-ФСС, СЗВ-СТАЖ) и отправка в ЭДО |
| integration | `/api/v1/integration` | Синхронизация с 1С |
| audit | `/api/v1/audit` | Журнал действий |
| lookups | `/api/v1/lookups` | Справочники (read-only) |

## Роли (RBAC)

9 ролей: `dispatcher`, `chief_engineer`, `master`, `brigade_leader`, `operator`, `storekeeper`, `accountant`, `hr_officer`, `employee`.

Учётная запись администратора для разработки: логин `admin`, пароль `admin123`.

## Мониторинг и автоматические заявки

При получении телеметрии с критическими значениями параметров система автоматически создаёт аварийную заявку (тип «Авария», источник `monitoring`). Дедупликация: если по данной котельной уже есть открытая аварийная заявка — новая не создаётся.

Пороговые значения настраиваются через `POST /api/v1/monitoring/thresholds` (роль `chief_engineer` или `dispatcher`).

## Регламентированная отчётность

Поддерживаемые формы ФНС:

| Форма | Период | Формат |
|---|---|---|
| 6-НДФЛ | YYYY-QN (квартал) | XML КНД 1151100, версия 5.04 |
| РСВ | YYYY-QN (квартал) | XML КНД 1151111 |
| 4-ФСС | YYYY-QN (квартал) | XML КНД 1151001 |
| СЗВ-СТАЖ | YYYY (год) | XML |

Отчёты генерируются через `POST /api/v1/reporting/generate` и отправляются оператору ЭДО через `POST /api/v1/reporting/submit`. При недоступности ЭДО возвращается `502 Bad Gateway`.

## Симулятор — сценарии аварий

| Сценарий | Параметры | Реакция backend |
|---|---|---|
| `overheat` | temperature_heat > 110°C | status=critical, автозаявка «Авария» |
| `leak` | pressure < 0.09 МПа, низкий уровень воды | status=critical, автозаявка «Авария» |
| `co_spike` | co_level > 55 мг/м³ | status=critical, автозаявка «Авария» |
| `draft_failure` | furnace_draft ≈ 0 Па | status=critical, автозаявка «Авария» |
| `low_water` | water_level < 145 мм | status=critical, автозаявка «Авария» |

## Тесты

```powershell
# Backend (97 тестов: 93 проходят, 4 пропускаются)
cd backend
python -m pytest tests/ -v

# Mock ЭДО (15 тестов)
cd mock-services/edo-mock
python -m pytest tests/ -v

# Симулятор
cd simulator
python -m pytest tests/ -v
```

## Структура базы данных

39 таблиц. Ключевые сущности:

- **boilers** — котельные установки
- **equipment** — оборудование котельной (привязано к котельной)
- **telemetry** — показания датчиков (7 параметров: температура подачи/обратки, давление, СО, газ, уровень воды, тяга)
- **monitoring_thresholds** — пороги предупреждений и критических значений
- **requests** — заявки на обслуживание
- **work_orders** — наряды-задания
- **brigades / employees** — бригады и сотрудники
- **materials / material_stock / material_movements** — складской учёт
- **timesheets** — табель рабочего времени
- **regulatory_reports** — сформированные регламентированные отчёты

## История разработки

| День | Что сделано |
|---|---|
| 1 | Схема БД SQL Server — 39 таблиц, тестовые данные (15 котельных) |
| 2 | Backend-инфраструктура: ORM-модели, Pydantic v2 схемы, JWT-аутентификация |
| 3 | CRUD-эндпоинты (12 роутеров), приём телеметрии, мониторинг пороговых значений |
| 4 | Бизнес-логика: назначение бригад, планирование ТО, складской сервис, табель |
| 5 | Симулятор телеметрии 15 котельных с 5 сценариями аварий |
| 6 | Mock-сервер 1С + реальный `OneCClient` (httpx + tenacity) |
| 7 | Mock оператора ЭДО + модуль регламентированной отчётности (XML КНД) |
