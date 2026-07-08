import whisper
import os

_model = None

def get_model():
    global _model
    if _model is None:
        print("[VOICE] Loading Whisper 'base' model... This may take a moment.")
        # Load the base model.
        # It requires ffmpeg installed on the host system to process audio.
        _model = whisper.load_model("base")
        print("[VOICE] Whisper model loaded.")
    return _model

def transcribe_audio(file_path: str) -> str:
    """
    Transcribes an audio file using local Whisper.
    Returns the recognized text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
        
    model = get_model()
    # explicitly specify language="ru" to improve accuracy on Russian text
    print(f"[VOICE] Transcribing {file_path}...")
    result = model.transcribe(file_path, language="ru")
    text = result["text"].strip()
    print(f"[VOICE] Transcription result: {text}")
    return text
