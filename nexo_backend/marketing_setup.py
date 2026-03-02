"""
Setup Script: Inicializar servicios de marketing con datos de ejemplo
"""

import json
from datetime import datetime, timedelta
from backend.services.social_media_service import SocialMediaManager
from backend.services.email_service import EmailService
from backend.services.analytics_service import AnalyticsService
from backend.services.automation_service import AutomationService
from backend.services.influencer_service import InfluencerService
from backend.services.content_service import ContentService
from backend.services.crm_service import CustomerService

class MarketingSetup:
    """Inicializar y configurar todos los servicios de marketing."""
    
    def __init__(self):
        self.social_media = SocialMediaManager()
        self.email = EmailService()
        self.analytics = AnalyticsService()
        self.automation = AutomationService()
        self.influencer = InfluencerService()
        self.content = ContentService()
        self.crm = CustomerService()
        
        log.info("✅ Servicios inicializados")
    
    def setup_social_media(self):
        """Configurar cuentas de redes sociales."""
        log.info("\n📱 Configurando Social Media...")
        
        platforms = [
            {"platform": "Instagram", "username": "nexo_oficial", "name": "Nexo Official"},
            {"platform": "Twitter", "username": "nexo_soberano", "name": "Nexo Soberano"},
            {"platform": "LinkedIn", "username": "nexo-soberano", "name": "Nexo Soberano"},
            {"platform": "TikTok", "username": "nexosoberano", "name": "Nexo Soberano"},
            {"platform": "Facebook", "username": "nexosoberano", "name": "Nexo Soberano"}
        ]
        
        for platform in platforms:
            result = self.social_media.connect_social_account(
                platform=platform['platform'],
                account_name=platform['name'],
                username=platform['username'],
                access_token="access_token_placeholder"
            )
            log.info(f"  ✅ {platform['platform']}: {result['message']}")
        
        # Crear posts de ejemplo
        log.info("\n  📝 Creando posts de ejemplo...")
        posts = [
            {
                'platform': 'Twitter',
                'content': '🚀 Las tendencias de IA para 2025 están aquí. Descubre cómo transformarán tu negocio.',
                'hashtags': ['IA', 'Tendencias2025', 'Tech']
            },
            {
                'platform': 'Instagram',
                'content': 'Nuevo análisis: Los 5 cambios más importantes en Marketing Digital 📊',
                'hashtags': ['Marketing', 'Digital', 'Tendencias']
            },
            {
                'platform': 'LinkedIn',
                'content': 'Publicamos nuestro último whitepaper sobre transformación digital.',
                'hashtags': ['Digital', 'Transformación', 'Business']
            }
        ]
        
        for post in posts:
            result = self.social_media.create_post(
                account_id=1,
                platform=post['platform'],
                content=post['content'],
                hashtags=post['hashtags'],
                scheduled_for=(datetime.now() + timedelta(days=1)).isoformat()
            )
        
        log.info("  ✅ Posts de ejemplo creados")
    
    def setup_email(self):
        """Configurar email y plantillas."""
        log.info("\n📧 Configurando Email Service...")
        
        # Crear plantillas
        templates = [
            {
                'name': 'Newsletter Template',
                'subject': 'Nuestra Edición Semanal - {{WEEK}}',
                'html': '''
                <html>
                  <body style="font-family: Arial;">
                    <h1>{{TITLE}}</h1>
                    <p>{{CONTENT}}</p>
                    <hr>
                    <a href="{{LINK}}">Leer más</a>
                  </body>
                </html>
                '''
            },
            {
                'name': 'Welcome Template',
                'subject': '¡Bienvenido a Nexo!',
                'html': '''
                <html>
                  <body>
                    <h2>Hola {{NAME}},</h2>
                    <p>Nos alegra que te hayas unido a nuestra comunidad.</p>
                    <p>Aquí encontrarás contenido exclusivo sobre marketing, IA y tendencias.</p>
                  </body>
                </html>
                '''
            }
        ]
        
        for template in templates:
            result = self.email.create_template(
                name=template['name'],
                subject=template['subject'],
                html_body=template['html']
            )
            log.info(f"  ✅ Plantilla '{template['name']}' creada")
        
        log.info("  💡 Tip: Configurar SMTP con email.configure_smtp()")
    
    def setup_content(self):
        """Crear contenido inicial."""
        log.info("\n📝 Configurando Content Management...")
        
        articles = [
            {
                'title': 'Tendencias de IA 2025',
                'type': 'blog',
                'keywords': ['IA', '2025', 'tendencias'],
                'content': '# Tendencias de IA\n\nEste 2025 traerá cambios importantes...'
            },
            {
                'title': 'Guía de Marketing Digital',
                'type': 'guide',
                'keywords': ['marketing', 'digital', 'guía'],
                'content': '# Marketing Digital\n\nLos 10 principios fundamentales...'
            },
            {
                'title': 'Caso de Éxito: Transformación Digital',
                'type': 'case_study',
                'keywords': ['case study', 'transformación', 'éxito'],
                'content': '# Caso de Estudio\n\nCómo una empresa logró...'
            }
        ]
        
        for article in articles:
            result = self.content.create_content(
                title=article['title'],
                content_type=article['type'],
                markup_content=article['content'],
                keywords=article['keywords']
            )
            log.info(f"  ✅ '{article['title']}' creado")
        
        # Programar publicación
        log.info("\n  📅 Programando contenido...")
        for i in range(1, 4):
            self.content.schedule_content(
                content_id=i,
                publish_date=(datetime.now() + timedelta(days=i*7)).strftime('%Y-%m-%d'),
                distribution_channels=['blog', 'email', 'social']
            )
        
        log.info("  ✅ Contenido programado para 3 semanas")
    
    def setup_automations(self):
        """Crear flujos de trabajo automáticos."""
        log.info("\n🤖 Configurando Automatizaciones...")
        
        workflows = [
            {
                'name': 'Welcome Email Series',
                'description': 'Envía bienvenida a nuevos suscriptores',
                'steps': [
                    {
                        'action': 'send_email',
                        'config': {
                            'template': 'welcome',
                            'recipient': '{{email}}',
                            'delay_minutes': 0
                        }
                    },
                    {
                        'action': 'send_email',
                        'config': {
                            'template': 'value_prop',
                            'recipient': '{{email}}',
                            'delay_minutes': 1440
                        }
                    }
                ]
            },
            {
                'name': 'Social Media Auto-Post',
                'description': 'Publica contenido en redes automáticamente',
                'steps': [
                    {
                        'action': 'schedule_post',
                        'config': {
                            'platform': 'Twitter',
                            'content': '{{article_title}}'
                        }
                    },
                    {
                        'action': 'schedule_post',
                        'config': {
                            'platform': 'LinkedIn',
                            'content': '{{article_title}}'
                        }
                    }
                ]
            }
        ]
        
        for wf in workflows:
            result = self.automation.create_workflow(
                name=wf['name'],
                description=wf['description'],
                trigger_type='event_based'
            )
            log.info(f"  ✅ Workflow '{wf['name']}' creado")
            
            # Agregar steps
            for i, step in enumerate(wf['steps'], 1):
                self.automation.add_workflow_step(
                    workflow_id=result['workflow_id'],
                    step_order=i,
                    action_type=step['action'],
                    action_config=step['config']
                )
        
        log.info("  ✅ Automatizaciones configuradas")
    
    def setup_crm(self):
        """Crear clientes y leads de ejemplo."""
        log.info("\n👥 Configurando CRM...")
        
        customers = [
            {'name': 'Acme Corp', 'email': 'contact@acme.com', 'company': 'Acme', 'industry': 'Tech'},
            {'name': 'Global Systems', 'email': 'sales@global.com', 'company': 'Global Systems', 'industry': 'Finance'},
            {'name': 'TechStart Inc', 'email': 'hello@techstart.com', 'company': 'TechStart', 'industry': 'Startup'}
        ]
        
        for customer in customers:
            result = self.crm.add_customer(
                name=customer['name'],
                email=customer['email'],
                company=customer['company'],
                industry=customer['industry'],
                acquisition_channel='LinkedIn'
            )
            
            # Crear lead
            lead_result = self.crm.add_lead(
                customer_id=result['customer_id'],
                source='LinkedIn',
                status='qualified'
            )
            
            # Score lead
            score_result = self.crm.score_lead(
                lead_id=lead_result['lead_id'],
                criteria={
                    'company_size': 'enterprise',
                    'engagement': 'high',
                    'budget_aligned': True,
                    'timeline': 'immediate'
                }
            )
            
            log.info(f"  ✅ {customer['name']} (Puntuación: {score_result['score']})")
        
        log.info("  ✅ CRM initializado con clientes de ejemplo")
    
    def setup_influencers(self):
        """Crear base de influencers."""
        log.info("\n⭐ Configurando Influencers...")
        
        influencers = [
            {
                'name': 'Juan Tech',
                'username': 'juantech',
                'platform': 'Instagram',
                'followers': 250000,
                'niches': ['tech', 'IA', 'startups'],
                'rate': 3000
            },
            {
                'name': 'María Marketing',
                'username': 'mariamarketing',
                'platform': 'LinkedIn',
                'followers': 150000,
                'niches': ['marketing', 'digital', 'business'],
                'rate': 2500
            },
            {
                'name': 'Carlos Innovation',
                'username': 'carlosinno',
                'platform': 'Twitter',
                'followers': 180000,
                'niches': ['innovation', 'startups', 'tech'],
                'rate': 2000
            }
        ]
        
        for inf in influencers:
            result = self.influencer.add_influencer(
                name=inf['name'],
                username=inf['username'],
                platform=inf['platform'],
                followers=inf['followers'],
                engagement_rate=random_engagement(),
                rate_per_post=inf['rate'],
                niches=inf['niches']
            )
            log.info(f"  ✅ {inf['name']} ({inf['platform']})")
        
        log.info("  ✅ Base de influencers creada")
    
    def full_setup(self):
        """Ejecutar setup completo."""
        log.info("=" * 60)
        log.info("🚀 NEXO BACKEND SERVICES - SETUP INICIAL")
        log.info("=" * 60)
        
        self.setup_social_media()
        self.setup_email()
        self.setup_content()
        self.setup_automations()
        self.setup_crm()
        self.setup_influencers()
        
        log.info("\n" + "=" * 60)
        log.info("✅ SETUP COMPLETADO")
        log.info("=" * 60)
        log.info("\n📊 Servicios configurados:")
        log.info("  ✓ Social Media (5 plataformas)")
        log.info("  ✓ Email (2 plantillas)")
        log.info("  ✓ Content (3 artículos)")
        log.info("  ✓ Automation (2 workflows)")
        log.info("  ✓ CRM (3 clientes)")
        log.info("  ✓ Influencers (3 influencers)")
        log.info("\n💡 Próximos pasos:")
        log.info("  1. Configurar SMTP: email.configure_smtp(...)")
        log.info("  2. Crear rutas en FastAPI")
        log.info("  3. Conectar a la interfaz web")
        log.info("  4. Iniciar campañas")
        log.info("\n" + "=" * 60)
    
    def generate_sample_report(self):
        """Generar reporte de ejemplo."""
        log.info("\n📊 Generando reporte de ejemplo...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'services_ready': {
                'social_media': True,
                'email': True,
                'analytics': True,
                'automation': True,
                'influencer': True,
                'content': True,
                'crm': True
            },
            'initialization_data': {
                'social_accounts': 5,
                'email_templates': 2,
                'content_pieces': 3,
                'workflows': 2,
                'customers': 3,
                'influencers': 3
            },
            'next_actions': [
                'Configure SMTP credentials',
                'Set up social media token integrations',
                'Create FastAPI routes',
                'Launch first email campaign'
            ]
        }
        
        with open('marketing_setup_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        log.info("  ✅ Reporte guardado en marketing_setup_report.json")


def random_engagement():
    """Generar engagement rate aleatorio."""
    import random
    return round(random.uniform(2.5, 8.5), 2)


if __name__ == "__main__":
    setup = MarketingSetup()
    setup.full_setup()
    setup.generate_sample_report()
