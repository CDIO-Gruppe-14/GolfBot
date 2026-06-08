import socket
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import PORT, BUFFER_SIZE, MAX_RETRIES, CONNECT_TIMEOUT_SEC, RETRY_DELAY_SEC

class RobotServer:
    """
    Koerer paa EV3. Lytter efter forbindelser og modtager kommandoer fra PC'en.
    """
    def __init__(self):
        # Saetter vores stik ("socket") op
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Goer at vi kan genstarte programmet hurtigt uden at porten er blokeret
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Lyt til alle der vil snakke paa PORT 12345 (USB, Bluetooth, WiFi)
        self.server_socket.bind(('0.0.0.0', PORT)) 
        self.server_socket.listen(1)
        
        self.client_conn = None
        self.client_addr = None
        
    def wait_for_connection(self):
        print("EV3 venter paa at PC'en forbinder paa port {}".format(PORT))
        # Dette "stopper" programmet indtil PC'en kontakter os
        self.client_conn, self.client_addr = self.server_socket.accept()
        print("BINGO! Forbundet til PC'en paa adresse {}".format(self.client_addr))

    def receive_message(self):
        """Venter her indtil der kommer en besked fra PC'en."""
        if not self.client_conn:
            return None
            
        try:
            data = self.client_conn.recv(BUFFER_SIZE)
            if not data: # Betyder at PC'en lukkede forbindelsen
                print("PC'en lukkede forbindelsen.")
                self.close_client()
                return None
            return data.decode('utf-8')
        except Exception as e:
            print("Ups! Mistede forbindelsen til PC: {}".format(e))
            self.close_client()
            return None
            
    def send_reply(self, text):
        """Sender vores svar tilbage til PC'en"""
        if not self.client_conn:
            print("Kan ikke svare: Ingen PC forbundet.")
            return False
            
        try:
            self.client_conn.sendall(text.encode('utf-8'))
            return True
        except Exception as e:
            print("Fejl! Kunne ikke svare PC'en: {}".format(e))
            self.close_client()
            return False

    def close_client(self):
        """Lukker kun forbindelsen til den nuvaerende PC (klar til en ny)"""
        if self.client_conn:
            try:
                self.client_conn.close()
            except:
                pass
            self.client_conn = None
            print("Forbindelse til PC lukket.")

    def close(self):
        """Lukker hele serveren ned permanent."""
        self.close_client()
        if self.server_socket:
            self.server_socket.close()
            print("Server lukket.")


class PCClient:
    """
    Koerer paa PC'en. Ringer EV3'en op og sender kommandoer til den.
    """
    def __init__(self, robot_ip):
        self.robot_ip = robot_ip
        self.client_socket = None
        
    def connect_to_robot(self, max_retries=MAX_RETRIES):
        """Forsoeger at forbinde til robotten med genforsoeg."""
        for attempt in range(max_retries):
            try:
                print("[{}/{}] Ringer til EV3 paa IP: {}...".format(attempt+1, max_retries, self.robot_ip))
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(CONNECT_TIMEOUT_SEC)
                self.client_socket.connect((self.robot_ip, PORT))
                self.client_socket.settimeout(None) # Slaa timeout fra, naar vi er forbundet
                print("Forbundet!")
                return True
            except Exception as e:
                print("Kunne ikke forbinde: {}. Proever om {} sekunder...".format(e, RETRY_DELAY_SEC))
                time.sleep(RETRY_DELAY_SEC)
        
        print("Fejl: Kunne ikke faa kontakt til EV3'en!")
        return False
        
    def send_command(self, text):
        """Sender en besked til EV3."""
        if not self.client_socket:
            print("Fejl: Du er ikke forbundet til EV3'en!")
            return False
            
        try:
            self.client_socket.sendall(text.encode('utf-8'))
            return True
        except Exception as e:
            print("Forbindelsen roeg under afsendelse: {}".format(e))
            self.close()
            return False
        
    def wait_for_reply(self):
        """Venter paa svar fra robotten (blokerer)"""
        if not self.client_socket:
            return None
            
        try:
            reply = self.client_socket.recv(BUFFER_SIZE)
            if not reply:
                print("EV3 lukkede forbindelsen.")
                self.close()
                return None
            return reply.decode('utf-8')
        except Exception as e:
            print("Mistede forbindelsen under venten paa svar: {}".format(e))
            self.close()
            return None

    def close(self):
        """Lukker forbindelsen paent ned."""
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            print("Forbindelse til EV3 lukket.")
