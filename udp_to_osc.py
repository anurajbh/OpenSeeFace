import time
import socket
import struct
from pythonosc.udp_client import SimpleUDPClient

# Configurations
FACETRACKER_IP = "127.0.0.1"  # IP where the facetracker sends data
FACETRACKER_PORT = 11573       # Port where the facetracker sends data
UNITY_IP = "127.0.0.1"        # IP to send OSC messages to Unity
UNITY_PORT = 7000             # Port to send OSC messages to Unity

# Initialize sockets and OSC client
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((FACETRACKER_IP, FACETRACKER_PORT))
osc_client = SimpleUDPClient(UNITY_IP, UNITY_PORT)

print(f"Listening for facetracker data on {FACETRACKER_IP}:{FACETRACKER_PORT}")
print(f"Sending OSC messages to {UNITY_IP}:{UNITY_PORT}")

# Buffer for debug data
debug_buffer = []
max_buffer_size = 10  # Maximum number of records to store
print_interval = 10  # Seconds between prints
last_print_time = time.time()
message_count = 0

# Time-based throttling
target_messages_per_second = 25  # Desired message rate
min_time_between_messages = 1 / target_messages_per_second
last_message_time = time.time()

def normalize_angle(angle):
    # Normalize from [-180, 180] to [-1, 1]
    return angle / 180.0

def buffer_euler_data(raw_euler, normalized_euler):
    global debug_buffer
    if len(debug_buffer) >= max_buffer_size:
        debug_buffer.pop(0)  # Remove the oldest entry
    debug_buffer.append((raw_euler, normalized_euler))

def print_debug_buffer(elapsed_time):
    global debug_buffer
    print("---- Buffered Euler Data ----")
    for i, (raw, norm) in enumerate(debug_buffer):
        print(f"[{i}] Normalized Euler: {norm}")
    print("---- End of Buffered Data ----")
    print(f"OSC messages sent per second: {message_count / elapsed_time:.2f}")

while True:
    try:
        # Receive raw data from facetracker
        data, addr = udp_socket.recvfrom(4096)  # Adjust buffer size if needed

        # Decode only the relevant fields
        offset = 0

        # Decode timestamp
        timestamp = struct.unpack_from("<d", data, offset)[0]  # 8 bytes
        offset += 8

        # Face ID (4 bytes) - Skip
        offset += 4

        # Resolution (Width and Height - 4 bytes each) - Skip
        offset += 4  # Width
        offset += 4  # Height

        # Eye Blink (4 bytes each) - Skip
        offset += 8

        # Success Flag (1 byte) - Skip
        offset += 1

        # PnP Error (4 bytes) - Skip
        offset += 4

        # Quaternion (4 bytes each) - Skip
        offset += 16

        # Decode Euler angles for direction
        euler_x = struct.unpack_from("<f", data, offset)[0]  # Pitch (up/down)
        offset += 4
        euler_y = struct.unpack_from("<f", data, offset)[0]  # Yaw (left/right)
        offset += 4
        euler_z = struct.unpack_from("<f", data, offset)[0]  # Roll (side tilt)
        offset += 4
        euler_x_normalized = normalize_angle(euler_x)  # Pitch
        euler_y_normalized = normalize_angle(euler_y)  # Yaw
        euler_z_normalized = normalize_angle(euler_z)  # Roll

        # Time-based throttling
        current_time = time.time()
        if current_time - last_message_time >= min_time_between_messages:
            # Send directional data to Unity
            osc_client.send_message("/facetracker/look/up_down", euler_x_normalized)
            osc_client.send_message("/facetracker/look/left_right", euler_y_normalized)
            osc_client.send_message("/facetracker/look/roll", euler_z_normalized)

            last_message_time = current_time
            message_count += 1

            # Add to debug buffer
            buffer_euler_data(
                raw_euler=[euler_x, euler_y, euler_z],
                normalized_euler=[euler_x_normalized, euler_y_normalized, euler_z_normalized]
            )

        # Check if it's time to print the buffer
        if current_time - last_print_time >= print_interval:
            elapsed_time = current_time - last_print_time
            print_debug_buffer(elapsed_time)
            last_print_time = current_time
            # print(f"OSC messages sent per second: {message_count}")
            message_count = 0

        # Translation (4 bytes each) - Skip
        offset += 12

    except KeyboardInterrupt:
        print("Exiting...")
        break
    except Exception as e:
        print(f"Error: {e}")
