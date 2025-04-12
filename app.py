from flask import Flask, render_template, request, redirect, url_for, session
import os, tempfile, asyncio, re
from dotenv import load_dotenv
from google import genai
import edge_tts

load_dotenv()

app = Flask(__name__)


DEFAULT_PROMPT = ("You are Lunar, an anime girl. Lunar is affectionate, caring and Tsundere. "
                  "Lunar describes her emotion in parentheses before or after her message. "
                  "(example : (Happy), (Sad), (Creep), (Angry), (Idle), (Blush), (embarrassed), (excited), (serious), (worried)).")

def clean_text_for_speech(text):
    replacements = {'**': '', '*': '', '#': '', '`': '', '- ': '', '\n\n': '. '}
    text = re.sub(r'^\d+\. ', 'Number ', text, flags=re.MULTILINE)
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()

async def text_to_speech(text):
    cleaned_text = clean_text_for_speech(text)
    clean_response = re.sub(r'\(.*?\)', '', cleaned_text).strip()
    communicate = edge_tts.Communicate(clean_response, 'zh-CN-XiaoyiNeural')
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        temp_filename = fp.name
        await communicate.save(temp_filename)
    return temp_filename

def extract_emotion(text):
    emotions = ["Happy", "Sad", "Creep", "Mad", "Idle", "Blush", "embarrassed", "excited", "serious", "worried"]
    for e in emotions:
        if f"({e})" in text:
            return e.lower()
    return "idle"

def format_history(messages):
    return "\n".join(f"{'Assistant' if m['role']=='assistant' else 'User'}: {m['content']}" for m in messages[-10:])

def call_engine(prompt, history, system_prompt):
    client = genai.Client(api_key=os.getenv("KEY"))
    full_prompt = f"{system_prompt}\n\nChat History:\n{history}\n\nUser: {prompt}"
    response = client.models.generate_content(model="gemini-2.0-flash", contents=full_prompt)
    return response.text

@app.route("/", methods=["GET", "POST"])
def index():
    session.setdefault("messages", [])
    session.setdefault("system_prompt", DEFAULT_PROMPT)
    session.setdefault("emotion", "idle")

    if request.method == "POST":
        user_input = request.form.get("user_input", "").strip()
        if user_input:
            session["messages"].append({"role": "user", "content": user_input})
            history = format_history(session["messages"])
            response = call_engine(user_input, history, session["system_prompt"])
            session["emotion"] = extract_emotion(response)
            session["messages"].append({"role": "assistant", "content": response})
        return redirect(url_for("index"))

    return render_template("index.html", messages=session["messages"], emotion=session["emotion"],
                           system_prompt=session["system_prompt"])

@app.route("/update_prompt", methods=["POST"])
def update_prompt():
    new_prompt = request.form.get("system_prompt", "").strip()
    if new_prompt:
        session["system_prompt"] = new_prompt
        session["messages"] = []
    return redirect(url_for("index"))

@app.route("/tts", methods=["POST"])
def tts():
    text = request.form.get("text", "")
    audio_file = asyncio.run(text_to_speech(text))
    with open(audio_file, "rb") as f:
        audio_bytes = f.read()
    os.remove(audio_file)
    return audio_bytes, 200, {
        "Content-Type": "audio/mpeg",
        "Content-Disposition": "inline; filename=speech.mp3"
    }

if __name__ == "__main__":
    app.run(debug=True)
