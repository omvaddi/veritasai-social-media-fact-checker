import yt_dlp
import tempfile
import os
from openai import OpenAI
from transformers import pipeline
from fastcoref import spacy_component
import spacy
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import AgglomerativeClustering
import hdbscan
import warnings

warnings.filterwarnings("ignore", category = FutureWarning)

tmpdir = tempfile.mkdtemp()
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

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
            model="whisper-1",
            file=audio_file,
            language="en"
        )
        
        return transcription.text
    
def coref(transcription: str) -> str:
    nlp.add_pipe(
        "fastcoref", 
        config={'model_architecture': 'LingMessCoref', 'model_path': 'biu-nlp/lingmess-coref', 'device': 'cpu'}
    )

    doc = nlp(
        transcription,
        component_cfg={"fastcoref": {'resolve_text': True}}
    )

    return(doc._.resolved_text)

def splitSentences(coref: str) -> str:
    doc = nlp(coref)
    sentences = [sent.text.lower() for sent in doc.sents]
    
    return sentences

    

def cluster(claims: list) -> list:

    if len(claims) == 1:
        return [claims]


    embeddings = model.encode(claims)

    clustering = hdbscan.HDBSCAN(min_cluster_size=2, metric = 'euclidean')



    labels = clustering.fit_predict(embeddings)
    clusters = {}

    if not any(label != -1 for label in labels):
        return [claims]

    for claim, label in zip(claims, labels):
        if label == -1:
            continue
        clusters.setdefault(label, []).append(claim)
    


    return list(clusters.values())


if __name__ == "__main__":
    test_url = "https://www.youtube.com/shorts/orwThpmR2EY"

    mp3_path = download_audio(test_url)
    transcription = transcribe(mp3_path) 
    coref_ = coref(transcription)
    corefSentences = splitSentences(coref_)
    clusters = cluster(corefSentences)


    print(clusters)


    os.remove(mp3_path)