"""
Ticket processing service with automatic assignment using CrewAI
"""
import json
import re
from typing import Dict, Optional
from database import Database
from agents import create_ticket_processing_crew, extract_json_from_text
from email_service import EmailService
from config import ORG_CONTEXT

class TicketProcessor:
    def __init__(self):
        self.db = Database()
        self.email_service = EmailService()
    
    def process_ticket(self, ticket_id: int) -> Dict:
        """Process a ticket using CrewAI agents and assign to appropriate manager"""
        ticket = self.db.get_ticket(ticket_id)
        if not ticket:
            return {"error": "Ticket not found"}
        
        # Log processing start
        self.db.add_ticket_log(ticket_id, "processing_started", "system", 
                              "CrewAI agents started processing ticket")
        
        try:
            # Get past incidents for better context
            past_incidents = self.db.get_past_incidents(limit=10)
            
            # Create crew and process ticket with enhanced context
            crew = create_ticket_processing_crew(ticket['title'], ticket['description'])
            result = crew.kickoff()
            
            # Save agent result
            self.db.save_agent_result(ticket_id, "crew_processing", str(result))
            
            # Extract classification from result
            classification = self._extract_classification(str(result))
            
            # Extract manager assignment recommendation
            assignment_info = self._extract_assignment_info(str(result))
            
            # Update ticket with classification
            update_data = {
                'severity': classification.get('severity', 'P2'),
                'priority': classification.get('priority', 'medium'),
                'category': classification.get('category', 'other')
            }
            
            # Assign manager based on recommendation
            manager = None
            if assignment_info.get('recommended_manager_role'):
                manager = self._assign_manager(
                    ticket_id, 
                    assignment_info['recommended_manager_role'],
                    assignment_info.get('assignment_reason', 'Auto-assigned by AI analysis')
                )
            
            if manager:
                update_data['assigned_manager_id'] = manager['id']
                update_data['assigned_manager_email'] = manager['email']
                update_data['assignment_reason'] = assignment_info.get('assignment_reason', '')
                update_data['status'] = 'assigned'
            else:
                # Fallback: assign to Support Manager
                manager = self.db.get_manager_by_role('Support')
                if manager:
                    update_data['assigned_manager_id'] = manager['id']
                    update_data['assigned_manager_email'] = manager['email']
                    update_data['assignment_reason'] = 'Auto-assigned to Support Manager (fallback)'
                    update_data['status'] = 'assigned'
            
            # Update ticket
            updated_ticket = self.db.update_ticket(ticket_id, **update_data)
            
            # Log assignment
            self.db.add_ticket_log(
                ticket_id, 
                "assigned", 
                "system",
                f"Ticket assigned to {manager['name'] if manager else 'Support Manager'}",
                {
                    'manager_id': manager['id'] if manager else None,
                    'reason': update_data.get('assignment_reason', '')
                }
            )
            
            # Send email notification to manager
            if manager:
                self.email_service.send_ticket_assignment_notification(
                    manager_email=manager['email'],
                    manager_name=manager['name'],
                    ticket_number=ticket['ticket_number'],
                    ticket_title=ticket['title'],
                    ticket_description=ticket['description'],
                    assignment_reason=update_data.get('assignment_reason', ''),
                    severity=update_data.get('severity', 'P2'),
                    priority=update_data.get('priority', 'medium')
                )
            
            # Log processing completion
            self.db.add_ticket_log(ticket_id, "processing_completed", "system", 
                                  "Ticket processing completed and assigned")
            
            return {
                "success": True,
                "ticket": updated_ticket,
                "classification": classification,
                "assignment": assignment_info
            }
            
        except Exception as e:
            error_msg = f"Error processing ticket: {str(e)}"
            self.db.add_ticket_log(ticket_id, "processing_error", "system", error_msg)
            return {"error": error_msg}
    
    def _extract_classification(self, result_text: str) -> Dict:
        """Extract severity, priority, and category from agent result"""
        classification = {
            'severity': 'P2',
            'priority': 'medium',
            'category': 'other'
        }
        
        # Try to extract JSON
        json_data = extract_json_from_text(result_text)
        if json_data:
            classification.update({
                'severity': json_data.get('severity', 'P2'),
                'priority': json_data.get('priority', 'medium'),
                'category': json_data.get('category', 'other')
            })
        
        # Fallback: try to extract from text
        severity_match = re.search(r'(P[012]|P0|P1|P2)', result_text, re.IGNORECASE)
        if severity_match:
            classification['severity'] = severity_match.group(1).upper()
        
        priority_keywords = {
            'high': ['high', 'critical', 'urgent', 'immediate'],
            'low': ['low', 'minor', 'non-critical']
        }
        result_lower = result_text.lower()
        for priority, keywords in priority_keywords.items():
            if any(kw in result_lower for kw in keywords):
                classification['priority'] = priority
                break
        
        category_keywords = {
            'payment': ['payment', 'billing', 'deduct', 'unlock', 'purchase'],
            'video': ['video', 'streaming', 'buffering', 'playback'],
            'auth': ['login', 'otp', 'authentication', 'password'],
            'performance': ['slow', 'performance', 'dashboard', 'load'],
            'crash': ['crash', 'error', 'exception', 'fail']
        }
        for category, keywords in category_keywords.items():
            if any(kw in result_lower for kw in keywords):
                classification['category'] = category
                break
        
        return classification
    
    def _extract_assignment_info(self, result_text: str) -> Dict:
        """Extract manager assignment recommendation from agent result"""
        assignment_info = {
            'recommended_manager_role': None,
            'assignment_reason': '',
            'action_items': []
        }
        
        # Try to extract JSON
        json_data = extract_json_from_text(result_text)
        if json_data:
            assignment_info.update({
                'recommended_manager_role': json_data.get('recommended_manager_role'),
                'assignment_reason': json_data.get('assignment_reason', ''),
                'action_items': json_data.get('action_items', [])
            })
        
        # Fallback: try to extract from text
        manager_roles = ['SRE Lead', 'Backend Lead', 'Support Manager', 'QA Lead', 'Tech Lead']
        result_lower = result_text.lower()
        
        for role in manager_roles:
            if role.lower() in result_lower:
                assignment_info['recommended_manager_role'] = role
                break
        
        # Extract assignment reason
        reason_patterns = [
            r'assignment reason[:\s]+([^\n]+)',
            r'should handle[:\s]+([^\n]+)',
            r'recommended[:\s]+([^\n]+)'
        ]
        for pattern in reason_patterns:
            match = re.search(pattern, result_text, re.IGNORECASE)
            if match:
                assignment_info['assignment_reason'] = match.group(1).strip()
                break
        
        return assignment_info
    
    def _assign_manager(self, ticket_id: int, recommended_role: str, reason: str) -> Optional[Dict]:
        """Assign a manager based on role recommendation"""
        # Map role keywords to manager roles
        role_mapping = {
            'sre': 'SRE Lead',
            'infra': 'SRE Lead',
            'backend': 'Backend Lead',
            'api': 'Backend Lead',
            'support': 'Support Manager',
            'customer': 'Support Manager',
            'qa': 'QA Lead',
            'test': 'QA Lead',
            'tech': 'Tech Lead',
            'engineering': 'Tech Lead'
        }
        
        # Find matching role
        recommended_role_lower = recommended_role.lower()
        for keyword, role in role_mapping.items():
            if keyword in recommended_role_lower:
                manager = self.db.get_manager_by_role(role)
                if manager:
                    return manager
        
        # Try direct match
        manager = self.db.get_manager_by_role(recommended_role)
        if manager:
            return manager
        
        # Fallback to Support Manager
        return self.db.get_manager_by_role('Support')
