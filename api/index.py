from flask import Flask, render_template, request, jsonify
import os
import json
import csv

# Initialize Flask with correct template folder
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Configure for Vercel
app.config['PROPAGATE_EXCEPTIONS'] = True

# Initialize OpenAI
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MODEL = "gpt-4.1-mini-2025-04-14"
except Exception as e:
    client = None
    print(f"OpenAI initialization error: {e}")

# Scripture data
CANONS = [
    {
        "key": "bom", "name": "Book of Mormon", "books": [
            {"name":"1 Nephi","chapters":22},{"name":"2 Nephi","chapters":33},
            {"name":"Jacob","chapters":7},{"name":"Enos","chapters":1},
            {"name":"Jarom","chapters":1},{"name":"Omni","chapters":1},
            {"name":"Words of Mormon","chapters":1},{"name":"Mosiah","chapters":29},
            {"name":"Alma","chapters":63},{"name":"Helaman","chapters":16},
            {"name":"3 Nephi","chapters":30},{"name":"4 Nephi","chapters":1},
            {"name":"Mormon","chapters":9},{"name":"Ether","chapters":15},
            {"name":"Moroni","chapters":10}
        ]
    },
    {
        "key": "nt", "name": "Bible - New Testament", "books": [
            {"name":"Matthew","chapters":28},{"name":"Mark","chapters":16},
            {"name":"Luke","chapters":24},{"name":"John","chapters":21},
            {"name":"Acts","chapters":28},{"name":"Romans","chapters":16}
        ]
    }
]

# Load talks from CSV
TALKS = []
def load_talks():
    global TALKS
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'talks.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                TALKS = list(reader)
    except Exception as e:
        print(f"Error loading talks: {e}")
        TALKS = []

load_talks()

# Routes
@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"<h1>Error loading template</h1><p>{str(e)}</p>", 500

@app.route('/api/canons')
def get_canons():
    return jsonify(CANONS)

@app.route('/api/talks')
def get_talks():
    return jsonify(TALKS)

@app.route('/api/health')
def health():
    return jsonify({
        "status": "ok",
        "openai_configured": client is not None,
        "talks_loaded": len(TALKS)
    })

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
