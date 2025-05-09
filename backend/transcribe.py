import yt_dlp
import tempfile
import os
from openai import OpenAI
from transformers import pipeline
from fastcoref import spacy_component
import spacy


OpenAI.api_key = "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"

tmpdir = tempfile.mkdtemp()

def download_audio(url: str) -> str:
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        downloaded_path = ydl.prepare_filename(info)
        mp3_path = os.path.splitext(downloaded_path)[0]+'.mp3'
        return mp3_path
        
def transcribe(mp3_path: str) -> str:
    client = OpenAI()

    with open(mp3_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
            language="en"
        )
        
        return transcription.text
    
def coref(transcription: str) -> str:
    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe(
        "fastcoref", 
        config={'model_architecture': 'LingMessCoref', 'model_path': 'biu-nlp/lingmess-coref', 'device': 'cpu'}
    )

    doc = nlp(
        transcription,
        component_cfg={"fastcoref": {'resolve_text': True}}
    )

    return(doc._.resolved_text)
        
if __name__ == "__main__":
    test_url = "https://www.youtube.com/shorts/RT3GI1vEAdc"

    mp3_path = download_audio(test_url)
    transcription = transcribe(mp3_path) 
    coref_ = coref(transcription)
    print(transcription)
    print(coref_)
    os.remove(mp3_path)