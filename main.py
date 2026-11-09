from models import Depozit,Colet
from optimizer import OptimizatorRuta

depozit_central = Depozit(x=0,y=0)
lista_colete = [
    Colet(id_colet=1, x=2, y=5),
    Colet(id_colet=2, x=7, y=1),
    Colet(id_colet=3, x=6, y=8),
    Colet(id_colet=4, x=1, y=9),
    Colet(id_colet=5, x=4, y=3)
]

optimizator = OptimizatorRuta(depozit_central, lista_colete)
ruta_optima = optimizator.ruleaza_insergia()

print("Traseul optimizat pentru curier:")
for pas, locatie in enumerate(ruta_optima):
    print(f"Pasul{pas}: {locatie}")

distanta_totala = optimizator.calculeaza_distanta_totala(ruta_optima)
print(f"\nDistanta totala parcursa: {distanta_totala:.2f}km")