import os
import tempfile
import time
import urllib.request
from pathlib import Path

import torch
import soundfile as sf

from transformers import pipeline as hf_pipeline
from kokoro import KPipeline

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage


# =========================
# CONFIG
# =========================

TWILIO_ACCOUNT_SID = "YOUR_SID"
TWILIO_AUTH_TOKEN = "YOUR_TOKEN"

GROQ_API_KEY = "YOUR_GROQ_KEY"
GROQ_MODEL = "llama-3.3-70b-versatile"

BASE_DIR = Path(__file__).resolve().parent.parent

AUDIO_DIR = BASE_DIR / "media" / "tts_audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOAD MODELS
# =========================

print("Loading Whisper...")

stt = hf_pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-small",
    device=0 if torch.cuda.is_available() else -1,
)

print("Loading Kokoro...")

tts = KPipeline(lang_code='b')

print("Loading Groq...")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL
)

SYSTEM_PROMPT = """
You are a helpful voice assistant.
Keep answers short.
"""


# =========================
# ASK LLM
# =========================

def ask_llm(user_text):

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_text),
    ]

    response = llm.invoke(messages)

    return response.content.strip()


# =========================
# TTS
# =========================

def synthesize(text):

    out = AUDIO_DIR / f"reply_{int(time.time()*1000)}.wav"

    generator = tts(text, voice="am_fenrir")

    for gs, ps, audio in generator:
        sf.write(str(out), audio, 24000)
        break

    return out.name


# =========================
# STT
# =========================

def transcribe_audio(audio_url):

    tmp = tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    )

    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()

    password_mgr.add_password(
        None,
        audio_url,
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN
    )

    opener = urllib.request.build_opener(
        urllib.request.HTTPBasicAuthHandler(password_mgr)
    )

    with opener.open(audio_url + ".wav") as resp:
        tmp.write(resp.read())

    tmp.flush()

    result = stt(tmp.name)

    os.unlink(tmp.name)

    return result["text"].strip()