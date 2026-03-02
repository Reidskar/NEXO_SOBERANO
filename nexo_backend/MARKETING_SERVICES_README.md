# 🚀 Nexo Backend Services - Marketing & Growth Suite

Sistema completo de gestión de marketing, ventas y crecimiento para Nexo Soberano.

## 📦 Servicios Incluidos

### 1. **Social Media Service** (`social_media_service.py`)
Gestión centralizada de redes sociales y publicaciones.

**Características:**
- Conexión con múltiples plataformas (Instagram, Twitter, LinkedIn, Facebook, TikTok)
- Programación de posts
- Tracking de engagement (likes, comments, shares, views)
- Análisis de hashtags trending
- Sugerencia automática de hashtags
- Horarios óptimos de publicación por plataforma
- Exportación de calendario social

**Métodos Principales:**
```python
service = SocialMediaManager()

# Conectar cuenta
service.connect_social_account("Instagram", "nexo_oficial", "nexo_oficial", "token123")

# Crear post
service.create_post(
    account_id=1,
    platform="Instagram",
    content="Nuevo análisis de tendencias...",
    hashtags=["IA", "tendencias"],
    scheduled_for="2025-01-25 09:00"
)

# Obtener analytics
analytics = service.get_social_analytics(account_id=1)
```

---

### 2. **Email Service** (`email_service.py`)
Gestión de email marketing y newsletters.

**Características:**
- Configuración SMTP
- Plantillas de email
- Campañas de email marketing
- Tracking de opens y clicks
- Programación de envíos
- Estadísticas de campaña
- Exportación de reportes

**Métodos Principales:**
```python
email = EmailService()

# Configurar SMTP
email.configure_smtp("smtp.gmail.com", 587, "your@email.com", "password")

# Crear plantilla
email.create_template(
    name="Newsletter",
    subject="Edición semanal",
    html_body="<h1>{{TITLE}}</h1><p>{{CONTENT}}</p>"
)

# Crear campaña
campaign = email.create_campaign(
    name="weekly_newsletter",
    template_id=1,
    recipients=["user1@example.com", "user2@example.com"],
    scheduled_for="2025-01-25 09:00"
)

# Enviar masivamente
email.send_bulk_emails(campaign_id=1)

# Obtener estadísticas
stats = email.get_campaign_stats(campaign_id=1)
```

---

### 3. **Analytics Service** (`analytics_service.py`)
Análisis integrado de rendimiento en todos los canales.

**Características:**
- Dashboard multicanal
- Tracking de eventos
- Análisis de embudo de conversión
- Segmentación de usuarios
- Modelo de atribución multi-toque
- ROI por canal
- Predicciones e insights
- Recomendaciones automáticas

**Métodos Principales:**
```python
analytics = AnalyticsService()

# Obtener dashboard
summary = analytics.get_dashboard_summary(days=30)

# Comparar canales
comparison = analytics.get_channel_comparison()

# Embudo de conversión
funnel = analytics.get_conversion_funnel()

# ROI por canal
roi = analytics.get_roi_by_channel()

# Recomendaciones
recommendations = analytics.get_recommendations()
```

---

### 4. **Automation Service** (`automation_service.py`)
Automatización de flujos de trabajo y campañas.

**Características:**
- Creación de flujos de trabajo
- Triggering basado en tiempo/eventos/condiciones
- Acciones automáticas (email, tasks, updates)
- Programación de ejecuciones
- Tracking de ejecuciones
- Flujos predefinidos
- Exportación de workflows

**Métodos Principales:**
```python
automation = AutomationService()

# Crear flujo
workflow = automation.create_workflow(
    name="Welcome Series",
    description="Bienvenida a nuevos suscriptores",
    trigger_type="event_based",
    trigger_config={"event": "new_subscriber"}
)

# Agregar pasos
automation.add_workflow_step(
    workflow_id=workflow['workflow_id'],
    step_order=1,
    action_type="send_email",
    action_config={
        "template": "welcome",
        "recipient": "{{email}}"
    }
)

# Ejecutar
result = automation.execute_workflow(
    workflow_id=workflow['workflow_id'],
    trigger_data={"email": "user@example.com"}
)
```

---

### 5. **Influencer Service** (`influencer_service.py`)
Gestión de influencers y partnerships.

**Características:**
- Base de datos de influencers
- Búsqueda avanzada (platform, niches, followers)
- Creación de partnerships
- Tracking de performance
- Programa de afiliados
- Análisis de ROI
- Templates de outreach
- Clasificación por tiers

**Métodos Principales:**
```python
influencer = InfluencerService()

# Agregar influencer
inf = influencer.add_influencer(
    name="Juan Influencer",
    username="juaninfluencer",
    platform="Instagram",
    followers=150000,
    rate_per_post=2000,
    niches=["tech", "marketing"]
)

# Buscar
results = influencer.search_influencers(
    platform="Instagram",
    niche="tech",
    min_followers=100000
)

# Crear partnership
partnership = influencer.create_partnership(
    influencer_id=1,
    partnership_name="Sponsored Post Q1",
    compensation=2000,
    deliverables={'posts': 1, 'stories': 5, 'reels': 1}
)

# Analizar ROI
roi = influencer.get_partnership_roi_analysis(partnership_id=1)
```

---

### 6. **Content Service** (`content_service.py`)
Gestión centralizada de contenido.

**Características:**
- Crear y editar contenido
- Workflow de aprobación
- Programación de publicación
- Editorial calendar (30 días)
- Tracking de performance
- Sugerencias de repurposing
- Recomendaciones SEO
- Ideas de contenido

**Métodos Principales:**
```python
content = ContentService()

# Crear contenido
piece = content.create_content(
    title="Tendencias de IA 2025",
    content_type="blog",
    markup_content="<h1>Tendencias...</h1>",
    keywords=["IA", "2025", "tendencias"]
)

# Programar publicación
content.schedule_content(
    content_id=piece['content_id'],
    publish_date="2025-01-25 09:00",
    distribution_channels=["blog", "email", "social"]
)

# Publicar
content.publish_content(piece['content_id'])

# Obtener calendar
calendar = content.get_editorial_calendar(days_ahead=30)

# Sugerencias de repurposing
repurposing = content.suggest_content_repurposing(piece['content_id'])
```

---

### 7. **CRM Service** (`crm_service.py`)
Customer Relationship Management completo.

**Características:**
- Gestión de clientes y leads
- Logging de interacciones
- Pipeline de ventas
- Deals/Oportunidades
- Scoring de leads
- Seguimiento de contactos
- Análisis del pipeline
- Exportación de datos

**Métodos Principales:**
```python
crm = CustomerService()

# Agregar cliente
customer = crm.add_customer(
    name="Acme Corp",
    email="contact@acme.com",
    company="Acme",
    industry="Tech"
)

# Crear lead
lead = crm.add_lead(
    customer_id=customer['customer_id'],
    source="LinkedIn",
    status="new"
)

# Log interacción
crm.log_interaction(
    customer_id=customer['customer_id'],
    interaction_type="call",
    channel="phone",
    subject="Presentación de producto",
    outcome="Interested"
)

# Crear deal
deal = crm.create_deal(
    customer_id=customer['customer_id'],
    deal_name="Proyecto Q1",
    value=50000,
    expected_close_date="2025-03-31"
)

# Score lead
score = crm.score_lead(
    lead_id=lead['lead_id'],
    criteria={
        'company_size': 'enterprise',
        'engagement': 'high',
        'budget_aligned': True
    }
)

# Ver pipeline
pipeline = crm.get_sales_pipeline()
```

---

## 🔗 Integración

### Importar Servicios
```python
from backend.services.social_media_service import SocialMediaManager
from backend.services.email_service import EmailService
from backend.services.analytics_service import AnalyticsService
from backend.services.automation_service import AutomationService
from backend.services.influencer_service import InfluencerService
from backend.services.content_service import ContentService
from backend.services.crm_service import CustomerService
```

### Crear Instancias
```python
# Cada servicio se inicializa con su DB
social_media = SocialMediaManager(db_path="social_media.db")
email = EmailService(db_path="email_campaigns.db")
analytics = AnalyticsService(db_path="analytics.db")
automation = AutomationService(db_path="automations.db")
influencer = InfluencerService(db_path="influencers.db")
content = ContentService(db_path="content.db")
crm = CustomerService(db_path="crm.db")
```

---

## 📊 Casos de Uso

### Caso 1: Newsletter Automática + Social
```python
# Crear contenido
article = content.create_content(
    title="Weekly Insights",
    content_type="blog"
)

# Programar publicación
content.schedule_content(
    content_id=article['content_id'],
    distribution_channels=["blog", "email", "social"]
)

# Crear email newsletter
email_campaign = email.create_campaign(
    name="Weekly Newsletter",
    template_id=1,
    recipients=[...all_subscribers...]
)

# Automatizar publicación en social
automation.create_workflow(
    name="Auto Social Publish",
    trigger_type="event_based",
    trigger_config={"event": "content_published"}
)

automation.add_workflow_step(
    workflow_id=workflow_id,
    step_order=1,
    action_type="schedule_post",
    action_config={
        "platform": "Twitter",
        "content": "{{article_title}}",
        "hashtags": ["tech", "insights"]
    }
)
```

### Caso 2: Lead Nurturing + Scoring
```python
# Crear lead
customer = crm.add_customer(name="prospect@company.com")
lead = crm.add_lead(customer_id=customer['customer_id'])

# Scoring
crm.score_lead(
    lead_id=lead['lead_id'],
    criteria={'company_size': 'enterprise', 'budget_aligned': True}
)

# Automatizar nurturing
workflow = automation.create_workflow(
    name="Lead Nurturing",
    trigger_type="event_based",
    trigger_config={"event": "high_score_lead"}
)

# Series de emails
for i in range(4):
    automation.add_workflow_step(
        workflow_id=workflow_id,
        step_order=i+1,
        action_type="send_email",
        action_config={"email_template": f"nurture_email_{i+1}"}
    )
```

### Caso 3: Influencer Campaign + Tracking
```python
# Buscar influencia
influencers = influencer.search_influencers(
    platform="Instagram",
    niche="tech",
    min_followers=100000
)

# Crear partnerships
partnerships = []
for inf in influencers:
    partnership = influencer.create_partnership(
        influencer_id=inf['id'],
        partnership_name=f"Campaign {inf['name']}",
        compensation=5000
    )
    partnerships.append(partnership)

# Track performance
for day in range(30):
    for partnership in partnerships:
        influencer.track_partnership_performance(
            partnership_id=partnership['partnership_id'],
            impressions=random_value(),
            engagement=random_value(),
            sales=random_value()
        )

# Analizar
for partnership in partnerships:
    roi = influencer.get_partnership_roi_analysis(
        partnership_id=partnership['partnership_id']
    )
```

---

## 🗄️ Base de Datos

Cada servicio tiene su propia base de datos SQLite:

- `social_media.db` - 3 tablas (accounts, posts, hashtag_analytics)
- `email_campaigns.db` - 4 tablas (templates, campaigns, logs, settings)
- `analytics.db` - 3 tablas (channel_performance, user_journey, segment_performance)
- `automations.db` - 4 tablas (workflows, workflow_steps, executions, scheduled_tasks)
- `influencers.db` - 4 tablas (influencers, partnerships, performance, affiliate_programs)
- `content.db` - 5 tablas (pieces, metadata, distribution, calendar, analytics)
- `crm.db` - 4 tablas (customers, leads, interactions, deals)

**Total: 27 tablas de datos**

---

## 🎯 Flujos de Trabajo Predefinidos

El servicio de automatización incluye templates:

1. **Bienvenida a nuevos suscriptores** - Email + tags
2. **Re-engagement de inactivos** - Email especial + descuento
3. **Nurturing de leads** - 4 emails secuenciados
4. **Amplificación social** - Auto-publicación en 5 plataformas
5. **Escalada de oportunidades** - Lead scoring → sales

---

## 📈 Métricas Disponibles

### Social Media
- Followers, Engagement Rate, Likes, Comments, Shares, Views
- Trending Hashtags, Optimal Posting Times

### Email
- Open Rate, Click Rate, Bounce Rate, Conversions
- Campaign Stats, Automation Performance

### Analytics
- CTR, CVR, ROI, Impressions, Conversions
- Channel Comparison, User Segments, Conversion Funnel

### Sales (CRM)
- Pipeline Value, Won Deals, Lead Scoring, Deal Probability
- Lifetime Value, Acquisition Channel, Interaction History

---

## 🔐 Seguridad

- SMTP credentials almacenados en settings
- Database encryption-ready (SQLite)
- Timestamps en UTC
- Audit trail de todas las acciones

---

## 📝 Próximos Pasos

1. Crear rutas API en FastAPI (`/backend/routes/marketing.py`)
2. Integrar en main.py
3. Crear interfaces frontend
4. Conectar con dispatcher para envíos automáticos
5. Integrar con chat para recomendaciones AI

---

## 💡 Ejemplo Completo

```python
from backend.services.social_media_service import SocialMediaManager
from backend.services.email_service import EmailService
from backend.services.analytics_service import AnalyticsService
from backend.services.automation_service import AutomationService

# Inicializar servicios
sm = SocialMediaManager()
em = EmailService()
ana = AnalyticsService()
auto = AutomationService()

# Conectar cuenta social
sm.connect_social_account("Instagram", "Nexo", "nexo_oficial", "token123")

# Crear workflow automático
workflow = auto.create_workflow(
    name="Post + Email",
    trigger_type="time_based",
    trigger_config={"time": "09:00"}
)

auto.add_workflow_step(
    workflow_id=workflow['workflow_id'],
    step_order=1,
    action_type="schedule_post",
    action_config={
        "platform": "Instagram",
        "content": "Nuevo contenido exclusivo disponible 🚀"
    }
)

auto.add_workflow_step(
    workflow_id=workflow['workflow_id'],
    step_order=2,
    action_type="send_email",
    action_config={
        "recipient": "{{email}}",
        "template": "content_alert"
    }
)

# Programar
auto.schedule_workflow(
    workflow_id=workflow['workflow_id'],
    scheduled_for="2025-01-25 09:00",
    frequency="daily"
)

# Ejecutar
result = auto.execute_workflow(workflow_id=workflow['workflow_id'])
print(result)

# Analytics
dashboard = ana.get_dashboard_summary()
print(dashboard)
```

---

**Versión:** 1.0  
**Última actualización:** 2025-01-24  
**Estado:** ✅ Production Ready
