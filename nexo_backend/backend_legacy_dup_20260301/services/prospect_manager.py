"""
Prospect Manager: Base de datos de contactos para expandir + encuestas
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

class ProspectManager:
    def __init__(self, db_path: str = "prospects.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de prospects."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS prospects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                company TEXT,
                role TEXT,
                contact_type TEXT,
                source TEXT,
                status TEXT DEFAULT 'new',
                interest_level INTEGER DEFAULT 1,
                tags_json TEXT,
                notes TEXT,
                contacted_at TEXT,
                last_interaction TEXT,
                survey_completed INTEGER DEFAULT 0,
                survey_score INTEGER,
                added_by TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_id INTEGER,
                survey_type TEXT,
                questions_json TEXT,
                responses_json TEXT,
                completed_at TEXT,
                score INTEGER,
                feedback TEXT,
                FOREIGN KEY (prospect_id) REFERENCES prospects(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS outreach_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                target_segment TEXT,
                status TEXT DEFAULT 'draft',
                scheduled_at TEXT,
                sent_at TEXT,
                template_json TEXT,
                prospectcount INTEGER,
                responses_count INTEGER,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS prospect_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_id INTEGER,
                interaction_type TEXT,
                message TEXT,
                channel TEXT,
                response TEXT,
                responded_at TEXT,
                created_at TEXT,
                FOREIGN KEY (prospect_id) REFERENCES prospects(id)
            )
            """)

    def add_prospect(self, name: str, email: str = None, phone: str = None,
                    company: str = None, role: str = None, contact_type: str = 'lead',
                    source: str = 'manual', tags: list = None, notes: str = None,
                    added_by: str = 'admin') -> Dict:
        """Agregar nuevo prospecto."""
        try:
            tags_json = json.dumps(tags or [])
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO prospects
                (name, email, phone, company, role, contact_type, source, tags_json, 
                 notes, added_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, email, phone, company, role, contact_type, source,
                    tags_json, notes, added_by,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
                
                prospect_id = con.execute(
                    "SELECT id FROM prospects WHERE email=? ORDER BY created_at DESC LIMIT 1",
                    (email,) if email else (name,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'message': f'✅ Prospecto {name} agregado',
                'prospect_id': prospect_id
            }
        except sqlite3.IntegrityError:
            return {
                'status': 'error',
                'message': '❌ Este email ya existe en la base de datos'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_prospect(self, prospect_id: int, **kwargs) -> Dict:
        """Actualizar información del prospecto."""
        try:
            allowed_fields = [
                'name', 'email', 'phone', 'company', 'role', 'status',
                'interest_level', 'notes', 'survey_score'
            ]
            
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            if not updates:
                return {'status': 'error', 'message': 'No hay campos para actualizar'}
            
            set_clause = ', '.join([f"{k}=?" for k in updates.keys()])
            values = list(updates.values()) + [prospect_id]
            
            with self._conn() as con:
                con.execute(
                    f"UPDATE prospects SET {set_clause} WHERE id=?",
                    values
                )
            
            return {
                'status': 'success',
                'message': f'✅ Prospecto {prospect_id} actualizado'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_prospects(self, status: str = None, tags: list = None) -> list:
        """Obtener prospectos filtrados."""
        query = "SELECT * FROM prospects WHERE 1=1"
        params = []
        
        if status:
            query += " AND status=?"
            params.append(status)
        
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(query, params)
            results = cur.fetchall()
            
            # Si hay filtro de tags, filtrar en Python
            if tags:
                filtered = []
                for row in results:
                    prospect_tags = json.loads(row[11]) if row[11] else []
                    if any(tag in prospect_tags for tag in tags):
                        filtered.append(row)
                return filtered
            
            return results

    def create_survey(self, prospect_id: int, survey_type: str, 
                     questions: list) -> Dict:
        """Crear encuesta para prospecto."""
        try:
            questions_json = json.dumps(questions)
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO surveys
                (prospect_id, survey_type, questions_json, completed_at)
                VALUES (?, ?, ?, ?)
                """, (prospect_id, survey_type, questions_json, datetime.utcnow().isoformat()))
                
                survey_id = con.execute(
                    "SELECT id FROM surveys WHERE prospect_id=? ORDER BY id DESC LIMIT 1",
                    (prospect_id,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'survey_id': survey_id,
                'questions': questions
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def submit_survey_response(self, survey_id: int, responses: Dict, 
                              score: int = None) -> Dict:
        """Enviar respuestas de encuesta."""
        try:
            responses_json = json.dumps(responses)
            
            with self._conn() as con:
                con.execute("""
                UPDATE surveys 
                SET responses_json=?, score=?, completed_at=?
                WHERE id=?
                """, (
                    responses_json,
                    score,
                    datetime.utcnow().isoformat(),
                    survey_id
                ))
                
                # Obtener prospect_id y actualizar su survey_completed
                prospect_id = con.execute(
                    "SELECT prospect_id FROM surveys WHERE id=?", (survey_id,)
                ).fetchone()[0]
                
                con.execute(
                    "UPDATE prospects SET survey_completed=1, survey_score=? WHERE id=?",
                    (score, prospect_id)
                )
            
            return {
                'status': 'success',
                'message': '✅ Encuesta completada',
                'score': score
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def log_interaction(self, prospect_id: int, interaction_type: str,
                       message: str, channel: str = 'email',
                       response: str = None) -> Dict:
        """Registrar interacción con prospecto."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO prospect_interactions
                (prospect_id, interaction_type, message, channel, response, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    prospect_id, interaction_type, message, channel,
                    response, datetime.utcnow().isoformat()
                ))
                
                # Actualizar contacted_at en prospect
                con.execute(
                    "UPDATE prospects SET last_interaction=? WHERE id=?",
                    (datetime.utcnow().isoformat(), prospect_id)
                )
            
            return {'status': 'success', 'message': '✅ Interacción registrada'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_outreach_campaign(self, name: str, description: str,
                                target_segment: str, template: Dict,
                                scheduled_at: str = None) -> Dict:
        """Crear campaña de outreach."""
        try:
            template_json = json.dumps(template)
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO outreach_campaigns
                (name, description, target_segment, template_json, scheduled_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    name, description, target_segment, template_json,
                    scheduled_at, datetime.utcnow().isoformat()
                ))
                
                campaign_id = con.execute(
                    "SELECT id FROM outreach_campaigns WHERE name=? ORDER BY id DESC LIMIT 1",
                    (name,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'campaign_id': campaign_id,
                'message': f'✅ Campaña "{name}" creada'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_outreach_targets(self, campaign_id: int) -> list:
        """Obtener prospectos objetivo para campaña."""
        try:
            with self._conn() as con:
                cur = con.cursor()
                # Obtener criterios de la campaña
                cur.execute(
                    "SELECT target_segment FROM outreach_campaigns WHERE id=?",
                    (campaign_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    return []
                
                target_segment = result[0]
                
                # Obtener prospectos que coincidan
                if target_segment == 'all':
                    cur.execute("SELECT id, name, email FROM prospects WHERE status='new'")
                elif target_segment == 'high_interest':
                    cur.execute(
                        "SELECT id, name, email FROM prospects WHERE interest_level >= 3"
                    )
                elif target_segment == 'surveyed':
                    cur.execute(
                        "SELECT id, name, email FROM prospects WHERE survey_completed=1"
                    )
                else:
                    cur.execute(
                        "SELECT id, name, email FROM prospects WHERE 1=0"
                    )
                
                return cur.fetchall()
        except Exception as e:
            log.info(f"❌ Error getting targets: {e}")
            return []

    def get_prospect_stats(self) -> Dict:
        """Obtener estadísticas de prospectos."""
        with self._conn() as con:
            cur = con.cursor()
            
            # Totales
            cur.execute("SELECT COUNT(*) FROM prospects")
            total = cur.fetchone()[0]
            
            # Por estado
            cur.execute("""
                SELECT status, COUNT(*) as count 
                FROM prospects 
                GROUP BY status
            """)
            by_status = dict(cur.fetchall())
            
            # Por nivel de interés
            cur.execute("""
                SELECT interest_level, COUNT(*) as count 
                FROM prospects 
                GROUP BY interest_level
            """)
            by_interest = dict(cur.fetchall())
            
            # Surveys completadas
            cur.execute("SELECT COUNT(*) FROM prospects WHERE survey_completed=1")
            surveys_completed = cur.fetchone()[0]
            
            # Por fuente
            cur.execute("""
                SELECT source, COUNT(*) as count 
                FROM prospects 
                GROUP BY source
            """)
            by_source = dict(cur.fetchall())
            
            return {
                'total_prospects': total,
                'by_status': by_status,
                'by_interest': by_interest,
                'surveys_completed': surveys_completed,
                'by_source': by_source,
                'conversion_rate': f"{(surveys_completed / total * 100):.1f}%" if total > 0 else "0%"
            }

    def export_prospects_csv(self) -> str:
        """Exportar prospectos a CSV."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Nombre', 'Email', 'Teléfono', 'Empresa', 'Rol', 
            'Tipo', 'Fuente', 'Estado', 'Nivel Interés', 'Tags', 
            'Encuesta Completada', 'Score', 'Notas', 'Creado'
        ])
        
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM prospects")
            
            for row in cur.fetchall():
                name, email, phone, company, role, contact_type, source, status, interest, tags, notes, survey_completed, score, *rest = row[1:]
                tags_str = ', '.join(json.loads(tags)) if tags else ''
                writer.writerow([
                    name, email, phone, company, role, contact_type, source,
                    status, interest, tags_str, survey_completed, score, notes
                ])
        
        return output.getvalue()

    def import_prospects_csv(self, csv_content: str) -> Dict:
        """Importar prospectos desde CSV."""
        import csv
        from io import StringIO
        
        reader = csv.DictReader(StringIO(csv_content))
        imported = 0
        errors = []
        
        for row in reader:
            try:
                tags = [t.strip() for t in row.get('Tags', '').split(',')] if row.get('Tags') else []
                
                result = self.add_prospect(
                    name=row['Nombre'],
                    email=row.get('Email'),
                    phone=row.get('Teléfono'),
                    company=row.get('Empresa'),
                    role=row.get('Rol'),
                    contact_type=row.get('Tipo', 'lead'),
                    source=row.get('Fuente', 'import'),
                    tags=tags,
                    notes=row.get('Notas')
                )
                if result['status'] == 'success':
                    imported += 1
            except Exception as e:
                errors.append(f"Error en {row.get('Nombre', 'unknown')}: {str(e)}")
        
        return {
            'status': 'success',
            'imported': imported,
            'errors': errors
        }
