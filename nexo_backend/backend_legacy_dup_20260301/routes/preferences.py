"""
Routes: Preferences, Notifications, Calendar
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from ..services.preferences_service import PreferencesService
from ..services.notification_service import NotificationService
from ..services.calendar_service import CalendarService
from .auth import verify_token

router = APIRouter(prefix="/api", tags=["preferences"])

preferences_service = PreferencesService()
notification_service = NotificationService()
calendar_service = CalendarService()

# ============================================
# MODELS
# ============================================

class CognitiveProfile(BaseModel):
    learning_style: str  # visual, auditory, reading, kinesthetic
    content_length: str  # short, medium, long, full
    vocabulary_level: str  # simple, intermediate, technical
    expertise: str  # technology, business, science, general
    notification_frequency: str  # daily, weekly, monthly
    processing_style: str  # analytical, contextual, practical
    response_tone: str  # formal, conversational, creative
    breaking_alerts: str  # instant, daily, never
    privacy_level: str  # maximum, balanced, open

class NotificationPreference(BaseModel):
    category: str
    enabled: bool
    frequency: str  # daily, weekly, monthly

class EmailNotificationRequest(BaseModel):
    articles: list
    user_email: str

# ============================================
# PREFERENCES ENDPOINTS
# ============================================

@router.post("/preferences/cognitive-profile")
async def save_cognitive_profile(
    profile: CognitiveProfile,
    user_id: str = Depends(verify_token)
):
    """Guardar perfil cognitivo del usuario."""
    try:
        preferences_service.set_cognitive_profile(user_id, {
            'learning_style': profile.learning_style,
            'vocabulary_level': profile.vocabulary_level,
            'expertise_area': profile.expertise,
            'engagement_score': 50
        })
        
        preferences_service.set_preferences(user_id, {
            'content_length': profile.content_length,
            'notification_frequency': profile.notification_frequency,
            'processing_style': profile.processing_style,
            'response_tone': profile.response_tone,
            'breaking_alerts': profile.breaking_alerts,
            'privacy_level': profile.privacy_level
        })
        
        return {
            'status': 'success',
            'message': 'Perfil cognitivo guardado',
            'user_id': user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preferences/{user_id}")
async def get_preferences(
    user_id: str = Depends(verify_token)
):
    """Obtener preferencias del usuario."""
    try:
        preferences = preferences_service.get_preferences(user_id)
        profile = preferences_service.get_cognitive_profile(user_id)
        notifications = preferences_service.get_notification_preferences(user_id)
        
        return {
            'preferences': preferences,
            'cognitive_profile': profile,
            'notification_preferences': notifications
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/preferences/{user_id}")
async def update_preferences(
    updates: Dict,
    user_id: str = Depends(verify_token)
):
    """Actualizar preferencias del usuario."""
    try:
        preferences_service.set_preferences(user_id, updates)
        return {'status': 'success', 'message': 'Preferencias actualizadas'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preferences/{user_id}/insight")
async def get_preference_insight(
    user_id: str = Depends(verify_token)
):
    """Obtener insight cognitivo del usuario."""
    try:
        profile = preferences_service.get_cognitive_profile(user_id)
        
        insights = {
            'learning_style': _get_learning_style_insight(profile.get('learning_style')),
            'recommended_content_length': _recommend_content_length(profile),
            'vocabulary_adaptation': _get_vocabulary_level(profile.get('vocabulary_level')),
            'expertise_level': profile.get('expertise_area'),
            'suggested_topics': _suggest_topics_for_expertise(profile.get('expertise_area'))
        }
        
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# NOTIFICATION ENDPOINTS
# ============================================

@router.post("/notifications/send-digest")
async def send_news_digest(
    request: EmailNotificationRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_token)
):
    """Enviar digest de noticias personalizado."""
    try:
        # Obtener preferencias del usuario
        preferences = preferences_service.get_preferences(user_id)
        profile = preferences_service.get_cognitive_profile(user_id)
        
        # Personalizar artículos según perfil cognitivo
        personalized_articles = _personalize_articles(
            request.articles,
            profile
        )
        
        # Encolar envío
        notification_service.queue_daily_digest(
            user_id,
            request.user_email,
            personalized_articles,
            profile
        )
        
        return {
            'status': 'queued',
            'message': 'Digest encolado para envío',
            'articles_count': len(personalized_articles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/send-breaking")
async def send_breaking_alert(
    news: Dict,
    user_id: str = Depends(verify_token)
):
    """Enviar alerta de breaking news."""
    try:
        # Obtener email del usuario (sería de la base de datos)
        user_email = "user@example.com"  # TODO: forzar de DB
        
        result = notification_service.send_breaking_news_alert(
            user_id,
            user_email,
            news
        )
        
        if result:
            return {'status': 'sent', 'message': 'Alerta enviada'}
        else:
            raise HTTPException(status_code=500, detail='Error enviando alerta')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications/history")
async def get_notification_history(
    user_id: str = Depends(verify_token),
    limit: int = 50
):
    """Obtener historial de notificaciones."""
    try:
        history = notification_service.get_user_notification_history(user_id, limit)
        return {
            'total': len(history),
            'notifications': history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications/engagement")
async def get_engagement_score(
    user_id: str = Depends(verify_token)
):
    """Obtener score de engagement del usuario."""
    try:
        score = notification_service.calculate_engagement_score(user_id)
        should_reduce = notification_service.should_reduce_notifications(user_id)
        
        return {
            'engagement_score': score,
            'should_reduce_frequency': should_reduce,
            'recommendation': _get_engagement_recommendation(score)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/preferences/{category}")
async def set_notification_preference(
    category: str,
    preference: NotificationPreference,
    user_id: str = Depends(verify_token)
):
    """Establecer preferencia de notificación para categoría."""
    try:
        preferences_service.set_notification_preference(
            user_id,
            category,
            preference.dict()
        )
        return {'status': 'success', 'message': f'Preferencia {category} actualizada'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# CALENDAR ENDPOINTS
# ============================================

@router.get("/calendar/auth/google")
async def get_google_auth_url(
    user_id: str = Depends(verify_token)
):
    """Obtener URL para autorización de Google Calendar."""
    try:
        auth_url = calendar_service.request_google_auth(user_id, "http://localhost:8000")
        return {'auth_url': auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar/auth/outlook")
async def get_outlook_auth_url(
    user_id: str = Depends(verify_token)
):
    """Obtener URL para autorización de Outlook."""
    try:
        auth_url = calendar_service.request_outlook_auth(user_id)
        return {'auth_url': auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calendar/auth/google/callback")
async def handle_google_callback(
    code: str,
    user_id: str = Depends(verify_token)
):
    """Procesar callback de Google OAuth."""
    try:
        result = calendar_service.handle_google_callback(user_id, code)
        if result:
            return {'status': 'success', 'message': 'Google Calendar conectado'}
        else:
            raise HTTPException(status_code=500, detail='Error autenticando Google')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar/events")
async def get_upcoming_events(
    user_id: str = Depends(verify_token),
    days_ahead: int = 7
):
    """Obtener eventos próximos del usuario."""
    try:
        events = calendar_service.get_upcoming_events(user_id, days_ahead)
        return {
            'total': len(events),
            'events': events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calendar/sync-news")
async def sync_news_to_calendar(
    news: Dict,
    user_id: str = Depends(verify_token)
):
    """Sincronizar noticia importante a calendario."""
    try:
        result = calendar_service.create_news_event(user_id, news)
        if result:
            return {'status': 'synced', 'message': 'Noticia añadida al calendario'}
        else:
            return {'status': 'skipped', 'message': 'Noticia no tiene importancia suficiente'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calendar/reminder")
async def set_reminder(
    event_id: str,
    reminder_type: str,
    minutes_before: int = 60,
    user_id: str = Depends(verify_token)
):
    """Establecer recordatorio para evento."""
    try:
        calendar_service.set_reminder(user_id, event_id, reminder_type, minutes_before)
        return {'status': 'set', 'message': f'Recordatorio en {minutes_before} minutos'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# HELPER FUNCTIONS
# ============================================

def _get_learning_style_insight(style: str) -> str:
    """Providencia insight sobre estilo de aprendizaje."""
    insights = {
        'visual': 'Respondés mejor a contenido con imágenes, gráficos y videos',
        'auditory': 'Preferís explicaciones habladas y formato podcast',
        'reading': 'Te destaca el texto detallado y documentación escrita',
        'kinesthetic': 'Aprendés mejor con ejemplos prácticos e interactivos'
    }
    return insights.get(style, 'Estilo no definido')

def _recommend_content_length(profile: Dict) -> str:
    """Recomendar longitud de contenido según expertise."""
    expertise = profile.get('expertise_area', 'general')
    if expertise == 'technology':
        return 'medium'  # Desarrolladores quieren texto balanceado
    elif expertise == 'business':
        return 'short'  # Ejecutivos prefieren resúmenes
    else:
        return 'medium'

def _get_vocabulary_level(level: str) -> Dict:
    """Obtener configuración de vocabulario."""
    levels = {
        'simple': {'use_jargon': False, 'explain_terms': True},
        'intermediate': {'use_jargon': True, 'explain_terms': False},
        'technical': {'use_jargon': True, 'explain_terms': False}
    }
    return levels.get(level, {})

def _suggest_topics_for_expertise(expertise: str) -> list:
    """Sugerir tópicos basado en expertise."""
    topics_map = {
        'technology': ['AI', 'Cybersecurity', 'Cloud', 'Web3', 'Mobile'],
        'business': ['Markets', 'Startups', 'Economics', 'Finance', 'M&A'],
        'science': ['Physics', 'Biology', 'Medicine', 'Space', 'Climate'],
        'general': ['Politics', 'World', 'Sports', 'Entertainment', 'Tech']
    }
    return topics_map.get(expertise, [])

def _personalize_articles(articles: list, profile: Dict) -> list:
    """Personalizar artículos según perfil cognitivo."""
    # Filtrar por expertise
    expertise = profile.get('expertise_area', 'general')
    filtered = [a for a in articles if _matches_expertise(a, expertise)]
    
    # Ordenar por relevancia
    filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return filtered[:10]

def _matches_expertise(article: Dict, expertise: str) -> bool:
    """Verificar si artículo coincide con expertise."""
    if expertise == 'general':
        return True
    
    article_tags = article.get('tags', [])
    expertise_keywords = {
        'technology': ['tech', 'ai', 'software', 'tech', 'digital'],
        'business': ['business', 'finance', 'market', 'economy'],
        'science': ['science', 'research', 'study', 'discovery']
    }
    
    keywords = expertise_keywords.get(expertise, [])
    return any(kw in str(article_tags).lower() for kw in keywords)

def _get_engagement_recommendation(score: float) -> str:
    """Obtener recomendación basada en engagement score."""
    if score < 30:
        return 'Reducir frecuencia de notificaciones - usuario poco engañado'
    elif score < 60:
        return 'Mantener frecuencia actual'
    else:
        return 'Aumentar notificaciones - usuario altamente engañado'
