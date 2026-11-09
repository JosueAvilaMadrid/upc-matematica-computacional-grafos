import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import textwrap
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import qrcode
import cv2
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode


# Código QR

def generar_qr_de_grafo(nombre, etiquetas, matriz, posiciones=None):
  datos = {
      "nombre": nombre,
      "etiquetas": etiquetas,
      "matriz": matriz.tolist(),
  }
  if posiciones is not None:
    datos["posiciones"] = [
        [round(x, 2), round(y, 2)] for x, y in posiciones
    ]

  cadena_json = json.dumps(datos, separators=(",", ":"))

  qr = qrcode.QRCode(
      version=None,
      error_correction=qrcode.constants.ERROR_CORRECT_M,
      box_size=8,
      border=4,
  )
  qr.add_data(cadena_json)
  qr.make(fit=True)

  return qr.make_image(fill_color="black", back_color="white")


def leer_grafo_desde_qr(ruta_imagen):
  try:
    pil_img = Image.open(ruta_imagen).convert("RGB")
  except Exception as e:
    raise ValueError(f"No se pudo abrir el archivo de imagen: {str(e)}")

  codigos = decode(pil_img)

  if not codigos:
    raise ValueError(
        "No se pudo detectar el código QR en la imagen seleccionada."
    )

  contenido = codigos[0].data.decode("utf-8")

  try:
    datos = json.loads(contenido)
  except json.JSONDecodeError:
    raise ValueError("El código QR no contiene un formato JSON válido.")

  if "matriz" not in datos or "etiquetas" not in datos:
    raise ValueError(
        "El código QR no pertenece a un ejercicio de esta aplicación."
    )

  matriz = np.array(datos["matriz"], dtype=int)
  etiquetas = datos.get("etiquetas", [str(i + 1) for i in range(len(matriz))])
  nombre = datos.get("nombre", "Ejercicio Importado QR")
  posiciones = datos.get("posiciones", None)

  return nombre, etiquetas, matriz, posiciones


class VentanaMostrarQR(tk.Toplevel):

  def __init__(self, parent, app):
    super().__init__(parent)
    self.title("Compartir por Código QR")
    self.geometry("440x600")
    self.app = app
    self.resizable(False, False)

    tk.Label(
        self, text="Código QR del Ejercicio", font=("Arial", 14, "bold")
    ).pack(pady=(15, 5))
    tk.Label(
        self,
        text=(
            "Guarda la imagen con el botón de abajo para enviársela a un"
            " compañero."
        ),
        font=("Arial", 9),
        fg="gray20",
        justify="center",
        wraplength=360,
    ).pack(pady=(0, 10))

    self.imagen_pil = generar_qr_de_grafo(
        "Ejercicio Compartido",
        self.app.etiquetas_actuales(),
        self.app.matriz,
        self.app.posiciones,
    )

    img_muestra = self.imagen_pil.resize((300, 300))
    self.imagen_tk = ImageTk.PhotoImage(img_muestra)

    self.label_qr = tk.Label(self, image=self.imagen_tk, bg="white", bd=1)
    self.label_qr.pack(pady=5, padx=10)

    frame_botones = tk.Frame(self)
    frame_botones.pack(pady=15, side="bottom")

    tk.Button(
        frame_botones,
        text="Descargar QR (.png)",
        command=self.descargar_qr,
        bg="#b3e6b3",
        width=18,
        height=2,
    ).grid(row=0, column=0, padx=5)

    tk.Button(
        frame_botones, text="Cerrar", command=self.destroy, width=10, height=2
    ).grid(row=0, column=1, padx=5)

  def descargar_qr(self):
    ruta = filedialog.asksaveasfilename(
        parent=self,
        title="Guardar código QR",
        defaultextension=".png",
        filetypes=[("Imagen PNG", "*.png")],
        initialfile="ejercicio_grafo_qr.png",
    )
    if not ruta:
      return

    try:
      self.imagen_pil.save(ruta)
      messagebox.showinfo(
          "Éxito", f"Imagen guardada correctamente en:\n{ruta}", parent=self
      )
    except Exception as error:
      messagebox.showerror(
          "Error", f"No se pudo guardar el archivo:\n{error}", parent=self
      )


# Lógica del grafo

def crear_grafo_aleatorio(n):
    matriz = np.zeros((n, n), dtype=int)

    for i in range(n):
        for j in range(n):

            if i == j:
                continue

            matriz[i][j] = np.random.randint(0, 2)

    return matriz


def texto_json_del_grafo(nombre, etiquetas, matriz, posiciones=None):
    guardado = datetime.now().strftime("%d/%m/%Y %H:%M")

    filas = []
    for fila in matriz.tolist():
        filas.append("    " + json.dumps(fila))

    texto = "{\n"
    texto += "  \"nombre\": " + json.dumps(nombre, ensure_ascii=False) + ",\n"
    texto += "  \"guardado\": " + json.dumps(guardado) + ",\n"
    texto += "  \"nodos\": " + str(len(matriz)) + ",\n"
    texto += "  \"etiquetas\": " + json.dumps(etiquetas, ensure_ascii=False) + ",\n"

    if posiciones is not None:
        redondeadas = []
        for x, y in posiciones:
            redondeadas.append([round(x, 3), round(y, 3)])

        texto += "  \"posiciones\": " + json.dumps(redondeadas) + ",\n"

    texto += "  \"matriz\": [\n" + ",\n".join(filas) + "\n  ]\n"
    texto += "}\n"

    return texto


def validar_posiciones(posiciones, n):
    if not isinstance(posiciones, list) or len(posiciones) != n:
        raise ValueError(f"se necesitan {n} posiciones de nodos")

    validas = []

    for posicion in posiciones:
        if not isinstance(posicion, list) or len(posicion) != 2:
            raise ValueError("cada posición debe ser un par [x, y]")

        for valor in posicion:
            if not isinstance(valor, (int, float)) or valor < 0 or valor > 1:
                raise ValueError("las posiciones deben ser números entre 0 y 1")

        validas.append([float(posicion[0]), float(posicion[1])])

    return validas


def leer_grafo_json(ruta):
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except json.JSONDecodeError:
        raise ValueError("el archivo no es un JSON válido")

    if not isinstance(datos, dict) or "matriz" not in datos:
        raise ValueError("el archivo no tiene una matriz de adyacencia")

    try:
        matriz = np.array(datos["matriz"], dtype=float)
    except (TypeError, ValueError):
        raise ValueError("la matriz tiene valores que no son números")

    if matriz.ndim != 2 or matriz.shape[0] != matriz.shape[1]:
        raise ValueError("la matriz debe ser cuadrada (mismas filas que columnas)")

    n = matriz.shape[0]

    if n < 4 or n > 12:
        raise ValueError(f"la cantidad de nodos debe estar entre 4 y 12 (el archivo tiene {n})")

    if not np.isin(matriz, [0, 1]).all():
        raise ValueError("la matriz solo puede tener 0 y 1")

    matriz = matriz.astype(int)

    etiquetas = datos.get("etiquetas")

    if etiquetas is None:
        etiquetas = []
        for i in range(n):
            etiquetas.append(str(i + 1))
    else:
        if not isinstance(etiquetas, list) or len(etiquetas) != n:
            raise ValueError(f"se necesitan {n} nombres de nodos")

        for nombre_nodo in etiquetas:
            if not isinstance(nombre_nodo, str) or nombre_nodo.strip() == "":
                raise ValueError("los nombres de los nodos deben ser textos no vacíos")

        if len(set(etiquetas)) < n:
            raise ValueError("hay nombres de nodos repetidos")

    nombre = datos.get("nombre", "")

    if not isinstance(nombre, str):
        nombre = ""

    guardado = datos.get("guardado", "")

    if not isinstance(guardado, str):
        guardado = ""

    posiciones = datos.get("posiciones")

    if posiciones is not None:
        posiciones = validar_posiciones(posiciones, n)

    return nombre, etiquetas, matriz, guardado, posiciones


def carpeta_ejercicios():
    base = os.path.dirname(os.path.abspath(__file__))
    carpeta = os.path.join(base, "ejercicios_guardados")
    es_nueva = not os.path.isdir(carpeta)

    try:
        os.makedirs(carpeta, exist_ok=True)
    except OSError:
        carpeta = os.path.join(os.path.expanduser("~"), "ejercicios_guardados")
        es_nueva = not os.path.isdir(carpeta)
        os.makedirs(carpeta, exist_ok=True)

    if es_nueva:
        crear_ejemplos(carpeta)

    return carpeta


def crear_ejemplos(carpeta):
    ejemplo_1 = np.array([
        [0, 1, 0, 0, 0],
        [0, 0, 1, 1, 1],
        [0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0],
        [0, 0, 1, 0, 0],
    ])
    practica_1 = np.array([
        [0, 1, 0, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 0, 0, 1, 0],
        [0, 1, 0, 0, 1],
        [0, 0, 0, 0, 0],
    ])

    ejemplos = [
        ("Ejemplo 1 del PDF", ["1", "2", "3", "4", "5"], ejemplo_1),
        ("Práctica 1 del PDF (A-E)", ["A", "B", "C", "D", "E"], practica_1),
    ]

    try:
        for nombre, etiquetas, matriz in ejemplos:
            ruta = os.path.join(carpeta, nombre_de_archivo(nombre))

            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write(texto_json_del_grafo(nombre, etiquetas, matriz))
    except OSError:
        pass


def nombre_de_archivo(nombre):
    archivo = nombre

    for caracter in '\\/:*?"<>|':
        archivo = archivo.replace(caracter, "_")

    archivo = archivo.strip(" .")

    if archivo == "":
        archivo = "ejercicio"

    return archivo + ".json"


def guardar_ejercicio(nombre, etiquetas, matriz, posiciones=None):
    ruta = os.path.join(carpeta_ejercicios(), nombre_de_archivo(nombre))

    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(texto_json_del_grafo(nombre, etiquetas, matriz, posiciones))

    return ruta


def listar_ejercicios():
    carpeta = carpeta_ejercicios()
    ejercicios = []

    for nombre_archivo in os.listdir(carpeta):

        if not nombre_archivo.lower().endswith(".json"):
            continue

        ruta = os.path.join(carpeta, nombre_archivo)

        try:
            nombre, etiquetas, matriz, guardado, posiciones = leer_grafo_json(ruta)
            modificado = os.path.getmtime(ruta)
        except (ValueError, OSError):
            continue

        if nombre == "":
            nombre = os.path.splitext(nombre_archivo)[0]

        ejercicios.append({
            "archivo": ruta,
            "nombre": nombre,
            "etiquetas": etiquetas,
            "matriz": matriz,
            "guardado": guardado,
            "posiciones": posiciones,
            "aristas": int(np.sum(matriz)),
            "modificado": modificado,
        })

    ejercicios.sort(key=lambda ejercicio: ejercicio["modificado"], reverse=True)

    return ejercicios


def producto_booleano(A, B):
    return (np.dot(A, B) > 0).astype(int)


def matriz_de_caminos(matriz):
    n = len(matriz)
    M = matriz.copy()

    for i in range(n):
        M[i][i] = 1

    potencia = M.copy()

    for _ in range(n):
        siguiente = producto_booleano(potencia, M)

        if (siguiente == potencia).all():
            break

        potencia = siguiente

    return potencia


def ordenar_por_filas(R):
    n = len(R)

    def clave(i):
        cantidad_unos = int(np.sum(R[i]))
        primer_uno = int(np.argmax(R[i]))
        return (-cantidad_unos, primer_uno)

    return sorted(range(n), key=clave)


def componentes_conexas(matriz):
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


def potencias_con_pasos(matriz):
    n = len(matriz)
    M1 = matriz.copy()

    for i in range(n):
        M1[i][i] = 1

    iteraciones = []
    anterior = M1.copy()

    for exponente in range(2, n + 2):
        potencia = producto_booleano(anterior, M1)

        nuevos = []

        for i in range(n):
            for j in range(n):

                if potencia[i][j] == 1 and anterior[i][j] == 0:

                    intermedio = 0
                    for t in range(n):
                        if anterior[i][t] == 1 and M1[t][j] == 1:
                            intermedio = t
                            break

                    nuevos.append((i, j, intermedio))

        if len(nuevos) == 0:
            estable = True
        else:
            estable = False

        iteraciones.append({
            "exponente": exponente,
            "matriz": potencia,
            "nuevos": nuevos,
            "estable": estable,
        })

        if estable:
            break

        anterior = potencia

    return M1, iteraciones


def calcular_procedimiento(matriz):
    n = len(matriz)

    M1, iteraciones = potencias_con_pasos(matriz)
    R = matriz_de_caminos(matriz)

    orden = ordenar_por_filas(R)
    R_filas = R[orden, :]

    R_final = R[np.ix_(orden, orden)]

    componentes = componentes_conexas(matriz)
    comp_de_nodo = {}
    for idx_c, comp in enumerate(componentes):
        for nodo in comp:
            comp_de_nodo[nodo] = idx_c

    bloques = []
    inicio = 0
    comp_actual = comp_de_nodo[orden[0] + 1]

    for pos in range(1, n + 1):
        if pos == n or comp_de_nodo[orden[pos] + 1] != comp_actual:
            bloques.append((inicio, pos - 1))

            if pos < n:
                comp_actual = comp_de_nodo[orden[pos] + 1]
                inicio = pos

    return {
        "M1": M1,
        "iteraciones": iteraciones,
        "R": R,
        "orden": orden,
        "R_filas": R_filas,
        "R_final": R_final,
        "componentes": componentes,
        "bloques": bloques,
    }


def celdas_nuevas(iteracion):
    celdas = set()

    for i, j, intermedio in iteracion["nuevos"]:
        celdas.add((i, j))

    return celdas


def texto_nuevos(etiquetas, iteracion):
    exponente = iteracion["exponente"]

    if iteracion["estable"]:
        return (f"M^{exponente} es igual a M^{exponente - 1}: ya no aparecen 1's nuevos, "
                f"así que la matriz de caminos es M^{exponente - 1}.")

    maximo_mostrar = 12
    partes = []

    for i, j, intermedio in iteracion["nuevos"][:maximo_mostrar]:
        partes.append(f"{etiquetas[i]}→{etiquetas[j]} (por {etiquetas[intermedio]})")

    texto = "1's nuevos (naranja): " + ", ".join(partes)

    if len(iteracion["nuevos"]) > maximo_mostrar:
        texto = texto + f" ... (y {len(iteracion['nuevos']) - maximo_mostrar} más)"

    return texto


def texto_alcance(R, etiquetas):
    n = len(R)
    lineas = ["Nodos alcanzables desde cada nodo:"]

    for i in range(n):
        alcanzables = []
        for j in range(n):
            if R[i][j] == 1:
                alcanzables.append(etiquetas[j])

        lineas.append(f"  {etiquetas[i]} llega hasta: {', '.join(alcanzables)}")

    return "\n".join(lineas)


def texto_cantidades(R, orden, etiquetas):
    cantidades = []

    for i in orden:
        cantidades.append(f"{etiquetas[i]} tiene {int(np.sum(R[i]))}")

    return "Cantidad de 1's por fila (en el orden mostrado):\n  " + ", ".join(cantidades)


def dibujar_grafo_en_ejes(ax, matriz, componentes, etiquetas, separar_componentes=False, titulo="Grafo",
                          posicion_leyenda="derecha", colorear=True, tamano_nodo=800, tamano_letra=12,
                          posiciones_guardadas=None):
    n = len(matriz)

    comp_de = [0] * n
    for idx_comp, componente in enumerate(componentes):
        for nodo in componente:
            comp_de[nodo - 1] = idx_comp

    if separar_componentes:
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
    elif posiciones_guardadas is not None:
        posiciones = []
        for x, y in posiciones_guardadas:
            posiciones.append((x * 2 - 1, 1 - y * 2))
    else:
        angulos = np.linspace(0, 2 * np.pi, n, endpoint=False)
        posiciones = [(np.cos(a), np.sin(a)) for a in angulos]

    for i in range(n):
        for j in range(n):

            if matriz[i][j] != 1:
                continue

            if i == j:
                continue

            if separar_componentes and comp_de[i] != comp_de[j]:
                continue

            x1, y1 = posiciones[i]
            x2, y2 = posiciones[j]
            ax.annotate(
                "", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1,
                                 shrinkA=15, shrinkB=15),
                zorder=1
            )

    if colorear:
        colores = plt.cm.tab10.colors

        for num_comp, componente in enumerate(componentes, start=1):
            color = colores[(num_comp - 1) % len(colores)]

            for nodo in componente:
                x, y = posiciones[nodo - 1]
                ax.scatter(x, y, s=tamano_nodo, color=color, label=f"Componente {num_comp}", zorder=2)
                ax.text(x, y, etiquetas[nodo - 1], ha="center", va="center", fontsize=tamano_letra)

        handles, labels = ax.get_legend_handles_labels()
        vistos = dict(zip(labels, handles))

        if posicion_leyenda == "abajo":
            columnas_leyenda = min(len(vistos), 6)
            ax.legend(list(vistos.values()), list(vistos.keys()), loc="upper center",
                      bbox_to_anchor=(0.5, -0.06), ncol=columnas_leyenda, fontsize=8)
        else:
            ax.legend(list(vistos.values()), list(vistos.keys()),
                      loc="upper left", bbox_to_anchor=(1.02, 1))
    else:
        for nodo in range(1, n + 1):
            x, y = posiciones[nodo - 1]
            ax.scatter(x, y, s=tamano_nodo, color="#8ecae6", zorder=2)
            ax.text(x, y, etiquetas[nodo - 1], ha="center", va="center", fontsize=tamano_letra)

    ax.set_title(titulo)
    ax.axis("equal")
    ax.axis("off")


def construir_grafo(matriz, componentes, etiquetas, separar_componentes=False, titulo="Grafo", figsize=(8, 8), fig=None):
    if fig is None:
        fig = plt.figure(figsize=figsize)

    ax = fig.add_subplot(111)
    dibujar_grafo_en_ejes(ax, matriz, componentes, etiquetas, separar_componentes, titulo)
    fig.tight_layout()

    return fig


def dibujar_grafo(matriz, componentes, etiquetas, separar_componentes=False, titulo="Grafo"):
    construir_grafo(matriz, componentes, etiquetas, separar_componentes, titulo)
    plt.show()


# Informe en PDF

ANCHO_A4 = 8.27
ALTO_A4 = 11.69

COLOR_UNO = "lightgreen"
COLOR_NUEVO = "#ffb84d"
COLOR_DIAGONAL = "#9ecbff"


def ajustar(texto, ancho):
    lineas = []

    for linea in texto.split("\n"):
        lineas.append(textwrap.fill(linea, ancho, subsequent_indent="    "))

    return "\n".join(lineas)


COLORES_SECCION = {
    "1. Interpretación": "#2f6db5",
    "2. Representación": "#2e8b57",
    "3. Cálculo": "#c0702a",
    "4. Análisis": "#7a3fa0",
}


def nueva_pagina(titulo, descripcion="", seccion=""):
    fig = Figure(figsize=(ANCHO_A4, ALTO_A4))

    if seccion in COLORES_SECCION:
        fig.add_artist(Rectangle((0, 0.965), 1, 0.035, transform=fig.transFigure,
                                 facecolor=COLORES_SECCION[seccion], edgecolor="none"))
        fig.text(0.07, 0.9825, seccion, ha="left", va="center", fontsize=11,
                 fontweight="bold", color="white")

    fig.text(0.5, 0.94, titulo, ha="center", va="center", fontsize=16, fontweight="bold")

    if descripcion != "":
        fig.text(0.07, 0.915, ajustar(descripcion, 80), ha="left", va="top",
                 fontsize=10, color="#333333")

    return fig


def escribir_texto(fig, y, texto, tamano=10, negrita=False, color="black", sangria=0.0):
    ancho = int(480 / (tamano * 0.6))
    texto = ajustar(texto, ancho)
    cantidad_lineas = texto.count("\n") + 1

    if negrita:
        peso = "bold"
    else:
        peso = "normal"

    fig.text(0.07 + sangria, y, texto, ha="left", va="top", fontsize=tamano,
             fontweight=peso, color=color, linespacing=1.35)

    alto_en_pulgadas = cantidad_lineas * tamano * 1.35 / 72

    return y - alto_en_pulgadas / ALTO_A4


def escribir_bloque(fig, y, encabezado, lineas, espacio=0.012):
    y = escribir_texto(fig, y, encabezado, tamano=11, negrita=True, color="#1a3d6b")
    y = y - 0.004

    for linea in lineas:
        y = escribir_texto(fig, y, linea, tamano=10)
        y = y - 0.003

    return y - espacio


def lado_de_matriz(n, maximo):
    celda = 0.8

    if celda * (n + 1) > maximo:
        celda = maximo / (n + 1)

    return celda * (n + 1)


def dibujar_matriz_en_figura(fig, izquierda, abajo, lado, M, etiquetas_filas, etiquetas_columnas,
                             bloques=None, nuevos=None, diagonal=None):
    n = len(M)
    bloques = bloques or []
    nuevos = nuevos or set()
    diagonal = diagonal or set()

    ax = fig.add_axes([izquierda / ANCHO_A4, abajo / ALTO_A4, lado / ANCHO_A4, lado / ALTO_A4])
    ax.set_xlim(0, n + 1)
    ax.set_ylim(n + 1, 0)
    ax.axis("off")

    if n <= 5:
        tamano = 13
    elif n <= 8:
        tamano = 11
    else:
        tamano = 9

    largo_maximo = 1
    for etiqueta in list(etiquetas_filas) + list(etiquetas_columnas):
        if len(etiqueta) > largo_maximo:
            largo_maximo = len(etiqueta)

    if largo_maximo >= 3 and n >= 9:
        tamano_etiqueta = 6.5
    elif largo_maximo >= 3:
        tamano_etiqueta = tamano - 1
    else:
        tamano_etiqueta = tamano

    for j in range(n):
        ax.text(j + 1.5, 0.5, etiquetas_columnas[j], ha="center", va="center",
                fontsize=tamano_etiqueta, fontweight="bold")

    for i in range(n):
        ax.text(0.5, i + 1.5, etiquetas_filas[i], ha="center", va="center",
                fontsize=tamano_etiqueta, fontweight="bold")

    for i in range(n):
        for j in range(n):
            valor = int(M[i][j])

            if (i, j) in nuevos:
                color = COLOR_NUEVO
            elif (i, j) in diagonal:
                color = COLOR_DIAGONAL
            elif valor == 1:
                color = COLOR_UNO
            else:
                color = "white"

            ax.add_patch(Rectangle((j + 1, i + 1), 1, 1, facecolor=color, edgecolor="gray", linewidth=0.8))
            ax.text(j + 1.5, i + 1.5, str(valor), ha="center", va="center", fontsize=tamano)

    for inicio, fin in bloques:
        tam = fin - inicio + 1
        ax.add_patch(Rectangle((inicio + 1, inicio + 1), tam, tam, fill=False, edgecolor="red", linewidth=3))


def pagina_matriz(titulo, descripcion, M, etiquetas_filas, etiquetas_columnas,
                  bloques=None, nuevos=None, diagonal=None, texto_abajo="", seccion=""):
    n = len(M)
    fig = nueva_pagina(titulo, descripcion, seccion)

    lado = lado_de_matriz(n, 6.6)
    arriba = 9.6
    izquierda = (ANCHO_A4 - lado) / 2

    dibujar_matriz_en_figura(fig, izquierda, arriba - lado, lado, M, etiquetas_filas, etiquetas_columnas,
                             bloques=bloques, nuevos=nuevos, diagonal=diagonal)

    if texto_abajo != "":
        fig.text(0.07, (arriba - lado - 0.3) / ALTO_A4, ajustar(texto_abajo, 88),
                 ha="left", va="top", fontsize=9, linespacing=1.4)

    return fig


def lista_de_aristas(matriz, etiquetas, maximo=40):
    n = len(matriz)
    partes = []
    total = 0

    for i in range(n):
        for j in range(n):
            if matriz[i][j] == 1:
                total += 1

                if len(partes) < maximo:
                    if i == j:
                        partes.append(f"{etiquetas[i]}→{etiquetas[j]} (bucle)")
                    else:
                        partes.append(f"{etiquetas[i]}→{etiquetas[j]}")

    if total == 0:
        return "ninguna"

    texto = ", ".join(partes)

    if total > maximo:
        texto = texto + f" ... (y {total - maximo} más)"

    return texto


def pagina_interpretacion(matriz, etiquetas):
    n = len(matriz)
    aristas = int(np.sum(matriz))
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    fig = nueva_pagina(
        "Informe de razonamiento cuantitativo",
        f"Componentes conexas de un grafo dirigido  -  {fecha}",
        seccion="1. Interpretación"
    )

    y = 0.88

    y = escribir_bloque(fig, y, "¿De qué trata el problema?", [
        f"Se tiene un grafo dirigido con {n} nodos ({', '.join(etiquetas)}) y {aristas} aristas. "
        "Cada arista X→Y indica que se puede ir del nodo X hacia el nodo Y. El problema consiste en "
        "estudiar cómo están conectados los nodos entre sí."
    ])

    y = escribir_bloque(fig, y, "¿Qué se pide?", [
        "Determinar las componentes conexas del grafo, es decir, los subgrafos conexos disjuntos "
        "con el mayor número de vértices que se pueden formar a partir del grafo original, e indicar "
        "si el grafo es conexo."
    ])

    y = escribir_bloque(fig, y, "¿Qué datos se tienen?", [
        f"• Cantidad de nodos: n = {n}.",
        f"• Nombres de los nodos: {', '.join(etiquetas)}.",
        f"• Cantidad de aristas: {aristas}.",
        f"• Aristas (origen → destino): {lista_de_aristas(matriz, etiquetas)}."
    ])

    y = escribir_bloque(fig, y, "¿Qué se utilizará?", [
        "• La matriz de adyacencia M del grafo (fila = origen, columna = destino).",
        "• La matriz de caminos M_R∞, calculada con las potencias de M (producto booleano), para saber "
        "qué nodos se alcanzan entre sí.",
        "• El orden de las filas según la cantidad de 1's y los bloques cuadrados diagonales de 1's, "
        "que forman las componentes conexas."
    ])

    return fig


def pagina_representacion(matriz, etiquetas):
    n = len(matriz)
    aristas = int(np.sum(matriz))

    fig = nueva_pagina(
        "Variables, restricciones y matriz",
        "Se definen las variables del problema, las restricciones que cumplen los datos y se "
        "representa el grafo con su matriz de adyacencia.",
        seccion="2. Representación"
    )

    y = 0.86

    y = escribir_bloque(fig, y, "Variables", [
        f"• n = {n}: cantidad de nodos del grafo.",
        f"• V = {{{', '.join(etiquetas)}}}: conjunto de vértices (nodos).",
        f"• E: conjunto de aristas dirigidas, pares (origen, destino). Aquí |E| = {aristas}.",
        "• M = [m_ij]: matriz de adyacencia de n × n; m_ij = 1 si existe la arista i → j y m_ij = 0 si no existe.",
        "• M^k: potencia k de M con producto booleano; m_ij = 1 si hay un camino de i a j de hasta k pasos.",
        "• M_R∞: matriz de caminos (la potencia de M que ya no cambia)."
    ])

    y = escribir_bloque(fig, y, "Restricciones", [
        f"• 4 ≤ n ≤ 12 (en este problema n = {n}, se cumple).",
        "• m_ij ∈ {0, 1} para todo i, j.",
        "• El grafo es dirigido: m_ij puede ser distinto de m_ji.",
        "• Todo nodo llega a sí mismo: antes de calcular los caminos se completa la diagonal con 1's (m_ii = 1).",
        "• Los nombres de los nodos son distintos entre sí.",
        "• Dos nodos i y j están en la misma componente conexa si i llega a j y j llega a i."
    ])

    y = escribir_texto(fig, y, "Matriz de adyacencia M (fila = origen, columna = destino)",
                       tamano=11, negrita=True, color="#1a3d6b")

    disponible = y * ALTO_A4 - 1.0
    lado = lado_de_matriz(n, min(5.8, disponible))
    arriba = y * ALTO_A4 - 0.15

    dibujar_matriz_en_figura(fig, (ANCHO_A4 - lado) / 2, arriba - lado, lado, matriz, etiquetas, etiquetas)

    return fig


def pagina_grafo_representacion(matriz, etiquetas, componentes, posiciones):
    fig = nueva_pagina(
        "Gráfico del grafo",
        "Figura 1. Cada flecha va de un nodo origen a un nodo destino. Los colores de las "
        "componentes se mostrarán al final, en el análisis.",
        seccion="2. Representación"
    )

    ax = fig.add_axes([0.08, 0.08, 0.84, 0.74])
    dibujar_grafo_en_ejes(ax, matriz, componentes, etiquetas, separar_componentes=False,
                          titulo="Grafo original", colorear=False, tamano_nodo=650, tamano_letra=11,
                          posiciones_guardadas=posiciones)

    return fig


def pagina_analisis(matriz, etiquetas, componentes):
  n = len(matriz)
  k = len(componentes)

  fig = nueva_pagina(
      "Análisis y respuesta",
      "Se responde lo que pedía el problema a partir de los cálculos"
      " realizados.",
      seccion="4. Análisis",
  )

  nombres_componentes = []
  lineas_componentes = []
  for numero, comp in enumerate(componentes, start=1):
    nombres = []
    for nodo in comp:
      nombres.append(etiquetas[nodo - 1])

    nombres_componentes.append(f"V{numero} = {{{', '.join(nombres)}}}")
    lineas_componentes.append(
        f"V{numero} = {{{', '.join(nombres)}}}   ({len(comp)} nodos)"
    )

  if k == 1:
    texto_conexo = (
        f"Sí, el grafo es conexo: hay una única componente que contiene a los"
        f" {n} nodos, o sea, todos los nodos se alcanzan entre sí."
    )
  else:
    texto_conexo = (
        f"No, el grafo no es conexo: está formado por {k} subgrafos conexos que"
        " no tienen vértices en común."
    )

  y = 0.88

  lineas_respuesta = (
      [f"El grafo tiene {k} componente(s) conexa(s):"]
      + lineas_componentes
      + [texto_conexo]
  )

  y = escribir_bloque(fig, y, "Respuesta", lineas_respuesta)

  y = escribir_bloque(fig, y, "Conclusión", [
      "Las componentes conexas del grafo son: "
      + "; ".join(nombres_componentes)
      + "."
  ])

  altura = y - 0.12
  if altura < 0.25:
    altura = 0.25

  ax = fig.add_axes([0.08, 0.08, 0.84, altura])
  dibujar_grafo_en_ejes(
      ax,
      matriz,
      componentes,
      etiquetas,
      separar_componentes=True,
      titulo="Figura 2. Componentes conexas del grafo",
      posicion_leyenda="abajo",
      tamano_nodo=600,
      tamano_letra=11,
  )

  return fig


def pagina_potencias(iteraciones, etiquetas):
    n = len(etiquetas)
    fig = nueva_pagina(
        "Paso 2: matriz de caminos (potencias de M)",
        "Se multiplica (producto booleano) la matriz anterior por la matriz M del Paso 1: hay un 1 en "
        "la posición (i, j) si existe un nodo t tal que i llega a t y desde t hay una arista hacia j. "
        "Los 1's nuevos se marcan en naranja. Se repite hasta que ya no aparezcan 1's nuevos.",
        seccion="3. Cálculo"
    )

    lado = lado_de_matriz(n, 3.6)
    alto_bloque = 4.9

    for posicion, it in enumerate(iteraciones):
        exponente = it["exponente"]
        arriba = 9.45 - posicion * alto_bloque

        fig.text(0.5, (arriba + 0.25) / ALTO_A4, f"M^{exponente} = M^{exponente - 1} · M",
                 ha="center", va="center", fontsize=11, fontweight="bold")

        dibujar_matriz_en_figura(fig, (ANCHO_A4 - lado) / 2, arriba - lado, lado, it["matriz"],
                                 etiquetas, etiquetas, nuevos=celdas_nuevas(it))

        fig.text(0.07, (arriba - lado - 0.15) / ALTO_A4, ajustar(texto_nuevos(etiquetas, it), 88),
                 ha="left", va="top", fontsize=9)

    return fig


def crear_paginas_informe(matriz, etiquetas, posiciones=None):
    n = len(matriz)
    datos = calcular_procedimiento(matriz)
    componentes = datos["componentes"]

    etiquetas_orden = []
    for i in datos["orden"]:
        etiquetas_orden.append(etiquetas[i])

    diagonal = set()
    for i in range(n):
        if matriz[i][i] == 0:
            diagonal.add((i, i))

    if len(diagonal) > 0:
        texto_diagonal = "Los 1's agregados en la diagonal principal se muestran en azul."
    else:
        texto_diagonal = "La diagonal principal ya tenía 1's, no fue necesario agregar ninguno."

    lineas_bloques = ["Bloques diagonales de 1's (marcados en rojo), de arriba hacia abajo:"]
    for numero, (inicio, fin) in enumerate(datos["bloques"], start=1):
        lineas_bloques.append(f"  Bloque {numero} = {{{', '.join(etiquetas_orden[inicio:fin + 1])}}}")

    paginas = []

    paginas.append(("1. Interpretación del problema", pagina_interpretacion(matriz, etiquetas)))

    paginas.append(("2. Representación: variables, restricciones y matriz",
                    pagina_representacion(matriz, etiquetas)))
    paginas.append(("2. Representación: gráfico del grafo",
                    pagina_grafo_representacion(matriz, etiquetas, componentes, posiciones)))

    paginas.append(("3. Cálculo - Paso 1: matriz con diagonal", pagina_matriz(
        "Paso 1: matriz de adyacencia con diagonal",
        "Se construye la matriz de adyacencia del grafo y se agrega el valor 1 en toda la "
        "diagonal principal.",
        datos["M1"], etiquetas, etiquetas, diagonal=diagonal, texto_abajo=texto_diagonal,
        seccion="3. Cálculo"
    )))

    iteraciones = datos["iteraciones"]
    for inicio in range(0, len(iteraciones), 2):
        paginas.append(("3. Cálculo - Paso 2: potencias de M",
                        pagina_potencias(iteraciones[inicio:inicio + 2], etiquetas)))

    paginas.append(("3. Cálculo - Paso 2: matriz de caminos", pagina_matriz(
        "Paso 2: matriz de caminos (resultado)",
        "Es la matriz M_R∞ que se obtiene cuando al multiplicar ya no aparecen 1's nuevos: "
        "indica qué nodos son alcanzables desde cada nodo.",
        datos["R"], etiquetas, etiquetas, texto_abajo=texto_alcance(datos["R"], etiquetas),
        seccion="3. Cálculo"
    )))

    paginas.append(("3. Cálculo - Paso 3: ordenar filas", pagina_matriz(
        "Paso 3: ordenar filas",
        "Se ordenan las filas según la cantidad de 1's que contienen (de mayor a menor). "
        "En caso de empate, se prioriza la fila cuyo primer 1 esté más cerca de la primera columna.",
        datos["R_filas"], etiquetas_orden, etiquetas,
        texto_abajo=texto_cantidades(datos["R"], datos["orden"], etiquetas),
        seccion="3. Cálculo"
    )))

    paginas.append(("3. Cálculo - Paso 4: ordenar columnas y formar bloques", pagina_matriz(
        "Paso 4: ordenar columnas y formar bloques",
        "Se reordenan las columnas en el mismo orden que las filas. Los bloques cuadrados "
        "diagonales formados por 1's (marcados en rojo) son las componentes conexas.",
        datos["R_final"], etiquetas_orden, etiquetas_orden, bloques=datos["bloques"],
        texto_abajo="\n".join(lineas_bloques), seccion="3. Cálculo"
    )))

    paginas.append(("4. Análisis y respuesta", pagina_analisis(matriz, etiquetas, componentes)))

    return paginas


def guardar_informe_pdf(ruta, paginas):
    with PdfPages(ruta) as pdf:
        for titulo, fig in paginas:
            pdf.savefig(fig)


# Aplicación

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Componentes Conexas")
        self.root.geometry("860x750")

        self.modo = None
        self.n = 4
        self.matriz = None
        self.etiquetas = []
        self.posiciones = None
        self.ventana_manual = None

        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        self.pantalla_bienvenida = PantallaBienvenida(self.container, self)
        self.pantalla_matriz = PantallaMatriz(self.container, self)

        for pantalla in (self.pantalla_bienvenida, self.pantalla_matriz):
            pantalla.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.root.bind("<F1>", lambda evento: self.abrir_manual())

        self.mostrar_bienvenida()

    def mostrar_bienvenida(self):
        self.pantalla_bienvenida.tkraise()

    def abrir_manual(self):
        if self.ventana_manual is not None:
            self.ventana_manual.lift()
            return

        VentanaManual(self.root, self)

    def guardar_grafo(self):
        cantidad = len(listar_ejercicios())

        nombre = simpledialog.askstring(
            "Guardar ejercicio", "Ponle un nombre al ejercicio:",
            initialvalue=f"Ejercicio {cantidad + 1}", parent=self.root
        )

        if nombre is None:
            return

        nombre = nombre.strip()

        if nombre == "":
            messagebox.showerror("Error", "El nombre no puede estar vacío")
            return

        ruta = os.path.join(carpeta_ejercicios(), nombre_de_archivo(nombre))

        if os.path.exists(ruta):
            respuesta = messagebox.askyesno(
                "Guardar ejercicio",
                f"Ya existe un ejercicio llamado «{nombre}».\n¿Deseas reemplazarlo?"
            )

            if not respuesta:
                return

        try:
            guardar_ejercicio(nombre, self.etiquetas_actuales(), self.matriz, self.posiciones)
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo guardar el ejercicio:\n{error}")
            return

        messagebox.showinfo("Ejercicio guardado", f"«{nombre}» se guardó. Lo verás en \"Ejercicios guardados\".")

    def abrir_ejercicios(self, confirmar=False):
        VentanaEjercicios(self.root, self, confirmar)

    def exportar_qr(self):
        VentanaMostrarQR(self.root, self)

    def importar_qr(self):
        ruta = filedialog.askopenfilename(
            parent=self.root,
            title="Cargar ejercicio desde QR",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp"), ("Todos los archivos", "*.*")]
        )
        if not ruta:
            return

        try:
            nombre, etiquetas, matriz, posiciones = leer_grafo_desde_qr(ruta)
            self.aplicar_grafo(nombre, etiquetas, matriz, posiciones)
        except Exception as error:
            messagebox.showerror("Error al leer QR", str(error), parent=self.root)

    def aplicar_grafo(self, nombre, etiquetas, matriz, posiciones=None):
        self.modo = "manual"
        self.n = len(matriz)
        self.matriz = matriz.copy()
        self.etiquetas = list(etiquetas)
        self.posiciones = posiciones

        self.mostrar_matriz()
        messagebox.showinfo("Ejercicio cargado", f"Se cargó «{nombre}».")

    def mostrar_matriz(self):
        self.pantalla_matriz.actualizar()
        self.pantalla_matriz.tkraise()

    def etiquetas_actuales(self):
        if len(self.etiquetas) != self.n:
            self.etiquetas = []

            for i in range(self.n):
                self.etiquetas.append(str(i + 1))

        return list(self.etiquetas)


# Pantalla de bienvenida

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

        self.botones_modo = {
            "aleatorio": self.btn_aleatorio,
            "manual": self.btn_manual,
        }

        tk.Label(self, text="Dime cant. de nodos (4-12):", font=("Arial", 11)).pack(pady=(20, 5))
        self.entry_n = tk.Spinbox(self, from_=4, to=12, width=5, justify="center")
        self.entry_n.pack(pady=5)

        tk.Button(self, text="Iniciar", width=15, height=2, command=self.iniciar).pack(pady=(30, 10))

        tk.Label(self, text="o carga un ejercicio desde un código QR:", font=("Arial", 10), fg="gray20").pack(pady=(5, 3))
        tk.Button(self, text="Cargar desde QR", width=22, bg="#e1d5f5", command=self.app.importar_qr).pack()

        tk.Label(self, text="o abre un ejercicio que guardaste antes:", font=("Arial", 10), fg="gray20").pack(pady=(10, 3))
        tk.Button(self, text="Ejercicios guardados", width=22, command=self.app.abrir_ejercicios).pack()

        tk.Button(self, text="Manual de usuario", width=22, command=self.app.abrir_manual).pack(pady=(25, 0))

    def elegir_modo(self, modo):
        self.app.modo = modo

        for nombre, boton in self.botones_modo.items():
            if nombre == modo:
                boton.config(relief="sunken")
            else:
                boton.config(relief="raised")

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
        self.app.etiquetas = []
        self.app.posiciones = None

        if self.app.modo == "aleatorio":
            self.app.matriz = crear_grafo_aleatorio(n)
        else:
            self.app.matriz = np.zeros((n, n), dtype=int)

        self.app.mostrar_matriz()


# Pantalla de la matriz

class PantallaMatriz(tk.Frame):
    TAMANO_VISTA = 300
    RADIO_NODO_VISTA = 15

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.ventana_edicion = None

        self.lienzo_scroll = tk.Canvas(self, highlightthickness=0, yscrollincrement=20)
        barra_scroll = ttk.Scrollbar(self, orient="vertical", command=self.lienzo_scroll.yview)
        self.lienzo_scroll.configure(yscrollcommand=barra_scroll.set)
        barra_scroll.pack(side="right", fill="y")
        self.lienzo_scroll.pack(side="left", fill="both", expand=True)

        cuerpo = tk.Frame(self.lienzo_scroll)
        ventana_cuerpo = self.lienzo_scroll.create_window((0, 0), window=cuerpo, anchor="nw")

        cuerpo.bind("<Configure>", lambda evento: self.lienzo_scroll.configure(scrollregion=self.lienzo_scroll.bbox("all")))
        self.lienzo_scroll.bind("<Configure>", lambda evento: self.lienzo_scroll.itemconfigure(ventana_cuerpo, width=evento.width))

        self.bind_all("<MouseWheel>", self.rueda_mouse, add="+")
        self.bind_all("<Button-4>", self.rueda_mouse, add="+")
        self.bind_all("<Button-5>", self.rueda_mouse, add="+")

        barra_superior = tk.Frame(cuerpo)
        barra_superior.pack(fill="x", pady=5, padx=5)
        tk.Button(barra_superior, text="< Atras", command=self.volver).pack(side="left")
        tk.Button(barra_superior, text="Manual de usuario", command=self.app.abrir_manual).pack(side="right")

        tk.Label(cuerpo, text="Matriz", font=("Arial", 16, "bold")).pack(pady=5)

        tk.Label(
            cuerpo,
            text="Grafo dirigido: cada arista va de un Origen a un Destino.\n"
                 "Con \"Editar Matriz o Gráfico\" puedes agregar o quitar aristas (también dibujándolas) y cambiar las\n"
                 "etiquetas de los nodos. También puedes revertir el grafo,\n"
                 "graficar el resultado, ver el procedimiento paso a paso,\n"
                 "generar un informe en PDF o guardar el ejercicio.",
            font=("Arial", 9), fg="gray20", justify="center", wraplength=460
        ).pack(pady=(0, 10))

        frame_central = tk.Frame(cuerpo)
        frame_central.pack(pady=10)

        self.frame_matriz = tk.Frame(frame_central)
        self.frame_matriz.grid(row=0, column=0, padx=(0, 20), sticky="n")

        frame_original = tk.Frame(frame_central)
        frame_original.grid(row=0, column=1, sticky="n")

        tk.Label(frame_original, text="Grafo original", font=("Arial", 10, "bold")).pack()
        self.lienzo_original = tk.Canvas(frame_original, width=self.TAMANO_VISTA, height=self.TAMANO_VISTA,
                                         bg="white", highlightthickness=1, highlightbackground="gray60")
        self.lienzo_original.pack(pady=3)

        frame_botones = tk.Frame(cuerpo)
        frame_botones.pack(pady=10)

        botones = [
            ("Editar Matriz o Gráfico", self.abrir_edicion, None, 0, 0, 1),
            ("Revertir", self.revertir, "#ffe0b3", 0, 1, 1),
            (
                "Graficar componentes conexas",
                self.graficar,
                "lightblue",
                0,
                2,
                1,
            ),
            (
                "Ver procedimiento paso a paso",
                self.ver_procedimiento,
                "#d9c7ff",
                0,
                3,
                1,
            ),
            ("Guardar ejercicio", self.app.guardar_grafo, "#dfe9f7", 1, 0, 1),
            (
                "Ejercicios guardados",
                lambda: self.app.abrir_ejercicios(confirmar=True),
                "#dfe9f7",
                1,
                1,
                1,
            ),
            ("Compartir por QR", self.app.exportar_qr, "#e1d5f5", 1, 2, 1),
            ("Generar informe", self.generar_informe, "#c7f0d8", 1, 3, 1),
        ]

        for texto, comando, color, fila, columna, ancho in botones:
          boton = tk.Button(frame_botones, text=texto, command=comando)
          if color is not None:
            boton.config(bg=color)
          boton.grid(
              row=fila,
              column=columna,
              columnspan=ancho,
              padx=4,
              pady=4,
              sticky="ew",
          )

        f_resultado = ttk.LabelFrame(cuerpo, text="Resultado final", padding=10)
        f_resultado.pack(fill="x", padx=10, pady=5)
        self.text_resultado = tk.Text(f_resultado, height=6, width=60)
        self.text_resultado.pack(fill="both", expand=True)

        f_analisis = ttk.LabelFrame(cuerpo, text="Análisis de nodo", padding=10)
        f_analisis.pack(fill="x", padx=10, pady=5)
        self.nodo_analisis = tk.StringVar(value="1")
        ttk.Label(f_analisis, text="Nodo:").pack(side="left", padx=5)
        self.spin_analisis = ttk.Combobox(f_analisis, textvariable=self.nodo_analisis, width=5, state="readonly")
        self.spin_analisis.pack(side="left", padx=5)
        ttk.Button(f_analisis, text="Analizar", command=self.analizar).pack(side="left", padx=10)
        self.text_analisis = tk.Text(f_analisis, height=3, width=50)
        self.text_analisis.pack(side="left", fill="both", expand=True, padx=5)

    def rueda_mouse(self, evento):
        try:
            widget = self.winfo_containing(evento.x_root, evento.y_root)
        except (KeyError, tk.TclError):
            return

        if widget is None or not str(widget).startswith(str(self)) or isinstance(widget, tk.Text):
            return

        if evento.num == 4:
            paso = -1
        elif evento.num == 5:
            paso = 1
        elif evento.delta > 0:
            paso = -1
        else:
            paso = 1

        self.lienzo_scroll.yview_scroll(paso * 3, "units")

    def volver(self):
        self.cerrar_edicion()
        self.app.mostrar_bienvenida()

    def abrir_edicion(self):
        if self.ventana_edicion is not None:
            self.ventana_edicion.lift()
            return

        self.ventana_edicion = VentanaEditarMatriz(self)

    def cerrar_edicion(self):
        if self.ventana_edicion is not None:
            self.ventana_edicion.cerrar()

    def revertir(self):
        respuesta = messagebox.askyesno(
            "Revertir",
            "Esto borrará todas las conexiones del grafo actual (la matriz quedará vacía).\n¿Deseas continuar?"
        )

        if not respuesta:
            return

        n = self.app.n
        self.app.matriz = np.zeros((n, n), dtype=int)
        self.actualizar()

    def actualizar(self):
        n = self.app.n
        matriz = self.app.matriz
        etiquetas = self.app.etiquetas_actuales()

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

        posiciones = self.app.posiciones or posiciones_en_circulo(n)
        dibujar_grafo_en_lienzo(self.lienzo_original, matriz, etiquetas, posiciones,
                                self.TAMANO_VISTA, self.RADIO_NODO_VISTA)

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

        posicion = self.spin_analisis.current()

        if posicion < 0 or posicion >= n:
            posicion = 0

        self.spin_analisis.config(values=etiquetas)
        self.spin_analisis.current(posicion)

        self.text_analisis.delete(1.0, tk.END)

    def analizar(self):
        n = self.app.n
        matriz = self.app.matriz
        etiquetas = self.app.etiquetas_actuales()
        idx = self.spin_analisis.current()

        if idx < 0 or idx >= n:
            messagebox.showerror("Error", "Elige un nodo de la lista")
            return

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

        dibujar_grafo(self.app.matriz, componentes, etiquetas,
                      separar_componentes=True, titulo="Componentes Conexas")

    def ver_procedimiento(self):
        VentanaPasos(self, self.app.matriz, self.app.etiquetas_actuales())

    def generar_informe(self):
        self.config(cursor="watch")
        self.update_idletasks()

        try:
            paginas = crear_paginas_informe(self.app.matriz, self.app.etiquetas_actuales(),
                                            self.app.posiciones)
        except Exception as error:
            self.config(cursor="")
            messagebox.showerror("Error", f"No se pudo generar el informe:\n{error}")
            return

        self.config(cursor="")
        VentanaVistaPrevia(self, paginas)


# Dibujo del grafo en el lienzo

COLOR_NODO = "#8ecae6"
COLOR_TEXTO_NODO = "#0b2a3a"


def posiciones_en_circulo(n):
    posiciones = []

    for i in range(n):
        angulo = 2 * np.pi * i / n - np.pi / 2
        posiciones.append([float(0.5 + 0.4 * np.cos(angulo)), float(0.5 + 0.4 * np.sin(angulo))])

    return posiciones


def dibujar_grafo_en_lienzo(lienzo, matriz, etiquetas, posiciones, tamano, radio_nodo, nodo_pendiente=None):
    n = len(matriz)
    puntos = []

    for x, y in posiciones:
        puntos.append((x * tamano, y * tamano))

    lienzo.delete("all")

    for i in range(n):
        for j in range(n):
            if matriz[i][j] != 1:
                continue

            x1, y1 = puntos[i]

            if i == j:
                cx_lienzo, cy_lienzo = tamano / 2.0, tamano / 2.0
                vx, vy = x1 - cx_lienzo, y1 - cy_lienzo
                largo_v = np.hypot(vx, vy)

                if largo_v == 0:
                    ux, uy = 0.0, -1.0
                else:
                    ux, uy = vx / largo_v, vy / largo_v

                px, py = -uy, ux

                x_salida = x1 + (ux * 0.85 - px * 0.5) * radio_nodo
                y_salida = y1 + (uy * 0.85 - py * 0.5) * radio_nodo

                x_entrada = x1 + (ux * 0.85 + px * 0.5) * radio_nodo
                y_entrada = y1 + (uy * 0.85 + py * 0.5) * radio_nodo

                distancia = radio_nodo * 2.2
                cp1_x = x1 + ux * distancia - px * (radio_nodo * 1.3)
                cp1_y = y1 + uy * distancia - py * (radio_nodo * 1.3)

                cp2_x = x1 + ux * distancia + px * (radio_nodo * 1.3)
                cp2_y = y1 + uy * distancia + py * (radio_nodo * 1.3)

                lienzo.create_line(
                    x_salida, y_salida,
                    cp1_x, cp1_y,
                    cp2_x, cp2_y,
                    x_entrada, y_entrada,
                    smooth=True,
                    splinesteps=30,
                    arrow="last",
                    arrowshape=(9, 11, 4),
                    width=2,
                    fill="#444444"
                )
                continue

            x2, y2 = puntos[j]
            largo = np.hypot(x2 - x1, y2 - y1)

            if largo == 0:
                continue

            ux, uy = (x2 - x1) / largo, (y2 - y1) / largo
            lx, ly = -uy * 5, ux * 5

            lienzo.create_line(x1 + ux * radio_nodo + lx, y1 + uy * radio_nodo + ly,
                               x2 - ux * (radio_nodo + 2) + lx, y2 - uy * (radio_nodo + 2) + ly,
                               arrow="last", arrowshape=(10, 12, 4), width=2, fill="#444444")

    for i in range(n):
        x, y = puntos[i]

        if i == nodo_pendiente:
            borde, grosor = "#e67e22", 4
        else:
            borde, grosor = "#333333", 1

        lienzo.create_oval(x - radio_nodo, y - radio_nodo, x + radio_nodo, y + radio_nodo,
                           fill=COLOR_NODO, outline=borde, width=grosor)
        lienzo.create_text(x, y, text=etiquetas[i], fill=COLOR_TEXTO_NODO, font=("Arial", 10, "bold"))


class LienzoGrafo(tk.Canvas):
    TAMANO = 400
    RADIO_NODO = 18

    def __init__(self, parent, ventana):
        super().__init__(parent, width=self.TAMANO, height=self.TAMANO, bg="white",
                         highlightthickness=1, highlightbackground="gray60")
        self.ventana = ventana
        self.origen_arrastre = None
        self.nodo_pendiente = None

        self.bind("<ButtonPress-1>", self.al_presionar)
        self.bind("<B1-Motion>", self.al_mover)
        self.bind("<ButtonRelease-1>", self.al_soltar)

    def modo_actual(self):
        return self.ventana.var_modo.get()

    def punto_de(self, nodo):
        x, y = self.ventana.posiciones[nodo]
        return x * self.TAMANO, y * self.TAMANO

    def nodo_en(self, x, y):
        for i in range(len(self.ventana.posiciones)):
            px, py = self.punto_de(i)

            if (x - px) ** 2 + (y - py) ** 2 <= (self.RADIO_NODO + 4) ** 2:
                return i

        return None

    def dibujar(self):
        dibujar_grafo_en_lienzo(self, self.ventana.matriz, self.ventana.etiquetas, self.ventana.posiciones,
                                self.TAMANO, self.RADIO_NODO, self.nodo_pendiente)

    def al_presionar(self, evento):
        self.origen_arrastre = self.nodo_en(evento.x, evento.y)

    def al_mover(self, evento):
        if self.origen_arrastre is None:
            return

        if self.modo_actual() == "mover":
            self.mover_nodo(evento)
        else:
            self.trazar_flecha(evento)

    def al_soltar(self, evento):
        origen = self.origen_arrastre
        self.origen_arrastre = None
        self.delete("temporal")

        if self.modo_actual() == "mover":
            return

        destino = self.nodo_en(evento.x, evento.y)

        if origen is None or destino is None:
            self.nodo_pendiente = None
            self.dibujar()
            return

        if origen != destino:
            self.nodo_pendiente = None
            self.ventana.conectar(origen, destino)
            return

        if self.nodo_pendiente is None:
            self.nodo_pendiente = origen
            self.ventana.mostrar_estado(f"Origen: {self.ventana.etiquetas[origen]}. Haz clic en el destino o en el mismo nodo para bucle.")
        elif self.nodo_pendiente == origen:
            self.nodo_pendiente = None
            self.ventana.conectar(origen, origen)
        else:
            pendiente = self.nodo_pendiente
            self.nodo_pendiente = None
            self.ventana.conectar(pendiente, origen)

        self.dibujar()

    def mover_nodo(self, evento):
        x = min(max(evento.x / self.TAMANO, 0.06), 0.94)
        y = min(max(evento.y / self.TAMANO, 0.06), 0.94)

        self.ventana.posiciones[self.origen_arrastre] = [x, y]
        self.dibujar()

    def trazar_flecha(self, evento):
        x, y = self.punto_de(self.origen_arrastre)

        self.delete("temporal")
        self.create_line(x, y, evento.x, evento.y, arrow="last", dash=(4, 3), width=2,
                         fill="#e67e22", tags="temporal")


# Ventana para editar la matriz

class VentanaEditarMatriz(tk.Toplevel):
    TEXTO_FLECHAS = ("Arrastra de un nodo a otro (o haz clic en el origen y luego en el destino).\n"
                     "Si repites una flecha, se quita.")
    TEXTO_MOVER = ("Arrastra un nodo para acomodarlo donde quieras.\n"
                   "La posición se conserva al presionar Aceptar.")

    def __init__(self, pantalla):
        super().__init__(pantalla)
        self.pantalla = pantalla
        self.app = pantalla.app

        self.matriz = self.app.matriz.copy()
        self.etiquetas = self.app.etiquetas_actuales()
        self.posiciones = [list(posicion) for posicion in
                           (self.app.posiciones or posiciones_en_circulo(self.app.n))]

        self.modo_rapido = False

        self.var_modo = tk.StringVar(value="flechas")

        self.title("Editar Matriz o Gráfico")
        self.protocol("WM_DELETE_WINDOW", self.cancelar)

        tk.Label(self, text="Editar Matriz o Gráfico", font=("Arial", 14, "bold")).pack(pady=(10, 0))
        tk.Label(
            self,
            text="Fila = Origen, Columna = Destino.\n"
                 "Usa \"Editar arista\", el modo rápido o dibuja las flechas en el gráfico.\n"
                 "Con \"Nombrar nodos\" eliges un estilo de nombres para todos los nodos.\n"
                 "Los cambios se aplican al presionar Aceptar.",
            font=("Arial", 9), fg="gray20", justify="center", wraplength=460
        ).pack(pady=(0, 10))

        frame_central = tk.Frame(self)
        frame_central.pack(padx=15, pady=5)

        self.frame_matriz = tk.Frame(frame_central)
        self.frame_matriz.grid(row=0, column=0, padx=(0, 15), sticky="n")

        frame_dibujo = tk.Frame(frame_central)
        frame_dibujo.grid(row=0, column=1)

        tk.Label(frame_dibujo, text="Grafo original", font=("Arial", 10, "bold")).pack()
        self.lienzo = LienzoGrafo(frame_dibujo, self)
        self.lienzo.pack(pady=3)

        frame_modos = tk.Frame(frame_dibujo)
        frame_modos.pack()
        tk.Radiobutton(frame_modos, text="Dibujar flechas", variable=self.var_modo, value="flechas",
                       command=self.cambiar_modo).pack(side="left", padx=8)
        tk.Radiobutton(frame_modos, text="Mover nodos", variable=self.var_modo, value="mover",
                       command=self.cambiar_modo).pack(side="left", padx=8)

        self.label_dibujo = tk.Label(frame_dibujo, text=self.TEXTO_FLECHAS, font=("Arial", 9),
                                     fg="gray20", wraplength=380, justify="center")
        self.label_dibujo.pack()

        frame_botones = tk.Frame(self)
        frame_botones.pack(pady=10)

        tk.Button(frame_botones, text="Editar arista", command=self.editar_arista).grid(
            row=0, column=0, padx=5, pady=5, sticky="ew")
        tk.Button(frame_botones, text="Nombrar nodos", command=self.nombrar_nodos).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew")

        self.btn_rapido = tk.Button(frame_botones, text="Modo rápido: OFF",
                                    command=self.cambiar_modo_rapido, bg="#e6e6e6")
        self.btn_rapido.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        frame_final = tk.Frame(self)
        frame_final.pack(pady=(5, 12))

        tk.Button(frame_final, text="Aceptar", command=self.aceptar, bg="#b3e6b3", width=12).grid(row=0, column=0, padx=8)
        tk.Button(frame_final, text="Cancelar", command=self.cancelar, bg="#ffb3b3", width=12).grid(row=0, column=1, padx=8)

        self.refrescar()

        self.transient(pantalla)

        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def cerrar(self):
        self.pantalla.ventana_edicion = None
        self.destroy()

    def aceptar(self):
        pantalla = self.pantalla

        self.app.matriz[:] = self.matriz
        self.app.etiquetas = list(self.etiquetas)
        self.app.posiciones = [list(posicion) for posicion in self.posiciones]

        self.cerrar()
        pantalla.actualizar()

    def cancelar(self):
        self.cerrar()

    def abrir_dialogo(self, ventana):
        ventana.transient(self)
        ventana.protocol("WM_DELETE_WINDOW", lambda: self.cerrar_dialogo(ventana))

        try:
            ventana.wait_visibility()
            ventana.grab_set()
        except tk.TclError:
            pass

    def cerrar_dialogo(self, ventana):
        ventana.destroy()

        try:
            self.grab_set()
        except tk.TclError:
            pass

    def refrescar(self):
        n = self.app.n
        matriz = self.matriz
        etiquetas = self.etiquetas

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

                celda = tk.Label(self.frame_matriz, text=str(val), width=4, relief="ridge", bg=bg)
                celda.grid(row=i + 1, column=j + 1)

                if self.modo_rapido:
                    celda.config(cursor="hand2")
                    celda.bind("<Button-1>", lambda evento, f=i, c=j: self.alternar_arista(f, c))

        self.lienzo.dibujar()

    def cambiar_modo_rapido(self):
        if self.modo_rapido:
            self.modo_rapido = False
            self.btn_rapido.config(text="Modo rápido: OFF", bg="#e6e6e6")
        else:
            self.modo_rapido = True
            self.btn_rapido.config(text="Modo rápido: ON (clic en la matriz)", bg="#b3e6b3")

        self.refrescar()

    def alternar_arista(self, fila, columna):
        if self.matriz[fila][columna] == 1:
            self.matriz[fila][columna] = 0
        else:
            self.matriz[fila][columna] = 1

        self.refrescar()

    def conectar(self, origen, destino):
        nombre_origen = self.etiquetas[origen]
        nombre_destino = self.etiquetas[destino]

        if self.matriz[origen][destino] == 1:
            self.matriz[origen][destino] = 0
            self.mostrar_estado(f"Se quitó la flecha {nombre_origen}→{nombre_destino}.")
        else:
            self.matriz[origen][destino] = 1
            self.mostrar_estado(f"Se agregó la flecha {nombre_origen}→{nombre_destino}.")

        self.refrescar()

    def cambiar_modo(self):
        self.lienzo.nodo_pendiente = None

        if self.var_modo.get() == "mover":
            self.mostrar_estado(self.TEXTO_MOVER)
        else:
            self.mostrar_estado(self.TEXTO_FLECHAS)

        self.lienzo.dibujar()

    def mostrar_estado(self, texto):
        self.label_dibujo.config(text=texto)

    def editar_arista(self):
        etiquetas = self.etiquetas
        ventana = tk.Toplevel(self)
        ventana.title("Editar arista")
        ventana.geometry("300x180")

        tk.Label(ventana, text="Origen:").grid(row=0, column=0, padx=5, pady=10)
        combo_o = ttk.Combobox(ventana, values=etiquetas, width=5, state="readonly")
        combo_o.current(0)
        combo_o.grid(row=0, column=1)
        tk.Label(ventana, text="Destino:").grid(row=1, column=0, padx=5, pady=10)
        combo_d = ttk.Combobox(ventana, values=etiquetas, width=5, state="readonly")
        combo_d.current(0)
        combo_d.grid(row=1, column=1)

        def agregar():
            o = combo_o.current()
            d = combo_d.current()

            if self.matriz[o][d] == 1:
                messagebox.showinfo("Info", "Esa conexión ya existe", parent=ventana)
                return

            self.matriz[o][d] = 1
            self.refrescar()

        def quitar():
            o = combo_o.current()
            d = combo_d.current()

            if self.matriz[o][d] == 0:
                messagebox.showinfo("Info", "Esa conexión no existe", parent=ventana)
                return

            self.matriz[o][d] = 0
            self.refrescar()

        tk.Button(ventana, text="Agregar", command=agregar).grid(row=2, column=0, pady=10)
        tk.Button(ventana, text="Quitar", command=quitar).grid(row=2, column=1, pady=10)
        tk.Button(ventana, text="Cerrar", command=lambda: self.cerrar_dialogo(ventana)).grid(row=2, column=2, pady=10)

        self.abrir_dialogo(ventana)

    def nombrar_nodos(self):
        n = self.app.n
        actuales = self.etiquetas

        mayusculas = []
        for codigo in range(ord("A"), ord("Z") + 1):
            mayusculas.append(chr(codigo))

        minusculas = []
        for codigo in range(ord("a"), ord("z") + 1):
            minusculas.append(chr(codigo))

        letras_validas = mayusculas + minusculas

        estilos = ["Números", "Letras", "Prefijo + número"]
        casos = ["Mayúsculas", "Minúsculas"]

        todos_mayusculas = True
        todos_minusculas = True
        todos_numeros = True
        todos_prefijo = True
        prefijos_usados = []

        for nombre in actuales:
            if nombre not in mayusculas:
                todos_mayusculas = False

            if nombre not in minusculas:
                todos_minusculas = False

            if not (nombre.isdigit() and 1 <= int(nombre) <= 999):
                todos_numeros = False

            if len(nombre) >= 2 and nombre[0] in letras_validas and nombre[1:].isdigit() and 1 <= int(nombre[1:]) <= 99:
                prefijos_usados.append(nombre[0])
            else:
                todos_prefijo = False

        estilo_inicial = "Números"
        caso_inicial = "Mayúsculas"
        prefijo_inicial = "Q"
        conservar_nombres = True

        if todos_mayusculas:
            estilo_inicial = "Letras"
            caso_inicial = "Mayúsculas"
        elif todos_minusculas:
            estilo_inicial = "Letras"
            caso_inicial = "Minúsculas"
        elif todos_numeros:
            estilo_inicial = "Números"
        elif todos_prefijo and len(set(prefijos_usados)) == 1:
            estilo_inicial = "Prefijo + número"
            prefijo_inicial = prefijos_usados[0]
        else:
            conservar_nombres = False

        ventana = tk.Toplevel(self)
        ventana.title("Nombrar nodos")

        var_estilo = tk.StringVar(value=estilo_inicial)
        var_caso = tk.StringVar(value=caso_inicial)
        var_prefijo = tk.StringVar(value=prefijo_inicial)
        var_texto_prefijo = tk.StringVar(value="")
        var_ayuda = tk.StringVar(value="")

        def ultima_letra(texto):
            letra = ""

            for caracter in texto:
                if caracter in letras_validas:
                    letra = caracter

            return letra

        def solo_digitos(texto, maximo):
            digitos = ""

            for caracter in texto:
                if caracter in "0123456789":
                    digitos = digitos + caracter

            digitos = digitos.lstrip("0")
            return digitos[:maximo]

        def forzar_caso(texto):
            if var_caso.get() == "Mayúsculas":
                return texto.upper()
            else:
                return texto.lower()

        def actualizar_texto_prefijo():
            if var_estilo.get() == "Prefijo + número":
                var_texto_prefijo.set(var_prefijo.get())
            else:
                var_texto_prefijo.set("")

        def actualizar_ayuda():
            estilo = var_estilo.get()

            if estilo == "Números":
                texto = "Escribe un número del 1 al 999 en cada nodo."
            elif estilo == "Letras":
                texto = "Escribe una letra en cada nodo (se ajusta sola a mayúscula o minúscula)."
            else:
                texto = ("Escribe la letra del prefijo y un número del 1 al 99 en cada nodo.\n"
                         "Si algún número es 10 o más, todos quedan con 2 dígitos (Q01, Q02... Q12).")

            texto = texto + "\nCon \"Rellenar\" se completan los demás nodos a partir del primero."
            var_ayuda.set(texto)

        def filtrar_valor(*args, v=None):
            texto = v.get()
            estilo = var_estilo.get()

            if estilo == "Letras":
                nuevo = forzar_caso(ultima_letra(texto))
            elif estilo == "Números":
                nuevo = solo_digitos(texto, 3)
            else:
                nuevo = solo_digitos(texto, 2)

            if nuevo != texto:
                v.set(nuevo)

        def filtrar_prefijo(*args):
            texto = var_prefijo.get()
            nuevo = ultima_letra(texto)

            if nuevo != texto:
                var_prefijo.set(nuevo)
            else:
                actualizar_texto_prefijo()

        def al_teclear_en_nodo(evento, v=None):
            caracter = evento.char

            if caracter != "" and caracter in letras_validas:
                if var_estilo.get() == "Letras":
                    v.set(forzar_caso(caracter))

                return "break"

        def al_teclear_en_prefijo(evento):
            caracter = evento.char

            if caracter != "" and caracter in letras_validas:
                var_prefijo.set(caracter)
                return "break"

        var_prefijo.trace_add("write", filtrar_prefijo)

        tk.Label(ventana, text="Elige un estilo de nombres (el mismo para todos los nodos):",
                 font=("Arial", 10)).pack(padx=15, pady=(12, 5))

        frame_estilo = tk.Frame(ventana)
        frame_estilo.pack(pady=5)

        tk.Label(frame_estilo, text="Estilo:").grid(row=0, column=0, padx=(5, 3), pady=3, sticky="e")
        combo_estilo = ttk.Combobox(frame_estilo, textvariable=var_estilo, values=estilos, width=16, state="readonly")
        combo_estilo.grid(row=0, column=1, padx=(0, 10), pady=3)

        tk.Label(frame_estilo, text="Letras en:").grid(row=1, column=0, padx=(5, 3), pady=3, sticky="e")
        combo_caso = ttk.Combobox(frame_estilo, textvariable=var_caso, values=casos, width=16, state="readonly")
        combo_caso.grid(row=1, column=1, padx=(0, 10), pady=3)

        tk.Label(frame_estilo, text="Prefijo:").grid(row=0, column=2, padx=(5, 3), pady=3, sticky="e")
        entry_prefijo = ttk.Entry(frame_estilo, textvariable=var_prefijo, width=4, justify="center")
        entry_prefijo.grid(row=0, column=3, padx=(0, 5), pady=3)
        entry_prefijo.bind("<KeyPress>", al_teclear_en_prefijo)

        tk.Label(ventana, textvariable=var_ayuda, font=("Arial", 9), fg="gray20",
                 wraplength=420, justify="center").pack(padx=15, pady=(0, 3))

        frame = tk.Frame(ventana)
        frame.pack(padx=10, pady=8)

        variables_valor = []

        for i in range(n):
            var_valor = tk.StringVar(value="")
            var_valor.trace_add("write", lambda *args, v=var_valor: filtrar_valor(v=v))
            variables_valor.append(var_valor)

            fila = i % 6
            columna = (i // 6) * 3

            tk.Label(frame, text=f"Nodo {i + 1}:").grid(row=fila, column=columna, padx=(10, 3), pady=4, sticky="e")
            tk.Label(frame, textvariable=var_texto_prefijo, width=2, anchor="e").grid(row=fila, column=columna + 1)

            entry_valor = ttk.Entry(frame, textvariable=var_valor, width=5, justify="center")
            entry_valor.grid(row=fila, column=columna + 2, padx=(0, 10))
            entry_valor.bind("<KeyPress>", lambda evento, v=var_valor: al_teclear_en_nodo(evento, v=v))

        def valor_por_defecto(posicion):
            estilo = var_estilo.get()

            if estilo == "Letras":
                if var_caso.get() == "Mayúsculas":
                    return chr(65 + posicion)
                else:
                    return chr(97 + posicion)
            else:
                return str(posicion + 1)

        def activar_opciones_del_estilo():
            estilo = var_estilo.get()

            if estilo == "Letras":
                combo_caso.config(state="readonly")
            else:
                combo_caso.config(state="disabled")

            if estilo == "Prefijo + número":
                entry_prefijo.config(state="normal")
            else:
                entry_prefijo.config(state="disabled")

        def aplicar_por_defecto(evento=None):
            activar_opciones_del_estilo()

            if var_estilo.get() == "Prefijo + número" and var_prefijo.get() == "":
                var_prefijo.set("Q")

            for i in range(n):
                variables_valor[i].set(valor_por_defecto(i))

            actualizar_texto_prefijo()
            actualizar_ayuda()

        def cambiar_caso(evento=None):
            for i in range(n):
                variables_valor[i].set(forzar_caso(variables_valor[i].get()))

        if conservar_nombres:
            activar_opciones_del_estilo()

            for i in range(n):
                if estilo_inicial == "Prefijo + número":
                    variables_valor[i].set(actuales[i][1:])
                else:
                    variables_valor[i].set(actuales[i])

            actualizar_texto_prefijo()
            actualizar_ayuda()
        else:
            aplicar_por_defecto()

        combo_estilo.bind("<<ComboboxSelected>>", aplicar_por_defecto)
        combo_caso.bind("<<ComboboxSelected>>", cambiar_caso)

        def rellenar():
            estilo = var_estilo.get()
            texto = variables_valor[0].get().strip()

            if texto == "":
                messagebox.showerror("Error", "Escribe primero el valor del nodo 1", parent=ventana)
                return

            if estilo == "Letras":
                letra = forzar_caso(texto)
                inicio = ord(letra)

                if var_caso.get() == "Mayúsculas":
                    ultima_permitida = ord("Z")
                else:
                    ultima_permitida = ord("z")

                if inicio + n - 1 > ultima_permitida:
                    ultima_para_empezar = chr(ultima_permitida - n + 1)
                    primera_que_no_alcanza = chr(ultima_permitida - n + 2)

                    messagebox.showerror(
                        "Error",
                        f"Desde la letra {primera_que_no_alcanza} no alcanza para {n} nodos.\n"
                        f"La última letra desde la que se puede empezar es {ultima_para_empezar}.",
                        parent=ventana
                    )
                    return

                for i in range(n):
                    variables_valor[i].set(chr(inicio + i))
            else:
                inicio = int(texto)

                if estilo == "Números":
                    maximo = 999
                else:
                    maximo = 99

                if inicio + n - 1 > maximo:
                    ultimo_para_empezar = maximo - n + 1
                    primero_que_no_alcanza = maximo - n + 2

                    messagebox.showerror(
                        "Error",
                        f"Desde el número {primero_que_no_alcanza} no alcanza para {n} nodos.\n"
                        f"El último número desde el que se puede empezar es {ultimo_para_empezar}.",
                        parent=ventana
                    )
                    return

                for i in range(n):
                    variables_valor[i].set(str(inicio + i))

        def aceptar():
            estilo = var_estilo.get()
            prefijo = var_prefijo.get()
            nombres = []

            if estilo == "Prefijo + número" and prefijo == "":
                messagebox.showerror("Error", "Escribe la letra del prefijo", parent=ventana)
                return

            numeros_prefijo = []

            for i in range(n):
                texto = variables_valor[i].get().strip()

                if texto == "":
                    messagebox.showerror("Error", f"El nodo {i + 1} no tiene valor", parent=ventana)
                    return

                if estilo == "Letras":
                    nombres.append(forzar_caso(texto))
                elif estilo == "Números":
                    nombres.append(str(int(texto)))
                else:
                    numeros_prefijo.append(int(texto))

            if estilo == "Prefijo + número":
                if max(numeros_prefijo) >= 10:
                    cantidad_digitos = 2
                else:
                    cantidad_digitos = 1

                for numero in numeros_prefijo:
                    nombres.append(prefijo + str(numero).zfill(cantidad_digitos))

            if len(set(nombres)) < n:
                messagebox.showerror("Error", "No puede haber dos nodos con el mismo nombre", parent=ventana)
                return

            self.etiquetas = nombres
            self.refrescar()
            self.cerrar_dialogo(ventana)

        frame_botones = tk.Frame(ventana)
        frame_botones.pack(pady=(5, 12))
        tk.Button(frame_botones, text="Por defecto", command=aplicar_por_defecto).grid(row=0, column=0, padx=5)
        tk.Button(frame_botones, text="Rellenar", command=rellenar).grid(row=0, column=1, padx=5)
        tk.Button(frame_botones, text="Aceptar", command=aceptar, bg="#b3e6b3").grid(row=0, column=2, padx=5)
        tk.Button(frame_botones, text="Cancelar", command=lambda: self.cerrar_dialogo(ventana)).grid(row=0, column=3, padx=5)

        self.abrir_dialogo(ventana)


# Manual de usuario

def contenido_manual():
    secciones = []

    secciones.append(("1. Inicio rápido", """## ¿Para qué sirve este programa?
Calcula las componentes conexas de un grafo dirigido con el procedimiento matricial de la clase (matriz de adyacencia, matriz de caminos, orden de filas y columnas, bloques de 1's) y te muestra cada paso.

## Pasos básicos
1. En la pantalla de bienvenida elige Aleatorio o Manual, escribe la cantidad de nodos (de 4 a 12) y presiona Iniciar (o usa "Cargar desde QR").
2. En la pantalla de la matriz revisa las conexiones o arma el grafo con el botón "Editar Matriz o Gráfico" (puedes cambiar los 1 y 0 o dibujar las flechas entre los nodos).
3. Mira el "Resultado final" (las componentes conexas encontradas) y presiona "Graficar componentes conexas" para ver el grafo.
4. Presiona "Ver procedimiento paso a paso" para ver cómo se llegó al resultado.
5. Presiona "Generar informe" para ver y guardar un PDF con la solución completa.
6. Guarda el ejercicio con "Guardar ejercicio" para abrirlo más tarde o usa "Compartir por QR" para enviárselo a otra persona.

## Atajo
Presiona la tecla F1 en cualquier momento para abrir este manual."""))

    secciones.append(("2. Pantalla de bienvenida", """## Cómo generar el grafo
- Aleatorio: el programa crea conexiones al azar entre los nodos.
- Manual: empiezas con la matriz vacía y tú pones las conexiones.

## Cantidad de nodos
Debe estar entre 4 y 12. Si pones otro valor, el programa avisa.

## Botones
- Iniciar: crea el grafo y abre la pantalla de la matriz.
- Cargar desde QR: lee un archivo de imagen PNG o JPG que contenga un código QR de la aplicación y carga el ejercicio automáticamente.
- Ejercicios guardados: abre la lista de ejercicios que guardaste antes para cargar uno directamente.
- Manual de usuario: abre esta ayuda."""))

    secciones.append(("3. Pantalla de la matriz", """## La tabla
Es la matriz de adyacencia. La fila es el ORIGEN y la columna es el DESTINO. Un 1 (verde) en la fila A y la columna B significa que hay una flecha de A hacia B. El grafo es dirigido: A→B no significa que exista B→A.

## El grafo original
A la derecha de la matriz se ve el grafo original, con todos los nodos del mismo color (así no se adelanta el resultado). Se actualiza solo cada vez que cambias la matriz y respeta la posición que le hayas dado a cada nodo.

## Botones
- Editar Matriz o Gráfico / Revertir (Fila 1): abre la ventana para modificar el grafo o borra todas las conexiones dejando la matriz vacía.
- Graficar componentes conexas / Ver procedimiento paso a paso (Fila 2): muestra el grafo reorganizado por componentes conexas o despliega el cálculo matricial etapa por etapa.
- Guardar ejercicio / Ejercicios guardados (Fila 3): guarda el ejercicio actual o abre la lista de ejercicios guardados previamente.
- Compartir por QR / Generar informe (Fila 4): genera la imagen QR para compartir el grafo o arma el informe PDF completo.
- < Atras (arriba a la izquierda): vuelve a la pantalla de bienvenida para elegir otro modo o cantidad de nodos y crear un grafo nuevo con Iniciar. El grafo actual se reemplaza, así que guárdalo antes con "Guardar ejercicio" si quieres conservarlo.

## Resultado final
Se actualiza solo cada vez que cambia la matriz. Muestra cuántas componentes hay, si el grafo es conexo (Sí/No), cuántas aristas tiene y qué nodos forman cada componente.

## Análisis de nodo
Elige un nodo en la lista y presiona Analizar: muestra a qué nodos llega directamente (por ejemplo A->B, A->C)."""))

    secciones.append(("4. Compartir por Código QR", """## Intercambio de ejercicios sin conexión
Esta función te permite transferir ejercicios completos entre dispositivos de forma 100% offline sin necesidad de servidores ni conexión a internet.

## Generar y enviar un QR
1. Presiona "Compartir por QR" en la pantalla de la matriz.
2. Haz clic en el botón "Descargar QR (.png)" dentro de la ventana emergente y guarda la imagen en tu equipo.
3. Envía la imagen PNG a un compañero por mensaje, correo o red social.

## Cargar un ejercicio desde un QR
1. En la pantalla de bienvenida de la aplicación, presiona el botón "Cargar desde QR".
2. Selecciona la imagen PNG o JPG que te enviaron.
3. El programa decodificará la estructura de forma instantánea y cargará la matriz, nombres de nodos y posiciones exactas."""))

    secciones.append(("5. Editar Matriz o Gráfico", """Con el botón "Editar Matriz o Gráfico" se abre una ventana con una copia de la matriz y del grafo original, lado a lado.

## Aceptar y Cancelar
Los cambios solo se aplican al grafo cuando presionas Aceptar. Con Cancelar (o cerrando la ventana con la X) se descartan todos y el grafo queda como estaba. Mientras esta ventana está abierta no se puede usar la pantalla de atrás.

## Editar arista
Elige el Origen y el Destino en las listas y presiona Agregar o Quitar. Si la conexión ya existe (o no existe) el programa avisa. También puedes poner un nodo hacia sí mismo: aparece como 1 en la diagonal de la matriz, pero no se dibuja flecha en el gráfico.

## Dibujar flechas y mover nodos en el gráfico
Debajo del gráfico hay dos modos:
- Dibujar flechas: arrastra con el mouse desde el nodo origen hasta el nodo destino (o haz clic en el origen y después en el destino). La matriz se actualiza sola. Si repites una flecha que ya existe, se quita. Debajo del gráfico se avisa qué flecha se agregó o se quitó.
- Mover nodos: arrastra un nodo para acomodarlo donde quieras y formar la figura que prefieras. Las posiciones se conservan al presionar Aceptar y se guardan junto con el ejercicio.
Mientras editas, los nodos no cambian de color: las componentes se muestran recién al final.

## Modo rápido
Presiona el botón para activarlo (queda en ON). Mientras esté activo, un clic en cualquier celda de la matriz cambia 0 por 1 o 1 por 0. Vuelve a presionarlo para desactivarlo.

## Nombrar nodos
Abre la ventana para ponerle nombre a los nodos (ver la sección siguiente)."""))

    secciones.append(("6. Nombrar nodos", """## Un solo estilo para todos
Primero eliges UN estilo que se aplica a todos los nodos:
- Números: del 1 al 999.
- Letras: mayúsculas o minúsculas (la opción "Letras en" decide cuál; no se pueden mezclar).
- Prefijo + número: una letra de prefijo igual para todos y un número del 1 al 99 por nodo (por ejemplo Q1, Q2, Q3).

## Cómo escribir
Cada nodo tiene un campo para escribir.
- Números: solo acepta dígitos (máximo 3 y sin cero al inicio).
- Letras: solo acepta una letra. Si escribes "v" y está en Mayúsculas, se convierte en "V".
- Prefijo + número: escribes la letra del prefijo (si pones "q" minúscula, todos quedan con q) y el número de cada nodo.

## Regla de los dígitos
Si algún número del prefijo es 10 o más, todos quedan con 2 dígitos para que haya orden: Q01, Q02, ..., Q12. Si ninguno llega a 10, quedan Q1, Q2, Q3...

## Botones
- Por defecto: deja nombres consecutivos (A, B, C... / 1, 2, 3... / Q1, Q2...).
- Rellenar: completa los demás nodos a partir del primero (si el primero es 10 quedan 10, 11, 12...; si es "c" quedan c, d, e...). Si ya no alcanzan los valores (por ejemplo empezando en Z), avisa.
- Aceptar: valida que no haya campos vacíos ni nombres repetidos.
- Cancelar: cierra sin cambiar nada.

Los nombres se usan en todo el programa: matriz, resultado, gráficos, pasos e informe. Recuerda presionar Aceptar también en la ventana "Editar Matriz o Gráfico" para que queden guardados."""))

    secciones.append(("7. Graficar componentes conexas", """El grafo original se ve siempre junto a la matriz. El botón "Graficar componentes conexas" muestra el resultado final: el grafo de las componentes conexas.

Cada componente aparece separada de las demás, con su propio color, y solo se dibujan las flechas que están dentro de cada una.

Una conexión de un nodo hacia sí mismo no se dibuja."""))

    secciones.append(("8. Procedimiento paso a paso", """Se abre con "Ver procedimiento paso a paso". Muestra cómo cambia la matriz en cada etapa.

## Etapas
1. Paso 1: matriz de adyacencia con 1's en la diagonal (los 1's agregados se ven en azul).
2. Paso 2: matriz de caminos. Se multiplica la matriz por sí misma (producto booleano) y se obtiene M^2, luego M^3, y así hasta que ya no aparezcan 1's nuevos. Los 1's nuevos salen en naranja y debajo se explica por qué nodo se pasa (por ejemplo 4→2 (por 1)).
3. Matriz de caminos: es el resultado del Paso 2, con la lista de nodos a los que llega cada nodo.
4. Paso 3: se ordenan las filas por la cantidad de 1's, de mayor a menor. Si hay empate, va primero la fila cuyo primer 1 está más cerca de la primera columna.
5. Paso 4: se ordenan las columnas igual que las filas. Los bloques cuadrados de 1's marcados en rojo son las componentes conexas.
6. Resultado: la lista de componentes.

## Botones
- Anterior / Siguiente: avanzar o retroceder una etapa.
- Reproducir: avanza solo de etapa en etapa y se detiene en el resultado. Se convierte en Pausar. Si lo presionas al final, vuelve a empezar.
- Velocidad: Lenta, Normal o Rápida.
- Si usas Anterior o Siguiente mientras reproduce, la reproducción se pausa.

## Colores
Verde = 1, blanco = 0, naranja = 1 nuevo, azul = 1 agregado en la diagonal, borde rojo = bloque de una componente."""))

    secciones.append(("9. Informe en PDF", """El botón "Generar informe" arma el informe y abre una vista previa antes de guardarlo.

## En la vista previa
- Anterior / Siguiente (o las flechas del teclado) cambian de hoja.
- Alejar / Acercar cambian el tamaño; con la rueda del mouse y las barras te desplazas.
- Guardar PDF te deja elegir dónde guardar el archivo.

## Estructura del informe (razonamiento cuantitativo)
1. Interpretación: de qué trata el problema, qué se pide, qué datos se tienen y qué se utilizará.
2. Representación: las variables, las restricciones de los datos, la matriz de adyacencia y el gráfico del grafo.
3. Cálculo: la resolución, con los Pasos 1 a 4 (incluye cada potencia M^2, M^3... y los 1's nuevos).
4. Análisis: la respuesta a la pregunta (las componentes conexas y si el grafo es conexo), la conclusión final y el gráfico de las componentes.

Cada hoja tiene una franja de color arriba que indica la sección."""))

    secciones.append(("10. Ejercicios guardados", """## Guardar
"Guardar ejercicio" te pide un nombre y guarda el grafo automáticamente (la matriz, los nombres y la posición de los nodos). Si ya existe un ejercicio con ese nombre, pregunta si quieres reemplazarlo. Se guardan en la carpeta "ejercicios_guardados", junto al programa.

## Ver, cargar y eliminar
"Ejercicios guardados" (en la bienvenida o en la pantalla de la matriz) muestra la lista con nombre, nodos, aristas y fecha, del más nuevo al más antiguo.
- Cargar (o doble clic): abre el ejercicio. Si ya había un grafo en pantalla, avisa que se reemplazará.
- Eliminar: lo borra de la lista y de la carpeta, después de pedir confirmación.

## Ejemplos
La primera vez que se crea la carpeta, trae dos ejercicios del PDF de la clase: "Ejemplo 1 del PDF" y "Práctica 1 del PDF (A-E)". Se pueden eliminar.

## Pasar un ejercicio a otra computadora
Copia el archivo .json de la carpeta "ejercicios_guardados" a la misma carpeta del otro programa, o utiliza el sistema de código QR para transferirlo visualmente."""))

    secciones.append(("11. Conceptos del tema", """## Grafo dirigido
Es un conjunto de nodos unidos por flechas. Cada flecha va de un nodo origen a un nodo destino.

## Grafo conexo
Un grafo es conexo si para cualquier par de vértices existe un camino entre ellos.

## Componentes conexas
Son los subgrafos conexos disjuntos (sin vértices en común) con el mayor número de vértices que se pueden formar a partir del grafo original.

## Matriz de adyacencia
Tiene un 1 en la fila i y la columna j si existe la arista de i hacia j, y 0 si no existe.

## Matriz de caminos
Indica si desde un nodo se puede llegar a otro siguiendo las flechas, sin importar cuántos pasos tome. Se obtiene multiplicando la matriz de adyacencia por sí misma hasta que ya no cambia.

## ¿Por qué se pone 1 en la diagonal?
Porque todo nodo llega a sí mismo. Además, así cada potencia incluye los caminos más cortos y la matriz crece ordenadamente hasta estabilizarse.

## ¿Cómo se forman las componentes?
Dos nodos están en la misma componente si se alcanzan mutuamente (de uno al otro y de vuelta). Al ordenar filas y columnas, esos nodos forman bloques cuadrados diagonales de 1's."""))

    secciones.append(("12. Preguntas frecuentes", """## Edité la matriz pero no cambió nada
Falta presionar Aceptar en la ventana "Editar Matriz o Gráfico". Con Cancelar o con la X los cambios se descartan.

## Dice "Conexo: No"
El grafo tiene más de una componente conexa. Mira el Resultado final o el Análisis del informe para ver cuáles son.

## No me deja guardar los nombres de los nodos
Revisa que no haya campos vacíos ni nombres repetidos. Los nombres tienen como máximo 3 caracteres.

## ¿Dónde quedan mis ejercicios?
En la carpeta "ejercicios_guardados" junto al programa. Se ven en el botón "Ejercicios guardados".

## ¿Cómo transfiero mi ejercicio a un amigo?
Usa el botón "Compartir por QR", guarda la imagen con "Descargar QR (.png)" y envíasela. Tu amigo solo debe presionar "Cargar desde QR" en su aplicación.

## La vista previa del informe se ve muy pequeña
Usa el botón Acercar y desplázate con la rueda del mouse o las barras.

## El gráfico no muestra una flecha de un nodo hacia sí mismo
Es normal: esa conexión aparece en la matriz (1 en la diagonal) pero no se dibuja."""))

    return secciones


class VentanaManual(tk.Toplevel):

    def __init__(self, parent, app):
        super().__init__(parent)
        self.title("Manual de usuario")
        self.geometry("820x560")
        self.app = app
        self.secciones = contenido_manual()

        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.app.ventana_manual = self

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.lista = tk.Listbox(self, width=28, font=("Arial", 10), exportselection=False, activestyle="none")
        self.lista.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)

        for titulo, texto in self.secciones:
            self.lista.insert("end", titulo)

        self.lista.bind("<<ListboxSelect>>", self.al_elegir)

        frame_texto = tk.Frame(self)
        frame_texto.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        frame_texto.grid_rowconfigure(0, weight=1)
        frame_texto.grid_columnconfigure(0, weight=1)

        self.texto = tk.Text(frame_texto, wrap="word", font=("Arial", 10), padx=14, pady=10,
                             spacing3=3, state="disabled")
        self.texto.grid(row=0, column=0, sticky="nsew")

        barra = tk.Scrollbar(frame_texto, orient="vertical", command=self.texto.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self.texto.config(yscrollcommand=barra.set)

        self.texto.tag_configure("titulo", font=("Arial", 15, "bold"), foreground="#1a3d6b", spacing3=8)
        self.texto.tag_configure("subtitulo", font=("Arial", 11, "bold"), foreground="#2f6db5", spacing1=8)

        self.lista.selection_set(0)
        self.mostrar_seccion(0)

    def al_elegir(self, evento=None):
        seleccion = self.lista.curselection()

        if len(seleccion) > 0:
            self.mostrar_seccion(seleccion[0])

    def mostrar_seccion(self, posicion):
        titulo, contenido = self.secciones[posicion]

        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("end", titulo + "\n", "titulo")

        for linea in contenido.split("\n"):
            if linea.startswith("## "):
                self.texto.insert("end", linea[3:] + "\n", "subtitulo")
            else:
                self.texto.insert("end", linea + "\n")

        self.texto.config(state="disabled")
        self.texto.yview_moveto(0)

    def cerrar(self):
        self.app.ventana_manual = None
        self.destroy()


# Ventana de ejercicios guardados

class VentanaEjercicios(tk.Toplevel):

    def __init__(self, parent, app, confirmar=False):
        super().__init__(parent)
        self.title("Ejercicios guardados")
        self.geometry("580x440")

        self.app = app
        self.confirmar = confirmar
        self.ejercicios = []

        tk.Label(self, text="Ejercicios guardados", font=("Arial", 14, "bold")).pack(pady=(12, 2))
        tk.Label(self, text="Elige uno para cargarlo o eliminarlo. También puedes hacer doble clic para cargarlo.",
                 font=("Arial", 9), fg="gray20").pack()

        frame_lista = tk.Frame(self)
        frame_lista.pack(fill="both", expand=True, padx=15, pady=8)

        self.arbol = ttk.Treeview(frame_lista, columns=("nombre", "nodos", "aristas", "guardado"),
                                  show="headings", selectmode="browse")
        self.arbol.heading("nombre", text="Nombre")
        self.arbol.heading("nodos", text="Nodos")
        self.arbol.heading("aristas", text="Aristas")
        self.arbol.heading("guardado", text="Guardado")
        self.arbol.column("nombre", width=230)
        self.arbol.column("nodos", width=60, anchor="center")
        self.arbol.column("aristas", width=60, anchor="center")
        self.arbol.column("guardado", width=130, anchor="center")

        barra = ttk.Scrollbar(frame_lista, orient="vertical", command=self.arbol.yview)
        self.arbol.config(yscrollcommand=barra.set)
        self.arbol.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        self.arbol.bind("<<TreeviewSelect>>", self.al_seleccionar)
        self.arbol.bind("<Double-1>", lambda evento: self.cargar())

        self.label_detalle = tk.Label(self, text="", font=("Arial", 9), fg="gray20",
                                      wraplength=540, justify="left")
        self.label_detalle.pack(padx=15, pady=(0, 5), anchor="w")

        frame_botones = tk.Frame(self)
        frame_botones.pack(pady=(5, 12))

        self.btn_cargar = tk.Button(frame_botones, text="Cargar", command=self.cargar, bg="#b3e6b3", width=12)
        self.btn_cargar.grid(row=0, column=0, padx=8)
        self.btn_eliminar = tk.Button(frame_botones, text="Eliminar", command=self.eliminar, bg="#ffb3b3", width=12)
        self.btn_eliminar.grid(row=0, column=1, padx=8)
        tk.Button(frame_botones, text="Cerrar", command=self.destroy, width=12).grid(row=0, column=2, padx=8)

        self.refrescar()

    def ejercicio_elegido(self):
        seleccion = self.arbol.selection()

        if len(seleccion) == 0:
            return None

        posicion = int(seleccion[0])

        if posicion >= len(self.ejercicios):
            return None

        return self.ejercicios[posicion]

    def refrescar(self):
        self.ejercicios = listar_ejercicios()

        for fila in self.arbol.get_children():
            self.arbol.delete(fila)

        for posicion, ejercicio in enumerate(self.ejercicios):
            self.arbol.insert("", "end", iid=str(posicion), values=(
                ejercicio["nombre"], len(ejercicio["etiquetas"]), ejercicio["aristas"], ejercicio["guardado"]
            ))

        self.btn_cargar.config(state="disabled")
        self.btn_eliminar.config(state="disabled")

        if len(self.ejercicios) == 0:
            self.label_detalle.config(
                text="Todavía no hay ejercicios guardados. Usa \"Guardar ejercicio\" en la pantalla de la matriz."
            )
        else:
            self.label_detalle.config(text="")

    def al_seleccionar(self, evento=None):
        ejercicio = self.ejercicio_elegido()

        if ejercicio is None:
            self.btn_cargar.config(state="disabled")
            self.btn_eliminar.config(state="disabled")
            return

        self.btn_cargar.config(state="normal")
        self.btn_eliminar.config(state="normal")
        self.label_detalle.config(
            text=f"Nodos: {', '.join(ejercicio['etiquetas'])}\n"
                 f"Archivo: {os.path.basename(ejercicio['archivo'])}"
        )

    def cargar(self):
        ejercicio = self.ejercicio_elegido()

        if ejercicio is None:
            return

        if self.confirmar:
            respuesta = messagebox.askyesno(
                "Cargar ejercicio",
                f"Esto reemplazará el grafo actual por «{ejercicio['nombre']}».\n¿Deseas continuar?",
                parent=self
            )

            if not respuesta:
                return

        self.destroy()
        self.app.aplicar_grafo(ejercicio["nombre"], ejercicio["etiquetas"], ejercicio["matriz"],
                               ejercicio["posiciones"])

    def eliminar(self):
        ejercicio = self.ejercicio_elegido()

        if ejercicio is None:
            return

        respuesta = messagebox.askyesno(
            "Eliminar ejercicio",
            f"¿Eliminar «{ejercicio['nombre']}»?\nEsta acción no se puede deshacer.",
            parent=self
        )

        if not respuesta:
            return

        try:
            os.remove(ejercicio["archivo"])
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo eliminar el ejercicio:\n{error}", parent=self)
            return

        self.refrescar()


# Vista previa del informe

class VentanaVistaPrevia(tk.Toplevel):

    def __init__(self, parent, paginas):
        super().__init__(parent)
        self.title("Vista previa del informe")

        self.paginas = paginas
        self.pagina_actual = 0
        self.canvas_hoja = None

        alto_pantalla = self.winfo_screenheight()
        ancho_pantalla = self.winfo_screenwidth()

        self.dpi = int((alto_pantalla - 260) / ALTO_A4)

        if self.dpi > 80:
            self.dpi = 80

        if self.dpi < 45:
            self.dpi = 45

        ancho = int(ANCHO_A4 * self.dpi) + 60
        alto = alto_pantalla - 100

        if ancho > ancho_pantalla - 100:
            ancho = ancho_pantalla - 100

        self.geometry(f"{ancho}x{alto}")

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label_titulo = tk.Label(self, text="", font=("Arial", 11, "bold"))
        self.label_titulo.grid(row=0, column=0, columnspan=2, pady=(8, 2))

        self.zona = tk.Canvas(self, highlightthickness=0, bg="#8c8c8c")
        self.zona.grid(row=1, column=0, sticky="nsew")

        barra_vertical = tk.Scrollbar(self, orient="vertical", command=self.zona.yview)
        barra_vertical.grid(row=1, column=1, sticky="ns")
        barra_horizontal = tk.Scrollbar(self, orient="horizontal", command=self.zona.xview)
        barra_horizontal.grid(row=2, column=0, sticky="ew")
        self.zona.config(yscrollcommand=barra_vertical.set, xscrollcommand=barra_horizontal.set)

        self.frame_hoja = tk.Frame(self.zona)
        self.zona.create_window((0, 0), window=self.frame_hoja, anchor="nw")

        frame_botones = tk.Frame(self)
        frame_botones.grid(row=3, column=0, columnspan=2, pady=8)

        self.btn_anterior = tk.Button(frame_botones, text="< Anterior", command=self.anterior, width=10)
        self.btn_anterior.grid(row=0, column=0, padx=5)
        self.label_pagina = tk.Label(frame_botones, text="", font=("Arial", 10, "bold"), width=16)
        self.label_pagina.grid(row=0, column=1, padx=5)
        self.btn_siguiente = tk.Button(frame_botones, text="Siguiente >", command=self.siguiente, width=10)
        self.btn_siguiente.grid(row=0, column=2, padx=5)

        tk.Button(frame_botones, text="Alejar", command=lambda: self.cambiar_zoom(-15), width=8).grid(
            row=0, column=3, padx=(20, 3))
        tk.Button(frame_botones, text="Acercar", command=lambda: self.cambiar_zoom(15), width=8).grid(
            row=0, column=4, padx=3)

        tk.Button(frame_botones, text="Guardar PDF", command=self.guardar, bg="#b3e6b3", width=12).grid(
            row=0, column=5, padx=(20, 5))
        tk.Button(frame_botones, text="Cerrar", command=self.destroy, width=8).grid(row=0, column=6, padx=5)

        self.bind("<Left>", lambda evento: self.anterior())
        self.bind("<Right>", lambda evento: self.siguiente())
        self.bind("<MouseWheel>", lambda evento: self.zona.yview_scroll(int(-evento.delta / 120), "units"))

        self.mostrar_pagina()

    def mostrar_pagina(self):
        titulo, fig = self.paginas[self.pagina_actual]
        total = len(self.paginas)

        self.label_titulo.config(text=titulo)
        self.label_pagina.config(text=f"Hoja {self.pagina_actual + 1} de {total}")

        if self.pagina_actual > 0:
            self.btn_anterior.config(state="normal")
        else:
            self.btn_anterior.config(state="disabled")

        if self.pagina_actual < total - 1:
            self.btn_siguiente.config(state="normal")
        else:
            self.btn_siguiente.config(state="disabled")

        for w in self.frame_hoja.winfo_children():
            w.destroy()

        fig.set_dpi(self.dpi)
        self.canvas_hoja = FigureCanvasTkAgg(fig, master=self.frame_hoja)
        self.canvas_hoja.draw()
        self.canvas_hoja.get_tk_widget().pack()

        self.frame_hoja.update_idletasks()
        self.zona.config(scrollregion=self.zona.bbox("all"))
        self.zona.xview_moveto(0)
        self.zona.yview_moveto(0)

    def cambiar_zoom(self, cambio):
        self.dpi = self.dpi + cambio

        if self.dpi < 30:
            self.dpi = 30

        if self.dpi > 160:
            self.dpi = 160

        self.mostrar_pagina()

    def anterior(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.mostrar_pagina()

    def siguiente(self):
        if self.pagina_actual < len(self.paginas) - 1:
            self.pagina_actual += 1
            self.mostrar_pagina()

    def guardar(self):
        ruta = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar informe",
            defaultextension=".pdf",
            filetypes=[("Archivo PDF", "*.pdf")],
            initialfile="informe_componentes_conexas.pdf"
        )

        if not ruta:
            return

        try:
            guardar_informe_pdf(ruta, self.paginas)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo guardar el informe:\n{error}", parent=self)
            return

        messagebox.showinfo("Informe", f"El informe se guardó en:\n{ruta}", parent=self)


# Procedimiento paso a paso

class VentanaPasos(tk.Toplevel):

    VELOCIDADES = {"Lenta": 3000, "Normal": 1500, "Rápida": 700}

    def __init__(self, parent, matriz, etiquetas):
        super().__init__(parent)
        self.title("Procedimiento: Componentes conexas")

        self.matriz = matriz
        self.etiquetas = etiquetas
        self.n = len(matriz)
        self.paso_actual = 0

        self.reproduciendo = False
        self.tarea = None

        self.geometry(f"640x{450 + 26 * self.n}")
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

        self._calcular_pasos()

        self.label_titulo = tk.Label(self, text="", font=("Arial", 13, "bold"))
        self.label_titulo.pack(pady=(12, 0))

        self.label_descripcion = tk.Label(
            self, text="", font=("Arial", 9), fg="gray20",
            wraplength=580, justify="center"
        )
        self.label_descripcion.pack(pady=(2, 10))

        self.frame_tabla = tk.Frame(self)
        self.frame_tabla.pack(pady=5)

        self.label_extra = tk.Label(
            self, text="", font=("Arial", 9), fg="gray20",
            wraplength=580, justify="left"
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

        frame_auto = tk.Frame(self)
        frame_auto.pack(pady=(0, 10))

        self.btn_reproducir = tk.Button(frame_auto, text="Reproducir", command=self.alternar_reproduccion,
                                        width=12, bg="#c7f0d8")
        self.btn_reproducir.grid(row=0, column=0, padx=10)

        tk.Label(frame_auto, text="Velocidad:").grid(row=0, column=1)
        self.var_velocidad = tk.StringVar(value="Normal")
        ttk.Combobox(frame_auto, textvariable=self.var_velocidad, values=list(self.VELOCIDADES.keys()),
                     width=8, state="readonly").grid(row=0, column=2, padx=5)

        self.mostrar_paso()

    def _calcular_pasos(self):
        datos = calcular_procedimiento(self.matriz)

        self.M1 = datos["M1"]
        self.iteraciones = datos["iteraciones"]
        self.R = datos["R"]
        self.orden = datos["orden"]
        self.R_filas = datos["R_filas"]
        self.R_final = datos["R_final"]
        self.componentes = datos["componentes"]
        self.bloques = datos["bloques"]

        self.diagonal = set()
        for i in range(self.n):
            if self.matriz[i][i] == 0:
                self.diagonal.add((i, i))

        self.pantallas = [("paso1", None)]

        for posicion in range(len(self.iteraciones)):
            self.pantallas.append(("potencia", posicion))

        self.pantallas.append(("caminos", None))
        self.pantallas.append(("filas", None))
        self.pantallas.append(("columnas", None))
        self.pantallas.append(("resultado", None))

    def _pintar_matriz(self, M, etiquetas_filas, etiquetas_columnas, resaltar=None,
                       nuevos=None, diagonal=None):
        for w in self.frame_tabla.winfo_children():
            w.destroy()

        resaltar = resaltar or set()
        nuevos = nuevos or set()
        diagonal = diagonal or set()

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

                if (i, j) in nuevos:
                    bg = "#ffb84d"
                elif (i, j) in diagonal:
                    bg = "#9ecbff"
                elif val == 1:
                    bg = "lightgreen"
                else:
                    bg = "white"

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
        tipo, indice = self.pantallas[self.paso_actual]
        total = len(self.pantallas)

        if self.paso_actual > 0:
            self.btn_anterior.config(state="normal")
        else:
            self.btn_anterior.config(state="disabled")

        if self.paso_actual < total - 1:
            self.btn_siguiente.config(state="normal")
        else:
            self.btn_siguiente.config(state="disabled")

        self.label_paso.config(text=f"Etapa {self.paso_actual + 1} de {total}")
        self.label_extra.config(text="")

        if tipo == "paso1":
            self.label_titulo.config(text="Paso 1: Matriz de adyacencia + diagonal")
            self.label_descripcion.config(
                text="Se construye la matriz de adyacencia del grafo y se agrega el valor 1 "
                     "en toda la diagonal principal."
            )
            self._pintar_matriz(self.M1, etiquetas, etiquetas, diagonal=self.diagonal)

            if len(self.diagonal) > 0:
                self.label_extra.config(text="Los 1's agregados en la diagonal se muestran en azul.")

        elif tipo == "potencia":
            iteracion = self.iteraciones[indice]
            exponente = iteracion["exponente"]

            self.label_titulo.config(text=f"Paso 2: calculando M^{exponente} = M^{exponente - 1} · M")

            if iteracion["estable"]:
                self.label_descripcion.config(
                    text=f"Se multiplica otra vez la matriz anterior por M (producto booleano) y el "
                         f"resultado no cambia: ya se encontraron todos los caminos."
                )
            else:
                self.label_descripcion.config(
                    text=f"Se multiplica (producto booleano) la matriz anterior por la matriz M del Paso 1: "
                         f"hay un 1 en la posición (i, j) si i llega a algún nodo t y desde t hay una arista "
                         f"hacia j. Como la diagonal tiene 1's, M^{exponente} incluye los caminos de hasta "
                         f"{exponente} pasos. Los 1's nuevos se marcan en naranja."
                )

            self._pintar_matriz(iteracion["matriz"], etiquetas, etiquetas, nuevos=celdas_nuevas(iteracion))
            self.label_extra.config(text=texto_nuevos(etiquetas, iteracion))

        elif tipo == "caminos":
            self.label_titulo.config(text="Paso 2: Matriz de caminos (resultado)")
            self.label_descripcion.config(
                text="Cuando al multiplicar ya no aparecen 1's nuevos se obtiene la matriz de "
                     "caminos M_R∞: indica qué nodos son alcanzables desde cada nodo."
            )
            self._pintar_matriz(self.R, etiquetas, etiquetas)
            self.label_extra.config(text=texto_alcance(self.R, etiquetas))

        elif tipo == "filas":
            self.label_titulo.config(text="Paso 3: Ordenar filas")
            self.label_descripcion.config(
                text="Se ordenan las filas según la cantidad de 1's que contienen (de mayor "
                     "a menor). En caso de empate, se prioriza la fila cuyo primer 1 esté "
                     "más cerca de la primera columna."
            )
            self._pintar_matriz(self.R_filas, etiquetas_orden, etiquetas)
            self.label_extra.config(text=texto_cantidades(self.R, self.orden, etiquetas))

        elif tipo == "columnas":
            self.label_titulo.config(text="Paso 4: Ordenar columnas y formar bloques")
            self.label_descripcion.config(
                text="Se reordenan las columnas en el mismo orden que las filas. Los bloques "
                     "cuadrados diagonales formados por 1's marcados en rojo son las "
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
        self.detener_reproduccion()

        if self.paso_actual > 0:
            self.paso_actual -= 1
            self.mostrar_paso()

    def siguiente(self):
        self.detener_reproduccion()

        if self.paso_actual < len(self.pantallas) - 1:
            self.paso_actual += 1
            self.mostrar_paso()

    def alternar_reproduccion(self):
        if self.reproduciendo:
            self.detener_reproduccion()
            return

        if self.paso_actual == len(self.pantallas) - 1:
            self.paso_actual = 0
            self.mostrar_paso()

        self.reproduciendo = True
        self.btn_reproducir.config(text="Pausar", bg="#ffe0b3")
        self.programar_siguiente()

    def programar_siguiente(self):
        milisegundos = self.VELOCIDADES[self.var_velocidad.get()]
        self.tarea = self.after(milisegundos, self.avanzar_automatico)

    def avanzar_automatico(self):
        if not self.reproduciendo:
            return

        if self.paso_actual < len(self.pantallas) - 1:
            self.paso_actual += 1
            self.mostrar_paso()

        if self.paso_actual >= len(self.pantallas) - 1:
            self.detener_reproduccion()
        else:
            self.programar_siguiente()

    def detener_reproduccion(self):
        self.reproduciendo = False
        self.btn_reproducir.config(text="Reproducir", bg="#c7f0d8")

        if self.tarea is not None:
            self.after_cancel(self.tarea)
            self.tarea = None

    def cerrar(self):
        self.detener_reproduccion()
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
