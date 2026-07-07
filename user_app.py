"""
EuronSupport - User Interface for raising and tracking tickets
"""
import streamlit as st
from database import Database
from ticket_processor import TicketProcessor
from email_service import EmailService
import time

# Page config
st.set_page_config(
    page_title="EuronSupport - Raise a Ticket",
    page_icon="🎫",
    layout="wide"
)

# Initialize services
db = Database()
processor = TicketProcessor()
email_service = EmailService()

st.title("🎫 EuronSupport - AI-Powered Ticket Resolution")
st.markdown("### Raise a Complaint or Track Your Tickets")

# User email session
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# Tab navigation
tab1, tab2 = st.tabs(["📝 Raise New Ticket", "📊 My Tickets"])

with tab1:
    st.subheader("Create a New Ticket")
    
    # User information form
    with st.form("user_info_form"):
        st.markdown("#### Your Information")
        col1, col2 = st.columns(2)
        
        with col1:
            user_name = st.text_input("Your Name *", placeholder="Enter your full name")
            user_email = st.text_input("Your Email *", placeholder="your.email@example.com")
        
        with col2:
            user_phone = st.text_input("Phone Number (Optional)", placeholder="+91XXXXXXXXXX")
        
        st.divider()
        
        # Ticket information
        st.markdown("#### Issue Details")
        ticket_title = st.text_input("Issue Title *", placeholder="Brief description of the issue")
        
        ticket_description = st.text_area(
            "Detailed Description *",
            placeholder="Please provide as much detail as possible:\n- What happened?\n- When did it occur?\n- What were you trying to do?\n- Any error messages?",
            height=150
        )
        
        category = st.selectbox(
            "Category (Optional)",
            ["", "Payment", "Video/Streaming", "Authentication/Login", "Performance", "Crash/Error", "Other"]
        )
        
        submitted = st.form_submit_button("🚀 Submit Ticket", type="primary", use_container_width=True)

    if submitted:
        # Validation
        if not user_name or not user_email or not ticket_title or not ticket_description:
            st.error("⚠️ Please fill in all required fields (marked with *)")
        else:
            with st.spinner("Creating your ticket..."):
                try:
                    # Get or create user
                    user = db.get_user_by_email(user_email)
                    if not user:
                        user_id = db.create_user(user_name, user_email, user_phone)
                    else:
                        user_id = user['id']
                    
                    # Create ticket
                    ticket = db.create_ticket(
                        user_id=user_id,
                        title=ticket_title,
                        description=ticket_description,
                        category=category if category else None
                    )
                    
                    if not ticket:
                        st.error("Failed to create ticket. Please try again.")
                    else:
                        st.success(f"✅ Ticket created successfully! Your ticket number is: **{ticket['ticket_number']}**")
                        st.session_state.user_email = user_email
                        
                        # Process ticket in background
                        with st.spinner("🤖 AI agents are analyzing your ticket and assigning to the best manager..."):
                            result = processor.process_ticket(ticket['id'])
                            
                            if result.get('success'):
                                updated_ticket = result['ticket']
                                st.info(f"📧 An email has been sent to the assigned manager: **{updated_ticket.get('manager_name', 'Support Team')}**")
                                
                                # Show ticket details
                                with st.expander("📋 View Ticket Details", expanded=True):
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        status = updated_ticket.get('status', 'open')
                                        st.metric("Status", status.upper() if status else 'OPEN')
                                    with col2:
                                        st.metric("Severity", updated_ticket.get('severity', 'P2'))
                                    with col3:
                                        priority = updated_ticket.get('priority', 'medium')
                                        st.metric("Priority", priority.upper() if priority else 'MEDIUM')
                                    
                                    if updated_ticket.get('assignment_reason'):
                                        st.info(f"**📌 Assignment Reason:** {updated_ticket['assignment_reason']}")
                            else:
                                st.warning("Ticket created but processing encountered an issue. It will be processed shortly.")
                        
                        # Send confirmation email to user
                        try:
                            email_service.send_ticket_status_update(
                                user_email=user_email,
                                user_name=user_name,
                                ticket_number=ticket['ticket_number'],
                                ticket_title=ticket_title,
                                status='open'
                            )
                        except:
                            pass  # Email is optional
                        
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error creating ticket: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

with tab2:
    st.subheader("📊 My Tickets")
    
    # Email input for ticket lookup
    if not st.session_state.user_email:
        lookup_email = st.text_input("Enter your email to view your tickets", placeholder="your.email@example.com")
        if st.button("View My Tickets"):
            if lookup_email:
                st.session_state.user_email = lookup_email
                st.rerun()
    else:
        st.info(f"📧 Viewing tickets for: **{st.session_state.user_email}**")
        if st.button("🔄 Refresh", type="primary"):
            st.rerun()
        
        # Get user tickets
        user_tickets = db.get_user_tickets(st.session_state.user_email)
        
        if user_tickets:
            st.metric("Total Tickets", len(user_tickets))
            
            # Status summary
            status_counts = {}
            for ticket in user_tickets:
                status = ticket.get('status', 'open')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            cols = st.columns(len(status_counts))
            for idx, (status, count) in enumerate(status_counts.items()):
                with cols[idx]:
                    st.metric(status.replace('_', ' ').title(), count)
            
            st.divider()
            
            # Display tickets
            for ticket in user_tickets:
                status = ticket.get('status', 'open')
                status_emoji = {
                    'open': '🟡',
                    'assigned': '🔵',
                    'in_progress': '🟠',
                    'resolved': '🟢',
                    'closed': '⚫'
                }.get(status, '⚪')
                
                with st.expander(f"{status_emoji} {ticket['ticket_number']} - {ticket['title']} ({status.upper()})", expanded=(status in ['resolved', 'closed'])):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Status", f"{status_emoji} {status.upper()}")
                    with col2:
                        st.metric("Severity", ticket.get('severity', 'N/A'))
                    with col3:
                        priority = ticket.get('priority')
                        st.metric("Priority", priority.upper() if priority else 'N/A')
                    with col4:
                        st.metric("Assigned To", ticket.get('manager_name', 'Not Assigned'))
                    
                    st.markdown(f"**📝 Description:** {ticket['description']}")
                    created_at = ticket.get('created_at', '')
                    if hasattr(created_at, 'strftime'):
                        created_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        created_str = str(created_at)
                    st.markdown(f"**📅 Created:** {created_str}")
                    
                    if ticket.get('assignment_reason'):
                        st.info(f"**📌 Why Assigned:** {ticket['assignment_reason']}")
                    
                    if ticket.get('resolution'):
                        st.success(f"**✅ Resolution:** {ticket['resolution']}")
                        if ticket.get('resolved_at'):
                            resolved_at = ticket['resolved_at']
                            if hasattr(resolved_at, 'strftime'):
                                resolved_str = resolved_at.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                resolved_str = str(resolved_at)
                            st.caption(f"Resolved on: {resolved_str}")
                    
                    # Show logs
                    logs = db.get_ticket_logs(ticket['id'])
                    if logs:
                        with st.expander("📜 Activity Log"):
                            for log in logs:
                                action = log.get('action', '')
                                log_time = log.get('created_at', '')
                                if hasattr(log_time, 'strftime'):
                                    log_time_str = log_time.strftime('%Y-%m-%d %H:%M:%S')
                                else:
                                    log_time_str = str(log_time)
                                st.text(f"[{log_time_str}] {action.upper() if action else 'ACTION'}: {log.get('details', '')}")
                    
                    # Refresh button for resolved/closed tickets
                    if status in ['resolved', 'closed']:
                        if st.button(f"🔄 Refresh Status", key=f"refresh_{ticket['id']}"):
                            # Re-fetch ticket
                            updated = db.get_ticket(ticket['id'])
                            if updated:
                                st.success("Status refreshed!")
                                st.rerun()
        else:
            st.info("📭 No tickets found for this email address.")
            if st.button("Clear Email"):
                st.session_state.user_email = None
                st.rerun()

# Footer
st.divider()
st.markdown("---")
st.caption("💬 For support, please contact support@euronsupport.com | Powered by EuronSupport AI")
