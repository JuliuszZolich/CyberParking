import sqlite3

# Połączenie z bazą danych SQLite
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
is_available = False

def init_database():
    """
    Inicjalizuje bazę danych, tworząc tabele, jeśli nie istnieją.
    """
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vehicles (
        registration_number TEXT PRIMARY KEY,
        parking_place_id INTEGER
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS car_history (
        id INTEGER PRIMARY KEY,
        registration_number TEXT,
        date_of_arrival DATE,
        date_of_departure DATE
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS incident_history (
        id INTEGER PRIMARY KEY,
        incident_type INTEGER,
        incident_date DATE,
        car_involved TEXT,
        additional_info TEXT
    )
    ''')
    conn.commit()
    global is_available
    is_available = True

def close_database():
    """
    Zamyka połączenie z bazą danych i ustawia flagę dostępności na False.
    """
    conn.close()
    global is_available
    is_available = False

def find_vehicle(registration_number):
    """
    Znajduje pojazd w bazie danych na podstawie numeru rejestracyjnego.

    Args:
        registration_number (str): Numer rejestracyjny pojazdu.

    Returns:
        tuple: Krotka zawierająca dane pojazdu lub None, jeśli nie znaleziono.
    """
    if not is_available:
        raise Exception('Database not available')
    cursor.execute('''
    SELECT * FROM vehicles WHERE registration_number = ?
    ''', (registration_number,))
    result = cursor.fetchone()
    return result # None if not found

def add_incident(incident_type, registration_number, additional_info = None):
    """
    Dodaje incydent do historii incydentów.

    Args:
        incident_type (int): Typ incydentu.
        registration_number (str): Numer rejestracyjny pojazdu.
        additional_info (str, optional): Dodatkowe informacje o incydencie.

    Returns:
        bool: True, jeśli operacja się powiodła, False w przeciwnym razie.
    """
    if not is_available:
        return False
    cursor.execute('''
    INSERT INTO incident_history (incident_type, incident_date, car_involved, additional_info)
    VALUES (?, CURRENT_DATE, ?, ?)
    ''', (incident_type, registration_number, additional_info))
    conn.commit()
    return True

def mark_arrival(registration_number):
    """
    Oznacza przyjazd pojazdu w historii pojazdów.

    Args:
        registration_number (str): Numer rejestracyjny pojazdu.

    Returns:
        bool: True, jeśli operacja się powiodła, False w przeciwnym razie.
    """
    if not is_available:
        return False
    cursor.execute('''
    INSERT INTO car_history (registration_number, date_of_arrival)
    VALUES (?, CURRENT_DATE)
    ''', (registration_number,))
    conn.commit()
    return True

def get_newest_arrival():
    """
    Pobiera numer rejestracyjny najnowszego przyjazdu pojazdu.

    Returns:
        tuple: Krotka zawierająca numer rejestracyjny pojazdu lub None, jeśli nie znaleziono.
    """
    if not is_available:
        return None
    cursor.execute('''
    SELECT registration_number FROM car_history
    ORDER BY date_of_arrival DESC
    LIMIT 1
    ''')
    result = cursor.fetchone()
    return result

def mark_departure(registration_number):
    """
    Oznacza odjazd pojazdu w historii pojazdów.

    Args:
        registration_number (str): Numer rejestracyjny pojazdu.

    Returns:
        bool: True, jeśli operacja się powiodła, False w przeciwnym razie.
    """
    if not is_available:
        return False
    cursor.execute('''
    UPDATE car_history SET date_of_departure = CURRENT_DATE
    WHERE registration_number = ? AND date_of_departure IS NULL
    ''', (registration_number,))
    conn.commit()
    return True

def get_vehicles_parking_spot(registration_number):
    """
    Pobiera miejsce parkingowe pojazdu na podstawie numeru rejestracyjnego.

    Args:
        registration_number (str): Numer rejestracyjny pojazdu.

    Returns:
        tuple: Krotka zawierająca identyfikator miejsca parkingowego lub None, jeśli nie znaleziono.
    """
    if not is_available:
        return None
    cursor.execute('''
    SELECT parking_place_id FROM vehicles
    WHERE registration_number = ?
    ''', (registration_number,))
    result = cursor.fetchone()
    return result