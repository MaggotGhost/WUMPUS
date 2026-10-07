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
    from tkinter import filedialog, messagebox, ttk
    from PIL import Image, ImageChops, ImageEnhance, ImageOps, ImageTk

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
    background_source = None
    logo_source = None
    for filename, kind in (("fondo_cueva.jpg", "background"),
                           ("escudo_universidad.png", "logo")):
        path = Path(__file__).with_name(filename)
        if path.exists():
            try:
                with Image.open(path) as image:
                    if kind == "background":
                        background_source = image.convert("RGB")
                    else:
                        logo_source = image.convert("RGBA")
            except OSError:
                pass
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
    logo_photo = {"image": None}

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
        home_canvas.create_text(width - 58, 48, anchor="ne", text="PROYECTO ACADÉMICO",
                                font=("Segoe UI", 9), fill="#a7b5b5", tags="scene")

        logo_x, logo_y = width * 0.25, height * 0.48
        if logo_source is not None:
            logo = ImageOps.contain(logo_source, (300, 340),
                                    method=Image.Resampling.LANCZOS)
            logo_photo["image"] = ImageTk.PhotoImage(logo)
            home_canvas.create_image(logo_x, logo_y, image=logo_photo["image"],
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
        home_canvas.coords(background_window, width - 178, 57)
        home_canvas.coords(logo_window, width - 64, 57)

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

        board_size = min(height - 320, width * 0.48, 560)
        board_x, board_y = 46, 218
        cell_size = board_size / N
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
        for row, y in enumerate(range(N, 0, -1)):
            for column, x in enumerate(range(1, N + 1)):
                cell = (x, y)
                left, top = board_x + column * cell_size, board_y + row * cell_size
                right, bottom = left + cell_size, top + cell_size
                if cell in agent.visitadas:
                    fill, outline, label = "#1b3941", "#45636b", "VISITADA"
                elif agent.segura(cell):
                    fill, outline, label = "#17483e", "#4e8978", "SEGURA"
                elif cell in pits or cell == certain_wumpus:
                    fill, outline = "#563437", "#a66a61"
                    label = "HOYO" if cell in pits else "WUMPUS"
                elif cell in possible_pits or cell in possible_wumpus:
                    fill, outline = "#4b422f", "#9b8350"
                    hints = []
                    if cell in possible_pits:
                        hints.append("HOYO?")
                    if cell in possible_wumpus:
                        hints.append("WUMPUS?")
                    label = " / ".join(hints)
                else:
                    fill, outline, label = "#17252d", "#354850", "SIN EXPLORAR"
                if cell == agent.pos:
                    fill, outline, label = "#6e542b", "#edc777", "AGENTE"
                if reveal:
                    if cell in world.hoyos:
                        label = "HOYO"
                    elif cell == world.wumpus:
                        label = "WUMPUS"
                    elif cell == world.oro:
                        label = "ORO"
                    if cell == agent.pos:
                        label = "AGENTE\n" + label
                game_canvas.create_rectangle(left + 3, top + 3, right - 3, bottom - 3,
                                             fill=fill, outline=outline,
                                             width=2 if cell == agent.pos else 1,
                                             tags="scene")
                game_canvas.create_text(left + 11, top + 9, anchor="nw",
                                        text=f"{x}, {y}", font=("Segoe UI", 8),
                                        fill="#a6b5b5", tags="scene")
                game_canvas.create_text((left + right) / 2, (top + bottom) / 2 + 5,
                                        text=label, font=("Segoe UI Semibold", 10),
                                        fill="#f0eadb", width=cell_size - 14,
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

    def choose_background():
        nonlocal background_source
        path = filedialog.askopenfilename(
            parent=root, title="Elegir fondo de la cueva",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png"), ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            with Image.open(path) as image:
                background_source = image.convert("RGB")
        except OSError as error:
            messagebox.showerror("No se pudo abrir la imagen", str(error), parent=root)
            return
        background_cache.clear()
        draw_home()
        draw_game()

    def choose_logo():
        nonlocal logo_source
        path = filedialog.askopenfilename(
            parent=root, title="Elegir escudo del equipo",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg"), ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            with Image.open(path) as image:
                logo_source = image.convert("RGBA")
                if image.mode == "RGBA" and image.getchannel("A").getextrema()[0] < 255:
                    bounds = logo_source.getchannel("A").getbbox()
                else:
                    rgb = logo_source.convert("RGB")
                    difference = ImageChops.difference(
                        rgb, Image.new("RGB", rgb.size, "black"),
                    ).convert("L")
                    bounds = difference.point(lambda value: 255 if value > 24 else 0).getbbox()
                if bounds:
                    logo_source = logo_source.crop(bounds)
        except OSError as error:
            messagebox.showerror("No se pudo abrir el escudo", str(error), parent=root)
            return
        draw_home()

    play_button = ttk.Button(home_canvas, text="JUGAR", style="Wumpus.Primary.TButton",
                             command=start_game)
    exit_button = ttk.Button(home_canvas, text="SALIR", style="Wumpus.Secondary.TButton",
                             command=root.destroy)
    background_button = ttk.Button(home_canvas, text="Fondo",
                                   style="Wumpus.Secondary.TButton",
                                   command=choose_background)
    logo_button = ttk.Button(home_canvas, text="Escudo",
                             style="Wumpus.Secondary.TButton", command=choose_logo)
    play_window = home_canvas.create_window(0, 0, window=play_button, width=190, height=52)
    exit_window = home_canvas.create_window(0, 0, window=exit_button, width=130, height=52)
    background_window = home_canvas.create_window(0, 0, window=background_button,
                                                  width=78, height=34)
    logo_window = home_canvas.create_window(0, 0, window=logo_button, width=78, height=34)

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
