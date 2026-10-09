"""Wumpus: agente logico (lógica proposicional) y simulador grafico.

Como razona el agente (lo visto en clase)
-----------------------------------------
* Simbolos proposicionales: P[x,y] = "hay un hoyo en (x,y)"
                            W[x,y] = "hay un Wumpus en (x,y)"
* Reglas del mundo (bicondicionales):
      B[x,y] <=> P[vecina1] v P[vecina2] v ...     (brisa)
      S[x,y] <=> W[vecina1] v W[vecina2] v ...     (hedor)
* Observaciones: lo que el agente percibe en cada casilla visitada (TELL).
* KB = reglas + observaciones.
* Modelos: se enumeran TODAS las asignaciones de verdad (tabla de verdad,
  2^n filas) y se conservan solo las que hacen verdadera la KB.
* Consecuencia logica (KB |= alfa): alfa es verdadera en TODOS los modelos
  de la KB. Una casilla es segura si la KB implica "no hay hoyo ni Wumpus".
* Si alfa es falsa en al menos un modelo, KB no implica alfa: la casilla es
  solo "posible" (incierta).

El BFS se usa unicamente como planificador de ruta: una vez la KB decide
cuales casillas son seguras, calcula el camino mas corto por ellas.

Bitacora
--------
Tiene dos niveles:
* Normal (por defecto): una linea por accion (movimiento + percepcion,
  disparo, grito, oro). Pensada para quien juega.
* Razonamiento (KB): ademas muestra los modelos y las inferencias
  (KB |= seguras: ...). Se activa con la casilla "Ver razonamiento (KB)".
"""

##HECHO POR
##PAULA ROMERO
##YESSICA TRIANA
##DANNA SOLER

import random
from collections import deque
from itertools import product

N = 4
NOMBRES_PERCEPCION = ("Hedor", "Brisa", "Brillo", "Golpe", "Grito")


def vecinos(c):
    x, y = c
    return [(a, b) for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if 1 <= a <= N and 1 <= b <= N]


def signo(n):
    return (n > 0) - (n < 0)


def alineados(a, b):
    """True si dos casillas comparten fila o columna (se puede disparar)."""
    return a[0] == b[0] or a[1] == b[1]


def coord(c):
    """Formato compacto para la bitacora: (3,2)."""
    return f"({c[0]},{c[1]})"


def texto_percepcion(p):
    """[Hedor, Brisa, Brillo, Golpe, Grito] -> 'Brisa + Hedor' o 'Sin señales'."""
    activas = [n for n, v in zip(NOMBRES_PERCEPCION, p) if v]
    return " + ".join(activas) if activas else "Sin señales"


class Mundo:
    """Entorno real: el agente no ve directamente sus contenidos."""

    def __init__(self, aleatorio=False, sin_salida=False):
        if aleatorio and sin_salida:
            raise ValueError("El mundo aleatorio y el caso sin salida son excluyentes.")

        self.grito = False
        if sin_salida:
            self.nombre = "Caso sin salida"
            self.hoyos = {(2, 1), (1, 2)}
            self.wumpus, self.oro = (4, 4), (4, 3)
        elif aleatorio:
            self.nombre = "Mundo aleatorio"
            libres = [(x, y) for x in range(1, N + 1) for y in range(1, N + 1)
                      if (x, y) != (1, 1)]
            # Se regenera hasta que el oro sea alcanzable sin pasar por hoyos.
            while True:
                self.wumpus, self.oro = random.sample(libres, 2)
                self.hoyos = {c for c in libres if c not in (self.wumpus, self.oro)
                              and random.random() < 0.2}
                if self._resoluble():
                    break
        else:
            self.nombre = "Mundo clásico"
            self.hoyos = {(3, 1), (3, 3), (4, 4)}
            self.wumpus, self.oro = (1, 3), (2, 3)

    def _resoluble(self):
        cola, vistos = deque([(1, 1)]), {(1, 1)}
        while cola:
            casilla = cola.popleft()
            if casilla == self.oro:
                return True
            for vecina in vecinos(casilla):
                if (vecina not in vistos and vecina not in self.hoyos
                        and vecina != self.wumpus):
                    vistos.add(vecina)
                    cola.append(vecina)
        return False

    def letal(self, casilla):
        """True si entrar a la casilla mata al agente (hoyo o Wumpus vivo)."""
        return casilla in self.hoyos or casilla == self.wumpus

    def disparar(self, origen, objetivo):
        dx = signo(objetivo[0] - origen[0])
        dy = signo(objetivo[1] - origen[1])
        self.grito = False
        if (dx and dy) or not (dx or dy):
            return 0
        x, y = origen
        while 1 <= x + dx <= N and 1 <= y + dy <= N:
            x, y = x + dx, y + dy
            if (x, y) == self.wumpus:
                self.wumpus = None
                self.grito = True
                return 1
        return 0

    def percibir(self, c):
        """Devuelve [Hedor, Brisa, Brillo, Golpe, Grito]."""
        adyacentes = vecinos(c)
        grito = int(self.grito)
        self.grito = False
        return [int(self.wumpus in adyacentes),
                int(any(casilla in self.hoyos for casilla in adyacentes)),
                int(self.oro == c), 0, grito]


class Agente:
    def __init__(self, mundo):
        self.m = mundo
        self.pos = (1, 1)
        self.visitadas = {self.pos}
        self.sin_hoyo = {self.pos}          # KB |= "no hay hoyo en c"
        self.sin_wumpus = {self.pos}        # KB |= "no hay Wumpus en c"
        self.hoyos_ciertos, self.hoyos_posibles = set(), set()
        self.wumpus_posibles, self.wumpus_cierto = set(), None
        self.n_modelos_hoyos = self.n_modelos_wumpus = 0
        self.descartadas_w = set()          # lineas de flechas fallidas
        self.percepciones = {}
        self.puntaje, self.vivo, self.fin = 0, True, False
        self.oro = False
        self.flecha, self.wumpus_muerto = True, False
        # Cada entrada: (nivel, texto). nivel 0 = accion (siempre visible);
        # nivel 1 = detalle del razonamiento KB (solo con "Ver razonamiento").
        self.log = []
        self.tell(f"Inicio en {coord(self.pos)}")

    def anotar(self, texto, detalle=False):
        self.log.append((1 if detalle else 0, texto))

    # ------------------------------------------------------------------
    # Base de conocimiento (KB) y model checking
    # ------------------------------------------------------------------
    def tell(self, accion=None):
        """TELL: agrega la percepcion actual a la KB y recalcula las inferencias.

        Si se pasa `accion`, se escribe una linea de bitacora normal del tipo
        'Me muevo a (3,2) -1 · Brisa'.
        """
        percepcion = self.m.percibir(self.pos)
        self.percepciones[self.pos] = percepcion
        if accion:
            self.anotar(f"{accion} · {texto_percepcion(percepcion)}")
        self.anotar(f"En {coord(self.pos)}: [S,B,G,Bu,Sc]={percepcion}", detalle=True)
        self.actualizar_kb()

    def frontera(self):
        """Casillas no visitadas vecinas de una visitada: las variables de la KB."""
        return sorted({v for c in self.visitadas for v in vecinos(c)} - self.visitadas)

    def modelos_hoyos(self, frontera):
        """Tabla de verdad sobre P[x,y]; deja los modelos donde la KB es verdadera.

        Regla:  B[c] <=> (hay hoyo en alguna vecina de c)
        """
        validos = []
        for valores in product([False, True], repeat=len(frontera)):
            hoyos = {c for c, v in zip(frontera, valores) if v}
            if all(bool(hoyos & set(vecinos(c))) == bool(p[1])
                   for c, p in self.percepciones.items()):
                validos.append(hoyos)
        return validos

    def modelos_wumpus(self, frontera):
        """Modelos sobre W[x,y] (a lo sumo un Wumpus) que hacen verdadera la KB.

        Regla:  S[c] <=> (hay Wumpus en alguna vecina de c)
        """
        if self.wumpus_muerto:
            return [set()]
        validos = []
        for w in [None] + frontera:
            if w in self.descartadas_w:
                continue
            if all((w in vecinos(c)) == bool(p[0])
                   for c, p in self.percepciones.items()):
                validos.append({w} if w else set())
        return validos

    @staticmethod
    def _describir(modelos, letra, nombre):
        n = len(modelos)
        texto = f"{n} modelo{'s' if n != 1 else ''} de {nombre}"
        if 0 < n <= 6:
            def fmt(m):
                return "{" + ", ".join(f"{letra}{x}{y}" for x, y in sorted(m)) + "}"
            texto += " -> " + "  ".join(fmt(m) for m in modelos)
        return texto

    def actualizar_kb(self):
        antes = self.sin_hoyo & self.sin_wumpus
        frontera = self.frontera()
        mh = self.modelos_hoyos(frontera)
        mw = self.modelos_wumpus(frontera)
        if not mh or not mw:
            self.anotar("KB inconsistente: se conservan las inferencias previas",
                        detalle=True)
            return
        self.n_modelos_hoyos, self.n_modelos_wumpus = len(mh), len(mw)
        self.anotar("KB: " + self._describir(mh, "P", "hoyos"), detalle=True)
        self.anotar("KB: " + self._describir(mw, "W", "Wumpus"), detalle=True)

        # KB |= "no hay hoyo en c"  <=>  c no tiene hoyo en NINGUN modelo.
        self.sin_hoyo = set(self.visitadas) | {c for c in frontera
                                               if all(c not in m for m in mh)}
        self.sin_wumpus = set(self.visitadas) | {c for c in frontera
                                                 if all(c not in m for m in mw)}
        if self.wumpus_muerto:
            self.sin_wumpus |= {(x, y) for x in range(1, N + 1)
                                for y in range(1, N + 1)}
        # Hoyo cierto: hay hoyo en TODOS los modelos. Posible: en AL MENOS uno.
        self.hoyos_ciertos = {c for c in frontera if all(c in m for m in mh)}
        self.hoyos_posibles = {c for c in frontera if any(c in m for m in mh)}
        self.wumpus_posibles = set().union(*mw)
        ciertos = [c for c in frontera if all(c in m for m in mw)]
        self.wumpus_cierto = ciertos[0] if ciertos else None

        nuevas = (self.sin_hoyo & self.sin_wumpus) - antes - self.visitadas
        if nuevas and not self.wumpus_muerto:
            self.anotar("KB |= seguras: " + ", ".join(coord(c) for c in sorted(nuevas)),
                        detalle=True)

    def segura(self, casilla):
        return casilla in self.sin_hoyo and casilla in self.sin_wumpus

    def inferir(self):
        """Devuelve (hoyos_ciertos, hoyos_posibles, wumpus_posibles, wumpus_cierto)."""
        return (self.hoyos_ciertos, self.hoyos_posibles,
                self.wumpus_posibles, self.wumpus_cierto)

    # ------------------------------------------------------------------
    # Planificacion de ruta y toma de decisiones
    # ------------------------------------------------------------------
    def bfs(self, meta, se_puede_pasar):
        cola, vistos = deque([(self.pos, [])]), {self.pos}
        while cola:
            casilla, camino = cola.popleft()
            for vecina in vecinos(casilla):
                if vecina in vistos:
                    continue
                vistos.add(vecina)
                if meta(vecina):
                    return camino + [vecina]
                if se_puede_pasar(vecina):
                    cola.append((vecina, camino + [vecina]))
        return None

    def objetivo_riesgo(self, hoyos_ciertos, hoyos_posibles, wumpus_posibles,
                        wumpus_cierto):
        """Casilla de la frontera con menos riesgo (hoyo posible + wumpus posible)."""
        candidatas = {v for c in self.visitadas for v in vecinos(c)
                      if v not in self.visitadas and v not in hoyos_ciertos
                      and v != wumpus_cierto}
        return min(sorted(candidatas),
                   key=lambda c: (c in hoyos_posibles) + (c in wumpus_posibles),
                   default=None)

    def paso(self):
        if not self.vivo or self.fin:
            return

        if self.oro:
            if self.pos == (1, 1):
                self.puntaje += 1000
                self.fin = True
                self.anotar("Regreso a la salida con el oro: escapo +1000")
                return
            camino = self.bfs(
                lambda c: c == (1, 1),
                lambda c: c in self.visitadas and self.segura(c),
            )
            if camino:
                return self.mover(camino[0])
            self.fin = True
            self.anotar("Tengo el oro, pero no hay ruta segura de regreso")
            return

        if self.percepciones[self.pos][2]:
            self.puntaje += 1000
            self.oro = True
            self.anotar("Brillo: agarro el oro +1000; regreso a la salida")
            return

        hoyos_ciertos, hoyos_posibles, wumpus_posibles, wumpus_cierto = self.inferir()

        # 1) Wumpus localizado con certeza (KB |= W[x,y]): dispararle.
        if self.flecha and wumpus_cierto and not self.wumpus_muerto:
            if alineados(self.pos, wumpus_cierto):
                return self.disparar(wumpus_cierto)
            camino = self.bfs(
                lambda c: self.segura(c) and alineados(c, wumpus_cierto),
                self.segura,
            )
            if camino:
                self.anotar(f"Busco alinearme con el Wumpus {coord(wumpus_cierto)}")
                return self.mover(camino[0])

        # 2) Explorar casillas que la KB implica seguras.
        camino = self.bfs(
            lambda c: c not in self.visitadas and self.segura(c), self.segura,
        )
        if camino:
            return self.mover(camino[0])

        # 3) Sin casillas seguras y con hedor: disparar antes de apostar.
        if self.flecha and not self.wumpus_muerto and wumpus_posibles:
            for objetivo in sorted(wumpus_posibles):
                if alineados(self.pos, objetivo):
                    self.anotar("Sin casillas seguras: disparo a un posible Wumpus",
                                detalle=True)
                    return self.disparar(objetivo)
            camino = self.bfs(
                lambda c: self.segura(c) and
                any(alineados(c, w) for w in wumpus_posibles),
                self.segura,
            )
            if camino:
                self.anotar("Sin casillas seguras: me alineo para disparar")
                return self.mover(camino[0])

        # 4) Apostar por la casilla menos riesgosa (la KB no implica que sea segura).
        objetivo = self.objetivo_riesgo(hoyos_ciertos, hoyos_posibles,
                                        wumpus_posibles, wumpus_cierto)
        camino = (self.bfs(lambda c: c == objetivo, self.segura)
                  if objetivo else None)
        if not camino:
            self.anotar("Sin movimientos posibles")
            self.fin = True
            return
        self.anotar(f"Sin casillas seguras: arriesgo {coord(objetivo)}")
        self.mover(camino[0])

    def disparar(self, objetivo):
        self.flecha = False
        self.puntaje -= 10
        origen = self.pos
        grito = self.m.disparar(origen, objetivo)
        self.anotar(f"Disparo hacia {coord(objetivo)} -10")
        if grito:
            self.wumpus_muerto = True
            self.anotar("Grito: Wumpus muerto")
        else:
            # La flecha cruzo toda la linea sin grito: ahi no hay Wumpus (nueva
            # observacion que entra a la KB).
            dx, dy = signo(objetivo[0] - origen[0]), signo(objetivo[1] - origen[1])
            x, y = origen
            while (dx or dy) and 1 <= x + dx <= N and 1 <= y + dy <= N:
                x, y = x + dx, y + dy
                self.descartadas_w.add((x, y))
            self.anotar("Sin grito: la flecha falló")
        self.tell()

    def mover(self, casilla):
        self.pos = casilla
        self.puntaje -= 1
        if self.m.letal(self.pos):
            self.vivo = False
            self.fin = True
            self.puntaje -= 1000
            causa = "Hoyo" if self.pos in self.m.hoyos else "Wumpus"
            self.anotar(f"Me muevo a {coord(self.pos)} -1 · {causa}: "
                        f"el agente murió -1000")
            return
        self.visitadas.add(self.pos)
        self.tell(f"Me muevo a {coord(self.pos)} -1")


def main():
    import tkinter as tk
    from pathlib import Path
    from tkinter import ttk
    from PIL import Image, ImageEnhance, ImageOps, ImageTk

    root = tk.Tk()
    root.title("Wumpus | Agente lógico")
    # La ventana nunca debe ser mas grande que la pantalla (si no, se corta
    # el panel derecho o los botones de abajo).
    ancho_ini = min(1180, root.winfo_screenwidth() - 40)
    alto_ini = min(820, root.winfo_screenheight() - 90)
    root.geometry(f"{ancho_ini}x{alto_ini}")
    root.minsize(min(980, ancho_ini), min(720, alto_ini))
    root.configure(bg="#0b141b")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Wumpus.Primary.TButton", font=("Segoe UI Semibold", 11),
                    foreground="#162126", background="#e3bd72", padding=(18, 8),
                    borderwidth=0)
    style.map("Wumpus.Primary.TButton", background=[("active", "#f0ce87")])
    style.configure("Wumpus.Secondary.TButton", font=("Segoe UI Semibold", 10),
                    foreground="#e4e9e5", background="#26363c", padding=(14, 8),
                    borderwidth=0)
    style.map("Wumpus.Secondary.TButton", background=[("active", "#35494f")])
    style.configure("Wumpus.TCheckbutton", font=("Segoe UI", 9), foreground="#e1e8e7",
                    background="#111c24", padding=5)
    style.map("Wumpus.TCheckbutton", background=[("active", "#111c24")])

    estado = {"mundo": Mundo(), "agente": None, "automatico": False, "after": None}
    mostrar_mundo = tk.BooleanVar(value=False)
    mostrar_kb = tk.BooleanVar(value=False)   # bitacora detallada (razonamiento KB)
    assets_dir = Path(__file__).with_name("Imgs Wumpus")
    background_source = None
    logo_source = None
    try:
        with Image.open(assets_dir / "Fondo juego.jpg") as image:
            background_source = image.convert("RGB")
    except OSError:
        pass
    try:
        with Image.open(assets_dir / "logo universidad.png") as image:
            logo_source = image.convert("RGBA")
    except OSError:
        pass
    wumpus_logo_source = None
    try:
        with Image.open(assets_dir / "LOGO WUMPUS.png") as image:
            wumpus_logo_source = image.convert("RGBA")
    except OSError:
        pass
    sprite_cache = {}
    background_cache = {}
    faltantes = set()

    home = tk.Frame(root, bg="#0b141b")
    game = tk.Frame(root, bg="#0b141b")
    home_canvas = tk.Canvas(home, highlightthickness=0, bg="#0b141b")
    game_canvas = tk.Canvas(game, highlightthickness=0, bg="#0b141b")
    home_canvas.pack(fill="both", expand=True)
    game_canvas.pack(fill="both", expand=True)
    home.place(relwidth=1, relheight=1)
    game.place_forget()

    history = tk.Text(game_canvas, wrap="word", bg="#0b141a", fg="#d3dedd",
                      insertbackground="#e4c47c", font=("Consolas", 9), bd=0,
                      padx=12, pady=10, relief="flat", state="disabled")
    # Acciones: lineas cortas y legibles. Detalle KB: mas pequeno, con sangria
    # francesa para que, si se parte, no se confunda con una accion.
    history.tag_configure("accion", foreground="#e1e8e7", spacing3=3)
    history.tag_configure("kb", foreground="#86a9a6", font=("Consolas", 8),
                          lmargin1=16, lmargin2=28, spacing3=2)
    scrollbar = ttk.Scrollbar(game_canvas, orient="vertical", command=history.yview)
    history.configure(yscrollcommand=scrollbar.set)
    logo_photos = {"university": None, "wumpus": None}

    def tamano(canvas):
        """Tamano real del canvas (sin forzar un minimo mayor que la ventana)."""
        w, h = canvas.winfo_width(), canvas.winfo_height()
        return (w if w > 1 else ancho_ini), (h if h > 1 else alto_ini)

    def background_photo(size):
        if size not in background_cache:
            if len(background_cache) >= 2:
                background_cache.clear()  # evita acumular un fondo por cada resize
            if background_source is None:
                gradient = Image.linear_gradient("L").resize(size)
                image = ImageOps.colorize(gradient, black="#091218", white="#1b3038")
            else:
                image = ImageOps.fit(background_source, size,
                                     method=Image.Resampling.LANCZOS)
                image = ImageEnhance.Color(image).enhance(0.62)
                image = ImageEnhance.Brightness(image).enhance(0.52)
                image = Image.blend(image, Image.new("RGB", size, "#071117"), 0.38)
            background_cache[size] = ImageTk.PhotoImage(image)
        return background_cache[size]

    def sprite_photo(filename, size, fit=False):
        key = (filename, size, fit)
        if key not in sprite_cache:
            try:
                with Image.open(assets_dir / filename) as image:
                    sprite = image.convert("RGBA")
            except OSError:
                if filename not in faltantes:
                    faltantes.add(filename)
                    print(f"[aviso] Falta la imagen: {filename}")
                sprite = Image.new("RGBA", size,
                                   "#26363c" if fit else (0, 0, 0, 0))
            if fit:
                sprite = ImageOps.fit(sprite, size, method=Image.Resampling.LANCZOS)
            else:
                sprite.thumbnail(size, Image.Resampling.LANCZOS)
            sprite_cache[key] = ImageTk.PhotoImage(sprite)
        return sprite_cache[key]

    def draw_home():
        width, height = tamano(home_canvas)
        home_canvas.delete("scene")
        home_canvas.create_image(0, 0, anchor="nw",
                                 image=background_photo((width, height)), tags="scene")
        home_canvas.create_rectangle(0, 0, width, height, fill="#071117",
                                     stipple="gray50", outline="", tags="scene")
        home_canvas.create_rectangle(32, 26, width - 32, 88, fill="#101a21",
                                     outline="#354850", tags="scene")
        home_canvas.create_text(58, 46, anchor="nw", text="WUMPUS  /  AGENTE LÓGICO",
                                font=("Segoe UI Semibold", 12), fill="#e3bd72",
                                tags="scene")
        if logo_source is not None:
            home_canvas.create_rectangle(width - 360, 28, width - 42, 86,
                                         fill="#f7f5ef", outline="#d7d0c2",
                                         tags="scene")
            university_logo = ImageOps.contain(
                logo_source, (300, 54), method=Image.Resampling.LANCZOS,
            )
            logo_photos["university"] = ImageTk.PhotoImage(university_logo)
            home_canvas.create_image(width - 201, 57,
                                     image=logo_photos["university"], tags="scene")

        logo_x, logo_y = width * 0.25, height * 0.48
        if wumpus_logo_source is not None:
            wumpus_logo = ImageOps.contain(
                wumpus_logo_source, (300, 340), method=Image.Resampling.LANCZOS,
            )
            logo_photos["wumpus"] = ImageTk.PhotoImage(wumpus_logo)
            home_canvas.create_image(logo_x, logo_y, image=logo_photos["wumpus"],
                                     tags="scene")
        else:
            home_canvas.create_oval(logo_x - 112, logo_y - 112, logo_x + 112,
                                    logo_y + 112, outline="#b78c4d", width=2,
                                    tags="scene")
            home_canvas.create_oval(logo_x - 96, logo_y - 96, logo_x + 96,
                                    logo_y + 96, outline="#52645f", width=1,
                                    tags="scene")
            home_canvas.create_text(logo_x, logo_y - 8, text="W",
                                    font=("Georgia", 82, "bold"), fill="#e3bd72",
                                    tags="scene")
            home_canvas.create_text(logo_x, logo_y + 68,
                                    text="CUEVA  /  LÓGICA  /  ORO",
                                    font=("Segoe UI Semibold", 8), fill="#b4c0b9",
                                    tags="scene")

        text_x = width * 0.51
        home_canvas.create_text(text_x, height * 0.20, anchor="nw",
                                text="AVENTURA DE INTELIGENCIA ARTIFICIAL",
                                font=("Segoe UI Semibold", 9), fill="#e3bd72",
                                tags="scene")
        home_canvas.create_text(text_x - 2, height * 0.255, anchor="nw",
                                text="Bienvenido a", font=("Segoe UI Light", 27),
                                fill="#edf0e8", tags="scene")
        home_canvas.create_text(text_x - 5, height * 0.315, anchor="nw",
                                text="Wumpus", font=("Segoe UI Semibold", 54),
                                fill="#f0cc7d", tags="scene")
        home_canvas.create_text(text_x, height * 0.425, anchor="nw",
                                text="Explora la cueva. Interpreta las señales.\n"
                                     "Encuentra el oro y vuelve con vida.",
                                font=("Segoe UI", 12), fill="#d4dfdc", justify="left",
                                tags="scene")
        credit_top = height * 0.555
        home_canvas.create_rectangle(text_x, credit_top, width * 0.88,
                                     credit_top + 132, fill="#111c22",
                                     outline="#46564f", tags="scene")
        home_canvas.create_rectangle(text_x, credit_top, text_x + 3,
                                     credit_top + 132, fill="#bd4540", outline="",
                                     tags="scene")
        home_canvas.create_text(text_x + 20, credit_top + 16, anchor="nw",
                                text="REALIZADO POR", font=("Segoe UI Semibold", 9),
                                fill="#e3bd72", tags="scene")
        home_canvas.create_text(text_x + 20, credit_top + 42, anchor="nw",
                                text="Paula Romero\nYessica Triana\nDanna Soler",
                                font=("Segoe UI Semibold", 11), fill="#e8ece7",
                                justify="left", tags="scene")
        home_canvas.coords(play_window, width * 0.64, height * 0.82)
        home_canvas.coords(exit_window, width * 0.82, height * 0.82)

    def draw_game():
        agent, world = estado["agente"], estado["mundo"]
        if agent is None:
            return
        width, height = tamano(game_canvas)
        game_canvas.delete("scene")
        if len(sprite_cache) > 120:
            sprite_cache.clear()  # los items ya se borraron, es seguro liberar
        game_canvas.create_image(0, 0, anchor="nw",
                                 image=background_photo((width, height)), tags="scene")
        game_canvas.create_rectangle(0, 0, width, height, fill="#071117",
                                     stipple="gray50", outline="", tags="scene")
        game_canvas.create_rectangle(28, 20, width - 28, 108, fill="#101a21",
                                     outline="#354850", tags="scene")
        game_canvas.create_text(50, 34, anchor="nw", text="MUNDO DEL WUMPUS",
                                font=("Segoe UI Semibold", 21), fill="#edf0e8",
                                tags="scene")
        game_canvas.create_text(52, 70, anchor="nw",
                                text=f"AGENTE LÓGICO  /  {world.nombre.upper()}",
                                font=("Segoe UI", 9), fill="#9eafb1", tags="scene")
        if not agent.vivo:
            status = "DERROTADO"
        elif agent.fin and agent.oro and agent.pos == (1, 1):
            status = "ESCAPÓ CON ORO"
        elif agent.fin and agent.oro:
            status = "ORO, SIN REGRESO"
        elif agent.oro:
            status = "REGRESANDO CON ORO"
        elif agent.fin:
            status = "SIN SALIDA"
        else:
            status = "EXPLORANDO"
        metrics = [("PUNTAJE", str(agent.puntaje)), ("ESTADO", status),
                   ("FLECHA", "DISPONIBLE" if agent.flecha else "USADA")]
        box_w, gap = 150, 8
        start = width - 28 - 14 - (3 * box_w + 2 * gap)
        for index, (label, value) in enumerate(metrics):
            left = start + index * (box_w + gap)
            game_canvas.create_rectangle(left, 32, left + box_w, 92,
                                         fill="#18262e", outline="#3b4d53",
                                         tags="scene")
            game_canvas.create_text(left + 10, 41, anchor="nw", text=label,
                                    font=("Segoe UI", 8), fill="#9eafb1", tags="scene")
            game_canvas.create_text(left + 10, 62, anchor="nw", text=value,
                                    font=("Segoe UI Semibold", 10),
                                    fill="#e5c276" if index == 0 else "#e1e8e7",
                                    tags="scene")

        # --- Layout: el tablero se encoge si hace falta para que el panel
        # derecho (bitacora) SIEMPRE quepa dentro de la ventana. ---
        board_x, board_y = 46, 170
        sidebar_gap, right_margin, min_sidebar = 38, 40, 340
        cell_size = min(140,
                        (height - 300) / N,
                        (width - board_x - sidebar_gap - right_margin - min_sidebar) / N)
        cell_size = max(cell_size, 64)
        board_size = cell_size * N

        reveal = mostrar_mundo.get() or agent.fin or not agent.vivo
        if reveal:
            game_canvas.create_text(board_x, board_y - 31, anchor="nw",
                                    text="MAPA  ·  MUNDO REAL REVELADO",
                                    font=("Segoe UI Semibold", 11), fill="#b9a6f0",
                                    tags="scene")
        else:
            game_canvas.create_text(board_x, board_y - 31, anchor="nw",
                                    text="MAPA DE EXPLORACIÓN",
                                    font=("Segoe UI Semibold", 11), fill="#e7ece8",
                                    tags="scene")
        game_canvas.create_rectangle(board_x - 7, board_y - 7,
                                     board_x + board_size + 7,
                                     board_y + board_size + 7, fill="#101a21",
                                     outline="#9b86d9" if reveal else "#465961",
                                     tags="scene")
        pits, possible_pits, possible_wumpus, certain_wumpus = agent.inferir()
        floor_sprites = (
            "Casilla 1.png",
            "casilla 2 medio quebrada.png",
            "cadilla 3 llena de musgo y quebrada.png",
            "casilla 4 llena de musgo.png",
            "hoyo escondido.png",
        )
        for row, y in enumerate(range(N, 0, -1)):
            for column, x in enumerate(range(1, N + 1)):
                cell = (x, y)
                left, top = board_x + column * cell_size, board_y + row * cell_size
                right, bottom = left + cell_size, top + cell_size
                if cell in agent.visitadas:
                    outline, label = "#6d9290", "VISITADA"
                elif agent.segura(cell):
                    outline, label = "#73a88f", "SEGURA"
                elif cell in pits or cell == certain_wumpus:
                    outline = "#ce7166"
                    label = "HOYO" if cell in pits else "WUMPUS"
                elif cell in possible_pits or cell in possible_wumpus:
                    outline = "#d1ad62"
                    hints = []
                    if cell in possible_pits:
                        hints.append("HOYO?")
                    if cell in possible_wumpus:
                        hints.append("WUMPUS?")
                    label = " / ".join(hints)
                else:
                    outline, label = "#354850", ""

                sprite = None
                real_only = False   # contenido tomado del mundo real, no deducido
                if reveal:
                    if cell in world.hoyos:
                        sprite, label = "hoyo revelado.png", "HOYO"
                        real_only = cell not in pits
                    elif cell == world.wumpus:
                        sprite, label = "wumpus revelado.png", "WUMPUS"
                        real_only = cell != certain_wumpus
                    elif cell == world.oro:
                        sprite, label = "cofre brillante.png", "ORO"
                        real_only = cell not in agent.visitadas
                if sprite is None:
                    if cell in pits:
                        sprite, label = "hoyo revelado.png", "HOYO"
                    elif cell == certain_wumpus:
                        sprite, label = "wumpus escondido.png", "WUMPUS?"
                    elif cell in possible_wumpus:
                        sprite, label = "wumpus escondido.png", "W?"
                    elif cell == world.oro and cell in agent.visitadas:
                        sprite, label = "cofre brillante.png", "ORO"

                tile = floor_sprites[(x + 2 * y) % len(floor_sprites)]
                tile_photo = sprite_photo(tile, (int(cell_size - 6), int(cell_size - 6)), fit=True)
                game_canvas.create_image((left + right) / 2, (top + bottom) / 2,
                                         image=tile_photo, tags="scene")
                if real_only:
                    # Violeta punteado = lo ve el jugador porque el mundo esta
                    # revelado, pero el agente NO lo habia deducido.
                    game_canvas.create_rectangle(left + 3, top + 3, right - 3,
                                                 bottom - 3, fill="",
                                                 outline="#9b86d9", width=3,
                                                 dash=(7, 4), tags="scene")
                else:
                    game_canvas.create_rectangle(left + 3, top + 3, right - 3,
                                                 bottom - 3, fill="",
                                                 outline=outline,
                                                 width=3 if cell == agent.pos else 2,
                                                 tags="scene")
                if sprite:
                    icon_size = int(cell_size * 0.65)
                    icon = sprite_photo(sprite, (icon_size, icon_size))
                    game_canvas.create_image((left + right) / 2,
                                             (top + bottom) / 2 - 5,
                                             image=icon, tags="scene")
                if real_only:
                    label = f"{label} · REAL"
                if cell == agent.pos:
                    explorer_size = int(cell_size * 0.52)
                    explorer = sprite_photo("explorador.png",
                                            (explorer_size, explorer_size))
                    game_canvas.create_image((left + right) / 2,
                                             (top + bottom) / 2 - 5,
                                             image=explorer, tags="scene")
                    label = "AGENTE" if not label else "AGENTE / " + label
                # Coordenadas con fondo oscuro para que se lean sobre cualquier tile.
                game_canvas.create_rectangle(left + 6, top + 6, left + 46, top + 23,
                                             fill="#101a21", outline="", tags="scene")
                game_canvas.create_text(left + 11, top + 8, anchor="nw",
                                        text=f"{x}, {y}", font=("Segoe UI", 8),
                                        fill="#c3d0cf", tags="scene")
                if label:
                    game_canvas.create_rectangle(left + 7, bottom - 22,
                                                 right - 7, bottom - 4,
                                                 fill="#101a21", outline="",
                                                 tags="scene")
                    game_canvas.create_text((left + right) / 2, bottom - 13,
                                            text=label,
                                            font=("Segoe UI Semibold", 8),
                                            fill="#d9ccff" if real_only else "#f0eadb",
                                            width=cell_size - 16,
                                            tags="scene")

        legend = "HEDOR: Wumpus cerca   /   BRISA: hoyo cerca   /   BRILLO: oro"
        if reveal:
            legend += ("\nBorde violeta punteado (REAL): contenido del mundo real "
                       "que el agente no había deducido.")
        game_canvas.create_text(board_x, board_y + board_size + 16, anchor="nw",
                                text=legend, font=("Segoe UI", 8),
                                fill="#bac8c6", width=board_size, tags="scene")

        # --- Panel derecho: nunca se sale de la ventana. ---
        sidebar_x = board_x + board_size + sidebar_gap
        sidebar_width = max(width - sidebar_x - right_margin, 260)
        text_w = sidebar_width - 32
        panel_top = board_y - 12
        game_canvas.create_rectangle(sidebar_x, panel_top, sidebar_x + sidebar_width,
                                     panel_top + 150, fill="#101a21",
                                     outline="#354850", tags="scene")
        game_canvas.create_text(sidebar_x + 16, panel_top + 14, anchor="nw",
                                text="ESTADO DEL AGENTE",
                                font=("Segoe UI Semibold", 11), fill="#e7ece8",
                                tags="scene")
        game_canvas.create_text(sidebar_x + 16, panel_top + 44, anchor="nw",
                                text=f"POSICIÓN   {agent.pos[0]}, {agent.pos[1]}"
                                     f"     VISITADAS   {len(agent.visitadas)}",
                                font=("Segoe UI", 9), fill="#bdccca", width=text_w,
                                tags="scene")
        perception = agent.percepciones.get(agent.pos, [0, 0, 0, 0, 0])
        active = [name.upper() for name, value in zip(NOMBRES_PERCEPCION, perception)
                  if value]
        sensors = "  /  ".join(active) if active else "SIN SEÑALES"
        game_canvas.create_text(sidebar_x + 16, panel_top + 79, anchor="nw",
                                text="PERCEPCIÓN ACTUAL",
                                font=("Segoe UI Semibold", 8), fill="#8fa5a7",
                                tags="scene")
        game_canvas.create_text(sidebar_x + 16, panel_top + 98, anchor="nw",
                                text=sensors, font=("Segoe UI Semibold", 10),
                                fill="#e5c276", width=text_w, tags="scene")
        game_canvas.create_text(sidebar_x + 16, panel_top + 126, anchor="nw",
                                text=f"KB: {agent.n_modelos_hoyos} modelos de hoyos"
                                     f" / {agent.n_modelos_wumpus} de Wumpus",
                                font=("Segoe UI", 9), fill="#bdccca", width=text_w,
                                tags="scene")
        log_y = panel_top + 170
        log_height = max(height - 90 - log_y, 120)
        game_canvas.create_rectangle(sidebar_x, log_y, sidebar_x + sidebar_width,
                                     log_y + log_height, fill="#101a21",
                                     outline="#354850", tags="scene")
        game_canvas.create_text(sidebar_x + 16, log_y + 12, anchor="nw",
                                text="BITÁCORA", font=("Segoe UI Semibold", 11),
                                fill="#e7ece8", tags="scene")
        if mostrar_kb.get():
            game_canvas.create_text(sidebar_x + sidebar_width - 16, log_y + 15,
                                    anchor="ne", text="RAZONAMIENTO KB ACTIVADO",
                                    font=("Segoe UI", 8), fill="#86a9a6",
                                    tags="scene")
        game_canvas.coords(history_window, sidebar_x + 10, log_y + 42)
        game_canvas.itemconfigure(history_window, width=sidebar_width - 36,
                                  height=log_height - 52)
        game_canvas.coords(scrollbar_window, sidebar_x + sidebar_width - 23, log_y + 42)
        game_canvas.itemconfigure(scrollbar_window, height=log_height - 52)

        # Bitacora: nivel 0 (acciones) siempre; nivel 1 (KB) solo si se pide.
        detalle = mostrar_kb.get()
        lineas = [(n, t) for n, t in agent.log if detalle or n == 0][-150:]
        history.configure(state="normal")
        history.delete("1.0", "end")
        for nivel, texto in lineas:
            history.insert("end", texto + "\n", "kb" if nivel else "accion")
        history.configure(state="disabled")
        history.see("end")

        total = sum(w for _, w in game_controls) + 7 * (len(game_controls) - 1)
        control_x = max((width - total) / 2, 8)
        for window, (_, control_width) in zip(game_windows, game_controls):
            game_canvas.coords(window, control_x + control_width / 2, height - 40)
            game_canvas.itemconfigure(window, width=control_width, height=44)
            control_x += control_width + 7

    def step_once():
        estado["agente"].paso()
        draw_game()

    def stop_auto():
        estado["automatico"] = False
        if estado["after"] is not None:
            root.after_cancel(estado["after"])
            estado["after"] = None
        auto_button.configure(text="Automático")

    def automatic_tick():
        estado["after"] = None
        agent = estado["agente"]
        if not estado["automatico"] or not agent.vivo or agent.fin:
            stop_auto()
            return
        step_once()
        if agent.vivo and not agent.fin:
            estado["after"] = root.after(650, automatic_tick)
        else:
            stop_auto()

    def toggle_auto():
        if estado["automatico"]:
            stop_auto()
            return
        agent = estado["agente"]
        if not agent.vivo or agent.fin:
            return
        estado["automatico"] = True
        auto_button.configure(text="Pausar")
        automatic_tick()

    def reset_game(aleatorio=False, sin_salida=False):
        stop_auto()
        estado["mundo"] = Mundo(aleatorio=aleatorio, sin_salida=sin_salida)
        estado["agente"] = Agente(estado["mundo"])
        draw_game()

    def start_game():
        reset_game()
        home.place_forget()
        game.place(relwidth=1, relheight=1)
        game.lift()
        draw_game()

    def return_home():
        stop_auto()
        game.place_forget()
        home.place(relwidth=1, relheight=1)
        home.lift()
        draw_home()

    play_button = ttk.Button(home_canvas, text="JUGAR", style="Wumpus.Primary.TButton",
                             command=start_game)
    exit_button = ttk.Button(home_canvas, text="SALIR", style="Wumpus.Secondary.TButton",
                             command=root.destroy)
    play_window = home_canvas.create_window(0, 0, window=play_button, width=190, height=52)
    exit_window = home_canvas.create_window(0, 0, window=exit_button, width=130, height=52)

    auto_button = ttk.Button(game_canvas, text="Automático",
                             style="Wumpus.Secondary.TButton", command=toggle_auto)
    world_menu = tk.Menu(root, tearoff=False)
    world_menu.add_command(label="Mundo clásico", command=reset_game)
    world_menu.add_command(
        label="Mundo aleatorio",
        command=lambda: reset_game(aleatorio=True),
    )
    world_menu.add_command(
        label="Caso sin salida",
        command=lambda: reset_game(sin_salida=True),
    )

    def show_world_menu():
        try:
            world_menu.tk_popup(root.winfo_pointerx(), root.winfo_pointery())
        finally:
            world_menu.grab_release()

    game_controls = [
        (ttk.Button(game_canvas, text="Un paso", style="Wumpus.Primary.TButton",
                    command=step_once), 94),
        (auto_button, 116),
        (ttk.Button(game_canvas, text="Reiniciar", style="Wumpus.Secondary.TButton",
                    command=reset_game), 102),
        (ttk.Button(game_canvas, text="Escenarios",
                    style="Wumpus.Secondary.TButton",
                    command=show_world_menu), 120),
        (ttk.Button(game_canvas, text="Inicio", style="Wumpus.Secondary.TButton",
                    command=return_home), 82),
        (ttk.Checkbutton(game_canvas, text="Ver mundo real", variable=mostrar_mundo,
                         style="Wumpus.TCheckbutton", command=draw_game), 136),
        (ttk.Checkbutton(game_canvas, text="Ver razonamiento (KB)",
                         variable=mostrar_kb, style="Wumpus.TCheckbutton",
                         command=draw_game), 188),
    ]
    game_windows = [game_canvas.create_window(0, 0, window=widget)
                    for widget, _ in game_controls]
    history_window = game_canvas.create_window(0, 0, anchor="nw", window=history)
    scrollbar_window = game_canvas.create_window(0, 0, anchor="nw", window=scrollbar)

    home_canvas.bind(
        "<Configure>",
        lambda event: draw_home() if event.width > 0 and event.height > 0 else None,
    )
    game_canvas.bind(
        "<Configure>",
        lambda event: draw_game() if event.width > 0 and event.height > 0 else None,
    )
    root.after_idle(draw_home)
    root.mainloop()


if __name__ == "__main__":
    main()