"""Server for streaming screen and receiving mouse events."""

from __future__ import annotations

import argparse
import json
import logging
import socket
import threading
from typing import Tuple

import cv2
import mss
import numpy as np
import pyautogui

pyautogui.PAUSE = 0


def send_screen(conn: socket.socket, stop_event: threading.Event) -> None:
    """Continuously capture the screen and stream it to the client."""
    with mss.mss() as monitor:
        while not stop_event.is_set():
            screenshot = monitor.grab(monitor.monitors[1])
            img = np.array(screenshot)
            _, buffer = cv2.imencode(".jpg", img)
            conn.sendall(len(buffer).to_bytes(4, byteorder="big"))
            conn.sendall(buffer)


def receive_mouse_input(
    conn: socket.socket,
    stop_event: threading.Event,
) -> None:
    """Handle mouse events received from the client."""
    buffer = ""
    while not stop_event.is_set():
        data = conn.recv(1024).decode()
        if not data:
            break
        buffer += data
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if not line:
                continue
            try:
                payload = json.loads(line)
                x = float(payload.get("x", 0))
                y = float(payload.get("y", 0))
                click = int(payload.get("button", 0))
                if 0 < x < 1920 and 0 < y < 1080:
                    pyautogui.moveTo(round(x), round(y))
                    if click == 0:
                        pyautogui.mouseUp(button="left")
                    elif click == 1:
                        pyautogui.mouseDown(button="left")
                    elif click == 2:
                        pyautogui.click(
                            button="right", clicks=1, interval=0.25
                        )
            except Exception:  # noqa: BLE001
                logging.exception("error decoding coordinates")


def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    """Serve a single client connection."""
    logging.info("Client connected from %s:%s", addr[0], addr[1])
    stop = threading.Event()
    sender = threading.Thread(
        target=send_screen,
        args=(conn, stop),
        daemon=True,
    )
    receiver = threading.Thread(
        target=receive_mouse_input, args=(conn, stop), daemon=True
    )

    sender.start()
    receiver.start()
    sender.join()
    receiver.join()
    conn.close()
    logging.info("Client disconnected from %s:%s", addr[0], addr[1])


def start_server(host: str, port: int) -> None:
    """Start listening for client connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen(10)
        logging.info("Server listening on %s:%s", host, port)
        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_client, args=(conn, addr), daemon=True
            ).start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remote device controller server"
    )  # noqa: E501
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    start_server(args.host, args.port)


if __name__ == "__main__":
    main()
