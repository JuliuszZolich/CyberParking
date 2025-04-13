import cv2
import numpy as np
from threading import Thread

from shapely.constructive import centroid

from database import add_incident, get_vehicles_parking_spot, get_newest_arrival
DISPLAY = False

camera_thread = None
main_working_flag = True

def main():
    # Inicjalizacja detektora tła
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=750, varThreshold=50, detectShadows=True)

    # Słownik przechowujący pojazdy: {ID: (cx, cy, w, h, angle, vanish_count, stationary_count, last_box)}
    vehicles = {}

    # Parametry obszaru wykrywania nowych pojazdów
    entry_x_min, entry_x_max = 350, 450
    entry_y_min, entry_y_max = 550, 700

    # Parametry obszaru wykrywania opuszczających pojazdów
    leave_min_x, leave_max_x = 75, 200
    leave_min_y, leave_max_y = 425, 600

    # Lokalizacje miejsc parkingowych
    parking_spots = [(100, 100), (200, 100), (300, 100), (400, 100), (500, 100), (600, 100), (700, 100), (800, 100)]

    # Symulowany obraz z kamery
    cap = cv2.VideoCapture(r'./test/kamera-gorna.mp4')
    # cap.set(cv2.CAP_PROP_POS_FRAMES, 630)
    import time

    while main_working_flag:
        ret, frame = cap.read()
        if not ret:
            break

        # Wykrywanie ruchomych obiektów
        fg_mask = bg_subtractor.apply(frame)
        cv2.imwrite('framemask.jpg', fg_mask)


        # Usunięcie cieni i szumów
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        cv2.imwrite('framethresh.jpg', fg_mask)
        kernel = np.ones((5, 5), np.uint8)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        cv2.imwrite('frameclose.jpg', fg_mask)

        # Znalezienie konturów pojazdów
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected_vehicles = []

        frame_copy = frame.copy()
        # Filtrowanie konturów i dodawanie do listy wykrytych pojazdów
        for cnt in contours:
            frame = cv2.drawContours(frame, [cnt], 0, (0, 255, 0), 2)
            if cv2.contourArea(cnt) > 500:
                rect = cv2.minAreaRect(cnt)
                (cx, cy), (w, h), angle = rect
                detected_vehicles.append((cx, cy, w, h, angle))
                frame_copy = cv2.drawContours(frame_copy, [cnt], 0, (0, 255, 0), 2)
        cv2.imwrite('framecont.jpg', frame)

        # Dopasowanie pojazdów do już istniejących
        updated_vehicles = {}

        for vid, (vx, vy, vw, vh, vangle, stationary_count, last_box) in vehicles.items():
            min_dist = float('inf')
            best_match = None

            # Sprawdzenie, czy wykryty pojazd jest tym samym, co śledzony
            for i, (cx, cy, w, h, angle) in enumerate(detected_vehicles):
                dist = np.sqrt((vx - cx) ** 2 + (vy - cy) ** 2)
                if dist < min_dist and dist < 40:
                    min_dist = dist
                    best_match = i

            # Jeśli znaleziono pasujący pojazd
            if best_match is not None:
                if min_dist < 5:  # Pojazd stoi w miejscu
                    stationary_count += 1
                    if stationary_count > 20:
                        vehicle_centroid = centroid(((vx,vy), vx+vw, vy+vh))
                        for spot in parking_spots: # Sprawdzenie, czy pojazd stoi na miejscu parkingowym
                            if np.sqrt((vehicle_centroid[0] - spot[0]) ** 2 + (vehicle_centroid[1] - spot[1]) ** 2) < 10:
                                if get_vehicles_parking_spot(vid) is None or get_vehicles_parking_spot(vid) != parking_spots.index(spot): # Sprawdzenie, czy pojazd jest już zarejestrowany na innym miejscu lub nie jest zarejestrowany
                                    add_incident(1, vid, f'Parked in spot {parking_spots.index(spot)}')
                            break
                else: # Pojazd się porusza
                    stationary_count = 0

                # Sprawdzenie, czy pojazd opuszcza obszar
                if leave_min_x < detected_vehicles[best_match][0] < leave_max_x and leave_min_y < detected_vehicles[best_match][1] < leave_max_y:
                    # logowanie zdarzenia, etc.
                    continue

                # if area of the detected vehicle is less than 50% of the area of the tracked vehicle, then it's a false positive (autko znika)
                if detected_vehicles[best_match][2] * detected_vehicles[best_match][3] < 0.5 * vw * vh:
                    updated_vehicles[vid] = (vx, vy, vw, vh, vangle, stationary_count, last_box)
                    continue

                # Aktualizacja parametrów pojazdu
                updated_vehicles[vid] = (*detected_vehicles[best_match], stationary_count, ((cx, cy), (w, h), angle))
                del detected_vehicles[best_match]
            else:
                # Jeśli nie znaleziono pasującego pojazdu, dodaj aktualny do słownika
                updated_vehicles[vid] = (vx, vy, vw, vh, vangle, stationary_count, last_box)

        # Dodanie nowych pojazdów w obszarze startowym
        for cx, cy, w, h, angle in detected_vehicles:
            if entry_x_min <= cx <= entry_x_max and entry_y_min <= cy <= entry_y_max:
                next_vehicle_id = get_newest_arrival()
                updated_vehicles[next_vehicle_id] = (cx, cy, w, h, angle, 0, ((cx, cy), (w, h), angle))

        vehicles = updated_vehicles

        # Rysowanie rotated bounding boxes
        if DISPLAY:
            for vid, (vx, vy, vw, vh, vangle, vanish_count, stationary_count, last_box) in vehicles.items():
                if stationary_count > 20:
                    box = cv2.boxPoints(last_box)  # last_box musi być w formacie ((cx, cy), (w, h), angle)
                else:
                    box = cv2.boxPoints(((vx, vy), (vw, vh), vangle))

                box = np.intp(box)
                # cv2.drawContours(frame, [box], 0, (0, 255, 0) if vanish_count < 20 else (0, 0, 255), 2)
                cv2.drawContours(frame, [box], 0, (0, 255, 0), 2)
                # cv2.putText(frame, f"ID {vid}", (int(vx), int(vy - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6,(0, 255, 0) if vanish_count < 20 else (0, 0, 255), 2)

            # Pokazanie wyników
            cv2.imshow("Foreground Mask", fg_mask)
            cv2.imshow("Tracking", frame)

        if cv2.waitKey(30) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


def main_cam():
    """
    Uruchamia wątek kamery głównej.
    """
    global camera_thread
    camera_thread = Thread(target=main)
    camera_thread.start()

def stop_main_cam():
    """
    Zatrzymuje wątek kamery głównej.
    """
    global main_working_flag
    main_working_flag = False
    global camera_thread
    if camera_thread:
        camera_thread.join()


if __name__ == '__main__':
    from database import init_database, close_database
    init_database()
    main_cam()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    stop_main_cam()
    close_database()