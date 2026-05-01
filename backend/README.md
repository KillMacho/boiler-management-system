# Boiler Management Backend (FastAPI)

REST API проекта «Информационная система управления котельной установкой».

## Стек
- Python 3.11
- FastAPI 0.115 + Uvicorn
- SQLAlchemy 2.0 (async) + aioodbc/pyodbc
- ODBC Driver 18 for SQL Server
- Pydantic v2 + pydantic-settings
- python-jose + passlib[bcrypt] для JWT

## Подготовка окружения

### 1. Виртуальное окружение
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell
# или
.\.venv\Scripts\activate.bat   # cmd
```

### 2. Установка зависимостей
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

> Если `pyodbc` падает на сборке — установите [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (workload «Desktop development with C++»). На свежих pyodbc обычно есть готовые wheel-ы для Windows и компиляция не нужна.
>
> Если ODBC Driver 18 не установлен — скачайте с [Microsoft Download](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).

### 3. Конфигурация
Скопируйте пример и заполните секреты:
```powershell
copy .env.example .env
```
В `.env` уже подставлены значения для локального стенда (логин `app_backend`).

### 4. Создание администратора в БД
В корне репозитория есть `database/06_CreateAdminUser.sql` — заводит пользователя `admin` со всеми ролями. Запустите один раз:
```powershell
sqlcmd -S "localhost\SQLEXPRESS" -U sa -P "<ваш sa-пароль>" -C -i ../database/06_CreateAdminUser.sql
```
Логин: `admin`, пароль: `admin123`.

### 5. Запуск
```powershell
uvicorn app.main:app --reload --port 8000
```
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

### 6. Тесты
```powershell
pytest -v
```

## Структура

```
backend/
├── app/
│   ├── main.py             # FastAPI app + CORS + routers
│   ├── config.py           # Pydantic Settings из .env
│   ├── database.py         # Async engine + AsyncSession
│   ├── models/             # SQLAlchemy 2.0 ORM (39 таблиц)
│   ├── schemas/            # Pydantic v2 (Base/Create/Update/Response)
│   ├── routers/            # FastAPI APIRouter-ы
│   │   └── auth.py         # /api/auth/{login,refresh,logout,me}
│   ├── services/           # Бизнес-логика
│   │   └── auth_service.py # JWT, bcrypt, blacklist
│   ├── dependencies/       # Depends-классы
│   │   └── auth.py         # get_current_user, RoleChecker
│   └── utils/
└── tests/
    ├── conftest.py
    └── test_auth.py
```

## Эндпоинты аутентификации

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/auth/login` | Логин по `username`/`password` (form-data, OAuth2). Возвращает access + refresh |
| POST | `/api/auth/refresh` | Новый access по refresh-токену |
| POST | `/api/auth/logout` | Отзыв access-токена (in-memory blacklist) |
| GET | `/api/auth/me` | Информация о текущем пользователе |

## Роли (RBAC)
9 ролей из таблицы `roles`: `dispatcher`, `chief_engineer`, `master`, `brigade_leader`, `operator`, `storekeeper`, `accountant`, `hr_officer`, `employee`.
В роутерах используйте `Depends(RoleChecker(["chief_engineer", "master"]))`.
