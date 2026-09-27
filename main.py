import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# LÓGICA DEL GRAFO
# ============================================================

def crear_grafo_aleatorio(n):
    matriz = np.zeros((n, n), dtype=int)

    for i in range(n):
        for j in range(n):

            if i == j:
                continue

            matriz[i][j] = np.random.randint(0, 2)

    return matriz


def matriz_de_caminos(matriz):
    """Paso 1 y 2 del PDF: agrega 1's en la diagonal y calcula la matriz de
    caminos (cierre transitivo) a partir de la matriz de adyacencia."""
    n = len(matriz)
    R = matriz.copy()

    for i in range(n):
        R[i][i] = 1

    for k in range(n):
        for i in range(n):

            if R[i][k] == 0:
                continue

            for j in range(n):
                if R[k][j] == 1:
                    R[i][j] = 1

    return R


def ordenar_por_filas(R):
    """Paso 3 del PDF: determina el orden de las filas según la cantidad de
    1's que contienen (de mayor a menor). En caso de empate, se prioriza la
    fila cuyo primer 1 está más cerca de la primera columna."""
    n = len(R)

    def clave(i):
        cantidad_unos = int(np.sum(R[i]))
        primer_uno = int(np.argmax(R[i]))
        return (-cantidad_unos, primer_uno)

    return sorted(range(n), key=clave)


def componentes_conexas(matriz):
    """Pasos 3 y 4 del PDF: a partir de la matriz de caminos, se agrupan los
    nodos que se alcanzan mutuamente (equivalente a los bloques cuadrados
    diagonales que se obtienen al ordenar filas y columnas)."""
    n = len(matriz)
    R = matriz_de_caminos(matriz)

    visitados = [False] * n
    componentes = []

    for i in range(n):

        if visitados[i]:
            continue

        componente = []
        for j in range(n):

            if R[i][j] == 1 and R[j][i] == 1:
                componente.append(j + 1)
                visitados[j] = True

        componentes.append(componente)

    return componentes


def dibujar_grafo(matriz, componentes, etiquetas, separar_componentes=False, titulo="Grafo"):
    n = len(matriz)

    # --- A qué componente pertenece cada nodo (para filtrar aristas si aplica) ---
    comp_de = [0] * n
    for idx_comp, componente in enumerate(componentes):
        for nodo in componente:
            comp_de[nodo - 1] = idx_comp

    if separar_componentes:
        # --- Ubicar cada componente en su propio grupo, separado de las demás ---
        k = len(componentes)
        columnas = int(np.ceil(np.sqrt(k)))
        separacion = 3.2

        posiciones = [None] * n

        for idx_comp, componente in enumerate(componentes):
            fila_grid = idx_comp // columnas
            col_grid = idx_comp % columnas
            cx = col_grid * separacion
            cy = -fila_grid * separacion

            m = len(componente)
            angulos = np.linspace(0, 2 * np.pi, m, endpoint=False)

            if m > 1:
                radio = 0.6
            else:
                radio = 0.0

            for angulo, nodo in zip(angulos, componente):
                x = cx + radio * np.cos(angulo)
                y = cy + radio * np.sin(angulo)
                posiciones[nodo - 1] = (x, y)
    else:
        # --- Grafo original: todos los nodos en un único círculo ---
        angulos = np.linspace(0, 2 * np.pi, n, endpoint=False)
        posiciones = [(np.cos(a), np.sin(a)) for a in angulos]

    plt.figure(figsize=(8, 8))

    # --- Dibujar las flechas de conexión (grafo dirigido) ---
    for i in range(n):
        for j in range(n):

            if matriz[i][j] != 1:
                continue

            if i == j:
                # --- No se dibuja nada para un nodo conectado consigo mismo ---
                continue

            # --- En la vista separada, solo se dibujan aristas dentro de la misma componente ---
            if separar_componentes and comp_de[i] != comp_de[j]:
                continue

            x1, y1 = posiciones[i]
            x2, y2 = posiciones[j]
            plt.annotate(
                "", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1,
                                 shrinkA=15, shrinkB=15),
                zorder=1
            )

    # --- Dibujar los nodos, coloreados por componente ---
    colores = plt.cm.tab10.colors

    for num_comp, componente in enumerate(componentes, start=1):
        color = colores[(num_comp - 1) % len(colores)]

        for nodo in componente:
            x, y = posiciones[nodo - 1]
            plt.scatter(x, y, s=800, color=color, label=f"Componente {num_comp}", zorder=2)
            plt.text(x, y, etiquetas[nodo - 1], ha="center", va="center", fontsize=12)

    # --- Leyenda sin etiquetas repetidas, fuera del área del gráfico ---
    handles, labels = plt.gca().get_legend_handles_labels()
    vistos = dict(zip(labels, handles))
    plt.legend(
        vistos.values(),
        vistos.keys(),
        loc="upper left",
        bbox_to_anchor=(1.02, 1)
    )

    plt.title(titulo)
    plt.axis("equal")
    plt.axis("off")
    plt.tight_layout()
    plt.show()


# ============================================================
# APLICACIÓN CON 2 PANTALLAS (WIZARD)
# ============================================================

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Componentes Conexas")
        self.root.geometry("560x680")

        # Estado compartido entre pantallas
        self.modo = None                 # "aleatorio" o "manual"
        self.n = 4
        self.matriz = None
        self.modo_etiqueta = "numeros"   # "numeros" o "letras"

        # Contenedor que va a superponer las dos pantallas
        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        self.pantalla_bienvenida = PantallaBienvenida(self.container, self)
        self.pantalla_matriz = PantallaMatriz(self.container, self)

        for pantalla in (self.pantalla_bienvenida, self.pantalla_matriz):
            pantalla.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.mostrar_bienvenida()

    def mostrar_bienvenida(self):
        self.pantalla_bienvenida.tkraise()

    def mostrar_matriz(self):
        self.pantalla_matriz.actualizar()
        self.pantalla_matriz.tkraise()

    def etiquetas_actuales(self):
        """Devuelve la lista de etiquetas para los n nodos, según el modo elegido."""
        etiquetas = []

        for i in range(self.n):

            if self.modo_etiqueta == "letras":
                etiquetas.append(chr(65 + i))   # A, B, C, ...
            else:
                etiquetas.append(str(i + 1))    # 1, 2, 3, ...

        return etiquetas


# ------------------------------------------------------------
# PANTALLA 1: BIENVENIDA
# ------------------------------------------------------------

class PantallaBienvenida(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tk.Label(self, text="Bienvenido", font=("Arial", 18, "bold")).pack(pady=15)
        tk.Label(self, text="Dime de qué manera generar el grafo:", font=("Arial", 11)).pack(pady=5)

        frame_botones = tk.Frame(self)
        frame_botones.pack(pady=10)

        self.btn_aleatorio = tk.Button(
            frame_botones, text="Aleatorio", width=12,
            command=lambda: self.elegir_modo("aleatorio")
        )
        self.btn_aleatorio.pack(side="left", padx=10)

        self.btn_manual = tk.Button(
            frame_botones, text="Manual", width=12,
            command=lambda: self.elegir_modo("manual")
        )
        self.btn_manual.pack(side="left", padx=10)

        tk.Label(self, text="Dime cant. de nodos (4-12):", font=("Arial", 11)).pack(pady=(20, 5))
        self.entry_n = tk.Spinbox(self, from_=4, to=12, width=5, justify="center")
        self.entry_n.pack(pady=5)

        tk.Button(self, text="Iniciar", width=15, height=2, command=self.iniciar).pack(pady=30)

    def elegir_modo(self, modo):
        self.app.modo = modo

        # Resaltar visualmente cuál está seleccionado
        if modo == "aleatorio":
            self.btn_aleatorio.config(relief="sunken")
            self.btn_manual.config(relief="raised")
        else:
            self.btn_aleatorio.config(relief="raised")
            self.btn_manual.config(relief="sunken")

    def iniciar(self):
        if self.app.modo is None:
            messagebox.showerror("Error", "Elige un modo: Aleatorio o Manual")
            return

        try:
            n = int(self.entry_n.get())
        except ValueError:
            messagebox.showerror("Error", "Ingresa un número válido de nodos")
            return

        if n < 4 or n > 12:
            messagebox.showerror("Error", "La cantidad de nodos debe estar entre 4 y 12")
            return

        self.app.n = n

        if self.app.modo == "aleatorio":
            self.app.matriz = crear_grafo_aleatorio(n)
        else:
            self.app.matriz = np.zeros((n, n), dtype=int)

        self.app.mostrar_matriz()


# ------------------------------------------------------------
# PANTALLA 2: MATRIZ
# ------------------------------------------------------------

class PantallaMatriz(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        barra_superior = tk.Frame(self)
        barra_superior.pack(fill="x", pady=5, padx=5)
        tk.Button(barra_superior, text="< Atras", command=self.volver).pack(side="left")

        tk.Label(self, text="Matriz", font=("Arial", 16, "bold")).pack(pady=5)

        # Texto instructivo: explica qué se puede hacer en esta pantalla
        tk.Label(
            self,
            text="Grafo dirigido: cada arista va de un Origen a un Destino.\n"
                 "Aquí puedes agregar aristas, cambiar las etiquetas de los nodos,\n"
                 "revertir el grafo (borrar aristas) o graficar el resultado.",
            font=("Arial", 9), fg="gray20", justify="center", wraplength=460
        ).pack(pady=(0, 10))

        # ---------- Matriz de adyacencia ----------
        self.frame_matriz = tk.Frame(self)
        self.frame_matriz.pack(pady=10)

        # ---------- Botonera ----------
        frame_botones = tk.Frame(self)
        frame_botones.pack(pady=10)

        tk.Button(frame_botones, text="Editar arista", command=self.editar_arista).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(frame_botones, text="Letras", command=lambda: self.cambiar_etiqueta("letras")).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(frame_botones, text="Numeros", command=lambda: self.cambiar_etiqueta("numeros")).grid(row=0, column=2, padx=5, pady=5)
        tk.Button(frame_botones, text="Revertir", command=self.revertir, bg="#ffe0b3").grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        tk.Button(frame_botones, text="Reiniciar", command=self.reiniciar, bg="#ffb3b3").grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(frame_botones, text="Graficar", command=self.graficar, bg="lightblue").grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        tk.Button(frame_botones, text="Ver procedimiento paso a paso", command=self.ver_procedimiento,
                  bg="#d9c7ff").grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # ---------- Resultado final ----------
        f_resultado = ttk.LabelFrame(self, text="Resultado final", padding=10)
        f_resultado.pack(fill="x", padx=10, pady=5)
        self.text_resultado = tk.Text(f_resultado, height=6, width=60)
        self.text_resultado.pack(fill="both", expand=True)

        # ---------- Análisis de nodo ----------
        f_analisis = ttk.LabelFrame(self, text="Análisis de nodo", padding=10)
        f_analisis.pack(fill="x", padx=10, pady=5)
        self.nodo_analisis = tk.IntVar(value=1)
        ttk.Label(f_analisis, text="Nodo:").pack(side="left", padx=5)
        self.spin_analisis = ttk.Spinbox(f_analisis, from_=1, to=12, textvariable=self.nodo_analisis, width=5)
        self.spin_analisis.pack(side="left", padx=5)
        ttk.Button(f_analisis, text="Analizar", command=self.analizar).pack(side="left", padx=10)
        self.text_analisis = tk.Text(f_analisis, height=3, width=50)
        self.text_analisis.pack(side="left", fill="both", expand=True, padx=5)

    def volver(self):
        self.app.mostrar_bienvenida()

    def revertir(self):
        """Borra todas las aristas, pero mantiene el mismo n y el mismo modo."""
        respuesta = messagebox.askyesno(
            "Revertir",
            "Esto borrará todas las conexiones del grafo actual (la matriz quedará vacía).\n¿Deseas continuar?"
        )

        if not respuesta:
            return

        n = self.app.n
        self.app.matriz = np.zeros((n, n), dtype=int)
        self.actualizar()

    def reiniciar(self):
        """Reinicia todo el programa: vuelve a la pantalla de bienvenida sin ningún dato previo."""
        respuesta = messagebox.askyesno(
            "Reiniciar",
            "Esto borrará el grafo actual y volverás a elegir modo y cantidad de nodos desde cero.\n¿Deseas continuar?"
        )

        if not respuesta:
            return

        self.app.modo = None
        self.app.matriz = None
        self.app.n = 4
        self.app.modo_etiqueta = "numeros"

        self.app.pantalla_bienvenida.btn_aleatorio.config(relief="raised")
        self.app.pantalla_bienvenida.btn_manual.config(relief="raised")
        self.app.pantalla_bienvenida.entry_n.delete(0, tk.END)
        self.app.pantalla_bienvenida.entry_n.insert(0, "4")

        self.app.mostrar_bienvenida()

    def cambiar_etiqueta(self, modo):
        self.app.modo_etiqueta = modo
        self.actualizar()

    def actualizar(self):
        n = self.app.n
        matriz = self.app.matriz
        etiquetas = self.app.etiquetas_actuales()

        # --- Refrescar la tabla de la matriz ---
        for w in self.frame_matriz.winfo_children():
            w.destroy()

        tk.Label(self.frame_matriz, text="", width=4).grid(row=0, column=0)

        for j in range(n):
            tk.Label(self.frame_matriz, text=etiquetas[j], width=4, relief="ridge").grid(row=0, column=j + 1)

        for i in range(n):
            tk.Label(self.frame_matriz, text=etiquetas[i], width=4, relief="ridge").grid(row=i + 1, column=0)

            for j in range(n):
                val = matriz[i][j]

                if val == 1:
                    bg = "lightgreen"
                else:
                    bg = "white"

                tk.Label(self.frame_matriz, text=str(val), width=4, relief="ridge", bg=bg).grid(row=i + 1, column=j + 1)

        # --- Refrescar el panel de Resultado final ---
        componentes = componentes_conexas(matriz)
        num = len(componentes)
        aristas = int(np.sum(matriz))

        if num == 1:
            es_conexo = "Sí"
        else:
            es_conexo = "No"

        info = f"Componentes: {num}\nConexo: {es_conexo}\nAristas: {aristas}\n"

        for i, comp in enumerate(componentes, start=1):
            comp_etiquetas = []
            for nodo in comp:
                comp_etiquetas.append(etiquetas[nodo - 1])
            info += f"  Comp {i}: {comp_etiquetas}\n"

        self.text_resultado.delete(1.0, tk.END)
        self.text_resultado.insert(tk.END, info)

        # --- Actualizar rango del spinbox de análisis según n ---
        self.spin_analisis.config(to=n)

        if self.nodo_analisis.get() > n:
            self.nodo_analisis.set(n)

        self.text_analisis.delete(1.0, tk.END)

    def editar_arista(self):
        n = self.app.n
        ventana = tk.Toplevel(self)
        ventana.title("Agregar arista")
        ventana.geometry("250x180")

        tk.Label(ventana, text="Origen:").grid(row=0, column=0, padx=5, pady=10)
        spin_o = tk.Spinbox(ventana, from_=1, to=n, width=5)
        spin_o.grid(row=0, column=1)
        tk.Label(ventana, text="Destino:").grid(row=1, column=0, padx=5, pady=10)
        spin_d = tk.Spinbox(ventana, from_=1, to=n, width=5)
        spin_d.grid(row=1, column=1)

        def agregar():
            o = int(spin_o.get())
            d = int(spin_d.get())

            if self.app.matriz[o - 1][d - 1] == 1:
                messagebox.showinfo("Info", "Esa conexión ya existe")
                return

            self.app.matriz[o - 1][d - 1] = 1
            self.actualizar()

        tk.Button(ventana, text="Agregar", command=agregar).grid(row=2, column=0, pady=10)
        tk.Button(ventana, text="Cerrar", command=ventana.destroy).grid(row=2, column=1, pady=10)

    def analizar(self):
        n = self.app.n
        matriz = self.app.matriz
        etiquetas = self.app.etiquetas_actuales()
        nodo = self.nodo_analisis.get()

        if nodo < 1 or nodo > n:
            messagebox.showerror("Error", f"Nodo debe estar entre 1 y {n}")
            return

        idx = nodo - 1

        vecinos = []
        for i in range(n):
            if matriz[idx][i] == 1:
                vecinos.append(etiquetas[i])

        self.text_analisis.delete(1.0, tk.END)
        self.text_analisis.insert(tk.END, f"Nodo actual: {etiquetas[idx]}\n")

        if not vecinos:
            self.text_analisis.insert(tk.END, "Conexiones: Ninguna")
            return

        conexiones_texto = []
        for v in vecinos:
            conexiones_texto.append(f"{etiquetas[idx]}->{v}")

        conex = ", ".join(conexiones_texto)
        self.text_analisis.insert(tk.END, f"Conexiones: {conex}")

    def graficar(self):
        componentes = componentes_conexas(self.app.matriz)
        etiquetas = self.app.etiquetas_actuales()

        # --- Imagen 1: grafo original, todos los nodos juntos ---
        dibujar_grafo(self.app.matriz, componentes, etiquetas,
                      separar_componentes=False, titulo="Grafo original")

        # --- Imagen 2: componentes separadas visualmente ---
        dibujar_grafo(self.app.matriz, componentes, etiquetas,
                      separar_componentes=True, titulo="Componentes Conexas")

    def ver_procedimiento(self):
        VentanaPasos(self, self.app.matriz, self.app.etiquetas_actuales())


# ------------------------------------------------------------
# VENTANA: PROCEDIMIENTO PASO A PASO (Pasos 1-4 del PDF)
# ------------------------------------------------------------

class VentanaPasos(tk.Toplevel):
    """Muestra, de forma interactiva, cómo va cambiando la matriz en cada
    paso del procedimiento (matriz + diagonal, matriz de caminos, orden de
    filas, orden de columnas y bloques), tal como se explica en el PDF."""

    def __init__(self, parent, matriz, etiquetas):
        super().__init__(parent)
        self.title("Procedimiento: Componentes conexas")
        self.geometry("560x580")

        self.matriz = matriz
        self.etiquetas = etiquetas
        self.n = len(matriz)
        self.paso_actual = 0

        self._calcular_pasos()

        self.label_titulo = tk.Label(self, text="", font=("Arial", 13, "bold"))
        self.label_titulo.pack(pady=(12, 0))

        self.label_descripcion = tk.Label(
            self, text="", font=("Arial", 9), fg="gray20",
            wraplength=500, justify="center"
        )
        self.label_descripcion.pack(pady=(2, 10))

        self.frame_tabla = tk.Frame(self)
        self.frame_tabla.pack(pady=5)

        self.label_extra = tk.Label(
            self, text="", font=("Arial", 9), fg="gray20",
            wraplength=500, justify="left"
        )
        self.label_extra.pack(pady=(5, 0))

        frame_nav = tk.Frame(self)
        frame_nav.pack(pady=15)

        self.btn_anterior = tk.Button(frame_nav, text="< Anterior", command=self.anterior, width=10)
        self.btn_anterior.grid(row=0, column=0, padx=10)
        self.label_paso = tk.Label(frame_nav, text="", font=("Arial", 10, "bold"))
        self.label_paso.grid(row=0, column=1, padx=10)
        self.btn_siguiente = tk.Button(frame_nav, text="Siguiente >", command=self.siguiente, width=10)
        self.btn_siguiente.grid(row=0, column=2, padx=10)

        self.mostrar_paso()

    def _calcular_pasos(self):
        n = self.n
        matriz = self.matriz

        # Paso 1: matriz de adyacencia con 1's en la diagonal
        M1 = matriz.copy()
        for i in range(n):
            M1[i][i] = 1

        # Paso 2: matriz de caminos (cierre transitivo)
        R = matriz_de_caminos(matriz)

        # Paso 3: orden de las filas
        orden = ordenar_por_filas(R)
        R_filas = R[orden, :]

        # Paso 4: mismas columnas, en el mismo orden que las filas
        R_final = R[np.ix_(orden, orden)]

        # Componentes reales, para resaltar los bloques correctamente
        componentes = componentes_conexas(matriz)
        comp_de_nodo = {}
        for idx_c, comp in enumerate(componentes):
            for nodo in comp:
                comp_de_nodo[nodo] = idx_c

        # Límites (inicio, fin) de cada bloque diagonal, según el orden final
        bloques = []
        inicio = 0
        comp_actual = comp_de_nodo[orden[0] + 1]

        for pos in range(1, n + 1):
            if pos == n or comp_de_nodo[orden[pos] + 1] != comp_actual:
                bloques.append((inicio, pos - 1))

                if pos < n:
                    comp_actual = comp_de_nodo[orden[pos] + 1]
                    inicio = pos

        self.M1 = M1
        self.R = R
        self.orden = orden
        self.R_filas = R_filas
        self.R_final = R_final
        self.componentes = componentes
        self.bloques = bloques

    def _pintar_matriz(self, M, etiquetas_filas, etiquetas_columnas, resaltar=None):
        """Dibuja M como una tabla. 'resaltar' es un set de (fila,col) que
        se marcan con borde rojo (los bloques de componentes)."""
        for w in self.frame_tabla.winfo_children():
            w.destroy()

        resaltar = resaltar or set()

        tk.Label(self.frame_tabla, text="", width=4).grid(row=0, column=0)

        for j in range(self.n):
            tk.Label(self.frame_tabla, text=etiquetas_columnas[j], width=4,
                     font=("Arial", 9, "bold")).grid(row=0, column=j + 1)

        for i in range(self.n):
            tk.Label(self.frame_tabla, text=etiquetas_filas[i], width=4,
                     font=("Arial", 9, "bold")).grid(row=i + 1, column=0)

            for j in range(self.n):
                val = int(M[i][j])
                marcado = (i, j) in resaltar

                # --- Color de fondo: verde si hay conexión (1), blanco si no (0) ---
                if val == 1:
                    bg = "lightgreen"
                else:
                    bg = "white"

                # --- Borde: rojo y grueso si la celda pertenece a un bloque (componente) ---
                if marcado:
                    color_borde = "red"
                    grosor_borde = 3
                else:
                    color_borde = "gray70"
                    grosor_borde = 1

                lbl = tk.Label(
                    self.frame_tabla, text=str(val), width=4, bg=bg,
                    highlightthickness=grosor_borde,
                    highlightbackground=color_borde
                )
                lbl.grid(row=i + 1, column=j + 1, padx=1, pady=1)

    def mostrar_paso(self):
        etiquetas = self.etiquetas
        etiquetas_orden = [etiquetas[i] for i in self.orden]

        # --- Habilitar/deshabilitar los botones de navegación según el paso actual ---
        if self.paso_actual > 0:
            self.btn_anterior.config(state="normal")
        else:
            self.btn_anterior.config(state="disabled")

        if self.paso_actual < 4:
            self.btn_siguiente.config(state="normal")
        else:
            self.btn_siguiente.config(state="disabled")

        self.label_paso.config(text=f"Paso {self.paso_actual + 1} de 5")
        self.label_extra.config(text="")

        if self.paso_actual == 0:
            self.label_titulo.config(text="Paso 1: Matriz de adyacencia + diagonal")
            self.label_descripcion.config(
                text="Se construye la matriz de adyacencia del grafo y se agrega el valor 1 "
                     "en toda la diagonal principal."
            )
            self._pintar_matriz(self.M1, etiquetas, etiquetas)

        elif self.paso_actual == 1:
            self.label_titulo.config(text="Paso 2: Matriz de caminos")
            self.label_descripcion.config(
                text="A partir de la matriz del Paso 1 se calcula la matriz de caminos "
                     "M_R∞: indica qué nodos son alcanzables desde cada nodo."
            )
            self._pintar_matriz(self.R, etiquetas, etiquetas)

            lineas = ["Nodos alcanzables desde cada nodo:"]

            for i in range(self.n):
                alcanzables = []
                for j in range(self.n):
                    if self.R[i][j] == 1:
                        alcanzables.append(etiquetas[j])

                lineas.append(f"  {etiquetas[i]} llega hasta: {', '.join(alcanzables)}")

            self.label_extra.config(text="\n".join(lineas))

        elif self.paso_actual == 2:
            self.label_titulo.config(text="Paso 3: Ordenar filas")
            self.label_descripcion.config(
                text="Se ordenan las filas según la cantidad de 1's que contienen (de mayor "
                     "a menor). En caso de empate, se prioriza la fila cuyo primer 1 esté "
                     "más cerca de la primera columna."
            )
            self._pintar_matriz(self.R_filas, etiquetas_orden, etiquetas)

            lineas = ["Cantidad de 1's por fila (en el orden mostrado):"]
            cantidades = [f"{etiquetas[i]} tiene {int(np.sum(self.R[i]))}" for i in self.orden]
            lineas.append("  " + ", ".join(cantidades))
            self.label_extra.config(text="\n".join(lineas))

        elif self.paso_actual == 3:
            self.label_titulo.config(text="Paso 4: Ordenar columnas y formar bloques")
            self.label_descripcion.config(
                text="Se reordenan las columnas en el mismo orden que las filas. Los bloques "
                     "cuadrados diagonales formados por 1's (marcados en rojo) son las "
                     "componentes conexas."
            )
            resaltar = set()
            for inicio, fin in self.bloques:
                for i in range(inicio, fin + 1):
                    for j in range(inicio, fin + 1):
                        resaltar.add((i, j))
            self._pintar_matriz(self.R_final, etiquetas_orden, etiquetas_orden, resaltar=resaltar)

        else:
            self.label_titulo.config(text="Resultado: Componentes conexas")
            self.label_descripcion.config(text="")

            for w in self.frame_tabla.winfo_children():
                w.destroy()

            texto = ""
            for i, comp in enumerate(self.componentes, start=1):
                nombres = [etiquetas[nodo - 1] for nodo in comp]
                texto += f"V{i} = {{{', '.join(nombres)}}}\n"

            tk.Label(self.frame_tabla, text=texto, font=("Arial", 13), justify="left").pack()

    def anterior(self):
        if self.paso_actual > 0:
            self.paso_actual -= 1
            self.mostrar_paso()

    def siguiente(self):
        if self.paso_actual < 4:
            self.paso_actual += 1
            self.mostrar_paso()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
