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

# BASE PROMPTS
BASE_PROMPT_SCRIPTURE = """You are a respectful, non-preachy scripture study guide.
Task: Summarize a scripture chapter (or range) and provide life application for a general audience.

Return JSON in this exact shape:
{
  "reference": string,
  "overview": string,
  "historical_context": string,
  "summary": string,
  "key_verses": string[],
  "themes": string[],
  "life_application": string[],
  "reflection_questions": string[],
  "cross_references": string[]
}

Guidelines:
- Be accurate to the chapter's content. Avoid quoting long passages; paraphrase.
- Keep a warm, invitational tone.
- "Life application" should be practical and specific (habits, small steps, questions).
- If a theme is provided instead of a chapter, recommend 3-5 chapters and summarize the top one.
- If a range is provided (e.g., Mosiah 2-5), weave the arc concisely."""

BASE_PROMPT_TALKS = """You are a helpful conference talk analyzer.
Task: Analyze a General Conference talk and provide insights for personal application.

Return JSON in this exact shape:
{
  "title": string,
  "speaker": string,
  "summary": string,
  "key_messages": string[],
  "quotes": string[],
  "life_application": string[],
  "reflection_questions": string[],
  "related_scriptures": string[]
}

Guidelines:
- Provide accurate summary of the talk's main points
- Extract meaningful quotes (paraphrased, not verbatim)
- Focus on practical application
- Keep a warm, respectful tone"""

def length_guidance(length: str) -> str:
    if length == "brief":
        return "CRITICAL: Keep responses VERY concise. Overview and context: 1-2 sentences each. Summary: 2-3 sentences max. Lists: 2-3 items each."
    if length == "deep":
        return "CRITICAL: Provide COMPREHENSIVE analysis. Overview and context: 3-5 sentences each with rich detail. Summary: 6+ sentences with thorough exploration. Lists: 5-8 items each with depth."
    return "Provide balanced detail. Overview and context: 2-3 sentences each. Summary: 3-5 sentences. Lists: 3-5 items each."

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
        TALKS = []

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

@app.route('/api/talks/search')
def search_talks():
    query = request.args.get('q', '').lower().strip()
    if not query:
        return jsonify(TALKS[:50])
    
    results = []
    for talk in TALKS:
        title = talk.get('title', '').lower()
        speaker = talk.get('speaker', '').lower()
        if query in title or query in speaker:
            results.append(talk)
    
    return jsonify(results[:50])

@app.route('/api/talks/years')
def get_talk_years():
    years = sorted(set(talk.get('year', '') for talk in TALKS if talk.get('year')), reverse=True)
    return jsonify(years)

@app.route('/api/talks/filter')
def filter_talks():
    year = request.args.get('year', '').strip()
    month = request.args.get('month', '').strip()
    
    results = TALKS
    
    if year:
        results = [t for t in results if t.get('year', '') == year]
    
    if month:
        results = [t for t in results if t.get('month', '').lower() == month.lower()]
    
    return jsonify(results[:100])

@app.route('/api/summarize/scripture', methods=['POST'])
def summarize_scripture():
    if not client:
        return jsonify({"error": "OpenAI client not configured"}), 500
    
    try:
        data = request.json
        reference = data.get('reference', '').strip()
        focus = data.get('focus', '').strip()
        length = data.get('length', 'standard')
        
        if not reference:
            return jsonify({"error": "No reference provided"}), 400
        
        user_prompt = (
            BASE_PROMPT_SCRIPTURE
            + "\n\nNow respond for:\n"
            + f"REFERENCE: {reference}\n"
            + f"FOCUS: {focus}\n"
            + f"LENGTH REQUIREMENT: {length_guidance(length)}\n"
            + "AUDIENCE: general\n"
        )
        
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Return only a valid JSON object that matches the schema. No prose outside JSON."},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        text = response.choices[0].message.content
        replacements = {"\u2019":"'","\u201C":'"',"\u201D":'"',"\u2013":"-","\u2014":"-"}
        for k, v in replacements.items():
            text = text.replace(k, v)
        
        result = json.loads(text)
        return jsonify(result)
        
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON from AI: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/summarize/talk', methods=['POST'])
def summarize_talk():
    if not client:
        return jsonify({"error": "OpenAI client not configured"}), 500
    
    try:
        data = request.json
        talk_title = data.get('title', '').strip()
        talk_speaker = data.get('speaker', '').strip()
        focus = data.get('focus', '').strip()
        length = data.get('length', 'standard')
        
        if not talk_title:
            return jsonify({"error": "No talk selected"}), 400
        
        context = f"Talk: {talk_title}\nSpeaker: {talk_speaker}"
        
        user_prompt = (
            BASE_PROMPT_TALKS
            + f"\n\n{context}\n"
            + f"FOCUS: {focus}\n"
            + f"LENGTH REQUIREMENT: {length_guidance(length)}\n"
        )
        
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Return only a valid JSON object that matches the schema. No prose outside JSON."},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        text = response.choices[0].message.content
        replacements = {"\u2019":"'","\u201C":'"',"\u201D":'"',"\u2013":"-","\u2014":"-"}
        for k, v in replacements.items():
            text = text.replace(k, v)
        
        result = json.loads(text)
        return jsonify(result)
        
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON from AI: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({
        "status": "ok", 
        "openai_configured": client is not None, 
        "talks_loaded": len(TALKS)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
