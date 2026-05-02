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


async def add_viewing_to_sheet(telegram_id: int, prop_id: int, viewing_datetime: str):
    """Записать просмотр в Google Sheets."""
    try:
        sheet = get_sheet()
        all_ids = sheet.col_values(1)
        if str(telegram_id) in all_ids:
            row_num = all_ids.index(str(telegram_id)) + 1
            parts = viewing_datetime.split(" в ")
            date_str = parts[0].strip() if len(parts) > 0 else viewing_datetime
            time_str = parts[1].strip() if len(parts) > 1 else "—"
            sheet.update_cell(row_num, 7, str(prop_id) if prop_id else "—")
            sheet.update_cell(row_num, 8, date_str)
            sheet.update_cell(row_num, 9, time_str)
        else:
            row = [
                str(telegram_id), "—", "—", "—", "—", "—",
                str(prop_id) if prop_id else "—",
                viewing_datetime, "—",
            ]
            sheet.append_row(row)
    except Exception as e:
        print(f"[Sheets] Ошибка записи просмотра: {e}")
