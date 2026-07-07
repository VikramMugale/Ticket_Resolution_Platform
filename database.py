"""
Database models and operations for EuronSupport ticket management system
PostgreSQL (Neon) implementation
"""
import psycopg2
import psycopg2.extras
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from config import DATABASE_URL

class Database:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or DATABASE_URL
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(self.db_url)
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Managers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS managers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    role VARCHAR(100) NOT NULL,
                    department VARCHAR(100),
                    expertise TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tickets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    ticket_number VARCHAR(100) UNIQUE NOT NULL,
                    user_id INTEGER REFERENCES users(id),
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category VARCHAR(100),
                    severity VARCHAR(10),
                    status VARCHAR(50) DEFAULT 'open',
                    priority VARCHAR(20),
                    assigned_manager_id INTEGER REFERENCES managers(id),
                    assigned_manager_email VARCHAR(255),
                    assignment_reason TEXT,
                    resolution TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP
                )
            """)
            
            # Ticket logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ticket_logs (
                    id SERIAL PRIMARY KEY,
                    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
                    action VARCHAR(100) NOT NULL,
                    performed_by VARCHAR(255),
                    details TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Agent processing results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_results (
                    id SERIAL PRIMARY KEY,
                    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
                    agent_name VARCHAR(255) NOT NULL,
                    result_text TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Past incidents table for context
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS past_incidents (
                    id SERIAL PRIMARY KEY,
                    incident_date DATE NOT NULL,
                    summary TEXT NOT NULL,
                    category VARCHAR(100),
                    severity VARCHAR(10),
                    resolution TEXT,
                    mitigation_steps TEXT,
                    related_tickets TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
                CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);
                CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);
                CREATE INDEX IF NOT EXISTS idx_ticket_logs_ticket_id ON ticket_logs(ticket_id);
            """)
            
            # Insert default managers if not exists
            self._insert_default_managers(cursor)
            conn.commit()
    
    def _insert_default_managers(self, cursor):
        """Insert default Indian managers"""
        default_managers = [
            ("Rajesh Kumar", "rajesh.kumar@euronsupport.com", "SRE Lead", "Infrastructure", "CDN, Networking, Autoscaling"),
            ("Priya Sharma", "priya.sharma@euronsupport.com", "Backend Lead", "Engineering", "APIs, Databases, Workers"),
            ("Amit Patel", "amit.patel@euronsupport.com", "Support Manager", "Customer Support", "User Issues, Communication"),
            ("Anjali Singh", "anjali.singh@euronsupport.com", "QA Lead", "Quality Assurance", "Testing, Reproductions"),
            ("Vikram Reddy", "vikram.reddy@euronsupport.com", "Tech Lead", "Engineering", "Architecture, Planning"),
        ]
        
        for name, email, role, dept, expertise in default_managers:
            cursor.execute("""
                INSERT INTO managers (name, email, role, department, expertise)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (name, email, role, dept, expertise))
    
    def create_user(self, name: str, email: str, phone: str = None) -> int:
        """Create a new user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (name, email, phone)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (name, email, phone))
            return cursor.fetchone()[0]
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_tickets(self, user_email: str) -> List[Dict]:
        """Get all tickets for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT t.*, u.name as user_name, u.email as user_email,
                       m.name as manager_name
                FROM tickets t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN managers m ON t.assigned_manager_id = m.id
                WHERE u.email = %s
                ORDER BY t.created_at DESC
            """, (user_email,))
            return [dict(row) for row in cursor.fetchall()]
    
    def create_ticket(self, user_id: int, title: str, description: str, 
                     category: str = None) -> Dict:
        """Create a new ticket"""
        ticket_number = f"EURON-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp())}"
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                INSERT INTO tickets (ticket_number, user_id, title, description, category, status)
                VALUES (%s, %s, %s, %s, %s, 'open')
                RETURNING id
            """, (ticket_number, user_id, title, description, category))
            
            ticket_id = cursor.fetchone()['id']
            
            # Log ticket creation
            cursor.execute("""
                INSERT INTO ticket_logs (ticket_id, action, performed_by, details)
                VALUES (%s, %s, %s, %s)
            """, (ticket_id, "created", "system", f"Ticket created: {title}"))
            
            # Fetch the created ticket
            cursor.execute("""
                SELECT t.*, u.name as user_name, u.email as user_email,
                       m.name as manager_name
                FROM tickets t
                LEFT JOIN users u ON t.user_id = u.id
                LEFT JOIN managers m ON t.assigned_manager_id = m.id
                WHERE t.id = %s
            """, (ticket_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_ticket(self, ticket_id: int) -> Optional[Dict]:
        """Get ticket by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT t.*, u.name as user_name, u.email as user_email,
                       m.name as manager_name
                FROM tickets t
                LEFT JOIN users u ON t.user_id = u.id
                LEFT JOIN managers m ON t.assigned_manager_id = m.id
                WHERE t.id = %s
            """, (ticket_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_ticket_by_number(self, ticket_number: str) -> Optional[Dict]:
        """Get ticket by ticket number"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT t.*, u.name as user_name, u.email as user_email,
                       m.name as manager_name
                FROM tickets t
                LEFT JOIN users u ON t.user_id = u.id
                LEFT JOIN managers m ON t.assigned_manager_id = m.id
                WHERE t.ticket_number = %s
            """, (ticket_number,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_ticket(self, ticket_id: int, **kwargs) -> Dict:
        """Update ticket fields"""
        allowed_fields = ['status', 'severity', 'priority', 'assigned_manager_id', 
                         'assigned_manager_email', 'assignment_reason', 'resolution', 
                         'category', 'resolved_at']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = %s")
                values.append(value)
        
        if not updates:
            return self.get_ticket(ticket_id)
        
        updates.append("updated_at = %s")
        values.append(datetime.now())
        values.append(ticket_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE tickets 
                SET {', '.join(updates)}
                WHERE id = %s
            """, values)
            
            return self.get_ticket(ticket_id)
    
    def get_all_tickets(self, status: str = None, limit: int = 100) -> List[Dict]:
        """Get all tickets with optional status filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if status and status != "All":
                cursor.execute("""
                    SELECT t.*, u.name as user_name, u.email as user_email,
                           m.name as manager_name
                    FROM tickets t
                    LEFT JOIN users u ON t.user_id = u.id
                    LEFT JOIN managers m ON t.assigned_manager_id = m.id
                    WHERE t.status = %s
                    ORDER BY t.created_at DESC
                    LIMIT %s
                """, (status, limit))
            else:
                cursor.execute("""
                    SELECT t.*, u.name as user_name, u.email as user_email,
                           m.name as manager_name
                    FROM tickets t
                    LEFT JOIN users u ON t.user_id = u.id
                    LEFT JOIN managers m ON t.assigned_manager_id = m.id
                    ORDER BY t.created_at DESC
                    LIMIT %s
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_managers(self, is_active: bool = True) -> List[Dict]:
        """Get all managers"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM managers WHERE is_active = %s
                ORDER BY name
            """, (is_active,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_manager_by_role(self, role_keyword: str) -> Optional[Dict]:
        """Get manager by role keyword"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM managers 
                WHERE (role LIKE %s OR department LIKE %s OR expertise LIKE %s)
                AND is_active = TRUE
                LIMIT 1
            """, (f"%{role_keyword}%", f"%{role_keyword}%", f"%{role_keyword}%"))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_ticket_log(self, ticket_id: int, action: str, performed_by: str, 
                      details: str = None, metadata: Dict = None):
        """Add a log entry for a ticket"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ticket_logs (ticket_id, action, performed_by, details, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (ticket_id, action, performed_by, details, 
                  json.dumps(metadata) if metadata else None))
    
    def get_ticket_logs(self, ticket_id: int) -> List[Dict]:
        """Get all logs for a ticket"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM ticket_logs 
                WHERE ticket_id = %s
                ORDER BY created_at ASC
            """, (ticket_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def save_agent_result(self, ticket_id: int, agent_name: str, 
                         result_text: str, metadata: Dict = None):
        """Save agent processing result"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_results (ticket_id, agent_name, result_text, metadata)
                VALUES (%s, %s, %s, %s)
            """, (ticket_id, agent_name, result_text, 
                  json.dumps(metadata) if metadata else None))
    
    def get_agent_results(self, ticket_id: int) -> List[Dict]:
        """Get all agent results for a ticket"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM agent_results 
                WHERE ticket_id = %s
                ORDER BY created_at ASC
            """, (ticket_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_past_incidents(self, limit: int = 50) -> List[Dict]:
        """Get past incidents for context"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM past_incidents
                ORDER BY incident_date DESC
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_ticket_metrics(self) -> Dict:
        """Get metrics for dashboard"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Total tickets
            cursor.execute("SELECT COUNT(*) as total FROM tickets")
            total = cursor.fetchone()['total']
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM tickets
                GROUP BY status
            """)
            by_status = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # By severity
            cursor.execute("""
                SELECT severity, COUNT(*) as count
                FROM tickets
                WHERE severity IS NOT NULL
                GROUP BY severity
            """)
            by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
            
            # Resolution time (average days)
            cursor.execute("""
                SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 86400) as avg_days
                FROM tickets
                WHERE resolved_at IS NOT NULL
            """)
            avg_resolution = cursor.fetchone()['avg_days'] or 0
            
            # Tickets by day (last 30 days)
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM tickets
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            daily_tickets = cursor.fetchall()
            
            # Convert date objects to strings
            daily_tickets_list = []
            for row in daily_tickets:
                row_dict = dict(row)
                if 'date' in row_dict and row_dict['date']:
                    # Convert date to string if it's a date object
                    if hasattr(row_dict['date'], 'isoformat'):
                        row_dict['date'] = row_dict['date'].isoformat()
                    else:
                        row_dict['date'] = str(row_dict['date'])
                daily_tickets_list.append(row_dict)
            
            return {
                'total': total,
                'by_status': by_status,
                'by_severity': by_severity,
                'avg_resolution_days': round(float(avg_resolution) if avg_resolution else 0, 2),
                'daily_tickets': daily_tickets_list
            }