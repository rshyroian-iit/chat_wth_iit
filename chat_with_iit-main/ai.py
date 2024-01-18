import openai
import numpy as np
import tiktoken
import os
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
# Use environment variable to set API key
openai.api_key = "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"

def turbo_boogle(messages=[], max_tokens=1000, temperature=0.7, model="gpt-3.5-turbo", stream=False):
    response = openai.ChatCompletion.create(
        model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, stream=stream)
    if stream:
        return response
    response_str = ""
    for i in range(len(response['choices'])):
        response_str += response['choices'][i]['message']['content']
    return response_str

def get_embedding_openai(text, model="text-embedding-ada-002"):
    text = text.replace("\n", " ")
    if text == "":
        text = "None"
    try:
        return openai.Embedding.create(input=[text], model=model)['data'][0]['embedding']
    except Exception as e:
        print(f'Error getting embedding for {text}: {e}')
        return None

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_default_embedding():
    # check if default embedding exists
    default_embedding = np.load('utils/default_embedding.npy')
    return default_embedding

def embedding_function(text, num_retries=0):
    embedding = None
    if text == '':
        return get_default_embedding()
    try:
        embedding = get_embedding_openai(text)
    except Exception as e:
        print(f'Error in embedding_function')
        embedding = None
    if embedding is None:
        if num_retries < 3:
            embedding = embedding_function(text, num_retries + 1)
        else:
            print(f'Error in embedding_function: embedding is None. Returning default embedding.')
            embedding = get_default_embedding()
    return embedding

def get_token_count(text):
    try:
        token_count = len(enc.encode(text))
        return token_count
    except Exception as e:
        print(f'Error counting tokens for {text}: {e}')
        return None

def split_content(text, length=800, append_content=""):
    content_tokens = enc.encode(text.replace('<|endoftext|>', ''))
    if len(content_tokens) > length:
        reminder = len(content_tokens) % length
        division_result = len(content_tokens) // length
        length = length + reminder // division_result + 1
    content_chunks = [content_tokens[i:i+length] for i in range(0, len(content_tokens), length)]
    content = [enc.decode(chunk) for chunk in content_chunks]
    if append_content != "":
        content = [(content[i] + append_content) for i in range(len(content))]
    return content

if __name__ == "__main__":
    text = """Hello, I am a human.
    I am a human.
    """
    embedding = embedding_function(text)
