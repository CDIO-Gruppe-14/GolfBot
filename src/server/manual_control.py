import sys
import os
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.communication.connection import PCClient
from config import ROBOT_IP

class ManualControlApp:
    def __init__(self, root, client):
        self.root = root
        self.client = client
        self.root.title("GolfBot Manuel Styring")
        self.root.geometry("400x300")
        self.root.configure(bg="#2E3440")

        self.current_drive = "STOP"
        self.current_collect = "COLLECT_STOP"

        # Holder styr på hvilke taster der er nede
        self.keys_pressed = {
            'w': False, 's': False, 'a': False, 'd': False,
            'e': False, 'q': False
        }

        # UI Elementer
        title = tk.Label(root, text="GolfBot Styring", font=("Arial", 16, "bold"), bg="#2E3440", fg="#D8DEE9")
        title.pack(pady=10)

        info = tk.Label(root, text="Hold vinduet markeret for at styre!\n\nW / S : Kør fremad / bagud\nA / D : Drej venstre / højre\nE / Q : Start opsamler frem / baglæns\nEsc : Afslut", 
                        font=("Arial", 12), bg="#2E3440", fg="#A3BE8C", justify=tk.LEFT)
        info.pack(pady=20)

        self.status_label = tk.Label(root, text="Status: Forbundet", font=("Arial", 10), bg="#2E3440", fg="#88C0D0")
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        # Bind taster
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)

        # Start opdaterings-loop
        self.update_robot()

    def on_key_press(self, event):
        key = event.keysym.lower()
        if key == 'escape':
            self.quit_app()
        if key in self.keys_pressed:
            self.keys_pressed[key] = True

    def on_key_release(self, event):
        key = event.keysym.lower()
        if key in self.keys_pressed:
            self.keys_pressed[key] = False

    def update_robot(self):
        # --- DRIVE KONTROL ---
        new_drive = "STOP"
        if self.keys_pressed['w']:
            new_drive = "FWD"
        elif self.keys_pressed['s']:
            new_drive = "BWD"
        elif self.keys_pressed['a']:
            new_drive = "LEFT"
        elif self.keys_pressed['d']:
            new_drive = "RIGHT"

        if new_drive != self.current_drive:
            self.client.send_command(new_drive + "\n")
            self.client.wait_for_reply()
            self.current_drive = new_drive
            self.status_label.config(text=f"Motor: {new_drive} | Opsamler: {self.current_collect}")

        # --- OPSAMLER KONTROL ---
        new_collect = "COLLECT_STOP"
        if self.keys_pressed['e']:
            new_collect = "COLLECT_FWD"
        elif self.keys_pressed['q']:
            new_collect = "COLLECT_BWD"

        if new_collect != self.current_collect:
            self.client.send_command(new_collect + "\n")
            self.client.wait_for_reply()
            self.current_collect = new_collect
            self.status_label.config(text=f"Motor: {self.current_drive} | Opsamler: {new_collect}")

        # Kør igen om 50ms
        self.root.after(50, self.update_robot)

    def quit_app(self):
        print("\nAfslutter...")
        self.client.send_command("EXIT\n")
        self.client.close()
        self.root.destroy()

def main():
    print("=====================================")
    print("  GolfBot PC - MANUEL STYRING        ")
    print("=====================================")
    client = PCClient(ROBOT_IP)
    
    if not client.connect_to_robot():
        return

    # Opretter et lille vindue til at fange tastetryk via Tkinter
    # (Kræver ingen pip installationer eller administrator rettigheder)
    root = tk.Tk()
    app = ManualControlApp(root, client)
    
    # Når vinduet lukkes via X i hjørnet
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    
    root.mainloop()

if __name__ == "__main__":
    main()
