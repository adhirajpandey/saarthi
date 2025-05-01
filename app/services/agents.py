from agents import (
    Agent,
    ModelSettings,
    Runner,
    #    RunConfig,
    #    TResponseInputItem,
    set_tracing_disabled,
    #    ModelSettings,
    #    InputGuardrailTripwireTriggered,
    function_tool,
    set_default_openai_key,
)
from agents.extensions.handoff_prompt import (
    prompt_with_handoff_instructions,
)
import requests
import json
from ..config import CONFIG


ai_service_config = CONFIG.ai_service
set_tracing_disabled(True)
# enable_verbose_stdout_logging()

if ai_service_config.openai_api_key:
    set_default_openai_key(ai_service_config.openai_api_key)
else:
    raise ValueError("OpenAI API key is not set in the configuration.")


@function_tool
def plus(number_a: int, number_b: int) -> int:
    """
    Provides sum of two numbers.
    Args:
        number_a (int): The first number.
        number_b (int): The second number.
    Returns:
        int: The sum of the two numbers.

    """
    result = number_a + number_b
    if not result:
        return -1
    return result


@function_tool
def minus(number_a: int, number_b: int) -> int:
    """
    Provides difference of two numbers.
    Args:
         number_a (int): The first number.
         number_b (int): The second number.
    Returns:
         int: The difference of the two numbers.

    """
    result = number_a - number_b
    if not result:
        return -1
    return result


@function_tool
def get_search_results_from_google_drive(query: str) -> str:
    """
    Provides search results from Google Drive based on the query.
    Args:
        query (str): The search query.
    Returns:
        str: Google Drive API response with all the relevant details.

    """
    n8n_webhook_url = (
        f"{ai_service_config.google_drive_search_webhook_url}?query={query}"
    )

    response = requests.get(n8n_webhook_url)
    response.raise_for_status()  # Raise an error for bad responses
    data = response.json()
    if not data:
        return json.dumps({"error": "Unable to find any results."})
    return data


TRIAGE_AGENT_INSTRUCTIONS = """You are a triage agent. Your job is to determine the best course of action for the user query. 
You can either pass it to the information retrieval agent or task performer agent.
If any query regarding Google Drive, pass it to information retrieval agent.
If any query regarding task performance, pass it to task performer agent.
Dont answer to user until the whole task is completed.
"""

TASK_PERFORMER_AGENT_INSTRUCTIONS = """You are a task performer agent. Your job is to perform the task based on the user query.
You have access to tools and can use them to perform the task.
"""

INFORMATION_RETRIEVAL_AGENT_INSTRUCTIONS = """You are an information retrieval agent. Your job is to retrieve the information based on the user query.
You have access to tools and can use them to retrieve the information.
Dont answer to user until the whole task is completed.
Use google drive search tool to find drive files related information.
"""

information_extraction_from_user_query_agent = Agent(
    name="Information Extraction Agent",
    instructions="Extract the key information from user query.",
)

task_performer_agent = Agent(
    name="Task Performer Agent",
    instructions=TASK_PERFORMER_AGENT_INSTRUCTIONS,
    model_settings=ModelSettings(tool_choice="required"),
    tools=[plus, minus],
)

information_retrieval_agent = Agent(
    name="Information Retreival Agent",
    instructions=INFORMATION_RETRIEVAL_AGENT_INSTRUCTIONS,
    model_settings=ModelSettings(tool_choice="required"),
    tools=[
        #    information_extraction_from_user_query_agent.as_tool(
        #        tool_name="Information Extraction",
        #        tool_description="Generates a list of information from the user query.",
        #    ),
        get_search_results_from_google_drive,
    ],
)

triage_agent = Agent(
    name="Triage agent",
    instructions=prompt_with_handoff_instructions(TRIAGE_AGENT_INSTRUCTIONS),
    handoffs=[information_retrieval_agent, task_performer_agent],
)


class AgentsService:
    def __init__(self, agent_config):
        self.config = agent_config

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
