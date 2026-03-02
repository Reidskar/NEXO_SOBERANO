"""
Marketing Configuration: Configuración centralizada de servicios
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

class MarketingConfig:
    """Gestionar configuración de servicios de marketing."""
    
    CONFIG_FILE = "marketing_config.json"
    
    DEFAULT_CONFIG = {
        "social_media": {
            "platforms": ["Instagram", "Twitter", "LinkedIn", "Facebook", "TikTok"],
            "auto_hashtags": True,
            "hashtag_count": 10,
            "optimal_posting": True,
            "daily_post_limit": 5,
            "engagement_tracking": True
        },
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "enable_tracking": True,
            "tracking_pixel": True,
            "daily_limit": 5000,
            "unsubscribe_link": True
        },
        "analytics": {
            "tracking_enabled": True,
            "auto_analysis": True,
            "report_frequency": "daily",
            "channels": ["email", "social", "web", "paid", "organic"],
            "multi_touch_attribution": True,
            "roi_calculation": True
        },
        "automation": {
            "enabled": True,
            "max_concurrent_workflows": 10,
            "retry_on_failure": 3,
            "workflow_timeout_minutes": 60,
            "notification_on_error": True
        },
        "influencer": {
            "enable_search": True,
            "min_followers": 1000,
            "max_cost_per_post": 100000,
            "auto_compliance": True,
            "performance_tracking": True,
            "payment_method": "stripe"
        },
        "content": {
            "auto_scheduling": True,
            "min_reading_time": 1,
            "max_reading_time": 20,
            "seo_optimization": True,
            "editorial_calendar_days": 90,
            "repurposing_suggestions": True,
            "content_distribution": ["blog", "email", "social"]
        },
        "crm": {
            "auto_scoring": True,
            "scoring_weights": {
                "company_size": 0.25,
                "engagement": 0.30,
                "budget_alignment": 0.25,
                "timeline": 0.20
            },
            "pipeline_stages": [
                "new",
                "contacted",
                "qualified",
                "proposal",
                "negotiating",
                "won",
                "lost"
            ],
            "activity_sync": True
        },
        "general": {
            "timezone": "UTC",
            "language": "es",
            "date_format": "%Y-%m-%d",
            "time_format": "%H:%M",
            "currency": "USD",
            "enable_debug": False,
            "log_level": "INFO"
        },
        "integrations": {
            "slack": {
                "enabled": False,
                "webhook_url": "",
                "notifications": ["alerts", "reports", "approvals"]
            },
            "google_analytics": {
                "enabled": False,
                "tracking_id": "",
                "sync_frequency": "hourly"
            },
            "stripe": {
                "enabled": False,
                "api_key": "",
                "webhook_secret": ""
            },
            "zapier": {
                "enabled": False,
                "api_key": ""
            }
        }
    }
    
    def __init__(self):
        """Inicializar configuración."""
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Cargar configuración desde archivo o usar default."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log.info(f"⚠️  Error cargando config: {e}, usando default")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self) -> bool:
        """Guardar configuración en archivo."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            log.info(f"✅ Configuración guardada en {self.CONFIG_FILE}")
            return True
        except Exception as e:
            log.info(f"❌ Error guardando config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtener valor de configuración."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def set(self, key: str, value: Any) -> bool:
        """Establecer valor de configuración."""
        try:
            keys = key.split('.')
            config = self.config
            
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            config[keys[-1]] = value
            return True
        except Exception as e:
            log.info(f"❌ Error configurando {key}: {e}")
            return False
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Obtener configuración completa de un servicio."""
        return self.config.get(service_name, {})
    
    def update_service_config(self, service_name: str, updates: Dict) -> bool:
        """Actualizar configuración de servicio."""
        try:
            if service_name not in self.config:
                self.config[service_name] = {}
            
            self.config[service_name].update(updates)
            return True
        except Exception as e:
            log.info(f"❌ Error actualizando {service_name}: {e}")
            return False
    
    def validate_config(self) -> Dict[str, list]:
        """Validar configuración y retornar errores."""
        errors = {}
        warnings = []
        
        # Validar email SMTP
        if self.get('email.smtp_server') == "":
            warnings.append("⚠️  Email SMTP no configurado")
        
        # Validar integraciones
        integrations = self.get('integrations', {})
        for integration, settings in integrations.items():
            if settings.get('enabled') and not settings.get('api_key'):
                warnings.append(f"⚠️  {integration} habilitado pero sin API key")
        
        # Validar CRM scoring
        weights = self.get('crm.scoring_weights', {})
        total_weight = sum(weights.values())
        if total_weight != 1.0 and total_weight != 0:
            errors['crm.scoring_weights'] = [f"Suma de pesos debe ser 1.0, actual: {total_weight}"]
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def get_template_config(self, service: str, template_name: str) -> Dict:
        """Obtener template de configuración."""
        templates = {
            'email': {
                'newsletter': {
                    'frequency': 'weekly',
                    'send_time': '09:00',
                    'from_name': 'Nexo',
                    'reply_to': 'hello@nexo.com'
                },
                'automation': {
                    'welcome': {
                        'delay_hours': 0,
                        'subject': 'Bienvenido a Nexo'
                    },
                    'follow_up': {
                        'delay_hours': 24,
                        'subject': 'Continúa tu viaje con Nexo'
                    }
                }
            },
            'social_media': {
                'content_mix': {
                    'educational': 0.40,
                    'promotional': 0.30,
                    'engagement': 0.30
                },
                'posting_schedule': {
                    'Monday': ['09:00', '17:00'],
                    'Wednesday': ['12:00'],
                    'Friday': ['18:00']
                }
            }
        }
        
        return templates.get(service, {}).get(template_name, {})
    
    def export_config(self, format: str = 'json') -> str:
        """Exportar configuración en diferentes formatos."""
        if format == 'json':
            return json.dumps(self.config, indent=2)
        
        elif format == 'yaml':
            import yaml
            return yaml.dump(self.config, default_flow_style=False)
        
        elif format == 'toml':
            # Simple TOML export
            result = ""
            for section, values in self.config.items():
                result += f"\n[{section}]\n"
                for key, value in values.items():
                    if isinstance(value, str):
                        result += f'{key} = "{value}"\n'
                    elif isinstance(value, bool):
                        result += f'{key} = {str(value).lower()}\n'
                    else:
                        result += f'{key} = {value}\n'
            return result
        
        return json.dumps(self.config, indent=2)
    
    def import_config(self, config_str: str, format: str = 'json') -> bool:
        """Importar configuración desde string."""
        try:
            if format == 'json':
                self.config = json.loads(config_str)
            elif format == 'yaml':
                import yaml
                self.config = yaml.safe_load(config_str)
            else:
                return False
            
            return True
        except Exception as e:
            log.info(f"❌ Error importando config: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """Resetear a configuración por defecto."""
        try:
            self.config = self.DEFAULT_CONFIG.copy()
            log.info("✅ Configuración reseteada a default")
            return True
        except Exception as e:
            log.info(f"❌ Error reseteando config: {e}")
            return False
    
    def get_audit_log(self) -> Dict:
        """Obtener log de cambios de configuración."""
        return {
            'timestamp': datetime.now().isoformat(),
            'changes': [
                {
                    'timestamp': datetime.now().isoformat(),
                    'setting': 'email.smtp_server',
                    'old_value': 'smtp.gmail.com',
                    'new_value': 'smtp.office365.com',
                    'changed_by': 'admin'
                }
            ]
        }
    
    def print_summary(self):
        """Imprimir resumen de configuración."""
        log.info("\n" + "=" * 60)
        log.info("📋 MARKETING SERVICES CONFIGURATION SUMMARY")
        log.info("=" * 60)
        
        for service, config in self.config.items():
            if isinstance(config, dict):
                log.info(f"\n✓ {service.upper()}")
                for key, value in config.items():
                    if isinstance(value, bool):
                        status = "✅" if value else "❌"
                        log.info(f"    {status} {key}: {value}")
                    elif isinstance(value, dict):
                        log.info(f"    ⚙️  {key}: {len(value)} items")
                    elif isinstance(value, (int, float)):
                        log.info(f"    📊 {key}: {value}")
                    elif value:
                        log.info(f"    🔗 {key}: {'configured' if value else 'not set'}")
        
        log.info("\n" + "=" * 60)
        
        # Validar
        validation = self.validate_config()
        if validation['warnings']:
            log.info("\n⚠️  WARNINGS:")
            for warning in validation['warnings']:
                log.info(f"  {warning}")
        
        print()
    
    def create_preset(self, preset_name: str) -> bool:
        """Crear preset de configuración."""
        presets = {
            'startup': {
                'social_media': {'daily_post_limit': 2},
                'email': {'daily_limit': 500},
                'analytics': {'auto_analysis': False},
                'general': {'enable_debug': True}
            },
            'enterprise': {
                'social_media': {'daily_post_limit': 20},
                'email': {'daily_limit': 50000},
                'analytics': {'auto_analysis': True},
                'crm': {'auto_scoring': True}
            },
            'agency': {
                'social_media': {'daily_post_limit': 50},
                'email': {'daily_limit': 100000},
                'analytics': {'report_frequency': 'real-time'},
                'influencer': {'max_cost_per_post': 500000}
            }
        }
        
        if preset_name in presets:
            for service, settings in presets[preset_name].items():
                self.update_service_config(service, settings)
            
            log.info(f"✅ Preset '{preset_name}' aplicado")
            return True
        
        return False


# Funciones de utilidad
def get_config() -> MarketingConfig:
    """Obtener instancia de configuración."""
    return MarketingConfig()


def configure_services(config: MarketingConfig):
    """Configurar todos los servicios con la configuración actual."""
    from backend.services.social_media_service import SocialMediaManager
    from backend.services.email_service import EmailService
    
    # Social Media
    sm_config = config.get_service_config('social_media')
    # Aplicar configuración a SocialMediaManager
    
    # Email
    email_config = config.get_service_config('email')
    email = EmailService()
    if email_config.get('sender_email'):
        email.configure_smtp(
            smtp_server=email_config.get('smtp_server'),
            smtp_port=email_config.get('smtp_port'),
            sender_email=email_config.get('sender_email'),
            sender_password=email_config.get('sender_password')
        )


if __name__ == "__main__":
    # Ejemplo de uso
    config = MarketingConfig()
    
    # Ver resumen
    config.print_summary()
    
    # Validar
    validation = config.validate_config()
    log.info(f"\n✓ Configuración valida: {validation['valid']}")
    
    # Guardar
    config.save_config()
    
    # Crear preset
    # config.create_preset('startup')
