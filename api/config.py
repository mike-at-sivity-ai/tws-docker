import os

TWS_HOST: str = os.getenv("TWS_HOST", "tws")
TWS_PORT: int = int(os.getenv("TWS_PORT", "8888"))
TWS_CLIENT_ID: int = int(os.getenv("TWS_CLIENT_ID", "10"))
TWS_TIMEOUT: int = int(os.getenv("TWS_TIMEOUT", "10"))

API_KEY: str = os.getenv("API_KEY", "")
AUTHELIA_INTERNAL_URL: str = os.getenv("AUTHELIA_INTERNAL_URL", "http://authelia:9091")
