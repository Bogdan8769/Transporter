import math

class OptimizatorRuta:
    def __init__(self, depozit, colete):
        self.depozit = depozit 
        self.colete = colete

    @staticmethod
    def distanta(p1, p2):
        """ Calculeaza distanta dintre doua puncte (x, y) """
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def calculeaza_distanta_totala(self, ruta):
        total = 0
        for i in range(len(ruta) - 1):
            total += self.distanta((ruta[i].x, ruta[i].y), (ruta[i+1].x, ruta[i+1].y))
        return total

    def ruleaza_insergia(self):
        ruta = [self.depozit, self.depozit]
        colete_ramase = list(self.colete)

        for colet in colete_ramase:
            cel_mai_bun_loc = 1
            crestere_minima = float('inf')

            for i in range(1, len(ruta)):
                p_ant = (ruta[i-1].x, ruta[i-1].y)
                p_urm = (ruta[i].x, ruta[i].y)
                p_nou = (colet.x, colet.y)

                dist_veche = self.distanta(p_ant, p_urm)
                dist_noua = self.distanta(p_ant, p_nou) + self.distanta(p_nou, p_urm)
                crestere = dist_noua - dist_veche

                if crestere < crestere_minima:
                    crestere_minima = crestere
                    cel_mai_bun_loc = i

            ruta.insert(cel_mai_bun_loc, colet)
        return ruta