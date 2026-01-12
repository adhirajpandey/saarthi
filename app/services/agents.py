from agents import (
    Agent,
    ModelSettings,
    Runner,
    RunConfig,
    #    TResponseInputItem,
    set_tracing_disabled,
    enable_verbose_stdout_logging,
    #    ModelSettings,
    #    InputGuardrailTripwireTriggered,
    set_default_openai_key,
    OpenAIChatCompletionsModel,
)
from agents.extensions.handoff_prompt import (
    prompt_with_handoff_instructions,
)
from openai import AsyncOpenAI
from ..config import CONFIG
from ..utils.logging import logger
from .instructions import (
    TRIAGE_AGENT_INSTRUCTIONS,
    TASK_PERFORMER_AGENT_INSTRUCTIONS,
    INFORMATION_RETRIEVAL_AGENT_INSTRUCTIONS,
)
from .tools import (
    get_search_results_from_google_drive,
)

ai_service_config = CONFIG.ai_service
set_tracing_disabled(True)
enable_verbose_stdout_logging()

if ai_service_config.openai_api_key:
    set_default_openai_key(ai_service_config.openai_api_key)
else:
    logger.warning("OpenAI API key is not set in the configuration.")


information_extraction_from_user_query_agent = Agent(
    name="Information Extraction Agent",
    instructions="Extract the key information from user query.",
)

task_performer_agent = Agent(
    name="Task Performer Agent",
    instructions=TASK_PERFORMER_AGENT_INSTRUCTIONS,
    model_settings=ModelSettings(tool_choice="required"),
)

information_retrieval_agent = Agent(
    name="Information Retreival Agent",
    instructions=INFORMATION_RETRIEVAL_AGENT_INSTRUCTIONS,
    model_settings=ModelSettings(tool_choice="required", temperature=0.2),
    tools=[
        get_search_results_from_google_drive,
    ],
)

triage_agent = Agent(
    name="Triage agent",
    instructions=prompt_with_handoff_instructions(TRIAGE_AGENT_INSTRUCTIONS),
    handoffs=[information_retrieval_agent, task_performer_agent],
)


class AgentsService:
    def __init__(self):
        # TODO: only pass available models after healthc check
        # self.config = agent_config
        self.preferred_model: str | OpenAIChatCompletionsModel = None
        self.set_preffered_model()
        self.config = RunConfig(
            model=self.preferred_model,
            tracing_disabled=True,
        )

    def set_preffered_model(self):
        sorted_models = sorted(ai_service_config.models, key=lambda x: x.priority)
        if sorted_models:
            top_model = sorted_models[0]
            if top_model.provider == "openai":
                logger.info(top_model)
                self.preferred_model = top_model.name
            elif top_model.provider == "ollama":
                client = AsyncOpenAI(
                    base_url=ai_service_config.providers.ollama.base_url,
                    api_key=ai_service_config.providers.ollama.api_key,
                )
                self.preferred_model = OpenAIChatCompletionsModel(
                    model=top_model.name, openai_client=client
                )
            elif top_model.provider == "gemini":
                client = AsyncOpenAI(
                    base_url=ai_service_config.providers.gemini.base_url,
                    api_key=ai_service_config.providers.gemini.api_key,
                )
                self.preferred_model = OpenAIChatCompletionsModel(
                    model=top_model.name, openai_client=client
                )
            elif top_model.provider == "openrouter":
                client = AsyncOpenAI(
                    base_url=ai_service_config.providers.openrouter.base_url,
                    api_key=ai_service_config.providers.openrouter.api_key,
                )
                self.preferred_model = OpenAIChatCompletionsModel(
                    model=top_model.name, openai_client=client
                )
            else:
                raise ValueError(f"Unsupported provider: {top_model.provider}")
        else:
            raise ValueError("No available models found in the configuration.")

    def get_preffered_model_name(self) -> str:
        """
        Get the name of the preferred model.
        Returns:
            str: The name of the preferred model.
        """
        if isinstance(self.preferred_model, str):
            return self.preferred_model
        elif isinstance(self.preferred_model, OpenAIChatCompletionsModel):
            return self.preferred_model.model
        else:
            raise ValueError("Preferred model is not set or is of an unexpected type.")

    async def invoke(self, user_input):
        """
        Invoke the agent with the user input and return the response.
        Args:
            user_input (str): The user input to be processed by the agent.
        Returns:
            str: The response from the agent.
        """
        # Here you would implement the logic to invoke the agent with the user input
        # For example, you might call a method on the agent instance and return its output
        result = await Runner.run(triage_agent, user_input, run_config=self.config)
        return result.final_output
