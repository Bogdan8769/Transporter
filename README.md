# Transporter

Aplicație Python pentru planificarea livrărilor dintr-un depozit.

## Pornire

```sh
pip install -r requirments.txt
python Transporter/main.py
```

## Utilizare

1. Adaugă depozitul prin adresă sau click pe hartă.
2. Completează greutatea în kg, volumul în m³ și intervalul HH:MM, apoi adaugă fiecare colet. Valorile trebuie să fie pozitive, iar intervalul în aceeași zi.
3. Alternativ, apasă **Importă colete CSV** și selectează `colete_exemplu.csv`. Importul adaugă colete la cele existente. Dacă un rând este invalid, întregul import este anulat și apare numărul rândului.
4. Alege ora plecării și calculează traseul. Lista arată ora estimată de începere a livrării, așteptarea, greutatea și volumul. Totalurile sunt afișate jos.

CSV poate folosi virgulă sau punct și virgulă. Coloane obligatorii:
`adresa,greutate_kg,volum_m3,ora_start,ora_sfarsit`.
Coloane opționale: `latitudine,longitudine`; dacă lipsesc, adresa este căutată online. Salvează fișierul în UTF-8. Pentru zecimale cu virgulă folosește separatorul punct și virgulă sau câmpuri între ghilimele.

## Algoritmul, explicat simplu

Coletele sunt luate în ordinea orei limită. Pentru fiecare colet încercăm fiecare poziție din traseu, păstrăm pozițiile care respectă toate intervalele și alegem traseul cel mai scurt dintre ele. Dacă ajungem devreme, așteptăm. Intervalul se referă la **începerea livrării**; descărcarea durează 3 minute. Viteza medie este fixată la 35 km/h, fără trafic real. Distanțele sunt memorate pe durata calculului pentru a evita cereri repetate.

Dacă euristica nu găsește o inserție validă, apare un mesaj; aceasta nu demonstrează că nu există nicio ordine posibilă. Nu se folosesc RL sau Q-Learning. Greutatea și volumul sunt înregistrate și însumate; nu există încă limită de capacitate sau distribuire între mai multe dube. Distanțele folosesc OSRM, cu rezervă în linie dreaptă când serviciul nu răspunde. Calculul și geocodarea se fac în firul interfeței și pot dura.

## Verificări

```sh
python -m unittest discover -s tests -v
```
