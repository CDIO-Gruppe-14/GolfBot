import sys
import os

# Tilføj roden af projektet til sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.communication.connection import PCClient
from config import ROBOT_IP

def main():
    print("--- Starter WiFi Test (PC Client) ---")
    client = PCClient(ROBOT_IP)
    
    if client.connect_to_robot():
        print("Forbundet! Sender HEADING kommando...")
        from src.communication.protocol import encode_command
        client.send_command(encode_command("HEADING"))
        
        print("Venter på svar...")
        svar = client.wait_for_reply()
        print("Robotten svarede: '{}'".format(svar))
        
        client.close()
        print("Test afsluttet succesfuldt.")
    else:
        print("Test fejlede. Kunne ikke forbinde.")

if __name__ == "__main__":
    main()
