"""
Link Security Service: Sistema de validación de URLs y protección de canal
Verifica links antes de publicar para evitar riesgos maliciosos
"""

import sqlite3
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from enum import Enum
from urllib.parse import urlparse

class LinkRiskLevel(Enum):
    SAFE = "safe"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    BLOCKED = "blocked"

class LinkSecurityService:
    """Sistema de seguridad para URLs con protección de canal."""
    
    def __init__(self, db_path: str = "link_security.db"):
        self.db_path = db_path
        self._init_db()
        self._init_security_patterns()
    
    def _conn(self):
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Crear tablas para sistema de seguridad de links."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS url_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                domain TEXT,
                risk_level TEXT,
                risk_score REAL,
                is_malicious INTEGER DEFAULT 0,
                reasons_json TEXT,
                last_scanned TEXT,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS blocked_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT UNIQUE,
                pattern_type TEXT,
                severity TEXT,
                reason TEXT,
                description TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                url TEXT,
                action TEXT,
                risk_level TEXT,
                details_json TEXT,
                timestamp TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS whitelisted_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE,
                reason TEXT,
                added_by TEXT,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS channel_deletion_exploits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exploit_name TEXT,
                pattern_indicator TEXT,
                severity TEXT,
                description TEXT,
                mitigation TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT
            )
            """)
    
    def _init_security_patterns(self):
        """Inicializar patrones de seguridad predefinidos."""
        with self._conn() as con:
            # Patrones maliciosos comunes
            malicious_patterns = [
                (r'youtube.com.*delete.*channel', 'youtube_deletion_exploit', 'critical',
                 'YouTube channel deletion exploit'), # detects attempts to delete channels
                (r'youtube.com.*privacy.*settings.*delete', 'youtube_privacy_exploit', 'critical',
                 'YouTube privacy settings deletion'),
                (r'studio.youtube.com.*delete', 'youtube_studio_delete', 'critical',
                 'YouTube Studio channel deletion'),
                (r'accounts.google.com.*delete.*account', 'google_account_deletion', 'critical',
                 'Google account deletion link'),
                (r'facebook.com.*delete.*account', 'facebook_deletion', 'high',
                 'Facebook account deletion'),
                (r'http[s]?:\/\/[^\/]+phishing', 'phishing_domain', 'high',
                 'Known phishing domain'),
                (r'bit.ly.*malware', 'suspicious_shortener', 'medium',
                 'Suspicious URL shortener'),
                (r'\.exe$', 'executable_file', 'critical',
                 'Executable file download'),
                (r'\.bat$', 'batch_file', 'high',
                 'Batch script file'),
                (r'\.scr$', 'screen_saver', 'high',
                 'Screen saver executable'),
            ]
            
            for pattern, ptype, severity, reason in malicious_patterns:
                try:
                    con.execute("""
                    INSERT OR IGNORE INTO blocked_patterns
                    (pattern, pattern_type, severity, reason, description, enabled, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    """, (pattern, ptype, severity, reason,
                         f'Pattern: {pattern}', datetime.utcnow().isoformat()))
                except:
                    pass
            
            # Exploits de eliminación de canal específicos
            deletion_exploits = [
                ('youtube_channel_deletion',
                 'studio.youtube.com/channel/*/settings/advanced',
                 'critical',
                 'Direct link to YouTube Studio channel deletion settings',
                 'Use official account settings with 2FA verification'),
                ('youtube_studio_settings_delete',
                 'youtube.com/*/account/delete',
                 'critical',
                 'Crafted URL to trigger account/channel deletion',
                 'Verify URL origin and never click from external sources'),
                ('google_account_compromise',
                 'accounts.google.com/o/oauth2/auth.*delete',
                 'critical',
                 'OAuth-based deletion attempt',
                 'Check browser address bar for official domain'),
                ('channel_transfer_exploit',
                 'youtube.com.*transfer.*ownership',
                 'high',
                 'Attempt to transfer channel ownership',
                 'Verify through YouTube Studio settings only'),
            ]
            
            for name, pattern, severity, desc, mitigation in deletion_exploits:
                try:
                    con.execute("""
                    INSERT OR IGNORE INTO channel_deletion_exploits
                    (exploit_name, pattern_indicator, severity, description, mitigation, enabled, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    """, (name, pattern, severity, desc, mitigation,
                         datetime.utcnow().isoformat()))
                except:
                    pass
            
            # Dominios seguros estándar
            safe_domains = [
                ('youtube.com', 'Official YouTube'),
                ('google.com', 'Official Google'),
                ('github.com', 'Official GitHub'),
                ('stackoverflow.com', 'Official Stack Overflow'),
                ('wikipedia.org', 'Official Wikipedia'),
                ('twitter.com', 'Official Twitter/X'),
                ('linkedin.com', 'Official LinkedIn'),
                ('medium.com', 'Official Medium'),
                ('dev.to', 'Official Dev.to'),
            ]
            
            for domain, reason in safe_domains:
                try:
                    con.execute("""
                    INSERT OR IGNORE INTO whitelisted_domains
                    (domain, reason, added_by, created_at)
                    VALUES (?, ?, 'system', ?)
                    """, (domain, reason, datetime.utcnow().isoformat()))
                except:
                    pass
    
    def scan_url(self, url: str, context: str = 'general') -> Dict:
        """
        Escanear URL y devolver evaluación de riesgo.
        context: 'general', 'youtube', 'social_media'
        """
        try:
            # Verificar si ya fue escaneada
            with self._conn() as con:
                cached = con.execute(
                    "SELECT risk_level, risk_score, reasons_json FROM url_scans WHERE url=?",
                    (url,)
                ).fetchone()
                
                if cached:
                    reasons = json.loads(cached[2]) if cached[2] else []
                    return {
                        'status': 'success',
                        'url': url,
                        'risk_level': cached[0],
                        'risk_score': cached[1],
                        'reasons': reasons,
                        'cached': True
                    }
            
            # Realizar nuevo escaneo
            risk_score = 0
            reasons = []
            
            # Validar formato de URL
            if not self._is_valid_url(url):
                risk_score += 20
                reasons.append('Invalid URL format')
            
            # Extraer dominio
            domain = self._extract_domain(url)
            
            # Comprobar si está en whitelist
            if self._is_whitelisted_domain(domain):
                risk_score = 0
                reasons = ['Whitelisted domain']
            else:
                # Escanear patrones peligrosos
                pattern_results = self._check_malicious_patterns(url)
                if pattern_results['found_patterns']:
                    risk_score += pattern_results['max_severity'] * 10
                    reasons.extend(pattern_results['patterns'])
                
                # Checks específicos para YouTube
                if context == 'youtube' or 'youtube.com' in domain:
                    youtube_risks = self._check_youtube_deletion_risks(url)
                    if youtube_risks['is_deletion_risk']:
                        risk_score += 40
                        reasons.extend(youtube_risks['risks'])
                
                # Checks de phishing
                phishing_score = self._check_phishing_indicators(url)
                risk_score += phishing_score
                if phishing_score > 0:
                    reasons.append(f'Phishing indicators detected (score: {phishing_score})')
                
                # Verificar redirecciones sospechosas
                redirect_risks = self._check_url_chains(url)
                if redirect_risks['suspicious']:
                    risk_score += redirect_risks['risk_amount']
                    reasons.extend(redirect_risks['details'])
            
            # Normalizar risk_score
            risk_score = min(100, max(0, risk_score))
            
            # Determinar nivel de riesgo
            if risk_score >= 80:
                risk_level = LinkRiskLevel.BLOCKED.value
            elif risk_score >= 60:
                risk_level = LinkRiskLevel.HIGH_RISK.value
            elif risk_score >= 40:
                risk_level = LinkRiskLevel.MEDIUM_RISK.value
            elif risk_score >= 20:
                risk_level = LinkRiskLevel.LOW_RISK.value
            else:
                risk_level = LinkRiskLevel.SAFE.value
            
            # Guardar escaneo
            with self._conn() as con:
                con.execute("""
                INSERT INTO url_scans
                (url, domain, risk_level, risk_score, is_malicious, reasons_json, last_scanned, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (url, domain, risk_level, risk_score,
                     1 if risk_score >= 60 else 0,
                     json.dumps(reasons),
                     datetime.utcnow().isoformat(),
                     datetime.utcnow().isoformat()))
            
            return {
                'status': 'success',
                'url': url,
                'domain': domain,
                'risk_level': risk_level,
                'risk_score': round(risk_score, 1),
                'is_safe': risk_score < 40,
                'reasons': reasons,
                'cached': False
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _is_valid_url(self, url: str) -> bool:
        """Validar formato básico de URL."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)*(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
            r'(?::\d+)?'  # port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(url_pattern, url) is not None
    
    def _extract_domain(self, url: str) -> str:
        """Extraer dominio de URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remover www si existe
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ''
    
    def _is_whitelisted_domain(self, domain: str) -> bool:
        """Verificar si dominio está en whitelist."""
        try:
            with self._conn() as con:
                result = con.execute(
                    "SELECT id FROM whitelisted_domains WHERE domain=? AND enabled=1",
                    (domain,)
                ).fetchone()
                return result is not None
        except:
            return False
    
    def _check_malicious_patterns(self, url: str) -> Dict:
        """Comprobar patrones maliciosos conocidos."""
        found_patterns = []
        max_severity = 0
        
        try:
            with self._conn() as con:
                patterns = con.execute(
                    """SELECT pattern, pattern_type, severity FROM blocked_patterns
                       WHERE enabled=1"""
                ).fetchall()
            
            for pattern, ptype, severity in patterns:
                try:
                    if re.search(pattern, url, re.IGNORECASE):
                        severity_score = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(severity, 1)
                        max_severity = max(max_severity, severity_score)
                        found_patterns.append(f'{ptype} ({severity}): {pattern}')
                except:
                    pass
            
            return {
                'found_patterns': len(found_patterns) > 0,
                'patterns': found_patterns,
                'max_severity': max_severity
            }
        except Exception as e:
            return {'found_patterns': False, 'patterns': [], 'max_severity': 0}
    
    def _check_youtube_deletion_risks(self, url: str) -> Dict:
        """Verificar riesgos específicos de eliminación de canal de YouTube."""
        risks = []
        
        # Patrones peligrosos de YouTube
        dangerous_paths = [
            r'studio\.youtube\.com/.*delete',
            r'youtube\.com/.*/settings/advanced/delete',
            r'accounts\.google\.com.*delete.*account',
            r'myaccount\.google\.com.*delete',
            r'studio\.youtube\.com.*channel.*settings.*delete',
            r'youtube\.com.*transfer.*ownership',
        ]
        
        for pattern in dangerous_paths:
            if re.search(pattern, url, re.IGNORECASE):
                risks.append(f'⚠️ Possible YouTube channel deletion exploit detected')
        
        return {
            'is_deletion_risk': len(risks) > 0,
            'risks': risks
        }
    
    def _check_phishing_indicators(self, url: str) -> float:
        """Detectar indicadores de phishing."""
        score = 0
        
        # Dominios falsos comunes
        phishing_indicators = [
            (r'你tube', 1.0),  # Unicode homograph
            (r'уoutube', 1.0),  # Cyrillic 'u'
            (r'youtu6e', 1.0),  # Character substitution
            (r'y0utube', 1.0),  # Character substitution
            (r'goog1e', 1.0),  # Character substitution
            (r'g0ogle', 1.0),  # Character substitution
            (r'facebook-verify', 0.5),  # Suspicious pattern
            (r'confirm-account', 0.5),  # Suspicious pattern
            (r'verify-identity', 0.5),  # Suspicious pattern
            (r'update-payment', 0.5),  # Suspicious pattern
        ]
        
        for pattern, risk_weight in phishing_indicators:
            if re.search(pattern, url, re.IGNORECASE):
                score += risk_weight * 10
        
        return min(30, score)  # Max 30 points for phishing
    
    def _check_url_chains(self, url: str) -> Dict:
        """Verificar cadenas de redirección sospechosas."""
        suspicious = False
        risk_amount = 0
        details = []
        
        # Detectar múltiples niveles de redirección
        if url.count('redirect') > 1:
            suspicious = True
            risk_amount += 10
            details.append('Multiple redirects detected')
        
        # URL shorteners conocidas (potencial riesgo)
        shorteners = ['bit.ly', 'tinyurl', 'ow.ly', 'short.link', 'goo.gl']
        for shortener in shorteners:
            if shortener in url.lower():
                risk_amount += 5
                details.append(f'URL shortener detected: {shortener}')
        
        # Parámetros sospechosos
        if 'utm_' in url and 'phishing' in url:
            suspicious = True
            risk_amount += 15
            details.append('Suspicious parameter combination')
        
        return {
            'suspicious': suspicious or risk_amount > 0,
            'risk_amount': risk_amount,
            'details': details
        }
    
    def validate_before_posting(self, channel_id: str, url: str,
                               content_id: str = None) -> Dict:
        """Validar URL antes de permitir publicación."""
        try:
            scan_result = self.scan_url(url, context='youtube')
            
            is_blocked = scan_result['risk_level'] == LinkRiskLevel.BLOCKED.value
            
            # Registrar en log
            with self._conn() as con:
                con.execute("""
                INSERT INTO security_logs
                (channel_id, url, action, risk_level, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (channel_id, url,
                     'blocked' if is_blocked else 'allowed',
                     scan_result['risk_level'],
                     json.dumps({
                         'risk_score': scan_result.get('risk_score', 0),
                         'reasons': scan_result.get('reasons', []),
                         'content_id': content_id
                     }),
                     datetime.utcnow().isoformat()))
            
            return {
                'status': 'success',
                'allowed': not is_blocked,
                'url': url,
                'risk_level': scan_result['risk_level'],
                'risk_score': scan_result.get('risk_score', 0),
                'reasons': scan_result.get('reasons', []),
                'message': f"✅ URL is safe to post" if not is_blocked else f"🚫 URL blocked for safety"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def whitelist_domain(self, domain: str, reason: str, added_by: str = 'system') -> Dict:
        """Agregar dominio a whitelist."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT OR REPLACE INTO whitelisted_domains
                (domain, reason, added_by, created_at)
                VALUES (?, ?, ?, ?)
                """, (domain, reason, added_by, datetime.utcnow().isoformat()))
            
            return {'status': 'success', 'message': f'Domain {domain} whitelisted'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def block_url_pattern(self, pattern: str, pattern_type: str,
                         severity: str = 'medium') -> Dict:
        """Agregar patrón de URL a lista de bloqueo."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT OR IGNORE INTO blocked_patterns
                (pattern, pattern_type, severity, reason, enabled, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """, (pattern, pattern_type, severity,
                     f'Custom blocked pattern: {pattern}',
                     datetime.utcnow().isoformat()))
            
            return {'status': 'success', 'message': f'Pattern blocked successfully'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_security_report(self, channel_id: str, days: int = 30) -> Dict:
        """Obtener reporte de seguridad del canal."""
        try:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self._conn() as con:
                # Resumen general
                summary = con.execute("""
                    SELECT action, COUNT(*) as count FROM security_logs
                    WHERE channel_id=? AND timestamp >= ?
                    GROUP BY action
                """, (channel_id, start_date)).fetchall()
                
                # URLs bloqueadas
                blocked = con.execute("""
                    SELECT url, risk_level, timestamp FROM security_logs
                    WHERE channel_id=? AND timestamp >= ? AND action='blocked'
                    ORDER BY timestamp DESC
                    LIMIT 20
                """, (channel_id, start_date)).fetchall()
                
                # Riesgos detectados
                risks = con.execute("""
                    SELECT risk_level, COUNT(*) as count FROM security_logs
                    WHERE channel_id=? AND timestamp >= ?
                    GROUP BY risk_level
                """, (channel_id, start_date)).fetchall()
            
            allowed_count = sum(row[1] for row in summary if row[0] == 'allowed')
            blocked_count = sum(row[1] for row in summary if row[0] == 'blocked')
            
            return {
                'status': 'success',
                'period_days': days,
                'summary': {
                    'total_scanned': allowed_count + blocked_count,
                    'allowed': allowed_count,
                    'blocked': blocked_count
                },
                'blocked_urls': [
                    {'url': b[0], 'risk_level': b[1], 'timestamp': b[2]}
                    for b in blocked
                ],
                'risk_distribution': {
                    row[0]: row[1] for row in risks
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_threat_intelligence(self) -> Dict:
        """Obtener inteligencia de amenazas actual."""
        try:
            with self._conn() as con:
                patterns = con.execute(
                    "SELECT COUNT(*) as total FROM blocked_patterns WHERE enabled=1"
                ).fetchone()[0]
                
                exploits = con.execute(
                    "SELECT COUNT(*) as total FROM channel_deletion_exploits WHERE enabled=1"
                ).fetchone()[0]
                
                recent_scans = con.execute(
                    "SELECT COUNT(*) as total FROM url_scans WHERE is_malicious=1"
                ).fetchone()[0]
                
                whitelisted = con.execute(
                    "SELECT COUNT(*) as total FROM whitelisted_domains"
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'threat_intelligence': {
                    'active_patterns': patterns,
                    'known_exploits': exploits,
                    'malicious_urls_detected': recent_scans,
                    'whitelisted_domains': whitelisted
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
