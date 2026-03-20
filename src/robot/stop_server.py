import socket
import threading

# TCP server der lytter efter "STOP" kommandoer fra vision-systemet og sætter en flag, som robotten kan tjekke for at stoppe motorerne. 
class StopServer:
    def __init__(self, host="0.0.0.0", port=5005):
        self.host = host
        self.port = port
        self.stop_requested = False
        self._thread = None

    # Starter serveren i en separat tråd, så den kan køre parallelt med robotens hovedlogik.
    def start(self):
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

    # Serverens hovedloop: accepterer indkommende forbindelser og læser data. Hvis data er "STOP", sættes stop_requested flaget til True.
    def _run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()

            while True:
                conn, _ = server.accept()
                with conn:
                    data = conn.recv(1024).decode().strip()
                    if data == "STOP":
                        self.stop_requested = True

    def reset(self):
        self.stop_requested = False