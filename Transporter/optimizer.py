from distante import calculeaza_distanta_km

def calculeaza_lungime_traseu(traseu):
    """ Adună distanțele dintre toate punctele dintr-o listă în buclă închisă """
    total = 0.0
    for i in range(len(traseu) - 1):
        total += calculeaza_distanta_km(traseu[i], traseu[i+1])
    return total

def ruleaza_tsp_cheapest_insertion(depozit, colete):
    """
    Rezolvă problema comis-voiajorului (TSP) cu întoarcere la depozit
    folosind euristică de inserție ieftină (Cheapest Insertion).
    """
    if not colete:
        return [depozit, depozit], 0.0, 0.0

    # Traseul fără AI (în ordinea în care au fost adăugate coletele)
    traseu_simplu = [depozit] + list(colete) + [depozit]
    km_neoptimizat = calculeaza_lungime_traseu(traseu_simplu)

    # Algoritmul TSP: Pornim cu un circuit închis [depozit -> depozit]
    traseu_optim = [depozit, depozit]

    # Inserăm fiecare colet pe rând în poziția care mărește cel mai puțin drumul total
    for colet in colete:
        cel_mai_bun_index = 1
        crestere_minima = float('inf')

        for i in range(1, len(traseu_optim)):
            p_inainte = traseu_optim[i - 1]
            p_dupa = traseu_optim[i]

            # Costul vechi între cele două puncte
            dist_veche = calculeaza_distanta_km(p_inainte, p_dupa)
            
            # Costul nou dacă inserăm coletul între ele
            dist_noua = calculeaza_distanta_km(p_inainte, colet) + calculeaza_distanta_km(colet, p_dupa)
            
            crestere = dist_noua - dist_veche

            if crestere < crestere_minima:
                crestere_minima = crestere
                cel_mai_bun_index = i

        traseu_optim.insert(cel_mai_bun_index, colet)

    km_optim = calculeaza_lungime_traseu(traseu_optim)
    return traseu_optim, km_optim, km_neoptimizat