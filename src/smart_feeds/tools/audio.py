import os
import logging
import tempfile
import httpx
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

def transcribe_audio_url(url: str) -> str:
    """
    Downloads an audio file from a URL and transcribes it using Gemini.
    """
    logger.info(f"Transcribing audio from: {url}")
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "Error: GOOGLE_API_KEY not set."

    client = genai.Client(api_key=api_key)

    try:
        # Download audio to a temp file
        # We need a temp file because the API uploads from file
        suffix = ".mp3" # default to mp3, but maybe we should detect from header or url
        if url.endswith(".m4a"):
            suffix = ".m4a"
        elif url.endswith(".wav"):
            suffix = ".wav"
            
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_audio:
            temp_path = temp_audio.name
            
            # httpx automatically respects HTTP_PROXY and HTTPS_PROXY environment variables
            
            with httpx.Client(timeout=300.0, follow_redirects=True) as http_client:
                with http_client.stream("GET", url) as response:
                    response.raise_for_status()
                    for chunk in response.iter_bytes():
                        temp_audio.write(chunk)
        
        logger.info(f"Audio downloaded to {temp_path}, uploading to Gemini...")
        
        # Upload to Gemini (using the File API)
        # The genai library handles this.
        # Check documentation for file upload: client.files.upload(path=...)

        # 1. Upload file
        uploaded_file = client.files.upload(path=temp_path)
        
        # 2. Generate content
        # We use a model that supports audio, e.g. gemini-2.0-flash
        model_id = os.environ.get("MODEL_ID", "gemini-2.0-flash")
        
        prompt = "Transcribe this audio file. Extract the main topics and a detailed summary of the conversation."
        
        response = client.models.generate_content(
            model=model_id,
            contents=[prompt, uploaded_file]
        )
        
        # Clean up
        os.unlink(temp_path)
        # Ideally we should also delete the file from Gemini storage to avoid clutter, 
        # check if client.files.delete is available or if it auto-cleanups (usually not).
        # But for now, let's just return the text.
        
        return response.text

    except Exception as e:
        logger.error(f"Error transcribing {url}: {e}")
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        return f"Error transcribing audio: {str(e)}"
