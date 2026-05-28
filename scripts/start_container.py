import os
import sys
from pathlib import Path


GOOGLE_SERVER_METADATA_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)


def main():
    load_dotenv_file()
    create_runtime_directories()
    write_streamlit_auth_secrets_from_env()

    os.execvp(
        "streamlit",
        [
            "streamlit",
            "run",
            "app.py",
            "--server.address=0.0.0.0",
            "--server.port=8501",
            "--server.headless=true",
        ],
    )


def load_dotenv_file(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, value = parse_dotenv_line(line)
        if not key or key in os.environ:
            continue

        os.environ[key] = value


def parse_dotenv_line(line):
    line = line.strip()

    if not line or line.startswith("#") or "=" not in line:
        return None, None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        return None, None

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]

    return key, value


def create_runtime_directories():
    Path(os.getenv("STORY_DB_PATH", "/app/data/sqlite/story_builder.db")).parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    Path(os.getenv("CHROMA_DB_PATH", "/app/data/chroma")).mkdir(
        parents=True,
        exist_ok=True,
    )


def write_streamlit_auth_secrets_from_env():
    required_names = [
        "AUTH_COOKIE_SECRET",
        "AUTH_REDIRECT_URI",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
    ]

    if not all(os.getenv(name) for name in required_names):
        print(
            "Authentication environment variables are incomplete; "
            "starting without Streamlit auth secrets.",
            file=sys.stderr,
        )
        return

    secrets_path = Path(".streamlit") / "secrets.toml"
    if secrets_path.exists():
        return

    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    secrets_path.write_text(
        "\n".join([
            "[auth]",
            f"redirect_uri={toml_string(os.environ['AUTH_REDIRECT_URI'])}",
            f"cookie_secret={toml_string(os.environ['AUTH_COOKIE_SECRET'])}",
            "",
            "[auth.google]",
            f"client_id={toml_string(os.environ['GOOGLE_CLIENT_ID'])}",
            f"client_secret={toml_string(os.environ['GOOGLE_CLIENT_SECRET'])}",
            (
                "server_metadata_url="
                f"{toml_string(os.getenv('GOOGLE_SERVER_METADATA_URL', GOOGLE_SERVER_METADATA_URL))}"
            ),
            "",
        ]),
        encoding="utf-8",
    )


def toml_string(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


if __name__ == "__main__":
    main()
