import math
import requests

def gaseste_coordonate_adresa(adresa_text, google_api_key=""):
    """
    Transformă o adresă scrisă (ex: 'Firiza 96, Baia Mare' sau 'Bd. Unirii 14')
    în coordonate [latitudine, longitudine, nume_curat].
    Folosește ArcGIS Geocoder (foarte precis pentru România, gratuit, fără cheie).
    """
    nume_curat = adresa_text.strip().title()
    
    # Adăugăm automat contextul local dacă nu este specificat
    adresa_completa = adresa_text
    if "baia mare" not in adresa_text.lower() and "maramures" not in adresa_text.lower():
        adresa_completa = f"{adresa_text}, Baia Mare, Maramureș, România"
    else:
        adresa_completa = f"{adresa_text}, Maramureș, România"

    # 1. Căutare principală prin ArcGIS (știe exact numerele de pe străzi)
    try:
        url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
        parametri = {
            "SingleLine": adresa_completa,
            "countryCode": "ROU",
            "maxLocations": 1,
            "f": "json"
        }
        raspuns = requests.get(url, params=parametri, timeout=4).json()
        candidati = raspuns.get("candidates", [])
        if len(candidati) > 0:
            loc = candidati[0]["location"]
            # ArcGIS returnează y = latitudine, x = longitudine
            return [float(loc["y"]), float(loc["x"]), nume_curat]
    except Exception:
        pass

    # 2. Rezervă prin OpenStreetMap (Nominatim)
    try:
        url = "https://nominatim.openstreetmap.org/search"
        parametri = {"q": adresa_completa, "format": "json", "limit": 1}
        antet = {"User-Agent": "TransporterProiectFacultate/1.0"}
        raspuns = requests.get(url, params=parametri, headers=antet, timeout=4).json()
        if len(raspuns) > 0:
            return [float(raspuns[0]["lat"]), float(raspuns[0]["lon"]), nume_curat]
    except Exception:
        pass

    return None


def calculeaza_distanta_km(p1, p2):
    """
    Calculează distanța rutieră în kilometri între două puncte [lat, lon] folosind OSRM (gratuit).
    Dacă pică internetul, folosește formula geometrică (Haversine).
    """
    lat1, lon1 = p1[0], p1[1]
    lat2, lon2 = p2[0], p2[1]

    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        date = requests.get(url, timeout=3).json()
        if date.get("code") == "Ok":
            return date["routes"][0]["distance"] / 1000.0
    except Exception:
        pass

    # Rezervă matematică (Haversine)
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return 2 * r * math.asin(math.sqrt(a))


def obtine_drum_pe_strazi(traseu):
    """
    Extrage traseul detaliat șosea cu șosea pentru a desena linia verde pe hartă.
    """
    drum_complet = []
    for i in range(len(traseu) - 1):
        p1, p2 = traseu[i], traseu[i+1]
        try:
            url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
            date = requests.get(url, timeout=3).json()
            if date.get("code") == "Ok":
                coordonate = date["routes"][0]["geometry"]["coordinates"]
                for c in coordonate:
                    drum_complet.append((c[1], c[0])) # (lat, lon)
            else:
                drum_complet.append((p1[0], p1[1]))
                drum_complet.append((p2[0], p2[1]))
        except Exception:
            drum_complet.append((p1[0], p1[1]))
            drum_complet.append((p2[0], p2[1]))
    return drum_complet