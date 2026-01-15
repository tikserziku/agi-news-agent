#!/usr/bin/env python3
"""
Architect - создание планов внедрения технологий
Генерирует архитектуру и план действий для интеграции
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "knowledge" / "news.db"

# Шаблоны архитектуры для разных типов технологий
ARCHITECTURE_TEMPLATES = {
    "protocol": {
        "components": ["connector", "adapter", "handler"],
        "integration_points": ["MCP-HUB", "API Gateway"],
        "estimated_effort": "medium"
    },
    "framework": {
        "components": ["wrapper", "service", "cli"],
        "integration_points": ["MCP-HUB tools"],
        "estimated_effort": "high"
    },
    "tool": {
        "components": ["installer", "config", "wrapper"],
        "integration_points": ["systemd service", "MCP tool"],
        "estimated_effort": "low"
    },
    "default": {
        "components": ["research", "poc", "integration"],
        "integration_points": ["TBD"],
        "estimated_effort": "unknown"
    }
}

def get_pending_technologies():
    """Get technologies awaiting architecture"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, name, description FROM technologies 
                 WHERE status = 'discovered' AND architecture IS NULL''')
    results = c.fetchall()
    conn.close()
    return results

def determine_tech_type(name, description):
    """Determine technology type"""
    text = f"{name} {description}".lower()
    
    if any(w in text for w in ["protocol", "standard", "api"]):
        return "protocol"
    elif any(w in text for w in ["framework", "library", "sdk"]):
        return "framework"
    elif any(w in text for w in ["tool", "cli", "utility"]):
        return "tool"
    return "default"

def generate_architecture(tech_id, name, description):
    """Generate architecture plan for technology"""
    tech_type = determine_tech_type(name, description)
    template = ARCHITECTURE_TEMPLATES.get(tech_type, ARCHITECTURE_TEMPLATES["default"])
    
    architecture = {
        "technology": name,
        "type": tech_type,
        "generated_at": datetime.now().isoformat(),
        "components": template["components"],
        "integration_points": template["integration_points"],
        "estimated_effort": template["estimated_effort"],
        "phases": [
            {"phase": 1, "name": "Research", "tasks": [
                f"Study {name} documentation",
                "Identify integration requirements",
                "Check compatibility with MCP-HUB"
            ]},
            {"phase": 2, "name": "POC", "tasks": [
                f"Create minimal {name} integration",
                "Test basic functionality",
                "Document findings"
            ]},
            {"phase": 3, "name": "Integration", "tasks": [
                f"Implement {name} in MCP-HUB",
                "Add MCP tools if applicable",
                "Write tests"
            ]},
            {"phase": 4, "name": "Deploy", "tasks": [
                "Deploy to VM2",
                "Configure systemd service",
                "Update documentation"
            ]}
        ]
    }
    
    return architecture

def create_implementation_plan(architecture):
    """Create actionable implementation plan"""
    plan = {
        "technology": architecture["technology"],
        "status": "planned",
        "effort": architecture["estimated_effort"],
        "steps": []
    }
    
    step_num = 1
    for phase in architecture["phases"]:
        for task in phase["tasks"]:
            plan["steps"].append({
                "step": step_num,
                "phase": phase["name"],
                "task": task,
                "status": "pending"
            })
            step_num += 1
    
    return plan

def plan_all_technologies():
    """Create plans for all pending technologies"""
    pending = get_pending_technologies()
    planned = 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for tech_id, name, description in pending:
        # Generate architecture
        arch = generate_architecture(tech_id, name, description)
        plan = create_implementation_plan(arch)
        
        # Save to database
        c.execute('''UPDATE technologies 
                     SET architecture = ?, implementation_plan = ?, status = 'planned'
                     WHERE id = ?''',
                  (json.dumps(arch), json.dumps(plan), tech_id))
        planned += 1
        
        print(f"Planned: {name}")
        print(f"  Type: {arch['type']}")
        print(f"  Effort: {arch['estimated_effort']}")
        print(f"  Steps: {len(plan['steps'])}")
    
    conn.commit()
    conn.close()
    
    return {"planned": planned}

def show_plans():
    """Show all implementation plans"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT name, status, implementation_plan FROM technologies 
                 WHERE implementation_plan IS NOT NULL''')
    results = c.fetchall()
    conn.close()
    
    for name, status, plan_json in results:
        plan = json.loads(plan_json)
        print(f"\n=== {name} [{status}] ===")
        print(f"Effort: {plan.get('effort', 'unknown')}")
        print("Steps:")
        for step in plan.get("steps", [])[:5]:
            print(f"  {step['step']}. [{step['phase']}] {step['task']}")
        if len(plan.get("steps", [])) > 5:
            print(f"  ... and {len(plan['steps']) - 5} more steps")

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    
    if cmd == "plan":
        result = plan_all_technologies()
        print(json.dumps(result))
    elif cmd == "show":
        show_plans()
