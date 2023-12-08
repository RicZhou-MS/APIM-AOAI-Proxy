import json
import azure.functions as func
import logging
import os
import tiktoken
import pyodbc
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel

app = func.FunctionApp()


class ApimAoaiToken:
    def __init__(self,
                 ExecTimeUTC="1970-01-01 00:00:00",
                 ExecDateUTC="1970-01-01",
                 GatewayRegion="",
                 GatewayServiceName="",
                 SubscriptionId="",
                 SubscriptionName="",
                 UserName="",
                 UserEmail="",
                 ProductName="",
                 ApiName="",
                 OperationId="",
                 ModelName="",
                 IsStreaming=0,
                 PromptTokens=0,
                 CompletionTokens=0,
                 TotalTokens=0
                 ):
        self.ExecTimeUTC = ExecTimeUTC
        self.ExecDateUTC = ExecDateUTC
        self.GatewayRegion = GatewayRegion
        self.GatewayServiceName = GatewayServiceName
        self.SubscriptionId = SubscriptionId
        self.SubscriptionName = SubscriptionName
        self.UserName = UserName
        self.UserEmail = UserEmail
        self.ProductName = ProductName
        self.ApiName = ApiName
        self.OperationId = OperationId
        self.ModelName = ModelName
        self.IsStreaming = IsStreaming
        self.PromptTokens = PromptTokens
        self.CompletionTokens = CompletionTokens
        self.TotalTokens = TotalTokens

# Function entry point for handling Azure Event Hub messages


@app.event_hub_message_trigger(arg_name="azevents", event_hub_name="<event hub instance name>",
                               connection="AOAI_APIM_EVENTHUB_CONNECTION", consumer_group="apim_aoai_eventhub_consumer_group", cardinality="many", data_type="string")
def apim_aoai_eventhub_trigger(azevents):
    for event in azevents:
        event_content = event.get_body().decode('utf-8')

        if is_json(event_content):
            json_data = json.loads(event_content)

            if (json_data.get("OperationId") and json_data.get("OperationId").lower() == "chatcompletions_create"):
                proceed_chat_completion_call(json_data)
            elif (json_data.get("OperationId") and json_data.get("OperationId").lower() == "completions_create"):
                proceed_completion_call(json_data)
            elif (json_data.get("OperationId") and json_data.get("OperationId").lower() == "embeddings_create"):
                proceed_embedding_call(json_data)
            else:
                logging.info("AOAI-No available OperationId found!")
            # need to use json.dumps to convert json to attributes with double quote string,
            # but there is limitation that the logging in azure function will convert it back to single quote string which will cause error in json parse in Azure log analytics
            logging.info(json.dumps(json_data))
        else:
            logging.info("AOAI-No json found!")
            logging.info(event_content)

    logging.info(
        f"AOAI-Total events received in one time function call: {len(azevents)}")


def proceed_chat_completion_call(json_data):
    logging.info("AOAI-proceed_chat_completion_call")
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    aoai_token = compose_aoai_token(json_data)
    model_name = json_data.get('Request', {}).get('model', 'Unknown')

    is_streaming = json_data.get('Request', {}).get('stream', False)

    if is_streaming:  # proceed if streaming
        aoai_token.IsStreaming = 1
        # concatenate prompt content
        concatenated_request_content = ' '.join(
            message['content'] for message in json_data['Request']['messages'])
        prompt_tokens = chat_num_tokens_from_string(
            concatenated_request_content)

        response_string = json_data.get('ResponseString', None)
        # ResponseString is not empty or null (which means APIM captured streaming response)
        if response_string:
            completion_tokens = chat_num_tokens_from_string(response_string)
        # ResponseString is empty or null (which means APIM didn't capture streaming response)
        else:
            completion_tokens = 0
        total_tokens = prompt_tokens + completion_tokens

        # logging.info(f"AOAI-{concatenated_request_content}")
        # logging.info(f"AOAI-{response_string}")

    else:  # if not streaming
        aoai_token.IsStreaming = 0
        json_response = json.loads(json_data.get('ResponseString', '{}'))
        prompt_tokens = json_response.get('usage', {}).get('prompt_tokens', 0)
        completion_tokens = json_response.get(
            'usage', {}).get('completion_tokens', 0)
        total_tokens = json_response.get('usage', {}).get('total_tokens', 0)

    logging.info(f"AOAI-model name: {model_name}")
    logging.info(f"AOAI-prompt token: {prompt_tokens}")
    logging.info(f"AOAI-completion token: {completion_tokens}")
    logging.info(f"AOAI-total token: {total_tokens}")

    aoai_token.ModelName = model_name
    aoai_token.PromptTokens = prompt_tokens
    aoai_token.CompletionTokens = completion_tokens
    aoai_token.TotalTokens = total_tokens
    insert_aoai_token(aoai_token)


def proceed_completion_call(json_data):
    logging.info("AOAI-proceed_chat_completion_call")
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    aoai_token = compose_aoai_token(json_data)
    model_name = json_data.get('Request', {}).get('model', 'Unknown')

    is_streaming = json_data.get('Request', {}).get('stream', False)

    if is_streaming:  # proceed if streaming
        aoai_token.IsStreaming = 1
        # get prompt content
        prompt_content = json_data.get('Request', {}).get('prompt', ' ')
        prompt_tokens = davinci_num_tokens_from_string(prompt_content)

        response_string = json_data.get('ResponseString', None)
        # ResponseString is not empty and not null (which means APIM captured streaming response)
        if response_string:
            completion_tokens = davinci_num_tokens_from_string(response_string)
        # ResponseString is empty or null (which means APIM didn't capture streaming response)
        else:
            completion_tokens = 0
        total_tokens = prompt_tokens + completion_tokens

        # logging.info(f"AOAI-{concatenated_request_content}")
        # logging.info(f"AOAI-{response_string}")

    else:  # if not streaming,
        aoai_token.IsStreaming = 0
        json_response = json.loads(json_data.get('ResponseString', '{}'))
        prompt_tokens = json_response.get('usage', {}).get('prompt_tokens', 0)
        completion_tokens = json_response.get(
            'usage', {}).get('completion_tokens', 0)
        total_tokens = json_response.get('usage', {}).get('total_tokens', 0)

    logging.info(f"AOAI-model name: {model_name}")
    logging.info(f"AOAI-prompt token: {prompt_tokens}")
    logging.info(f"AOAI-completion token: {completion_tokens}")
    logging.info(f"AOAI-total token: {total_tokens}")

    aoai_token.ModelName = model_name
    aoai_token.PromptTokens = prompt_tokens
    aoai_token.CompletionTokens = completion_tokens
    aoai_token.TotalTokens = total_tokens
    insert_aoai_token(aoai_token)


def proceed_embedding_call(json_data):
    logging.info("AOAI-proceed_embedding_call")
    json_response = json.loads(json_data.get('ResponseString', '{}'))
    model_name = json_data.get('Request', {}).get('model', 'Unknown')
    prompt_tokens = json_response.get('usage', {}).get('prompt_tokens', 0)
    total_tokens = json_response.get('usage', {}).get('total_tokens', 0)

    logging.info(f"AOAI-model name: {model_name}")
    logging.info(f"AOAI-prompt token: {prompt_tokens}")
    logging.info(f"AOAI-total token: {total_tokens}")

    aoai_token = compose_aoai_token(json_data)
    aoai_token.ModelName = model_name
    aoai_token.IsStreaming = 0
    aoai_token.PromptTokens = prompt_tokens
    aoai_token.CompletionTokens = 0  # no completion token for embedding
    aoai_token.TotalTokens = total_tokens
    insert_aoai_token(aoai_token)


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    # cl100k_base -->	gpt-4, gpt-3.5-turbo, text-embedding-ada-002
    # p50k_base --> Codex models, text-davinci-002, text-davinci-003
    # r50k_base (or gpt2) -->	GPT-3 models like davinci
    # encoding_for_model('gpt-3.5-turbo')
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def chat_num_tokens_from_string(string: str) -> int:
    return num_tokens_from_string(string, "cl100k_base")


def davinci_num_tokens_from_string(string: str) -> int:
    return num_tokens_from_string(string, "p50k_base")


def embedding_num_tokens_from_string(string: str) -> int:
    return num_tokens_from_string(string, "cl100k_base")


def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError as e:
        return False
    return True


def get_conn():
    # get from function app settings
    connection_string = os.environ["AOAI_DB_STORE_CONNECTION"]
    # print(connection_string)
    conn = pyodbc.connect(connection_string)
    return conn


def insert_aoai_token(aoai_token: ApimAoaiToken):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""INSERT INTO [dbo].[ApimAoaiToken]
            ([ExecTimeUTC], [ExecDateUTC], [GatewayRegion], [GatewayServiceName],
                [SubscriptionId], [SubscriptionName], [UserName], [UserEmail], [ProductName],
                [ApiName], [OperationId], [ModelName], [IsStreaming], [PromptTokens], [CompletionTokens], [TotalTokens])
        VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (
                           aoai_token.ExecTimeUTC,
                           aoai_token.ExecDateUTC,
                           aoai_token.GatewayRegion,
                           aoai_token.GatewayServiceName,
                           aoai_token.SubscriptionId,
                           aoai_token.SubscriptionName,
                           aoai_token.UserName,
                           aoai_token.UserEmail,
                           aoai_token.ProductName,
                           aoai_token.ApiName,
                           aoai_token.OperationId,
                           aoai_token.ModelName,
                           aoai_token.IsStreaming,
                           aoai_token.PromptTokens,
                           aoai_token.CompletionTokens,
                           aoai_token.TotalTokens
                       )
                       )
        conn.commit()


def compose_aoai_token(json_data):
    aoai_token = ApimAoaiToken()
    aoai_token.ExecTimeUTC = json_data.get(
        'ExecTimeUTC', '1970-01-01 00:00:00')
    # get the date part of "yyyy-MM-dd HH:mm:ss"
    aoai_token.ExecDateUTC = aoai_token.ExecTimeUTC[0:10]
    aoai_token.GatewayRegion = json_data.get('GatewayRegion', '')
    aoai_token.GatewayServiceName = json_data.get('GatewayServiceName', '')
    aoai_token.SubscriptionId = json_data.get('SubscriptionId', '')
    aoai_token.SubscriptionName = json_data.get('SubscriptionName', '')
    aoai_token.UserName = json_data.get('UserName', '')
    aoai_token.UserEmail = json_data.get('UserEmail', '')
    aoai_token.ProductName = json_data.get('ProductName', '')
    aoai_token.ApiName = json_data.get('ApiName', '')
    aoai_token.OperationId = json_data.get('OperationId', '')
    # aoai_token.ModelName = json_data.get('ModelName', '')
    # aoai_token.PromptTokens = json_data.get('PromptTokens', 0)
    # aoai_token.CompletionTokens = json_data.get('CompletionTokens', 0)
    # aoai_token.TotalTokens = json_data.get('TotalTokens', 0)
    return aoai_token
