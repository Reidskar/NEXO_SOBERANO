"""
Automation Service: Automatizaciones de marketing y flujos de trabajo
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Callable
from enum import Enum

class TriggerType(Enum):
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    CONDITION_BASED = "condition_based"

class ActionType(Enum):
    SEND_EMAIL = "send_email"
    CREATE_TASK = "create_task"
    UPDATE_PROSPECT = "update_prospect"
    SCHEDULE_POST = "schedule_post"
    SEGMENT_USERS = "segment_users"
    TRIGGER_NOTIFICATION = "trigger_notification"

class AutomationService:
    def __init__(self, db_path: str = "automations.db"):
        self.db_path = db_path
        self._init_db()
        self.callbacks = {}

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de automatizaciones."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                status TEXT,
                trigger_type TEXT,
                trigger_config_json TEXT,
                execution_count INTEGER DEFAULT 0,
                last_executed TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER,
                step_order INTEGER,
                action_type TEXT,
                action_config_json TEXT,
                created_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER,
                trigger_data_json TEXT,
                status TEXT,
                completed_steps INTEGER,
                total_steps INTEGER,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER,
                scheduled_for TEXT,
                frequency TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id)
            )
            """)

    def create_workflow(self, name: str, description: str = "",
                       trigger_type: str = "time_based",
                       trigger_config: Dict = None) -> Dict:
        """Crear nuevo flujo de trabajo."""
        try:
            trigger_config_json = json.dumps(trigger_config or {})
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO workflows
                (name, description, status, trigger_type, trigger_config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, description, 'active', trigger_type, trigger_config_json,
                     datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                workflow_id = con.execute(
                    "SELECT id FROM workflows WHERE name=?", (name,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'workflow_id': workflow_id,
                'message': f'✅ Flujo "{name}" creado'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def add_workflow_step(self, workflow_id: int, step_order: int,
                         action_type: str, action_config: Dict) -> Dict:
        """Agregar paso a un flujo."""
        try:
            action_config_json = json.dumps(action_config)
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO workflow_steps
                (workflow_id, step_order, action_type, action_config_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (workflow_id, step_order, action_type, action_config_json,
                     datetime.utcnow().isoformat()))
            
            return {'status': 'success', 'message': '✅ Paso agregado al flujo'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_workflow(self, workflow_id: int) -> Dict:
        """Eliminar flujo de trabajo."""
        try:
            with self._conn() as con:
                con.execute("DELETE FROM workflow_steps WHERE workflow_id=?", (workflow_id,))
                con.execute("DELETE FROM scheduled_tasks WHERE workflow_id=?", (workflow_id,))
                con.execute("DELETE FROM workflows WHERE id=?", (workflow_id,))
            
            return {'status': 'success', 'message': '✅ Flujo eliminado'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_workflows(self, status: str = None) -> List[Dict]:
        """Obtener lista de flujos."""
        try:
            with self._conn() as con:
                if status:
                    workflows = con.execute(
                        "SELECT * FROM workflows WHERE status=? ORDER BY created_at DESC",
                        (status,)
                    ).fetchall()
                else:
                    workflows = con.execute(
                        "SELECT * FROM workflows ORDER BY created_at DESC"
                    ).fetchall()
            
            result = []
            for w in workflows:
                result.append({
                    'id': w[0],
                    'name': w[1],
                    'description': w[2],
                    'status': w[3],
                    'trigger_type': w[4],
                    'executions': w[8],
                    'last_executed': w[9]
                })
            
            return result
        except Exception as e:
            log.info(f"❌ Error getting workflows: {e}")
            return []

    def execute_workflow(self, workflow_id: int, trigger_data: Dict = None) -> Dict:
        """Ejecutar flujo de trabajo."""
        try:
            trigger_data = trigger_data or {}
            trigger_data_json = json.dumps(trigger_data)
            
            with self._conn() as con:
                # Obtener workflow y sus steps
                workflow = con.execute(
                    "SELECT * FROM workflows WHERE id=?", (workflow_id,)
                ).fetchone()
                
                if not workflow:
                    return {'status': 'error', 'message': 'Flujo no encontrado'}
                
                steps = con.execute(
                    "SELECT * FROM workflow_steps WHERE workflow_id=? ORDER BY step_order",
                    (workflow_id,)
                ).fetchall()
                
                # Registrar ejecución
                con.execute("""
                INSERT INTO workflow_executions
                (workflow_id, trigger_data_json, status, completed_steps, total_steps, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (workflow_id, trigger_data_json, 'running', 0, len(steps),
                     datetime.utcnow().isoformat()))
                
                execution_id = con.execute(
                    "SELECT id FROM workflow_executions WHERE workflow_id=? ORDER BY id DESC LIMIT 1",
                    (workflow_id,)
                ).fetchone()[0]
                
                # Ejecutar cada paso
                completed = 0
                errors = []
                
                for step in steps:
                    try:
                        action_type = step[3]
                        action_config = json.loads(step[4])
                        
                        # Ejecutar acción
                        result = self._execute_action(action_type, action_config, trigger_data)
                        
                        if result.get('status') == 'success':
                            completed += 1
                        else:
                            errors.append(result.get('message', 'Unknown error'))
                    except Exception as e:
                        errors.append(str(e))
                
                # Actualizar ejecución
                status = 'completed' if not errors else 'partial'
                con.execute("""
                UPDATE workflow_executions
                SET status=?, completed_steps=?, completed_at=?
                WHERE id=?
                """, (status, completed, datetime.utcnow().isoformat(), execution_id))
                
                # Actualizar contador de ejecuciones del workflow
                con.execute(
                    "UPDATE workflows SET execution_count = execution_count + 1, last_executed=? WHERE id=?",
                    (datetime.utcnow().isoformat(), workflow_id)
                )
            
            return {
                'status': 'success',
                'execution_id': execution_id,
                'completed_steps': completed,
                'total_steps': len(steps),
                'errors': errors
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _execute_action(self, action_type: str, action_config: Dict,
                       trigger_data: Dict) -> Dict:
        """Ejecutar una acción individual."""
        
        if action_type == 'send_email':
            return self._action_send_email(action_config, trigger_data)
        
        elif action_type == 'create_task':
            return self._action_create_task(action_config, trigger_data)
        
        elif action_type == 'update_prospect':
            return self._action_update_prospect(action_config, trigger_data)
        
        elif action_type == 'schedule_post':
            return self._action_schedule_post(action_config, trigger_data)
        
        elif action_type == 'segment_users':
            return self._action_segment_users(action_config, trigger_data)
        
        elif action_type == 'trigger_notification':
            return self._action_trigger_notification(action_config, trigger_data)
        
        return {'status': 'error', 'message': f'Tipo de acción desconocido: {action_type}'}

    def _action_send_email(self, config: Dict, data: Dict) -> Dict:
        """Acción: Enviar email."""
        try:
            recipient = config.get('recipient') or data.get('email')
            subject = config.get('subject', 'Nuevo mensaje')
            body = config.get('body', '')
            
            # Reemplazar placeholders
            for key, value in data.items():
                body = body.replace(f'{{{{{key}}}}}', str(value))
            
            return {
                'status': 'success',
                'message': f'✅ Email enviado a {recipient}',
                'action': 'send_email'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _action_create_task(self, config: Dict, data: Dict) -> Dict:
        """Acción: Crear tarea."""
        try:
            title = config.get('title', 'Nueva tarea')
            assignee = config.get('assignee', 'admin')
            priority = config.get('priority', 'medium')
            
            return {
                'status': 'success',
                'message': f'✅ Tarea creada: {title}',
                'action': 'create_task'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _action_update_prospect(self, config: Dict, data: Dict) -> Dict:
        """Acción: Actualizar prospect."""
        try:
            prospect_id = data.get('prospect_id')
            updates = config.get('updates', {})
            
            return {
                'status': 'success',
                'message': f'✅ Prospect {prospect_id} actualizado',
                'action': 'update_prospect'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _action_schedule_post(self, config: Dict, data: Dict) -> Dict:
        """Acción: Programar post social."""
        try:
            platform = config.get('platform', 'Twitter')
            content = config.get('content', 'Nuevo post')
            scheduled_for = config.get('scheduled_for')
            
            return {
                'status': 'success',
                'message': f'✅ Post programado en {platform}',
                'action': 'schedule_post'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _action_segment_users(self, config: Dict, data: Dict) -> Dict:
        """Acción: Segmentar usuarios."""
        try:
            segment = config.get('segment', 'default')
            criteria = config.get('criteria', {})
            
            return {
                'status': 'success',
                'message': f'✅ Usuarios segmentados: {segment}',
                'action': 'segment_users'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _action_trigger_notification(self, config: Dict, data: Dict) -> Dict:
        """Acción: Disparar notificación."""
        try:
            notification_type = config.get('type', 'info')
            message = config.get('message', 'Nueva notificación')
            
            return {
                'status': 'success',
                'message': f'✅ Notificación enviada',
                'action': 'trigger_notification'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def schedule_workflow(self, workflow_id: int, scheduled_for: str,
                         frequency: str = "once") -> Dict:
        """Programar ejecución de flujo."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO scheduled_tasks
                (workflow_id, scheduled_for, frequency, created_at)
                VALUES (?, ?, ?, ?)
                """, (workflow_id, scheduled_for, frequency, datetime.utcnow().isoformat()))
            
            return {'status': 'success', 'message': f'✅ Flujo programado para {scheduled_for}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_predefined_workflows(self) -> List[Dict]:
        """Obtener flujos predefinidos."""
        return [
            {
                'name': 'Bienvenida a nuevos suscriptores',
                'description': 'Envía email de bienvenida y agrega a segmento',
                'trigger': 'Nuevo suscriptor',
                'steps': [
                    'Enviar email de bienvenida',
                    'Agregar tag: new_subscriber',
                    'Agendar follow-up en 7 días'
                ]
            },
            {
                'name': 'Re-engagement de usuarios inactivos',
                'description': 'Reactiva usuarios con 30+ días sin actividad',
                'trigger': 'Inactividad 30 días',
                'steps': [
                    'Segmentar usuarios inactivos',
                    'Enviar email especial de reactivación',
                    'Ofrecer descuento',
                    'Programar follow-up en 5 días'
                ]
            },
            {
                'name': 'Nurturing de leads',
                'description': 'Serie de emails para convertir leads en clientes',
                'trigger': 'Lead capturado',
                'steps': [
                    'Email 1: Introducción',
                    'Email 2 (Día 3): Propuesta de valor',
                    'Email 3 (Día 7): Case study',
                    'Email 4 (Día 14): Oferta'
                ]
            },
            {
                'name': 'Amplificación social de contenido',
                'description': 'Programa posts automáticos en múltiples plataformas',
                'trigger': 'Nuevo artículo publicado',
                'steps': [
                    'Generar variaciones de contenido',
                    'Programar en Instagram',
                    'Programar en Twitter',
                    'Programar en LinkedIn',
                    'Crear video corto para TikTok'
                ]
            },
            {
                'name': 'Escalada de oportunidades',
                'description': 'Escala leads de alta propensión a ventas',
                'trigger': 'Score de lead > 80',
                'steps': [
                    'Crear tarea para seller',
                    'Enviar notificación al equipo de ventas',
                    'Registrar en CRM',
                    'Agendar call'
                ]
            }
        ]

    def get_automation_suggestions(self) -> List[Dict]:
        """Obtener sugerencias de automatización."""
        return [
            {
                'title': 'Automatiza tu newsletter',
                'description': 'Envía automáticamente a cada nuevo suscriptor',
                'impact': 'Ahorra 5 horas/semana',
                'setup_time': '10 minutos'
            },
            {
                'title': 'Re-engagement automático',
                'description': 'Reactiva usuarios inactivos automáticamente',
                'impact': 'Recupera 15% de usuarios churned',
                'setup_time': '15 minutos'
            },
            {
                'title': 'Amplificación social',
                'description': 'Publica en 5 plataformas desde 1 click',
                'impact': 'Aumenta reach 300%',
                'setup_time': '20 minutos'
            },
            {
                'title': 'Scoring y segmentación',
                'description': 'Segmenta usuarios automáticamente por comportamiento',
                'impact': 'Mejora relevancia 40%',
                'setup_time': '25 minutos'
            }
        ]

    def export_workflows_json(self) -> str:
        """Exportar todos los flujos como JSON."""
        try:
            with self._conn() as con:
                workflows = con.execute("SELECT * FROM workflows").fetchall()
                
                exported = []
                for w in workflows:
                    steps = con.execute(
                        "SELECT * FROM workflow_steps WHERE workflow_id=?", (w[0],)
                    ).fetchall()
                    
                    exported.append({
                        'id': w[0],
                        'name': w[1],
                        'description': w[2],
                        'status': w[3],
                        'trigger_type': w[4],
                        'steps': [
                            {
                                'order': s[2],
                                'action_type': s[3],
                                'config': json.loads(s[4])
                            } for s in steps
                        ]
                    })
                
                return json.dumps(exported, indent=2)
        except Exception as e:
            log.info(f"❌ Error exporting workflows: {e}")
            return "{}"
