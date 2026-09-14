
# ============================================================
# LIBRERÍAS IMPORTADAS
# ============================================================
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
        for j in range(i + 1, n):
            valor = np.random.randint(0, 2)
            matriz[i][j] = valor
            matriz[j][i] = valor

    return matriz


def componentes_conexas(matriz):
    n = len(matriz)
    visitados = [False] * n
    componentes = []

    for inicio in range(n):

        if visitados[inicio]:
            continue

        componente = []
        pendientes = [inicio]
        visitados[inicio] = True

        while pendientes:
            actual = pendientes.pop(0)
            componente.append(actual + 1)

            for vecino in range(n):

                if matriz[actual][vecino] != 1:
                    continue

                if visitados[vecino]:
                    continue

                visitados[vecino] = True
                pendientes.append(vecino)

        componentes.append(componente)

    return componentes


def dibujar_grafo(matriz, componentes, etiquetas):
    n = len(matriz)
    angulos = np.linspace(0, 2 * np.pi, n, endpoint=False)

    posiciones = []
    for angulo in angulos:
        posiciones.append((np.cos(angulo), np.sin(angulo)))

    plt.figure(figsize=(8, 8))

    # --- Dibujar las líneas de conexión ---
    for i in range(n):
        for j in range(i + 1, n):

            if matriz[i][j] != 1:
                continue

            x1, y1 = posiciones[i]
            x2, y2 = posiciones[j]
            plt.plot([x1, x2], [y1, y2], 'k-', zorder=1)

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

    plt.title("Componentes Conexas")
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
            text="Aquí puedes agregar aristas, cambiar las etiquetas de los nodos,\n"
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
        aristas = int(np.sum(matriz) // 2)

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

            if o == d:
                messagebox.showerror("Error", "No se puede conectar un nodo consigo mismo")
                return

            if self.app.matriz[o - 1][d - 1] == 1:
                messagebox.showinfo("Info", "Esa conexión ya existe")
                return

            self.app.matriz[o - 1][d - 1] = 1
            self.app.matriz[d - 1][o - 1] = 1
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
        dibujar_grafo(self.app.matriz, componentes, etiquetas)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
