import tiktoken

def num_tokens_from_messages(messages, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message object
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
    num_tokens += 2  # priming tokens
    return num_tokens
