from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

TOOLS = ToolsSchema(standard_tools=[
    FunctionSchema(
        name="check_availability",
        description="Check open appointment slots for a date.",
        properties={"date": {"type": "string", "description": "YYYY-MM-DD"}},
        required=["date"],
    ),
    FunctionSchema(
        name="book_appointment",
        description="Book a slot for the caller.",
        properties={"date": {"type": "string"}, "time": {"type": "string"}, "name": {"type": "string"}},
        required=["date", "time", "name"],
    ),
])


async def check_availability(params):
    await params.result_callback({"slots": ["14:00", "15:30"]})


async def book_appointment(params):
    await params.result_callback({"confirmed": True})
