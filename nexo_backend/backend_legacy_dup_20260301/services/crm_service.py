"""
CRM Service: Customer Relationship Management integrado
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List
from enum import Enum

class LeadStatus(Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATING = "negotiating"
    WON = "won"
    LOST = "lost"

class CustomerService:
    def __init__(self, db_path: str = "crm.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de CRM."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT UNIQUE,
                phone TEXT,
                company TEXT,
                industry TEXT,
                website TEXT,
                size_category TEXT,
                lifetime_value REAL,
                acquisition_channel TEXT,
                created_at TEXT,
                updated_at TEXT,
                last_contact TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                source TEXT,
                status TEXT,
                scoring INTEGER,
                notes TEXT,
                assigned_to TEXT,
                created_at TEXT,
                updated_at TEXT,
                converted_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                interaction_type TEXT,
                channel TEXT,
                subject TEXT,
                notes TEXT,
                outcome TEXT,
                next_followup TEXT,
                created_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                deal_name TEXT,
                value REAL,
                currency TEXT,
                stage TEXT,
                expected_close_date TEXT,
                probability_percentage INTEGER,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT,
                closed_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
            """)

    def add_customer(self, name: str, email: str, phone: str = "",
                    company: str = "", industry: str = "",
                    acquisition_channel: str = "direct") -> Dict:
        """Agregar nuevo cliente."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO customers
                (name, email, phone, company, industry, acquisition_channel, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, email, phone, company, industry, acquisition_channel,
                     datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                customer_id = con.execute(
                    "SELECT id FROM customers WHERE email=?", (email,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'customer_id': customer_id,
                'message': f'✅ Cliente "{name}" agregado'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def add_lead(self, customer_id: int, source: str = "manual",
                status: str = "new", scoring: int = 0) -> Dict:
        """Agregar lead."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO leads
                (customer_id, source, status, scoring, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (customer_id, source, status, scoring,
                     datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                lead_id = con.execute(
                    "SELECT id FROM leads WHERE customer_id=? ORDER BY id DESC LIMIT 1",
                    (customer_id,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'lead_id': lead_id,
                'message': '✅ Lead agregado'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def log_interaction(self, customer_id: int, interaction_type: str,
                       channel: str = "email", subject: str = "",
                       notes: str = "", outcome: str = "") -> Dict:
        """Registrar interacción con cliente."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO interactions
                (customer_id, interaction_type, channel, subject, notes, outcome, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (customer_id, interaction_type, channel, subject, notes, outcome,
                     datetime.utcnow().isoformat()))
                
                # Actualizar last_contact en customer
                con.execute(
                    "UPDATE customers SET last_contact=? WHERE id=?",
                    (datetime.utcnow().isoformat(), customer_id)
                )
            
            return {'status': 'success', 'message': '✅ Interacción registrada'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_deal(self, customer_id: int, deal_name: str,
                   value: float = 0, stage: str = "initial",
                   expected_close_date: str = None) -> Dict:
        """Crear deal/oportunidad."""
        try:
            if not expected_close_date:
                expected_close_date = (datetime.now() + timedelta(days=30)).isoformat()
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO deals
                (customer_id, deal_name, value, stage, expected_close_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (customer_id, deal_name, value, stage, expected_close_date,
                     datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                deal_id = con.execute(
                    "SELECT id FROM deals WHERE customer_id=? ORDER BY id DESC LIMIT 1",
                    (customer_id,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'deal_id': deal_id,
                'message': f'✅ Deal "{deal_name}" creado',
                'value': f"${value}"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_deal_stage(self, deal_id: int, new_stage: str,
                         probability: int = None) -> Dict:
        """Actualizar etapa de deal."""
        try:
            with self._conn() as con:
                if probability:
                    con.execute(
                        "UPDATE deals SET stage=?, probability_percentage=?, updated_at=? WHERE id=?",
                        (new_stage, probability, datetime.utcnow().isoformat(), deal_id)
                    )
                else:
                    con.execute(
                        "UPDATE deals SET stage=?, updated_at=? WHERE id=?",
                        (new_stage, datetime.utcnow().isoformat(), deal_id)
                    )
            
            return {'status': 'success', 'message': f'✅ Deal movido a {new_stage}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_customer_profile(self, customer_id: int) -> Dict:
        """Obtener perfil completo del cliente."""
        try:
            with self._conn() as con:
                customer = con.execute(
                    "SELECT * FROM customers WHERE id=?", (customer_id,)
                ).fetchone()
                
                leads = con.execute(
                    "SELECT * FROM leads WHERE customer_id=?", (customer_id,)
                ).fetchall()
                
                interactions = con.execute(
                    "SELECT * FROM interactions WHERE customer_id=? ORDER BY created_at DESC LIMIT 10",
                    (customer_id,)
                ).fetchall()
                
                deals = con.execute(
                    "SELECT * FROM deals WHERE customer_id=? ORDER BY created_at DESC",
                    (customer_id,)
                ).fetchall()
            
            total_lifetime_value = sum(d[3] if d[3] else 0 for d in deals)
            
            return {
                'status': 'success',
                'customer': {
                    'id': customer[0],
                    'name': customer[1],
                    'email': customer[2],
                    'company': customer[4],
                    'industry': customer[5],
                    'lifetime_value': f"${total_lifetime_value:.2f}",
                    'acquisition_channel': customer[9]
                },
                'leads_count': len(leads),
                'recent_interactions': len(interactions),
                'active_deals': len([d for d in deals if d[6] != 'closed']),
                'total_value': f"${sum(d[3] if d[3] else 0 for d in deals):.2f}"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_sales_pipeline(self) -> Dict:
        """Obtener pipeline de ventas."""
        try:
            with self._conn() as con:
                pipeline = con.execute("""
                    SELECT stage, COUNT(*) as count, SUM(value) as total_value, AVG(probability_percentage) as avg_probability
                    FROM deals
                    WHERE stage != 'closed'
                    GROUP BY stage
                    ORDER BY stage
                """).fetchall()
            
            stages = {
                'initial': '🟡 Inicial',
                'qualified': '🟢 Calificado',
                'proposal': '🔵 Propuesta',
                'negotiating': '🟣 Negociando',
                'won': '✅ Ganado'
            }
            
            pipeline_data = {}
            total_in_pipeline = 0
            
            for row in pipeline:
                stage, count, value, probability = row
                value = value or 0
                total_in_pipeline += value
                
                pipeline_data[stage] = {
                    'count': count,
                    'value': f"${value:.2f}",
                    'avg_probability': f"{probability:.0f}%" if probability else "N/A",
                    'label': stages.get(stage, stage)
                }
            
            return {
                'status': 'success',
                'pipeline': pipeline_data,
                'total_value': f"${total_in_pipeline:.2f}"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def score_lead(self, lead_id: int, criteria: Dict) -> Dict:
        """Puntuar lead según criterios."""
        try:
            score = 0
            
            # Criterios de scoring
            if criteria.get('company_size') == 'enterprise':
                score += 30
            elif criteria.get('company_size') == 'mid-market':
                score += 20
            elif criteria.get('company_size') == 'startup':
                score += 10
            
            if criteria.get('engagement') == 'high':
                score += 25
            elif criteria.get('engagement') == 'medium':
                score += 15
            
            if criteria.get('budget_aligned'):
                score += 20
            
            if criteria.get('timeline') == 'immediate':
                score += 15
            elif criteria.get('timeline') == '1-3_months':
                score += 10
            
            with self._conn() as con:
                con.execute(
                    "UPDATE leads SET scoring=? WHERE id=?",
                    (score, lead_id)
                )
            
            rating = '🌟🌟🌟🌟🌟' if score >= 90 else '🌟🌟🌟🌟' if score >= 70 else '🌟🌟🌟' if score >= 50 else '🌟🌟'
            
            return {
                'status': 'success',
                'score': score,
                'rating': rating,
                'message': f'✅ Lead puntuado: {score}/100'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_customer_analytics(self) -> Dict:
        """Obtener analíticas de clientes."""
        try:
            with self._conn() as con:
                customers_count = con.execute(
                    "SELECT COUNT(*) FROM customers"
                ).fetchone()[0]
                
                active_leads = con.execute(
                    "SELECT COUNT(*) FROM leads WHERE status IN ('new', 'contacted', 'qualified')"
                ).fetchone()[0]
                
                total_pipeline = con.execute(
                    "SELECT SUM(value) FROM deals WHERE stage != 'closed'"
                ).fetchone()[0] or 0
                
                won_deals = con.execute(
                    "SELECT COUNT(*), SUM(value) FROM deals WHERE stage = 'won'"
                ).fetchone()
                
                by_channel = con.execute("""
                    SELECT acquisition_channel, COUNT(*) as count
                    FROM customers
                    GROUP BY acquisition_channel
                """).fetchall()
            
            won_count, won_value = won_deals or (0, 0)
            won_value = won_value or 0
            
            return {
                'status': 'success',
                'metrics': {
                    'total_customers': customers_count,
                    'active_leads': active_leads,
                    'pipeline_value': f"${total_pipeline:.2f}",
                    'won_deals': won_count,
                    'won_value': f"${won_value:.2f}"
                },
                'acquisition_channels': {
                    row[0]: row[1] for row in by_channel
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_next_actions(self) -> List[Dict]:
        """Obtener acciones próximas programadas."""
        return [
            {
                'customer': 'Acme Corp',
                'action': 'Follow-up call',
                'due_date': '2025-01-25',
                'priority': 'High',
                'assigned_to': 'John Sales'
            },
            {
                'customer': 'TechStart Inc',
                'action': 'Send proposal',
                'due_date': '2025-01-26',
                'priority': 'High',
                'assigned_to': 'Sarah Marketing'
            },
            {
                'customer': 'Global Systems',
                'action': 'Demo session',
                'due_date': '2025-01-27',
                'priority': 'Medium',
                'assigned_to': 'Mike Demo'
            }
        ]

    def export_customer_list(self) -> str:
        """Exportar lista de clientes en CSV."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Nombre', 'Email', 'Empresa', 'Industria', 'Lifetime Value', 'Último Contacto'])
        
        try:
            with self._conn() as con:
                cur = con.cursor()
                cur.execute("""
                    SELECT name, email, company, industry, lifetime_value, last_contact
                    FROM customers
                    ORDER BY lifetime_value DESC
                """)
                
                for row in cur.fetchall():
                    writer.writerow([
                        row[0], row[1], row[2], row[3],
                        f"${row[4]:.2f}" if row[4] else "$0",
                        row[5][:10] if row[5] else ''
                    ])
        except Exception as e:
            log.info(f"❌ Error exporting customers: {e}")
        
        return output.getvalue()

    def get_crm_dashboard_summary(self) -> Dict:
        """Obtener resumen del dashboard de CRM."""
        with self._conn() as con:
            # Estadísticas
            total_customers = con.execute(
                "SELECT COUNT(*) FROM customers"
            ).fetchone()[0]
            
            active_leads = con.execute(
                "SELECT COUNT(*) FROM leads WHERE status IN ('new', 'contacted', 'qualified')"
            ).fetchone()[0]
            
            today_interactions = con.execute(
                "SELECT COUNT(*) FROM interactions WHERE DATE(created_at) = DATE('now')"
            ).fetchone()[0]
            
            pending_followups = con.execute(
                "SELECT COUNT(*) FROM interactions WHERE next_followup IS NOT NULL AND DATE(next_followup) >= DATE('now')"
            ).fetchone()[0]
        
        return {
            'status': 'success',
            'summary': {
                'total_customers': total_customers,
                'active_leads': active_leads,
                'today_interactions': today_interactions,
                'pending_followups': pending_followups
            }
        }
