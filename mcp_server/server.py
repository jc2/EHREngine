import functools
import os

from asgiref.sync import sync_to_async
from mcp.server.fastmcp import FastMCP

from .roles import ALL_TOOLS, PUBLIC_TOOLS

_INSTRUCTIONS = (
    "EHR/PMS system for managing patient appointments and medication refills. "
    "Typical workflow: "
    "1) identify_patient — resolve patient code from name, phone, and ID. "
    "2) list_insurance_payers / list_medical_specialties — discover available options. "
    "3) verify_insurance_eligibility — check patient has active coverage. "
    "4) check_provider_availability — find open slots for a specialty. "
    "5) schedule_appointment — book the slot (notes required: reasons for visit). "
    "HMO patients need a referral from their PCP before seeing a specialist. "
    "PPO patients can see specialists directly. "
    "For medication refills: "
    "1) list_patient_prescriptions — find the prescription_id for the patient. "
    "2) request_medication_refill — process the refill request. "
    "3) check_refill_status — verify authorization status using the refill reference code. "
    "Controlled substances, expired prescriptions, and prescriptions with no "
    "refills remaining require provider review (NEEDS_PROVIDER_REVIEW). "
    "For human escalations: "
    "1) report_human_escalation — record a case when the agent cannot complete "
    "a request (include demographics, intent, and failure reason). "
    "2) check_pending_escalation — check if the patient already has an open (NEW) case "
    "by patient_id before retrying or creating a duplicate escalation."
)


def _traced_async_tool(fn):
    if os.environ.get("LOGFIRE_TOKEN"):
        import logfire

        # Bind the original BEFORE rebinding `fn`: `traced` closes over the
        # variable, so `return fn(...)` after `fn = traced` recurses forever.
        original = fn

        @logfire.instrument(f"mcp.tool.{original.__name__}", extract_args=True)
        def traced(*args, **kwargs):
            return original(*args, **kwargs)

        # update_wrapper (not manual attribute copies) also sets __wrapped__,
        # which inspect.signature follows — without it FastMCP publishes the
        # wrapper's (*args, **kwargs) as every tool's input schema.
        functools.update_wrapper(traced, original)
        fn = traced

    async_fn = sync_to_async(fn)
    functools.update_wrapper(async_fn, fn)
    return async_fn


def build_mcp(name, tools):
    instance = FastMCP(name, instructions=_INSTRUCTIONS)
    for fn in tools:
        instance.tool()(_traced_async_tool(fn))
    return instance


public_mcp = build_mcp("EHREngine-Public", PUBLIC_TOOLS)
all_mcp = build_mcp("EHREngine-All", ALL_TOOLS)
