class Colet:
    def __init__ (self, id_colet, x ,y):
        self.id_colet = id_colet
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Colet {self.id_colet}({self.x}, {self.y})"

class Depozit:
    def __init__(self,x ,y):
        self.x =x
        self.y= y

    def __repr__(self):
        return f"Depozit ({self.x}, {self.y})"


    