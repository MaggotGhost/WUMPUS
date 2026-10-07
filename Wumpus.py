"""Wumpus: agente logico y simulador grafico."""

##HECHO POR
##PAULA ROMERO
##YESSICA TRIANA
##DANNA SOLER

import random
from collections import deque

N = 4


def vecinos(c):
    x, y = c
    return [(a, b) for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if 1 <= a <= N and 1 <= b <= N]


class Mundo:
    """Entorno real: el agente no ve directamente sus contenidos."""

    def __init__(self, aleatorio=False):
        self.grito = False
        if aleatorio:
            libres = [(x, y) for x in range(1, N + 1) for y in range(1, N + 1)
                      if (x, y) != (1, 1)]
            self.wumpus, self.oro = random.sample(libres, 2)
            self.hoyos = {c for c in libres if c not in (self.wumpus, self.oro)
                          and random.random() < 0.2}
        else:
            self.hoyos = {(3, 1), (3, 3), (4, 4)}
            self.wumpus, self.oro = (1, 3), (2, 3)

    def disparar(self, origen, objetivo):
        dx = (objetivo[0] > origen[0]) - (objetivo[0] < origen[0])
        dy = (objetivo[1] > origen[1]) - (objetivo[1] < origen[1])
        self.grito = False
        if dx and dy:
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
        self.sin_hoyo = {self.pos}
        self.sin_wumpus = {self.pos}
        self.percepciones = {}
        self.puntaje, self.vivo, self.fin = 0, True, False
        self.flecha, self.wumpus_muerto = True, False
        self.log = []
        self.tell()

    def tell(self):
        percepcion = self.m.percibir(self.pos)
        self.percepciones[self.pos] = percepcion
        self.log.append(f"En {self.pos}: [S,B,G,Bu,Sc]={percepcion}")
        self.sin_hoyo.add(self.pos)
        self.sin_wumpus.add(self.pos)
        for casilla in vecinos(self.pos):
            if not percepcion[0]:
                self.sin_wumpus.add(casilla)
            if not percepcion[1]:
                self.sin_hoyo.add(casilla)
        if not percepcion[0] and not percepcion[1]:
            self.log.append(f"  Sin hedor ni brisa: vecinas de {self.pos} seguras")

    def segura(self, casilla):
        return casilla in self.sin_hoyo and casilla in self.sin_wumpus

    def inferir(self):
        hoyos_seguros, hoyos_posibles = set(), set()
        for casilla, percepcion in self.percepciones.items():
            if percepcion[1]:
                candidatas = [vecina for vecina in vecinos(casilla)
                              if vecina not in self.sin_hoyo]
                hoyos_posibles.update(candidatas)
                if len(candidatas) == 1:
                    hoyos_seguros.add(candidatas[0])

        wumpus_posibles = None
        for casilla, percepcion in self.percepciones.items():
            if percepcion[0]:
                candidatas = {vecina for vecina in vecinos(casilla)
                              if vecina not in self.sin_wumpus}
                wumpus_posibles = (candidatas if wumpus_posibles is None
                                   else wumpus_posibles & candidatas)
        wumpus_posibles = wumpus_posibles or set()
        wumpus_seguro = next(iter(wumpus_posibles)) if len(wumpus_posibles) == 1 else None
        return hoyos_seguros, hoyos_posibles, wumpus_posibles, wumpus_seguro

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

    def paso(self):
        if not self.vivo or self.fin:
            return
        if self.percepciones[self.pos][2]:
            self.puntaje += 1000
            self.fin = True
            self.log.append("Brillo: agarro el oro (+1000)")
            return

        hoyos_seguros, _, _, wumpus_seguro = self.inferir()
        if self.flecha and wumpus_seguro and not self.wumpus_muerto:
            if self.pos[0] == wumpus_seguro[0] or self.pos[1] == wumpus_seguro[1]:
                return self.disparar(wumpus_seguro)
            camino = self.bfs(
                lambda c: self.segura(c) and
                (c[0] == wumpus_seguro[0] or c[1] == wumpus_seguro[1]),
                self.segura,
            )
            if camino:
                self.log.append(f"Wumpus en {wumpus_seguro}: busco alinearme para disparar.")
                return self.mover(camino[0])

        camino = self.bfs(
            lambda c: c not in self.visitadas and self.segura(c), self.segura,
        )
        if not camino:
            self.log.append("Sin casillas seguras nuevas: asumo un riesgo.")
            camino = self.bfs(
                lambda c: c not in self.visitadas and c not in hoyos_seguros
                and c != wumpus_seguro,
                self.segura,
            )
        if not camino:
            self.log.append("Sin movimientos posibles.")
            self.fin = True
            return
        self.mover(camino[0])

    def disparar(self, objetivo):
        self.flecha = False
        self.puntaje -= 10
        grito = self.m.disparar(self.pos, objetivo)
        self.log.append(f"Disparo desde {self.pos} hacia {objetivo} (-10)")
        if grito:
            self.wumpus_muerto = True
            self.sin_wumpus |= {(x, y) for x in range(1, N + 1)
                                for y in range(1, N + 1)}
        self.tell()
        if grito:
            self.log.append("Grito: el Wumpus murio; ya no hay peligro de Wumpus.")
        else:
            self.log.append("Sin grito: la flecha fallo.")

    def mover(self, casilla):
        self.pos = casilla
        self.puntaje -= 1
        self.log.append(f"Me muevo a {self.pos} (-1)")
        if self.pos in self.m.hoyos or self.pos == self.m.wumpus:
            self.vivo = False
            self.puntaje -= 1000
            self.log.append("El agente murio (-1000)")
            return
        self.visitadas.add(self.pos)
        self.tell()


def main():
    import tkinter as tk
    from pathlib import Path
    from tkinter import ttk
    from PIL import Image, ImageEnhance, ImageOps, ImageTk

    root = tk.Tk()
    root.title("Wumpus | Agente lógico")
    root.geometry("1180x820")
    root.minsize(980, 720)
    root.configure(bg="#0b141b")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Wumpus.Primary.TButton", font=("Segoe UI Semibold", 11),
                    foreground="#162126", background="#e3bd72", padding=(18, 11),
                    borderwidth=0)
    style.map("Wumpus.Primary.TButton", background=[("active", "#f0ce87")])
    style.configure("Wumpus.Secondary.TButton", font=("Segoe UI Semibold", 10),
                    foreground="#e4e9e5", background="#26363c", padding=(14, 9),
                    borderwidth=0)
    style.map("Wumpus.Secondary.TButton", background=[("active", "#35494f")])
    style.configure("Wumpus.TCheckbutton", font=("Segoe UI", 9), foreground="#e1e8e7",
                    background="#111c24", padding=5)
    style.map("Wumpus.TCheckbutton", background=[("active", "#111c24")])

    estado = {"mundo": Mundo(), "agente": None, "automatico": False}
    mostrar_mundo = tk.BooleanVar(value=False)
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
    scrollbar = ttk.Scrollbar(game_canvas, orient="vertical", command=history.yview)
    history.configure(yscrollcommand=scrollbar.set)
    logo_photos = {"university": None, "wumpus": None}

    def background_photo(size):
        if size not in background_cache:
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
            path = assets_dir / filename
            with Image.open(path) as image:
                sprite = image.convert("RGBA")
            if fit:
                sprite = ImageOps.fit(sprite, size, method=Image.Resampling.LANCZOS)
            else:
                sprite.thumbnail(size, Image.Resampling.LANCZOS)
            sprite_cache[key] = ImageTk.PhotoImage(sprite)
        return sprite_cache[key]

    def draw_home():
        width = max(home_canvas.winfo_width(), 980)
        height = max(home_canvas.winfo_height(), 720)
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
        width = max(game_canvas.winfo_width(), 980)
        height = max(game_canvas.winfo_height(), 720)
        game_canvas.delete("scene")
        game_canvas.create_image(0, 0, anchor="nw",
                                 image=background_photo((width, height)), tags="scene")
        game_canvas.create_rectangle(0, 0, width, height, fill="#071117",
                                     stipple="gray50", outline="", tags="scene")
        game_canvas.create_rectangle(28, 20, width - 28, 108, fill="#101a21",
                                     outline="#354850", tags="scene")
        agent, world = estado["agente"], estado["mundo"]
        game_canvas.create_text(50, 34, anchor="nw", text="MUNDO DEL WUMPUS",
                                font=("Segoe UI Semibold", 21), fill="#edf0e8",
                                tags="scene")
        game_canvas.create_text(52, 70, anchor="nw",
                                text="AGENTE LÓGICO  /  EXPLORACIÓN",
                                font=("Segoe UI", 9), fill="#9eafb1", tags="scene")
        status = "DERROTADO" if not agent.vivo else "ORO RECUPERADO" if agent.fin else "EXPLORANDO"
        metrics = [("PUNTAJE", str(agent.puntaje)), ("ESTADO", status),
                   ("FLECHA", "DISPONIBLE" if agent.flecha else "USADA")]
        for index, (label, value) in enumerate(metrics):
            left = width - 370 + index * 112
            game_canvas.create_rectangle(left, 32, left + 104, 92,
                                         fill="#18262e", outline="#3b4d53",
                                         tags="scene")
            game_canvas.create_text(left + 10, 41, anchor="nw", text=label,
                                    font=("Segoe UI", 8), fill="#9eafb1", tags="scene")
            game_canvas.create_text(left + 10, 62, anchor="nw", text=value,
                                    font=("Segoe UI Semibold", 10),
                                    fill="#e5c276" if index == 0 else "#e1e8e7",
                                    tags="scene")

        cell_size = max(88, min(140, (height - 320) / N, (width * 0.48) / N))
        board_size = cell_size * N
        board_x, board_y = 46, 218
        game_canvas.create_text(board_x, board_y - 31, anchor="nw",
                                text="MAPA DE EXPLORACIÓN",
                                font=("Segoe UI Semibold", 11), fill="#e7ece8",
                                tags="scene")
        game_canvas.create_rectangle(board_x - 7, board_y - 7,
                                     board_x + board_size + 7,
                                     board_y + board_size + 7, fill="#101a21",
                                     outline="#465961", tags="scene")
        pits, possible_pits, possible_wumpus, certain_wumpus = agent.inferir()
        reveal = mostrar_mundo.get() or agent.fin or not agent.vivo
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
                if reveal:
                    if cell in world.hoyos:
                        sprite = "hoyo revelado.png"
                        label = "HOYO"
                    elif cell == world.wumpus:
                        sprite = "wumpus revelado.png"
                        label = "WUMPUS"
                    elif cell == world.oro and cell in agent.visitadas:
                        sprite = "cofre brillante.png"
                        label = "ORO"
                elif cell in pits:
                    sprite, label = "hoyo revelado.png", "HOYO"
                elif cell == certain_wumpus:
                    sprite, label = "wumpus escondido.png", "WUMPUS?"
                elif cell in possible_wumpus:
                    sprite, label = "wumpus escondido.png", "W?"

                if cell == world.oro and (reveal or cell in agent.visitadas):
                    sprite, label = "cofre brillante.png", "ORO"

                tile = floor_sprites[(x + 2 * y) % len(floor_sprites)]
                tile_photo = sprite_photo(tile, (int(cell_size - 6), int(cell_size - 6)), fit=True)
                game_canvas.create_image((left + right) / 2, (top + bottom) / 2,
                                         image=tile_photo, tags="scene")
                game_canvas.create_rectangle(left + 3, top + 3, right - 3, bottom - 3,
                                             fill="", outline=outline,
                                             width=3 if cell == agent.pos else 2,
                                             tags="scene")
                game_canvas.create_text(left + 11, top + 9, anchor="nw",
                                        text=f"{x}, {y}", font=("Segoe UI", 8),
                                        fill="#a6b5b5", tags="scene")
                if sprite:
                    icon_size = int(cell_size * 0.65)
                    icon = sprite_photo(sprite, (icon_size, icon_size))
                    game_canvas.create_image((left + right) / 2,
                                             (top + bottom) / 2 - 5,
                                             image=icon, tags="scene")
                if cell == agent.pos:
                    explorer_size = int(cell_size * 0.52)
                    explorer = sprite_photo("explorador.png",
                                            (explorer_size, explorer_size))
                    game_canvas.create_image((left + right) / 2,
                                             (top + bottom) / 2 - 5,
                                             image=explorer, tags="scene")
                    label = "AGENTE" if not label else "AGENTE / " + label
                if label:
                    game_canvas.create_rectangle(left + 7, bottom - 22,
                                                 right - 7, bottom - 4,
                                                 fill="#101a21", outline="",
                                                 tags="scene")
                    game_canvas.create_text((left + right) / 2, bottom - 13,
                                            text=label,
                                            font=("Segoe UI Semibold", 8),
                                            fill="#f0eadb", width=cell_size - 16,
                                            tags="scene")

        sidebar_x = board_x + board_size + 38
        sidebar_width = width - sidebar_x - 40
        game_canvas.create_rectangle(sidebar_x, 206, sidebar_x + sidebar_width, 356,
                                     fill="#101a21", outline="#354850", tags="scene")
        game_canvas.create_text(sidebar_x + 16, 220, anchor="nw",
                                text="ESTADO DEL AGENTE",
                                font=("Segoe UI Semibold", 11), fill="#e7ece8",
                                tags="scene")
        game_canvas.create_text(sidebar_x + 16, 250, anchor="nw",
                                text=f"POSICIÓN   {agent.pos[0]}, {agent.pos[1]}"
                                     f"     VISITADAS   {len(agent.visitadas)}",
                                font=("Segoe UI", 9), fill="#bdccca", tags="scene")
        perception = agent.percepciones.get(agent.pos, [0, 0, 0, 0, 0])
        names = ("HEDOR", "BRISA", "BRILLO", "GOLPE", "GRITO")
        active = [name for name, value in zip(names, perception) if value]
        sensors = "  /  ".join(active) if active else "SIN SEÑALES"
        game_canvas.create_text(sidebar_x + 16, 285, anchor="nw",
                                text="PERCEPCIÓN ACTUAL",
                                font=("Segoe UI Semibold", 8), fill="#8fa5a7",
                                tags="scene")
        game_canvas.create_text(sidebar_x + 16, 304, anchor="nw", text=sensors,
                                font=("Segoe UI Semibold", 10), fill="#e5c276",
                                tags="scene")
        log_y, log_height = 375, height - 465
        game_canvas.create_rectangle(sidebar_x, log_y, sidebar_x + sidebar_width,
                                     log_y + log_height, fill="#101a21",
                                     outline="#354850", tags="scene")
        game_canvas.create_text(sidebar_x + 16, log_y + 12, anchor="nw",
                                text="BITÁCORA", font=("Segoe UI Semibold", 11),
                                fill="#e7ece8", tags="scene")
        game_canvas.coords(history_window, sidebar_x + 10, log_y + 42)
        game_canvas.itemconfigure(history_window, width=sidebar_width - 36,
                                  height=log_height - 52)
        game_canvas.coords(scrollbar_window, sidebar_x + sidebar_width - 23, log_y + 42)
        game_canvas.itemconfigure(scrollbar_window, height=log_height - 52)
        history.configure(state="normal")
        history.delete("1.0", "end")
        history.insert("end", "\n".join(agent.log[-80:]))
        history.configure(state="disabled")
        history.see("end")
        game_canvas.create_text(board_x, board_y + board_size + 20, anchor="nw",
                                text="HEDOR: Wumpus cerca   /   BRISA: hoyo cerca   /   BRILLO: oro",
                                font=("Segoe UI", 8), fill="#bac8c6", tags="scene")

        total = sum(width for _, width in game_controls) + 7 * (len(game_controls) - 1)
        control_x = (width - total) / 2
        for window, (_, control_width) in zip(game_windows, game_controls):
            game_canvas.coords(window, control_x + control_width / 2, height - 37)
            game_canvas.itemconfigure(window, width=control_width, height=38)
            control_x += control_width + 7

    def step_once():
        estado["agente"].paso()
        draw_game()

    def automatic_tick():
        agent = estado["agente"]
        if estado["automatico"] and agent.vivo and not agent.fin:
            step_once()
            root.after(650, automatic_tick)
        else:
            estado["automatico"] = False
            auto_button.configure(text="Automático")

    def toggle_auto():
        estado["automatico"] = not estado["automatico"]
        auto_button.configure(text="Pausar" if estado["automatico"] else "Automático")
        if estado["automatico"]:
            automatic_tick()

    def reset_game(aleatorio=False):
        estado["automatico"] = False
        auto_button.configure(text="Automático")
        estado["mundo"] = Mundo(aleatorio)
        estado["agente"] = Agente(estado["mundo"])
        draw_game()

    def start_game():
        reset_game()
        home.place_forget()
        game.place(relwidth=1, relheight=1)
        game.lift()
        draw_game()

    def return_home():
        estado["automatico"] = False
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
    game_controls = [
        (ttk.Button(game_canvas, text="Un paso", style="Wumpus.Primary.TButton",
                    command=step_once), 94),
        (auto_button, 116),
        (ttk.Button(game_canvas, text="Reiniciar", style="Wumpus.Secondary.TButton",
                    command=reset_game), 102),
        (ttk.Button(game_canvas, text="Mundo aleatorio",
                    style="Wumpus.Secondary.TButton",
                    command=lambda: reset_game(True)), 140),
        (ttk.Button(game_canvas, text="Inicio", style="Wumpus.Secondary.TButton",
                    command=return_home), 82),
        (ttk.Checkbutton(game_canvas, text="Ver mundo real", variable=mostrar_mundo,
                         style="Wumpus.TCheckbutton", command=draw_game), 136),
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
