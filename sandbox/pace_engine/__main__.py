"""Run the sandbox API: python -m pace_engine [--host 127.0.0.1] [--port 8090]"""
import argparse
import logging

import uvicorn

from .api import create_app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8090)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    uvicorn.run(create_app(), host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()
