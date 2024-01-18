import requests
import json
from ai import embedding_function, cosine_similarity, get_token_count
import os
import streamlit as st
import datetime
import psycopg2

# Define your OpenAI API key
today = datetime.date.today()
today = today.strftime("%Y-%m-%d")

#write a function to get the current school semester based on the current date, i.e. Fall 2023, Spring 2024, etc.
season = ''
if today[5:7] == '01' or today[5:7] == '02' or today[5:7] == '03' or today[5:7] == '04' or today[5:7] == '05':
    season = 'Spring'
elif today[5:7] == '06' or today[5:7] == '07' or today[5:7] == '08' or today[5:7] == '09' or today[5:7] == '10':
    season = 'Fall'
else:
    season = 'Summer'
st.set_page_config(page_title="Chat with Illinois Tech", page_icon="https://banner2.cleanpng.com/20180406/pjw/kisspng-illinois-institute-of-technology-chicago-kent-coll-hawk-5ac81d22f1c219.7625313915230640989903.jpg")

#write a function to get the current school year based on the current date, i.e. 2023, 2024, etc.
year = today[:4]
SYSTEM_MESSAGE_WITH_FUNCTION = """Your primary role as an advanced AI model is to serve as a personalized assistant for students at Illinois Institute of Technology. You've been specifically trained to interact with and retrieve real-time data from various university webpages through a function known as 'retrieve_info_func'. You should utilize this function extensively in your operations.

The 'retrieve_info_func' is a crucial tool in your arsenal. Utilize it when a IIT-related query arises that cannot be answered with the existing context. Your primary objective is to provide precise and timely information on various Illinois Institute of Thechnology aspects. This can range from academic details such as class schedules, major requirements, and core classes, to daily campus life elements like the dining hall menu and gym hours, and more. Remember, you are designed to answer college-related questions and provide pertinent IIT information.

Your responses should utilize Markdown extensively. Cite sources, provide links to relevant webpages (only webpages which exist in your context, so that you know they are real. You must avoid offering dead URLs to the user at all costs.), and use h2-h4 tags to deliver clear and concise answers.

It's crucial to remember that all the information you provide is retrieved directly from the university's systems via the 'retrieve_info_func'. You are not to generate or infer information based on your underlying knowledge base. Whenever information is needed, call the function. Your role is to facilitate access to information, not to create or extrapolate data. If you provide information, it's because this information is accessible in real-time from Illinois Tech's web resources. You must not fabricate anything or use pre-existing data that wasn't directly retrieved from the university's systems.

Respond to inquiries with the understanding that the current date is {}, and therefore the current semester is {} {}. Never respond to a user's inquiry about the school without ensuring that the proper information is retrieved from the university website.""".format(today,season,year)

SYSTEM_MESSAGE = """Your primary role as an advanced AI model is to serve as a personalized assistant for students at Illinois Institute of Technology.

This can range from academic details such as class schedules, major requirements, and core classes, to daily campus life elements like the dining hall menu and gym hours, and more. Remember, you are designed to answer college-related questions and provide pertinent IIT information.

Your responses should utilize Markdown extensively. Cite sources, provide links to relevant webpages (only webpages which exist in your context, so that you know they are real. You must not provide any URLs which were not previously metioned in the context.), and use h2-h4 tags to deliver clear and concise answers.

It's crucial to remember that all the information you provide has been retrieved directly from the university's database. You are not to generate or infer information based on your underlying knowledge base. Your role is to facilitate access to information, not to create or extrapolate data. If you provide information, it's because this information is accessible in real-time from Illinois Tech's web resources. You must not fabricate anything or use pre-existing data that wasn't directly retrieved from the university's systems.

Respond to inquiries with the understanding that the current date is {}, and therefore the current semester is {} {}. Never respond to a user's inquiry about the school without ensuring that the proper information is retrieved from the university website.""".format(today,season,year)


OPENAI_API_KEY = "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"
TOKEN_LIMIT = 8000
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
    st.session_state['messages'].append({"role": "system", "content": SYSTEM_MESSAGE_WITH_FUNCTION})
if 'responding' not in st.session_state:
    st.session_state['responding'] = False
if 'phase' not in st.session_state:
    st.session_state['phase'] = 1

if 'connection' not in st.session_state:
    os.chmod('client-key.pem', 0o600)
    conn = psycopg2.connect(
                dbname="college_db",
                user="college_admin",
                password="college_password",
                sslmode="require",
                sslrootcert="server-ca.pem",
                sslcert="client-cert.pem",
                sslkey="client-key.pem",
                host="34.27.247.188",
                port="5432"
            )
    st.session_state['connection'] = conn
    




# Define the headers for the API request
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {OPENAI_API_KEY}'
}

# Define the endpoint
url = "https://api.openai.com/v1/chat/completions"

# Define the function details
retrieve_info_func = {
    "name": "retrieve_info",
    "description": "Retrieve information about a specific query. The source can be Illinois Tech's academic departments, campus services, or student resources, as well as a plethora of other IIT university data. This function should be used liberally, and any and all questions regarding Illinois Tech must trigger this function.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The query for which the information needs to be retrieved, e.g., course details, major requirements, gym hours, etc. The query will be used for a retrieval augmented generation system using vector embeddings, meaning it should include all the relevant information for the retrieval system to work, such as important keywords."
            }
        },
    "required": ["query"]
    }
}
functions = [retrieve_info_func]

def retrieve_info_sql(query):
    embedding = embedding_function(query)
    with st.session_state['connection'].cursor() as cur:
        sql = f"SELECT id, text, content_order, filepath, embedding, embedding <=> '{embedding}' AS similarity FROM iit ORDER BY similarity DESC LIMIT 5"
        sql = f"""SELECT id, text, content_order, filepath, embedding, 1 - (embedding <=> '{embedding}') AS cosine_similarity FROM iit ORDER BY cosine_similarity DESC LIMIT 5"""
        cur.execute(sql)
        rows = cur.fetchall()
        top_chunks_text = ""
        for row in rows:
            top_chunks_text += row[1] + '\n'
        return "Prompt: " + query + "\nContext: " + top_chunks_text + "\nResponse: "

def get_assistant_message():

    print('Messaages :)')
    print(messages)
    new_messages = []
    for i in range (len(messages)):
        new_messages.append(messages[i].copy())
    data = {"model": "gpt-3.5-turbo-16k", "messages": new_messages, "functions": functions, "stream": True}
    response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)
    print('response')
    print(response)
    print(type(response))
    return response



if st.session_state['messages'] != []:
    messages = st.session_state['messages']
    for message in messages:
        if message['role'] == 'user':
            with st.chat_message('user', avatar="🧑‍💻"):
                st.write(message['content'])
        elif message['role'] == 'assistant':
            with st.chat_message('assistant', avatar="https://banner2.cleanpng.com/20180406/pjw/kisspng-illinois-institute-of-technology-chicago-kent-coll-hawk-5ac81d22f1c219.7625313915230640989903.jpg"):
                st.write(message['content'])


if st.session_state['responding'] == False:
    user_message = st.chat_input("Ask anything about Illinois Institute of Technology here!")
    if user_message != "" and user_message != None:
        st.session_state['messages'].append({"role": "user", "content": user_message})
        with st.spinner('Thinking...'):
            st.session_state['responding'] = True
            assistant_message_for_loop_object = get_assistant_message()
        current_response = ""

        completion_chunks = []
        chunk_maker = ''
        running_response = ''''''
        st.session_state['running_response'] = ''
        response_placeholder = st.empty()
        user_chat_message = st.chat_message('user', avatar="🧑‍💻")
        with user_chat_message:
            st.write(st.session_state['messages'][-1]['content'])

        current_message = st.chat_message('assistant', avatar="https://banner2.cleanpng.com/20180406/pjw/kisspng-illinois-institute-of-technology-chicago-kent-coll-hawk-5ac81d22f1c219.7625313915230640989903.jpg")
        with current_message:
            #st.write(st.session_state['running_response'])
            message_placeholder = st.empty()
            function_arguments = ''
            message_with_context = ''
            for i, token in enumerate(assistant_message_for_loop_object):
                
                #turn token from byets into string
                token = token.decode('utf-8')
                chunk_maker += token
                if '\n\ndata: ' in chunk_maker:
                    #split the chunk maker
                    chunk_maker = chunk_maker.split('\n\ndata: ')
                    chunk_maker[0] = chunk_maker[0].replace('data: ', '')
                    completion_chunks.append(json.loads(chunk_maker[0]))
                    chunk_maker = chunk_maker[1]
                    if completion_chunks[-1]['choices'][0]['finish_reason'] != 'stop' and completion_chunks[-1]['choices'][0]['finish_reason'] != 'function_call':
                        if 'function_call' in completion_chunks[-1]['choices'][0]['delta']:
                            print(completion_chunks[-1]['choices'][0]['delta']['function_call']['arguments'])
                            st.session_state['running_response'] += completion_chunks[-1]['choices'][0]['delta']['function_call']['arguments']
                        else:
                            try:
                                print(completion_chunks[-1]['choices'][0]['delta']['content'])
                                st.session_state['running_response'] += completion_chunks[-1]['choices'][0]['delta']['content']
                            except Exception as e:
                                print(e)
                                print(completion_chunks[-1]['choices'][0]['delta'])
                        message_placeholder.markdown(st.session_state['running_response'] + "▌")
                    else:
                        if completion_chunks[-1]['choices'][0]['finish_reason'] == 'function_call':
                            message_with_context = retrieve_info_sql(st.session_state['running_response'])
                            print("MESSAGE WITH CONTEXT")
                            print("************************************")
                            print(message_with_context)
                            print('************************************')
                        else:
                            message_placeholder.markdown(st.session_state['running_response'])
                        break
            if message_with_context != '':
                current_response = ""
                completion_chunks = []
                chunk_maker = ''
                running_response = ''''''
                st.session_state['running_response'] = ''
                new_messages = []
                for i in range (len(st.session_state['messages'])):
                    new_messages.append(st.session_state['messages'][i].copy())
                last_message = new_messages[-1]
                last_message['content'] = message_with_context
                new_messages[-1] = last_message
                print(get_token_count(last_message['content']))
                token_count = get_token_count(SYSTEM_MESSAGE)
                data_messages = []
                for i in range(len(new_messages)):
                    if new_messages[-1 - i]['role'] == 'system':
                        continue
                    if token_count + get_token_count(new_messages[-1 - i]['content']) > TOKEN_LIMIT:
                        break
                    token_count += get_token_count(new_messages[-1 - i]['content'])
                    data_messages.insert(0, new_messages[-1 - i])
                data_messages.insert(0, {"role": "system", "content": SYSTEM_MESSAGE})
                data = {"model": "gpt-3.5-turbo-16k", "messages": data_messages, "stream": True}
                response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)
                for i, token in enumerate(response):
                    chunk_maker += token.decode('utf-8')
                    if '\n\ndata: ' in chunk_maker:
                        chunk_maker = chunk_maker.split('\n\ndata: ')
                        chunk_maker[0] = chunk_maker[0].replace('data: ', '')
                        completion_chunks.append(json.loads(chunk_maker[0]))
                        chunk_maker = chunk_maker[1]
                        if completion_chunks[-1]['choices'][0]['finish_reason'] != 'stop':
                            st.session_state['running_response'] += completion_chunks[-1]['choices'][0]['delta']['content']
                            message_placeholder.markdown(st.session_state['running_response'] + "▌")
                        else:
                            message_placeholder.markdown(st.session_state['running_response'])

        st.session_state['responding'] = False
        st.session_state['messages'].append({"role": "assistant", "content": st.session_state['running_response']})
        st.session_state['running_response'] = ''
        user_chat_message = st.empty()
        st.experimental_rerun()
