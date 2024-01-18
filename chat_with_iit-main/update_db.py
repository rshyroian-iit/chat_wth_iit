import os
import pdftotext
from bs4 import BeautifulSoup
import re
from ics import Calendar
import json
import time
from markdownify import markdownify as md
from concurrent.futures import ThreadPoolExecutor, as_completed
from ai import embedding_function, split_content, get_token_count
import uuid
import psycopg2

def connect_db(chunks_dict):
    print('here')
    conn = None
    try:
        # execute in a terminal this command chmod 0600 server-ca.pem
        # here is pyhton running the command
        
        # Establish a connection to the database
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

        # Create a cursor object
        with conn.cursor() as cur:
            print('connected')
            
            '''
            cur.execute("""
                CREATE TABLE iit (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    content_order INT NOT NULL,
                    filepath TEXT NOT NULL,
                    school TEXT NOT NULL,
                    embedding VECTOR(1536) NOT NULL
                );
                """)
            '''
            # Delete all rows
            cur.execute("DELETE FROM iit;")
            # Insert data
            for i,id in enumerate(chunks_dict):
                print(len(chunks_dict) - i)
                print(id)

                text = chunks_dict[id]['text']
                order = chunks_dict[id]['order']
                url = chunks_dict[id]['url']
                school = chunks_dict[id]['school']
                embedding = chunks_dict[id]['embedding']
                uid = chunks_dict[id]['id']
                sql = """INSERT INTO iit (id, text, content_order, filepath , school, embedding)
                         VALUES (%s, %s, %s, %s, %s, %s)"""
                values = (uid, text, order, url, school, embedding)

                cur.execute(sql, values)

            # Commit changes
            conn.commit()

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
    finally:
        if conn is not None:
            conn.close()

counter = 0

def convert_file(filepath):
    hrefs = []
    emails = set()

    if filepath.endswith(".html"):
        with open(filepath, 'r') as file:
            contents = file.read()
        file.close()

        soup = BeautifulSoup(contents, 'html.parser')
        for link in soup.findAll('a', attrs={'href': re.compile("^http://") or re.compile("^https://") or re.compile("^www.") or re.compile("^/")}):
            hrefs.append(link.get('href'))    

        found_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[edu]+\b', contents)
        found_emails += re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[gmail]+\.[com]+\b', contents)
        for email in found_emails:
            emails.add(email)

        for script in soup(["script", "style", "header", "footer", "nav", "aside", "menu", "sidebar", "meta", "link", "noscript", "ins", "iframe", "button", "input", "select", "textarea", "form", "label", "dl", "dt", "dd", "col", "colgroup", "noscript", "audio", "video", "svg", "map", "area", "meter", "progress", "details", "summary", "dialog", "template",  "pre", "samp", "kbd", "var", "bdi", "bdo", "ruby", "rt", "rp", "wbr", "cite", "abbr", "acronym", "q", "img"]):
            script.extract()
        
        contents = str(soup.prettify())
        contents = str(md(contents))
        contents = contents.splitlines()
        text = ""
        for i in range(len(contents)):
            if contents[i].startswith(" ") and contents[i].strip() != "" and contents[i].strip().startswith("#") == False:
                text += contents[i]
            else:
                text += "\n" + contents[i]
        # replace 4+ = with 4 =
        text = re.sub(r'={4,}', '===', text)
        # replace 3+ /n with 2 /n
        text = re.sub(r'\n{3,}', '\n\n', text)

    elif filepath.endswith(".pdf"):
        with open(filepath, 'rb') as file:
            pdf = pdftotext.PDF(file)
        file.close()
        pdf_content = "\n\n".join(pdf)
        pdf_content = pdf_content.splitlines()
        text = ""
        for i in range(len(pdf_content)):
            pdf_content[i].replace("", "")
            pdf_content[i].replace("", "")
            pdf_content[i].replace("", "")
            pdf_content[i].strip()
            text += "\n" + pdf_content[i]
        text = re.sub(r'\n{3,}', '\n\n', text)

    elif filepath.endswith(".ics"):
        with open(filepath, 'r') as file:
            calendar = Calendar(file.read())
        file.close()
        calendar_name = calendar.name if calendar.name else "Calendar"
        event_texts = []
        for event in calendar.events:
            event_name = event.name
            event_start = event.begin.strftime("%Y-%m-%d %H:%M")
            event_text = f"{event_start}: {event_name}"
            if calendar_name != "Calendar":
                event_text = f"{calendar_name}\n{event_text}"
            event_texts.append(event_text)
        text = json.dumps(event_texts, indent=4)
    return text, hrefs, list(emails)

def write_to_json(filepath, url, text, interval, hrefs, emails, timestamp):
    global counter
    chunks = split_content(text, interval, append_content = "Retrieved from " + url)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(embedding_function, chunk) for chunk in chunks]
        for future in as_completed(futures):
            counter += 1
            chunk_embedding = future.result()
            chunk_index = futures.index(future)
            chunks[chunk_index] = {'text': chunks[chunk_index], 'embedding': chunk_embedding, 'order': chunk_index, 'id': str(uuid.uuid4())}
    print(counter)
    if counter > 2000:
        counter = 0
        print("Sleeping for 20 seconds...")
        time.sleep(20)
    json_content = {'token_count': get_token_count(text), 'chunks': chunks, 'hrefs': hrefs, 'emails': emails, 'url': url, 'timestamp': timestamp}
    json_filepath = filepath + ".json"
    with open(json_filepath, 'w', encoding='utf-8') as json_file:
        json.dump(json_content, json_file, ensure_ascii=False, indent=4)

school_name = 'Illinois Institute of Technology'

with open(f'{school_name}/last_timestamp.txt', 'r') as file:
    last_timestamp = float(file.read().strip())
file.close()

with open(f'{school_name}/last_timestamp.txt', 'w') as file:
    file.write(str(time.time()))
file.close()

for root, dirs, files in os.walk(school_name):
    for file in files:
        if file.endswith('.html') or file.endswith('.pdf') or file.endswith('.ics'):
                try:
                    filepath = os.path.join(root, file)
                    file_timestamp = os.path.getmtime(filepath)
                    url = filepath.replace(school_name, 'https:/')
                    url = os.path.splitext(url)[0]
                    if file_timestamp > last_timestamp:
                        if os.path.exists(filepath + '.json'):
                            os.remove(filepath + '.json')
                        text, hrefs, emails = convert_file(filepath)
                        write_to_json(filepath, url, text, interval=400, hrefs=hrefs, emails=emails, timestamp=file_timestamp)
                except Exception as e:
                    print(e)
                    print(f"Error converting {filepath} to json.")

json_files = []
for root, dirs, files in os.walk(school_name):
    for file in files:
        if file.endswith('.json'):
            json_files.append(os.path.join(root, file))

embeddings_dict = {}
text_dict = {}
chunks_dict = {}
numbers_used = []
for json_file in json_files:
    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    file.close()
    if 'url' not in data.keys():
        continue
        

    for chunk in data['chunks']:

        embeddings_dict[chunk['id']] = chunk['embedding']
        text_dict[chunk['id']] = {'text': chunk['text'], 'order': chunk['order'], 'url': data['url']}
        random_int = str(uuid.uuid4())
        while random_int in numbers_used:
            random_int = str(uuid.uuid4())
        numbers_used.append(random_int)
        chunks_dict[chunk['id']] = {'text': chunk['text'], 'order': chunk['order'], 'url': data['url'], 'embedding': chunk['embedding'], 'school': school_name, 'id': random_int}

connect_db(chunks_dict)