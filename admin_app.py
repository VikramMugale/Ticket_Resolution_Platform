"""
EuronSupport - Admin Dashboard with Metrics and Analytics
"""
import streamlit as st
from database import Database
from ticket_processor import TicketProcessor
from email_service import EmailService
from config import ADMIN_PASSWORD
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="EuronSupport Admin Dashboard",
    page_icon="🔧",
    layout="wide"
)

# Initialize services
db = Database()
processor = TicketProcessor()
email_service = EmailService()

# Authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 EuronSupport Admin Login")
    password = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()

# Main dashboard
st.title("🔧 EuronSupport - Admin Dashboard")
st.markdown("### AI-Powered Ticket Management & Analytics")

# Refresh button
if st.button("🔄 Refresh Dashboard"):
    st.rerun()

# Get metrics
metrics = db.get_ticket_metrics()

# Key Metrics Row
st.subheader("📊 Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Tickets", metrics['total'])
with col2:
    st.metric("Open", metrics['by_status'].get('open', 0))
with col3:
    st.metric("In Progress", metrics['by_status'].get('in_progress', 0) + metrics['by_status'].get('assigned', 0))
with col4:
    st.metric("Resolved", metrics['by_status'].get('resolved', 0))
with col5:
    st.metric("Avg Resolution", f"{metrics['avg_resolution_days']:.1f} days")

# Charts Row
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Tickets by Status")
    if metrics['by_status']:
        status_df = pd.DataFrame(list(metrics['by_status'].items()), columns=['Status', 'Count'])
        fig = px.pie(status_df, values='Count', names='Status', 
                     color_discrete_map={
                         'open': '#FFA500',
                         'assigned': '#4169E1',
                         'in_progress': '#FF6347',
                         'resolved': '#32CD32',
                         'closed': '#808080'
                     })
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tickets yet")

with col2:
    st.subheader("📊 Tickets by Severity")
    if metrics['by_severity']:
        severity_df = pd.DataFrame(list(metrics['by_severity'].items()), columns=['Severity', 'Count'])
        fig = px.bar(severity_df, x='Severity', y='Count', 
                     color='Severity',
                     color_discrete_map={'P0': '#FF0000', 'P1': '#FF8C00', 'P2': '#FFD700'})
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No severity data yet")

# Daily Tickets Chart
if metrics['daily_tickets']:
    st.subheader("📅 Tickets Created (Last 30 Days)")
    daily_df = pd.DataFrame(metrics['daily_tickets'])
    daily_df['date'] = pd.to_datetime(daily_df['date'])
    fig = px.line(daily_df, x='date', y='count', 
                  labels={'date': 'Date', 'count': 'Number of Tickets'},
                  markers=True)
    fig.update_traces(line_color='#1f77b4', line_width=2)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Sidebar filters
st.sidebar.header("🔍 Filters")
status_filter = st.sidebar.selectbox(
    "Status",
    ["All", "open", "assigned", "in_progress", "resolved", "closed"]
)

severity_filter = st.sidebar.selectbox(
    "Severity",
    ["All", "P0", "P1", "P2"]
)

manager_filter = st.sidebar.selectbox(
    "Assigned Manager",
    ["All"] + [m['name'] for m in db.get_managers()]
)

# Get tickets
all_tickets = db.get_all_tickets(limit=500)

# Apply filters
filtered_tickets = all_tickets
if status_filter != "All":
    filtered_tickets = [t for t in filtered_tickets if t['status'] == status_filter]
if severity_filter != "All":
    filtered_tickets = [t for t in filtered_tickets if t.get('severity') == severity_filter]
if manager_filter != "All":
    filtered_tickets = [t for t in filtered_tickets if t.get('manager_name') == manager_filter]

# Tickets table
st.subheader(f"🎫 Tickets ({len(filtered_tickets)})")

if filtered_tickets:
    # Create DataFrame for display
    df_data = []
    for ticket in filtered_tickets:
        created_at = ticket.get('created_at')
        if created_at:
            if hasattr(created_at, 'strftime'):
                created_at_str = created_at.strftime('%Y-%m-%d')
            else:
                created_at_str = str(created_at)[:10]
        else:
            created_at_str = 'N/A'
        
        df_data.append({
            'Ticket #': ticket['ticket_number'],
            'Title': ticket['title'][:50] + '...' if len(ticket['title']) > 50 else ticket['title'],
            'User': ticket.get('user_name', 'N/A'),
            'Status': ticket['status'].upper(),
            'Severity': ticket.get('severity', 'N/A'),
            'Priority': ticket.get('priority', 'N/A').upper() if ticket.get('priority') else 'N/A',
            'Assigned To': ticket.get('manager_name', 'Unassigned'),
            'Created': created_at_str,
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Ticket details
    st.subheader("📋 Ticket Details")
    selected_ticket_num = st.selectbox(
        "Select a ticket to view details",
        [""] + [t['ticket_number'] for t in filtered_tickets]
    )
    
    if selected_ticket_num:
        ticket = db.get_ticket_by_number(selected_ticket_num)
        if ticket:
            # Display ticket details
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### {ticket['title']}")
                st.markdown(f"**Ticket Number:** {ticket['ticket_number']}")
                st.markdown(f"**Description:**\n{ticket['description']}")
                
                if ticket.get('category'):
                    st.markdown(f"**Category:** {ticket['category']}")
            
            with col2:
                st.markdown("### Status Information")
                status_color = {
                    'open': '🟡',
                    'assigned': '🔵',
                    'in_progress': '🟠',
                    'resolved': '🟢',
                    'closed': '⚫'
                }.get(ticket['status'], '⚪')
                st.markdown(f"**Status:** {status_color} {ticket['status'].upper()}")
                st.markdown(f"**Severity:** {ticket.get('severity', 'N/A')}")
                priority = ticket.get('priority')
                st.markdown(f"**Priority:** {priority.upper() if priority else 'N/A'}")
                st.markdown(f"**Assigned To:** {ticket.get('manager_name', 'Unassigned')}")
                if ticket.get('assigned_manager_email'):
                    st.markdown(f"**Manager Email:** {ticket['assigned_manager_email']}")
            
            # Assignment reason
            if ticket.get('assignment_reason'):
                st.info(f"**📌 Assignment Reason:** {ticket['assignment_reason']}")
            
            # Resolution
            if ticket.get('resolution'):
                st.success(f"**✅ Resolution:** {ticket['resolution']}")
                if ticket.get('resolved_at'):
                    resolved_at = ticket['resolved_at']
                    if hasattr(resolved_at, 'strftime'):
                        resolved_str = resolved_at.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        resolved_str = str(resolved_at)
                    st.caption(f"Resolved on: {resolved_str}")
            
            # Action buttons
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if ticket['status'] == 'open':
                    if st.button("🔄 Reprocess Ticket", use_container_width=True):
                        with st.spinner("Reprocessing ticket..."):
                            result = processor.process_ticket(ticket['id'])
                            if result.get('success'):
                                st.success("Ticket reprocessed and reassigned!")
                                st.rerun()
                            else:
                                st.error(f"Error: {result.get('error', 'Unknown error')}")
            
            with col2:
                if ticket['status'] in ['assigned', 'in_progress']:
                    resolution_text = st.text_area("Enter resolution details", key=f"res_{ticket['id']}", height=100)
                    if st.button("✅ Mark Resolved", key=f"resolve_{ticket['id']}", use_container_width=True):
                        if resolution_text:
                            db.update_ticket(
                                ticket['id'],
                                status='resolved',
                                resolution=resolution_text,
                                resolved_at=datetime.now()
                            )
                            db.add_ticket_log(
                                ticket['id'],
                                "resolved",
                                "admin",
                                f"Ticket resolved: {resolution_text}"
                            )
                            # Send email to user
                            if ticket.get('user_email'):
                                try:
                                    email_service.send_ticket_status_update(
                                        ticket['user_email'],
                                        ticket.get('user_name', 'User'),
                                        ticket['ticket_number'],
                                        ticket['title'],
                                        'resolved',
                                        resolution_text
                                    )
                                except:
                                    pass
                            st.success("Ticket marked as resolved!")
                            st.rerun()
                        else:
                            st.warning("Please enter resolution details")
            
            with col3:
                if ticket['status'] != 'closed':
                    if st.button("🔒 Close Ticket", use_container_width=True):
                        db.update_ticket(ticket['id'], status='closed')
                        db.add_ticket_log(ticket['id'], "closed", "admin", "Ticket closed")
                        st.success("Ticket closed!")
                        st.rerun()
            
            with col4:
                # Refresh button for resolved/closed tickets
                if ticket['status'] in ['resolved', 'closed']:
                    if st.button("🔄 Refresh Status", use_container_width=True):
                        updated = db.get_ticket(ticket['id'])
                        if updated:
                            st.success("Status refreshed!")
                            st.rerun()
                elif st.button("📧 Resend Email", use_container_width=True):
                    if ticket.get('assigned_manager_email') and ticket.get('manager_name'):
                        try:
                            email_service.send_ticket_assignment_notification(
                                ticket['assigned_manager_email'],
                                ticket['manager_name'],
                                ticket['ticket_number'],
                                ticket['title'],
                                ticket['description'],
                                ticket.get('assignment_reason', ''),
                                ticket.get('severity', 'P2'),
                                ticket.get('priority', 'medium')
                            )
                            st.success("Email sent!")
                        except:
                            st.warning("Email service not configured")
            
            # Activity Logs
            st.subheader("📜 Activity Log")
            logs = db.get_ticket_logs(ticket['id'])
            if logs:
                for log in logs:
                    action = log.get('action', '')
                    log_time = log.get('created_at', '')
                    if hasattr(log_time, 'strftime'):
                        log_time_str = log_time.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        log_time_str = str(log_time)
                    st.text(f"[{log_time_str}] {action.upper() if action else 'ACTION'} by {log.get('performed_by', 'system')}: {log.get('details', '')}")
                    if log.get('metadata'):
                        try:
                            metadata = json.loads(log['metadata']) if isinstance(log['metadata'], str) else log['metadata']
                            st.json(metadata)
                        except:
                            pass
            else:
                st.info("No activity logs yet.")
            
            # Agent Results
            st.subheader("🤖 AI Agent Processing Results")
            agent_results = db.get_agent_results(ticket['id'])
            if agent_results:
                for result in agent_results:
                    result_time = result.get('created_at', '')
                    if hasattr(result_time, 'strftime'):
                        result_time_str = result_time.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        result_time_str = str(result_time)
                    with st.expander(f"Agent: {result['agent_name']} - {result_time_str}"):
                        st.text(result['result_text'])
                        if result.get('metadata'):
                            try:
                                metadata = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                                st.json(metadata)
                            except:
                                pass
            else:
                st.info("No agent processing results yet.")
else:
    st.info("No tickets found with the selected filters.")

# Managers section
st.divider()
st.subheader("👥 Managers")
managers = db.get_managers()
if managers:
    manager_df = pd.DataFrame([
        {
            'Name': m['name'],
            'Email': m['email'],
            'Role': m['role'],
            'Department': m['department'],
            'Expertise': m['expertise']
        }
        for m in managers
    ])
    st.dataframe(manager_df, use_container_width=True, hide_index=True)

# Logout
st.sidebar.divider()
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()
