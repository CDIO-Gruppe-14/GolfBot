from motor_controller import MotorController
import time

# hjernen = den der ved hvilke baner der skal køres, og i hvilken rækkefølge, for at få robotten til at klippe græsset effektivt

def run_mowing_pattern():
    robot = MotorController()
    
    baner = 8
    bane_laengde_mm = 1000  # 1 meter
    bane_afstand_mm = 125   # Afstand mellem baner (1 meter / 8 baner)

    print("Starter rute...")

    for i in range(baner):
        # Kør banen i frem
        print(f"Kører bane {i+1}")
        robot.drive_distance(bane_laengde_mm)

        # Hvis det er sidste bane, skal vi ikke dreje for en ny bane fordi at vi skal tilbage til start efter
        if i < baner - 1:
            if i % 2 == 0: # Lige baner: sving højre-højre
                robot.turn_90_degrees('right')
                robot.drive_distance(bane_afstand_mm)
                robot.turn_90_degrees('right')
            else:          # Ulige baner: sving venstre-venstre
                robot.turn_90_degrees('left')
                robot.drive_distance(bane_afstand_mm)
                robot.turn_90_degrees('left')
    
    # Retur til start når alle baner er færdige
    print("Returnerer til start...")
    robot.turn_90_degrees('left')
    robot.drive_distance(1000) # Kører den meter tilbage vi er kommet "ned"
    robot.turn_90_degrees('left')
    robot.drive_distance(1000) # Kører tilbage langs den første bane
    
    robot.stop()
    print("Rute færdig!")

if __name__ == "__main__":
    while (True): #vi kører i en uendelig løkke så robotten kører igeeen og igen, indtil vi stopper den manuelt
        run_mowing_pattern()
        
        print("Venter 10 sekunder før næste rute...")
        time.sleep(10)
