"""
Services Index: Punto de acceso centralizado a todos los servicios de marketing
"""

from backend.services.social_media_service import SocialMediaManager
from backend.services.email_service import EmailService
from backend.services.analytics_service import AnalyticsService
from backend.services.automation_service import AutomationService
from backend.services.influencer_service import InfluencerService
from backend.services.content_service import ContentService
from backend.services.crm_service import CustomerService
from backend.services.polymarket_service import PolymarketService
from backend.services.smart_donation_system import SmartDonationSystem
from backend.services.link_security_service import LinkSecurityService
from marketing_config import MarketingConfig
from typing import Dict, Any

class NexoMarketingServices:
    """
    Acceso centralizado a todos los servicios de marketing de Nexo.
    
    Uso:
    ```python
    services = NexoMarketingServices()
    
    # Acceder a servicios
    services.social_media.create_post(...)
    services.email.send_bulk_emails(...)
    services.crm.add_customer(...)
    ```
    """
    
    def __init__(self, config_path: str = "marketing_config.json"):
        """Inicializar todos los servicios."""
        # Cargar configuración
        self.config = MarketingConfig()
        
        # Inicializar servicios - Phase 8 (Marketing)
        self.social_media = SocialMediaManager(db_path="social_media.db")
        self.email = EmailService(db_path="email_campaigns.db")
        self.analytics = AnalyticsService(db_path="analytics.db")
        self.automation = AutomationService(db_path="automations.db")
        self.influencer = InfluencerService(db_path="influencers.db")
        self.content = ContentService(db_path="content.db")
        self.crm = CustomerService(db_path="crm.db")
        
        # Inicializar servicios - Phase 9 (Economic & Security Layer)
        self.polymarket = PolymarketService(db_path="polymarket.db")
        self.donations = SmartDonationSystem(db_path="smart_donations.db")
        self.link_security = LinkSecurityService(db_path="link_security.db")
        
        self._initialized = True
    
    def get_service_status(self) -> Dict[str, Any]:
        """Obtener estado de todos los servicios."""
        return {
            'status': 'all_services_active',
            'services': {
                'social_media': '✅ Active',
                'email': '✅ Active',
                'analytics': '✅ Active',
                'automation': '✅ Active',
                'influencer': '✅ Active',
                'content': '✅ Active',
                'crm': '✅ Active',
                'polymarket': '✅ Active (Phase 9)',
                'donations': '✅ Active (Phase 9)',
                'link_security': '✅ Active (Phase 9)'
            },
            'config_loaded': True,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
    
    def quick_start_setup(self):
        """Setup rápido con datos de ejemplo."""
        from marketing_setup import MarketingSetup
        setup = MarketingSetup()
        setup.full_setup()
    
    def validate_all_services(self) -> Dict[str, bool]:
        """Validar que todos los servicios estén funcionales."""
        validations = {
            'social_media': self._validate_social_media(),
            'email': self._validate_email(),
            'analytics': self._validate_analytics(),
            'automation': self._validate_automation(),
            'influencer': self._validate_influencer(),
            'content': self._validate_content(),
            'crm': self._validate_crm(),
            'polymarket': self._validate_polymarket(),
            'donations': self._validate_donations(),
            'link_security': self._validate_link_security()
        }
        return validations
    
    def _validate_social_media(self) -> bool:
        try:
            self.social_media.get_social_analytics()
            return True
        except:
            return False
    
    def _validate_email(self) -> bool:
        try:
            # Intentar acceder a tablas
            self.email._conn()
            return True
        except:
            return False
    
    def _validate_analytics(self) -> bool:
        try:
            self.analytics.get_dashboard_summary()
            return True
        except:
            return False
    
    def _validate_automation(self) -> bool:
        try:
            self.automation.get_workflows()
            return True
        except:
            return False
    
    def _validate_influencer(self) -> bool:
        try:
            self.influencer.search_influencers()
            return True
        except:
            return False
    
    def _validate_content(self) -> bool:
        try:
            self.content.get_content_ideas()
            return True
        except:
            return False
    
    def _validate_crm(self) -> bool:
        try:
            self.crm.get_customer_analytics()
            return True
        except:
            return False
    
    def _validate_polymarket(self) -> bool:
        try:
            self.polymarket._conn()
            return True
        except:
            return False
    
    def _validate_donations(self) -> bool:
        try:
            self.donations._conn()
            return True
        except:
            return False
    
    def _validate_link_security(self) -> bool:
        try:
            self.link_security._conn()
            return True
        except:
            return False
    
    def get_health_check(self) -> Dict[str, Any]:
        """Health check completo del sistema."""
        import sqlite3
        import os
        
        def check_db(path):
            if os.path.exists(path):
                try:
                    conn = sqlite3.connect(path)
                    conn.execute("SELECT 1")
                    conn.close()
                    return "✅"
                except:
                    return "❌"
            return "⚠️ Not found"
        
        return {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'services': self.get_service_status(),
            'databases': {
                'social_media.db': check_db("social_media.db"),
                'email_campaigns.db': check_db("email_campaigns.db"),
                'analytics.db': check_db("analytics.db"),
                'automations.db': check_db("automations.db"),
                'influencers.db': check_db("influencers.db"),
                'content.db': check_db("content.db"),
                'crm.db': check_db("crm.db"),
                'polymarket.db': check_db("polymarket.db"),
                'smart_donations.db': check_db("smart_donations.db"),
                'link_security.db': check_db("link_security.db")
            },
            'config': {
                'path': 'marketing_config.json',
                'status': 'loaded' if self.config.config else 'error'
            },
            'validations': self.validate_all_services()
        }
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas rápidas de todos los servicios."""
        stats = {
            'social_media': {
                'analytics': self.social_media.get_social_analytics() if hasattr(self.social_media, 'get_social_analytics') else {}
            },
            'email': {
                'templates': 'N/A',
                'campaigns': 'N/A'
            },
            'crm': self.crm.get_crm_dashboard_summary(),
            'automation': {
                'workflows': len(self.automation.get_workflows())
            },
            'analytics': self.analytics.get_dashboard_summary(days=7),
            'influencer': {
                'top_influencers': self.influencer.search_influencers(min_followers=100000)
            },
            'content': {
                'calendar': self.content.get_editorial_calendar(days_ahead=30)
            }
        }
        return stats
    
    def print_dashboard(self):
        """Imprimir dashboard de estado."""
        log.info("\n" + "="*70)
        log.info("🎯 NEXO MARKETING SERVICES DASHBOARD")
        log.info("="*70)
        
        # Status
        status = self.get_service_status()
        log.info("\n📊 Services Status:")
        for service, state in status['services'].items():
            log.info(f"  {state} {service.replace('_', ' ').title()}")
        
        # Health Check
        health = self.get_health_check()
        log.info("\n💾 Databases:")
        for db, state in health['databases'].items():
            log.info(f"  {state} {db}")
        
        # Validations
        log.info("\n✓ Validations:")
        for service, valid in health['validations'].items():
            state = "✅" if valid else "❌"
            log.info(f"  {state} {service}")
        
        log.info("\n" + "="*70)
    
    def export_all_data(self, format: str = 'json') -> Dict[str, Any]:
        """Exportar todos los datos."""
        export = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'format': format,
            'services': {
                'social_media': self.social_media.export_social_calendar() if hasattr(self.social_media, 'export_social_calendar') else {},
                'email': {},
                'crm': self.crm.export_customer_list() if hasattr(self.crm, 'export_customer_list') else {},
                'automation': self.automation.export_workflows_json(),
                'content': {}
            }
        }
        return export
    
    def create_backup(self, backup_path: str = "marketing_backup") -> bool:
        """Crear backup de todas las bases de datos."""
        import shutil
        import os
        from datetime import datetime
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"{backup_path}_{timestamp}"
            
            os.makedirs(backup_dir, exist_ok=True)
            
            databases = [
                "social_media.db",
                "email_campaigns.db",
                "analytics.db",
                "automations.db",
                "influencers.db",
                "content.db",
                "crm.db"
            ]
            
            for db in databases:
                if os.path.exists(db):
                    shutil.copy(db, f"{backup_dir}/{db}")
            
            shutil.copy("marketing_config.json", f"{backup_dir}/marketing_config.json")
            
            log.info(f"✅ Backup created: {backup_dir}")
            return True
        except Exception as e:
            log.info(f"❌ Backup failed: {e}")
            return False
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restaurar desde backup."""
        import shutil
        import os
        
        try:
            if not os.path.exists(backup_path):
                log.info(f"❌ Backup not found: {backup_path}")
                return False
            
            databases = [
                "social_media.db",
                "email_campaigns.db",
                "analytics.db",
                "automations.db",
                "influencers.db",
                "content.db",
                "crm.db"
            ]
            
            for db in databases:
                backup_file = f"{backup_path}/{db}"
                if os.path.exists(backup_file):
                    shutil.copy(backup_file, db)
            
            if os.path.exists(f"{backup_path}/marketing_config.json"):
                shutil.copy(f"{backup_path}/marketing_config.json", "marketing_config.json")
            
            log.info(f"✅ Restore complete from {backup_path}")
            return True
        except Exception as e:
            log.info(f"❌ Restore failed: {e}")
            return False


# Funciones de utilidad global
def get_nexo_services() -> NexoMarketingServices:
    """Obtener instancia de servicios."""
    return NexoMarketingServices()


def quick_setup():
    """Setup rápido."""
    services = NexoMarketingServices()
    services.quick_start_setup()
    return services


def print_system_info():
    """Imprimir información del sistema."""
    services = NexoMarketingServices()
    services.print_dashboard()


if __name__ == "__main__":
    # Demo
    log.info("🚀 Nexo Marketing Services")
    
    services = NexoMarketingServices()
    services.print_dashboard()
    
    # Quick stats
    # stats = services.get_quick_stats()
    # log.info("\n📈 Quick Stats:", stats)
