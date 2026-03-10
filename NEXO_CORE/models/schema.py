"""
NEXO_CORE/models/schema.py
===========================
Modelos ORM SQLAlchemy para NEXO SOBERANO.

Mapea las 7 bases SQLite al modelo PostgreSQL schema-per-tenant:

  boveda.db         → Evidencia, VectorizadosLog
  cost_tracking.db  → CostoAPI
  conversations.db  → Conversacion, Mensaje
  preferences.db    → CognitiveProfile, NotificationPreference
  notifications.db  → EmailQueue
  calendar.db       → CalendarEvent, OAuthCredential
  auth.db           → Tenant, Usuario, Session (schema public)

Tablas en schema PUBLIC (globales del sistema):
    tenants · users · sessions

Tablas en schema TENANT_XXXX (una copia por empresa):
    evidencia · vectorizados_log · consultas · costos_api · alertas
    cognitive_profile · notification_preferences
    conversaciones · mensajes · email_queue
    calendar_events · oauth_credentials
"""

import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, Date, ForeignKey, BigInteger, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from NEXO_CORE.core.database import Base


# ═══════════════════════════════════════════════════════════════
#  SCHEMA PUBLIC — tablas globales del sistema
# ═══════════════════════════════════════════════════════════════

class Tenant(Base):
    """Empresas / clientes del sistema."""
    __tablename__ = "tenants"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug           = Column(String(63), unique=True, nullable=False, index=True)
    name           = Column(String(255), nullable=False)
    plan           = Column(String(32), default="starter")   # starter|pro|enterprise
    max_users      = Column(Integer, default=5)
    max_tokens_dia = Column(Integer, default=50_000)
    max_storage_mb = Column(Integer, default=500)
    active         = Column(Boolean, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    def schema_name(self) -> str:
        from NEXO_CORE.core.database import slug_to_schema
        return slug_to_schema(self.slug)


class Usuario(Base):
    """Usuarios del sistema (globales, pertenecen a un tenant)."""
    __tablename__ = "users"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id        = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email            = Column(String(255), nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    role             = Column(String(32), default="member")  # owner|admin|member
    active           = Column(Boolean, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    last_login       = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
        Index("idx_users_tenant_id", "tenant_id"),
        Index("idx_users_email", "email"),
    )


class Session(Base):
    """Sesiones JWT activas."""
    __tablename__ = "sessions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id  = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_sessions_expires", "expires_at"),
    )


# ═══════════════════════════════════════════════════════════════
#  SCHEMA TENANT_XXXX — tablas por empresa
#  Alembic aplica estas a cada schema con:
#    ALEMBIC_TARGET_SCHEMA=tenant_demo alembic upgrade head
# ═══════════════════════════════════════════════════════════════

class Evidencia(Base):
    """
    Documentos ingestionados y vectorizados.
    Equivale a la tabla principal de boveda.db.
    """
    __tablename__ = "evidencia"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # SHA-256 del contenido — para deduplicación exacta
    content_hash       = Column(String(64), unique=True, nullable=False, index=True)
    filename           = Column(String(512), nullable=True)
    file_type          = Column(String(32), nullable=True)      # pdf|txt|docx|url|imagen
    content_text       = Column(Text, nullable=True)
    metadata_          = Column("metadata", JSONB, default=dict) # autor, tags, fuente, etc.
    vectorizado        = Column(Boolean, default=False)
    vectorizado_at     = Column(DateTime(timezone=True), nullable=True)
    qdrant_id          = Column(String(128), nullable=True)
    qdrant_collection  = Column(String(128), nullable=True)
    created_by         = Column(UUID(as_uuid=True), nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_evidencia_created", "created_at"),
        Index("idx_evidencia_tipo", "file_type"),
    )


class VectorizadosLog(Base):
    """Log de operaciones de vectorización. Equivale a vectorizados_log en boveda.db."""
    __tablename__ = "vectorizados_log"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    evidencia_id  = Column(UUID(as_uuid=True), nullable=True, index=True)
    filename      = Column(String(512), nullable=True)
    chunks_total  = Column(Integer, default=0)
    tokens_usados = Column(Integer, default=0)
    modelo_embed  = Column(String(64), default="all-MiniLM-L6-v2")
    duracion_seg  = Column(Float, nullable=True)
    estado        = Column(String(32), default="ok")   # ok|error|parcial
    error_msg     = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class Consulta(Base):
    """Historial de consultas RAG. Equivale a consultas en boveda.db / conversations.db."""
    __tablename__ = "consultas"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), nullable=True, index=True)
    conversacion_id  = Column(UUID(as_uuid=True), nullable=True, index=True)
    pregunta         = Column(Text, nullable=False)
    respuesta        = Column(Text, nullable=True)
    modelo_usado     = Column(String(64), nullable=True)
    tokens_in        = Column(Integer, default=0)
    tokens_out       = Column(Integer, default=0)
    contexto_chunks  = Column(JSONB, default=list)  # chunks recuperados del RAG
    duracion_ms      = Column(Integer, nullable=True)
    cache_hit        = Column(Boolean, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_consultas_user", "user_id"),
        Index("idx_consultas_fecha", "created_at"),
    )


class CostoAPI(Base):
    """
    Registro de tokens consumidos por cada llamada a IA.
    Equivale a cost_tracking.db → costos_api.
    """
    __tablename__ = "costos_api"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(UUID(as_uuid=True), nullable=True)
    modelo     = Column(String(64), nullable=False)
    tokens_in  = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    operacion  = Column(String(64), nullable=True)   # rag|embedding|digest|worldmonitor|...
    fecha      = Column(Date, default=date.today, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_costos_fecha_modelo", "fecha", "modelo"),
    )


class Alerta(Base):
    """
    Alertas generadas por NEXO o WorldMonitor.
    Tipos: cii_spike · military_surge · geo_convergence · protest_event · ais_anomaly
    """
    __tablename__ = "alertas"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo        = Column(String(64), nullable=False, index=True)
    severidad   = Column(Float, default=0.5)
    titulo      = Column(String(512), nullable=False)
    descripcion = Column(Text, nullable=True)
    pais        = Column(String(128), nullable=True, index=True)
    region      = Column(String(128), nullable=True)
    coordenadas = Column(JSONB, nullable=True)   # {"lat": x, "lon": y}
    fuente      = Column(String(64), default="nexo")   # nexo|worldmonitor|usuario
    datos_raw   = Column(JSONB, default=dict)
    procesada   = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_alertas_severidad", "severidad"),
        Index("idx_alertas_fecha", "created_at"),
    )


class CognitiveProfile(Base):
    """
    Perfil cognitivo del usuario — 10 dimensiones de personalización.
    Equivale a preferences.db → cognitive_profile.
    """
    __tablename__ = "cognitive_profile"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    learning_style = Column(String(32), default="reading")    # visual|auditory|reading|kinesthetic
    vocabulary     = Column(String(32), default="simple")     # simple|academic|technical
    content_length = Column(String(32), default="200w")       # 50w|200w|full
    tone           = Column(String(32), default="casual")     # formal|casual
    presentation   = Column(String(32), default="bullet")     # bullet|narrative
    sequence       = Column(String(32), default="linear")     # linear|modular
    depth_level    = Column(String(32), default="surface")    # surface|deep
    example_mode   = Column(String(32), default="practical")  # conceptual|practical
    format_pref    = Column(String(32), default="text")       # text|visual|mixed
    expertise      = Column(JSONB, default=dict)              # {"retail": 0.8, "tech": 0.3}
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())


class NotificationPreference(Base):
    """Preferencias de alertas por usuario (umbral, regiones, canales)."""
    __tablename__ = "notification_preferences"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    alert_threshold     = Column(Float, default=0.65)
    regions_of_interest = Column(JSONB, default=list)   # ["Chile", "South America"]
    signal_types        = Column(JSONB, default=list)   # ["cii_spike", "military_surge"]
    digest_enabled      = Column(Boolean, default=True)
    realtime_alerts     = Column(Boolean, default=True)
    channels            = Column(JSONB, default=list)   # ["email", "discord", "whatsapp"]
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())


class Conversacion(Base):
    """Hilo de chat. Equivale a conversations.db."""
    __tablename__ = "conversaciones"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), nullable=False, index=True)
    titulo     = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    mensajes   = relationship("Mensaje", back_populates="conversacion", cascade="all, delete-orphan")


class Mensaje(Base):
    """Mensaje dentro de una conversación (role: user | assistant | system)."""
    __tablename__ = "mensajes"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversacion_id  = Column(UUID(as_uuid=True), ForeignKey("conversaciones.id", ondelete="CASCADE"), nullable=False)
    user_id          = Column(UUID(as_uuid=True), nullable=False)
    role             = Column(String(16), nullable=False)
    content          = Column(Text, nullable=False)
    tokens_usados    = Column(Integer, default=0)
    modelo_usado     = Column(String(64), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    conversacion     = relationship("Conversacion", back_populates="mensajes")

    __table_args__ = (
        Index("idx_mensajes_conv_fecha", "conversacion_id", "created_at"),
    )


class EmailQueue(Base):
    """Cola de emails pendientes. Equivale a notifications.db."""
    __tablename__ = "email_queue"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), nullable=False, index=True)
    status       = Column(String(16), default="pending", index=True)  # pending|sent|failed
    subject      = Column(String(255), nullable=True)
    html_content = Column(Text, nullable=True)
    intentos     = Column(Integer, default=0)
    sent_at      = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class CalendarEvent(Base):
    """Eventos de calendario sincronizados (Google / Outlook). Equivale a calendar.db."""
    __tablename__ = "calendar_events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    source      = Column(String(32), nullable=True)     # google|outlook
    external_id = Column(String(255), nullable=True)
    title       = Column(String(512), nullable=True)
    start_time  = Column(DateTime(timezone=True), nullable=True)
    end_time    = Column(DateTime(timezone=True), nullable=True)
    synced_at   = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "source", "external_id", name="uq_cal_event"),
    )


class OAuthCredential(Base):
    """Tokens OAuth por proveedor — los tokens van cifrados en la capa de aplicación."""
    __tablename__ = "oauth_credentials"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id           = Column(UUID(as_uuid=True), nullable=False)
    provider          = Column(String(32), nullable=False)   # google|microsoft|youtube
    access_token_enc  = Column(Text, nullable=True)          # cifrado en app, nunca en claro
    refresh_token_enc = Column(Text, nullable=True)
    expires_at        = Column(DateTime(timezone=True), nullable=True)
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
    )
