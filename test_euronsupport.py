"""
Test script for EuronSupport system
"""
import sys
import os
os.environ["DATABASE_PATH"] = "test_euronsupport.db"
from database import Database
from ticket_processor import TicketProcessor
from config import OPENAI_API_KEY

def test_system():
    print("=" * 70)
    print("EuronSupport - System Test")
    print("=" * 70)
    
    # Check API key
    if not OPENAI_API_KEY:
        print("[ERROR] OPENAI_API_KEY not set!")
        return False
    print(f"[OK] API Key loaded: {OPENAI_API_KEY[:20]}...")
    
    # Initialize database
    print("\n1. Testing PostgreSQL Database Connection...")
    try:
        db = Database()
        print("[OK] Database connected and initialized successfully")
        
        # Check managers
        managers = db.get_managers()
        print(f"[OK] Found {len(managers)} Indian managers in database")
        for m in managers:
            print(f"   - {m['name']} ({m['role']})")
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test ticket creation
    print("\n2. Testing Ticket Creation...")
    try:
        import time
        test_email = f"test_{int(time.time())}@example.com"
        user = db.get_user_by_email(test_email)
        if user:
            user_id = user['id']
            print(f"[OK] Using existing test user (ID: {user_id})")
        else:
            user_id = db.create_user("Test User", test_email, "1234567890")
            print(f"[OK] Test user created (ID: {user_id})")
        
        # Create test ticket
        ticket = db.create_ticket(
            user_id=user_id,
            title="Test: Payment got deducted but course not unlocked",
            description="I made a payment for a course but it's not showing as unlocked in my account. Payment was deducted from my card.",
            category="payment"
        )
        if ticket:
            print(f"[OK] Test ticket created: {ticket['ticket_number']}")
            ticket_id = ticket['id']
        else:
            print("[ERROR] Failed to create ticket")
            return False
    except Exception as e:
        print(f"[ERROR] Ticket creation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test AI processing
    print("\n3. Testing AI Processing (this may take 30-60 seconds)...")
    try:
        processor = TicketProcessor()
        result = processor.process_ticket(ticket_id)
        
        if result.get('success'):
            print("[OK] AI processing completed successfully!")
            print(f"   - Severity: {result['classification'].get('severity', 'N/A')}")
            print(f"   - Priority: {result['classification'].get('priority', 'N/A')}")
            print(f"   - Category: {result['classification'].get('category', 'N/A')}")
            
            if result.get('ticket', {}).get('assigned_manager_email'):
                print(f"   - Assigned to: {result['ticket'].get('manager_name', 'N/A')}")
                print(f"   - Manager Email: {result['ticket'].get('assigned_manager_email', 'N/A')}")
            
            # Check agent results
            agent_results = db.get_agent_results(ticket_id)
            print(f"   - Agent results saved: {len(agent_results)} entries")
            
            # Check logs
            logs = db.get_ticket_logs(ticket_id)
            print(f"   - Activity logs: {len(logs)} entries")
            
            # Test metrics
            print("\n4. Testing Metrics...")
            metrics = db.get_ticket_metrics()
            print(f"[OK] Metrics retrieved:")
            print(f"   - Total tickets: {metrics['total']}")
            print(f"   - By status: {metrics['by_status']}")
            print(f"   - Avg resolution: {metrics['avg_resolution_days']} days")
            
            # Test user tickets
            print("\n5. Testing User Ticket Retrieval...")
            user_tickets = db.get_user_tickets(test_email)
            print(f"[OK] Found {len(user_tickets)} tickets for user")
            
            return True
        else:
            print(f"[ERROR] AI processing failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"[ERROR] AI processing error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_system()
    print("\n" + "=" * 70)
    if success:
        print("[SUCCESS] ALL TESTS PASSED! EuronSupport is working correctly.")
        print("=" * 70)
        print("\n[READY] System is ready!")
        print("   - User Interface: http://localhost:8501")
        print("   - Admin Dashboard: http://localhost:8502")
    else:
        print("[FAILED] TESTS FAILED! Please check the errors above.")
        print("=" * 70)
    sys.exit(0 if success else 1)
