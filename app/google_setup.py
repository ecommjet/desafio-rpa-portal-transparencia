"""Setup interativo executado pelo usuário: OAuth e recursos dedicados ao desafio."""
import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import Settings
from app.google_export import HEADERS, SCOPES, google_services
from app.storage import save_json


def main():
    parser = argparse.ArgumentParser(description="Conectar Google e criar pasta/planilha dedicadas")
    parser.add_argument("--client-secrets", type=Path, default=Path("secrets/client.json"))
    parser.add_argument("--token", type=Path, default=Path("secrets/google-token.json"))
    parser.add_argument("--resources", type=Path, default=Path("secrets/google-resources.json"))
    args = parser.parse_args()
    if not args.client_secrets.is_file():
        parser.error("Baixe o cliente OAuth Desktop do seu projeto Google Cloud em secrets/client.json. Veja docs/bonus-google.md")
    if not args.token.exists():
        flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secrets), SCOPES, autogenerate_code_verifier=True)
        credentials = flow.run_local_server(host="127.0.0.1", port=0, access_type="offline", prompt="consent", timeout_seconds=300)
        save_json(args.token, json.loads(credentials.to_json()))
    resources = json.loads(args.resources.read_text()) if args.resources.exists() else {}
    with google_services(Settings(google_token_file=args.token)) as (drive, sheets):
        if not resources.get("folder_id"):
            resources["folder_id"] = drive.files().create(body={"name": "Observa — consultas", "mimeType": "application/vnd.google-apps.folder"}, fields="id").execute()["id"]
            save_json(args.resources, resources)
        if not resources.get("spreadsheet_id"):
            resources["spreadsheet_id"] = drive.files().create(body={"name": "Observa — registro de consultas", "mimeType": "application/vnd.google-apps.spreadsheet", "parents": [resources["folder_id"]]}, fields="id").execute()["id"]
            save_json(args.resources, resources)
        spreadsheet_id = resources["spreadsheet_id"]
        tabs = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()["sheets"]
        if not any(tab["properties"]["title"] == "Consultas" for tab in tabs):
            sheets.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": [{"updateSheetProperties": {"properties": {"sheetId": tabs[0]["properties"]["sheetId"], "title": "Consultas"}, "fields": "title"}}]}).execute()
        sheets.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range="Consultas!A1:G1", valueInputOption="RAW", body={"values": [HEADERS]}).execute()
    print("Adicione ao .env e reinicie a API (nenhum token é exibido):")
    print(f"GOOGLE_TOKEN_FILE={args.token}\nGOOGLE_DRIVE_FOLDER_ID={resources['folder_id']}\nGOOGLE_SPREADSHEET_ID={resources['spreadsheet_id']}\nGOOGLE_SHEET_TAB=Consultas")


if __name__ == "__main__":
    main()
