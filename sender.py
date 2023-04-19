import socket
from mss import mss
from PIL import Image
from io import BytesIO

bounding_box = {'top': 100, 'left': 0, 'width': 400, 'height': 300}
UDP_IP = '192.168.143.46' # change this to the IP address of the remote device
UDP_PORT = 1234

sct = mss()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    while True:
        sct_img = sct.grab(bounding_box)
        img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
        with BytesIO() as f:
            img.save(f, format='PNG')
            data = f.getvalue()
        sock.sendto(data, (UDP_IP, UDP_PORT))
