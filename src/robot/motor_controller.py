from ev3dev2.motor import MoveTank, OUTPUT_A, OUTPUT_B, SpeedPercent

# chaufføren = den der ved hvilke kommandoer der skal sendes til motorerne for at få robotten til at bevæge sig


class MotorController:
    def __init__(self):
        # Juster OUTPUT_A/B til de porte motorene sidder i
        self.tank = MoveTank(OUTPUT_A, OUTPUT_B)
        self.wheel_diameter_mm = 56  # Standard EV3 hjul
        self.track_width_mm = 120    # Afstanden mellem midten af de to hjul (VIGTIG for sving)

    def drive_distance(self, distance_mm, speed=30):
        """Kører en specifik distance i mm"""
        # Formel: (Distance / Omkreds) * 360 grader
        circumference = self.wheel_diameter_mm * 3.1415
        degrees = (distance_mm / circumference) * 360
        self.tank.on_for_degrees(SpeedPercent(speed), SpeedPercent(speed), degrees)

    def turn_90_degrees(self, direction='right', speed=20):
        """Drej 90 grader på stedet"""
        # Denne formel er et estimat. Du skal nok fintune 'degrees' tallet
        # indtil robotten rammer præcis 90 grader på dit specifikke gulv.
        arc_length = (self.track_width_mm * 3.1415) / 4
        circumference = self.wheel_diameter_mm * 3.1415
        wheel_degrees = (arc_length / circumference) * 360 * 2 # *2 pga. modsat rotation
        
        if direction == 'right':
            self.tank.on_for_degrees(SpeedPercent(speed), SpeedPercent(-speed), wheel_degrees)
        else:
            self.tank.on_for_degrees(SpeedPercent(-speed), SpeedPercent(speed), wheel_degrees)

    def stop(self):
        self.tank.off()