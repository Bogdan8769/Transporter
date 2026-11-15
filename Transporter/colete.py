"""Citirea și verificarea datelor unui colet, fără biblioteci suplimentare."""
import csv
import math


def ora_in_minute(text):
    if not isinstance(text, str):
        raise ValueError("Ora lipsește; folosește HH:MM.")
    parti = text.strip().split(":")
    if len(parti) != 2 or not all(p.isdigit() for p in parti):
        raise ValueError("Ora trebuie scrisă HH:MM.")
    ore, minute = map(int, parti)
    if not (0 <= ore <= 23 and 0 <= minute <= 59):
        raise ValueError("Ora trebuie să fie între 00:00 și 23:59.")
    return ore * 60 + minute


def format_ora(minute):
    minute = math.ceil(minute)
    zile, minute = divmod(minute, 1440)
    return f"{minute // 60:02d}:{minute % 60:02d}" + (f" (+{zile} zi)" if zile else "")


def numar_pozitiv(text, nume):
    valoare = float(str(text).strip().replace(",", "."))
    if not math.isfinite(valoare) or valoare <= 0:
        raise ValueError(f"{nume} trebuie să fie un număr pozitiv.")
    return valoare


def date_colet(greutate, volum, inceput, sfarsit):
    kg = numar_pozitiv(greutate, "Greutatea")
    m3 = numar_pozitiv(volum, "Volumul")
    start = ora_in_minute(inceput)
    stop = ora_in_minute(sfarsit)
    if start > stop:
        raise ValueError("Începutul intervalului trebuie să fie înainte de sfârșit (aceeași zi).")
    return [kg, m3, start, stop]


def citeste_csv(cale, cauta_adresa):
    """Returnează toate coletele; nu modifică aplicația dacă există un rând greșit."""
    colete = []
    with open(cale, encoding="utf-8-sig", newline="") as fisier:
        mostra = fisier.read(4096)
        fisier.seek(0)
        separator = ";" if mostra.splitlines() and ";" in mostra.splitlines()[0] else ","
        reader = csv.DictReader(fisier, delimiter=separator)
        obligatorii = {"adresa", "greutate_kg", "volum_m3", "ora_start", "ora_sfarsit"}
        if not obligatorii.issubset(reader.fieldnames or []):
            raise ValueError("Coloane obligatorii: " + ", ".join(sorted(obligatorii)))
        for linie, rand in enumerate(reader, 2):
            try:
                date = date_colet(rand["greutate_kg"], rand["volum_m3"], rand["ora_start"], rand["ora_sfarsit"])
                adresa = (rand["adresa"] or "").strip()
                if not adresa:
                    raise ValueError("Adresa lipsește.")
                lat, lon = rand.get("latitudine"), rand.get("longitudine")
                if lat or lon:
                    lat, lon = float(lat), float(lon)
                    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                        raise ValueError("Coordonate invalide.")
                    punct = [lat, lon, adresa]
                else:
                    punct = cauta_adresa(adresa)
                    if not punct:
                        raise ValueError(f"Adresa nu a fost găsită: {adresa}")
                colete.append(list(punct[:3]) + date)
            except (ValueError, TypeError) as eroare:
                raise ValueError(f"Rândul {linie}: {eroare}") from eroare
    if not colete:
        raise ValueError("Fișierul nu conține colete.")
    return colete
