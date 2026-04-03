import { useState, useEffect } from 'react';
import * as satellite from 'satellite.js';

// CelesTrak active satellites standard URL (Proxy via backend or direct if CORS allows)
const CELESTRAK_ACTIVE_URL = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle';

export function useSatellites(enabled = true) {
  const [satellites, setSatellites] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!enabled) return;

    const fetchTLEs = async () => {
      try {
        const res = await fetch(CELESTRAK_ACTIVE_URL);
        if (!res.ok) throw new Error('Error fetching TLE data');
        const text = await res.text();
        
        // Parse TLE pairs
        const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        const sats = [];
        
        // Keep a curated list or take top 50 to avoid slowing down the globe
        const MAX_SATS = 100;

        for (let i = 0; i < lines.length && sats.length < MAX_SATS; i += 3) {
          const name = lines[i];
          const tle1 = lines[i + 1];
          const tle2 = lines[i + 2];
          
          if (!tle1 || !tle2) break;

          try {
            const satrec = satellite.twoline2satrec(tle1, tle2);
            // Only add if we can propagate it at current time
            const positionAndVelocity = satellite.propagate(satrec, new Date());
            if (positionAndVelocity.position && typeof positionAndVelocity.position !== 'boolean') {
               sats.push({ name, satrec, id: sats.length });
            }
          } catch(e) { /* ignore parse error for specific sat */ }
        }
        setSatellites(sats);
      } catch (err) {
        console.error("useSatellites error:", err);
        setError(err.message);
      }
    };

    fetchTLEs();
  }, [enabled]);

  return { satellites, error };
}
