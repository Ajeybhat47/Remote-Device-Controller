
# Remote Device Controller

This project enables screen sharing and remote mouse control, allowing one laptop to manage another's screen using its trackpad. The application uses socket programming for communication, and ARP scanning to detect target devices on the network.

## Features

- **Screen Sharing**: View the screen of one laptop on another device in real-time.
- **Mouse Control**: Remotely control the mouse (including clicks) of the target laptop using the trackpad or mouse of the controlling laptop.
- **ARP Scanning**: Automatically detect the target device's IP address based on its MAC address.
- **TCP Communication**: Efficiently send mouse movement data and screen frames between devices.

## Tools & Technologies

- Python
- OpenCV
- PyAutoGUI
- Scapy (for ARP scanning)
- Socket Programming

## How it Works

1. **Device Detection**: The application uses ARP scanning to find the target laptop by its MAC address.
2. **Screen Sharing**: The server-side captures the screen continuously, compresses it, and sends it to the client.
3. **Mouse Control**: The client-side sends mouse movement and click events, which are executed on the server laptop.

## Usage

### Requirements

- Python 3.x
- OpenCV
- PyAutoGUI
- Scapy
- Pynput

Install the required packages using:
```bash
pip install -r requirements.txt
```

### Running the Application

1. Clone this repository.
2. Run the server on the laptop to be controlled (target device):
    ```bash
    python server.py
    ```
3. Run the client on the controlling laptop:
    ```bash
    python client.py
    ```

### Notes

- Ensure both devices are on the same local network for ARP scanning and communication.
- Update the MAC addresses in the script to match the target device.

## Future Enhancements

- Adding multi-device support.
- Improving latency for better real-time control.
- Incorporating security features such as authentication.

## License

This project is licensed under the MIT License.
