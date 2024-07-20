#!/usr/bin/env python3
import sqlite3
import json
import subprocess
import os
import traceback
from pathlib import Path
import time
import csv
import datetime
import random
import base64

VERSION = "0.4"
DB_NAME = "vocabulary.db"
TABLE_NAME = "vocabulary"
KEY = None
CONFIG_DIR = "phrases_configs"
DEFAULT_VIEW_OPTION_IDX = 0
REMOTE_CONFIG_URL = 'https://raw.githubusercontent.com/songlinhou/phrases/main/configs/general.json'
SERVER_ADDR = None


__cloud_user_email = None
__cloud_username = None
__cloud_password = None
__in_main_menu = True

example = json.dumps({"explanation":"THE EXPLAINATION GOES HERE", "example sentences":["sentence 1", "sentence 2", "sentence 3"], "translations":["翻译1", "翻译2", "翻译3"]})

config_path = os.path.join(str(Path.home()), CONFIG_DIR)
os.makedirs(config_path, exist_ok=True)
DEFAULT_DB_NAME = os.path.join(config_path, DB_NAME)

def title():
    _title = f"""
██████╗ ██╗  ██╗██████╗  █████╗ ███████╗███████╗███████╗
██╔══██╗██║  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝
██████╔╝███████║██████╔╝███████║███████╗█████╗  ███████╗
██╔═══╝ ██╔══██║██╔══██╗██╔══██║╚════██║██╔══╝  ╚════██║
██║     ██║  ██║██║  ██║██║  ██║███████║███████╗███████║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
-----------------------------------------VERSION: {VERSION}----
    """
    if __cloud_username:
        _title += f"\nLogged in as {__cloud_username}"
    return _title

class ListOrderOptions:
    RANDOM = "Randomized"
    EARLIST_FIRST = "Start with Earliest"
    LATEST_FIRST = "Start with Latest"

def success_text(msg):
    OKGREEN = '\033[92m'
    ENDC = '\033[0m'
    return OKGREEN + msg + ENDC

def error_text(msg):
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    return FAIL + msg + ENDC

def warn_text(msg):
    WARNING = '\033[93m'
    ENDC = '\033[0m'
    return WARNING + msg + ENDC

def clear_console():
    if os.name == "nt":
        os.system('cls')
    else:
        os.system('clear')        

def chat_with_gpt(prompt):
    if KEY is not None:
        import openai
        openai.api_key = KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # You can choose different engines like "gpt-3.5-turbo" or "davinci"
            messages=[{'role': 'user', 'content': prompt}]
        )

        return response.choices[0].message.content.strip()
    else:
        import requests
        url = f"{SERVER_ADDR}/chat_with_gpt"
        resp = requests.post(url, json={
            'prompt': prompt,
            'email': __cloud_user_email,
            'password': __cloud_password
        })
        if resp.ok:
            data = resp.json()
            success = data['success']
            if success:
                return data['output']
            else:
                print(error_text(data['message']))
                return None
        else:
            print(error_text("Unable to use Lookup function."))
            return None

def validate_non_empty(_, answer):
    import inquirer
    if not answer.strip():
        inquirer.errors.ValidationError("Empty input", reason="Cannot be empty")
        return False
    else:
        return True
def validate_password(_, answer):
    import inquirer
    if not answer.strip():
        inquirer.errors.ValidationError("Empty password", reason="Cannot be empty")
        return False
    if len(answer.strip()) < 6:
        inquirer.errors.ValidationError("Password length is at least 6", reason="Password too short")
        return False
    return True

def get_input(label="Search", validate=True, password=False):
    import inquirer
    try:
        if validate is False:
            if not password:
                questions = [
                inquirer.Text(label, message=label)
                ]
            else:
                questions = [
                inquirer.Password(label, message=label)
                ]
        else:
            if not password:
                questions = [
                inquirer.Text(label, message=label, validate=validate_non_empty)
                ]
            else:
                questions = [
                inquirer.Password(label, message=label, validate=validate_password)
                ]
        answers = inquirer.prompt(questions)
        return answers[label]
    except:
        show_menu()

def get_selection(options, question, default_idx = 0):
    import inquirer
    try:
        questions = [
        inquirer.List('answer',
                        message=question,
                        choices=options,
                        default=options[default_idx]
                    ),
        ]
        answers = inquirer.prompt(questions)
        if answers is None:
            # print("Cancelled.")
            show_menu()
            
        return answers['answer']
    except:
        if not __in_main_menu:
            show_menu()
        
def get_db_conn():
    if __cloud_user_email is None:
        # Connect to the database (or create it if it doesn't exist)
        conn = sqlite3.connect(DEFAULT_DB_NAME)
    else:
        user_dir = os.path.join(config_path, 'users', __cloud_user_email)
        os.makedirs(user_dir, exist_ok=True)
        db_name = os.path.join(user_dir, DB_NAME)
        conn = sqlite3.connect(db_name)
    return conn

def init_db():
    conn = get_db_conn()
    # Create a cursor object
    cursor = conn.cursor()

    # Define the CREATE TABLE statement
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    phases TEXT,
    explanations TEXT,
    examples TEXT,
    translations TEXT,
    notes TEXT
    );
    """

    # Execute the CREATE TABLE statement
    cursor.execute(create_table_sql)

    # Commit the changes to the database
    conn.commit()

    # Close the connection
    conn.close()

    print("Table created successfully!")
    update_database()
    
def edit_note_of_phase():
    pass

def find_existing_record(voc):
    phase = json.dumps(voc)
    
    # Connect to the database
    conn = get_db_conn()

    # Create a cursor object
    cursor = conn.cursor()
    sql = f"SELECT * FROM {TABLE_NAME} where phases = ?"
    # Execute the SELECT statement
    cursor.execute(sql, (phase, ))

    # Fetch all records at once using fetchall()
    all_records = cursor.fetchall()
    if len(all_records) == 0:
        return None
    else:
        return all_records[0]
    
    
    
def get_results(voc):
    record = find_existing_record(voc)
    if record is not None:
        show_record(None, record, None, from_search=True)
        return None
    else:
        answer = chat_with_gpt(f"Explain the meaning of {voc} in simple words. And give 3 example sentences as well as the translations of these 3 example sentences in Chinese. The output should be a JSON following the format below:\n{example}")
        output_json = json.loads(answer)
        return output_json

def insert_record(voc, output_json, note=None, skip_backup=True, skip_message=False):
    if output_json is None:
        return
    try:
        phase = json.dumps(voc)
        explanation = json.dumps(output_json['explanation'])
        example = json.dumps(output_json['example sentences'])
        translation = json.dumps(output_json['translations'])
        
        # Connect to the database
        conn = get_db_conn()

        # Create a cursor object
        cursor = conn.cursor()

        # Define the INSERT statement with placeholders for data
        if note is None:
            insert_sql = f"""
            INSERT INTO vocabulary (phases, explanations, examples, translations)
            VALUES (?, ?, ?, ?)
            """

            # Insert data as a tuple
            data_tuple = (phase, explanation, example, translation)
        
        else:
            insert_sql = f"""
            INSERT INTO vocabulary (phases, explanations, examples, translations, notes)
            VALUES (?, ?, ?, ?, ?)
            """
            note = json.dumps(note)
            # Insert data as a tuple
            data_tuple = (phase, explanation, example, translation, note)

        # Execute the INSERT statement with data tuple
        cursor.execute(insert_sql, data_tuple)

        # Commit the changes to the database
        conn.commit()

        # Close the connection
        conn.close()
        if not skip_message:
            print(success_text(f"Record inserted successfully: {voc}"))
    except sqlite3.Error as e:
        print(error_text("Error inserting record:" + str(e)))

    if not skip_backup:
        backup_vocabulary()
        
def update_record_note(voc, note):
    import requests
    conn = get_db_conn()
    cursor = conn.cursor()
    condition = f"phases = '{voc}'"
    update_query = f"UPDATE {TABLE_NAME} SET notes = ? WHERE {condition}"
    cursor.execute(update_query, (json.dumps(note),))
    conn.commit()
    conn.close()

    if __cloud_user_email is not None:
        resp = requests.post(f"{SERVER_ADDR}/edit_note", json={
            'email': __cloud_user_email,
            'phrase': json.loads(voc),
            'note': note
        })
        if resp.ok:
            data = resp.json()
            success = data['success']
            if not success:
                print(error_text("Unable to communicate with server: " + data['message']))
                time.sleep(2)
        else:
            print(error_text("Server connection failed ..."))
            time.sleep(2)

    
def delete_record(voc):
    import requests
    conn = get_db_conn()
    cursor = conn.cursor()
    # condition = f"phases = '{voc}'"
    delete_query = f"DELETE FROM {TABLE_NAME} WHERE phases = ?"
    print("query", delete_query)
    cursor.execute(delete_query, (voc, ))
    conn.commit()
    conn.close()

    if __cloud_user_email is not None:
        resp = requests.post(f"{SERVER_ADDR}/delete_from_server", json={
            'email': __cloud_user_email,
            'phrase': json.loads(voc)
        })
        if resp.ok:
            data = resp.json()
            success = data['success']
            if not success:
                print(error_text("Unable to delete from server: " + data['message']))
                time.sleep(2)
        else:
            print(error_text("Server connection failed ..."))
            time.sleep(2)
        
def edit_record(idx, record, total_num):
    global __in_main_menu
    __in_main_menu = False
    clear_console()
    print("Edit now")
    print("================================")
    print(f"{idx + 1} / {total_num}")
    phase = json.loads(record[0])
    explanation = json.loads(record[1])
    examples = json.loads(record[2])
    translates = json.loads(record[3])
    note = json.loads(record[4]) if record[4] is not None else ""
    print(success_text("Phase: ") + phase)
    print(success_text("Explanation: ") + explanation)
    print("\n" + success_text("Examples: "))
    for example,translate in zip(examples, translates):
        print(example)
        print(translate)
    if note:
        print("\n" + success_text("Note: ") + note)
        
    note = get_input("Note", validate=False)
    if note.strip() != '':
        update_record_note(record[0], note.strip())
        print(success_text("Note is updated."))
    options = ['Done', 'Delete']
    idx = options.index(get_selection(options, "Edit Options"))
    if idx == 0:
        return
    elif idx == 1:
        delete_record(record[0])
        print(success_text(f"Record of {phase} is deleted... Back in 3 seconds ..."))
        time.sleep(3)
    
def evaluate_translation(voc, chinese, english, language="English"):
    if chinese.strip() == "" or english.strip() == "":
        return ""
    prompt = f"This is an sentence making exercise using \"{voc}\"." 
    prompt += f"Given the sentence \"{chinese}\" and the translation \"{english}\", " 
    prompt += f"evaluate the translation, correct any mistakes and recommend any improvements in {language}."
    prompt += f"The evaluation must include \"{voc}\" in it."
    output = chat_with_gpt(prompt)
    return output

def show_record(idx, record, total_num, from_search = False, default_option_idx = 0):
    global DEFAULT_VIEW_OPTION_IDX
    global __in_main_menu
    __in_main_menu = False
    print("================================")
    if not from_search:
        print(f"{idx + 1} / {total_num}")
    phase = json.loads(record[0])
    explanation = json.loads(record[1])
    examples = json.loads(record[2])
    translates = json.loads(record[3])
    note = json.loads(record[4]) if record[4] is not None else ""
    print(success_text("Phase: ") + phase)
    print(success_text("Explanation: ") + explanation)
    print("\n" + success_text("Examples: "))
    for example,translate in zip(examples, translates):
        print(example)
        print(translate)
    
    if note:
        print("\n" + success_text("Note: ") + note)
    
    if not from_search:
        options = ['Next', 'Prev', 'Practice', 'Edit', 'Back']
        print()
        choice = get_selection(options,'Operation', default_idx = default_option_idx)
        if choice is None:
            return
        
        DEFAULT_VIEW_OPTION_IDX = options.index(choice)
        if options.index(choice) == 0:
            return idx + 1, None
        elif options.index(choice) == 1:
            return idx - 1, None
        elif options.index(choice) == 2:
            return idx, lambda: practice_phase(record[0], examples, translates)
        elif options.index(choice) == 3:
            return idx, lambda: edit_record(idx, record, total_num)
        else:
            show_menu()
            return -1, None

    
def add_column_to_table(table_name, column_name, data_type):
    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {data_type}")
        conn.commit()
        print(f"Column '{column_name}' added successfully to database.")
    except sqlite3.OperationalError as e:
        print(f"Error adding column: {e}")
    finally:
        cursor.close()
        conn.close()
        
def get_all_voc(clear=True, order_option=ListOrderOptions.EARLIST_FIRST):
    # Connect to the database
    conn = get_db_conn()

    # Create a cursor object
    cursor = conn.cursor()

    # Define the SELECT statement to retrieve all columns from all rows
    select_all_sql = f"""
    SELECT * FROM {TABLE_NAME}
    """

    # Execute the SELECT statement
    cursor.execute(select_all_sql)

    # Fetch all records at once using fetchall()
    all_records = cursor.fetchall()
    if order_option == ListOrderOptions.RANDOM:
        random.shuffle(all_records)
    elif order_option == ListOrderOptions.LATEST_FIRST:
        all_records = list(reversed(all_records))
    # Print all records
    if all_records:
        print("Records:")
        # for idx, record in enumerate(all_records):
        #     show_record(idx, record, len(all_records))
        idx = 0
        record = all_records[idx]
        
        while True:
            if clear:
                clear_console()
            next_idx, op = show_record(idx, record, len(all_records), default_option_idx=DEFAULT_VIEW_OPTION_IDX)
            if op is not None:
                op()
                cursor.execute(select_all_sql)
                all_records = cursor.fetchall()
                if idx < 0:
                    idx = 0
                elif idx >= len(all_records):
                    idx = len(all_records)
                
                if order_option == ListOrderOptions.RANDOM:
                    random.shuffle(all_records)
                elif order_option == ListOrderOptions.LATEST_FIRST:
                    all_records = list(reversed(all_records))
                
                if len(all_records) == 0:
                    clear_console()
                    show_menu()
                    return 
                
                record = all_records[idx]
                clear_console()
                
            idx = next_idx
            if idx == -1:
                idx = len(all_records) - 1
            elif idx >= len(all_records):
                idx = 0
                
            record = all_records[idx]
    else:
        print(error_text("No records found in the table."))
        wait_for_enter_key()
        show_menu()

    # Close the connection
    conn.close()

def get_all_records():
    # Connect to the database
    conn = get_db_conn()

    # Create a cursor object
    cursor = conn.cursor()

    # Define the SELECT statement to retrieve all columns from all rows
    select_all_sql = f"""
    SELECT * FROM {TABLE_NAME}
    """

    # Execute the SELECT statement
    cursor.execute(select_all_sql)

    # Fetch all records at once using fetchall()
    all_records = cursor.fetchall()
    return all_records

def start_general_practice(review_language='English'):
    print(success_text("Vocabulary Size: ") + str(len(get_all_records())))
    options = ["Warm Up (5 - 10 exercises)", "Standard (11 - 20 exercises)", "Advanced (21 - 40 exercises)", "Challenge (41 - 80 exercises)", "All (all exercises)"]
    idx = options.index(get_selection(options, "How many exercises?"))
    if idx == 0:
        general_practice(num_questions=random.randint(5,10), review_language=review_language)
    elif idx == 1:
        general_practice(num_questions=random.randint(11,20), review_language=review_language)
    elif idx == 2:
        general_practice(num_questions=random.randint(21,40), review_language=review_language)
    elif idx == 3:
        general_practice(num_questions=random.randint(41,80), review_language=review_language)
    elif idx == 4:
        general_practice(num_questions=-1)

def general_practice(num_questions=-1, review_language='English'):
    global __in_main_menu
    __in_main_menu = False
    clear_console()
    all_records = get_all_records()
    question_list = []
    
    for id, record in enumerate(all_records):
        phase = json.loads(record[0])
        explanation = json.loads(record[1])
        examples = json.loads(record[2])
        translates = json.loads(record[3])
        note = json.loads(record[4]) if record[4] is not None else ""
        for translate, example in zip(translates, examples):
            item = (phase, explanation, translate, example, note)
            question_list.append(item)
            
    random.shuffle(question_list)
    if num_questions > 0:
        num_questions = min(num_questions, len(question_list))
        question_list = question_list[:num_questions]
    
    for id, question in enumerate(question_list):
        (phrase, explanation, translate, example, note) = question
        print(f"\n{id + 1}/{len(question_list)}\t" + success_text(translate))
        user_trans = get_input("Translate")
        print("-" * 10)
        print(success_text("Answer: ") + example)
        print()
        print(success_text('Phrase: ') + phrase)
        print(success_text('Explanation: ') + explanation)
        if note.strip() != "":
            print(success_text('Note: ') + note)
        evaluation = evaluate_translation(phrase, translate, user_trans, language=review_language)
        print(success_text("Evaluation: ") + evaluation)
        
    print(success_text("Test completed!"))
    print('\n' + success_text("<Press ENTER key to continue>"))
    input()
    show_menu()
    
def practice_phase(voc, examples, translations, review_language='English'):
    global __in_main_menu
    __in_main_menu = False
    clear_console()
    print("Translate the following sentence into English using phase " + success_text(voc))
    for idx, (example, translation) in enumerate(zip(examples, translations)):
        print("\n" + success_text(translation))
        user_trans = get_input("Translate:")
        print(f"Answer: {example}")
        evaluation = evaluate_translation(voc, translation, user_trans, language=review_language)
        print(success_text("Evaluation: ") + evaluation)
    print("\n" + "=" * 10)
    options = ['Try again', 'Done']
    idx = options.index(get_selection(options, "Operation"))
    if idx == 0:
        return practice_phase(voc, examples, translations)
    elif idx == 1:
        return

def show_output_json(voc, data_json, pause=True):
    global __in_main_menu
    __in_main_menu = False
    phase = voc
    explanation = data_json['explanation']
    examples = data_json['example sentences']
    translations = data_json['translations']
    print(explanation)
    print("\n" + success_text("Examples:"))
    for example, translation in zip(examples, translations):
        print(example)
        print(translation)
    if pause:
        print('\n' + success_text("<Press ENTER key to continue>"))
        input()

def show_menu(show_title=True):
    global DEFAULT_VIEW_OPTION_IDX
    global __in_main_menu
    __in_main_menu = True
    init_db()
    clear_console()
    if __cloud_user_email is None:
        print(success_text(title()))
        print("To use local version, please provide your own ChatGPT API Key.")
        read_chatgpt_key()
    else:
        print(warn_text(title()))
    
    
    DEFAULT_VIEW_OPTION_IDX = 0
    options = ["Lookup", "Vocabulary Book", "General Test", "Export to CSV","Exit"]
    answer = get_selection(options, "What do you want to do?")
    if answer is None:
        exit(0)
    idx = options.index(answer)
    if idx == 0:
        voc = get_input(validate=False)
        if voc.strip() != '':
            try:
                output_json = get_results(voc)
                if output_json is not None:
                    show_output_json(voc, output_json, pause=False)
                    insert_record(voc, output_json, skip_backup=False)
            except Exception as e:
                print(error_text("Failed to get results:") + str(e))
        
            print('\n' + success_text("<Press ENTER key to continue>"))
            input()
        show_menu()
        
    elif idx == 1:
        options = [ListOrderOptions.RANDOM, ListOrderOptions.EARLIST_FIRST, ListOrderOptions.LATEST_FIRST]
        order = get_selection(options, "Select the browsing order")
        clear_console()
        backup_vocabulary()
        get_all_voc(order_option=order)
    elif idx == 2:
        backup_vocabulary()
        start_general_practice()
    elif idx == 3:
        backup_vocabulary()
        export_to_csv()
    elif idx == 4:
        exit(0)

def update_database():
    add_column_to_table(TABLE_NAME, 'notes', 'TEXT')
    
def get_local_config():
    config_path = os.path.join(str(Path.home()), CONFIG_DIR)
    os.makedirs(config_path, exist_ok=True)
    general_config_path = os.path.join(config_path, 'general.json')
    if os.path.exists(general_config_path):
        with open(general_config_path, 'r') as f:
            general_config = json.load(f)
    else:
        with open(general_config_path, 'w') as f:
            json.dump({}, f)
        general_config = {}
    return general_config

def save_local_config(key, value):
    config_path = os.path.join(str(Path.home()), CONFIG_DIR)
    os.makedirs(config_path, exist_ok=True)
    general_config_path = os.path.join(config_path, 'general.json')
    if os.path.exists(general_config_path):
        with open(general_config_path, 'r') as f:
            general_config = json.load(f)
    else:
        general_config = {}
    general_config[key] = value
    with open(general_config_path, 'w') as f:
        json.dump(general_config, f)
        
def export_to_csv():
    # Connect to the database
    conn = get_db_conn()

    # Create a cursor object
    cursor = conn.cursor()

    # Define the SELECT statement to retrieve all columns from all rows
    select_all_sql = f"""
    SELECT * FROM {TABLE_NAME}
    """

    # Execute the SELECT statement
    cursor.execute(select_all_sql)

    # Fetch all records at once using fetchall()
    all_records = cursor.fetchall()
    
    fname = f"phases_export_{str(datetime.datetime.now())}.csv".replace(" ", "_")
    with open(fname, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Phases', 'Explanations', 'Examples', 'Translations', 'Notes'])
        for record in all_records:
            phase = json.loads(record[0])
            explanation = json.loads(record[1])
            examples = json.loads(record[2])
            translates = json.loads(record[3])
            note = json.loads(record[4]) if record[4] is not None else ""
            writer.writerow([phase, explanation, '\n'.join(examples), '\n'.join(translates), note])
            
    print(success_text(f"Successfully export to csv: {fname}"))
    time.sleep(2)
    clear_console()
    show_menu()

def vocabulary_to_json():
    # Connect to the database
    conn = get_db_conn()

    # Create a cursor object
    cursor = conn.cursor()

    # Define the SELECT statement to retrieve all columns from all rows
    select_all_sql = f"""
    SELECT * FROM {TABLE_NAME}
    """

    # Execute the SELECT statement
    cursor.execute(select_all_sql)

    # Fetch all records at once using fetchall()
    all_records = cursor.fetchall()
    
    # writer.writerow(['Phases', 'Explanations', 'Examples', 'Translations', 'Notes'])
    json_data = []
    for record in all_records:
        item = {}
        item['phrase'] = json.loads(record[0])
        item['explanation'] = json.loads(record[1])
        item['examples'] = json.loads(record[2])
        item['translations'] = json.loads(record[3])
        item['note'] = json.loads(record[4]) if record[4] is not None else ""
        json_data.append(item)
            
    # print(success_text(json.dumps(json_data, indent=2)))
    # wait_for_enter_key()
    # clear_console()
    # show_menu()
    return json_data

def backup_vocabulary():
    import requests
    from tqdm.auto import tqdm
    if __cloud_user_email is None:
        return
    try:
        voc_data = vocabulary_to_json()
        latest_voc = requests.post(f"{SERVER_ADDR}/backup_voc", json={
            'email': __cloud_user_email,
            'password': __cloud_password,
            'local_voc': voc_data
        })
        resp = latest_voc.json()
        if resp['success']:
            remote_voc = resp['voc']
            local_vocabs = [s['phrase'] for s in voc_data]
            print(success_text("Syncronizing local data ..."))
            for remote_vocab in tqdm(remote_voc):
                phrase = remote_vocab['phrase']
                if phrase not in local_vocabs:
                    record_json = {
                        'explanation': remote_vocab['explanation'],
                        'example sentences': remote_vocab['examples'],
                        'translations': remote_vocab['translations']
                    }
                    note = remote_vocab['note'] if remote_vocab['note'].strip() != '' else None
                    insert_record(phrase, record_json, note, skip_backup=True, skip_message=True)
            print(success_text("vocabulary is backed up successfully"))
        else:
            print(error_text("Failed to backup vocabulary"))

    except Exception as e:
        print(error_text(e))

def encode_binary_file_to_base64_string(file_path):
    # Read the binary file
    with open(file_path, 'rb') as binary_file:
        binary_data = binary_file.read()

    # Encode the binary data to a Base64 string
    base64_encoded_data = base64.b64encode(binary_data)

    # Convert bytes to string
    base64_string = base64_encoded_data.decode('utf-8')
    
    return base64_string
        
        
def get_config_value(key):
    general_config = get_local_config()
    return general_config.get(key, None)


def read_chatgpt_key():
    global KEY
    chatgpt_key_label = "chatgpt_key"
    key = get_config_value(chatgpt_key_label)
    if key is None:
        while True:
            # chatgpt_key = get_input("ChatGPT Key")
            chatgpt_key = input("[?] ChatGPT Key: ")
            try:
                KEY = chatgpt_key
                chat_with_gpt("hello")
                save_local_config(chatgpt_key_label, KEY)
                print(success_text("ChatGPT Key is saved locally... Entering in 3 seconds ..."))
                time.sleep(3)
                clear_console()
                print(success_text(title()))
                break
            except Exception as e:
                print(error_text("Failed to connect to ChatGPT. Double check if the key is correct and try again.") + f"[{str(e)}]")
                KEY = None
    else:
        chatgpt_key = key
    KEY = chatgpt_key
        
def install_dependencies(libs):
    try:
        py_bin = subprocess.check_output("which python3", shell=True).decode().strip()
        for lib in libs:
            ret = subprocess.call(f"{py_bin} -m pip install -q {lib}", shell=True)
            assert ret == 0, error_text(f"Cannot install library {lib}")
    except:
        print(error_text("Please make sure python3 and pip are installed in your system."))

def change_version():
    global SERVER_ADDR
    clear_console()
    import requests
    try:
        remote_config = requests.get(REMOTE_CONFIG_URL).json()
        SERVER_ADDR = remote_config['server_addr']
        if requests.get(SERVER_ADDR).ok:
            print("Server detected!")
            options = ["Cloud (Recommended)", "Local"]
            idx = options.index(get_selection(options, "Select your preferred version (Can be switched anytime in settings.)"))
        else:
            idx = 1
    except:
        idx = 1
    if idx == 0:
        # cloud
        email = get_input("Email", validate=True)
        is_new = is_user_new(email)
        if is_new:
            username = get_input("Username", validate=True)
            password = get_input("Password", validate=True, password=True)
            print(email, username, password)
            create_user(email, username, password)
        else:
            password = get_input("Password", validate=True, password=True)
            login_user(email, password)
    else:
        # read_chatgpt_key()
        show_menu()
        pass

def wait_for_enter_key():
    print('\n' + success_text("<Press ENTER key to continue>"))
    input()

def is_user_new(email):
    import requests
    url = f"{SERVER_ADDR}/is_user_new"
    resp = requests.post(url, json={
        "email": email
    })
    if resp.ok:
        resp_data = resp.json()
        success = resp_data['success']
        if success:
            is_new = resp_data['is_new']
            if is_new:
                print(success_text(f"Creating a new user..."))
                return True
            else:
                username = resp_data['username']
                print(success_text(f"Login as {username}"))
                return False
        else:
            message = resp_data['message']
            # print(resp_data)
            print(error_text(f"Failed to verify email: {message}"))
            wait_for_enter_key()
            change_version()
            return False
    else:
        print(error_text(f"Connection failed... Please try again later ..."))
        wait_for_enter_key()
        change_version()
        return False
    
def login_user(email, password):
    global __cloud_user_email
    global __cloud_username
    global __cloud_password
    global KEY
    import requests
    url = f"{SERVER_ADDR}/login_user"
    resp = requests.post(url, json={
        "email": email,
        "password": password
    })
    if resp.ok:
        resp_data = resp.json()
        success = resp_data['success']
        if success:
            user_data = resp_data['data']
            username = user_data['Username']
            print(success_text(f"Welcome back, {username}!"))
            __cloud_user_email = email
            __cloud_username = username
            __cloud_password = password
            _key = user_data['ChatGPT Key'].strip()
            if _key != "":
                KEY = _key

            # fetch latest vocabs from server
            # TODO
            wait_for_enter_key()
            # vocabulary_to_json()
            init_db()
            show_menu()
        else:
            message = resp_data['message']
            print(error_text(f"Login failed:{message}"))
            wait_for_enter_key()
            change_version()
    else:
        print(error_text(f"Login failed. Please try it later ..."))
        wait_for_enter_key()
        change_version()

def create_user(email, username, password):
    global __cloud_user_email
    global __cloud_username
    global __cloud_password
    import requests
    login_user_addr = f"{SERVER_ADDR}/new_user"
    if password.strip() == '':
        print(error_text(f"Password cannot be empty"))
        wait_for_enter_key()
        change_version()
    resp = requests.post(login_user_addr, json={
        "email": email,
        "username": username,
        "password": password
    })
    if resp.ok:
        resp_data = resp.json()
        success = resp_data['success']
        if success:
            print(success_text(f"Success! Welcome {username}!"))
            __cloud_user_email = email
            __cloud_username = username
            __cloud_password = password
            init_db()
            wait_for_enter_key()
            show_menu()
        else:
            message = resp_data['message']
            print(error_text(f"Failed to create user:{message}"))
            wait_for_enter_key()
            change_version()
    else:
        print(error_text(f"Failed to create user. Please try again later."))
        wait_for_enter_key()
        change_version()

if __name__ == "__main__":
    try:
        install_dependencies(['inquirer==2.8.0', 'openai==0.28', 'requests', 'tqdm'])
        init_db()
        change_version()
        init_db()
        show_menu()
        
    except Exception as e:
        print(error_text("Error occurred: " + str(e)))
        stack_trace = traceback.format_exc()
        print(stack_trace)
