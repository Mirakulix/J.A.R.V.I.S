import os
import autogen
import autogen
from autogen import AssistantAgent, UserProxyAgent
# # Load LLM inference endpoints from an env variable or a file
# # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
# # and OAI_CONFIG_LIST_sample
# config_list = config_list(env_or_file="OAI_CONFIG_LIST")
# # You can also set config_list directly as a list, for example, config_list = [{'model': 'gpt-4', 'api_key': '<your OpenAI API key here>'},]
# assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
# user_proxy = UserProxyAgent("user_proxy", code_execution_config={"work_dir": "coding"})
# user_proxy.initiate_chat(assistant, message="Plot a chart of NVDA and TESLA stock price change YTD.")
# # This initiates an automated chat between the two agents to solve the task

config_list = [
    {
        'model': 'gpt-4-1106-preview',
        'api_key': os.getenv('OPENAI_API_KEY'),
    },
    {
        'model': 'gpt-4-vision-preview',
        'api_key': os.getenv('OPENAI_API_KEY'),
    },
    {
        'model': 'gpt-3.5-turbo-1106',
        'api_key': os.getenv('OPENAI_API_KEY'),
    },
    {
        'model': 'gpt-4-32k',
        'api_key': os.getenv('OPENAI_API_KEY'),
    },
    {
        'model': 'gpt-3.5-turbo-16k',
        'api_key': os.getenv('OPENAI_API_KEY'),
    }
]

config_list = autogen.config_list(
    dotenv_file_path='.env',
    filter_dict={
        "model": ["gpt-4-1106-preview", "gpt-4-vision-preview", "gpt-3.5-turbo-1106", "gpt-4-32k", "gpt-3.5-turbo-16k"],
    },
)

config_list_gpt4 = autogen.config_list(
    dotenv_file_path='.env',
    filter_dict={
        "model": ["gpt-4-1106-preview"],
    },
)
# config_list_gpt4 = autogen.config_list(
#     "OAI_CONFIG_LIST",
#     filter_dict={
#         "model": ["gpt-4-1106-preview", "gpt-4-vision-preview", "gpt-4-32k", "gpt-4-32k-0314"],
#     },
# )


'''
Construct AI Agents
'''


gpt4_config = {
    "cache_seed": 44,  # change the cache_seed for different trials
    "temperature": 0.4,
    "config_list": config_list_gpt4,
    "timeout": 120,
}
user_proxy = autogen.UserProxyAgent(
   name="Admin",
   system_message="A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin.",
   code_execution_config=False,
)
engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=gpt4_config,
    system_message='''Engineer. You follow an approved plan. You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor. Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor. If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try. ''',
)
developer = autogen.AssistantAgent(
    name="Developer",
    llm_config=gpt4_config,
    system_message='''Developer and DevOps Specialist. You are to adhere strictly to an approved plan. Your task involves writing Python and Shell scripts to address specific tasks. Ensure that your code is enclosed within a code block, clearly specifying the type of script. It is imperative to remember that users are not permitted to modify your code. Therefore, avoid submitting incomplete code that necessitates alterations by others. Use code blocks exclusively for code that is meant to be executed by the executor. Refrain from including multiple code blocks in a single response. Additionally, do not instruct others to copy and paste results. After execution, thoroughly review the results returned by the executor. In the event of an error, it is your responsibility to rectify the issue and provide the corrected code in its entirety. Offer complete solutions rather than fragments or mere modifications. If you encounter irreparable errors, or if the problem persists despite successful code execution, you must reassess your assumptions. Gather any additional information required and contemplate alternative strategies for resolution.'''

)
scientist = autogen.AssistantAgent(
    name="Scientist",
    llm_config=gpt4_config,
    system_message="""Scientist. You follow an approved plan. You are able to categorize papers after seeing their abstracts printed. You don't write code."""
)
planner = autogen.AssistantAgent(
    name="Planner",
    system_message='''Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval. The plan may involve an engineer who can write code and a scientist who doesn't write code. Explain the plan first. Be clear which step is performed by an engineer, a developer & DevOps experience and which step is performed by a scientist.''',
    llm_config=gpt4_config,
)
executor = autogen.UserProxyAgent(
    name="Executor",
    system_message="Executor. Execute the code written by the engineer and report the result.",
    human_input_mode="NEVER",
    code_execution_config={"last_n_messages": 3, "work_dir": "paper"},
)
critic = autogen.AssistantAgent(
    name="Critic",
    system_message="Constructive Critic with a solution as goal. Double check plan, claims, code from other agents and provide feedback. Check whether the plan includes adding verifiable info such as source URL.",
    llm_config=gpt4_config,
)
groupchat = autogen.GroupChat(agents=[user_proxy, engineer, developer, scientist, planner, executor, critic], messages=[], max_round=50)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

user_proxy.initiate_chat(
    manager,
    message="""Develope and Create a J.A.R.V.I.S. AI Tool witten in Python with all relevant openAI API requests with gpt-4, especially for text-to-speech, speech-to-text, voice-recognition, vision, function caller and code interpreter. Design the project to run efficiently and fully functional.  For further examples please consider https://cookbook.openai.com or the whole openAI/cookbook or openAI/baselines repo located in "openAI-packages/openai-cookbook" (relativ link is starting form location of this script) providing good examples for openAI API usecases and code examples. Wenn möglich sollen alle python funktionen in dem Skript 'jarvis_autogen_v0.py' enthalten sein. Sollten doch bereits andere Dateien außerhalb des Python skripts jarvis_autogen_v0.py notwendig sein, soll ein eigener ordner mit jarvis_autogen_v0 erstellt und in diesem Ordner eine saubere und ordentliche Applicationstruktur mit Python als Hauptsprache mit den relevantesten, oben genannten openAI API Funktionen entwickelt werden. In der finalen Form, die noch viele Schritte entfernt liegt, soll das J.A.R.V.I.S. AI Tool mit einer breiten Kompatibilität (Smartphone App, PC, Mac, WebApp usw.), charmant, hoch gebildet und vor allem hilfreich und entlastend für seine menschlichen Partner sein."""
)