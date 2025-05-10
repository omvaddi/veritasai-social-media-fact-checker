import yt_dlp
import tempfile
import os
from openai import OpenAI
from transformers import pipeline
from fastcoref import spacy_component
import spacy
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import AgglomerativeClustering


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
            model="whisper-1",
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

def splitSentences(coref: str) -> str:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(coref)
    sentences = [sent.text for sent in doc.sents]
    return sentences

def detectClaims(corefSentences: str) -> list:

    checkpoint = "Sami92/XLM-R-Large-ClaimDetection"
    tokenizer_kwargs = {'padding':True, 'truncation':True, 'max_length':512}
    claimdetection = pipeline("text-classification", model = checkpoint, tokenizer=checkpoint, **tokenizer_kwargs)

    claims = []

    for s in corefSentences:
        sentenceResult = claimdetection(s)
        if sentenceResult[0]['label'] == 'factual':
            print(sentenceResult)
            claims.append(s)


        


    return claims

    

def cluster(claims: list) -> list:

    if len(claims) == 1:
        return [claims]
        

    model = SentenceTransformer('all-MiniLM-L6-v2')


    embeddings = model.encode(claims)

    clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=0.3, metric='cosine', linkage='average')

    labels = clustering.fit_predict(embeddings)
    clusters = {}

    for claim, label in zip(claims, labels):
        clusters.setdefault(label, []).append(claim)

    return list(clusters.values())


if __name__ == "__main__":
    test_url = "https://www.youtube.com/shorts/wl9_C_yRLT4"

    mp3_path = download_audio(test_url)
    transcription = transcribe(mp3_path) 
    coref_ = coref(transcription)
    corefSentences = splitSentences(coref_)
    claims = detectClaims(corefSentences)
    
    print(corefSentences)

    print("\n")
    print(claims)

    # clusters = cluster(claims)
    print("\n")

    # print(clusters)

    os.remove(mp3_path)