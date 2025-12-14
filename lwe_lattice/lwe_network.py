import socket
import ssl
import json
import numpy as np

class LWENetwork:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # TLS context for server
        self.server_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.server_context.load_cert_chain(certfile="server.crt", keyfile="server.key")
        self.server_context.load_verify_locations("client.crt")
        self.server_context.verify_mode = ssl.CERT_REQUIRED
        # TLS context for client
        self.client_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.client_context.load_cert_chain(certfile="client.crt", keyfile="client.key")
        self.client_context.load_verify_locations("server.crt")

    def np_to_json(self, data):
        if isinstance(data, tuple):
            return {'type': 'tuple', 'data': [self.np_to_json(item) for item in data]}
        elif isinstance(data, np.ndarray):
            # Convert NumPy int64 to Python int
            return {'type': 'ndarray', 'data': data.astype(object).tolist()}
        elif isinstance(data, np.integer):
            return int(data)  # Convert single NumPy int to Python int
        return data

    def json_to_np(self, data):
        if isinstance(data, dict) and 'type' in data:
            if data['type'] == 'ndarray':
                return np.array(data['data'])
            elif data['type'] == 'tuple':
                return tuple(self.json_to_np(item) for item in data['data'])
        return data

    def send_lwe_data(self, data, destination):
        """Send JSON data"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                ssl_s = self.client_context.wrap_socket(s, server_hostname=destination[0])
                ssl_s.connect(destination)
            
                # Convert to JSON and send
                json_data = json.dumps(self.np_to_json(data)).encode('utf-8')
                ssl_s.sendall(json_data)
                print(f"Sending JSON data, size: {len(json_data)} bytes to {destination}")
            
        except Exception as e:
            print(f"Error sending data: {e}")
            raise

    def receive_lwe_data(self):
        """Receive JSON data with optimal buffer management"""
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        conn, addr = self.socket.accept()
        ssl_conn = self.server_context.wrap_socket(conn, server_side=True)

        with ssl_conn:
            # Read data until complete JSON
            data = b""
            buffer_size = 131072  # 128KB chunks
            max_data_size = 10 * 1024 * 1024  # 10MB safety limit

            while True:
                # Take chunk
                chunk = ssl_conn.recv(buffer_size)
                if not chunk:
                    if not data:
                        raise ConnectionError("Connection closed without data")
                    break

                data += chunk

                # Check to prevent memory exhaustion
                if len(data) > max_data_size:
                    raise ValueError(f"Data exceeds maximum allowed size: {max_data_size} bytes")

                # parse JSON, if we have complete data
                try:
                    json_data = json.loads(data.decode('utf-8'))
                    # Successfully parsed - we have complete message
                    return self.json_to_np(json_data)
                except json.JSONDecodeError:
                    # Incomplete JSON, continue receiving
                    continue
                except UnicodeDecodeError:
                    # Invalid UTF-8, continue receiving (might be incomplete)
                    continue
                
            # If we exit the loop, try one final parse
            try:
                json_data = json.loads(data.decode('utf-8'))
                return self.json_to_np(json_data)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise ValueError(f"Invalid JSON data received: {e}")