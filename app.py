import os
import io
import psycopg2 
from psycopg2 import Error
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
# import google.generativeai as genai
from google import genai
from google.genai import types

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    system_instruction = "You are an elite personal gym trainer. You provide workout plans, diet advice, and form checks based on user input and uploaded files (images/PDFs). Be motivational, precise, and helpful. If user provide their injuries details, consider them carefully in your advice."

    client = genai.Client()
    modelchat = client.chats.create(
        model='gemini-2.5-flash',
        config= types.GenerateContentConfig(
            system_instruction= system_instruction
        )
    )
    

    # genai.configure(api_key=GEMINI_API_KEY)
    # model = genai.GenerativeModel('gemini-2.5-flash')
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")


def connect_to_db():
    
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASS", "mysecretpassword")
    DB_PORT = os.getenv("DB_PORT", "5432")

    connection = None
    try:
        # Establish connection
        connection = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, 
            password=DB_PASSWORD, port=DB_PORT
        )
        print("Database connection established successfully.")
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

    return connection

def initialize_db():
    """Create files table if it doesn't exist"""
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                mimetype VARCHAR(100),
                file_data BYTEA NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER
            )
        """)
        conn.commit()
        print("Files table initialized successfully.")
        return True
    except Error as e:
        print(f"Error initializing database: {e}")
        return False
    finally:
        if conn:
            cursor.close()
            conn.close()

def save_file_to_db(filename, mimetype, file_data, file_size):
    """Save uploaded file to PostgreSQL"""
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO uploaded_files (filename, mimetype, file_data, file_size)
            VALUES (%s, %s, %s, %s)
        """, (filename, mimetype, file_data, file_size))
        conn.commit()
        print(f"File '{filename}' saved to database successfully.")
        return True
    except Error as e:
        print(f"Error saving file to database: {e}")
        conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.form.get('message', '')
    files = request.files.getlist('files')

    # Prepare for Gemini
    gemini_parts = []
    
    if user_message:
        gemini_parts.append(user_message)

    try:
        import tempfile
        import pathlib

        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                
                file_data = file.read()
                file.seek(0) # Reset pointer
                mimetype = file.mimetype
                file_size = len(file_data)

                # Save file to PostgreSQL
                save_file_to_db(filename, mimetype, file_data, file_size)









                # Upload to Gemini File API
                if GEMINI_API_KEY:
                    # Create a temp file to upload
                    with tempfile.NamedTemporaryFile(delete=False, suffix=pathlib.Path(filename).suffix) as tmp:
                        tmp.write(file_data)
                        tmp_path = tmp.name
                    
                    try:
                        
                        uploaded_file = client.files.upload(
                            file=tmp_path,
                        )
                        gemini_parts.append(uploaded_file)
                    except Exception as upload_error:
                        print(f"Error uploading to Gemini: {upload_error}")
                    finally:
                        # Clean up temp file
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

    except Exception as e:
        print(f"File processing error: {e}")
        return jsonify({"response": f"Error processing files: {str(e)}"}), 500

    
    if not GEMINI_API_KEY:
         return jsonify({"response": "Error: Gemini API Key is missing. Please check your .env file."})

    try:
        
        # system_instruction = "You are an elite personal gym trainer. You provide workout plans, diet advice, and form checks based on user input and uploaded files (images/PDFs/Videos). Be motivational, precise, and helpful. Format your response in clean Markdown."
        
        
        
        
        # full_prompt = [system_instruction] + gemini_parts
        full_prompt = gemini_parts
        print("Gemini Parts:", gemini_parts)
        print("Full Prompt to Gemini:", full_prompt)
        # response = model.generate_content(full_prompt)
        # bot_reply = response.text

        

        # response = chat.send_message(full_prompt)
        response = modelchat.send_message(full_prompt)

        bot_reply = response.text
        
        return jsonify({"response": bot_reply})

    except Exception as e:
        return jsonify({"response": f"I encountered an error processing your request with Gemini: {str(e)}"}), 500

if __name__ == '__main__':
    initialize_db()
    app.run(debug=True, port=5000)
