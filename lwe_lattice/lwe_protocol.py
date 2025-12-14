from lwe import LWE
from lwe_network import LWENetwork
import socket
import threading
import jwt
import json

class LWEProtocol:
    def __init__(self, n=128, q=3329, stddev=3.19, host='localhost', port=65432):
        self.lwe = LWE(n, q, stddev)
        self.network = LWENetwork(host, port)
        self.host = host
        self.port = port
        self.auth_key = 'your-secret-key'  # Use env var in prod

    def run_server(self):
        print("Server running...")
        public_key, secret_key = self.lwe.generate_keys()
        self.network.socket.bind((self.host, self.port))
        self.network.socket.listen()

        def handle_client(conn, addr):
            ssl_conn = self.network.server_context.wrap_socket(conn, server_side=True)
            with ssl_conn:
                print(f"Handling client {addr}")
                # Receive JWT
                auth_data = b""
                while True:
                    chunk = ssl_conn.recv(1024)
                    if not chunk:
                        print(f"No auth data received from {addr}")
                        return
                    auth_data += chunk
                    try:
                        jwt.decode(auth_data.decode(), self.auth_key, algorithms=["HS256"])
                        break
                    except (jwt.InvalidTokenError, UnicodeDecodeError, json.JSONDecodeError) as e:
                        print(f"Authentication failed for {addr}: {e}")
                        return
                print(f"Connected by {addr}")
                # Send public key
                json_data = json.dumps(self.network.np_to_json(public_key)).encode('utf-8')
                print(f"Sending public key, size: {len(json_data)} bytes")
                ssl_conn.sendall(json_data)
                # Receive ciphertext
                data = b""
                max_chunks = 20  # Prevent infinite loop
                chunk_count = 0
                while chunk_count < max_chunks:
                    chunk = ssl_conn.recv(131072)  # Increased buffer size
                    if not chunk:
                        print(f"No ciphertext received from {addr}")
                        return
                    data += chunk
                    chunk_count += 1
                    try:
                        ciphertext = self.network.json_to_np(json.loads(data.decode('utf-8')))
                        break
                    except json.JSONDecodeError as e:
                        print(f"Ciphertext JSON decode error, waiting: {e}")
                        continue
                else:
                    print(f"Failed to receive valid ciphertext after {max_chunks} chunks")
                    return
                decrypted_message = self.lwe.decrypt(ciphertext)
                print(f"Decrypted message: {decrypted_message}")

        while True:
            conn, addr = self.network.socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()

    def run_client(self, server_address):
        print(f"Client connecting to {server_address}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            ssl_s = self.network.client_context.wrap_socket(s, server_hostname=server_address[0])
            ssl_s.settimeout(5.0)  # 5-second timeout
            try:
                ssl_s.connect(server_address)
                # Send JWT
                token = jwt.encode({'user': 'client'}, self.auth_key, algorithm="HS256")
                ssl_s.sendall(token.encode())
                print(f"Sent JWT, size: {len(token)} bytes")
                # Receive public key
                data = b""
                max_chunks = 20  # Prevent infinite loop
                chunk_count = 0
                while chunk_count < max_chunks:
                    try:
                        chunk = ssl_s.recv(131072)  # Increased buffer size
                        if not chunk:
                            print(f"No public key received from {server_address}")
                            raise ValueError("No public key received")
                        data += chunk
                        chunk_count += 1
                        public_key = self.network.json_to_np(json.loads(data.decode('utf-8')))
                        print(f"Received public key, size: {len(data)} bytes")
                        break
                    except json.JSONDecodeError as e:
                        print(f"Public key JSON decode error, waiting: {e}")
                        continue
                    except socket.timeout:
                        print(f"Timeout waiting for public key from {server_address}")
                        raise
                else:
                    print(f"Failed to receive valid public key after {max_chunks} chunks")
                    raise ValueError("Incomplete public key data")
                # Encrypt and send message
                message = 1  # Change to 0 to test
                ciphertext = self.lwe.encrypt(public_key, message)
                json_data = json.dumps(self.network.np_to_json(ciphertext)).encode('utf-8')
                ssl_s.sendall(json_data)
                print(f"Sent encrypted message for original: {message}, size: {len(json_data)} bytes")
            except Exception as e:
                print(f"Client error: {e}")
                raise
            finally:
                ssl_s.settimeout(None)