"""Client for controlling a remote machine via mouse and screen share."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import threading
import time

import cv2
import numpy as np
import psutil
import pyautogui
from pynput.mouse import Button, Listener
from scapy.all import ARP, Ether, srp


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def _discover_host(target_mac: str, alt_mac: str) -> str:
    """Attempt to discover the host IP using the ARP table or network scan."""

    host = "localhost"
    with os.popen("arp -a") as f:
        arp_data = f.read()

    for ip_addr, mac in re.findall(r"([-.0-9]+)\s+([-0-9a-f]{17})", arp_data):
        if mac.lower() == alt_mac.lower():
            logging.info("Found %s in ARP table", mac)
            return ip_addr

    logging.info("Could not find device in ARP table; scanning network")

    addrs = psutil.net_if_addrs()
    interface = [i for i in addrs if i.startswith("Wi-Fi")]
    if not interface:
        logging.warning("Wi-Fi interface not found; using localhost")
        return host

    iface = interface[0]
    ip_address = addrs[iface][1].address
    netmask = addrs[iface][1].netmask

    ip_bytes = [int(x) for x in ip_address.split(".")]
    mask_bytes = [int(x) for x in netmask.split(".")]
    network_bytes = [ip_bytes[i] & mask_bytes[i] for i in range(4)]
    network_address = ".".join(str(x) for x in network_bytes)

    arp = ARP(op=1, pdst=f"{network_address}/24", hwdst="ff:ff:ff:ff:ff:ff")
    packet = Ether(dst="ff:ff:ff:ff:ff:ff") / arp
    result = srp(packet, timeout=5, verbose=0)[0]

    for _, received in result:
        logging.debug("%s %s", received.hwsrc, received.psrc)
        if received.hwsrc.lower() == target_mac.lower():
            logging.info("Found host %s for MAC %s", received.psrc, target_mac)
            return str(received.psrc)

    logging.warning("Device not found; falling back to localhost")
    return host


TARGET_MAC = "00:00:00:00:00:00"
ALT_MAC = "00:00:00:00:00:00"


def _get_connection(host: str, port: int) -> socket.socket:
    """Establish a TCP connection to the server."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    logging.info("Connected to %s:%s", host, port)
    return sock


STOP_BUTTON = 0
Button_state = 0  # 0-no click 1-left click 2-right click
MOUSE_REFRESH_TIME = 0.075

win_x = 0
win_y = 0
win_width = 1920
win_height = 1080


def send_mouse_coords(conn):

    while True:
        # Get the current mouse position
        if STOP_BUTTON:
            break

        x, y = pyautogui.position()

        try:
            msg = json.dumps(
                {
                    "x": (x - win_x) / (win_width / 1920),
                    "y": (y - win_y) / (win_height / 1080),
                    "button": Button_state,
                }
            )
        except Exception:  # noqa: BLE001
            continue
        conn.sendall((msg + "\n").encode())
        # Wait for some time before sending the next mouse coordinates
        time.sleep(MOUSE_REFRESH_TIME)


# Function to receive video data from the server


def clicking(conn):

    if STOP_BUTTON:
        return

    def on_click(x, y, button, pressed):
        global Button_state

        if STOP_BUTTON:
            return

        if pressed:
            logging.debug("mouse button: %s", button)
            if button == Button.left:
                Button_state = 1
            elif button == Button.right:
                Button_state = 2
            else:
                Button_state = 0

            try:
                msg = json.dumps(
                    {
                        "x": (x - win_x) / (win_width / 1920),
                        "y": (y - win_y) / (win_height / 1080),
                        "button": Button_state,
                    }
                )
                logging.debug(msg)
            except Exception:  # noqa: BLE001
                return
            conn.sendall((msg + "\n").encode())
            # Wait for some time before sending the next mouse coordinates
            time.sleep(MOUSE_REFRESH_TIME)
        else:
            Button_state = 0

    with Listener(on_click=on_click) as listener:
        listener.join()


def receive_video_data(conn):
    # Create a buffer to hold the received video data
    global STOP_BUTTON

    global win_x
    global win_y
    global win_width
    global win_height
    cv2.namedWindow("Screen", cv2.WINDOW_NORMAL)

    win_x = cv2.getWindowImageRect("Screen")[0]
    win_y = cv2.getWindowImageRect("Screen")[1]
    win_width = cv2.getWindowImageRect("Screen")[2]
    win_height = cv2.getWindowImageRect("Screen")[3]

    buffer = b""

    while True:

        win_x = cv2.getWindowImageRect("Screen")[0]
        win_y = cv2.getWindowImageRect("Screen")[1]
        win_width = cv2.getWindowImageRect("Screen")[2]
        win_height = cv2.getWindowImageRect("Screen")[3]

        # Receive the size of the JPEG buffer from the server
        size_bytes = conn.recv(4)
        if not size_bytes:
            break
        size = int.from_bytes(size_bytes, byteorder="big")
        logging.debug("frame size: %s", size)
        # Receive the JPEG buffer from the server
        while len(buffer) < size:
            data = conn.recv(min(1024, size - len(buffer)))
            if not data:
                break
            buffer += data

        # Convert the JPEG buffer to a numpy array
        img = cv2.imdecode(
            np.frombuffer(buffer, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        # Display the image
        cv2.imshow("Screen", img)
        # cv2.waitKey(1)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            STOP_BUTTON = 1
            break

        # Reset the buffer for the next image
        buffer = b""


def run_client(host: str, port: int) -> None:
    """Run the remote client against the given host."""

    conn = _get_connection(host, port)

    send_mouse_coords_thread = threading.Thread(
        target=send_mouse_coords, args=(conn,), daemon=True
    )
    receive_video_data_thread = threading.Thread(
        target=receive_video_data, args=(conn,), daemon=True
    )
    detect_mouse_click_thread = threading.Thread(
        target=clicking, args=(conn,), daemon=True
    )

    send_mouse_coords_thread.start()
    receive_video_data_thread.start()
    detect_mouse_click_thread.start()

    send_mouse_coords_thread.join()
    receive_video_data_thread.join()
    detect_mouse_click_thread.join()

    conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Remote device controller client")
    )  # noqa: E501
    parser.add_argument("--host", help="Server IP address")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--mac", default=TARGET_MAC, help="Target MAC address")
    parser.add_argument(
        "--alt-mac",
        default=ALT_MAC,
        help="Alternate MAC address used in ARP table lookup",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    host = args.host or _discover_host(args.mac, args.alt_mac)
    run_client(host, args.port)


if __name__ == "__main__":
    main()
