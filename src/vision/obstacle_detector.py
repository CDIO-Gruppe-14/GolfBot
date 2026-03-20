import cv2
import socket
from camera import RobotCamera
from color_detector import ColorDetector, draw_detection, get_largest_result, estimate_obstacle_distance_cm

ROBOT_IP = "172.20.10.3"
ROBOT_PORT = 5005
STOP_THRESHOLD_CM = 20.0

# Eksempelværdi - skal kalibreres rigtigt
CM_PER_PIXEL = 0.125

# sender en "STOP" kommando til robotten via TCP socket når forhindringen er tæt nok på. Robotten skal have en server kørende der lytter efter denne kommando og reagerer ved at stoppe motorerne.
def send_command(command: str):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ROBOT_IP, ROBOT_PORT))
        s.sendall(command.encode())


def main():
    detector = ColorDetector(min_area=500)
    detector.load_profile("orange")
    detector.load_profile("red")

    camera = RobotCamera()

    try:
        while True:
            frame = camera.get_frame() #returnere et BGR billede fra kameraet, eller None hvis der opstår en fejl.
            if frame is None:
                continue

            all_results = detector.detect_all_colors(frame)

            robot_result = get_largest_result(all_results.get("orange", [])) # finder det største detektionsresultat for den orange farve, som vi antager repræsenterer robotten. Hvis der ikke er nogen detektioner for orange, vil robot_result være None.
            obstacle_result = get_largest_result(all_results.get("red", [])) # finder det største detektionsresultat for den røde farve, som vi antager repræsenterer forhindringen. Hvis der ikke er nogen detektioner for rød, vil obstacle_result være None.

            annotated = frame.copy()


            # Hvis der er en detektion for robotten, tegnes den på det annoterede billede med en orange boks og label "robot". Hvis der er en detektion for forhindringen, tegnes den med en rød boks og label "obstacle".
            if robot_result:
                annotated = draw_detection(annotated, robot_result, label="robot", color=(0, 165, 255))

            if obstacle_result:
                annotated = draw_detection(annotated, obstacle_result, label="obstacle", color=(0, 0, 255))

            # Hvis både robotten og forhindringen er detekteret, beregnes afstanden mellem dem i centimeter ved hjælp af deres detektionscentre
            distance_cm = estimate_obstacle_distance_cm(robot_result, obstacle_result, CM_PER_PIXEL)

            if distance_cm is not None:
                print(f"Afstand robot -> forhindring: {distance_cm:.1f} cm")

                if distance_cm <= STOP_THRESHOLD_CM:
                    print("STOP sendt til robot")
                    send_command("STOP")

            cv2.imshow("Obstacle Monitor", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()


if __name__ == "__main__":
    main()