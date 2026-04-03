/**
 * usePolymarket.js — Phase 13 Pilar 3
 * Fetches live conflict prediction markets from Polymarket's public Gamma API.
 * No authentication required.
 */
import { useState, useEffect } from 'react';

const POLYMARKET_API = 'https://gamma-api.polymarket.com/markets';
const CONFLICT_TAGS  = ['war', 'conflict', 'military', 'nuclear', 'geopolitical', 'iran', 'israel', 'ukraine', 'taiwan', 'russia'];
const POLL_INTERVAL  = 5 * 60 * 1000; // 5 minutes

export function usePolymarket(enabled = true) {
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const fetchMarkets = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetching from Polymarket's Gamma API — no auth needed
      const params = new URLSearchParams({
        limit: 20,
        active: true,
        closed: false,
        order: 'volume',
        ascending: false,
      });

      const res = await fetch(`${POLYMARKET_API}?${params}`, {
        headers: { 'Accept': 'application/json' },
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Filter for conflict-related markets
      const filtered = data.filter(m => {
        const q = (m.question || m.title || '').toLowerCase();
        const tags = (m.tags || []).map(t => (typeof t === 'string' ? t : t.label || '').toLowerCase());
        return CONFLICT_TAGS.some(tag => q.includes(tag) || tags.includes(tag));
      });

      // Normalize
      const normalized = filtered.map(m => ({
        id: m.id,
        question: m.question || m.title || 'Unknown',
        yesPrice: m.outcomePrices ? parseFloat(m.outcomePrices[0]) : null,
        noPrice:  m.outcomePrices ? parseFloat(m.outcomePrices[1]) : null,
        volume:   m.volume24hr || m.volume || 0,
        liquidity: m.liquidity || 0,
        tags: m.tags || [],
        slug: m.slug || '',
        endDate: m.endDate || null,
        // Price change 24h if available
        priceDelta24h: m.lastTradedPrices?.[0]
          ? ((parseFloat(m.outcomePrices?.[0] || 0) - parseFloat(m.lastTradedPrices[0])) * 100).toFixed(1)
          : null,
      }));

      setMarkets(normalized.slice(0, 10));
      setLastUpdate(new Date());
    } catch (err) {
      console.warn('[Polymarket] Fetch failed:', err.message);
      setError(err.message);
      // Fallback: static mock data for demonstration
      setMarkets(MOCK_MARKETS);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!enabled) return;
    fetchMarkets();
    const interval = setInterval(fetchMarkets, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [enabled]);

  return { markets, loading, lastUpdate, error, refetch: fetchMarkets };
}

// Mock data for demonstration / CORS fallback
const MOCK_MARKETS = [
  {
    id: 'm1',
    question: 'Will Iran successfully target US shipping in 2026?',
    yesPrice: 0.24, noPrice: 0.76, volume: 4100000,
    priceDelta24h: '+2.1', slug: 'iran-shipping-2026',
    tags: ['iran', 'military'], endDate: '2026-12-31',
  },
  {
    id: 'm2',
    question: 'Resolution: Middle East Conflict by Q2 2026?',
    yesPrice: 0.08, noPrice: 0.92, volume: 19200000,
    priceDelta24h: '-1.4', slug: 'middle-east-resolution-q2-2026',
    tags: ['conflict', 'israel'], endDate: '2026-06-30',
  },
  {
    id: 'm3',
    question: 'Taiwan Strait Military Action Q3 2026?',
    yesPrice: 0.06, noPrice: 0.94, volume: 31000000,
    priceDelta24h: '+0.8', slug: 'taiwan-strait-conflict-q3-2026',
    tags: ['taiwan', 'military'], endDate: '2026-09-30',
  },
  {
    id: 'm4',
    question: 'Will Russia launch nuclear weapon before 2027?',
    yesPrice: 0.04, noPrice: 0.96, volume: 8400000,
    priceDelta24h: '0.0', slug: 'russia-nuclear-2027',
    tags: ['russia', 'nuclear'], endDate: '2026-12-31',
  },
  {
    id: 'm5',
    question: 'Will Ukraine recapture Crimea by end of 2026?',
    yesPrice: 0.11, noPrice: 0.89, volume: 22100000,
    priceDelta24h: '+3.2', slug: 'ukraine-crimea-2026',
    tags: ['ukraine', 'war'], endDate: '2026-12-31',
  },
];
