
import asyncio
import edge_tts
import streamlit as st
from google import genai
import os
import tempfile


st.set_page_config(layout="wide")
# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

# Default system prompt
DEFAULT_SYSTEM_PROMPT = ("The following is a warm, romantic, and playful conversation between a human and an AI assistant named Lunar. "
                "Lunar is affectionate, caring and Tsundere "
                "Lunar describes her emotion in parentheses before or after her message. (example : (Happy), (Sad), (Creep), (Angry), (Idle), (Blush), (embarrassed), (excited), (serious), (worried)).\n\n")

# Initialize system prompt in session state
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT

if "emotion" not in st.session_state:
        st.session_state.emotion = "idle"

def clean_text_for_speech(text):
    # Remove markdown formatting
    
    replacements = {
        '**': '',  # Bold
        '*': '',   # Italic
        '#': '',   # Headers
        '`': '',   # Code
        '- ': '',  # Unordered lists
        '\n\n': '. ',  # Multiple newlines
    }
    
    # Replace ordered list numbers with spoken text
    import re
    text = re.sub(r'^\d+\. ', 'Number ', text, flags=re.MULTILINE)
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text.strip()

async def text_to_speech(text):
    import re
    cleaned_text = clean_text_for_speech(text)
    clean_response = re.sub(r'\(.*?\)', '', cleaned_text).strip()
    communicate = edge_tts.Communicate(clean_response, 'zh-CN-XiaoyiNeural')
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        temp_filename = fp.name
        await communicate.save(temp_filename)
    return temp_filename

def extract_emotion(response):
    emotions = ["Happy", "Sad", "Creep", "Mad", "Idle", "Blush", "embarrassed", "excited", "serious", "worried"]
    for emotion in emotions:
        if f"({emotion})" in response:
            return emotion.lower()
    return "idle" 
    
# Sidebar for system prompt configuration
with st.sidebar:
    st.title("Chat Settings")
    new_system_prompt = st.text_area("System Prompt", st.session_state.system_prompt, height=150)
    if st.button("Update System Prompt"):
        st.session_state.system_prompt = new_system_prompt
        st.session_state.messages = []  # Clear chat history when prompt changes

def format_chat_history(messages):
    formatted = []
    for msg in messages[-10:]:  # Take last 10 messages (5 exchanges)
        role = "Assistant" if msg["role"] == "assistant" else "User"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)

def engine(prompt):
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    
    # Format chat history
    chat_history = format_chat_history(st.session_state.messages)
    
    # Combine system prompt, chat history, and current prompt
    full_prompt = f"{st.session_state.system_prompt}\n\nChat History:\n{chat_history}\n\nUser: {prompt}"
    
    response = client.models.generate_content(model="gemini-2.0-flash",
                                           contents=str(full_prompt))
    return response.text

st.title("Lunar")

# Accept user input
if prompt := st.chat_input("What do you want to know?"):
    # Keep only last 8 messages before adding new ones (maintains 5 exchanges)
    if len(st.session_state.messages) >= 8:
        st.session_state.messages = st.session_state.messages[-8:]
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Generate AI response
    ai_response = engine(prompt)
    
    st.session_state.emotion = extract_emotion(ai_response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()
    
cols = st.columns([1, 2])
with cols[0]:
        gif_path = f"emotions/{st.session_state.emotion}.gif"
        st.image(gif_path, caption=f"Lunar is {st.session_state.emotion}")
        
with cols[1]:
# Display chat messages from history
    with st.container(border=True):
        st.write(st.session_state.emotion)
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant":
                    # Generate and play audio for assistant responses
                    audio_file = asyncio.run(text_to_speech(message["content"]))
                    st.audio(audio_file, format='audio/mp3')
                    # Clean up temporary audio file
                    os.unlink(audio_file)

