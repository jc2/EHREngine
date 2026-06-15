import functools

from asgiref.sync import sync_to_async
from mcp.server.fastmcp import FastMCP

from .tools.catalog import list_insurance_payers as _payers, list_medical_specialties as _specialties
from .tools.insurance import verify_insurance_eligibility as _verify
from .tools.availability import check_provider_availability as _check
from .tools.scheduling import schedule_appointment as _schedule

mcp = FastMCP(
    "EHREngine",
    instructions=(
        "EHR/PMS system for managing patient appointments. "
        "Typical workflow: "
        "1) list_insurance_payers / list_medical_specialties — discover available options. "
        "2) verify_insurance_eligibility — check patient has active coverage. "
        "3) check_provider_availability — find open slots for a specialty. "
        "4) schedule_appointment — book the slot. "
        "HMO patients need a referral from their PCP before seeing a specialist. "
        "PPO patients can see specialists directly."
    ),
)


def _async_tool(fn):
    async_fn = sync_to_async(fn)
    functools.update_wrapper(async_fn, fn)
    return async_fn


mcp.tool()(_async_tool(_payers))
mcp.tool()(_async_tool(_specialties))
mcp.tool()(_async_tool(_verify))
mcp.tool()(_async_tool(_check))
mcp.tool()(_async_tool(_schedule))
