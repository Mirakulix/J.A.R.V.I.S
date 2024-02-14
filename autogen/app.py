# import autogen
from autogen import OpenAIWrapper

config_list = [
    {
        'model': 'gpt-3.5-turbo-1106',
        'api_key': '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'
    }
]

client = OpenAIWrapper(config_list=config_list)
response = client.create(messages=[{"role": "user", "content": "2+2="}])
print(client.extract_text_or_function_call(response))
# from autogen import AssistantAgent, UserProxyAgent, config_list_from_json



llm_config = {
    "request_timeout": 600,
    "seed": 42,
    "config": config_list,
    "temperature": 0
}

codemonkey = client.AssistantAgent(
    name='codemonkey',
    llm_config=llm_config,
    system_message="Generate python code"
)

developer = client.AssistantAgent(
    name='developer',
    llm_config=llm_config,
    system_message="Test provided code, make sure it is working and critically review if the results are useful in order to complete the task."
)

architect = client.AssistantAgent(
    name='architect',
    llm_config=llm_config,
    system_message="Design a useful and efficient architecture"
)

researcher = client.AssistantAgent(
    name="researcher",
    llm_config=llm_config,
    system_message="Research other projects or provide detailed information that could be useful for improvements."
)

user_proxy = client.UserProxyAgent(
    name="user_proxy",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"work_dir": "web"},
    llm_config=llm_config,
    system_message=""""Reply TERMINATE if the task has been solved at full satisfaction.
Otherwise, reply CONTINUE, or the reason why the task is not solved yet."""
)

task = """
Erstelle ein python projekt, das den täglichen bitcoin zu euro kurs der letzten 3 Jahre inklusive des aktuellen kurses ermittelt und daraus ein chart als bild erstellt.
"""

user_proxy.initiate_chat(
    codemonkey,
    developer,
    architect,
    researcher,
    message=task,
)