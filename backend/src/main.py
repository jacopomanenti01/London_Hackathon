import logging
import uvicorn
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)


def main():
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )


if __name__ == "__main__":
    main()
