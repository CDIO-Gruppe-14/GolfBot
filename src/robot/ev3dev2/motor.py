# Kun til lokal test – simulerer ev3dev2
OUTPUT_D = "D"
OUTPUT_B = "B"

class LargeMotor:
    pass

class SpeedPercent:
    def __init__(self, val): self.val = val

class MoveTank:
    def __init__(self, left, right): pass
    def on_for_rotations(self, left_speed, right_speed, rotations):
        print(f"  Koer: venstre={left_speed.val}%, hoejre={right_speed.val}%, rotationer={rotations:.2f}")
    def off(self):
        print("  Stop")