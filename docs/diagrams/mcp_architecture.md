# Architecture of EHREngine MCP System

```mermaid
C4Component
    title Architecture of EHREngine MCP System
    
    Person(llm, "LLM Client", "Interacts with standard MCP protocol")
    
    System_Boundary(mcp_system, "FastMCP Server") {
        Component(server, "FastMCP App", "mcp_server/server.py", "Registers tools and handles MCP Protocol")
        
        Container_Boundary(tools_suite, "MCP Tools Suite") {
            Component(availability, "availability.py", "Availability", "check_provider_availability")
            Component(billing, "billing.py", "Billing", "estimate_visit_cost")
            Component(catalog, "catalog.py", "Catalog", "list_insurance_payers, list_medical_specialties")
            Component(insurance, "insurance.py", "Insurance", "verify_insurance_eligibility")
            Component(refills, "refills.py", "Refills", "list_patient_prescriptions, request_medication_refill")
            Component(scheduling, "scheduling.py", "Scheduling", "schedule_appointment")
        }
    }
    
    System_Boundary(django, "Django Application (clinic)") {
        Component(orm, "Django ORM Models", "clinic.models", "Appointment, Doctor, InsurancePayer, Prescription, etc.")
    }
    
    SystemDb(db, "PostgreSQL Database", "db_data", "Stores all EHR state")
    
    Rel(llm, server, "Calls tools via MCP Protocol", "JSON-RPC")
    
    Rel(server, availability, "Dispatches mapped tools")
    Rel(server, billing, "Dispatches mapped tools")
    Rel(server, catalog, "Dispatches mapped tools")
    Rel(server, insurance, "Dispatches mapped tools")
    Rel(server, refills, "Dispatches mapped tools")
    Rel(server, scheduling, "Dispatches mapped tools")

    Rel(availability, orm, "Fetches/Updates State (sync-to-async)")
    Rel(billing, orm, "Fetches/Updates State (sync-to-async)")
    Rel(catalog, orm, "Fetches/Updates State (sync-to-async)")
    Rel(insurance, orm, "Fetches/Updates State (sync-to-async)")
    Rel(refills, orm, "Fetches/Updates State (sync-to-async)")
    Rel(scheduling, orm, "Fetches/Updates State (sync-to-async)")

    Rel(orm, db, "SQL Queries")
```

## Step-by-Step Code References

- **LLM Client**: Represents any agent resolving the instructions mapped in `mcp_server/server.py lines 16-27`.
- **FastMCP App**: Declared in `mcp_server/server.py line 14`. Bootstrapping and tool injection handlers (`_traced_async_tool`) occur in `mcp_server/server.py lines 30-41`.
- **availability.py**: Registered via FastMCP sync-wrapper on `mcp_server/server.py line 46`.
- **billing.py**: Tool mappings initialized on `mcp_server/server.py line 50`.
- **catalog.py**: Tool mappings initialized on `mcp_server/server.py lines 43-44`.
- **insurance.py**: Component injection tracked on `mcp_server/server.py line 45`.
- **refills.py**: Functions exposed endpoints mapping onto `mcp_server/server.py lines 48-49`.
- **scheduling.py**: System terminal execution point registered via `mcp_server/server.py line 47`.
- **Django ORM Models**: Underlying model state manipulated through querysets linked in tool implementations via local application `clinic.models`.
- **PostgreSQL Database**: Configured SQL persistence layer managed natively backing Python's execution logic.