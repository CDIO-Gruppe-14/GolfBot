# ev3dev2/robot.py

OUTPUT_A = "outA"
OUTPUT_B = "outB"
OUTPUT_C = "outC"
OUTPUT_D = "outD"

class SpeedPercent:
    def __init__(self, val):
        self.val = val

class MoveTank:
    def __init__(self, left_port, right_port):
        self.left_port = left_port
        self.right_port = right_port

    def on_for_degrees(self, left_speed, right_speed, degrees):
        # Vi udregner om det er et sving eller kørsel ligeud for at printe noget læsbart
        type_af_kørsel = "Kører ligeud" if left_speed.val == right_speed.val else "Drejer"
        print(f"[{type_af_kørsel}] Speed: L={left_speed.val}% R={right_speed.val}% | Grader: {degrees:.1f}")

    def on_for_rotations(self, left_speed, right_speed, rotations):
        self.on_for_degrees(left_speed, right_speed, rotations * 360)

    def off(self):
        print("  !!! Motorer stoppet !!!")