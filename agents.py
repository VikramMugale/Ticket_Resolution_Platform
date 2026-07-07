"""
CrewAI agents setup for ticket processing
"""
import json
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from config import OPENAI_API_KEY, LLM_MODEL, ORG_CONTEXT

# Lazy LLM initialization
_llm_instance = None

def get_llm():
    """Get or create LLM instance (lazy initialization)"""
    global _llm_instance
    if _llm_instance is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required. Please set it in your .env file.")
        _llm_instance = LLM(
            model=LLM_MODEL,
            api_key=OPENAI_API_KEY
        )
    return _llm_instance

def create_agents():
    """Create all CrewAI agents"""
    llm = get_llm()
    
    triage_lead = Agent(
        role="Incident Triage Lead (Support + Ops)",
        goal="Turn raw complaints into structured incidents with severity, scope, and user impact.",
        backstory=(
            "You run the incident war-room for a SaaS+EdTech platform. "
            "You classify issues (P0/P1/P2), identify blast radius, and ensure stakeholders align fast."
        ),
        llm=llm,
        verbose=True,
    )
    
    support_analyst = Agent(
        role="Customer Support Analyst",
        goal="Summarize customer complaints with patterns, reproduction hints, and affected cohorts.",
        backstory=(
            "You translate messy user language into crisp problem statements. "
            "You can infer affected devices, time windows, and steps-to-reproduce from sparse reports."
        ),
        llm=llm,
        verbose=True,
    )
    
    sre_infra = Agent(
        role="SRE / Infra Analyst",
        goal="Analyze infra/system-level causes using logs/metrics signals and propose mitigations.",
        backstory=(
            "You debug production: CDN, networking, autoscaling, queues, caches, DB performance. "
            "You prefer safe mitigations and rollback strategies."
        ),
        llm=llm,
        verbose=True,
    )
    
    backend_analyst = Agent(
        role="Backend & Data Analyst",
        goal="Map issues to backend services, DB, workers, idempotency, and data consistency.",
        backstory=(
            "You are an expert in APIs, async workers, database locks, and event-driven systems. "
            "You look for race conditions, retries, and schema mismatches."
        ),
        llm=llm,
        verbose=True,
    )
    
    qa_lead = Agent(
        role="QA Lead / Repro Specialist",
        goal="Create reproducible test plans and identify gaps in automated testing.",
        backstory=(
            "You design test suites that catch regressions before prod: mobile matrix, flags, schema changes. "
            "You write crisp repro steps and acceptance criteria."
        ),
        llm=llm,
        verbose=True,
    )
    
    tech_lead = Agent(
        role="Engineering Tech Lead",
        goal="Produce an engineering action plan with priorities, owners, and timelines.",
        backstory=(
            "You run the engineering execution. You choose between rollback, hotfix, mitigation, "
            "and long-term refactor based on impact and effort."
        ),
        llm=llm,
        verbose=True,
    )
    
    comms_manager = Agent(
        role="Product/Support Communications Manager",
        goal="Draft customer-facing updates: status page, in-app banners, and support macros.",
        backstory=(
            "You communicate incidents without panic. You set expectations, ETAs, and workarounds "
            "while engineering resolves issues."
        ),
        llm=llm,
        verbose=True,
    )
    
    return {
        'triage_lead': triage_lead,
        'support_analyst': support_analyst,
        'sre_infra': sre_infra,
        'backend_analyst': backend_analyst,
        'qa_lead': qa_lead,
        'tech_lead': tech_lead,
        'comms_manager': comms_manager
    }

def create_ticket_processing_crew(ticket_title: str, ticket_description: str):
    """Create a crew for processing a single ticket"""
    from database import Database
    db = Database()
    
    agents = create_agents()
    
    # Get past incidents for context
    past_incidents = db.get_past_incidents(limit=20)
    incidents_context = ""
    if past_incidents:
        incidents_context = "\n\nPAST INCIDENTS (for reference and pattern matching):\n"
        for incident in past_incidents:
            incidents_context += f"- Date: {incident.get('incident_date')}\n"
            incidents_context += f"  Summary: {incident.get('summary', '')}\n"
            incidents_context += f"  Category: {incident.get('category', 'N/A')}\n"
            incidents_context += f"  Severity: {incident.get('severity', 'N/A')}\n"
            if incident.get('resolution'):
                incidents_context += f"  Resolution: {incident.get('resolution', '')}\n"
            if incident.get('mitigation_steps'):
                incidents_context += f"  Mitigation: {incident.get('mitigation_steps', '')}\n"
            incidents_context += "\n"
    
    # Enhanced context with past incidents
    enhanced_context = ORG_CONTEXT.copy()
    enhanced_context['past_incidents_from_db'] = [
        {
            'date': str(inc.get('incident_date', '')),
            'summary': inc.get('summary', ''),
            'category': inc.get('category', ''),
            'severity': inc.get('severity', ''),
            'resolution': inc.get('resolution', ''),
            'mitigation': inc.get('mitigation_steps', '')
        }
        for inc in past_incidents
    ]
    
    # Context task
    task0_context = Task(
        description=(
            "You are given org/system context, recent release notes, and past incident history.\n\n"
            f"ORG CONTEXT (memory):\n{json.dumps(enhanced_context, indent=2)}\n"
            f"{incidents_context}\n"
            "Analyze this context and:\n"
            "1) Identify patterns between current ticket and past incidents\n"
            "2) Summarize key risk areas from recent changes\n"
            "3) List what to watch in metrics/logs\n"
            "4) Map this complaint to similar past incidents if applicable\n"
            "Output:\n"
            "1) 5-8 bullet 'risk hypotheses'\n"
            "2) What you would watch first in metrics/logs\n"
            "3) Any immediate suspicion about which complaints map to known incidents\n"
            "4) Similar past incidents that might help resolve this"
        ),
        expected_output="Risk hypotheses + what-to-check list + past incident patterns.",
        agent=agents['triage_lead'],
    )
    
    # Support analysis task
    task1_support = Task(
        description=(
            f"Analyze the following customer complaint:\n"
            f"Title: {ticket_title}\n"
            f"Description: {ticket_description}\n\n"
            "Create a structured support summary:\n"
            "- User impact assessment\n"
            "- Affected platform (mobile/web)\n"
            "- Time sensitivity\n"
            "- Probable reproduction hints\n"
            "- Severity classification (P0/P1/P2) with justification\n"
            "- Category classification\n"
            "Use the org context memory to map issues to past incidents or releases.\n\n"
            "IMPORTANT: At the end, output a JSON block with this exact format:\n"
            '{"severity": "P0|P1|P2", "category": "payment|video|auth|performance|crash|other", "priority": "high|medium|low"}'
        ),
        expected_output="Structured incident analysis with severity, category, and priority in JSON format.",
        agent=agents['support_analyst'],
    )
    
    # SRE analysis task
    task2_sre = Task(
        description=(
            f"Investigate infra-level signals for this incident:\n"
            f"Title: {ticket_title}\n"
            f"Description: {ticket_description}\n\n"
            "Output:\n"
            "- Key metrics to check\n"
            "- Log evidence to search for\n"
            "- Likely infra causes\n"
            "- Safe mitigation steps (feature flag, rollback, scaling, CDN config, cache tuning)\n"
            "- Confidence score (0-100) and assumptions\n\n"
            "Also suggest which manager role should handle this (SRE, Backend, Support, QA, or Tech Lead)."
        ),
        expected_output="Infra-focused RCA with mitigations, confidence, and manager role recommendation.",
        agent=agents['sre_infra'],
    )
    
    # Backend analysis task
    task3_backend = Task(
        description=(
            f"Investigate backend/data causes for this incident:\n"
            f"Title: {ticket_title}\n"
            f"Description: {ticket_description}\n\n"
            "Output:\n"
            "- Suspected service/component\n"
            "- Data consistency risks\n"
            "- Root cause hypotheses\n"
            "- Proposed code-level fixes\n"
            "- Idempotency + retry handling recommendations\n"
            "- Confidence score and what extra data you need"
        ),
        expected_output="Backend RCA mapped to services + fixes.",
        agent=agents['backend_analyst'],
    )
    
    # Tech lead action plan
    task4_plan = Task(
        description=(
            f"Synthesize all prior findings for this ticket into an action plan:\n"
            f"Title: {ticket_title}\n"
            f"Description: {ticket_description}\n\n"
            "Output MUST include:\n"
            "A) Final severity and priority classification\n"
            "B) Recommended manager role to assign (SRE Lead, Backend Lead, Support Manager, QA Lead, or Tech Lead)\n"
            "C) Assignment reason (why this manager should handle it)\n"
            "D) Quick mitigations vs long-term fixes\n"
            "E) Next steps for the assigned manager\n\n"
            "IMPORTANT: At the end, output a JSON block with this exact format:\n"
            '{"recommended_manager_role": "SRE Lead|Backend Lead|Support Manager|QA Lead|Tech Lead", "assignment_reason": "detailed reason", "action_items": ["item1", "item2"]}'
        ),
        expected_output="Action plan with manager assignment recommendation in JSON format.",
        agent=agents['tech_lead'],
    )
    
    crew = Crew(
        agents=[
            agents['triage_lead'],
            agents['support_analyst'],
            agents['sre_infra'],
            agents['backend_analyst'],
            agents['tech_lead']
        ],
        tasks=[task0_context, task1_support, task2_sre, task3_backend, task4_plan],
        process=Process.sequential,
        llm=get_llm(),
        verbose=True,
    )
    
    return crew

def extract_json_from_text(text: str) -> dict:
    """Extract JSON from agent output text"""
    import re
    # Try to find JSON block
    json_match = re.search(r'\{[^{}]*"severity"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # Try to find any JSON-like structure
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    return {}
