import gspread
from google.oauth2.service_account import Credentials
import pandas as pd


class GSheetConnector:
    def __init__(self, creds_path: str = "credentials.json"):
        creds = Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        self.client = gspread.authorize(creds)

    def get_sheet(self, ID: str):
        return self.client.open_by_key(ID)


def sheet2pandas(worksheet: gspread.Worksheet) -> tuple[pd.DataFrame, int]:
    # Читаем данные
    data = worksheet.get_all_values()
    # Определяем строку начиная с которой идет таблица
    first_line = next(n for n, v in enumerate(data) if v[0] == "Имя")
    data = pd.DataFrame(data[first_line + 1 :], columns=data[first_line])
    return (data, first_line)
