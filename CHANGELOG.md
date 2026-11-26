# Registro de cambios

## v2.6

### ✨ Novedades
- **Vuelve la opción «Sonido de z (minúscula / MAYÚSCULA)»**, ahora con tres esquemas:
  - `z → s`, `Z → dz` **(nuevo, predeterminado):** `za` → `s a`, `ZA` → `dz a`. La `s` sorda es el sonido real de la `z` española y la `Z` mayúscula da la `dz`, con un golpe de «d» antes: ataque más marcado, útil a principio de palabra o tras una pausa.
  - `z → s`, `Z → z` (el comportamiento de la v2.5): `za` → `s a`, `ZA` → `z a`.
  - `z → z`, `Z → dz`: `za` → `z a`, `ZA` → `dz a`.

### 🔧 Mejoras
- «Restaurar predeterminados» vuelve ahora a `z → s`, `Z → dz`.
- La opción se guarda en `config.json`. Si ya tenías guardado un esquema, se respeta; en instalaciones nuevas, o tras restaurar predeterminados, se usa el nuevo.
- El menú de ayuda («Atajos y fonemas») explica los tres esquemas de `Z`, con ejemplos.
- La página web actualiza el apartado "Un vistazo" para que funcione igual que esta versión, con las capturas de los 29 temas renovadas.

## v2.5

### ✨ Novedades
- **Erre fuerte con `RR`:** dos `R` mayúsculas juntas (Bloq Mayús o Shift) dan **cuatro** `4` en lugar de dos: una erre fuertemente pronunciada, más marcada que la `R` sola.
  - `RO` → `4 4 o`, `RRO` → `4 4 4 4 o`
  - `peRRo` → `p e 4 4 4 4 o`
  - Cada `R` mayúscula suma dos `4`, así que `RRR` → seis `4`.
- Sin cambios: `r` → `4`, y `rr`, `Rr`, `rR` y `R` siguen dando `4 4`.

### 🔧 Mejoras
- Se quita la opción «Sonido de z». La `z` minúscula sale siempre como `s` y la `Z` mayúscula siempre como `z`, que era lo predeterminado. Si tu `config.json` todavía guarda esa opción, se ignora.
- El menú de ayuda («Atajos y fonemas») incluye la entrada de `RR` y un texto de `Z` más simple.
- La página web actualiza el apartado "Un vistazo" para que funcione igual que esta versión.

## v2.4

### ✨ Novedades
- **Consonante + `i` + vocal tónica:** cuando una `i` queda entre una consonante y una vocal, y la última vocal lleva tilde o está en mayúscula, la `i` se absorbe en la consonante, que recibe apóstrofe.
  - `pió`, `piO` → `p' o`
  - `kiú`, `kiU` → `k' M`
  - `rió` → `4' o`, `Rió` → `4 4' o`
  - `nió`, `niO` → `J o` (la `n` pasa a `J`, que no lleva apóstrofe)
- Sin cambios: `kiu` → `k j M`, `kíu` / `kIu` → `k' i M`.

### 🎯 Excepciones
- `f` (`p\`): no suena bien con apóstrofe en este caso. `fió` → `p\ j o`.
- `C`: no se pronuncia con apóstrofe.
- Consonantes sin versión palatalizada (s, ch, c, g suave, ll...): siguen con el diptongo normal (`siO` → `s j o`).

### 🔧 Mejoras
- Las letras `A`, `E` y `O` en mayúscula (Bloq Mayús o Shift) ahora cuentan como vocal tónica. En el resto de reglas se comportan igual que en minúscula.
- El menú de ayuda explica la nueva regla, en las secciones de minúsculas y mayúsculas.
- El proyecto pasa a ser software libre bajo la **GPL-3.0** (archivo `LICENSE`).
- La página web actualiza el apartado "Un vistazo" para que funcione igual que esta versión.
