# BRIEF ANTIGRAVITY — OmniGlobe Engine Upgrade + Crucix Integration
**Fecha:** 2026-04-01 | **Prioridad:** ALTA | **Token Budget:** MÍNIMO

---

## OBJETIVO ÚNICO
Mejorar el motor gráfico del OmniGlobe en `frontend/src/components/Globe3D.jsx` de WebGL básico (puntos) a **Three.js con textura real de la Tierra + marcadores de eventos OSINT en tiempo real**, y unificar las capas del Crucix Monitor (localhost:3117) en el dominio `elanarcocapital.com`.

---

## BLOQUE 1 — Instalar dependencias

```bash
cd C:\Users\Admn\Desktop\NEXO_SOBERANO\frontend
npm install three @react-three/fiber @react-three/drei
```

---

## BLOQUE 2 — Reemplazar Globe3D.jsx

**Archivo:** `frontend/src/components/Globe3D.jsx`

Reemplazar completamente con una implementación Three.js que incluya:

1. **Esfera con textura** — usar `https://unpkg.com/three-globe/example/img/earth-dark.jpg` como mapa base (o incluir como asset local en `frontend/public/earth-dark.jpg`)
2. **Puntos de calor** — recibir prop `events: [{lat, lng, type, intensity}]` y renderizar como esferas/sprites sobre el globo con color según `type`:
   - `conflict` → rojo `#ff2244`
   - `osint` → cyan `#00e5ff`
   - `nuclear` → verde `#00ff88`
   - `maritime` → azul `#0088ff`
3. **Rotación automática** — `autoRotate: true, speed: 0.3` con pausa al hover
4. **Atmósfera glow** — shader de atmósfera exterior (ver ejemplo: `@react-three/drei` `<Sphere>` + material custom)
5. **Props mínimas:**
   ```jsx
   <Globe3D
     events={[]}        // array de marcadores
     size={420}
     autoRotate={true}
     onPointClick={(event) => {}}
   />
   ```

**Referencia de código base:** https://github.com/vasturiano/react-globe.gl — NO instalar esta librería, tomar solo la lógica de shaders de atmósfera y adaptarla.

---

## BLOQUE 3 — Conectar datos reales al globo

**Archivo:** `frontend/src/pages/Mapa.jsx`

Agregar fetch a `/api/inteligencia/eventos-geo` cada 30s para obtener los eventos y pasarlos al Globe3D:

```jsx
const [events, setEvents] = useState([]);

useEffect(() => {
  const load = () =>
    fetch('/api/inteligencia/eventos-geo')
      .then(r => r.json())
      .then(d => setEvents(d.eventos || []))
      .catch(() => {});
  load();
  const iv = setInterval(load, 30000);
  return () => clearInterval(iv);
}, []);
```

Si el endpoint no existe, crear mock data en el mismo componente con 10 eventos reales de la vista Crucix (Iran, Ukraine, Taiwan, etc.).

---

## BLOQUE 4 — Clonar e integrar repos OSINT

Ejecutar en `C:\Users\Admn\Desktop\NEXO_SOBERANO\AI-INTELLIGENCE-SYSTEM\`:

```bash
# Repos a clonar (solo los relevantes)
git clone https://github.com/calesthio/Crucix crucix_source
git clone https://github.com/h9zdev/GeoSentinel geosentinel_source
git clone https://github.com/ni5arga/sightline sightline_source
git clone https://github.com/koala73/worldmonitor worldmonitor_source
git clone https://github.com/sgoudelis/ground-station ground_station_source
```

De cada repo, extraer SOLO:
- **Crucix** → panel de sensores laterales (HTML/JS) → documentar en `CRUCIX_COMPONENTS.md`
- **GeoSentinel** → lógica de geolocalización de IPs → copiar a `backend/services/geo_sentinel.py`
- **Sightline** → feeds RSS/OSINT parsers → copiar a `backend/services/sightline_feeds.py`
- **WorldMonitor** → estructura de zonas geográficas → extraer JSON de regiones
- **Ground Station** → tracking de satélites TLE → copiar a `backend/services/ground_station.py`

---

## BLOQUE 5 — Unificación en elanarcocapital.com

**Archivo:** `vercel.json`

Agregar rewrite para que `/monitor` sirva el Crucix y `/globe` sirva el OmniGlobe:

```json
{
  "rewrites": [
    { "source": "/monitor/:path*", "destination": "/frontend_public/crucix_monitor.html" },
    { "source": "/api/:path*", "destination": "https://nexo-backend.railway.app/api/:path*" }
  ]
}
```

Crear `frontend_public/crucix_monitor.html` como copia del index del Crucix (localhost:3117) con:
- Base URL de datos apuntando a `/api/inteligencia/`
- Sin referencias a localhost

---

## BLOQUE 6 — Verificación

Antes de declarar completo, mostrar:

```
[OK] Globe3D renderiza con Three.js (no WebGL puro)
[OK] Al menos 5 marcadores visibles sobre el globo
[OK] Rotación automática funciona, pausa al hover
[OK] npm run build sin errores
[OK] vercel.json actualizado con /monitor route
```

---

## RESTRICCIÓN DE CIERRE

**NO declarar el sprint terminado sin mostrar:**
1. Screenshot del Globe3D con Three.js corriendo en `localhost:5173`
2. Output de `npm run build` exitoso
3. Los 5 repos clonados en `AI-INTELLIGENCE-SYSTEM/`

---

## ARCHIVOS A NO TOCAR
- `main.py`, `backend/main.py`
- `.env`
- `backend/auth/*.json`
- Cualquier archivo con credenciales

---

## REPOS DESCARTADOS (no implementar ahora)
- `alphafox02/iridium-sniffer` — hardware SDR, fuera de scope
- `h9zdev/WireTapper` — red local, fuera de scope
- `ucsdsysnet/dontlookup` — DNS research tool, no prioritario
- `Kuberwastaken/claurst` / `instructkr/claw-code` — Claude wrappers, no necesarios
