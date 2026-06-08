import sys
import os
import time

# Tilfoej roden af projektet til sys.path, saa vi kan importere src.communication
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.communication.connection import RobotServer

def main():
    print("--- Starter WiFi Test (EV3 Server) ---")
    server = RobotServer()
    server.wait_for_connection()
    
    print("Venter paa besked fra PC...")
    besked = server.receive_message()
    print("Modtog: '{}'".format(besked))
    
    print("Sender svar tilbage...")
    server.send_reply("Hej PC, forbindelsen over WiFi virker perfekt!")
    
    # Giv PC'en et kort sekund til at modtage svaret, for netvaerket lukkes
    time.sleep(1)
    
    server.close()
    print("Test afsluttet.")

if __name__ == "__main__":
    main()
