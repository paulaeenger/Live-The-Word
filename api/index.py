from flask import Flask, render_template, request, jsonify
import os
import json
import csv

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['PROPAGATE_EXCEPTIONS'] = True

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MODEL = "gpt-4.1-mini-2025-04-14"
except Exception as e:
    client = None
    print(f"OpenAI initialization error: {e}")

# Scripture data - ALL 5 STANDARD WORKS
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
        "key": "ot", "name": "Bible - Old Testament", "books": [
            {"name":"Genesis","chapters":50},{"name":"Exodus","chapters":40},
            {"name":"Leviticus","chapters":27},{"name":"Numbers","chapters":36},
            {"name":"Deuteronomy","chapters":34},{"name":"Joshua","chapters":24},
            {"name":"Judges","chapters":21},{"name":"Ruth","chapters":4},
            {"name":"1 Samuel","chapters":31},{"name":"2 Samuel","chapters":24},
            {"name":"1 Kings","chapters":22},{"name":"2 Kings","chapters":25},
            {"name":"1 Chronicles","chapters":29},{"name":"2 Chronicles","chapters":36},
            {"name":"Ezra","chapters":10},{"name":"Nehemiah","chapters":13},
            {"name":"Esther","chapters":10},{"name":"Job","chapters":42},
            {"name":"Psalms","chapters":150},{"name":"Proverbs","chapters":31},
            {"name":"Ecclesiastes","chapters":12},{"name":"Song of Solomon","chapters":8},
            {"name":"Isaiah","chapters":66},{"name":"Jeremiah","chapters":52},
            {"name":"Lamentations","chapters":5},{"name":"Ezekiel","chapters":48},
            {"name":"Daniel","chapters":12},{"name":"Hosea","chapters":14},
            {"name":"Joel","chapters":3},{"name":"Amos","chapters":9},
            {"name":"Obadiah","chapters":1},{"name":"Jonah","chapters":4},
            {"name":"Micah","chapters":7},{"name":"Nahum","chapters":3},
            {"name":"Habakkuk","chapters":3},{"name":"Zephaniah","chapters":3},
            {"name":"Haggai","chapters":2},{"name":"Zechariah","chapters":14},
            {"name":"Malachi","chapters":4}
        ]
    },
    {
        "key": "nt", "name": "Bible - New Testament", "books": [
            {"name":"Matthew","chapters":28},{"name":"Mark","chapters":16},
            {"name":"Luke","chapters":24},{"name":"John","chapters":21},
            {"name":"Acts","chapters":28},{"name":"Romans","chapters":16},
            {"name":"1 Corinthians","chapters":16},{"name":"2 Corinthians","chapters":13},
            {"name":"Galatians","chapters":6},{"name":"Ephesians","chapters":6},
            {"name":"Philippians","chapters":4},{"name":"Colossians","chapters":4},
            {"name":"1 Thessalonians","chapters":5},{"name":"2 Thessalonians","chapters":3},
            {"name":"1 Timothy","chapters":6},{"name":"2 Timothy","chapters":4},
            {"name":"Titus","chapters":3},{"name":"Philemon","chapters":1},
            {"name":"Hebrews","chapters":13},{"name":"James","chapters":5},
            {"name":"1 Peter","chapters":5},{"name":"2 Peter","chapters":3},
            {"name":"1 John","chapters":5},{"name":"2 John","chapters":1},
            {"name":"3 John","chapters":1},{"name":"Jude","chapters":1},
            {"name":"Revelation","chapters":22}
        ]
    },
    {
        "key":"dc","name":"Doctrine and Covenants","books":[
            {"name":"Doctrine and Covenants","chapters":138}
        ]
    },
    {
        "key":"pgp","name":"Pearl of Great Price","books":[
            {"name":"Moses","chapters":8},
            {"name":"Abraham","chapters":5},
            {"name":"Joseph Smith-Matthew","chapters":1},
            {"name":"Joseph Smith-History","chapters":1},
            {"name":"Articles of Faith","chapters":1}
        ]
    }
]

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

load_talks()

@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route('/api/canons')
def get_canons():
    return jsonify(CANONS)

@app.route('/api/talks')
def get_talks():
    return jsonify(TALKS)

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "openai_configured": client is not None, "talks_loaded": len(TALKS)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
