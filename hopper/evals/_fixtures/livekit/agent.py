from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext, function_tool
from livekit.plugins import deepgram, cartesia, openai, silero

INSTRUCTIONS = """You are Sam, the booking assistant for Northside Auto Repair. Keep replies to one or two short sentences; you're on a phone call.
Find out what's wrong with the caller's car, use lookup_slots to find openings and book_service once they pick one. The shop is open 7am to 6pm on weekdays and 8am to noon on Saturdays. Don't quote prices; say a technician will confirm after inspection."""


class Receptionist(Agent):
    def __init__(self):
        super().__init__(instructions=INSTRUCTIONS)

    @function_tool
    async def lookup_slots(self, context: RunContext, day: str) -> list[str]:
        """Find open service slots on a day (YYYY-MM-DD)."""
        return ["09:00", "13:30"]

    @function_tool
    async def book_service(self, context: RunContext, day: str, time: str, name: str) -> str:
        """Book a service slot for the caller."""
        return "booked"


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4.1"),
        tts=cartesia.TTS(),
        vad=silero.VAD.load(),
    )
    await session.start(Receptionist(), room=ctx.room)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
