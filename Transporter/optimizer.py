from distante import calculeaza_distanta_km


def calculeaza_lungime_traseu(traseu, distanta=calculeaza_distanta_km):
    return sum(distanta(traseu[i], traseu[i + 1]) for i in range(len(traseu) - 1))


def program_livrari(traseu, plecare=480, distanta=calculeaza_distanta_km):
    """35 km/h, 3 minute/opriere; dacă ajungem devreme, așteptăm."""
    timp = plecare
    program = []
    for i in range(1, len(traseu) - 1):
        colet = traseu[i]
        sosire = timp + distanta(traseu[i - 1], colet) / 35 * 60
        inceput = max(sosire, colet[5])
        if inceput > colet[6]:
            return None
        program.append((inceput, inceput - sosire))
        timp = inceput + 3
    return program


def ruleaza_tsp_cheapest_insertion(depozit, colete, plecare=480):
    # Distanțele sunt memorate doar pentru acest calcul (inclusiv sensul drumului).
    distante = {}

    def distanta(a, b):
        cheie = (a[0], a[1], b[0], b[1])
        if cheie not in distante:
            distante[cheie] = 0.0 if a[:2] == b[:2] else calculeaza_distanta_km(a, b)
        return distante[cheie]

    traseu_simplu = [depozit] + list(colete) + [depozit]
    km_simplu = calculeaza_lungime_traseu(traseu_simplu, distanta)
    traseu = [depozit, depozit]
    # Începem cu termenele cele mai apropiate.
    for colet in sorted(colete, key=lambda c: c[6]):
        cel_mai_bun = None
        km_minim = float("inf")
        for i in range(1, len(traseu)):
            candidat = traseu[:i] + [colet] + traseu[i:]
            if program_livrari(candidat, plecare, distanta) is None:
                continue
            km = calculeaza_lungime_traseu(candidat, distanta)
            if km < km_minim:
                km_minim, cel_mai_bun = km, candidat
        if cel_mai_bun is None:
            raise ValueError(f"Nu am găsit o inserție care respectă orele pentru {colet[2]}. "
                             "Schimbă ora plecării sau intervalele. Euristica nu verifică toate ordonările.")
        traseu = cel_mai_bun
    program = program_livrari(traseu, plecare, distanta)
    return traseu, calculeaza_lungime_traseu(traseu, distanta), km_simplu, program
