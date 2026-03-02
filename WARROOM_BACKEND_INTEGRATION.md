# 🛰️ NEXO WAR ROOM: Arquitectura de Integración Backend

**Documento:** Integración de 8 Repositorios OSINT  
**Versión:** 1.0  
**Estado:** Blueprint técnico  
**Fecha:** 28 Feb 2026

---

## 📋 Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Integraciones Repo por Repo](#integraciones-repo-por-repo)
3. [API Endpoints](#api-endpoints)
4. [WebSocket Real-Time](#websocket-real-time)
5. [Data Models](#data-models)
6. [Deployment](#deployment)

---

## 🏗️ Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                    NEXO War Room (Frontend)                │
│              warroom_repos_integrados.html                 │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    REST API              WebSocket (live feeds)
    (HTTP/8000)           (WS/8001)
         │                       │
┌────────────────────────────────────────────────────────────┐
│              FastAPI Backend (NEXO Phase 9)                │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │           War Room Integration Layer                │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │                                                     │  │
│  │  GeoSentinel    (ships, flights)                    │  │
│  │  WorldMonitor   (country stability)                 │  │
│  │  tvscreener     (financial markets)                 │  │
│  │  Sightline      (infrastructure OSM)                │  │
│  │  WebOSINT       (domain OSINT)                      │  │
│  │  sn0int         (passive recon)                     │  │
│  │  GroundStation  (satellite tracking)                │  │
│  │  pgrok          (tunneling)                         │  │
│  │                                                     │  │
│  │  [Cache Layer: Redis]                              │  │
│  │  [Queues: Celery]                                  │  │
│  │  [DB: PostgreSQL + ChromaDB]                       │  │
│  │                                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
         │                       │
    ┌────┴─────────────────────┬────┐
    │                          │    │
External APIs:          External Services:
├─ GeoSentinel API      ├─ Leaflet Map
├─ WorldMonitor API     ├─ TradingView  
├─ tvscreener API       ├─ OpenStreetMap
├─ sn0int DB            ├─ Shodan (optional)
└─ sightline OSM        └─ VirusTotal (optional)
```

---

## 🔌 Integraciones Repo por Repo

### 1️⃣ GeoSentinel (Naval + Vuelos)

**GitHub:** `h9zdev/GeoSentinel`  
**Tipo:** Real-time geo-tracking (AIS ships, ADS-B flights)  
**Datos:** Coordenadas, velocidad, rumbo, ID de buque/vuelo en vivo  

**Integración Backend:**

```python
# services/geosentimental_service.py

import asyncio
from typing import List, Dict
import aiohttp
from datetime import datetime, timedelta

class GeoSentinelService:
    """Integración con GeoSentinel para tracking naval y de vuelos."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://api.geosentianel.ai"  # or local endpoint
        self.cache = {}
        self.last_update = {}
    
    async def get_active_ships(self, region: str = None) -> List[Dict]:
        """
        Obtener buques activos via AIS.
        region: 'mena', 'caribbean', 'south-china-sea', etc.
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'type': 'ship',
                    'region': region or 'global',
                    'realtime': True,
                    'fields': 'mmsi,lon,lat,speed_kts,heading,ship_name,callsign'
                }
                async with session.get(f"{self.base_url}/vessels", 
                                      params=params,
                                      headers={'Authorization': f'Bearer {self.api_key}'}) as resp:
                    data = await resp.json()
                    
                    # Cache for 30 seconds
                    self.cache['ships'] = data['data']
                    self.last_update['ships'] = datetime.utcnow()
                    
                    return data['data']
        except Exception as e:
            print(f"GeoSentinel ships error: {e}")
            return self.cache.get('ships', [])
    
    async def get_active_flights(self, region: str = None) -> List[Dict]:
        """
        Obtener vuelos activos via ADS-B.
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'type': 'flight',
                    'region': region or 'global',
                    'realtime': True,
                    'fields': 'icao,lon,lat,altitude_ft,heading,speed_kts,callsign,aircraft_type'
                }
                async with session.get(f"{self.base_url}/aircraft",
                                      params=params,
                                      headers={'Authorization': f'Bearer {self.api_key}'}) as resp:
                    data = await resp.json()
                    self.cache['flights'] = data['data']
                    self.last_update['flights'] = datetime.utcnow()
                    return data['data']
        except Exception as e:
            print(f"GeoSentinel flights error: {e}")
            return self.cache.get('flights', [])
    
    async def get_regional_statistics(self) -> Dict:
        """Stats por región."""
        ships = await self.get_active_ships()
        flights = await self.get_active_flights()
        
        return {
            'total_ships': len(ships),
            'total_flights': len(flights),
            'updates_at': datetime.utcnow().isoformat(),
            'regions': {
                'mena': len([s for s in ships if s.get('region') == 'mena']),
                'caribbean': len([s for s in ships if s.get('region') == 'caribbean']),
            }
        }

geosentinel = GeoSentinelService(api_key=os.getenv('GEOSENTIANEL_API_KEY'))
```

**FastAPI Endpoints:**

```python
# routes/warroom_geosentinel.py

@router.get("/api/v1/warroom/ships")
async def get_ships(region: str = None):
    ships = await geosentinel.get_active_ships(region)
    return {
        'status': 'success',
        'data': ships,
        'count': len(ships),
        'last_update': geosentimel.last_update.get('ships')
    }

@router.get("/api/v1/warroom/flights")
async def get_flights(region: str = None):
    flights = await geosentimel.get_active_flights(region)
    return {
        'status': 'success',
        'data': flights,
        'count': len(flights),
        'last_update': geosentimel.last_update.get('flights')
    }

@router.get("/api/v1/warroom/geosentimel/stats")
async def geosentimel_stats():
    stats = await geosentimel.get_regional_statistics()
    return stats
```

---

### 2️⃣ WorldMonitor (Country Instability Index)

**Tipo:** Geopolitical risk scoring  
**Datos:** CII (Country Instability Index) por país, conflictos activos  

**Integración Backend:**

```python
# services/worldmonitor_service.py

class WorldMonitorService:
    """Country Instability Index + Conflict tracking."""
    
    def __init__(self):
        self.base_url = "https://api.worldmonitor.ai"
        self.cii_cache = {}
        self.conflict_zones = []
    
    async def get_cii_score(self, country_code: str) -> Dict:
        """
        CII Score (0-100):
        0-30: Stable
        31-60: Moderate Risk
        61-80: High Risk
        81-100: Critical Instability
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/cii/{country_code}") as resp:
                    data = await resp.json()
                    return data
        except:
            return {'score': 0, 'error': 'unavailable'}
    
    async def get_all_cii_scores(self) -> Dict[str, float]:
        """Get CII for top 50 countries by instability."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/cii/top50") as resp:
                    data = await resp.json()
                    # Sort descending
                    sorted_cii = sorted(data.items(), key=lambda x: x[1], reverse=True)
                    return dict(sorted_cii)
        except:
            return {}
    
    async def get_conflict_zones(self, severity: str = None) -> List[Dict]:
        """
        Get active conflict zones.
        severity: 'critical', 'high', 'medium'
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {'severity': severity} if severity else {}
                async with session.get(f"{self.base_url}/conflicts", params=params) as resp:
                    data = await resp.json()
                    # Each has: lat, lon, name, severity, zone_type
                    return data['conflicts']
        except:
            return []
    
    async def get_regional_alert(self, region: str) -> Dict:
        """Get alert level for region: MENA, Europa, Asia-Pac, etc."""
        zones = await self.get_conflict_zones()
        regional_zones = [z for z in zones if z.get('region') == region]
        
        if regional_zones:
            max_severity = max([z.get('severity_score', 0) for z in regional_zones])
            return {
                'region': region,
                'alert_level': 'CRITICAL' if max_severity > 80 else 'HIGH' if max_severity > 60 else 'MEDIUM',
                'active_zones': len(regional_zones),
                'zones': regional_zones
            }
        return {'region': region, 'alert_level': 'NORMAL', 'active_zones': 0}

worldmonitor = WorldMonitorService()
```

**FastAPI Endpoints:**

```python
@router.get("/api/v1/warroom/cii")
async def get_cii_scores():
    scores = await worldmonitor.get_all_cii_scores()
    return {'status': 'success', 'cii': scores}

@router.get("/api/v1/warroom/cii/{country}")
async def get_cii_country(country: str):
    score = await worldmonitor.get_cii_score(country)
    return score

@router.get("/api/v1/warroom/conflicts")
async def get_conflicts(severity: str = None):
    zones = await worldmonitor.get_conflict_zones(severity)
    return {'status': 'success', 'conflicts': zones}

@router.get("/api/v1/warroom/regional-alert/{region}")
async def regional_alert(region: str):
    alert = await worldmonitor.get_regional_alert(region)
    return alert
```

---

### 3️⃣ tvscreener (Financial Markets)

**GitHub:** `deepentropy/tvscreener`  
**Tipo:** TradingView Screener API  
**Datos:** Forex, Crypto, Commodities, Stocks, Futures  

**Integración Backend:**

```python
# services/tvscreener_service.py

class TvScreenerService:
    """TradingView Screener integration."""
    
    def __init__(self):
        # Can use tvDatafeed or direct TradingView API
        self.symbols = {
            'forex': ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCAD', 'AUDUSD'],
            'crypto': ['BTCUSD', 'ETHUSD', 'BNBUSD', 'XRPUSD'],
            'commodities': ['OILUSD', 'BRENTUSD', 'GOLD', 'NATGAS'],
            'indices': ['SPX', 'NDX', 'DXY', 'VIX']
        }
        self.cache = {}
        self.last_update = {}
    
    async def get_symbol_data(self, symbol: str, interval: str = '1h') -> Dict:
        """Get OHLCV data for symbol."""
        try:
            # Using tvDatafeed or similar
            # data = get_hist(symbol, n_bars=100, interval=interval)
            
            # For demo: mock data
            return {
                'symbol': symbol,
                'price': 100.0,
                'change_pct': 2.3,
                'volume': 1000000,
                'high_24h': 105.0,
                'low_24h': 95.0
            }
        except Exception as e:
            print(f"tvscreener error: {e}")
            return {}
    
    async def get_screener_results(self, category: str) -> List[Dict]:
        """
        Get filtered results by category.
        category: 'top_gainers', 'top_losers', 'most_active', etc.
        """
        symbols = self.symbols.get(category, [])
        results = []
        
        for symbol in symbols:
            data = await self.get_symbol_data(symbol)
            results.append(data)
        
        return results
    
    async def get_correlation_signals(self, event: Dict) -> List[Dict]:
        """
        Detect price-event correlations.
        event: {'type': 'conflict', 'region': 'MENA', 'severity': 'high'}
        
        Returns: List of affected symbols with correlations
        """
        correlations = []
        
        if event.get('type') == 'conflict' and 'MENA' in event.get('region', ''):
            # Oil likely to spike
            oil_data = await self.get_symbol_data('OILUSD')
            if oil_data.get('change_pct', 0) > 0:
                correlations.append({
                    'symbol': 'OILUSD',
                    'correlation': 'Posible inflación geopolítica',
                    'signal': oil_data
                })
        
        return correlations

tvscreener = TvScreenerService()
```

**FastAPI Endpoints:**

```python
@router.get("/api/v1/warroom/markets/{category}")
async def get_markets(category: str):
    # category: 'forex', 'crypto', 'commodities', 'indices'
    results = await tvscreener.get_screener_results(category)
    return {'status': 'success', 'category': category, 'data': results}

@router.get("/api/v1/warroom/symbol/{symbol}")
async def get_symbol(symbol: str):
    data = await tvscreener.get_symbol_data(symbol)
    return data

@router.post("/api/v1/warroom/correlations")
async def detect_correlations(event: Dict):
    """
    Post an event (conflict, natural disaster, etc.) 
    and get market correlations.
    """
    correlations = await tvscreener.get_correlation_signals(event)
    return {'status': 'success', 'event': event, 'correlations': correlations}
```

---

### 4️⃣ Sightline (Infrastructure OSM)

**Tipo:** Critical infrastructure mapping  
**Datos:** Militar, puertos, energía, data centers, cables submarinos  

**Integración Backend:**

```python
# services/sightline_service.py

class SightlineService:
    """OpenStreetMap-based critical infrastructure mapping."""
    
    def __init__(self):
        self.base_url = "https://api.openstreetmap.org/api/0.6"
        self.infrastructure_types = {
            'military': ['military', 'barracks'],
            'ports': ['port', 'maritime'],
            'energy': ['power_plant', 'substation', 'wind_turbine'],
            'data': ['data_center'],
            'nuclear': ['nuclear'],
            'airports': ['aerodrome'],
            'cables': ['submarine_cable']
        }
    
    async def get_infrastructure(self, category: str, bbox: str = None) -> List[Dict]:
        """
        Get infrastructure by category.
        bbox: "left,bottom,right,top" (lat/lon bounds)
        """
        osm_tags = self.infrastructure_types.get(category, [])
        
        try:
            # Query OSM Overpass API
            overpass_query = f"""
            [out:json];
            (
                node[{osm_tags[0]}];
                way[{osm_tags[0]}];
                relation[{osm_tags[0]}];
            );
            out geom;
            """
            
            if bbox:
                overpass_query = f"({bbox});" + overpass_query
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://overpass-api.de/api/interpreter',
                    params={'data': overpass_query}
                ) as resp:
                    data = await resp.json()
                    return data.get('elements', [])
        except Exception as e:
            print(f"Sightline error: {e}")
            return []
    
    async def get_military_bases(self, region: str = None) -> List[Dict]:
        """Get all military installations in a region."""
        bases = await self.get_infrastructure('military')
        
        # Parse and return formatted
        formatted = []
        for base in bases:
            formatted.append({
                'name': base.get('tags', {}).get('name', 'Unknown Base'),
                'lat': base.get('lat'),
                'lon': base.get('lon'),
                'type': base.get('tags', {}).get('military', 'installation'),
                'country': base.get('tags', {}).get('country'),
            })
        
        return formatted
    
    async def get_critical_infrastructure_risk(self, category: str) -> Dict:
        """
        Risk assessment for infrastructure category.
        Returns: total count, risk score, key locations
        """
        infra = await self.get_infrastructure(category)
        
        return {
            'category': category,
            'total_count': len(infra),
            'risk_score': self._calculate_risk(category, len(infra)),
            'locations': infra[:10]  # Top 10
        }
    
    def _calculate_risk(self, category: str, count: int) -> float:
        """Simple risk scoring (0-100)."""
        base_risk = {
            'nuclear': 95,
            'military': 80,
            'energy': 70,
            'ports': 65,
            'data': 60,
            'cables': 50
        }
        return min(100, base_risk.get(category, 50) + (count / 100))

sightline = SightlineService()
```

**FastAPI Endpoints:**

```python
@router.get("/api/v1/warroom/infrastructure/{category}")
async def get_infrastructure(category: str):
    infra = await sightline.get_infrastructure(category)
    return {'status': 'success', 'category': category, 'data': infra}

@router.get("/api/v1/warroom/military-bases")
async def military_bases():
    bases = await sightline.get_military_bases()
    return {'status': 'success', 'bases': bases}

@router.get("/api/v1/warroom/infrastructure-risk/{category}")
async def infrastructure_risk(category: str):
    risk = await sightline.get_critical_infrastructure_risk(category)
    return risk
```

---

### 5️⃣ WebOSINT (Domain Intelligence)

**GitHub:** `C3n7ral051nt4g3ncy/WebOSINT`  
**Tipo:** Passive domain OSINT  
**Datos:** WHOIS, DNS records, subdominios, tech stack, historia  

**Integración Backend:**

```python
# services/webosint_service.py

class WebOSINTService:
    """WebOSINT integration for domain reconnaissance."""
    
    def __init__(self):
        # Can integrate with actual WebOSINT library
        self.base_url = "https://webosint.nexo.local"  # or use lib directly
        self.cache = {}
    
    async def recon_domain(self, domain: str) -> Dict:
        """
        Full domain recon: WHOIS, DNS, subdomains, history.
        """
        try:
            result = {
                'domain': domain,
                'whois': await self._get_whois(domain),
                'dns': await self._get_dns_records(domain),
                'subdomains': await self._get_subdomains(domain),
                'tech_stack': await self._get_tech_stack(domain),
                'ssl_cert': await self._get_ssl_cert(domain),
                'history': await self._get_domain_history(domain),
                'risk_score': 0
            }
            
            # Calculate risk
            result['risk_score'] = self._calculate_domain_risk(result)
            
            # Cache for 1 hour
            self.cache[domain] = result
            
            return result
        except Exception as e:
            print(f"WebOSINT error: {e}")
            return {'domain': domain, 'error': str(e)}
    
    async def _get_whois(self, domain: str) -> Dict:
        """WHOIS data."""
        return {
            'registrar': 'Example Registrar',
            'created_date': '1995-04-13',
            'expiry_date': '2030-04-14',
            'updated_date': '2025-01-15',
            'registrant_country': 'US',
            'status': 'clientTransferProhibited'
        }
    
    async def _get_dns_records(self, domain: str) -> Dict:
        """DNS A, MX, NS, TXT records."""
        return {
            'A': ['151.101.130.73'],
            'CNAME': [],
            'MX': ['10 mail.example.com'],
            'NS': ['ns1.example.com', 'ns2.example.com'],
            'TXT': ['v=spf1 include:_spf.google.com ~all']
        }
    
    async def _get_subdomains(self, domain: str) -> List[str]:
        """Find subdomains (passive)."""
        # Use crt.sh, Rapid7 or passive DNS
        return ['api.example.com', 'mail.example.com', 'admin.example.com']
    
    async def _get_tech_stack(self, domain: str) -> Dict:
        """Detect tech stack (Wappalyzer-style)."""
        return {
            'web_servers': ['Nginx'],
            'cdns': ['Fastly'],
            'frameworks': ['React', 'Node.js'],
            'cms': [],
            'analytics': ['Google Analytics']
        }
    
    async def _get_ssl_cert(self, domain: str) -> Dict:
        """SSL certificate info."""
        return {
            'valid': True,
            'issuer': "Let's Encrypt",
            'subject': domain,
            'issued_date': '2025-01-01',
            'expiry_date': '2026-01-01',
            'san': ['*.example.com', 'www.example.com']
        }
    
    async def _get_domain_history(self, domain: str) -> List[Dict]:
        """Domain Wayback Machine history."""
        return [
            {'date': '2024-01-15', 'title': 'Homepage V2', 'status': 200},
            {'date': '2023-06-20', 'title': 'Old Design', 'status': 200}
        ]
    
    def _calculate_domain_risk(self, recon: Dict) -> int:
        """Risk score 0-100."""
        risk = 0
        
        # Check WHOIS age
        if 'whois' in recon:
            created = recon['whois'].get('created_date')
            if created and (datetime.now() - parse(created)).days < 30:
                risk += 20  # New domain = suspicious
        
        # Check SSL
        if 'ssl_cert' not in recon or not recon.get('ssl_cert', {}).get('valid'):
            risk += 15
        
        # Check DNS reputation (would integrate with DNSDB)
        
        return min(100, risk)

webosint = WebOSINTService()
```

**FastAPI Endpoints:**

```python
@router.post("/api/v1/warroom/domain-recon")
async def domain_recon(body: Dict):
    domain = body.get('domain')
    if not domain:
        return {'error': 'domain required'}
    
    result = await webosint.recon_domain(domain)
    return result

@router.get("/api/v1/warroom/domain/{domain}")
async def get_domain_intel(domain: str):
    # Check cache first
    if domain in webosint.cache:
        return webosint.cache[domain]
    
    result = await webosint.recon_domain(domain)
    return result
```

---

### 6️⃣ sn0int (Passive Recon)

**Tipo:** Automated passive reconnaissance  
**Datos:** Network scans, open ports, subdomain enumeration  

**Integración Backend:**

```python
# services/sn0int_service.py

class Sn0intService:
    """sn0int integration for passive reconnaissance."""
    
    def __init__(self):
        # sn0int can run as daemon or we integrate library
        self.api_base = "https://sn0int.local:8080"
        self.results = {}
    
    async def enum_subdomains(self, domain: str) -> List[str]:
        """Passive subdomain enumeration."""
        # Uses certificate transparency, DNS, passive sources
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/recon/subdomains",
                    json={'target': domain}
                ) as resp:
                    data = await resp.json()
                    return data.get('subdomains', [])
        except:
            # Fallback to mock
            return [f'subdomain{i}.{domain}' for i in range(5)]
    
    async def enum_ipaddrs(self, domain: str) -> List[str]:
        """Find IP addresses (A, AAAA records + passive DNS)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/recon/ips",
                    json={'target': domain}
                ) as resp:
                    data = await resp.json()
                    return data.get('ips', [])
        except:
            return ['203.0.113.1']
    
    async def enum_netblocks(self, asn: str) -> List[Dict]:
        """Find all netblocks for ASN."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base}/asn/{asn}/netblocks"
                ) as resp:
                    data = await resp.json()
                    return data.get('netblocks', [])
        except:
            return []
    
    async def check_blacklist_status(self, domain: str) -> Dict:
        """Check if domain/IP is on security blacklists."""
        return {
            'domain': domain,
            'urlhaus': False,
            'abuse_ch': False,
            'phishing_db': False,
            'malware_db': False,
            'blocked_by_isp': False,
            'risk_level': 'CLEAN'
        }

sn0int = Sn0intService()
```

**FastAPI Endpoints:**

```python
@router.post("/api/v1/warroom/sn0int/enum")
async def sn0int_enum(body: Dict):
    target = body.get('target')
    target_type = body.get('type', 'domain')  # domain, asn, ip
    
    if target_type == 'domain':
        subdomains = await sn0int.enum_subdomains(target)
        ips = await sn0int.enum_ipaddrs(target)
        return {
            'target': target,
            'subdomains': subdomains,
            'ips': ips
        }
    elif target_type == 'asn':
        netblocks = await sn0int.enum_netblocks(target)
        return {'asn': target, 'netblocks': netblocks}

@router.get("/api/v1/warroom/sn0int/blacklist/{target}")
async def check_blacklist(target: str):
    result = await sn0int.check_blacklist_status(target)
    return result
```

---

### 7️⃣ Ground Station (Satellite Tracking)

**Tipo:** Real-time satellite tracking  
**Datos:** Posiciones actuales, órbitas, próximos avistamientos  

**Integración Backend:**

```python
# services/groundstation_service.py

from skyfield.api import EarthSatellite, load, wgs84
from skyfield.timelib import Time
from datetime import datetime, timedelta

class GroundStationService:
    """satellite tracking via Skyfield."""
    
    def __init__(self):
        self.ts = load.timescale()
        self.planets = load('de421.bsp')
        self.earth = self.planets['earth']
        
        # ISS TLE (update regularly)
        self.iss = EarthSatellite(
            "ISS (ZARYA)",
            "1 25544U 98067A   26059.01234567  .00005149  00000-0  95215-4 0  9996",
            "2 25544  51.6406 165.4298 0002632  44.6789 315.4751 15.53806157391000"
        )
        
        # Ground stations
        self.ground_stations = {
            'santiago': (self.earth + wgs84.latlong(-33.450, -70.667)),
            'miami': (self.earth + wgs84.latlong(25.761, -80.191)),
            'madrid': (self.earth + wgs84.latlong(40.415, -3.694)),
        }
    
    async def get_satellite_position(self, sat_name: str = 'ISS') -> Dict:
        """Get current position of satellite."""
        t = self.ts.now()
        astrometric = self.iss.at(t).observe(self.earth)
        lat, lon = wgs84.latlong_of(astrometric)
        
        # Get altitude above Earth
        geocentric = self.iss.at(t).position.au
        alt_km = (geocentric - self.earth.at(t).position.au).length().au * 149597870.7
        
        return {
            'satellite': sat_name,
            'latitude': float(lat.degrees),
            'longitude': float(lon.degrees),
            'altitude_km': float(alt_km),
            'velocity_kms': 7.66,  # ISS typical
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_next_passes(self, 
                             ground_station: str = 'santiago',
                             sat_name: str = 'ISS',
                             days_ahead: int = 7) -> List[Dict]:
        """Get next N passes over ground station."""
        station = self.ground_stations[ground_station]
        passes = []
        
        t = self.ts.now()
        end_time = self.ts.utc(
            t.utc_iso()[:4], t.utc_iso()[5:7], t.utc_iso()[8:10]
        ) + timedelta(days=days_ahead)
        
        # Find rise/culmination/set times
        # Simplified: return mock data
        passes.append({
            'rise_time': (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            'culmination_time': (datetime.utcnow() + timedelta(hours=2, minutes=5)).isoformat(),
            'set_time': (datetime.utcnow() + timedelta(hours=2, minutes=10)).isoformat(),
            'max_elevation_deg': 78.4,
            'brightness': 'BRIGHT'
        })
        
        return passes
    
    async def get_active_satellites_overhead(self) -> List[Dict]:
        """Get currently visible satellites above horizon."""
        # Would integrate with satellite.js or similar
        return [
            {
                'name': 'ISS',
                'elevation': 45.2,
                'azimuth': 315.8,
                'range_km': 392.1,
                'brightness': 'VERY BRIGHT'
            },
            {
                'name': 'NOAA-19',
                'elevation': 22.3,
                'azimuth': 180.0,
                'range_km': 1245.0,
                'brightness': 'BRIGHT'
            }
        ]

groundstation = GroundStationService()
```

**FastAPI Endpoints:**

```python
@router.get("/api/v1/warroom/satellite/{sat_name}")
async def get_satellite(sat_name: str = 'ISS'):
    pos = await groundstation.get_satellite_position(sat_name)
    return pos

@router.get("/api/v1/warroom/satellite/{sat_name}/passes")
async def get_passes(sat_name: str = 'ISS', ground_station: str = 'santiago'):
    passes = await groundstation.get_next_passes(
        ground_station=ground_station,
        sat_name=sat_name
    )
    return {'satellite': sat_name, 'passes': passes}

@router.get("/api/v1/warroom/satellites/visible")
async def visible_satellites():
    sats = await groundstation.get_active_satellites_overhead()
    return {'visible': sats}
```

---

### 8️⃣ pgrok (Tunneling)

**Tipo:** Exposición segura del War Room a internet  
**Datos:** Túnel reverso localhost:8000 → URL pública  

**Integración Backend:**

```python
# services/pgrok_service.py

import subprocess
import asyncio
from typing import Optional

class PgrokService:
    """pgrok tunnel management."""
    
    def __init__(self):
        self.tunnel_process = None
        self.tunnel_url = None
        self.is_running = False
    
    async def start_tunnel(self, 
                          local_port: int = 8000,
                          protocol: str = 'http') -> Dict:
        """Start pgrok tunnel."""
        try:
            # Start pgrok process
            self.tunnel_process = subprocess.Popen(
                ['pgrok', protocol, str(local_port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            await asyncio.sleep(2)  # Wait for startup
            
            # Extract tunnel URL from pgrok logs
            # (pgrok outputs to localhost:4040 inspector)
            self.tunnel_url = await self._get_tunnel_url()
            self.is_running = True
            
            return {
                'status': 'success',
                'tunnel_url': self.tunnel_url,
                'local_port': local_port,
                'is_running': True
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def stop_tunnel(self) -> Dict:
        """Stop pgrok tunnel."""
        if self.tunnel_process:
            self.tunnel_process.terminate()
            self.tunnel_process.wait()
            self.is_running = False
            return {'status': 'success', 'message': 'Tunnel stopped'}
        return {'status': 'error', 'message': 'No tunnel running'}
    
    async def _get_tunnel_url(self) -> Optional[str]:
        """Fetch tunnel URL from pgrok inspector."""
        try:
            import requests
            resp = requests.get('http://localhost:4040/api/tunnels')
            data = resp.json()
            
            for tunnel in data.get('tunnels', []):
                if tunnel.get('proto') == 'https':
                    return tunnel.get('public_url')
        except:
            pass
        return 'https://xxxx.pgrok.io'  # Placeholder
    
    async def get_tunnel_stats(self) -> Dict:
        """Get tunnel usage stats."""
        if not self.is_running:
            return {'status': 'offline'}
        
        try:
            import requests
            resp = requests.get('http://localhost:4040/api/requests/http')
            data = resp.json()
            
            return {
                'status': 'online',
                'tunnel_url': self.tunnel_url,
                'total_requests': len(data.get('requests', [])),
                'bandwidth_mb': len(str(data)) / 1024 / 1024
            }
        except:
            return {'status': 'online', 'tunnel_url': self.tunnel_url}

pgrok = PgrokService()
```

**FastAPI Endpoints:**

```python
@router.post("/api/v1/warroom/tunnel/start")
async def start_tunnel():
    result = await pgrok.start_tunnel(local_port=8000)
    return result

@router.post("/api/v1/warroom/tunnel/stop")
async def stop_tunnel():
    result = await pgrok.stop_tunnel()
    return result

@router.get("/api/v1/warroom/tunnel/status")
async def tunnel_status():
    return {
        'is_running': pgrok.is_running,
        'tunnel_url': pgrok.tunnel_url,
        'stats': await pgrok.get_tunnel_stats()
    }
```

---

## 📡 API Endpoints (Resumen)

```
GEOSENTIMEL
GET    /api/v1/warroom/ships
GET    /api/v1/warroom/flights
GET    /api/v1/warroom/geosentimel/stats

WORLDMONITOR
GET    /api/v1/warroom/cii
GET    /api/v1/warroom/cii/{country}
GET    /api/v1/warroom/conflicts
GET    /api/v1/warroom/regional-alert/{region}

TVSCREENER
GET    /api/v1/warroom/markets/{category}
GET    /api/v1/warroom/symbol/{symbol}
POST   /api/v1/warroom/correlations

SIGHTLINE
GET    /api/v1/warroom/infrastructure/{category}
GET    /api/v1/warroom/military-bases
GET    /api/v1/warroom/infrastructure-risk/{category}

WEBOSINT
POST   /api/v1/warroom/domain-recon
GET    /api/v1/warroom/domain/{domain}

SN0INT
POST   /api/v1/warroom/sn0int/enum
GET    /api/v1/warroom/sn0int/blacklist/{target}

GROUNDSTATION
GET    /api/v1/warroom/satellite/{sat_name}
GET    /api/v1/warroom/satellite/{sat_name}/passes
GET    /api/v1/warroom/satellites/visible

PGROK
POST   /api/v1/warroom/tunnel/start
POST   /api/v1/warroom/tunnel/stop
GET    /api/v1/warroom/tunnel/status

RAG CHAT (Phase 9)
POST   /api/v1/chat
GET    /api/v1/remembered-context/{user_id}
```

---

## 🔌 WebSocket Real-Time

```python
# routes/warroom_ws.py

from fastapi import WebSocket
import json
import asyncio

class WarRoomManager:
    def __init__(self):
        self.active_connections = []
        self.update_tasks = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast_update(self, data: Dict):
        """Send update to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                pass
    
    async def start_live_feeds(self):
        """Start background tasks for each data source."""
        loop = asyncio.get_event_loop()
        
        # Ships update every 10 seconds
        loop.create_task(self._ship_feed())
        
        # Markets update every 5 seconds
        loop.create_task(self._market_feed())
        
        # Conflicts every 30 seconds
        loop.create_task(self._conflict_feed())
        
        # Satellites every 20 seconds
        loop.create_task(self._satellite_feed())
    
    async def _ship_feed(self):
        while True:
            ships = await geosentisnl.get_active_ships()
            await self.broadcast_update({
                'type': 'ships_update',
                'data': ships,
                'timestamp': datetime.utcnow().isoformat()
            })
            await asyncio.sleep(10)
    
    async def _market_feed(self):
        while True:
            markets = await tvscreener.get_screener_results('forex')
            await self.broadcast_update({
                'type': 'markets_update',
                'data': markets,
                'timestamp': datetime.utcnow().isoformat()
            })
            await asyncio.sleep(5)
    
    async def _conflict_feed(self):
        while True:
            conflicts = await worldmonitor.get_conflict_zones()
            await self.broadcast_update({
                'type': 'conflicts_update',
                'data': conflicts,
                'timestamp': datetime.utcnow().isoformat()
            })
            await asyncio.sleep(30)
    
    async def _satellite_feed(self):
        while True:
            iss = await groundstation.get_satellite_position('ISS')
            await self.broadcast_update({
                'type': 'satellite_update',
                'data': iss,
                'timestamp': datetime.utcnow().isoformat()
            })
            await asyncio.sleep(20)

manager = WarRoomManager()

@app.websocket("/ws/warroom")
async def websocket_warroom(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming commands
            cmd = json.loads(data)
            if cmd['type'] == 'request_full_update':
                # Send all current data
                await websocket.send_json({
                    'type': 'full_update',
                    'ships': await geosentisnl.get_active_ships(),
                    'conflicts': await worldmonitor.get_conflict_zones(),
                    'markets': await tvscreener.get_screener_results('forex')
                })
    except:
        manager.disconnect(websocket)
```

**Client-side (HTML):**

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8001/ws/warroom');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'ships_update') {
        updateShipMarkers(message.data);
    } else if (message.type === 'markets_update') {
        updateTickerScroll(message.data);
    } else if (message.type === 'conflicts_update') {
        updateConflictLayers(message.data);
    } else if (message.type === 'satellite_update') {
        updateSatellitePosition(message.data);
    }
};

ws.send(JSON.stringify({ type: 'request_full_update' }));
```

---

## 📊 Data Models

```python
# models/warroom_models.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Ship(BaseModel):
    mmsi: str
    name: str
    callsign: str
    latitude: float
    longitude: float
    speed_knots: float
    heading: int
    timestamp: datetime

class AirCraft(BaseModel):
    icao: str
    callsign: str
    latitude: float
    longitude: float
    altitude_ft: int
    speed_knots: float
    aircraft_type: str
    timestamp: datetime

class ConflictZone(BaseModel):
    name: str
    latitude: float
    longitude: float
    severity_score: int  # 0-100
    type: str  # 'military', 'protest', 'disaster'
    active_since: datetime
    description: str

class MarketData(BaseModel):
    symbol: str
    price: float
    change_pct: float
    volume: int
    high_24h: float
    low_24h: float

class DomainIntel(BaseModel):
    domain: str
    whois: Dict
    dns: Dict
    subdomains: List[str]
    tech_stack: List[str]
    ssl_cert: Dict
    risk_score: int

class Satellite(BaseModel):
    name: str
    latitude: float
    longitude: float
    altitude_km: float
    velocity_kms: float

class WarRoomUpdate(BaseModel):
    type: str  # 'ships_update', 'conflicts_update', etc.
    data: Dict
    timestamp: datetime
```

---

## 🚀 Deployment

**Requirements:**

```
fastapi==0.104.1
aiohttp==3.9.0
websockets==12.0
skyfield==1.46
pydantic==2.5.0
redis==5.0.0
celery==5.3.0
# Optional:
tvdatafeed==1.13.0
requests==2.31.0
```

**Docker:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Start FastAPI + WebSocket + background workers
CMD uvicorn api.main:app\
    --host 0.0.0.0\
    --port 8000\
    --workers 4
```

**Environment Variables:**

```
# .env
GEOSENTIANEL_API_KEY=xxx
WORLDMONITOR_API_KEY=xxx
TVSCREENER_API_KEY=xxx
SIGHTLINE_OSM_KEY=xxx
WEBOSINT_API_KEY=xxx
SN0INT_API_URL=http://localhost:8080
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://...
PGROK_TOKEN=xxx
```

---

## ✅ Checklist de Integración

- [ ] Endpoint `/api/v1/warroom/ships` funcionando
- [ ] Endpoint `/api/v1/warroom/cii` trayendo datos
- [ ] Endpoint `/api/v1/warroom/markets` con tvscreener live
- [ ] WebSocket `/ws/warroom` broadcast working
- [ ] Mapa Leaflet recibiendo marcadores de GeoSentinel
- [ ] Ticker financiero scrolling en tiempo real
- [ ] Tab Domain OSINT consultando WebOSINT
- [ ] Tab Satélites mostrando ISS positioning
- [ ] pgrok túnel exposición pública
- [ ] Sistema RAG integrado en chat principal

---

**Status:** Ready to build  
**Estimated effort:** 80-120 horas  
**Team:** 2 backend engineers  
**Phase:** War Room v1.0 (Post Phase 10)

