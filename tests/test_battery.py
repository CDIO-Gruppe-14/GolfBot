#!/usr/bin/env python3
from ev3dev2.power import PowerSupply

LOW_VOLTAGE_THRESHOLD = 7.0  # volt

def main():
    print("--- BATTERITEST ---")

    power = PowerSupply()
    voltage = power.measured_volts

    print("Aktuel spænding: {:.2f} V".format(voltage))

    if voltage < LOW_VOLTAGE_THRESHOLD:
        print("ADVARSEL: Batteriet er lavt! Oplad venligst robotten.")
    else:
        print("Batteriet er OK.")

if __name__ == "__main__":
    main()
