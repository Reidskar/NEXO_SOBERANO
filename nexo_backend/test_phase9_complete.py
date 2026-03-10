"""
PHASE 9 COMPLETE: Test & Demo para Polymarket + Smart Donations + Link Security
Demuestra la integración completa del sistema económico y de seguridad de Nexo
"""

import sys
import json
import os
import logging
from datetime import datetime

# Ensure backend services directory is on sys.path so we can import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_services = os.path.join(project_root, "backend", "services")
sys.path.insert(0, backend_services)

legacy_services = os.path.join(
    project_root,
    "nexo_backend",
    "backend_legacy_dup_20260301",
    "services",
)
if os.path.isdir(legacy_services):
    sys.path.insert(0, legacy_services)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

try:
    # Try to import from the services directory
    try:
        from polymarket_service import PolymarketService
        from smart_donation_system import SmartDonationSystem
        from link_security_service import LinkSecurityService
    except (ModuleNotFoundError, ImportError):
        # If not found, try importing from current directory
        import importlib.util
        import sys
        
        # Try to locate the modules in the nexo_backend directory
        nexo_backend_dir = os.path.dirname(__file__)
        
        # Helper function to import module from file path
        def import_from_path(module_name, file_name):
            file_path = os.path.join(nexo_backend_dir, file_name)
            if not os.path.exists(file_path):
                raise ModuleNotFoundError(f"Module {module_name} not found at {file_path}")
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                raise ModuleNotFoundError(f"Cannot load module {module_name} from {file_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        
        polymarket_module = import_from_path("polymarket_service", "polymarket_service.py")
        PolymarketService = polymarket_module.PolymarketService
        
        donation_module = import_from_path("smart_donation_system", "smart_donation_system.py")
        SmartDonationSystem = donation_module.SmartDonationSystem
        
        link_security_module = import_from_path("link_security_service", "link_security_service.py")
        LinkSecurityService = link_security_module.LinkSecurityService
        
except ModuleNotFoundError as exc:
    try:
        import pytest
        pytest.skip(f"Phase 9 demo dependencies not available: {exc}", allow_module_level=True)
    except Exception:
        raise

def print_header(title: str):
    """Imprimir encabezado decorativo."""
    log.info("\n" + "="*80)
    log.info(f"🎯 {title}")
    log.info("="*80)

def demo_polymarket():
    """Demostración del sistema de mercados de predicción."""
    print_header("POLYMARKET: Prediction Markets for Content Metrics")
    
    service = PolymarketService()
    
    # 1. Crear mercado de predicción
    log.info("\n1️⃣ Creating Prediction Market...")
    market = service.create_market(
        market_name="Will Article reach 100K views?",
        description="Prediction market for article virality",
        category="content_performance",
        initial_liquidity=1000.0
    )
    log.info(f"✅ Market created: {market}")
    market_id = market['market_id']
    
    # 2. Obtener probabilidad inicial
    log.info("\n2️⃣ Getting Market Probability...")
    prob = service.get_market_probability(market_id)
    log.info(f"✅ Probability: {prob}")
    
    # 3. Realizar apuestas (trades)
    log.info("\n3️⃣ Placing Bets (Trades)...")
    bet1 = service.place_bet(market_id, "user_alice", "yes", 250.0)
    log.info(f"✅ Bet 1: {bet1}")
    
    bet2 = service.place_bet(market_id, "user_bob", "no", 150.0)
    log.info(f"✅ Bet 2: {bet2}")
    
    # 4. Verificar cambio en probabilidad
    log.info("\n4️⃣ Updated Probability After Trades...")
    new_prob = service.get_market_probability(market_id)
    log.info(f"✅ New probability: {new_prob}")
    
    # 5. Obtener insights
    log.info("\n5️⃣ Getting Market Insights...")
    insights = service.get_market_insights(market_id)
    log.info(f"✅ Insights: {json.dumps(insights, indent=2)}")
    
    # 6. Resolver mercado
    log.info("\n6️⃣ Resolving Market...")
    resolution = service.resolve_market(market_id, "yes")
    log.info(f"✅ Market resolved: {resolution}")
    
    # 7. Obtener leaderboard
    log.info("\n7️⃣ Getting Market Leaderboard...")
    leaderboard = service.get_market_leaderboard(market_id)
    log.info(f"✅ Leaderboard: {json.dumps(leaderboard, indent=2)}")

def demo_smart_donations():
    """Demostración del sistema de donaciones inteligentes."""
    print_header("SMART DONATIONS: Dynamic Screen Time Valuation")
    
    service = SmartDonationSystem()
    channel_id = "nexo_channel_001"
    
    # 1. Calcular valor de tiempo en pantalla
    log.info("\n1️⃣ Calculating Screen Time Value...")
    log.info("Scenario: 1000 viewers, 85% engagement rate, $5 base CPM")
    
    valuation = service.calculate_screen_time_value(
        channel_id=channel_id,
        viewers_count=1000,
        engagement_rate=0.85,
        cpm_base=5.0
    )
    log.info(f"✅ Valuation: {json.dumps(valuation, indent=2)}")
    
    # 2. Agregar contenido al catálogo
    log.info("\n2️⃣ Adding Content to Catalog...")
    service.add_content_to_catalog(
        channel_id=channel_id,
        content_id="article_001",
        title="¿Cómo crear una startup exitosa?",
        duration_seconds=1200,  # 20 minutos
        content_type="article",
        category="entrepreneurship",
        tags=["startup", "business", "tips"],
        description="Guía completa para emprendedores"
    )
    log.info("✅ Content added to catalog")
    
    # 3. Procesar donaciones
    log.info("\n3️⃣ Processing Donations...")
    
    donation1 = service.process_donation(
        donor_id="donor_alice",
        channel_id=channel_id,
        donation_amount=50.0,
        currency="USD",
        content_preferences=["entrepreneurship", "technology"]
    )
    log.info(f"✅ Donation 1: {json.dumps(donation1, indent=2)}")
    
    donation2 = service.process_donation(
        donor_id="donor_bob",
        channel_id=channel_id,
        donation_amount=100.0,
        currency="USD",
        content_preferences=["marketing", "social"]
    )
    log.info(f"✅ Donation 2: {json.dumps(donation2, indent=2)}")
    
    # 4. Ver contenido disponible
    log.info("\n4️⃣ Getting Available Content...")
    content = service.get_available_content(channel_id, donor_id="donor_alice")
    log.info(f"✅ Available content: {json.dumps(content, indent=2)}")
    
    # 5. Dashboard del donor
    log.info("\n5️⃣ Donor Dashboard...")
    dashboard = service.get_donor_dashboard("donor_alice", channel_id)
    log.info(f"✅ Dashboard: {json.dumps(dashboard, indent=2)}")
    
    # 6. Analíticas del canal
    log.info("\n6️⃣ Channel Donation Analytics...")
    analytics = service.get_channel_donation_analytics(channel_id, days=30)
    log.info(f"✅ Analytics: {json.dumps(analytics, indent=2)}")

def demo_link_security():
    """Demostración del sistema de seguridad de links."""
    print_header("LINK SECURITY: URL Validation & Channel Protection")
    
    service = LinkSecurityService()
    channel_id = "nexo_channel_001"
    
    # 1. Escanear URL segura
    log.info("\n1️⃣ Scanning Safe URL...")
    safe_url_scan = service.scan_url("https://github.com/nexo-soberano/docs")
    log.info(f"✅ Result: {json.dumps(safe_url_scan, indent=2)}")
    
    # 2. Escanear URL sospechosa
    log.info("\n2️⃣ Scanning Suspicious URL...")
    suspicious_url = "https://bit.ly/phishing-attack-youtube-delete"
    suspicious_scan = service.scan_url(suspicious_url)
    log.info(f"✅ Result: {json.dumps(suspicious_scan, indent=2)}")
    
    # 3. Escanear URL de eliminación de canal
    log.info("\n3️⃣ Scanning Channel Deletion Risk...")
    deletion_risk_url = "https://studio.youtube.com/channel/ABC123/settings/advanced/delete"
    deletion_scan = service.scan_url(deletion_risk_url, context='youtube')
    log.info(f"✅ Result: {json.dumps(deletion_scan, indent=2)}")
    
    # 4. Validar antes de publicar
    log.info("\n4️⃣ Validate Before Posting...")
    validation = service.validate_before_posting(
        channel_id=channel_id,
        url="https://github.com/nexo-soberano",
        content_id="post_001"
    )
    log.info(f"✅ Validation: {json.dumps(validation, indent=2)}")
    
    # 5. Whitelist dominio personalizado
    log.info("\n5️⃣ Whitelisting Custom Domain...")
    whitelist = service.whitelist_domain(
        domain="partner.nexo.ai",
        reason="Partner integration platform",
        added_by="admin"
    )
    log.info(f"✅ Whitelist: {whitelist}")
    
    # 6. Reporte de seguridad
    log.info("\n6️⃣ Security Report...")
    report = service.get_security_report(channel_id)
    log.info(f"✅ Report: {json.dumps(report, indent=2)}")
    
    # 7. Inteligencia de amenazas
    log.info("\n7️⃣ Threat Intelligence...")
    threat_intel = service.get_threat_intelligence()
    log.info(f"✅ Threat Intel: {json.dumps(threat_intel, indent=2)}")

def demo_integration():
    """Demostración de integración completa."""
    print_header("INTEGRATION: Complete Phase 9 Workflow")
    
    log.info("\n📋 Workflow Scenario:")
    print("""
    1. Content creator publishes article with prediction market
    2. Users donate to support content AND get voting power
    3. System calculates screen time value based on viewership
    4. Donors get access to premium content based on donations
    5. All links are validated before posting to prevent channel harm
    """)
    
    # Inicializar servicios
    polymarket = PolymarketService()
    donations = SmartDonationSystem()
    link_security = LinkSecurityService()
    
    channel_id = "nexo_channel_demo"
    
    log.info("\n🔄 Step 1: Create prediction market for content...")
    market = polymarket.create_market(
        market_name="Will Nexo reach 100K subscribers?",
        category="channel_growth",
        initial_liquidity=500.0
    )
    log.info(f"   ✅ Market created: ID {market['market_id']}")
    
    log.info("\n🔄 Step 2: Validate link to market...")
    market_link = f"https://nexo.platform/markets/{market['market_id']}"
    link_check = link_security.scan_url(market_link)
    log.info(f"   ✅ Link valid: {link_check['risk_level']}")
    
    log.info("\n🔄 Step 3: Process viewer donations...")
    donation = donations.process_donation(
        donor_id="supporter_001",
        channel_id=channel_id,
        donation_amount=75.0,
        currency="USD"
    )
    log.info(f"   ✅ Donation processed: {donation['donation_amount']}USD = {donation['screen_time_seconds']}s screen time")
    
    log.info("\n🔄 Step 4: Get donation analytics...")
    analytics = donations.get_channel_donation_analytics(channel_id)
    log.info(f"   ✅ Total revenue: ${analytics['total_revenue']}")
    
    log.info("\n🔄 Step 5: Get market probability prediction...")
    prob = polymarket.get_market_probability(market['market_id'])
    log.info(f"   ✅ Market probability: {prob['probability_yes']}% chance of success")
    
    log.info("\n✅ Integration workflow complete!")

def main():
    """Función principal."""
    log.info("\n" + "🎉 "*40)
    log.info("NEXO SOBERANO - PHASE 9: Economic & Security Layer")
    log.info("🎉 "*40)
    
    try:
        # Demo Polymarket
        demo_polymarket()
        
        # Demo Smart Donations
        demo_smart_donations()
        
        # Demo Link Security
        demo_link_security()
        
        # Demo Integration
        demo_integration()
        
        # Resumen final
        print_header("SUMMARY: Phase 9 Complete ✅")
        print("""
✅ POLYMARKET Service
   • Prediction markets for content metrics
   • CFMM pricing algorithm
   • Market resolution & analytics
   • Professional insights & leaderboards

✅ SMART DONATIONS System
   • Dynamic screen time valuation
   • Professional CPM-based pricing
   • Viewer agency through donations
   • Comprehensive donor analytics

✅ LINK SECURITY Service
   • URL scanning & validation
   • Channel deletion protection
   • Threat intelligence
   • Security audit logs

🚀 NEXO is now a complete economic platform with:
   • Marketing infrastructure (Phase 8)
   • Predictive analytics (Polymarket)
   • Dynamic revenue system (Smart Donations)
   • Platform safety (Link Security)

🎯 Next: Integrate into API routes and deploy!
        """)
        
    except Exception as e:
        log.info(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
