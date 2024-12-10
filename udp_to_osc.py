import socket
import struct
from pythonosc.udp_client import SimpleUDPClient

# Configurations
FACETRACKER_IP = "127.0.0.1"  # IP where the facetracker sends data
FACETRACKER_PORT = 5005       # Port where the facetracker sends data
UNITY_IP = "127.0.0.1"        # IP to send OSC messages to Unity
UNITY_PORT = 7000             # Port to send OSC messages to Unity

# Initialize sockets and OSC client
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((FACETRACKER_IP, FACETRACKER_PORT))
osc_client = SimpleUDPClient(UNITY_IP, UNITY_PORT)

print(f"Listening for facetracker data on {FACETRACKER_IP}:{FACETRACKER_PORT}")
print(f"Sending OSC messages to {UNITY_IP}:{UNITY_PORT}")

while True:
    try:
        # Receive raw data from facetracker
        data, addr = udp_socket.recvfrom(4096)  # Adjust buffer size if needed
        
        # Decode only the relevant fields
        offset = 0

        # Decode timestamp
        timestamp = struct.unpack_from("<d", data, offset)[0]  # 8 bytes
        offset += 8

        # Skip Face ID
        offset += 4  # 4 bytes

        # Skip Resolution (Width and Height)
        offset += 4  # Width (4 bytes)
        offset += 4  # Height (4 bytes)

        # Decode Euler angles for direction
        euler_x = struct.unpack_from("<f", data, offset)[0]  # Pitch (up/down)
        offset += 4
        euler_y = struct.unpack_from("<f", data, offset)[0]  # Yaw (left/right)
        offset += 4
        euler_z = struct.unpack_from("<f", data, offset)[0]  # Roll (side tilt)
        offset += 4

        # Send directional data to Unity
        osc_client.send_message("/facetracker/look/up_down", euler_x)
        osc_client.send_message("/facetracker/look/left_right", euler_y)
        osc_client.send_message("/facetracker/look/roll", euler_z)

        # Debug output
        print(f"Timestamp: {timestamp}, Euler: [Up/Down: {euler_x}, Left/Right: {euler_y}, Roll: {euler_z}]")

    except KeyboardInterrupt:
        print("Exiting...")
        break
    except Exception as e:
        print(f"Error: {e}")
