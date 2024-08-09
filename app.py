from flask import Flask, request, jsonify, render_template
import sqlite3
import requests
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Database setup
def setup_database():
    conn = sqlite3.connect('company_info.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY, title TEXT, content TEXT, file_path TEXT)''')
    conn.commit()
    return conn

# Function to query the LLM
def query_llm(prompt):
    data = {
        "model": "llama2:9b",
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_API_URL, json=data)
    return response.json()['response']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_document', methods=['POST'])
def add_document():
    conn = setup_database()
    c = conn.cursor()
    
    title = request.form['title']
    content = request.form['content']
    file = request.files.get('file')
    
    file_path = None
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        file.save(file_path)
    
    c.execute("INSERT INTO documents (title, content, file_path) VALUES (?, ?, ?)", 
              (title, content, file_path))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Document added successfully"}), 200

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    conn = setup_database()
    c = conn.cursor()
    
    c.execute("SELECT title, content FROM documents WHERE content LIKE ?", ('%' + query + '%',))
    results = c.fetchall()
    
    if not results:
        return jsonify({"message": "No documents found matching the query."}), 404
    
    summaries = []
    for title, content in results:
        prompt = f"Summarize the following document about {title}:\n\n{content}\n\nSummary:"
        summary = query_llm(prompt)
        summaries.append({"title": title, "summary": summary})
    
    conn.close()
    return jsonify(summaries), 200

@app.route('/summarize', methods=['POST'])
def summarize_file():
    content = request.form['content']
    prompt = f"Summarize the following document:\n\n{content}\n\nSummary:"
    summary = query_llm(prompt)
    return jsonify({"summary": summary}), 200

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, host='127.0.0.1', port=5000)