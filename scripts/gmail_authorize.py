from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import get_settings
from app.services.gmail import GMAIL_SCOPES


def main() -> None:
    settings = get_settings()
    credentials_path = settings.gmail_credentials_path
    if not credentials_path.exists():
        raise SystemExit(
            f"OAuth client file not found at {credentials_path}. "
            "Download a Desktop app OAuth client from Google Cloud first."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), GMAIL_SCOPES)
    credentials = flow.run_local_server(port=0)
    token_path = settings.gmail_token_path
    Path(token_path).parent.mkdir(parents=True, exist_ok=True)
    Path(token_path).write_text(credentials.to_json(), encoding="utf-8")
    print(f"Gmail authorization saved to {token_path}")


if __name__ == "__main__":
    main()
