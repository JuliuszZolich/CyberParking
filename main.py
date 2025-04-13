import database
from obsluga_bramek import main_gate_cam, stop_gate_threads
from kamera_glowna import main_cam, stop_main_cam

def main():
    """
    Funkcja main uruchamiająca program do obsługi parkingu
    """
    database.init_database()
    main_cam()
    main_gate_cam(True)
    main_gate_cam(False)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    stop_gate_threads()
    stop_main_cam()
    database.close_database()