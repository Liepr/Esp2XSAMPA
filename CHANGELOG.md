# Registro de cambios

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
