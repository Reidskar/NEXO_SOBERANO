"""
Phase 9 Setup: Quick initialization for Polymarket, Smart Donations, and Link Security
"""

from backend.services.polymarket_service import PolymarketService
from backend.services.smart_donation_system import SmartDonationSystem
from backend.services.link_security_service import LinkSecurityService
import json
from datetime import datetime

class Phase9Setup:
    """Setup automation para servicios de Phase 9."""
    
    def __init__(self):
        self.polymarket = PolymarketService()
        self.donations = SmartDonationSystem()
        self.security = LinkSecurityService()
        log.info("✅ Phase 9 Services Initialized")
    
    def setup_demo_channel(self, channel_id: str = "nexo_demo_channel") -> Dict:
        """Setup completo con datos de demostración."""
        log.info(f"\n🚀 Setting up Phase 9 for channel: {channel_id}")
        
        # 1. Crear mercados de demostración
        log.info("\n1️⃣ Creating demonstration markets...")
        markets = []
        
        market_configs = [
            {
                "name": "Will channel reach 100K subscribers?",
                "category": "channel_growth",
                "liquidity": 500.0
            },
            {
                "name": "Will next article get 50K views?",
                "category": "content_performance",
                "liquidity": 300.0
            },
            {
                "name": "Will engagement rate exceed 10%?",
                "category": "analytics",
                "liquidity": 200.0
            }
        ]
        
        for config in market_configs:
            market = self.polymarket.create_market(
                market_name=config["name"],
                category=config["category"],
                initial_liquidity=config["liquidity"]
            )
            markets.append(market)
            log.info(f"   ✅ Created market: {config['name']}")
        
        # 2. Setup contenido del canal
        log.info("\n2️⃣ Adding sample content to catalog...")
        content_items = [
            {
                "content_id": "article_startup_guide",
                "title": "Complete Startup Guide 2024",
                "duration": 2400,  # 40 minutes
                "category": "entrepreneurship"
            },
            {
                "content_id": "video_social_media",
                "title": "Social Media Strategy Masterclass",
                "duration": 3600,  # 60 minutes
                "category": "marketing"
            },
            {
                "content_id": "guide_ai_tools",
                "title": "Essential AI Tools for Creators",
                "duration": 1800,  # 30 minutes
                "category": "technology"
            }
        ]
        
        for item in content_items:
            result = self.donations.add_content_to_catalog(
                channel_id=channel_id,
                content_id=item["content_id"],
                title=item["title"],
                duration_seconds=item["duration"],
                category=item["category"],
                tags=item["category"].lower().split()
            )
            log.info(f"   ✅ Content added: {item['title']}")
        
        # 3. Calcular valuación
        log.info("\n3️⃣ Calculating screen time valuations...")
        valuation = self.donations.calculate_screen_time_value(
            channel_id=channel_id,
            viewers_count=1000,
            engagement_rate=0.85,
            cpm_base=5.0
        )
        log.info(f"   ✅ Current valuations established:")
        log.info(f"      • Price per second: ${valuation['price_per_second']:.4f}")
        log.info(f"      • Price per minute: ${valuation['price_per_minute']:.2f}")
        log.info(f"      • Price per hour: ${valuation['price_per_hour']:.2f}")
        
        # 4. Demo donaciones
        log.info("\n4️⃣ Creating sample donations...")
        donors = [
            {"donor_id": "demo_supporter_1", "amount": 50.0},
            {"donor_id": "demo_supporter_2", "amount": 100.0},
            {"donor_id": "demo_supporter_3", "amount": 75.0}
        ]
        
        for donor in donors:
            donation = self.donations.process_donation(
                donor_id=donor["donor_id"],
                channel_id=channel_id,
                donation_amount=donor["amount"]
            )
            minutes = int(donation['screen_time_seconds'] // 60)
            seconds = int(donation['screen_time_seconds'] % 60)
            log.info(f"   ✅ {donor['donor_id']}: ${donor['amount']} = {minutes}m {seconds}s")
        
        # 5. Whitelist dominios seguros
        log.info("\n5️⃣ Whitelisting trusted domains...")
        safe_domains = [
            "github.com",
            "nexo.ai",
            "medium.com",
            "dev.to",
            "youtube.com"
        ]
        
        for domain in safe_domains:
            self.security.whitelist_domain(domain, f"Trusted domain for {channel_id}")
            log.info(f"   ✅ {domain}")
        
        # 6. Realizar apuestas de demo
        log.info("\n6️⃣ Placing demo bets...")
        if markets:
            market_id = markets[0]['market_id']
            for idx, donor in enumerate(donors):
                amount = 25.0 + (idx * 10)
                bet = self.polymarket.place_bet(
                    market_id=market_id,
                    user_id=donor["donor_id"],
                    position_type="yes" if idx % 2 == 0 else "no",
                    amount=amount
                )
                log.info(f"   ✅ Bet placed by {donor['donor_id']}: ${amount}")
        
        summary = {
            'status': 'success',
            'channel_id': channel_id,
            'timestamp': datetime.now().isoformat(),
            'setup_completed': {
                'markets_created': len(markets),
                'content_items': len(content_items),
                'demo_donations': len(donors),
                'whitelisted_domains': len(safe_domains)
            },
            'markets': markets,
            'valuation': valuation
        }
        
        return summary
    
    def setup_channel_with_custom_config(self, 
                                        channel_id: str,
                                        config: dict) -> dict:
        """Setup con configuración personalizada."""
        log.info(f"\n🎯 Custom setup for {channel_id}")
        
        # Validar contenido
        if 'content' in config:
            for item in config['content']:
                self.donations.add_content_to_catalog(
                    channel_id=channel_id,
                    content_id=item.get('id', f'content_{datetime.now().timestamp()}'),
                    title=item.get('title', 'Untitled'),
                    duration_seconds=item.get('duration', 600),
                    category=item.get('category', 'general')
                )
        
        # Crear mercados personalizados
        if 'markets' in config:
            for market_config in config['markets']:
                self.polymarket.create_market(
                    market_name=market_config.get('name'),
                    category=market_config.get('category', 'general'),
                    initial_liquidity=market_config.get('liquidity', 500.0)
                )
        
        # Whitelist personalizado
        if 'safe_domains' in config:
            for domain in config['safe_domains']:
                self.security.whitelist_domain(domain, f"Custom whitelist for {channel_id}")
        
        return {'status': 'success', 'channel_id': channel_id}
    
    def health_check(self) -> dict:
        """Verificar salud de todos los servicios."""
        log.info("\n🏥 Phase 9 Health Check")
        
        checks = {
            'polymarket': self._check_polymarket(),
            'donations': self._check_donations(),
            'security': self._check_security()
        }
        
        all_healthy = all(checks.values())
        log.info(f"\n📊 Overall Status: {'✅ Healthy' if all_healthy else '❌ Issues detected'}")
        
        return {
            'status': 'healthy' if all_healthy else 'degraded',
            'services': checks,
            'timestamp': datetime.now().isoformat()
        }
    
    def _check_polymarket(self) -> bool:
        """Verificar servicio de Polymarket."""
        try:
            # Try to access database
            self.polymarket._conn()
            log.info("   ✅ Polymarket")
            return True
        except Exception as e:
            log.info(f"   ❌ Polymarket: {str(e)}")
            return False
    
    def _check_donations(self) -> bool:
        """Verificar servicio de donaciones."""
        try:
            self.donations._conn()
            log.info("   ✅ Smart Donations")
            return True
        except Exception as e:
            log.info(f"   ❌ Smart Donations: {str(e)}")
            return False
    
    def _check_security(self) -> bool:
        """Verificar servicio de seguridad."""
        try:
            self.security._conn()
            log.info("   ✅ Link Security")
            return True
        except Exception as e:
            log.info(f"   ❌ Link Security: {str(e)}")
            return False
    
    def export_channel_config(self, channel_id: str) -> dict:
        """Exportar configuración de canal completa."""
        try:
            return {
                'status': 'success',
                'channel_id': channel_id,
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'donations_analytics': self.donations.get_channel_donation_analytics(
                        channel_id, days=30
                    ),
                    'threat_intelligence': self.security.get_threat_intelligence()
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def print_setup_summary(self, setup_result: dict):
        """Imprimir resumen de setup."""
        log.info("\n" + "="*70)
        log.info("🎯 PHASE 9 SETUP COMPLETE")
        log.info("="*70)
        
        if setup_result.get('status') == 'success':
            completed = setup_result.get('setup_completed', {})
            log.info(f"\n✅ Channel: {setup_result.get('channel_id')}")
            log.info(f"   • Markets created: {completed.get('markets_created', 0)}")
            log.info(f"   • Content items: {completed.get('content_items', 0)}")
            log.info(f"   • Demo donations: {completed.get('demo_donations', 0)}")
            log.info(f"   • Whitelisted domains: {completed.get('whitelisted_domains', 0)}")
            
            val = setup_result.get('valuation', {})
            log.info(f"\n💰 Screen Time Valuations:")
            log.info(f"   • Per second: ${val.get('price_per_second', 0):.4f}")
            log.info(f"   • Per minute: ${val.get('price_per_minute', 0):.2f}")
            log.info(f"   • Per hour: ${val.get('price_per_hour', 0):.2f}")
        else:
            log.info(f"\n❌ Setup failed: {setup_result.get('message', 'Unknown error')}")
        
        log.info("\n" + "="*70)

def quick_setup():
    """Quick setup function para uso inmediato."""
    setup = Phase9Setup()
    result = setup.setup_demo_channel()
    setup.print_setup_summary(result)
    return setup

if __name__ == "__main__":
    log.info("Phase 9 Setup Automation")
    setup = quick_setup()
    setup.health_check()
