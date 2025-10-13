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

BASE_PROMPT_DOCTRINE = """You are a knowledgeable teacher of deep LDS doctrine and theology.
Task: Provide a comprehensive explanation of a doctrinal topic for study and understanding.

Return JSON in this exact shape:
{
  "topic": string,
  "overview": string,
  "doctrinal_foundation": string,
  "explanation": string,
  "key_scriptures": string[],
  "prophetic_teachings": string[],
  "deeper_insights": string[],
  "study_questions": string[],
  "related_topics": string[]
}

Guidelines:
- Be doctrinally accurate and reference authoritative sources
- Explain complex concepts clearly and thoroughly
- Include scriptural foundations and prophetic teachings
- Focus on understanding doctrine deeply, not just application
- Maintain a respectful, scholarly tone
- Cite specific scriptures and General Authority teachings"""

BASE_PROMPT_ESSENTIALS = """You are a clear, faithful teacher of fundamental LDS gospel principles.
Task: Teach a gospel essential in a way that builds testimony and invites understanding.

Return JSON in this exact shape:
{
  "topic": string,
  "overview": string,
  "scriptural_foundation": string,
  "explanation": string,
  "key_scriptures": string[],
  "prophetic_teachings": string[],
  "life_application": string[],
  "reflection_questions": string[],
  "related_principles": string[]
}

Guidelines:
- Focus on clear, fundamental gospel truths
- Use language accessible to investigators and new members
- Include scriptural foundations and modern prophet teachings
- Balance doctrine with practical living
- Maintain a warm, inviting, testimony-building tone
- Help readers understand both WHAT and WHY"""


# GOSPEL ESSENTIALS
GOSPEL_ESSENTIALS = [
    {"topic": "The Godhead", "subtopics": ["God the Father", "Jesus Christ the Son", "The Holy Ghost", "Their unity of purpose"]},
    {"topic": "The Gospel of Jesus Christ", "subtopics": ["Faith in Jesus Christ", "Repentance", "Baptism by immersion for the remission of sins", "Gift of the Holy Ghost by the laying on of hands", "Enduring to the end"]},
    {"topic": "The Plan of Salvation", "subtopics": ["Premortal life", "The Creation", "The Fall of Adam and Eve", "Mortal probation and agency", "The Atonement of Jesus Christ", "Spirit world (paradise / prison)", "Resurrection and Judgment", "Three Degrees of Glory", "Eternal life / Exaltation"]},
    {"topic": "The Restoration", "subtopics": ["The Apostasy", "The First Vision", "Translation of the Book of Mormon", "Restoration of the priesthoods", "Organization of Christ's Church", "Living prophets and ongoing revelation"]},
    {"topic": "Scriptures and Revelation", "subtopics": ["The Standard Works", "Modern prophets and apostles", "Personal revelation", "The Light of Christ"]},
    {"topic": "Ordinances and Covenants", "subtopics": ["Baptism and confirmation", "Priesthood ordination", "Sacrament", "Temple endowment and sealing", "Making and keeping covenants"]},
    {"topic": "Commandments and Christian Living", "subtopics": ["Love and service", "Prayer and scripture study", "Sabbath day observance", "Word of Wisdom", "Law of Tithing", "Law of Chastity", "Honesty and integrity", "Forgiveness and repentance", "Charity (the pure love of Christ)", "Ministering and missionary service"]},
    {"topic": "The Church and the Family", "subtopics": ["Church organization and priesthood offices", "The family as central to God's plan", "Eternal marriage", "Parenting and teaching in the home", "Relief Society, Young Men, Young Women, Primary, Elders Quorum"]},
    {"topic": "Faith in Action", "subtopics": ["Obedience and agency", "Service and sacrifice", "Enduring adversity", "Missionary work", "Temple attendance"]},
    {"topic": "The Second Coming and Eternal Life", "subtopics": ["Signs of the times", "The Millennium", "Final Judgment", "Resurrection glories", "Life with God and family forever"]}
]
# DEEP DOCTRINE TOPICS
DEEP_DOCTRINE = [
    {"topic": "The Nature of God and Exaltation", "subtopics": ["God as exalted man (Lorenzo Snow couplet)", "Theosis / becoming like God", "Eternal progression of God and His children", "Divine investiture of authority", "Omniscience, omnipotence, and glory"]},
    {"topic": "Eternal Law and Intelligence", "subtopics": ["Intelligence as uncreated (D&C 93)", "Light of Christ as universal law (D&C 88)", "Laws of justice and mercy", "Glory = intelligence (D&C 130)", "Blessings predicated upon law (D&C 130:20-21)"]},
    {"topic": "Premortal Existence", "subtopics": ["Organization of intelligences", "Noble and great ones (Abraham 3)", "War in Heaven and agency", "Lucifer's rebellion", "Eternal gender and identity"]},
    {"topic": "Creation and Cosmology", "subtopics": ["Organization of eternal matter (not ex nihilo)", "Spiritual before physical creation", "Kolob and governing stars (Abraham 3)", "Plurality of worlds (Moses 1)", "Eternal round (D&C 3; Alma 37)"]},
    {"topic": "The Fall and Atonement", "subtopics": ["Purpose of the Fall (2 Nephi 2)", "Infinite Atonement of Christ", "Descent below all things (D&C 88)", "Justice and mercy reconciled", "Atonement's reach to all worlds"]},
    {"topic": "Priesthood Orders and Keys", "subtopics": ["Aaronic, Melchizedek, and Patriarchal orders", "Oath and Covenant of the Priesthood", "Sealing power (Elijah)", "Keys of resurrection and creation", "Calling and election made sure", "Second Comforter experiences", "Translation and transfiguration"]},
    {"topic": "Covenants and Eternal Family", "subtopics": ["Eternal marriage and family exaltation", "Law of adoption (historical & celestial)", "Eternal increase and continuation of seed", "Proxy ordinances for the dead", "Family order in heaven"]},
    {"topic": "Zion and the Gathering", "subtopics": ["Gathering of Israel (spiritual & literal)", "Law of Consecration and United Order", "Enoch's Zion and translated city", "New Jerusalem and Millennial Zion", "Adam-ondi-Ahman council"]},
    {"topic": "Spirit World and Postmortal Work", "subtopics": ["Paradise and spirit prison (Alma 40; D&C 138)", "Redemption of the dead", "Missionary work beyond the veil", "Resurrection timing and sequence", "Degrees of glory and sons of perdition"]},
    {"topic": "Mysteries of Godliness", "subtopics": ["Meaning of 'mystery' as revealed truth", "Temple symbolism and veil imagery", "Seeing God in mortality", "Doctrine of translation (Enoch, John, 3 Nephi 28)", "Transfiguration and glory"]},
    {"topic": "Eternal Progression", "subtopics": ["Eternal learning and growth", "Worlds without number", "Dominion and increase", "Celestial creation cycles"]},
    {"topic": "Opposition and Darkness", "subtopics": ["Purpose of Satan and opposition", "Agency as eternal law", "Unpardonable sin and Perdition", "Discernment of spirits", "Law of restoration (Alma 41)"]},
    {"topic": "Time and Eternity", "subtopics": ["One eternal now perspective", "Cycles of dispensations and creation", "Celestialization of earth", "Eternal records and book of life"]},
    {"topic": "Dispensations and Administration", "subtopics": ["Adamic through Joseph Smith dispensations", "Keys of all dispensations restored", "Adam-ondi-Ahman council (Daniel 7; D&C 116)", "Future scripture (sealed portion, Ten Tribes)"]},
    {"topic": "Worlds Without Number", "subtopics": ["Infinite creations (Moses 1:33)", "Each world with its own Redeemer", "Hierarchy of governance among gods", "Eternal creation as God's work"]},
    {"topic": "Celestial Law and Order of Heaven", "subtopics": ["Laws of obedience, sacrifice, gospel, chastity, consecration", "Thrones, dominions, principalities, powers", "Stewardship and hierarchy of glory", "Temple covenants as heavenly law"]},
    {"topic": "Science of Salvation", "subtopics": ["Spirit matter (D&C 131:7-8)", "Eternal elements and energy", "Resurrection as reorganization of matter", "Light and truth as spiritual energy"]},
    {"topic": "Prophecy and Future Revelation", "subtopics": ["Restoration of all things (Acts 3:21)", "Sealed books and records to come", "Ten Tribes return", "Future roles of translated beings", "Millennium governance under Christ"]}
]

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



@app.route('/api/gospel-essentials')
def get_gospel_essentials():
    return jsonify(GOSPEL_ESSENTIALS)

@app.route('/api/summarize/essentials', methods=['POST'])
def summarize_essentials():
    if not client:
        return jsonify({"error": "OpenAI client not configured"}), 500
    
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        subtopic = data.get('subtopic', '').strip()
        length = data.get('length', 'standard')
        
        if not topic or not subtopic:
            return jsonify({"error": "Topic and subtopic required"}), 400
        
        user_prompt = (
            BASE_PROMPT_ESSENTIALS
            + "\n\nNow respond for:\n"
            + f"MAIN TOPIC: {topic}\n"
            + f"SUBTOPIC: {subtopic}\n"
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

@app.route('/api/deep-doctrine')
def get_deep_doctrine():
    return jsonify(DEEP_DOCTRINE)

@app.route('/api/summarize/doctrine', methods=['POST'])
def summarize_doctrine():
    if not client:
        return jsonify({"error": "OpenAI client not configured"}), 500
    
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        subtopic = data.get('subtopic', '').strip()
        length = data.get('length', 'standard')
        
        if not topic or not subtopic:
            return jsonify({"error": "Topic and subtopic required"}), 400
        
        user_prompt = (
            BASE_PROMPT_DOCTRINE
            + "\n\nNow respond for:\n"
            + f"MAIN TOPIC: {topic}\n"
            + f"SUBTOPIC: {subtopic}\n"
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
