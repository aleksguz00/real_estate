import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SHEET_ID = "1qLTfGYzFqCe5etYWeb5fYpDP_CJfQ5UBUKiU9Sed48E"
CREDENTIALS_FILE = "api_google.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

async def add_user_to_sheet(telegram_id: int, name: str, username: str = None, phone: str = None, lang: str = None):
    """Добавить пользователя в Google Sheets.
    Колонки: TG ID | Имя | Username | Телефон | Язык | Дата регистрации | Id объекта | Дата просмотра | Время просмотра
    """
    try:
        sheet = get_sheet()
        all_ids = sheet.col_values(1)
        if str(telegram_id) in all_ids:
            return  # уже записан

        row = [
            str(telegram_id),
            name or "—",
            f"@{username}" if username else "—",
            phone or "—",
            lang or "—",
            datetime.now().strftime("%d.%m.%Y %H:%M"),
            "—",  # Id объекта
            "—",  # Дата просмотра
            "—",  # Время просмотра
        ]
        sheet.append_row(row)
    except Exception as e:
        print(f"[Sheets] Ошибка: {e}")


async def add_viewing_to_sheet(client_id: int, prop_id: int, datetime_str: str):
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        from datetime import datetime

        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "api_google.json", scope
        )
        client = gspread.authorize(creds)

        CLIENTS_SHEET_ID = "1qLTfGYzFqCe5etYWeb5fYpDP_CJfQ5UBUKiU9Sed48E"
        spreadsheet = client.open_by_key(CLIENTS_SHEET_ID)

        # 1. Обновляем колонки G и H в таблице клиентов (последний просмотр)
        clients_sheet = spreadsheet.sheet1
        col_a = clients_sheet.col_values(1)
        row = None
        for i, val in enumerate(col_a):
            if str(val).strip() == str(client_id).strip():
                row = i + 1
                break

        if row:
            try:
                dt = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
                date_str = dt.strftime("%d.%m.%Y")
                time_str = dt.strftime("%H:%M")
            except Exception:
                date_str = datetime_str
                time_str = ""

            clients_sheet.update_cell(row, 7, date_str)   # G — дата просмотра
            clients_sheet.update_cell(row, 8, time_str)   # H — время просмотра

        # 2. Добавляем новую строку в лист "Просмотры"
        viewings_sheet = spreadsheet.worksheet("Просмотры")

        from db import pool
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT full_name, username, phone FROM users WHERE telegram_id=$1",
                client_id
            )
            prop = await conn.fetchrow(
                "SELECT source_code, address FROM properties WHERE id=$1",
                prop_id
            ) if prop_id else None

        client_name = user["full_name"] if user else str(client_id)
        client_phone = user["phone"] if user and user["phone"] else ""
        prop_info = f"{prop['source_code']} | {prop['address']}" if prop else ""

        try:
            dt = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
            date_str = dt.strftime("%d.%m.%Y")
            time_str = dt.strftime("%H:%M")
        except Exception:
            date_str = datetime_str
            time_str = ""

        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        viewings_sheet.append_row([
            now,                  # A — Дата записи
            str(client_id),       # B — Telegram ID
            client_name,          # C — Имя клиента
            client_phone or "",   # D — Телефон
            prop_info,            # E — Объект
            date_str,             # F — Дата просмотра
            time_str,             # G — Время просмотра
            "Назначен",           # H — Статус
        ])

        print(f"DEBUG add_viewing_to_sheet: OK client={client_id} prop={prop_id}")

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"add_viewing_to_sheet error: {e}")


OWNERS_SHEET_ID = "1C7asDz3U8xJ-eysVpGmEiZms-SvpDJWN8CJTO1zj8tk"


async def get_owner_phone(source_code: str, deal_type: str) -> str | None:
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        import asyncio

        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("api_google.json", scope)
        client = gspread.authorize(creds)

        sheet_name = "АРЕНДА" if deal_type == "rent" else "ПРОДАЖА"
        sheet = client.open_by_key(OWNERS_SHEET_ID).worksheet(sheet_name)

        cell = sheet.find(source_code)
        if cell:
            phone = sheet.cell(cell.row, 4).value  # колонка D
            return phone if phone else None
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"get_owner_phone error: {e}")
    return None


async def update_client_contact(telegram_id: int, phone: str | None):
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        from datetime import datetime

        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "api_google.json", scope
        )
        client = gspread.authorize(creds)

        CLIENTS_SHEET_ID = "1qLTfGYzFqCe5etYWeb5fYpDP_CJfQ5UBUKiU9Sed48E"
        sheet = client.open_by_key(CLIENTS_SHEET_ID).sheet1

        col_a = sheet.col_values(1)
        row = None
        for i, val in enumerate(col_a):
            if str(val).strip() == str(telegram_id).strip():
                row = i + 1
                break

        if not row:
            print(f"DEBUG update_client_contact: {telegram_id} не найден")
            return

        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        if phone:
            sheet.update_cell(row, 4, str(phone))   # колонка D
        sheet.update_cell(row, 6, now)               # колонка F — дата обращения

        print(f"DEBUG update_client_contact OK: row={row} phone={phone} date={now}")

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"update_client_contact error: {e}")
