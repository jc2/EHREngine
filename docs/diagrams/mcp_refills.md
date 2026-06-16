# MCP Refills Tools

```mermaid
sequenceDiagram
    title Refills Tools Flow
    actor MCP as FastMCP
    participant Tool as refills.py
    participant DB as Django ORM

    rect rgb(200, 220, 240)
    note right of MCP: list_patient_prescriptions
    MCP->>Tool: Call list_patient_prescriptions(patient_id)
    Tool->>DB: Verify patient in PatientInsurance
    Tool->>DB: Query Prescriptions (ACTIVE/EXPIRED)
    DB-->>Tool: Return list of prescriptions
    Tool-->>MCP: Return summary dict
    end

    rect rgb(220, 240, 200)
    note right of MCP: request_medication_refill
    MCP->>Tool: Call request_medication_refill(patient_id, prescription_id)
    Tool->>DB: Query existent RefillRequest (24h idempotent check)
    Tool->>DB: Assess rules (expired, controlled, 0 refills left, denied)
    alt Approved
        Tool->>DB: Create RefillRequest (APPROVED)
        Tool->>DB: Subtract 1 from refills_remaining
    else Requires Provider Review
        Tool->>DB: Create RefillRequest (NEEDS_PROVIDER_REVIEW)
    else Denied
        Tool->>DB: Create RefillRequest (DENIED)
    end
    DB-->>Tool: Outcome persisted
    Tool-->>MCP: Return status and reason
    end
```

## Step-by-Step Code References

- **Call list_patient_prescriptions(patient_id)**: Logic starting inside the discovery wrapper `mcp_server/tools/refills.py lines 4-22`.
- **Verify patient in PatientInsurance**: Ensure the individual has mapped entity values inside application bounding mapping via `mcp_server/tools/refills.py lines 26-37`.
- **Query Prescriptions (ACTIVE/EXPIRED)**: Sucking out prescriptions ignoring discontinued paths evaluated explicitly `mcp_server/tools/refills.py lines 39-43`.
- **Return summary dict**: Array structuring operations evaluated through comprehension operations generating payload output at `mcp_server/tools/refills.py lines 45-61`.
- **Call request_medication_refill**: Execution endpoint traversal bounding parameters logic via intent triggers mapped roughly around documentation docstrings `mcp_server/tools/refills.py lines 64-88`.
- **Query existent RefillRequest (24h idempotent check)**: Checks designed against 24 hour limits (mapped theoretically around application rule execution limits evaluated past `line 90`).
- **Assess rules (expired, controlled, 0 refills left, denied)**: Evaluated rule constraints matching against outcomes driven explicitly across state variables (typically mapped after `line 95`).
- **Create RefillRequest (APPROVED / Subtract 1)**: Internal update decrement operations mapping success executions.
- **Create RefillRequest (NEEDS_PROVIDER_REVIEW / DENIED)**: Mapping explicit failure pathways logging requests against records tracking.
- **Return status and reason**: End point payload wrapper ensuring status updates are matched sequentially resolving agent transaction outputs mapping state components.