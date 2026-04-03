/**
 * GlobeMaplibre — Motor gráfico Mizar-style
 * Maplibre GL JS en proyección globe con tiles CartoDB Dark Matter.
 * Roads visibles desde zoom 4+. Sin parpadeo. Zoom suave.
 * forwardRef: expone flyToEvent(lat,lng,zoom) y getMap() al padre.
 */
import { useEffect, useRef, useCallback, useImperativeHandle, forwardRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { STRATEGIC_CITIES, CITY_COLORS, COUNTRY_NAMES } from '../data/strategicCities';

// ── Estilos de mapa ───────────────────────────────────────────────────────────
const STYLE_DARK  = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const STYLE_SAT   = 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json';

// ── Colores por tipo de marker ────────────────────────────────────────────────
const MARKER_COLORS = {
  conflict:   '#ff2244',
  thermal:    '#fb923c',
  naval:      '#0088ff',
  flight:     '#ffdd00',
  base:       '#00e5ff',
  drive:      '#a855f7',
  satellite:  '#44aaff',
  strike:     '#ef4444',
};

// ── Marker HTML — tamaño ciudad (pequeño, elegante) ───────────────────────────
const makeMarkerEl = (type, label, severity) => {
  const color = MARKER_COLORS[type] || '#00e5ff';
  const size  = severity === 'critical' ? 7 : 5;
  const el    = document.createElement('div');
  el.style.cssText = 'position:relative;cursor:pointer;';
  el.innerHTML = `
    <div style="
      display:flex;align-items:center;gap:4px;
      background:rgba(5,10,20,0.88);
      border:1px solid ${color}44;
      border-radius:3px;
      padding:1px 5px;
      font-family:monospace;
      font-size:8px;
      color:${color};
      white-space:nowrap;
      box-shadow:0 0 6px ${color}33;
      backdrop-filter:blur(4px);
      pointer-events:auto;
    ">
      <div style="
        width:${size}px;height:${size}px;
        border-radius:50%;
        background:${color};
        box-shadow:0 0 ${size}px ${color}66;
        flex-shrink:0;
      "></div>
      ${label ? `<span>${label.slice(0, 18).toUpperCase()}</span>` : ''}
    </div>
  `;
  return el;
};

// ── Componente (forwardRef para exponer flyToEvent al padre) ──────────────────
const GlobeMaplibre = forwardRef(function GlobeMaplibre({
  conflictMarkers = [],
  thermalMarkers  = [],
  liveVessels     = [],
  liveFlights     = [],
  driveMarkers    = [],
  tacticalBases   = [],
  channels        = {},
  onMarkerClick   = () => {},
  satStyle        = false,
}, ref) {
  const containerRef = useRef(null);
  const mapRef       = useRef(null);
  const markersRef   = useRef([]);

  // ── Init map ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style:     STYLE_DARK,
      projection: 'globe',
      zoom:      2.2,
      center:    [42, 24],
      minZoom:   1,
      maxZoom:   18,
      antialias: true,
      fadeDuration: 0,
      preserveDrawingBuffer: false,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'bottom-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');

    map.on('style.load', () => {
      try {
        map.setFog({
          color: 'rgb(2, 8, 18)',
          'high-color': 'rgb(0, 10, 30)',
          'horizon-blend': 0.05,
          'space-color': 'rgb(0, 0, 8)',
          'star-intensity': 0.6,
        });
      } catch (_) {}
    });

    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  // ── Exponer API al padre ──────────────────────────────────────────────────────
  useImperativeHandle(ref, () => ({
    // flyToEvent: vuela a zoom 15 con perspectiva 3D (pitch 45°) para ver edificios
    flyToEvent: (lat, lng, zoom = 15) => {
      if (!mapRef.current) return;
      mapRef.current.flyTo({
        center:   [lng, lat],
        zoom,
        pitch:    zoom >= 14 ? 45 : 0,   // perspectiva 3D al nivel de calle
        bearing:  zoom >= 14 ? -15 : 0,
        duration: 2000,
        easing:   t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
      });
    },
    getMap: () => mapRef.current,
  }), []);

  // ── Style switch + capa de edificios 3D ───────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.setStyle(satStyle ? STYLE_SAT : STYLE_DARK);
  }, [satStyle]);

  // Capa de edificios 3D — aparece automáticamente al hacer zoom > 13 (nivel ciudad)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const add3DBuildings = () => {
      // Verifica que la fuente de OSM esté disponible en el estilo actual
      if (!map.getSource('openmaptiles') && !map.getSource('carto')) return;
      if (map.getLayer('3d-buildings')) return;
      try {
        map.addLayer({
          id: '3d-buildings',
          source: map.getSource('openmaptiles') ? 'openmaptiles' : 'carto',
          'source-layer': 'building',
          type: 'fill-extrusion',
          minzoom: 13,
          paint: {
            'fill-extrusion-color': [
              'interpolate', ['linear'], ['zoom'],
              13, 'rgba(20,30,50,0.7)',
              16, 'rgba(10,20,40,0.9)',
            ],
            'fill-extrusion-height': ['get', 'render_height'],
            'fill-extrusion-base':   ['get', 'render_min_height'],
            'fill-extrusion-opacity': 0.85,
          },
        });
      } catch (_) {}
    };
    if (map.isStyleLoaded()) add3DBuildings();
    else map.on('style.load', add3DBuildings);
    map.on('style.load', add3DBuildings); // re-add after style switch
  }, [satStyle]);

  // ── Update markers ────────────────────────────────────────────────────────────
  const clearMarkers = useCallback(() => {
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const addMarkers = () => {
      clearMarkers();
      const newMarkers = [];

      // GDELT conflicts
      if (channels.gdelt !== false) {
        conflictMarkers.forEach(m => {
          const el = makeMarkerEl('conflict', m.label, m.severity);
          const countryStr = m.country ? ` · ${m.country}` : '';
          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([m.lng, m.lat])
            .setPopup(new maplibregl.Popup({ className: 'nexo-popup' }).setHTML(
              `<div style="font-family:monospace;font-size:10px;color:#ff2244;background:#050a14;padding:8px 10px;min-width:160px;">
                <div style="font-size:8px;letter-spacing:0.15em;color:#445;margin-bottom:4px;">CONFLICTO GDELT</div>
                <b style="font-size:11px;">${m.label.slice(0,40).toUpperCase()}</b>${countryStr}
                <div style="color:#445;font-size:8px;margin-top:4px;">${m.lat?.toFixed(3)}°, ${m.lng?.toFixed(3)}° &middot; ${m.severity?.toUpperCase() || ''}</div>
              </div>`
            ))
            .addTo(map);
          el.onclick = () => { onMarkerClick(m); };
          newMarkers.push(marker);
        });
      }

      // FIRMS thermal
      if (channels.firms !== false) {
        thermalMarkers.forEach(m => {
          const el = makeMarkerEl('thermal', 'FIRE', 'normal');
          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([m.lng, m.lat])
            .addTo(map);
          newMarkers.push(marker);
        });
      }

      // AIS Live vessels
      if (channels.aisLive !== false && liveVessels.length > 0) {
        liveVessels.slice(0, 120).forEach(v => {
          if (!v.lat || !v.lng) return;
          const el = makeMarkerEl('naval', v.name || v.mmsi, 'normal');
          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([v.lng, v.lat])
            .setPopup(new maplibregl.Popup({ className: 'nexo-popup' }).setHTML(
              `<div style="font-family:monospace;font-size:11px;color:#0088ff;background:#050a14;padding:8px;">
                <b>[VESSEL]</b> ${v.name || v.mmsi || 'UNKNOWN'}<br/>
                SOG: ${v.sog ?? '?'} kn &middot; COG: ${v.cog ?? '?'}&deg;<br/>
                <span style="color:#445;font-size:9px;">${v.lat?.toFixed(3)}, ${v.lng?.toFixed(3)}</span>
              </div>`
            ))
            .addTo(map);
          el.onclick = () => { onMarkerClick(v); };
          newMarkers.push(marker);
        });
      }

      // OpenSky flights
      if (channels.osintFlights !== false) {
        liveFlights.slice(0, 80).forEach(f => {
          if (!f.lat || !f.lng) return;
          const el = makeMarkerEl('flight', f.callsign, 'normal');
          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([f.lng, f.lat])
            .addTo(map);
          newMarkers.push(marker);
        });
      }

      // Drive docs
      if (channels.drive !== false) {
        driveMarkers.forEach(m => {
          const el = makeMarkerEl('drive', m.label, 'normal');
          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([m.lng, m.lat])
            .addTo(map);
          el.onclick = () => { onMarkerClick(m); };
          newMarkers.push(marker);
        });
      }

      // Tactical bases
      if (channels.bases !== false) {
        tacticalBases.forEach(b => {
          const el = makeMarkerEl('base', b.id, 'critical');
          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([b.lng, b.lat])
            .setPopup(new maplibregl.Popup({ className: 'nexo-popup' }).setHTML(
              `<div style="font-family:monospace;font-size:10px;color:#00e5ff;background:#050a14;padding:8px 10px;min-width:160px;">
                <div style="font-size:8px;letter-spacing:0.15em;color:#445;margin-bottom:4px;">BASE TÁCTICA</div>
                <b>${b.name?.toUpperCase() || b.id?.toUpperCase()}</b>
                ${b.country ? `<span style="color:#445"> · ${b.country}</span>` : ''}
                <div style="color:#445;font-size:8px;margin-top:4px;">${b.troops ? `${b.troops} tropas` : ''}</div>
              </div>`
            ))
            .addTo(map);
          newMarkers.push(marker);
        });
      }

      // Ciudades estratégicas (critical + high) — pequeños dots con label Ciudad · País
      if (channels.cities !== false) {
        STRATEGIC_CITIES.filter(c => c.tier === 'critical' || c.tier === 'high').forEach(city => {
          const color = CITY_COLORS[city.tier];
          const countryName = COUNTRY_NAMES[city.country] || city.country;
          const el = document.createElement('div');
          el.style.cssText = 'cursor:pointer;position:relative;';
          el.innerHTML = `
            <div style="display:flex;align-items:center;gap:3px;pointer-events:auto;">
              <div style="width:4px;height:4px;border-radius:50%;background:${color};box-shadow:0 0 4px ${color}88;flex-shrink:0;"></div>
              <span style="font-family:monospace;font-size:7px;color:${color};white-space:nowrap;opacity:0.85;">${city.name.toUpperCase()} · ${countryName.toUpperCase()}</span>
            </div>
          `;
          const marker = new maplibregl.Marker({ element: el, anchor: 'left' })
            .setLngLat([city.lng, city.lat])
            .setPopup(new maplibregl.Popup({ className: 'nexo-popup' }).setHTML(
              `<div style="font-family:monospace;font-size:10px;color:${color};background:#050a14;padding:8px 10px;min-width:140px;">
                <div style="font-size:8px;letter-spacing:0.15em;color:#445;margin-bottom:4px;">${city.tier.toUpperCase()} RISK</div>
                <b>${city.name.toUpperCase()}</b>
                <span style="color:#445;"> · ${countryName}</span>
                <div style="color:#445;font-size:8px;margin-top:4px;">${city.lat.toFixed(2)}°, ${city.lng.toFixed(2)}°</div>
              </div>`
            ))
            .addTo(map);
          newMarkers.push(marker);
        });
      }

      markersRef.current = newMarkers;
    };

    if (map.isStyleLoaded()) {
      addMarkers();
    } else {
      map.once('load', addMarkers);
    }
  }, [conflictMarkers, thermalMarkers, liveVessels, liveFlights, driveMarkers,
      tacticalBases, channels, clearMarkers, onMarkerClick]);

  return (
    <>
      <style>{`
        .nexo-popup .maplibregl-popup-content {
          background: #050a14 !important;
          border: 1px solid rgba(0,229,255,0.3) !important;
          border-radius: 4px !important;
          padding: 0 !important;
          box-shadow: 0 0 20px rgba(0,229,255,0.15) !important;
        }
        .nexo-popup .maplibregl-popup-tip { border-top-color: rgba(0,229,255,0.3) !important; }
        .maplibregl-ctrl-attrib { display: none !important; }
        .maplibregl-ctrl-logo   { display: none !important; }
      `}</style>
      <div
        ref={containerRef}
        style={{ width: '100%', height: '100%', position: 'absolute', inset: 0 }}
      />
    </>
  );
});

export default GlobeMaplibre;
