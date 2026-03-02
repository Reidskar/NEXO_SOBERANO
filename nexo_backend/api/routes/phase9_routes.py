"""
API Routes Integration for Phase 9 Services
Rutas FastAPI para Polymarket, Smart Donations y Link Security
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional, List
from pydantic import BaseModel
from backend.services.polymarket_service import PolymarketService, LinkRiskLevel
from backend.services.smart_donation_system import SmartDonationSystem
from backend.services.link_security_service import LinkSecurityService
import json
from datetime import datetime

# Inicializar servicios
polymarket_service = PolymarketService()
donation_service = SmartDonationSystem()
security_service = LinkSecurityService()

# Crear routers
polymarket_router = APIRouter(prefix="/api/markets", tags=["Polymarket"])
donation_router = APIRouter(prefix="/api/donations", tags=["Donations"])
security_router = APIRouter(prefix="/api/security", tags=["Security"])

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class CreateMarketRequest(BaseModel):
    market_name: str
    market_description: Optional[str] = None
    category: str
    initial_liquidity: float

class PlaceBetRequest(BaseModel):
    market_id: int
    user_id: str
    position_type: str  # "yes" or "no"
    amount: float

class DonationRequest(BaseModel):
    donor_id: str
    channel_id: str
    donation_amount: float
    currency: str = "USD"
    content_preferences: Optional[List[str]] = None

class URLScanRequest(BaseModel):
    url: str
    context: str = "general"  # "general", "youtube", "social_media"
    channel_id: Optional[str] = None

class ContentRequest(BaseModel):
    channel_id: str
    content_id: str
    content_title: str
    duration_seconds: int
    content_type: str = "video"
    category: str = "general"
    tags: Optional[List[str]] = None
    description: Optional[str] = None

# ============================================================================
# POLYMARKET ROUTES
# ============================================================================

@polymarket_router.post("/create")
async def create_market(request: CreateMarketRequest) -> Dict:
    """Crear nuevo mercado de predicción."""
    try:
        market = polymarket_service.create_market(
            market_name=request.market_name,
            market_description=request.market_description,
            category=request.category,
            initial_liquidity=request.initial_liquidity
        )
        return {'status': 'success', 'data': market}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@polymarket_router.get("/{market_id}")
async def get_market(market_id: int) -> Dict:
    """Obtener detalles del mercado."""
    try:
        market = polymarket_service._get_market_details(market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")
        return {'status': 'success', 'data': market}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@polymarket_router.get("/")
async def list_markets(limit: int = 20, offset: int = 0) -> Dict:
    """Listar todos los mercados."""
    try:
        markets = polymarket_service.get_all_markets(limit=limit, offset=offset)
        return {
            'status': 'success',
            'data': markets,
            'limit': limit,
            'offset': offset
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@polymarket_router.post("/{market_id}/bets")
async def place_bet(market_id: int, request: PlaceBetRequest) -> Dict:
    """Ejecutar apuesta en mercado."""
    try:
        bet = polymarket_service.place_bet(
            market_id=market_id,
            user_id=request.user_id,
            position_type=request.position_type,
            amount=request.amount
        )
        return {'status': 'success', 'data': bet}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@polymarket_router.get("/{market_id}/probability")
async def get_probability(market_id: int) -> Dict:
    """Obtener probabilidades del mercado."""
    try:
        prob = polymarket_service.get_market_probability(market_id)
        return {'status': 'success', 'data': prob}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@polymarket_router.get("/{market_id}/insights")
async def get_insights(market_id: int) -> Dict:
    """Obtener análisis profesional del mercado."""
    try:
        insights = polymarket_service.get_market_insights(market_id)
        return {'status': 'success', 'data': insights}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@polymarket_router.get("/{market_id}/leaderboard")
async def get_leaderboard(market_id: int, limit: int = 10) -> Dict:
    """Obtener leaderboard de traders."""
    try:
        leaderboard = polymarket_service.get_market_leaderboard(market_id, limit)
        return {'status': 'success', 'data': leaderboard}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@polymarket_router.post("/{market_id}/resolve")
async def resolve_market(market_id: int, outcome: str) -> Dict:
    """Resolver mercado con resultado."""
    try:
        resolution = polymarket_service.resolve_market(market_id, outcome)
        return {'status': 'success', 'data': resolution}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@polymarket_router.get("/{market_id}/analytics")
async def get_analytics(market_id: int, days: int = 30) -> Dict:
    """Obtener analíticas históricas del mercado."""
    try:
        analytics = polymarket_service.get_market_analytics(market_id, days)
        return {'status': 'success', 'data': analytics}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# DONATION ROUTES
# ============================================================================

@donation_router.post("/process")
async def process_donation(request: DonationRequest) -> Dict:
    """Procesar donación de viewer."""
    try:
        donation = donation_service.process_donation(
            donor_id=request.donor_id,
            channel_id=request.channel_id,
            donation_amount=request.donation_amount,
            currency=request.currency,
            content_preferences=request.content_preferences
        )
        return {'status': 'success', 'data': donation}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@donation_router.get("/valuations/{channel_id}")
async def get_valuations(channel_id: str, viewers_count: int = 1000,
                        engagement_rate: float = 0.85) -> Dict:
    """Obtener valuación actual de tiempo en pantalla."""
    try:
        valuation = donation_service.calculate_screen_time_value(
            channel_id=channel_id,
            viewers_count=viewers_count,
            engagement_rate=engagement_rate
        )
        return {'status': 'success', 'data': valuation}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@donation_router.get("/dashboard/{donor_id}")
async def get_donor_dashboard(donor_id: str, channel_id: Optional[str] = None) -> Dict:
    """Obtener dashboard del donor."""
    try:
        dashboard = donation_service.get_donor_dashboard(donor_id, channel_id)
        return {'status': 'success', 'data': dashboard}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@donation_router.get("/analytics/{channel_id}")
async def get_donation_analytics(channel_id: str, days: int = 30) -> Dict:
    """Obtener analíticas de donaciones del canal."""
    try:
        analytics = donation_service.get_channel_donation_analytics(channel_id, days)
        return {'status': 'success', 'data': analytics}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@donation_router.get("/content/{channel_id}")
async def get_available_content(channel_id: str, donor_id: Optional[str] = None,
                               content_type: Optional[str] = None) -> Dict:
    """Obtener contenido disponible para el channel."""
    try:
        content = donation_service.get_available_content(
            channel_id=channel_id,
            donor_id=donor_id,
            content_type=content_type
        )
        return {'status': 'success', 'data': content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@donation_router.post("/content/add")
async def add_content(request: ContentRequest) -> Dict:
    """Agregar contenido al catálogo."""
    try:
        result = donation_service.add_content_to_catalog(
            channel_id=request.channel_id,
            content_id=request.content_id,
            title=request.content_title,
            duration_seconds=request.duration_seconds,
            content_type=request.content_type,
            category=request.category,
            tags=request.tags,
            description=request.description
        )
        return {'status': 'success', 'data': result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@donation_router.post("/screen-time/redeem")
async def redeem_screen_time(donation_id: int, content_id: str,
                            content_title: str, seconds_watched: int) -> Dict:
    """Registrar visualización de contenido."""
    try:
        result = donation_service.redeem_screen_time(
            donation_id=donation_id,
            content_id=content_id,
            content_title=content_title,
            seconds_watched=seconds_watched
        )
        return {'status': 'success', 'data': result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# SECURITY ROUTES
# ============================================================================

@security_router.post("/scan")
async def scan_url(request: URLScanRequest) -> Dict:
    """Escanear URL para riesgos de seguridad."""
    try:
        result = security_service.scan_url(request.url, context=request.context)
        return {'status': 'success', 'data': result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@security_router.post("/validate")
async def validate_before_posting(request: URLScanRequest,
                                 content_id: Optional[str] = None) -> Dict:
    """Validar URL antes de permitir publicación."""
    try:
        if not request.channel_id:
            raise HTTPException(status_code=400, detail="channel_id required")
        
        result = security_service.validate_before_posting(
            channel_id=request.channel_id,
            url=request.url,
            content_id=content_id
        )
        return {'status': 'success', 'data': result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@security_router.get("/report/{channel_id}")
async def get_security_report(channel_id: str, days: int = 30) -> Dict:
    """Obtener reporte de seguridad del canal."""
    try:
        report = security_service.get_security_report(channel_id, days)
        return {'status': 'success', 'data': report}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@security_router.post("/whitelist")
async def whitelist_domain(domain: str, reason: str,
                          added_by: str = "system") -> Dict:
    """Agregar dominio a whitelist."""
    try:
        result = security_service.whitelist_domain(domain, reason, added_by)
        return {'status': 'success', 'data': result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@security_router.post("/block-pattern")
async def block_pattern(pattern: str, pattern_type: str,
                       severity: str = "medium") -> Dict:
    """Agregar patrón de URL a lista de bloqueo."""
    try:
        result = security_service.block_url_pattern(pattern, pattern_type, severity)
        return {'status': 'success', 'data': result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@security_router.get("/threats")
async def get_threat_intelligence() -> Dict:
    """Obtener inteligencia de amenazas actual."""
    try:
        threats = security_service.get_threat_intelligence()
        return {'status': 'success', 'data': threats}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@security_router.get("/health")
async def health_check() -> Dict:
    """Health check para seguridad."""
    try:
        return {
            'status': 'healthy',
            'service': 'link_security',
            'timestamp': datetime.now().isoformat(),
            'threats': security_service.get_threat_intelligence()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FUNCIONES PARA INTEGRACIÓN EN main.py
# ============================================================================

def register_phase9_routes(app):
    """
    Registrar todas las rutas de Phase 9 en la aplicación FastAPI.
    
    Uso en main.py:
    ```python
    from api.routes.phase9_routes import register_phase9_routes
    
    app = FastAPI()
    register_phase9_routes(app)
    ```
    """
    app.include_router(polymarket_router)
    app.include_router(donation_router)
    app.include_router(security_router)
    
    log.info("✅ Phase 9 routes registered:")
    log.info("   - /api/markets")
    log.info("   - /api/donations")
    log.info("   - /api/security")

# ============================================================================
# ENDPOINTS SUMMARY
# ============================================================================

"""
POLYMARKET ENDPOINTS:
├─ POST   /api/markets/create              Create prediction market
├─ GET    /api/markets                     List all markets
├─ GET    /api/markets/{market_id}         Get market details
├─ POST   /api/markets/{market_id}/bets    Place bet
├─ GET    /api/markets/{market_id}/probability  Get probabilities
├─ GET    /api/markets/{market_id}/insights    Get market insights
├─ GET    /api/markets/{market_id}/leaderboard Get top traders
├─ POST   /api/markets/{market_id}/resolve Resolve market
└─ GET    /api/markets/{market_id}/analytics   Get historical data

DONATION ENDPOINTS:
├─ POST   /api/donations/process           Process donation
├─ GET    /api/donations/valuations/{channel_id}  Get screen time price
├─ GET    /api/donations/dashboard/{donor_id}    Get donor dashboard
├─ GET    /api/donations/analytics/{channel_id}  Get channel analytics
├─ GET    /api/donations/content/{channel_id}    List available content
├─ POST   /api/donations/content/add       Add content to catalog
└─ POST   /api/donations/screen-time/redeem       Register viewing

SECURITY ENDPOINTS:
├─ POST   /api/security/scan               Scan URL for risks
├─ POST   /api/security/validate           Validate before posting
├─ GET    /api/security/report/{channel_id} Get security report
├─ POST   /api/security/whitelist          Whitelist domain
├─ POST   /api/security/block-pattern      Block URL pattern
├─ GET    /api/security/threats            Get threat intelligence
└─ GET    /api/security/health             Health check
"""

if __name__ == "__main__":
    log.info("Phase 9 API Routes Module")
    log.info("Import and use register_phase9_routes(app) in your main FastAPI app")
