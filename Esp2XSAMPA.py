"""
Esp2XSAMPA - espanol a X-SAMPA para VOCALOID japones
----------------------------------------------------
Mientras este activo, lo que escribas (en espanol) se transforma al instante
en fonemas X-SAMPA compatibles con los VOCALOID japoneses, separados por
espacios. Escribe silaba por silaba; no hace falta apretar espacio.

Requisitos:   pip install pynput pystray pillow   (solo Windows; tkinter ya viene con Python)
Ejecutar:     python Esp2XSAMPA.py                (conviene como administrador)

Atajos (en cualquier programa):
    F9 (configurable)   activar / desactivar la conversion
    Ctrl+Alt+Q          salir del programa
"""
import ctypes
import queue
import re as _re
import threading
import unicodedata

# ----------------------------------------------------------------------------
# Opciones
# ----------------------------------------------------------------------------
# Pronunciacion de "ll" y de "y" consonantica.
# Rioplatense: "Z" (zheismo) o "S" (sheismo). Otros dialectos: "j".
# Excepcion: una Y escrita en MAYUSCULA al inicio de silaba (ante vocal) da siempre "j",
# sea cual sea esta opcion:   yo -> Z o  (o S o / j o)      YO -> j o
YEISMO = "Z"

# "sh" da siempre el fonema "S" (sha -> S a), igual que "ch" da "tS".
# Una C escrita en MAYUSCULA ante e o i (Ce, Ci) cambia igual que la Z mayuscula, segun el
# esquema de z elegido (ver ZETA_ESQUEMAS abajo); la c minuscula siempre da "s":
#   z -> s, Z / C -> dz:   ce -> s e   Ce -> dz e   Ci -> dz i
#   z -> s, Z / C -> ts:   ce -> s e   Ce -> ts e   Ci -> ts i
#   z -> s, Z / C -> z:    ce -> s e   Ce -> z e    Ci -> z i
# (Ca, Co, Cu y Ch no cambian)

# Fonemas X-SAMPA de los VOCALOID japoneses (los unicos que acepta la voz):
#   vocales:     a i M e o
#   consonantes: k g s S z dz Z dZ t ts tS d n J h C p\ p b m j 4 w N
#   palatalizadas (solo ante i): k' g' N' t' d' p' b' m' 4' p\'
# Este programa solo produce fonemas de esa lista.
#
# Los VOCALOID japoneses no tienen "r" ni "l": su unico sonido de ese tipo es
# el "4" (ra, ri, ru, re, ro).
#   r  -> 4        l  -> 4        rr -> 4 4        R (mayuscula) -> 4 4
#   RR (dos R mayusculas juntas) -> 4 4 4 4  (erre fuertemente pronunciada)
# El programa NO adivina si una r es suave o fuerte: eso lo decides tu al
# escribir (r = un golpe; rr o R en mayuscula = dos golpes; RR = cuatro golpes).
R_L_JAPONESA = "4"

# Palatalizacion automatica ante la vocal i. Solo se usan pares que existen de verdad
# en los VOCALOID japoneses (comprobado contra las tablas de fonemas y las muestras
# de un banco japones). Las consonantes palatalizadas que existen son:
#   k' g' N' t' d' p' b' m' 4' p\'
#   ri -> 4' i, ti -> t' i, ki -> k' i, gi -> g' i, di -> d' i, pi -> p' i,
#   bi -> b' i, mi -> m' i, fi -> p\' i
# Estos NO existen con apostrofe, asi que no se les pone:
#   - ya palatales o con i propia: s S Z dz dZ ts tS C J (si -> s i, chi -> tS i, ...)
#   - h (hi, ji -> h i, que tu voz si tiene; con mayusculas JI -> C i)
#   - z (zi -> z i, que tu voz si tiene)
#   - n no tiene "n' i" ni "n i" propio; se reemplaza por el fonema japones
#     equivalente:  ni -> J i
# Quedan afuera las semiconsonantes j y w, que suenan como vocales.
PALATAL = {"k": "k'", "g": "g'", "N": "N'", "t": "t'", "d": "d'", "p": "p'",
           "b": "b'", "m": "m'", "4": "4'", "p\\": "p\\'"}
ANTE_I = {"n": "J"}      # reemplazo ante i (no existe la version con apostrofe)

# La jota (j, ge, gi) en espanol es [x], que no existe en japones.
#   minuscula:  h                       (ja, ji, je, jo -> h a, h i, h e, h o; ju -> h M)
#   mayuscula:  h igual que arriba      (JA, JE, JO -> h a, h e, h o)
#               salvo JI -> C i (mas fuerte) y JU -> p\ M
# "Mayuscula" = Bloq Mayus o Shift, igual que con la U.
JOTA = "h"
JOTA_FUERTE = "C"

# La "u" espanola es la "M" japonesa (う). "ju" suena como ふ: "p\ M".
VOCAL_U = "M"

# La "f" espanola es [f] (labiodental), que no existe en japones. Se usa la mas
# cercana: p\ (ふ, [ɸ] bilabial), suave y con poco ruido. f y F dan el mismo resultado.
#   fa, fe, fi, fo, fu -> p\ a, p\ e, p\ i, p\ o, p\ M
F_SUAVE = "p\\"

# La "z" espanola es [s] (seseo) o [θ] (Espana); en japones no hay [θ].
# La "c" ante e / i (ce, ci) suena igual que la z, asi que el esquema elegido afecta a las dos.
# Hay tres esquemas (se elige en la ventana); el predeterminado es "sdz".
# La minuscula (z, y c ante e / i) siempre da s; la MAYUSCULA (Z, y C ante e / i) cambia:
#   "sdz":  minuscula s  (さ, sorda)   el sonido real de la z espanola
#           mayuscula dz (ざ africada) lleva un golpe de "d" antes: ataque marcado cuando
#                                      se quiere, sin perder el seseo normal.
#   "sts":  minuscula s  (さ, sorda)   el sonido real de la z espanola
#           mayuscula ts (つ africada) lleva un golpe de "t" antes: ataque marcado como la dz,
#                                      pero sorda, igual que la s (sin voz).
#   "sz":   minuscula s  (さ, sorda)   el sonido real de la z espanola
#           mayuscula z  (ざ, sonora)  mas suave y "zumbada"; sirve si la s suena seca
#                                      o se pierde entre vocales, o para la z sonora
#                                      (mismo, desde). Es una opcion estetica.
# "Mayuscula" = Bloq Mayus o Shift. Se puede alternar letra por letra.
#   za -> s a    ZA -> dz a / ts a / z a        ce -> s e    Ce -> dz e / ts e / z e
# (Los esquemas "zdz" -- z -> z, Z -> dz -- y "sch" -- Z / C -> tS, que sonaba incorrecto --
# ya no existen; si config.json los tiene guardados, se usa el predeterminado.)
ZETA_ESQUEMAS = {"sdz": ("s", "dz"), "sts": ("s", "ts"), "sz": ("s", "z")}   # (minuscula, mayuscula)
ZETA = "sdz"

# La "i": en minuscula el programa decide solo si es semiconsonante (j) o vocal (i):
# j cuando forma diptongo con una vocal vecina, tanto al principio (tiene -> t j e n e)
# como al final de la silaba (baile -> b a j 4 e, hay -> a j); i en los demas casos.
# Escrita en mayuscula (Bloq Mayus o Shift) es SIEMPRE la vocal "i", nunca "j"
# (baIle -> b a i 4 e, tIene -> t i e n e). En los VOCALOID japoneses tanto "a i" como
# "a j" son validas: "a j" se usa para suavizar la union cuando "a i" suena cortada
# (pasa en voicebanks de primera generacion). La mayuscula permite elegir "a i" cuando
# la "j" no suena bien. Se eligio "i" y no "j" para la mayuscula porque el automatico
# ya pone "j" en todos los diptongos: forzar "j" casi nunca cambiaria nada.

U_CAP = "\x03"           # u escrita en mayuscula: siempre M, nunca w
DIERESIS_CAP = "\x04"    # ü escrita en mayuscula: siempre M
J_CAP = "\x05"           # J escrita en mayuscula: JI -> C i, JU -> p\ M (el resto sigue con h)
G_CAP = "\x06"           # G escrita en mayuscula: GI (suave) -> C i; GE -> h e
R_CAP = "\x07"           # R escrita en mayuscula: siempre rr (4 4); dos juntas (RR): 4 4 4 4
I_CAP = "\x0e"           # I escrita en mayuscula: siempre la vocal i, nunca j
Z_CAP = "\x10"           # Z escrita en mayuscula: variante segun el esquema (ver ZETA)
C_CAP = "\x13"           # C escrita en mayuscula ante e / i (Ce, Ci): variante segun el esquema (ver ZETA)
Y_CAP = "\x11"           # Y escrita en mayuscula ante vocal: siempre j, en todos los modos de ll / y
I_MARCA = "\x12"          # i entre consonante y vocal tonica (tilde o mayuscula): ver g2p
CONS_ANTES_I = "bcdfgjklmnñprstvwxzBCDFGJKLMNÑPRSTVWXZ"
RE_I_TONICA = _re.compile("([%s])i([aeouáéóúAEOUÁÉÓÚ]+)" % CONS_ANTES_I)
VOCALES = "aeiouIU" + U_CAP + DIERESIS_CAP + I_CAP   # I y U = i y u acentuadas (nunca diptongo)
SUAVES = "eiI" + I_CAP + I_MARCA   # vocales que suavizan c y g (ce, ci, ge, gi)
FUERTES = "aeo"


# ----------------------------------------------------------------------------
# Conversion texto -> X-SAMPA
# ----------------------------------------------------------------------------
def normalizar(palabra):
    """Minusculas, sin tildes, pero conserva n con tilde y u con dieresis;
    i/u acentuadas pasan a I/U."""
    p = palabra.lower()
    p = p.replace("\u00f1", "\x01").replace("\u00fc", "\x02")
    p = p.replace("\u00ed", "I").replace("\u00fa", "U")
    p = unicodedata.normalize("NFD", p)
    p = "".join(c for c in p if unicodedata.category(c) != "Mn")
    return p.replace("\x01", "\u00f1").replace("\x02", "\u00fc")


def jota(fuerte, sig=""):
    """Fonema japones de la jota: h normal. C solo si se escribio en mayuscula
    y va ante i (JI, GI); ante a, e, o la mayuscula sigue dando h."""
    return JOTA_FUERTE if (fuerte and sig in ("i", "I", I_CAP)) else JOTA


def g2p(palabra):
    """Devuelve la transcripcion X-SAMPA con los fonemas separados por espacios."""
    # i entre consonante y vocal, si la ultima vocal lleva tilde o va en mayuscula (pio, kiU):
    # la i se absorbe en la consonante palatalizada (p' o, k' M). Se marca antes de normalizar.
    palabra = RE_I_TONICA.sub(
        lambda m: m.group(1) + (I_MARCA if m.group(2)[-1] in "áéóúAEOUÁÉÓÚ" else "i") + m.group(2),
        palabra)
    palabra = palabra.replace("U", U_CAP).replace("\u00dc", DIERESIS_CAP)
    palabra = palabra.replace("J", J_CAP).replace("G", G_CAP).replace("R", R_CAP)
    palabra = palabra.replace("Z", Z_CAP).replace("Y", Y_CAP).replace("C", C_CAP)
    palabra = palabra.replace("I", I_CAP)          # antes de normalizar (que pasa a minusculas)
    w = normalizar(palabra)
    n = len(w)
    out = []
    i = 0
    while i < n:
        c = w[i]
        ant = w[i - 1] if i > 0 else ""
        sig = w[i + 1] if i + 1 < n else ""
        sig2 = w[i + 2] if i + 2 < n else ""
        suave = sig != "" and sig in SUAVES

        if c in ("c", C_CAP):
            if sig == "h":
                out.append("tS")
                i += 2
                continue
            if c == C_CAP and suave:
                out.append(ZETA_ESQUEMAS[ZETA][1])   # Ce, Ci con C mayuscula: igual que la Z mayuscula
            else:
                out.append("s" if suave else "k")
        elif c == "q":
            out.append("k")
            if sig in ("u", U_CAP):
                i += 1          # la u de que/qui es muda
        elif c in ("g", G_CAP):
            if sig in ("u", U_CAP) and sig2 != "" and sig2 in SUAVES:
                out.append("g")  # gue, gui
                i += 1
            elif suave:
                out.append(jota(c == G_CAP, sig))
            else:
                out.append("g")
        elif c == "l":
            if sig == "l":
                out.append(YEISMO)
                i += 2
                continue
            out.append(R_L_JAPONESA)
        elif c in ("r", R_CAP):
            doble = sig in ("r", R_CAP)            # rr, RR, rR o Rr
            if c == R_CAP and sig == R_CAP:        # RR: erre fuertemente pronunciada (4 4 4 4)
                out.extend([R_L_JAPONESA] * 4)
                i += 2
                continue
            if doble or c == R_CAP:                # o una R escrita en mayuscula
                out.extend([R_L_JAPONESA, R_L_JAPONESA])
                i += 2 if doble else 1
                continue
            out.append(R_L_JAPONESA)
        elif c == Y_CAP and sig != "" and sig in VOCALES:
            out.append("j")             # Y en mayuscula al inicio de silaba: siempre j
        elif c in ("y", Y_CAP):
            if sig == "" or sig not in VOCALES:
                if n == 1:
                    out.append("i")
                else:
                    out.append("j" if (ant != "" and ant in VOCALES) else "i")
            else:
                out.append(YEISMO)
        elif c == "i":
            glide = (sig != "" and sig in FUERTES) or (ant != "" and ant in FUERTES) or sig in ("u", U_CAP)
            out.append("j" if glide else "i")
        elif c == I_MARCA:
            out.append(I_MARCA)                  # se resuelve despues (ver abajo)
        elif c == "u":
            glide = (sig != "" and sig in FUERTES) or (ant != "" and ant in FUERTES) or sig == "i"
            out.append("w" if glide else VOCAL_U)
        elif c == "\u00fc":
            out.append("w")
        elif c in (U_CAP, DIERESIS_CAP):
            out.append(VOCAL_U)
        elif c in ("I", I_CAP):                  # i acentuada o escrita en mayuscula
            out.append("i")
        elif c == "U":
            out.append(VOCAL_U)
        elif c == "\u00f1":
            out.append("J")
        elif c == "h":
            pass
        elif c in ("j", J_CAP):
            fuerte = c == J_CAP
            if fuerte:
                glide_u = sig == "u" and sig2 != "" and (sig2 in FUERTES or sig2 == "i")
                if sig != "" and (sig in "uU" or sig == U_CAP) and not glide_u:
                    out.extend(["p\\", VOCAL_U])   # JU -> fu
                    i += 2
                    continue
            out.append(jota(fuerte, sig))
        elif c == "s":
            if sig == "h":
                out.append("S")         # sh: siempre S (sha -> S a)
                i += 2
                continue
            out.append("s")
        elif c == "z":
            out.append(ZETA_ESQUEMAS[ZETA][0])
        elif c == Z_CAP:
            out.append(ZETA_ESQUEMAS[ZETA][1])   # Z en mayuscula
        elif c == "v":
            out.append("b")
        elif c == "f":
            out.append(F_SUAVE)     # f no existe en japones: se usa la de ふ
        elif c == "x":
            out.extend(["k", "s"])
        else:
            out.append(c)
        i += 1
    for k in range(1, len(out)):                  # consonante + i + vocal tonica -> C' vocal
        if out[k] == I_MARCA:
            prev = out[k - 1]
            if prev in PALATAL and prev != "p\\":    # p\ (f) queda fuera: no suena bien
                out[k - 1], out[k] = PALATAL[prev], None
            elif prev in ANTE_I:
                out[k - 1], out[k] = ANTE_I[prev], None  # J no lleva apostrofe: n -> J
            else:
                out[k] = "j"                      # sin version palatal: diptongo normal
    out = [f for f in out if f is not None]
    for k in range(len(out) - 1):                 # consonante + i -> version palatal valida
        if out[k + 1] == "i":
            if out[k] in PALATAL:
                out[k] = PALATAL[out[k]]
            elif out[k] in ANTE_I:
                out[k] = ANTE_I[out[k]]
    return " ".join(out)


# ----------------------------------------------------------------------------
# Captura y reemplazo de teclado (Windows)
# ----------------------------------------------------------------------------
import base64  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import tkinter as tk  # noqa: E402
import tkinter.font as tkfont  # noqa: E402
from tkinter import messagebox, ttk  # noqa: E402
from xml.sax.saxutils import escape as xml_escape  # noqa: E402

from pynput import keyboard  # noqa: E402

try:                                   # dibujo del icono (opcional)
    from PIL import Image, ImageDraw  # noqa: E402
    HAY_PIL = True
except Exception:
    HAY_PIL = False

try:                                   # icono en la bandeja del sistema (opcional)
    import pystray  # noqa: E402
    HAY_BANDEJA = HAY_PIL
except Exception:
    HAY_BANDEJA = False

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.restype = ctypes.c_void_p
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
kernel32.CreateEventW.restype = ctypes.c_void_p
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p]
kernel32.SetEvent.argtypes = [ctypes.c_void_p]
kernel32.WaitForSingleObject.restype = ctypes.c_uint32
kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

# --- Instancia unica -------------------------------------------------------------
# Un mutex con nombre impide abrir una segunda copia. La segunda copia avisa a la primera
# (con un evento con nombre) para que muestre su ventana, y se cierra.
MUTEX_NOMBRE = "Local\\Esp2XSAMPA_instancia_unica"
EVENTO_NOMBRE = "Local\\Esp2XSAMPA_mostrar_ventana"
ERROR_ACCESS_DENIED, ERROR_ALREADY_EXISTS = 5, 183   # (el 5 pasa si la otra copia es de otro nivel de permisos)
_mutex = None
EVENTO_MOSTRAR = None


def instancia_unica(avisar=True):
    """True si esta es la unica copia. Si ya hay otra da False y, si 'avisar', le pide que
    muestre su ventana (el arranque automatico no avisa: no debe abrir nada)."""
    global _mutex, EVENTO_MOSTRAR
    ctypes.set_last_error(0)
    _mutex = kernel32.CreateMutexW(None, False, MUTEX_NOMBRE)      # el sistema lo libera al salir
    ya_hay = ctypes.get_last_error() in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED)
    evento = kernel32.CreateEventW(None, False, False, EVENTO_NOMBRE)
    if ya_hay:
        if evento and avisar:
            kernel32.SetEvent(evento)
        return False
    EVENTO_MOSTRAR = evento
    return True


user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetParent.restype = ctypes.c_void_p
user32.GetParent.argtypes = [ctypes.c_void_p]
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_uint]


# --- Escritura de texto independiente de Bloq Mayus / Shift -----------------
# Se envian los caracteres como eventos Unicode (SendInput + KEYEVENTF_UNICODE):
# llegan tal cual, sin pasar por el teclado, asi que Bloq Mayus no los altera.
class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_uint16), ("wScan", ctypes.c_uint16),
                ("dwFlags", ctypes.c_uint32), ("time", ctypes.c_uint32),
                ("dwExtraInfo", ctypes.c_size_t)]


class _MOUSEINPUT(ctypes.Structure):      # solo para que la union tenga el tamano correcto
    _fields_ = [("dx", ctypes.c_int32), ("dy", ctypes.c_int32),
                ("mouseData", ctypes.c_uint32), ("dwFlags", ctypes.c_uint32),
                ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_uint32), ("wParamL", ctypes.c_uint16),
                ("wParamH", ctypes.c_uint16)]


class _UNION_INPUT(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("u", _UNION_INPUT)]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
# Marca que ponemos en dwExtraInfo de TODO lo que inyectamos nosotros. Asi el filtro
# reconoce sus propios eventos y no confunde con ellos a los inyectados por otros
# programas (Moonlight/Sunshine, escritorio remoto, etc.), que si deben convertirse.
MARCA_PROPIA = 0x45325358


def escribir_texto(texto):
    """Escribe 'texto' caracter a caracter, sin que Bloq Mayus ni Shift lo cambien."""
    eventos = []
    for ch in texto:
        for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP):
            e = _INPUT(type=INPUT_KEYBOARD)
            e.u.ki = _KEYBDINPUT(0, ord(ch), flags, 0, MARCA_PROPIA)
            eventos.append(e)
    if eventos:
        lista = (_INPUT * len(eventos))(*eventos)
        user32.SendInput(len(eventos), lista, ctypes.sizeof(_INPUT))

def enviar_vk(vk):
    """Pulsa y suelta una tecla virtual (marcada como propia)."""
    eventos = []
    for flags in (0, KEYEVENTF_KEYUP):
        e = _INPUT(type=INPUT_KEYBOARD)
        e.u.ki = _KEYBDINPUT(vk, 0, flags, 0, MARCA_PROPIA)
        eventos.append(e)
    lista = (_INPUT * len(eventos))(*eventos)
    user32.SendInput(len(eventos), lista, ctypes.sizeof(_INPUT))


VK_F9 = 0x78
VK_Q = 0x51
WM_KEYDOWN, WM_SYSKEYDOWN = 0x100, 0x104
MODIFICADORES = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C, 0x14}
DELIMITADORES = {0x20, 0x0D, 0x09}                 # espacio, enter, tab
ACENTOS = {
    "agudo": {"a": "\u00e1", "e": "\u00e9", "i": "\u00ed", "o": "\u00f3", "u": "\u00fa"},
    "dieresis": {"u": "\u00fc"},
}

# Teclas que se pueden elegir para activar/desactivar (ninguna sirve para escribir)
NOMBRES_TECLAS = {
    0x13: "Pause", 0x91: "Scroll Lock", 0x2C: "Print Screen", 0x2D: "Insert",
    0x2E: "Delete", 0x24: "Home", 0x23: "End", 0x21: "Page Up", 0x22: "Page Down",
}
TECLAS_ACTIVACION = set(range(0x70, 0x88)) | set(NOMBRES_TECLAS)   # F1-F24 y las de arriba

config = {"toggle": VK_F9, "visible": False, "bandeja": True, "tema": "clasico",
          "inicio": False, "inicio_ruta": ""}   # inicio: desactivado por defecto; inicio_ruta: programa registrado en la tarea
# Arranque automatico (tarea programada): el programa se abre en segundo plano, solo con el
# icono de la bandeja y con la conversion desactivada. Solo tiene sentido si hay bandeja.
INICIO_SILENCIOSO = "--inicio" in sys.argv[1:] and HAY_BANDEJA
# La configuracion se guarda junto al programa: al lado del .exe (PyInstaller) o del .py.
# Se usa sys.executable y no el directorio actual, porque con --uac-admin el directorio
# de trabajo puede ser otro (p. ej. System32).
if getattr(sys, "frozen", False):
    CARPETA_PROGRAMA = os.path.dirname(os.path.abspath(sys.executable))
else:
    CARPETA_PROGRAMA = os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG = os.path.join(CARPETA_PROGRAMA, "config.json")
# Ubicaciones de versiones anteriores: solo se leen una vez para migrar los ajustes.
_APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
RUTAS_CONFIG_ANTIGUAS = (
    os.path.join(_APPDATA, "Esp2XSAMPA", "config.json"),
    os.path.join(_APPDATA, "TecladoXSAMPA", "config.json"),
)


def dibujar_icono(tam, activo=True):
    """Icono del programa, al estilo de los programas clasicos de Windows: una ventana con
    barra de titulo en degradado turquesa (como VOCALOID), un pentagrama con corcheas
    (musica) y, abajo, la conversion  n~ -> J  (espanol -> X-SAMPA).
    Gris si la conversion esta desactivada. Se dibuja grande y se reduce (bordes suaves)."""
    K = 4                                                  # factor de sobremuestreo
    g = 256 * K
    img = Image.new("RGBA", (g, g), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    detalle = tam >= 40                                    # en tamanos chicos, sin letras ni pentagrama

    def P(*v):
        return [c * K for c in v]

    def caja(x1, y1, x2, y2, **kw):
        d.rectangle(P(x1, y1, x2, y2), **kw)

    def trazo(puntos, ancho, color):                       # linea gruesa con puntas redondeadas
        pts = [(x * K, y * K) for x, y in puntos]
        d.line(pts, fill=color, width=int(ancho * K), joint="curve")
        for x, y in pts:
            r = ancho * K / 2
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def elipse(cx, cy, a, b, ang, color):                  # elipse inclinada (cabeza de nota)
        pts = []
        for i in range(48):
            t = 2 * math.pi * i / 48
            x, y = a * math.cos(t), b * math.sin(t)
            pts.append(((cx + x * math.cos(ang) - y * math.sin(ang)) * K,
                        (cy + x * math.sin(ang) + y * math.cos(ang)) * K))
        d.polygon(pts, fill=color)

    def nota(cx, cy, e, color):                            # dos corcheas unidas (nota musical)
        x1, y1, x2, y2 = cx - 26 * e, cy + 24 * e, cx + 26 * e, cy + 16 * e
        elipse(x1, y1, 15 * e, 11 * e, -0.35, color)
        elipse(x2, y2, 15 * e, 11 * e, -0.35, color)
        s1, s2 = x1 + 13 * e, x2 + 13 * e                  # plicas
        t1, t2 = cy - 34 * e, cy - 42 * e
        d.rectangle(P(s1 - 3.5 * e, t1, s1 + 3.5 * e, y1), fill=color)
        d.rectangle(P(s2 - 3.5 * e, t2, s2 + 3.5 * e, y2), fill=color)
        d.polygon(P(s1 - 3.5 * e, t1, s2 + 3.5 * e, t2, s2 + 3.5 * e, t2 + 14 * e,
                    s1 - 3.5 * e, t1 + 14 * e), fill=color)   # barra

    # --- ventana ---
    d.rounded_rectangle(P(20, 26, 248, 244), radius=16 * K, fill=(0, 0, 0, 70))        # sombra
    d.rounded_rectangle(P(10, 14, 240, 234), radius=14 * K, fill=(14, 22, 44))         # contorno
    d.rounded_rectangle(P(13, 17, 237, 231), radius=12 * K, fill=(212, 208, 200))      # cara
    caja(15, 19, 235, 20.5, fill=(255, 255, 255))                                       # bisel claro
    caja(15, 19, 16.5, 229, fill=(255, 255, 255))
    caja(15, 229.5, 235, 231, fill=(128, 128, 128))                                     # bisel oscuro
    caja(233.5, 19, 235, 231, fill=(128, 128, 128))

    # barra de titulo con degradado navy -> turquesa
    grad = Image.new("RGBA", (g, g), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    c0, c1 = (8, 40, 110), (60, 196, 188)
    x0, x1 = 21 * K, 229 * K
    for x in range(int(x0), int(x1)):
        t = (x - x0) / (x1 - x0)
        gd.line((x, 0, x, g), fill=tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3)) + (255,))
    mascara = Image.new("L", (g, g), 0)
    md = ImageDraw.Draw(mascara)
    md.rounded_rectangle(P(21, 24, 229, 80), radius=9 * K, fill=255)
    md.rectangle(P(0, 64, 256, 90), fill=0)                                             # recorta abajo
    img.paste(grad, (0, 0), mascara)

    if detalle:
        trazo([(31, 44), (112, 44)], 7, (255, 255, 255))                                # titulo
        for bx in (160, 180, 204):                                                      # botones
            caja(bx, 31, bx + 18, 57, fill=(212, 208, 200))
            caja(bx, 31, bx + 18, 32.5, fill=(255, 255, 255))
            caja(bx, 31, bx + 1.5, 57, fill=(255, 255, 255))
            caja(bx, 55.5, bx + 18, 57, fill=(64, 64, 64))
            caja(bx + 16.5, 31, bx + 18, 57, fill=(64, 64, 64))
        caja(165, 50, 173, 53, fill=(20, 20, 20))                                       # minimizar
        d.rectangle(P(185, 38, 193, 47), outline=(20, 20, 20), width=3 * K // 2)       # maximizar
        trazo([(209.5, 39), (216.5, 49)], 3, (20, 20, 20))                              # cerrar
        trazo([(216.5, 39), (209.5, 49)], 3, (20, 20, 20))

    # zona de contenido hundida (blanca)
    caja(22, 68, 228, 226, fill=(255, 255, 255))
    caja(22, 68, 228, 70, fill=(110, 110, 110))
    caja(22, 68, 24, 226, fill=(110, 110, 110))

    turquesa, rojo, azul = (0, 128, 140), (196, 32, 44), (10, 56, 140)
    if detalle:
        for y in (100, 110, 120, 130, 140):                                             # pentagrama
            caja(34, y - 1, 216, y + 1, fill=(150, 162, 168))
        nota(122, 112, 1.0, turquesa)
        # n~  ->  J   (X-SAMPA: la ene se escribe J)
        trazo([(46, 188), (46, 214)], 9, rojo)                                          # n: palo
        trazo([(46, 198), (50, 190), (58, 186), (66, 189), (70, 198), (70, 214)], 9, rojo)  # n: arco
        trazo([(44 + 30 * i / 20, 174 - 5 * math.sin(2 * math.pi * i / 20)) for i in range(21)],
              5, rojo)                                                                  # ~
        trazo([(96, 200), (134, 200)], 7, (60, 60, 60))                                 # flecha
        trazo([(124, 190), (136, 200), (124, 210)], 7, (60, 60, 60))
        trazo([(176, 182), (176, 203)], 9, azul)                                        # J: palo
        trazo([(176, 203), (172, 211), (164, 213), (158, 208)], 9, azul)                # J
        trazo([(164, 182), (186, 182)], 7, azul)
    else:
        nota(125, 150, 1.55, turquesa)

    if not activo:                                                                      # gris
        gris = img.convert("L")
        img = Image.merge("RGBA", (gris, gris, gris, img.split()[3]))
    return img.resize((tam, tam), Image.LANCZOS)


def crear_icono(activo):
    """Icono de la bandeja: azul si esta activo, gris si no."""
    return dibujar_icono(64, activo)


def nombre_tecla(vk):
    if 0x70 <= vk <= 0x87:
        return "F%d" % (vk - 0x6F)
    return NOMBRES_TECLAS.get(vk, "tecla %d" % vk)


def cargar_config():
    global YEISMO, ZETA
    ruta = next((r for r in (RUTA_CONFIG,) + RUTAS_CONFIG_ANTIGUAS if os.path.exists(r)),
                RUTA_CONFIG)
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("toggle") in TECLAS_ACTIVACION:
            config["toggle"] = d["toggle"]
        if d.get("ll") in ("Z", "S", "j"):
            YEISMO = d["ll"]
        if d.get("zeta") in ZETA_ESQUEMAS:
            ZETA = d["zeta"]
        config["visible"] = bool(d.get("visible", False))
        config["bandeja"] = bool(d.get("bandeja", True))
        if d.get("tema") in TEMAS:
            config["tema"] = d["tema"]
        config["inicio"] = d.get("inicio") is True
        config["inicio_ruta"] = str(d.get("inicio_ruta", ""))
    except Exception:
        pass            # sin archivo o dañado: valores por defecto


def guardar_config():
    try:
        with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
            json.dump({"toggle": config["toggle"], "ll": YEISMO, "zeta": ZETA,
                       "visible": config["visible"], "bandeja": config["bandeja"],
                       "tema": config["tema"], "inicio": config["inicio"], "inicio_ruta": config["inicio_ruta"]}, f)
    except Exception:
        pass


# --- Inicio con Windows -----------------------------------------------------------
# Se usa una tarea programada (al iniciar sesion, con privilegios maximos) y no la clave
# Run del registro: el .exe se compila con --uac-admin y Windows no inicia automaticamente
# los programas que piden permisos de administrador desde esa clave.
NOMBRE_TAREA = "Esp2XSAMPA_inicio"
SIN_VENTANA = 0x08000000        # CREATE_NO_WINDOW


def _schtasks(*args):
    return subprocess.run(["schtasks"] + list(args), capture_output=True, text=True,
                          errors="replace", stdin=subprocess.DEVNULL,
                          creationflags=SIN_VENTANA, timeout=30)


def comando_inicio():
    """(programa, argumentos) con que la tarea abre Esp2XSAMPA."""
    if getattr(sys, "frozen", False):
        return sys.executable, "--inicio"
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")   # sin consola
    programa = pyw if os.path.exists(pyw) else sys.executable
    return programa, '"%s" --inicio' % os.path.abspath(__file__)


def inicio_existe():
    try:
        return _schtasks("/Query", "/TN", NOMBRE_TAREA).returncode == 0
    except Exception:
        return False


def inicio_activar():
    """Crea la tarea de inicio. Devuelve (ok, mensaje de error)."""
    programa, argumentos = comando_inicio()
    usuario = "%s\\%s" % (os.environ.get("USERDOMAIN", ""), os.environ.get("USERNAME", ""))
    usuario = xml_escape(usuario.lstrip("\\"))
    xml = ('<?xml version="1.0" encoding="UTF-16"?>\n'
           '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
           "<RegistrationInfo><Description>Esp2XSAMPA: abre el programa en segundo plano "
           "al iniciar sesion.</Description></RegistrationInfo>\n"
           "<Triggers><LogonTrigger><Enabled>true</Enabled><UserId>%(u)s</UserId>"
           "</LogonTrigger></Triggers>\n"
           '<Principals><Principal id="Author"><UserId>%(u)s</UserId>'
           "<LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel>"
           "</Principal></Principals>\n"
           "<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>"
           "<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>"
           "<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>"
           "<AllowHardTerminate>true</AllowHardTerminate><AllowStartOnDemand>true</AllowStartOnDemand>"
           "<Enabled>true</Enabled><Hidden>false</Hidden>"
           "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit><Priority>7</Priority></Settings>\n"
           '<Actions Context="Author"><Exec><Command>%(c)s</Command><Arguments>%(a)s</Arguments>'
           "<WorkingDirectory>%(d)s</WorkingDirectory></Exec></Actions>\n"
           "</Task>\n") % {"u": usuario, "c": xml_escape(programa), "a": xml_escape(argumentos),
                          "d": xml_escape(CARPETA_PROGRAMA)}
    ruta_xml = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False,
                                         encoding="utf-16") as f:
            f.write(xml)
            ruta_xml = f.name
        r = _schtasks("/Create", "/TN", NOMBRE_TAREA, "/XML", ruta_xml, "/F")
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or "Error desconocido.").strip()
        config["inicio"] = True
        config["inicio_ruta"] = firma_inicio()
        guardar_config()
        return True, ""
    except Exception as e:
        return False, str(e)
    finally:
        if ruta_xml:
            try:
                os.remove(ruta_xml)
            except Exception:
                pass


def inicio_desactivar():
    """Borra la tarea de inicio. Devuelve (ok, mensaje de error)."""
    try:
        if inicio_existe():
            r = _schtasks("/Delete", "/TN", NOMBRE_TAREA, "/F")
            if r.returncode != 0:
                return False, (r.stderr or r.stdout or "Error desconocido.").strip()
        config["inicio"] = False
        config["inicio_ruta"] = ""
        guardar_config()
        return True, ""
    except Exception as e:
        return False, str(e)


def firma_inicio():
    programa, argumentos = comando_inicio()
    return os.path.abspath(programa + argumentos)


class Captura:
    """Modo 'pulsa la nueva tecla de activación'."""
    activa = False
    mensaje = ""


captura = Captura()

cola = queue.Queue()
bloqueadas = set()
salir = threading.Event()
listener = None
HWND_PROPIA = None          # ventana del programa: ahi las teclas no se convierten
VENTANAS_PROPIAS = set()    # ventana principal + ventana de ayuda (si esta abierta)


class Estado:
    activo = True
    buffer = []
    acento = None


estado = Estado()


def presionada(vk):
    return (user32.GetAsyncKeyState(vk) & 0x8000) != 0


class Teclas:
    """Estado de Bloq Mayus llevado por el propio filtro.
    GetKeyState(VK_CAPITAL) no sirve dentro del hook de teclado: el hilo del hook no
    procesa mensajes de teclado y su copia del estado del "toggle" queda desactualizada
    (se ve bien hasta que se cambia Bloq Mayus y luego sale al reves)."""
    caps = False          # Bloq Mayus activado
    caps_abajo = False    # tecla Bloq Mayus mantenida (la repeticion no cuenta)


teclas = Teclas()


def leer_caps_sistema():
    """Lectura inicial de Bloq Mayus (se llama desde el hilo de la ventana)."""
    return (user32.GetKeyState(0x14) & 1) == 1


def mayusculas():
    """True si la letra saldria en mayuscula (Bloq Mayus o Shift, pero no ambos)."""
    return teclas.caps != presionada(0x10)


def reiniciar_palabra():
    estado.buffer.clear()
    estado.acento = None
    cola.put(("reset",))


def enviar_palabra():
    cola.put(("palabra", g2p("".join(estado.buffer))))


def fijar_activo(valor):
    estado.activo = bool(valor)
    reiniciar_palabra()


def trabajador():
    """Escribe en pantalla, siempre en orden, cambiando solo lo necesario."""
    mostrado = ""
    while True:
        op = cola.get()
        if op[0] == "palabra":
            objetivo = op[1]
            p = 0
            while p < len(mostrado) and p < len(objetivo) and mostrado[p] == objetivo[p]:
                p += 1
            for _ in range(len(mostrado) - p):
                enviar_vk(0x08)                    # retroceso
            if objetivo[p:]:
                escribir_texto(objetivo[p:])
            mostrado = objetivo
        elif op[0] == "tecla":
            enviar_vk(op[1])
            mostrado = ""
        else:
            mostrado = ""


def bloquear(vk):
    bloqueadas.add(vk)
    listener.suppress_event()   # debe ser lo ultimo: corta la ejecucion del filtro


def filtro(msg, data):
    if getattr(data, "dwExtraInfo", 0) == MARCA_PROPIA:   # evento inyectado por nosotros
        return True
    vk = data.vkCode
    abajo = msg in (WM_KEYDOWN, WM_SYSKEYDOWN)

    if vk == 0x14:                                        # Bloq Mayus: llevar la cuenta
        if abajo:
            if not teclas.caps_abajo:                     # ignorar autorepeticion
                teclas.caps_abajo = True
                teclas.caps = not teclas.caps
        else:
            teclas.caps_abajo = False
        return True

    if not abajo:
        if vk in bloqueadas:
            bloqueadas.discard(vk)
            listener.suppress_event()
        return True

    if vk == VK_Q and presionada(0x11) and presionada(0x12):
        salir.set()
        return True
    if captura.activa and vk not in MODIFICADORES:
        if vk == 0x1B:                         # Esc cancela
            captura.activa = False
            captura.mensaje = ""
        elif vk in TECLAS_ACTIVACION:
            config["toggle"] = vk
            captura.activa = False
            captura.mensaje = ""
            guardar_config()
        else:
            captura.mensaje = "Tecla no permitida"
        bloquear(vk)
    if vk == config["toggle"]:
        fijar_activo(not estado.activo)
        bloquear(vk)
    if VENTANAS_PROPIAS and user32.GetForegroundWindow() in VENTANAS_PROPIAS:
        return True                            # escribiendo en nuestra ventana
    if not estado.activo or vk in MODIFICADORES:
        return True

    if presionada(0x11) or presionada(0x12):   # Ctrl/Alt (incluye AltGr)
        reiniciar_palabra()
        return True

    if vk == 0x08:                             # retroceso
        if estado.buffer:
            estado.buffer.pop()
            enviar_palabra()
            bloquear(vk)
        return True

    if vk in DELIMITADORES:                    # fin de palabra
        estado.buffer.clear()
        estado.acento = None
        cola.put(("tecla", vk))
        bloquear(vk)

    car = user32.MapVirtualKeyW(vk, 2)
    if car & 0x80000000:                       # tecla muerta (acento)
        estado.acento = "dieresis" if presionada(0x10) else "agudo"
        bloquear(vk)

    letra = chr(car & 0xFFFF).lower() if car else ""
    if letra.isalpha():
        if estado.acento:
            letra = ACENTOS[estado.acento].get(letra, letra)
            estado.acento = None
        if letra in ("u", "\u00fc", "i", "j", "g", "r", "z", "y", "c", "a", "e", "o") and mayusculas():
            letra = letra.upper()              # u -> M, i -> i, j/g -> jota fuerte, r -> rr, z -> z sonora, y -> j, c -> igual que Z ante e/i (ver g2p)
        estado.buffer.append(letra)
        enviar_palabra()
        bloquear(vk)

    if letra and letra.isprintable():          # digito o signo: cierra palabra
        estado.buffer.clear()
        estado.acento = None
        cola.put(("tecla", vk))
        bloquear(vk)

    reiniciar_palabra()                        # flechas, F-teclas, etc.
    return True


# ----------------------------------------------------------------------------
# Interfaz
# ----------------------------------------------------------------------------
TEXTO_AYUDA = (
    "Atajos (funcionan en cualquier programa):\n"
    "    {tecla}  \u2192  activar / desactivar\n"
    "    Ctrl+Alt+Q  \u2192  salir\n"
    "\n"
    "Puedes cambiar la tecla de activación en la ventana.\n"
    "Se puede usar F1-F24, Pause, Scroll Lock, Print Screen,\n"
    "Insert, Delete, Home, End, Page Up y Page Down.\n"
    "\n"
    "Escribe sílaba por sílaba. La sílaba se cierra con\n"
    "espacio, enter o tab.\n"
    "\n"
    "Con minúsculas:\n"
    "    r \u2192 4        rr \u2192 4 4        l \u2192 4\n"
    "    u \u2192 M        f \u2192 p\\        j \u2192 h\n"
    "    z \u2192 s  siempre   c + e / i \u2192 s  siempre  (ce \u2192 s e)\n"
    "    sh \u2192 S  siempre  (sha \u2192 S a,  shu \u2192 S M)\n"
    "    i \u2192 j si forma diptongo, si no i (tiene \u2192 t j e n e)\n"
    "    k g t d p b m r + i \u2192 con apóstrofe  (ri \u2192 4' i,  ti \u2192 t' i,  Ri \u2192 4 4' i)\n"
    "    ni \u2192 J i      fi \u2192 p\\' i      (s, z, ch, h, etc.: sin apóstrofe)\n"
    "    consonante + i + vocal con tilde: la i se absorbe en la\n"
    "    consonante  (pió \u2192 p' o,  kiú \u2192 k' M,  nió \u2192 J o)\n"
    "\n"
    "Con mayúsculas (Bloq Mayús o Shift) algunas letras cambian:\n"
    "\n"
    "  U  sale siempre como M, nunca como w, aunque vaya\n"
    "      junto a otra vocal.\n"
    "      cuando \u2192 k w a n d o        CUANDO \u2192 k M a n d o\n"
    "\n"
    "  I  sale siempre como la vocal i, nunca como j, aunque\n"
    "      forme diptongo. Útil cuando la j no suena bien.\n"
    "      baile \u2192 b a j 4 e        baIle \u2192 b a i 4 e\n"
    "      tiene \u2192 t j e n e        tIene \u2192 t i e n e\n"
    "\n"
    "  A E O U  (la última vocal) tras consonante + i: la i se absorbe\n"
    "      en la consonante, que lleva apóstrofe. Igual que con tilde.\n"
    "      piO \u2192 p' o        kiU \u2192 k' M        niO \u2192 J o\n"
    "      Sin cambio con f (p\\) ni con consonantes sin versión con\n"
    "      apóstrofe (siO \u2192 s j o). Con minúscula sin tilde, normal:\n"
    "      kiu \u2192 k j M\n"
    "\n"
    "  J  (y la G de gi) ante la i sale más fuerte: C en lugar\n"
    "      de h; y ante la U, p\\ M en lugar de h M. Ante a, e, o\n"
    "      sigue siendo h.\n"
    "      jin \u2192 h i n        JIN \u2192 C i n\n"
    "      jun \u2192 h M n        JUN \u2192 p\\ M n\n"
    "      ja \u2192 h a           JA \u2192 h a\n"
    "\n"
    "  R  sale como rr (4 4 en lugar de 4), para que suene\n"
    "      fuerte. Es lo mismo que escribir rr.\n"
    "      ro \u2192 4 o        RO \u2192 4 4 o\n"
    "      mar \u2192 m a 4        maR \u2192 m a 4 4\n"
    "\n"
    "  RR  dos R mayúsculas juntas dan cuatro 4 (4 4 4 4): una erre\n"
    "      fuertemente pronunciada, más marcada que la R sola.\n"
    "      RO \u2192 4 4 o        RRO \u2192 4 4 4 4 o\n"
    "      pero \u2192 p e 4 o        peRRo \u2192 p e 4 4 4 4 o\n"
    "\n"
    "  C  ante e o i (Ce, Ci) cambia igual que la Z, seg\u00fan el esquema\n"
    "      elegido en la ventana (ver Z, m\u00e1s abajo). La c min\u00fascula\n"
    "      ante e / i siempre da s. Ante a, o, u sigue siendo k, y Ch\n"
    "      sigue siendo tS.\n"
    "      Con z \u2192 s,  Z / C \u2192 dz:   ce \u2192 s e   Ce \u2192 dz e   Ci \u2192 dz i\n"
    "      Con z \u2192 s,  Z / C \u2192 ts:   ce \u2192 s e   Ce \u2192 ts e   Ci \u2192 ts i\n"
    "      Con z \u2192 s,  Z / C \u2192 z:    ce \u2192 s e   Ce \u2192 z e    Ci \u2192 z i\n"
    "      ca \u2192 k a        Ca \u2192 k a\n"
    "\n"
    "  Y  al inicio de una sílaba (ante vocal) sale siempre como j,\n"
    "      sea cual sea el sonido de ll / y elegido en la ventana.\n"
    "      Con ll / y \u2192 Z:   yo \u2192 Z o        YO \u2192 j o\n"
    "      Con ll / y \u2192 S:   yo \u2192 S o        YO \u2192 j o\n"
    "      Con ll / y \u2192 j:   yo \u2192 j o        YO \u2192 j o\n"
    "      Al final de la sílaba (hoy, rey) la Y no cambia.\n"
    "\n"
    "  Z  cambia a su variante, y con ella la C de Ce / Ci. En la\n"
    "      ventana se elige entre tres esquemas:\n"
    "\n"
    "      z \u2192 s,  Z / C \u2192 dz   (predeterminado)\n"
    "        La s sorda (\u3055) es el sonido real de la z espa\u00f1ola, y se\n"
    "        mantiene con la z min\u00fascula. La Z may\u00fascula (y la C de\n"
    "        Ce, Ci) da la dz, con un golpe de \"d\" antes: ataque m\u00e1s\n"
    "        marcado, \u00fatil a principio de palabra o tras una pausa.\n"
    "        za \u2192 s a        ZA \u2192 dz a        Ce \u2192 dz e\n"
    "\n"
    "      z \u2192 s,  Z / C \u2192 ts\n"
    "        La s sorda se mantiene con la z min\u00fascula. La Z may\u00fascula\n"
    "        (y la C de Ce, Ci) da la ts (\u3064), con un golpe de \"t\" antes:\n"
    "        ataque marcado como la dz, pero sorda, igual que la s.\n"
    "        \u00datil si la dz suena demasiado sonora.\n"
    "        za \u2192 s a        ZA \u2192 ts a        Ce \u2192 ts e\n"
    "\n"
    "      z \u2192 s,  Z / C \u2192 z\n"
    "        La s (\u3055) es el sonido real de la z espa\u00f1ola. La z\n"
    "        sonora (\u3056) suena m\u00e1s suave y \"zumbada\": \u00fatil si la s\n"
    "        suena seca o se pierde entre vocales. Tambi\u00e9n afecta a\n"
    "        la C de Ce, Ci.\n"
    "        za \u2192 s a        ZA \u2192 z a        Ce \u2192 z e\n"
    "\n"
    "Los ajustes (tecla de activación, sonido de ll / y,\n"
    "esquema de z / C, tema, ventana siempre visible y bandeja) se\n"
    "guardan en config.json, en la misma carpeta que el\n"
    "programa.\n"
    "\n"
    "El botón Restaurar predeterminados vuelve a: tecla F9,\n"
    "ll / y \u2192 Z, z \u2192 s / Z, C \u2192 dz, ventana no siempre\n"
    "visible, envío a la bandeja al cerrar, tema Clásico e inicio\n"
    "con Windows desactivado.\n"
    "\n"
    "El icono del programa está siempre en la bandeja del sistema\n"
    "(clic o doble clic para mostrar la ventana). Al cerrar la\n"
    "ventana el programa sigue ahí (se puede desactivar en la\n"
    "ventana). Para salir del todo: Archivo > Salir, el botón\n"
    "Salir o clic derecho en el icono de la bandeja > Salir.\n"
    "\n"
    "Iniciar con Windows (solo disponible si el icono de la\n"
    "bandeja está habilitado): crea una tarea programada que,\n"
    "al iniciar sesión, abre el programa en segundo plano (solo\n"
    "el icono de la bandeja) y con la conversión desactivada.\n"
    "Se activa o desactiva con su casilla en la ventana y hace\n"
    "falta ejecutar el programa como administrador.\n"
    "\n"
    "Solo se puede abrir una copia del programa: si lo abres de\n"
    "nuevo, se muestra la ventana de la copia que ya está abierta.\n"
    "\n"
    "Fonemas del VOCALOID japonés:\n"
    "    a i M e o\n"
    "    k g s S z dz Z dZ t ts tS d n J h C p\\ p b m j 4 w N"
)


# ----------------------------------------------------------------------------
# Temas de la ventana
# ----------------------------------------------------------------------------
# Cada tema define: fondo (bg), paneles (panel), texto (fg, fg2 = texto suave),
# campos de texto (campo, campo_fg, campo_ro), botones (boton, boton_fg), colores de
# acento (acento y acento_fg para texto sobre el acento, acento2 para la franja superior)
# y la barra de titulo (barra, barra_fg; solo Windows 11). "oscuro" activa el modo
# oscuro de la barra de titulo. El tema "clasico" no cambia nada: restaura el aspecto
# original de la ventana (los valores de abajo son de relleno).
TEMAS = {
    "clasico": {
        "nombre": "Clásico", "clasico": True, "oscuro": False,
        "bg": "#f0f0f0", "panel": "#f0f0f0", "fg": "#000000", "fg2": "#666666",
        "campo": "#ffffff", "campo_fg": "#000000", "campo_ro": "#f0f0f0",
        "boton": "#f0f0f0", "boton_fg": "#000000",
        "acento": "#0078d7", "acento_fg": "#ffffff", "acento2": "#0078d7",
        "barra": None, "barra_fg": None,
    },
    # Basado en la interfaz de VOCALOID7: negro y grises oscuros, azul de seleccion.
    "vocaloid7": {
        "nombre": "VOCALOID7", "oscuro": True,
        "bg": "#141414", "panel": "#1e1e1e", "fg": "#e6e6e6", "fg2": "#8e8e8e",
        "campo": "#000000", "campo_fg": "#ffffff", "campo_ro": "#0b0b0b",
        "boton": "#2c2c2c", "boton_fg": "#e6e6e6",
        "acento": "#1673c2", "acento_fg": "#ffffff", "acento2": "#0f5a9e",
        "barra": "#000000", "barra_fg": "#ffffff",
    },
    # Voces de Crypton Future Media (colores de cada personaje).
    "miku": {            # turquesa 39C5BB + rosa E12885
        "nombre": "Hatsune Miku", "oscuro": True,
        "bg": "#0f2427", "panel": "#16363a", "fg": "#e8fffd", "fg2": "#8fc9c4",
        "campo": "#081a1c", "campo_fg": "#e8fffd", "campo_ro": "#0c2427",
        "boton": "#1f4a4e", "boton_fg": "#e8fffd",
        "acento": "#39c5bb", "acento_fg": "#06201f", "acento2": "#e12885",
        "barra": "#0a1c1e", "barra_fg": "#e8fffd",
    },
    "rin": {             # naranja FFA500 + amarillo
        "nombre": "Kagamine Rin", "oscuro": False,
        "bg": "#fff6e6", "panel": "#ffe9c4", "fg": "#3a2808", "fg2": "#7a5a20",
        "campo": "#ffffff", "campo_fg": "#3a2808", "campo_ro": "#fff0d6",
        "boton": "#ffd58a", "boton_fg": "#3a2808",
        "acento": "#ffa500", "acento_fg": "#2b1c00", "acento2": "#ffe04a",
        "barra": "#ffb52e", "barra_fg": "#2b1c00",
    },
    "len": {             # amarillo banana FFE211 + negro + blanco (su ropa y sus auriculares)
        "nombre": "Kagamine Len", "oscuro": True,
        "bg": "#14130a", "panel": "#24210d", "fg": "#fff6c9", "fg2": "#c9bc6a",
        "campo": "#0b0a05", "campo_fg": "#fff6c9", "campo_ro": "#12100a",
        "boton": "#d9bf10", "boton_fg": "#14120a",
        "acento": "#ffe211", "acento_fg": "#14120a", "acento2": "#ffffff",
        "barra": "#ffe211", "barra_fg": "#14120a",
    },
    "luka": {            # rosa FFBACC + dorado
        "nombre": "Megurine Luka", "oscuro": False,
        "bg": "#fff3f7", "panel": "#ffdfe9", "fg": "#4a1d2e", "fg2": "#8a4f67",
        "campo": "#ffffff", "campo_fg": "#4a1d2e", "campo_ro": "#ffe9f0",
        "boton": "#ffbacc", "boton_fg": "#4a1d2e",
        "acento": "#c8416b", "acento_fg": "#ffffff", "acento2": "#e0ae3d",
        "barra": "#ffbacc", "barra_fg": "#4a1d2e",
    },
    "meiko": {           # rojo D80000 + marron
        "nombre": "MEIKO", "oscuro": True,
        "bg": "#1d0f0f", "panel": "#2c1717", "fg": "#ffecec", "fg2": "#c79a9a",
        "campo": "#130909", "campo_fg": "#ffecec", "campo_ro": "#170c0c",
        "boton": "#4a2222", "boton_fg": "#ffecec",
        "acento": "#d80000", "acento_fg": "#ffffff", "acento2": "#9c6b45",
        "barra": "#120707", "barra_fg": "#ffecec",
    },
    "kaito": {           # azul + blanco
        "nombre": "KAITO", "oscuro": False,
        "bg": "#eef3ff", "panel": "#dbe6ff", "fg": "#0c1a4f", "fg2": "#4a5a90",
        "campo": "#ffffff", "campo_fg": "#0c1a4f", "campo_ro": "#e6edff",
        "boton": "#bcd0ff", "boton_fg": "#0c1a4f",
        "acento": "#1f3cf0", "acento_fg": "#ffffff", "acento2": "#8fb4ff",
        "barra": "#1f3cf0", "barra_fg": "#ffffff",
    },
}
ORDEN_TEMAS_BASE = ("clasico", "vocaloid7", None, "miku", "rin", "len", "luka", "meiko", "kaito")


def mezclar(a, b, t):
    """Mezcla dos colores #rrggbb (t = 0 da a, t = 1 da b)."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


# ----------------------------------------------------------------------------
# Temas de banderas: uno por cada pais de habla hispana
# ----------------------------------------------------------------------------
# Cada tema lleva "bandera": una miniatura de la bandera que se dibuja como franja
# en la parte superior de la ventana. Es una lista de filas (de arriba abajo); cada
# fila es una lista de (color, ancho relativo) de izquierda a derecha.
def _luminancia(h):
    def c(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)


def _contraste(a, b):
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _texto_sobre(fondo):
    """Blanco o casi negro, el que mejor se lea sobre 'fondo'."""
    return max(("#ffffff", "#111111"), key=lambda c: _contraste(c, fondo))


def _bandera(nombre, filas, oscuro, bg, panel, fg, acento, acento2, barra):
    """Arma un tema completo a partir de unos pocos colores."""
    campo = mezclar(bg, "#000000", 0.45) if oscuro else "#ffffff"
    boton = mezclar(panel, acento, 0.3)
    return {
        "nombre": nombre, "oscuro": oscuro, "bandera": filas,
        "bg": bg, "panel": panel, "fg": fg, "fg2": mezclar(fg, panel, 0.25),
        "campo": campo, "campo_fg": fg, "campo_ro": mezclar(campo, panel, 0.4),
        "boton": boton,
        "boton_fg": fg if _contraste(fg, boton) >= 4.5 else _texto_sobre(boton),
        "acento": acento, "acento_fg": _texto_sobre(acento), "acento2": acento2,
        "barra": barra, "barra_fg": _texto_sobre(barra),
    }


_BL = "#ffffff"


def _h(*colores):          # franjas horizontales iguales, de arriba abajo
    return [[(c, 1)] for c in colores]


def _v(*colores):          # franjas verticales iguales, de izquierda a derecha
    return [[(c, 1) for c in colores]]


_CUBA_AZ, _CUBA_RJ = "#002a8f", "#cf142b"
_URU_AZ, _URU_SOL = "#0038a8", "#fcd116"

# clave: (nombre, bandera, oscuro, bg, panel, fg, acento, acento2, barra)
_PAISES = {
    "argentina": ("Argentina",
                  [[("#74acdf", 1)], [(_BL, 9), ("#f6b40e", 2), (_BL, 9)], [("#74acdf", 1)]],
                  False, "#f3f9fe", "#dcebf8", "#12324f", "#74acdf", "#f6b40e", "#74acdf"),
    "bolivia": ("Bolivia", _h("#d52b1e", "#f9e300", "#007934"),
                True, "#0e1f13", "#16301d", "#f6f3d8", "#f9e300", "#d52b1e", "#007934"),
    "chile": ("Chile", [[("#0039a6", 1), (_BL, 2)], [("#d52b1e", 1)]],
              False, "#f3f6fc", "#dfe7f7", "#0b1f4f", "#0039a6", "#d52b1e", "#0039a6"),
    "colombia": ("Colombia", _h("#fcd116", "#fcd116", "#003893", "#ce1126"),
                 True, "#0c1a3a", "#142a5a", "#fff6cf", "#fcd116", "#ce1126", "#003893"),
    "costa_rica": ("Costa Rica", _h("#002b7f", _BL, "#ce1126", "#ce1126", _BL, "#002b7f"),
                   True, "#0b1c44", "#122b6a", "#f4f6ff", "#ce1126", "#ffffff", "#002b7f"),
    "cuba": ("Cuba",
             [[(_CUBA_RJ, k), (c, 10 - k)]
              for c, k in ((_CUBA_AZ, 1), (_BL, 2), (_CUBA_AZ, 3), (_BL, 2), (_CUBA_AZ, 1))],
             False, "#f5f7fd", "#e0e6f5", "#0a1b4d", "#cf142b", "#002a8f", "#002a8f"),
    "ecuador": ("Ecuador", _h("#ffdd00", "#ffdd00", "#034ea2", "#ed1c24"),
                False, "#fffbe0", "#fff0a8", "#2b2400", "#034ea2", "#ed1c24", "#ffdd00"),
    "el_salvador": ("El Salvador", _h("#0f47af", _BL, "#0f47af"),
                    True, "#0b1a45", "#12296b", "#eef2ff", "#2f66cf", "#ffffff", "#0f47af"),
    "espana": ("España", _h("#aa151b", "#f1bf00", "#f1bf00", "#aa151b"),
               True, "#2a0b0d", "#3d1216", "#fff3c4", "#f1bf00", "#aa151b", "#aa151b"),
    "guatemala": ("Guatemala", _v("#4997d0", _BL, "#4997d0"),
                  True, "#0d2231", "#14354c", "#eaf6ff", "#4997d0", "#ffffff", "#4997d0"),
    "guinea_ecuatorial": ("Guinea Ecuatorial",
                          [[("#0073ce", 1), ("#3e9a00", 9)], [("#0073ce", 2), (_BL, 8)],
                           [("#0073ce", 1), ("#e32118", 9)]],
                          False, "#f1f8ec", "#dcefd0", "#143012", "#3e9a00", "#e32118", "#3e9a00"),
    "honduras": ("Honduras", _h("#0073cf", _BL, "#0073cf"),
                 True, "#071f3a", "#0e3560", "#eef6ff", "#0073cf", "#ffffff", "#0073cf"),
    "mexico": ("México", _v("#006847", _BL, "#ce1126"),
               False, "#faf7f2", "#efe9dc", "#1f3a2a", "#006847", "#ce1126", "#006847"),
    "nicaragua": ("Nicaragua", _h("#0067c6", _BL, "#0067c6"),
                  False, "#f1f7fd", "#d9e8f8", "#0b2a52", "#0067c6", "#ffffff", "#0067c6"),
    "panama": ("Panamá", [[(_BL, 1), ("#d21034", 1)], [("#072357", 1), (_BL, 1)]],
               False, "#f7f9fc", "#e5eaf3", "#0b1d44", "#d21034", "#072357", "#072357"),
    "paraguay": ("Paraguay", _h("#d52b1e", _BL, "#0038a8"),
                 False, "#fff4f2", "#fbdcd8", "#3a0f0c", "#0038a8", "#d52b1e", "#d52b1e"),
    "peru": ("Perú", _v("#d91023", _BL, "#d91023"),
             False, "#ffffff", "#f1f1f1", "#2b0a0f", "#d91023", "#ffffff", "#d91023"),
    "puerto_rico": ("Puerto Rico",
                    [[("#0050f0", k), (c, 10 - k)]
                     for c, k in (("#ed0000", 1), (_BL, 2), ("#ed0000", 3), (_BL, 2), ("#ed0000", 1))],
                    True, "#081a4a", "#102a70", "#f4f7ff", "#ed0000", "#ffffff", "#0050f0"),
    "republica_dominicana": ("República Dominicana",
                             [[("#002d62", 5), (_BL, 1), ("#ce1126", 5)], [(_BL, 1)],
                              [("#ce1126", 5), (_BL, 1), ("#002d62", 5)]],
                             False, "#f7f8fc", "#e4e8f4", "#0b1c44", "#002d62", "#ce1126", "#002d62"),
    "uruguay": ("Uruguay",
                [[(_BL, 1)], [(_BL, 1), (_URU_SOL, 2), (_BL, 1), (_URU_AZ, 12)],
                 [(_BL, 1), (_URU_SOL, 2), (_BL, 1), (_BL, 12)], [(_BL, 4), (_URU_AZ, 12)],
                 [(_BL, 1)], [(_URU_AZ, 1)], [(_BL, 1)], [(_URU_AZ, 1)], [(_BL, 1)]],
                False, "#f6f9ff", "#e3ecfb", "#0a2a6b", "#0038a8", "#fcd116", "#0038a8"),
    "venezuela": ("Venezuela", _h("#ffcc00", "#00247d", "#cf142b"),
                  True, "#1c1a0a", "#2d2910", "#fff8d0", "#ffcc00", "#cf142b", "#00247d"),
}
for _clave, _datos in _PAISES.items():
    TEMAS[_clave] = _bandera(*_datos)

# Menu: Clasico, VOCALOID7 | voces de Crypton | paises (orden alfabetico, sin tildes)
ORDEN_TEMAS = (ORDEN_TEMAS_BASE + (None,)
               + tuple(sorted(_PAISES, key=lambda k: normalizar(TEMAS[k]["nombre"]))))


def paleta(clave):
    """Colores completos del tema (con los derivados)."""
    t = dict(TEMAS.get(clave, TEMAS["clasico"]))
    t.setdefault("clasico", False)
    t["foco"] = t["acento"]
    t["boton_hover"] = mezclar(t["boton"], t["acento"], 0.35)
    t["borde"] = mezclar(t["panel"], t["fg"], 0.22)
    return t


def barra_titulo(t, hwnd=None):
    """Colorea la barra de titulo de una ventana (oscura / color del tema); por defecto,
    la principal. El modo oscuro funciona en Windows 10 (2004+) y 11; el color propio, en
    Windows 11. En versiones que no lo admiten no hace nada."""
    hwnd = hwnd or HWND_PROPIA
    if not hwnd:
        return
    try:
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                              ctypes.c_void_p, ctypes.c_uint]

        def rgb(h):                                   # COLORREF = 0x00BBGGRR
            return ctypes.c_uint(int(h[5:7], 16) << 16 | int(h[3:5], 16) << 8 | int(h[1:3], 16))

        oscuro = ctypes.c_int(1 if t["oscuro"] else 0)
        for atributo in (20, 19):                     # DWMWA_USE_IMMERSIVE_DARK_MODE
            if dwm.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(oscuro), 4) == 0:
                break
        if t["barra"]:
            color, texto = rgb(t["barra"]), rgb(t["barra_fg"])
        else:
            color = texto = ctypes.c_uint(0xFFFFFFFF)  # DWMWA_COLOR_DEFAULT
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), 4)   # DWMWA_CAPTION_COLOR
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(texto), 4)   # DWMWA_TEXT_COLOR
        # SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
    except Exception:
        pass


class Ventana:
    def __init__(self):
        global HWND_PROPIA
        self.root = r = tk.Tk()
        r.title("Esp2XSAMPA")
        if INICIO_SILENCIOSO:
            r.withdraw()                   # arranque automatico: solo el icono de la bandeja
        r.resizable(False, False)
        r.protocol("WM_DELETE_WINDOW", self.al_cerrar)

        self.var_activo = tk.BooleanVar(value=estado.activo)
        self.var_ll = tk.StringVar(value=YEISMO)
        self.var_zeta = tk.StringVar(value=ZETA)
        self.var_top = tk.BooleanVar(value=config["visible"])
        self.var_texto_activo = tk.StringVar()
        self.var_bandeja = tk.BooleanVar(value=config["bandeja"] and HAY_BANDEJA)
        # Inicio con Windows: solo disponible con el icono de la bandeja
        # Desactivado por defecto: solo esta activo si el ajuste "inicio" (config.json) lo dice
        # y existe la tarea. Una tarea sin ese ajuste (o sin icono de bandeja) se elimina.
        existe = inicio_existe()
        activo_inicio = bool(config["inicio"]) and HAY_BANDEJA and existe
        if existe and not activo_inicio:
            inicio_desactivar()
        elif activo_inicio and config["inicio_ruta"] != firma_inicio():
            activo_inicio = inicio_activar()[0]    # el programa cambio de lugar: se actualiza
        config["inicio"] = activo_inicio
        self.var_inicio = tk.BooleanVar(value=activo_inicio)
        self.acciones = queue.Queue()      # pedidos del icono de la bandeja
        self.icono = None
        self._activo_icono = None
        self.var_entrada = tk.StringVar()
        self.var_salida = tk.StringVar()

        self.var_tema = tk.StringVar(value=config["tema"])
        self.win_ayuda = None              # ventana de Atajos y fonemas (si esta abierta)
        self._hwnd_ayuda = None
        self._tema_ttk_orig = ttk.Style(r).theme_use()   # para devolver la barra de desplazamiento al estilo nativo
        self.menus = []                    # todos los menus desplegables (para los temas)
        self._orig = {}                    # opciones originales de cada widget (tema clasico)
        entradas = (("Archivo", self._llenar_archivo), ("Tema", self._llenar_tema),
                    ("Ayuda", self._llenar_ayuda))

        # Menú nativo (tema clásico)
        barra = tk.Menu(r)
        for texto, llenar in entradas:
            sub = self._nuevo_menu(barra)
            llenar(sub)
            barra.add_cascade(label=texto, menu=sub)
        self.barra_nativa = barra

        # Menú propio (temas de color: la barra nativa de Windows no admite colores)
        # franja de acento (o bandera) arriba de todo: un Canvas que se repinta solo
        self.franja = tk.Canvas(r, height=4, bd=0, highlightthickness=0)
        self.franja_linea = tk.Frame(r, height=1)      # filete bajo la bandera
        self.barra_custom = tk.Frame(r)
        self.botones_menu = []
        for texto, llenar in entradas:
            mb = tk.Menubutton(self.barra_custom, text=texto, bd=0, padx=10, pady=4,
                               highlightthickness=0)
            sub = self._nuevo_menu(mb)
            llenar(sub)
            mb.config(menu=sub)
            mb.pack(side="left")
            self.botones_menu.append(mb)

        self.marco = marco = tk.Frame(r, padx=8, pady=6)
        marco.pack(fill="both", expand=True)

        # Estado
        f1 = tk.LabelFrame(marco, text="Estado", padx=6, pady=3)
        f1.pack(fill="x")
        tk.Checkbutton(f1, textvariable=self.var_texto_activo, variable=self.var_activo,
                       command=self.cambiar_activo).pack(anchor="w")
        tk.Checkbutton(f1, text="Mantener ventana siempre visible", variable=self.var_top,
                       command=self.cambiar_top).pack(anchor="w")
        self.chk_bandeja = tk.Checkbutton(f1, text="Al cerrar, enviar a la bandeja del sistema",
                                          variable=self.var_bandeja, command=self.cambiar_bandeja)
        self.chk_bandeja.pack(anchor="w")
        if not HAY_BANDEJA:
            self.chk_bandeja.config(state="disabled")
        self.chk_inicio = tk.Checkbutton(f1, text="Iniciar con Windows en segundo plano, sin conversión",
                                         variable=self.var_inicio, command=self.cambiar_inicio)
        self.chk_inicio.pack(anchor="w")
        if not HAY_BANDEJA:
            self.chk_inicio.config(state="disabled")

        # Tecla de activación
        fk = tk.LabelFrame(marco, text="Tecla de activación", padx=6, pady=3)
        fk.pack(fill="x", pady=(4, 0))
        self.lbl_tecla = tk.Label(fk, width=28, anchor="w", relief="sunken", bd=1)
        self.lbl_tecla.pack(side="left")
        self.btn_tecla = tk.Button(fk, text="Cambiar\u2026", width=9, command=self.cambiar_tecla)
        self.btn_tecla.pack(side="left", padx=4)
        tk.Button(fk, text="F9", width=4, command=self.tecla_predeterminada).pack(side="left")

        # ll / y
        f2 = tk.LabelFrame(marco, text="Sonido de ll / y", padx=6, pady=3)
        f2.pack(fill="x", pady=4)
        for texto, valor in (("Z  (zheísmo)", "Z"), ("S  (sheísmo)", "S"), ("j  (yeísmo)", "j")):
            tk.Radiobutton(f2, text=texto, value=valor, variable=self.var_ll,
                           command=self.cambiar_ll).pack(side="left")

        # z / Z  (y c / C ante e, i)
        f2z = tk.LabelFrame(marco, text="Sonido de z / c  (minúscula / MAYÚSCULA)", padx=6, pady=3)
        f2z.pack(fill="x", pady=(0, 4))
        for texto, valor in (("z → s,  Z / C → dz", "sdz"), ("z → s,  Z / C → ts", "sts"), ("z → s,  Z / C → z", "sz")):
            tk.Radiobutton(f2z, text=texto, value=valor, variable=self.var_zeta,
                           command=self.cambiar_zeta).pack(side="left", padx=(0, 10))

        # Prueba
        f3 = tk.LabelFrame(marco, text="Prueba", padx=6, pady=3)
        f3.pack(fill="x")
        tk.Entry(f3, textvariable=self.var_entrada, width=36).pack(fill="x")
        tk.Entry(f3, textvariable=self.var_salida, state="readonly", width=36).pack(fill="x", pady=(4, 0))
        tk.Button(f3, text="Copiar", width=8, command=self.copiar).pack(anchor="e", pady=(4, 0))
        self.var_entrada.trace_add("write", lambda *a: self.actualizar())

        # Pie
        pie = tk.Frame(marco)
        pie.pack(fill="x", pady=(6, 0))
        self.lbl_pie = tk.Label(pie, text="Ctrl+Alt+Q: salir", fg="gray40")
        self.lbl_pie.pack(side="left")
        tk.Button(pie, text="Salir", width=8, command=self.salir_definitivo).pack(side="right")
        tk.Button(pie, text="Restaurar predeterminados", command=self.restaurar).pack(side="right", padx=4)

        if HAY_PIL:                         # icono de la ventana y de la barra de tareas
            try:
                buf = io.BytesIO()
                dibujar_icono(64).save(buf, format="PNG")
                self._img_icono = tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
                r.iconphoto(True, self._img_icono)
            except Exception:
                pass

        r.attributes("-topmost", config["visible"])
        self.refrescar_tecla()
        r.update_idletasks()
        HWND_PROPIA = user32.GetParent(r.winfo_id())
        VENTANAS_PROPIAS.add(HWND_PROPIA)
        self.aplicar_tema()

    # --- menus y temas ---
    def _nuevo_menu(self, padre):
        m = tk.Menu(padre, tearoff=0)
        self.menus.append(m)
        return m

    def _llenar_archivo(self, m):
        m.add_command(label="Salir", command=self.salir_definitivo)

    def _llenar_tema(self, m):
        for clave in ORDEN_TEMAS:
            if clave is None:
                m.add_separator()
            else:
                m.add_radiobutton(label=TEMAS[clave]["nombre"], variable=self.var_tema,
                                  value=clave, command=self.cambiar_tema)

    def _llenar_ayuda(self, m):
        m.add_command(label="Atajos y fonemas", command=self.ayuda)
        m.add_separator()
        m.add_command(label="Creado por Liper", state="disabled")     # solo creditos

    def _aplicar(self, w, opciones, t):
        """Aplica opciones de color a un widget. La primera vez recuerda los valores
        originales: el tema clasico los restaura tal cual (aspecto original exacto)."""
        orig = self._orig.setdefault(w, {})
        for k in opciones:
            if k not in orig:
                orig[k] = w.cget(k)
        w.config(**({k: orig[k] for k in opciones} if t["clasico"] else opciones))

    def _tema_hijos(self, padre, t, fondo):
        for w in padre.winfo_children():
            c = w.winfo_class()
            if c == "Labelframe":
                self._aplicar(w, {"bg": t["panel"], "fg": t["fg"]}, t)
                self._tema_hijos(w, t, t["panel"])
            elif c == "Frame":
                self._aplicar(w, {"bg": fondo}, t)
                self._tema_hijos(w, t, fondo)
            elif c == "Label":
                if w is self.lbl_tecla:                    # campo con la tecla actual
                    op = {"bg": t["campo"], "fg": t["campo_fg"], "relief": "flat",
                          "highlightthickness": 1, "highlightbackground": t["borde"],
                          "highlightcolor": t["borde"]}
                elif w is self.lbl_pie:
                    op = {"bg": fondo, "fg": t["fg2"]}
                else:
                    op = {"bg": fondo, "fg": t["fg"]}
                self._aplicar(w, op, t)
            elif c == "Button":
                self._aplicar(w, {"bg": t["boton"], "fg": t["boton_fg"],
                                  "activebackground": t["boton_hover"],
                                  "activeforeground": t["boton_fg"], "relief": "flat", "bd": 1,
                                  "padx": 8, "pady": 2, "cursor": "hand2",
                                  "highlightthickness": 1, "highlightbackground": t["borde"],
                                  "highlightcolor": t["foco"]}, t)
            elif c in ("Checkbutton", "Radiobutton"):
                self._aplicar(w, {"bg": fondo, "fg": t["fg"], "activebackground": fondo,
                                  "activeforeground": t["fg"], "selectcolor": t["campo"],
                                  "disabledforeground": t["fg2"], "highlightbackground": fondo,
                                  "highlightcolor": t["foco"]}, t)
            elif c == "Entry":
                self._aplicar(w, {"bg": t["campo"], "fg": t["campo_fg"],
                                  "insertbackground": t["campo_fg"],
                                  "selectbackground": t["acento"],
                                  "selectforeground": t["acento_fg"],
                                  "readonlybackground": t["campo_ro"],
                                  "disabledbackground": t["campo_ro"],
                                  "disabledforeground": t["fg2"], "relief": "flat", "bd": 3,
                                  "highlightthickness": 1, "highlightbackground": t["borde"],
                                  "highlightcolor": t["foco"]}, t)

    def aplicar_tema(self):
        t = paleta(config["tema"])
        r = self.root
        self._aplicar(r, {"bg": t["bg"]}, t)
        self._aplicar(self.marco, {"bg": t["bg"]}, t)
        self._tema_hijos(self.marco, t, t["bg"])
        for m in self.menus:
            self._aplicar(m, {"bg": t["panel"], "fg": t["fg"],
                              "activebackground": t["acento"],
                              "activeforeground": t["acento_fg"],
                              "selectcolor": t["fg"], "disabledforeground": t["fg2"]}, t)
        self.franja.pack_forget()
        self.franja_linea.pack_forget()
        self.barra_custom.pack_forget()
        if t["clasico"]:
            r.config(menu=self.barra_nativa)
        else:
            r.config(menu="")
            self.dibujar_franja(t)
            self.franja_linea.config(bg=t["borde"])
            self.barra_custom.config(bg=t["panel"])
            for mb in self.botones_menu:
                mb.config(bg=t["panel"], fg=t["fg"], activebackground=t["acento"],
                          activeforeground=t["acento_fg"])
            self.franja.pack(fill="x", side="top", before=self.marco)
            if t.get("bandera"):
                self.franja_linea.pack(fill="x", side="top", before=self.marco)
            self.barra_custom.pack(fill="x", side="top", before=self.marco)
        barra_titulo(t)
        r.update_idletasks()
        self._tema_ayuda()

    def dibujar_franja(self, t):
        self._franja_en(self.franja, t)

    def _franja_en(self, franja, t):
        """Franja superior: la bandera del pais (temas de banderas) o dos tramos de acento.
        Se dibuja sobre un Canvas con rectangulos y se repinta cada vez que cambia su tamano
        o se muestra (antes eran marcos anidados, que a veces quedaban sin tamano y no se veian).
        Se usa en la ventana principal y en la de ayuda."""
        bandera = t.get("bandera")
        franja._filas = bandera or [[(t["acento"], 3), (t["acento2"], 1)]]
        franja.config(bg=franja._filas[0][0][0],
                      height=min(18, max(12, 3 * len(franja._filas))) if bandera else 4)
        if not getattr(franja, "_enlazada", False):
            franja._enlazada = True
            franja.bind("<Configure>", lambda e, f=franja: self._pintar_franja(f))
            franja.bind("<Map>", lambda e, f=franja: self._pintar_franja(f))
        self._pintar_franja(franja)

    @staticmethod
    def _pintar_franja(franja):
        ancho, alto = franja.winfo_width(), franja.winfo_height()
        if ancho <= 1 or alto <= 1:        # aun sin tamano real: el evento Configure la repintara
            return
        filas = franja._filas
        franja.delete("all")
        for i, fila in enumerate(filas):
            y0, y1 = round(i * alto / len(filas)), round((i + 1) * alto / len(filas))
            total, acum, x0 = sum(p for _, p in fila), 0, 0
            for color, peso in fila:
                acum += peso
                x1 = round(ancho * acum / total)
                franja.create_rectangle(x0, y0, x1, y1, fill=color, outline="", width=0)
                x0 = x1

    def cambiar_tema(self):
        config["tema"] = self.var_tema.get()
        self.aplicar_tema()
        guardar_config()

    # --- acciones ---
    def cambiar_activo(self):
        fijar_activo(self.var_activo.get())

    def cambiar_top(self):
        config["visible"] = self.var_top.get()
        self.root.attributes("-topmost", config["visible"])
        self._topmost_ayuda()
        guardar_config()

    def cambiar_tecla(self):
        captura.mensaje = ""
        captura.activa = not captura.activa

    def tecla_predeterminada(self):
        captura.activa = False
        captura.mensaje = ""
        config["toggle"] = VK_F9
        guardar_config()

    def refrescar_tecla(self):
        if captura.activa:
            texto = captura.mensaje or "Pulsa una tecla  (Esc cancela)"
        else:
            texto = nombre_tecla(config["toggle"])
        if self.lbl_tecla.cget("text") != texto:
            self.lbl_tecla.config(text=texto)
        self.btn_tecla.config(text="Cancelar" if captura.activa else "Cambiar\u2026")
        etiqueta = "Conversión activada  (%s)" % nombre_tecla(config["toggle"])
        if self.var_texto_activo.get() != etiqueta:
            self.var_texto_activo.set(etiqueta)

    def cambiar_ll(self):
        global YEISMO
        YEISMO = self.var_ll.get()
        guardar_config()
        self.actualizar()

    def cambiar_zeta(self):
        global ZETA
        ZETA = self.var_zeta.get()
        guardar_config()
        self.actualizar()

    def restaurar(self):
        """Vuelve a la configuracion predeterminada (no cambia si la conversion esta activa)."""
        global YEISMO, ZETA
        if not messagebox.askyesno("Restaurar predeterminados",
                                   "¿Volver a la configuración predeterminada?",
                                   parent=self.root):
            return
        captura.activa = False
        captura.mensaje = ""
        config["toggle"] = VK_F9
        config["visible"] = False
        config["bandeja"] = True
        config["tema"] = "clasico"
        if self.var_inicio.get():
            ok, error = inicio_desactivar()
            self.var_inicio.set(not ok)
        YEISMO, ZETA = "Z", "sdz"
        self.var_ll.set(YEISMO)
        self.var_zeta.set(ZETA)
        self.var_top.set(False)
        self.var_bandeja.set(HAY_BANDEJA)
        self.var_tema.set("clasico")
        self.root.attributes("-topmost", False)
        self._topmost_ayuda()
        self.aplicar_tema()
        guardar_config()
        self.refrescar_tecla()
        self.actualizar()

    def actualizar(self):
        palabras = self.var_entrada.get().split()
        self.var_salida.set(" ".join(g2p(p) for p in palabras))

    def copiar(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.var_salida.get())

    # --- ventana de Atajos y fonemas (caja de texto con el estilo del tema) ---
    def ayuda(self):
        if self.win_ayuda is not None and self.win_ayuda.winfo_exists():
            self._poblar_ayuda()                     # ya abierta: se actualiza y se trae al frente
            self.win_ayuda.deiconify()
            self.win_ayuda.lift()
            self.win_ayuda.focus_force()
            return
        r = self.root
        w = self.win_ayuda = tk.Toplevel(r)
        w.title("Atajos y fonemas")
        w.transient(r)
        w.minsize(460, 300)
        w.attributes("-topmost", config["visible"])
        w.protocol("WM_DELETE_WINDOW", self.cerrar_ayuda)
        w.bind("<Escape>", lambda e: self.cerrar_ayuda())

        self.ay_franja = tk.Canvas(w, height=4, bd=0, highlightthickness=0)
        self.ay_linea = tk.Frame(w, height=1)
        self.ay_cuerpo = tk.Frame(w, padx=8, pady=8)
        self.ay_cuerpo.pack(fill="both", expand=True)

        self.ay_caja = tk.Frame(self.ay_cuerpo, highlightthickness=1)    # borde del cuadro de texto
        self.ay_caja.pack(fill="both", expand=True)
        self.ay_scroll = ttk.Scrollbar(self.ay_caja, orient="vertical",
                                       style="Ayuda.Vertical.TScrollbar")
        self.ay_scroll.pack(side="right", fill="y")
        self.fuente_ayuda = tkfont.Font(root=r, family="Consolas", size=10)
        self.fuente_ayuda_neg = tkfont.Font(root=r, family="Consolas", size=10, weight="bold")
        ancho = max(len(l) for l in TEXTO_AYUDA.split("\n")) + 2
        self.ay_texto = tk.Text(self.ay_caja, wrap="word", width=min(ancho, 80), height=28,
                                relief="flat", bd=0, padx=14, pady=10, cursor="arrow",
                                font=self.fuente_ayuda, spacing1=1, spacing3=1,
                                yscrollcommand=self.ay_scroll.set)
        self.ay_scroll.config(command=self.ay_texto.yview)
        self.ay_texto.pack(side="left", fill="both", expand=True)
        self.ay_texto.bind("<Button-1>", lambda e: self.ay_texto.focus_set())

        pie = tk.Frame(self.ay_cuerpo)
        pie.pack(fill="x", pady=(8, 0))
        self.ay_pie_lbl = tk.Label(pie, text="Esc: cerrar")
        self.ay_pie_lbl.pack(side="left")
        self.ay_cerrar = tk.Button(pie, text="Cerrar", width=9, command=self.cerrar_ayuda)
        self.ay_cerrar.pack(side="right")
        self.ay_pie = pie

        self._poblar_ayuda()
        self._tema_ayuda()
        w.update_idletasks()
        self._hwnd_ayuda = user32.GetParent(w.winfo_id())
        VENTANAS_PROPIAS.add(self._hwnd_ayuda)
        barra_titulo(paleta(config["tema"]), self._hwnd_ayuda)
        w.geometry("+%d+%d" % (r.winfo_x() + 40, r.winfo_y() + 40))
        self.ay_cerrar.focus_set()

    def _poblar_ayuda(self):
        """Escribe el texto de ayuda con formato: titulos, teclas (C U I J R RR Y Z) y flechas."""
        txt = self.ay_texto
        lineas = TEXTO_AYUDA.format(tecla=nombre_tecla(config["toggle"])).split("\n")
        txt.config(state="normal")
        txt.delete("1.0", "end")
        for i, linea in enumerate(lineas):
            n = i + 1
            txt.insert("end", linea + ("\n" if i < len(lineas) - 1 else ""))
            if re.match(r"^\S.*:$", linea):                          # encabezado de seccion
                txt.tag_add("titulo", "%d.0" % n, "%d.end" % n)
            if re.match(r"^ {6}[zZ] ", linea):                       # esquemas de la z
                txt.tag_add("sub", "%d.0" % n, "%d.end" % n)
            m = re.match(r"^(\s+)(RR|[CUIJRYZ])\s\s", linea)           # letra en mayuscula
            if m:
                c = len(m.group(1))
                txt.tag_add("tecla", "%d.%d" % (n, c), "%d.%d" % (n, c + len(m.group(2))))
            for m in re.finditer("\u2192", linea):
                txt.tag_add("flecha", "%d.%d" % (n, m.start()), "%d.%d" % (n, m.end()))
        txt.config(state="disabled")
        txt.yview_moveto(0)

    @staticmethod
    def _legible(fondo, color, destino, minimo=4.5):
        """Acerca 'color' a 'destino' hasta que se lea bien sobre 'fondo' (conserva el tono)."""
        for paso in range(11):
            c = mezclar(color, destino, paso / 10)
            if _contraste(c, fondo) >= minimo:
                return c
        return destino

    def _tema_ayuda(self):
        """Pinta la ventana de ayuda con el tema actual (igual que la ventana principal)."""
        w = self.win_ayuda
        if w is None or not w.winfo_exists():
            return
        t = paleta(config["tema"])
        self._aplicar(w, {"bg": t["bg"]}, t)
        self._aplicar(self.ay_cuerpo, {"bg": t["bg"]}, t)
        self._aplicar(self.ay_pie, {"bg": t["bg"]}, t)
        self._aplicar(self.ay_pie_lbl, {"bg": t["bg"], "fg": t["fg2"]}, t)
        self.ay_caja.config(bg=t["campo"], highlightbackground=t["borde"],
                            highlightcolor=t["borde"])
        self._aplicar(self.ay_texto, {"bg": t["campo"], "fg": t["campo_fg"],
                                      "insertbackground": t["campo_fg"],
                                      "selectbackground": t["acento"],
                                      "selectforeground": t["acento_fg"],
                                      "inactiveselectbackground": mezclar(t["campo"], t["acento"], 0.5)}, t)
        self._aplicar(self.ay_cerrar, {"bg": t["boton"], "fg": t["boton_fg"],
                                       "activebackground": t["boton_hover"],
                                       "activeforeground": t["boton_fg"], "relief": "flat", "bd": 1,
                                       "padx": 8, "pady": 2, "cursor": "hand2",
                                       "highlightthickness": 1, "highlightbackground": t["borde"],
                                       "highlightcolor": t["foco"]}, t)
        # colores de las etiquetas del texto (siempre legibles sobre el fondo del cuadro)
        titulo = self._legible(t["campo"], t["acento"], t["campo_fg"])
        self.ay_texto.tag_config("titulo", foreground=titulo, font=self.fuente_ayuda_neg,
                                 spacing1=8, spacing3=2)
        self.ay_texto.tag_config("flecha", foreground=titulo)
        self.ay_texto.tag_config("sub", font=self.fuente_ayuda_neg)
        self.ay_texto.tag_config("tecla", background=t["acento"], foreground=t["acento_fg"],
                                 font=self.fuente_ayuda_neg)
        self.ay_texto.tag_raise("sel")
        # barra de desplazamiento
        st = ttk.Style(self.root)
        if t["clasico"]:
            st.theme_use(self._tema_ttk_orig)
        else:
            st.theme_use("clam")
            st.configure("Ayuda.Vertical.TScrollbar", background=t["boton"],
                         troughcolor=t["campo"], bordercolor=t["campo"], lightcolor=t["boton"],
                         darkcolor=t["boton"], arrowcolor=t["boton_fg"], gripcount=0, relief="flat")
            st.map("Ayuda.Vertical.TScrollbar",
                   background=[("pressed", t["acento"]), ("active", t["boton_hover"])],
                   arrowcolor=[("pressed", t["acento_fg"])])
        # franja superior (acento o bandera), como en la ventana principal
        self.ay_franja.pack_forget()
        self.ay_linea.pack_forget()
        if not t["clasico"]:
            self._franja_en(self.ay_franja, t)
            self.ay_linea.config(bg=t["borde"])
            self.ay_franja.pack(fill="x", side="top", before=self.ay_cuerpo)
            if t.get("bandera"):
                self.ay_linea.pack(fill="x", side="top", before=self.ay_cuerpo)
        if self._hwnd_ayuda:
            barra_titulo(t, self._hwnd_ayuda)
        w.update_idletasks()

    def _topmost_ayuda(self):
        if self.win_ayuda is not None and self.win_ayuda.winfo_exists():
            self.win_ayuda.attributes("-topmost", config["visible"])

    def cerrar_ayuda(self):
        w = self.win_ayuda
        if w is None:
            return
        self.win_ayuda = None
        VENTANAS_PROPIAS.discard(self._hwnd_ayuda)
        self._hwnd_ayuda = None
        pila = [w]                                   # olvidar los widgets de esta ventana
        while pila:
            x = pila.pop()
            self._orig.pop(x, None)
            pila.extend(x.winfo_children())
        try:
            w.destroy()
        except Exception:
            pass

    def cambiar_inicio(self):
        quiere = self.var_inicio.get()
        ok, error = inicio_activar() if quiere else inicio_desactivar()
        if not ok:
            self.var_inicio.set(not quiere)
            messagebox.showerror(
                "Iniciar con Windows",
                "No se pudo %s el inicio con Windows.\n\n%s\n\n"
                "Prueba ejecutando el programa como administrador."
                % ("activar" if quiere else "desactivar", error), parent=self.root)

    def cambiar_bandeja(self):
        config["bandeja"] = self.var_bandeja.get()
        guardar_config()

    def al_cerrar(self):
        """Boton X de la ventana: a la bandeja o salir, segun el ajuste."""
        if config["bandeja"] and HAY_BANDEJA:
            self.ocultar()
        else:
            self.salir_definitivo()

    def ocultar(self):
        self.cerrar_ayuda()
        self.root.withdraw()
        self.mostrar_icono()

    def mostrar(self):
        self.root.deiconify()               # el icono de la bandeja se queda hasta salir
        self.root.lift()
        self.root.focus_force()

    def titulo_icono(self):
        return "Esp2XSAMPA - " + ("activo" if estado.activo else "desactivado")

    def mostrar_icono(self):
        if self.icono is not None:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Mostrar ventana", lambda icono, item: self.acciones.put("mostrar"),
                             default=True),
            pystray.MenuItem("Conversión activada", lambda icono, item: self.acciones.put("alternar"),
                             checked=lambda item: estado.activo),
            pystray.MenuItem("Salir", lambda icono, item: self.acciones.put("salir")),
        )
        self._activo_icono = estado.activo
        self.icono = pystray.Icon("Esp2XSAMPA", crear_icono(estado.activo), self.titulo_icono(), menu)
        self.icono.run_detached()

    def quitar_icono(self):
        if self.icono is not None:
            try:
                self.icono.stop()
            except Exception:
                pass
            self.icono = None

    def salir_definitivo(self):
        salir.set()
        self.quitar_icono()
        self.root.destroy()

    def refrescar(self):
        """Sincroniza casilla e icono con el estado, atiende la bandeja y Ctrl+Alt+Q."""
        if salir.is_set():
            self.quitar_icono()
            self.root.destroy()
            return
        while True:
            try:
                accion = self.acciones.get_nowait()
            except queue.Empty:
                break
            if accion == "mostrar":
                self.mostrar()
            elif accion == "alternar":
                fijar_activo(not estado.activo)
            elif accion == "salir":
                self.salir_definitivo()
                return
        if EVENTO_MOSTRAR and kernel32.WaitForSingleObject(EVENTO_MOSTRAR, 0) == 0:
            self.mostrar()                  # otra copia intento abrirse
        if self.var_activo.get() != estado.activo:
            self.var_activo.set(estado.activo)
        if self.icono is not None and self._activo_icono != estado.activo:
            self._activo_icono = estado.activo
            self.icono.icon = crear_icono(estado.activo)
            self.icono.title = self.titulo_icono()
            try:
                self.icono.update_menu()    # pystray solo recalcula el tilde al reconstruir el menu
            except Exception:
                pass
        self.refrescar_tecla()
        self.root.after(150, self.refrescar)

    def ejecutar(self):
        if HAY_BANDEJA:
            self.mostrar_icono()            # el icono de la bandeja esta siempre visible
        self.root.after(150, self.refrescar)
        self.root.mainloop()


def main():
    global listener
    if not instancia_unica(avisar=not INICIO_SILENCIOSO):   # ya hay otra copia: se sale
        return
    cargar_config()
    if INICIO_SILENCIOSO:
        estado.activo = False              # al iniciar la PC, la conversion arranca desactivada
    threading.Thread(target=trabajador, daemon=True).start()
    ventana = Ventana()
    ventana.root.update()
    teclas.caps = leer_caps_sistema()      # estado real de Bloq Mayus al arrancar
    listener = keyboard.Listener(win32_event_filter=filtro)
    listener.start()
    ventana.ejecutar()
    salir.set()
    listener.stop()


if __name__ == "__main__":
    main()
