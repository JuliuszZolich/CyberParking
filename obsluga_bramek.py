from asyncio import sleep
from threading import Thread

import cv2
import numpy as np
from cv2 import imwrite
from skimage.filters import threshold_otsu
from skimage.measure import regionprops, label
import easyocr
from database import mark_arrival, add_incident, find_vehicle

arrival_thread = None
departure_thread = None
gate_working_flag = True


def main(wjazdowa):
    if wjazdowa:
        # Obraz z kamery wjazdowej
        camera = cv2.VideoCapture(r'./test/kamera-wjazdowa.mp4')
        ...
    else:
        # Obraz z kamery wyjazdowej
        camera = cv2.VideoCapture(r'./test/kamera-wyjazdowa.mp4')
        ...

    # Inicjalizacja czytnika
    reader = easyocr.Reader(['en'])
    
    while gate_working_flag:
        ret, frame = camera.read()
        if not ret:
            break

        # Konwersja obrazu na skalę szarości
        img_bw = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        # Zastosowanie binaryzacji
        threshold = threshold_otsu(img_bw)
        img_bw = (img_bw > threshold).astype(np.uint8) * 255
        # Zastosowanie etykietowania
        label_image = label(img_bw)
        # Wyszukanie regionów
        regions = regionprops(label_image)

        rejestracja = None

        img_bw = cv2.cvtColor(img_bw, cv2.COLOR_GRAY2RGB)

        for region in regions:
            top_left_y, top_left_x, bottom_right_y, bottom_right_x = region.bbox
            width = bottom_right_x - top_left_x
            height = bottom_right_y - top_left_y
            aspect_ratio = width / height
            area = region.area

            # Warunki na kształt rejestracji
            if 2.5 < aspect_ratio < 3.5 and 5000 < area < 9000:
                # Obrysuj rejestrację na obrazie
                # img_bw = cv2.rectangle(img_bw, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), (0, 255, 0), 2)
                rejestracja = img_bw[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
                break
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if rejestracja is None:
            continue

        # Zwiększenie rozdzielczości (interpolacja)
        resized = cv2.resize(rejestracja, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Usuwanie zakłóceń (filtrowanie gaussowskie)
        denoised = cv2.GaussianBlur(resized, (5, 5), 0)

        try:
            tekst_denoised = reader.readtext(denoised)[0][1]
            ...
        except:
            continue

        # Sprawdzenie, czy rejestracja pojazdu jest w bazie
        if not find_vehicle(tekst_denoised):
            add_incident(0, tekst_denoised)
        else:
            mark_arrival(tekst_denoised)

    camera.release()
    cv2.destroyAllWindows()

def main_gate_cam(wjazdowa):
    """
    Funkcja uruchamiająca wątek obsługujący kamerę bramki.
    :param wjazdowa: Flaga określająca, czy kamera jest wjazdowa, czy wyjazdowa.
    """
    if wjazdowa:
        global arrival_thread
        arrival_thread = Thread(target=main, args=(wjazdowa,))
        arrival_thread.start()
    else:
        global departure_thread
        departure_thread = Thread(target=main, args=(wjazdowa,))
        departure_thread.start()
    global gate_working_flag
    gate_working_flag = True

def stop_gate_threads():
    """
    Funkcja zatrzymująca wątki obsługujące kamery bramek.
    """
    global gate_working_flag
    gate_working_flag = False
    global arrival_thread, departure_thread
    if arrival_thread is not None:
        arrival_thread.join()
    if departure_thread is not None:
        departure_thread.join()


if __name__ == '__main__':
    from database import init_database, close_database
    init_database()
    main_gate_cam(True)
    main_gate_cam(False)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    stop_gate_threads()
    close_database()