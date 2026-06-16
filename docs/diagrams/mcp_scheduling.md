# MCP Scheduling Tool

```mermaid
sequenceDiagram
    title Scheduling Tool Flow (schedule_appointment)
    actor MCP as FastMCP
    participant Tool as scheduling.py
    participant DB as Django ORM

    MCP->>Tool: Call schedule_appointment(patient_id, doctor_id, date, time)
    Tool->>Tool: Parse & validate date/time format
    Tool->>DB: Lookup active Doctor by ID/Name
    DB-->>Tool: Return Doctor object
    
    Tool->>DB: Query DoctorSchedule for exact exact date/time slot
    DB-->>Tool: Return schedule_slot
    
    Tool->>DB: Check if Appointment exists for slot (SCHEDULED/COMPLETED)
    alt Already Booked
        DB-->>Tool: Match found
        Tool-->>MCP: Error: Slot is already booked
    else Slot Free
        Tool->>DB: Create Appointment instance
        alt IntegrityError (Race Condition)
            DB-->>Tool: Error: Database lock/conflict
            Tool-->>MCP: Error: Slot just booked by another request
        else Success
            DB-->>Tool: Appointment created
            Tool-->>MCP: Return success: True, appointment details
        end
    end
```

## Step-by-Step Code References

- **Call schedule_appointment**: The external prompt drives variables passed directly onto `mcp_server/tools/scheduling.py lines 4-25` representing intent mapping for transaction completion.
- **Parse & validate date/time format**: Exception handling bounds wrapping conversion of strings to python native datetime objects via `mcp_server/tools/scheduling.py lines 29-37`.
- **Lookup active Doctor by ID/Name**: Flexible check checking strings as IDs then names returning explicitly across `mcp_server/tools/scheduling.py lines 39-48`.
- **Query DoctorSchedule for exact exact date/time slot**: Bounds logic ensuring doctor has shift availability during precise timestamps via `mcp_server/tools/scheduling.py lines 50-61`.
- **Check if Appointment exists for slot (Already Booked)**: Business duplication logic avoiding overlaps queried against internal systems mapped inside `mcp_server/tools/scheduling.py lines 63-69`.
- **Create Appointment instance / IntegrityError (Race Condition)**: Transaction atomic layer operations checking `IntegrityError` to resolve threading/async overlap races occurring in `mcp_server/tools/scheduling.py lines 71-82`.
- **Return success: True, appointment details**: Formatting outputs parsing data components bounding logic responses mapped into UI interfaces via `mcp_server/tools/scheduling.py lines 84-98`.