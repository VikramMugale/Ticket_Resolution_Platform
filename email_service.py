"""
Email service for sending notifications to managers
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM

class EmailService:
    def __init__(self):
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.smtp_username = SMTP_USERNAME
        self.smtp_password = SMTP_PASSWORD
        self.email_from = EMAIL_FROM or SMTP_USERNAME
    
    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Send an email"""
        if not self.smtp_username or not self.smtp_password:
            print(f"[EMAIL SERVICE] Email not configured. Would send to {to_email}: {subject}")
            print(f"[EMAIL SERVICE] Body: {body[:200]}...")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"[EMAIL SERVICE] Email sent successfully to {to_email}")
            return True
        except Exception as e:
            print(f"[EMAIL SERVICE] Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_ticket_assignment_notification(self, manager_email: str, manager_name: str, 
                                          ticket_number: str, ticket_title: str, 
                                          ticket_description: str, assignment_reason: str,
                                          severity: str, priority: str) -> bool:
        """Send ticket assignment notification to manager"""
        subject = f"New Ticket Assigned: {ticket_number} - {ticket_title}"
        
        body = f"""
Dear {manager_name},

A new ticket has been assigned to you for resolution.

Ticket Details:
- Ticket Number: {ticket_number}
- Title: {ticket_title}
- Severity: {severity}
- Priority: {priority}

Description:
{ticket_description}

Assignment Reason:
{assignment_reason}

Please log into the admin portal to view full details and begin resolution.

Best regards,
Ticket Management System
        """
        
        html_body = f"""
<html>
<body>
    <h2>New Ticket Assigned</h2>
    <p>Dear {manager_name},</p>
    <p>A new ticket has been assigned to you for resolution.</p>
    
    <h3>Ticket Details:</h3>
    <ul>
        <li><strong>Ticket Number:</strong> {ticket_number}</li>
        <li><strong>Title:</strong> {ticket_title}</li>
        <li><strong>Severity:</strong> {severity}</li>
        <li><strong>Priority:</strong> {priority}</li>
    </ul>
    
    <h3>Description:</h3>
    <p>{ticket_description}</p>
    
    <h3>Assignment Reason:</h3>
    <p>{assignment_reason}</p>
    
    <p>Please log into the admin portal to view full details and begin resolution.</p>
    
    <p>Best regards,<br>Ticket Management System</p>
</body>
</html>
        """
        
        return self.send_email(manager_email, subject, html_body, is_html=True)
    
    def send_ticket_status_update(self, user_email: str, user_name: str,
                                 ticket_number: str, ticket_title: str,
                                 status: str, resolution: str = None) -> bool:
        """Send ticket status update to user"""
        subject = f"Ticket Update: {ticket_number} - {ticket_title}"
        
        status_messages = {
            'open': 'Your ticket has been received and is being reviewed.',
            'assigned': 'Your ticket has been assigned to a specialist.',
            'in_progress': 'Your ticket is currently being worked on.',
            'resolved': 'Your ticket has been resolved.',
            'closed': 'Your ticket has been closed.'
        }
        
        status_msg = status_messages.get(status, 'Your ticket status has been updated.')
        
        body = f"""
Dear {user_name},

Your ticket status has been updated.

Ticket Number: {ticket_number}
Title: {ticket_title}
Status: {status.upper()}

{status_msg}
        """
        
        if resolution:
            body += f"\n\nResolution:\n{resolution}"
        
        return self.send_email(user_email, subject, body)
