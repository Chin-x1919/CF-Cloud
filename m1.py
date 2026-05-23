import os, uuid, asyncio, edge_tts, re, random, time, threading
from flask import Flask, render_template, request, jsonify, send_from_directory
from llama_cpp import Llama
import whisper

app = Flask(__name__)

# --- CONFIGURATION ---
MODEL_PATH = "./models/phi-2.Q4_K_M.gguf" # model path
MUSIC_FOLDER = "./music"
STATIC_DIR = "static"
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")

for d in [STATIC_DIR, AUDIO_DIR, MUSIC_FOLDER]: os.makedirs(d, exist_ok=True)

print("M1 Edition: Metal Acceleration Active")

# 1. Load System Prompt from MD
def load_system_prompt():
    if os.path.exists("system_prompt.md"):
        with open("system_prompt.md", "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Instruct: You are Latte, a sassy coding waifu."

SYSTEM_PROMPT = load_system_prompt()

# 2. Models Initialization (M1 Optimized)
# n_gpu_layers=-1 is basiclly run on Metal GPU on M1, n_ctx=512 for faster response (adjust as needed)
llm = Llama(model_path=MODEL_PATH, n_gpu_layers=-1, n_ctx=512, verbose=False)
whisper_model = whisper.load_model("tiny") # บน Mac 'tiny' วิ่งไวมาก

# --- AUTO DELETE SYSTEM ---
def cleanup_loop():
    while True:
        now = time.time()
        for f in os.listdir(AUDIO_DIR):
            try:
                if os.stat(os.path.join(AUDIO_DIR, f)).st_mtime < now - 60:
                    os.remove(os.path.join(AUDIO_DIR, f))
            except: pass
        time.sleep(30)
threading.Thread(target=cleanup_loop, daemon=True).start()

# --- CORE LOGIC ---
def get_latte_reply(user_text):
    prompt = f"{SYSTEM_PROMPT}\nUser: {user_text}\nLatte: 【"

    output = llm(
        prompt,
        max_tokens=64,
        stop=["User:", "\n"],
        echo=False,
        temperature=0.8
    )

    reply = output['choices'][0]['text'].strip()
    if not reply.startswith("【"): reply = "【happy1】 " + reply
    return reply

async def generate_voice_async(text, filename):
    clean = re.sub(r'【.*?】|\*.*?\*', '', text).strip()
    path = os.path.join(AUDIO_DIR, filename)
    await edge_tts.Communicate(clean or "Hmm", "en-US-AvaNeural", rate="+15%").save(path)

def chat_logic_internal(user_text):
    music_file = None
    if any(k in user_text.lower() for k in ["music", "play", "song"]):
        songs = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith(('.mp3', '.wav'))]
        if songs: music_file = random.choice(songs)

    reply = get_latte_reply(user_text)
    fname = f"v_{uuid.uuid4().hex[:8]}.mp3"
    asyncio.run(generate_voice_async(reply, fname))

    return {
        "user": user_text, "reply": reply,
        "audio_url": f"/static/audio/{fname}",
        "play_music": f"/music/{music_file}" if music_file else None
    }

# --- ROUTES ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_text = request.json.get("message", "")
    return jsonify(chat_logic_internal(user_text))

@app.route('/voice', methods=['POST'])
def voice():
    audio_in = request.files['file']
    temp_path = os.path.join(AUDIO_DIR, f"temp_{uuid.uuid4().hex}.webm")
    audio_in.save(temp_path)

    if os.path.getsize(temp_path) < 2000:
        if os.path.exists(temp_path): os.remove(temp_path)
        return jsonify({"user": "...", "reply": "【shy1】 Speak up, Senpai!", "audio_url": None})

    try:
        res = whisper_model.transcribe(temp_path)
        return jsonify(chat_logic_internal(res['text'].strip()))
    except Exception:
        return jsonify({"error": "M1 Audio Error"}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

@app.route('/music/<path:filename>')
def serve_music(filename): return send_from_directory(MUSIC_FOLDER, filename)

if __name__ == '__main__':
    print("🚀 M1 LITE AI VERSION: READY ON PORT 5002")
    app.run(host='0.0.0.0', port=5002)
