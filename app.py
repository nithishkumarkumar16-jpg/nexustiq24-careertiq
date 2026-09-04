"""Single-command entry point for the NexusTiQ24 MVP."""
import uvicorn
from src.config import DEFAULT_PORT
from src.database import initialize_database


def main() -> None:
    initialize_database()
    uvicorn.run("src.web:app", host="0.0.0.0", port=DEFAULT_PORT, reload=False)


if __name__ == "__main__":
    main()
