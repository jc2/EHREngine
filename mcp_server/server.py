import functools

import logfire
from asgiref.sync import sync_to_async
from mcp.server.fastmcp import FastMCP

from .tools.catalog import list_insurance_payers as _payers, list_medical_specialties as _specialties
from .tools.insurance import verify_insurance_eligibility as _verify
from .tools.availability import check_provider_availability as _check
from .tools.scheduling import schedule_appointment as _schedule
from .tools.refills import list_patient_prescriptions as _list_rx, request_medication_refill as _refill
from .tools.billing import estimate_visit_cost as _estimate_cost

mcp = FastMCP(
    "EHREngine",
    instructions=(
        "EHR/PMS system for managing patient appointments and medication refills. "
        "Typical workflow: "
        "1) list_insurance_payers / list_medical_specialties — discover available options. "
        "2) verify_insurance_eligibility — check patient has active coverage. "
        "3) check_provider_availability — find open slots for a specialty. "
        "4) schedule_appointment — book the slot. "
        "HMO patients need a referral from their PCP before seeing a specialist. "
        "PPO patients can see specialists directly. "
        "For medication refills: "
        "1) list_patient_prescriptions — find the prescription_id for the patient. "
        "2) request_medication_refill — process the refill request. "
        "Controlled substances, expired prescriptions, and prescriptions with no "
        "refills remaining require provider review (NEEDS_PROVIDER_REVIEW)."
    ),
)


def _traced_async_tool(fn):
    @logfire.instrument("mcp.tool.{fn_name}", extract_args=True)
    def traced(*args, **kwargs):
        return fn(*args, **kwargs)

    traced.__name__ = fn.__name__
    traced.__qualname__ = fn.__qualname__
    traced.__doc__ = fn.__doc__
    traced.__annotations__ = fn.__annotations__
    traced.__module__ = fn.__module__

    async_fn = sync_to_async(traced)
    functools.update_wrapper(async_fn, fn)
    return async_fn


mcp.tool()(_traced_async_tool(_payers))
mcp.tool()(_traced_async_tool(_specialties))
mcp.tool()(_traced_async_tool(_verify))
mcp.tool()(_traced_async_tool(_check))
mcp.tool()(_traced_async_tool(_schedule))
mcp.tool()(_traced_async_tool(_list_rx))
mcp.tool()(_traced_async_tool(_refill))
mcp.tool()(_traced_async_tool(_estimate_cost))
