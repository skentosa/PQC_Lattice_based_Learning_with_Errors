import sys
import os
from lwe_protocol import LWEProtocol

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py [server|client]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    protocol = LWEProtocol()
    
    if mode == "server":
        protocol.run_server()
    elif mode == "client":
        server_address = os.getenv("SERVER_ADDRESS", "localhost:65432")
        host, port = server_address.split(":")
        protocol.run_client((host, int(port)))
    else:
        print("Invalid mode. Use 'server' or 'client'.")