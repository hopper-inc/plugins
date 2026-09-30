import os

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService

from tools import TOOLS, check_availability, book_appointment

SYSTEM_PROMPT = open(os.path.join(os.path.dirname(__file__), "prompt.txt")).read()


def build_llm():
    llm = OpenAILLMService(
        api_key=os.environ["OPENAI_API_KEY"],
        settings=OpenAILLMService.Settings(model="gpt-4.1", system_instruction=SYSTEM_PROMPT),
    )
    llm.register_function("check_availability", check_availability)
    llm.register_function("book_appointment", book_appointment)
    return llm


async def run_bot(transport):
    stt = DeepgramSTTService(api_key=os.environ["DEEPGRAM_API_KEY"])
    tts = CartesiaTTSService(api_key=os.environ["CARTESIA_API_KEY"], voice_id="a0e99841-438c-4a64-b679-ae501e7d6091")
    llm = build_llm()
    context = LLMContext(tools=TOOLS)
    aggregators = LLMContextAggregatorPair(context)
    pipeline = Pipeline([
        transport.input(),
        stt,
        aggregators.user(),
        llm,
        tts,
        transport.output(),
        aggregators.assistant(),
    ])
    task = PipelineTask(pipeline, params=PipelineParams(enable_metrics=True))
    return task
