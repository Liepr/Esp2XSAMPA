<div align="center">

<img src="assets/icon.png" alt="Icono de Esp2XSAMPA" width="128">

# Esp2XSAMPA

**Escribe en español, canta en español con VOCALOID japonés.** ♪

Convierte en vivo lo que tecleas en español a fonemas X-SAMPA que los voicebanks japoneses sí saben pronunciar.

🌐 **[Web oficial](https://esp2xsampa.nekoweb.org/)** · 📦 [Descargas](../../releases)

![Versión](https://img.shields.io/badge/versión-2.4-1f6feb)
![Licencia](https://img.shields.io/badge/licencia-GPL--3.0-2ea44f)
![Plataforma](https://img.shields.io/badge/Windows-0078d7?logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-3776ab?logo=python&logoColor=white)

</div>

---

## ✨ ¿Qué hace?

Mientras el programa está activo, lo que escribes (en español, sílaba por sílaba) se transforma al instante en fonemas X-SAMPA separados por espacios, usando **solo** los que acepta un VOCALOID japonés. Ideal para el *modo de símbolos fonéticos* del editor.

```
cuando  →  k w a n d o        CUANDO  →  k M a n d o
baile   →  b a j 4 e          baIle   →  b a i 4 e
ro      →  4 o                RO      →  4 4 o
jin     →  h i n              JIN     →  C i n
pió     →  p' o               kiU     →  k' M
```

## 🎹 Características

- **Conversión en vivo** en cualquier programa, sin pulsar nada más.
- **Tecla de activación configurable** (F1-F24, Pause, Insert, etc.). Por defecto, `F9`.
- **Variantes con mayúsculas** (Bloq Mayús o Shift): `U`, `I`, `J`, `G`, `R`, `Z`, `A`, `E`, `O` cambian el resultado.
- **Palatalización automática** con `i` (`ti` → `t' i`, `ni` → `J i`...) solo con pares que existen de verdad en los VOCALOID.
- **Ajustes de pronunciación:** `ll` / `y` (zheísmo, sheísmo o yeísmo) y dos esquemas para la `z`.
- **Bandeja del sistema**, instancia única e inicio opcional con Windows.
- **29 temas:** Clásico, VOCALOID7, voces de Crypton y banderas de países hispanohablantes.
- Ligero y portable: la configuración se guarda en `config.json`, junto al programa.

## 🚀 Uso rápido

1. Descarga el `.zip` desde [Releases](../../releases) y descomprímelo.
2. Ejecuta `Esp2XSAMPA.exe` (conviene como administrador).
3. En VOCALOID, activa el **modo de símbolos fonéticos** y pon una nota.
4. Pulsa `F9` y escribe tu sílaba en español. Se cierra con espacio, enter o tab.

| Atajo | Acción |
|---|---|
| `F9` (configurable) | Activar / desactivar la conversión |
| `Ctrl` + `Alt` + `Q` | Salir del programa |

## 🔤 Reglas principales

| Escribes | Sale | Nota |
|---|---|---|
| `r`, `l` | `4` | No existe `r` ni `l` en japonés |
| `rr`, `R` | `4 4` | Dos golpes: sonido fuerte |
| `u` | `M` | `U` fuerza `M` aunque forme diptongo |
| `f` | `p\` | La `f` no existe en japonés |
| `j`, `ge`, `gi` | `h` | `JI` → `C i`, `JU` → `p\ M` |
| `ñ` | `J` | |
| `ll`, `y` | `Z` (configurable) | `S` o `j` según dialecto |
| `ti`, `ki`, `pi`... | `t' i`, `k' i`, `p' i` | Palatalización ante `i` |
| `i` + vocal | `j` | `I` fuerza la vocal `i` |

### 🆕 Consonante + `i` + vocal tónica (v2.4)

Si la última vocal lleva tilde o va en mayúscula, la `i` se absorbe en la consonante, que recibe apóstrofe:

| Escribes | Sale |
|---|---|
| `kiu` | `k j M` *(sin cambios)* |
| `kíu` / `kIu` | `k' i M` |
| `pió` / `piO` | `p' o` |
| `kiú` / `kiU` | `k' M` |
| `nió` / `niO` | `J o` |

Excepciones: `f` (`p\`) y `C` no llevan apóstrofe, y las consonantes sin versión palatalizada (s, ch, etc.) mantienen el diptongo normal (`siO` → `s j o`).

## 🛠️ Ejecutar o compilar desde el código

Requiere **Windows** y **Python 3** (con *tcl/tk*).

```bash
pip install pynput pystray pillow
python Esp2XSAMPA.py
```

Para generar el `.exe`, deja `crear_exe.bat`, `Esp2XSAMPA.py` y `Esp2XSAMPA.ico` en la misma carpeta y haz doble clic en el `.bat`. El resultado queda en `dist\Esp2XSAMPA.exe`.

## 📝 Registro de cambios

Consulta el [changelog completo](CHANGELOG.md).

## ⚖️ Licencia

Esp2XSAMPA es software libre bajo la [GNU GPL v3](LICENSE). Puedes usarlo, modificarlo y compartirlo, pero toda versión modificada que distribuyas debe seguir siendo libre y con su código fuente disponible bajo la misma licencia.

Usa [pynput](https://github.com/moses-palmer/pynput) y [pystray](https://github.com/moses-palmer/pystray) (LGPL-3.0) y [Pillow](https://github.com/python-pillow/Pillow) (HPND).

---

<div align="center">

Creado por **Liper** · Copyright © 2026 · Herramienta de fans, sin relación con YAMAHA ni con los creadores de ningún voicebank. VOCALOID es marca de sus respectivos dueños.

</div>
