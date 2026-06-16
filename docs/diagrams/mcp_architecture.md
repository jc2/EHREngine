# EHREngine MCP Architecture & Workflow

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Client as MCP Client (Agent)
    participant Server as FastMCP Server (EHREngine)
    participant Tools as MCP Tools
    participant ORM as Django ORM / Models
    participant DB as PostgreSQL DB

    Client->>Server: Call list_medical_specialties()
    Server->>Tools: Invoke _traced_async_tool(_specialties)
    Tools->>ORM: Query MedicalDepartment
    ORM->>DB: SELECT departments
    DB-->>ORM: Return records
    ORM-->>Tools: Model instances
    Tools-->>Server: Return specialties (dict)
    Server-->>Client: JSON Response (Specialties)

    Client->>Server: Call verify_insurance_eligibility(patient, payer)
    Server->>Tools: Invoke _traced_async_tool(_verify)
    Tools->>ORM: Query PatientInsurance
    ORM->>DB: SELECT active policies
    DB-->>ORM: Return records
    ORM-->>Tools: Eligibility result (HMO/PPO)
    Tools-->>Server: Return eligibility (dict)
    Server-->>Client: JSON Response (Eligibility)

    Client->>Server: Call check_provider_availability(specialty, date)
    Server->>Tools: Invoke _traced_async_tool(_check)
    Tools->>ORM: Query DoctorSchedule <br> (exclude SCHEDULED/COMPLETED)
    ORM->>DB: SELECT available slots
    DB-->>ORM: Return records
    ORM-->>Tools: Formatted open slots
    Tools-->>Server: Return slots (dict)
    Server-->>Client: JSON Response (Availability)

    Client->>Server: Call schedule_appointment(patient, doctor, date, time)
    Server->>Tools: Invoke _traced_async_tool(_schedule)
    Tools->>ORM: Appointment.objects.create(...)
    ORM->>DB: INSERT INTO clinic_appointment
    DB-->>ORM: Success / IntegrityError
    ORM-->>Tools: Appointment tracking
    Tools-->>Server: Return booking confirmation
    Server-->>Client: JSON Response (Success)
```

## Step-by-Step Code References

*   **FastMCP Server (EHREngine)**
    *   File Path: `mcp_server/server.py lines 12-43`
    *   Explanation: This is the core entry point of the FastMCP application. The server initializes here, logs with `logfire` through `_traced_async_tool`, and exposes four main interactive tools bound securely.

*   **Call list_medical_specialties() / Invoke _traced_async_tool(_specialties)**
    *   File Path: `mcp_server/tools/catalog.py lines 30-59`
    *   Explanation: The MCP Client searches for available medical specialties in the system. The Django ORM queries `MedicalDepartment` and calculates active doctor counts dynamically. 

*   **Call verify_insurance_eligibility(patient, payer) / Invoke _traced_async_tool(_verify)**
    *   File Path: `mcp_server/tools/insurance.py lines 6-76`
    *   Explanation: Validates whether the given patient has active policy terms covering the appointment. The ORM queries `PatientInsurance` enforcing that coverage is active (`enrollment_start` & `enrollment_end`), and returns if it's "HMO" or "PPO" to inform the Agent about referral needs.

*   **Call check_provider_availability(specialty, date) / Invoke _traced_async_tool(_check)**
    *   File Path: `mcp_server/tools/availability.py lines 5-78`
    *   Explanation: Looks for empty slots. The system queries `DoctorSchedule` ensuring `appointment__status` excludes `SCHEDULED` and `COMPLETED`. Retrieves open schedule records for formatting.

*   **Call schedule_appointment(...) / Invoke _traced_async_tool(_schedule)**
    *   File Path: `mcp_server/tools/scheduling.py lines 4-96`
    *   Explanation: Completes the transaction. The tool fetches the exact `DoctorSchedule` slot and, protecting against race conditions via DB `IntegrityError` constraints (`clinic.models.Appointment`), inserts the record.

*   **Django ORM / Models & PostgreSQL DB Interaction**
    *   File Path: `pyproject.toml lines 8-9` and `clinic/models/` definitions
    *   Explanation: Underlying connection management using `psycopg2-binary` binding Django's standard Object-Relational Mapper seamlessly into standard PostgreSQL. Data interactions throughout flow down to this layer automatically.