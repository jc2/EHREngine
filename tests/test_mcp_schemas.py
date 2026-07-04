"""Verify MCP tools expose structured outputSchema metadata."""

from mcp_server.server import mcp


def _tool_output_schema(tool_name: str) -> dict | None:
    tool = mcp._tool_manager._tools[tool_name]
    return tool.output_schema


def test_identify_patient_output_schema_has_fields():
    schema = _tool_output_schema("identify_patient")
    assert schema is not None
    assert schema["title"] == "IdentifyPatientResult"
    assert "success" in schema["properties"]
    assert schema["properties"]["success"]["type"] == "boolean"
    assert "patient_code" in schema["properties"]
    assert "pending_appointments" in schema["properties"]
    assert "pending_refill_requests" in schema["properties"]
    assert "pending_escalations" in schema["properties"]
    assert "insurance_policies" in schema["properties"]


def test_list_insurance_payers_output_schema_has_nested_items():
    schema = _tool_output_schema("list_insurance_payers")
    assert schema is not None
    assert schema["title"] == "ListInsurancePayersResult"
    payers = schema["properties"]["payers"]
    assert payers["type"] == "array"
    payer_item = schema["$defs"]["PayerSummary"]
    assert "code" in payer_item["properties"]


def test_check_refill_status_output_schema_has_fields():
    schema = _tool_output_schema("check_refill_status")
    assert schema is not None
    assert schema["title"] == "CheckRefillStatusResult"
    assert "is_authorized" in schema["properties"]
    assert "authorization_status" in schema["properties"]
