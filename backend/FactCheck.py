import yt_dlp
import tempfile
import os
from openai import OpenAI
from transformers import pipeline
from fastcoref import spacy_component
import spacy
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import normalize
import hdbscan
import requests
from dotenv import load_dotenv
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import urlparse
import shutil
from bertopic import BERTopic
import umap




load_dotenv()


openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)


tmpdir = tempfile.mkdtemp()
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

cache = {}

nlp.add_pipe(
    "fastcoref", 
    config={'model_architecture': 'LingMessCoref', 'model_path': 'biu-nlp/lingmess-coref', 'device': 'cpu'}
)

def download_audio(url: str) -> str:
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '0',
        }]
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        downloaded_path = ydl.prepare_filename(info)
        return os.path.splitext(downloaded_path)[0] + ".wav"


def transcribe(path: str) -> str:

    with open(path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="en"
        )
        
        return transcription.text
    
def coref(transcription: str) -> str:
    doc = nlp(
        transcription,
        component_cfg={"fastcoref": {'resolve_text': True}}
    )

    return(doc._.resolved_text)

def splitSentences(coref: str) -> str:
    doc = nlp(coref)
    sentences = [sent.text.lower() for sent in doc.sents]
    
    return sentences

    
def cluster(sentences: list) -> list:
    
    if len(sentences) == 1:
        return [sentences]

    embeddings = model.encode(sentences)
    embeddings = normalize(embeddings)


    if len(sentences) < 10:
        hdbscan_model = hdbscan.HDBSCAN(min_cluster_size=2, metric = 'euclidean')
        labels = hdbscan_model.fit_predict(embeddings)
    else:
        hdbscan_model = hdbscan.HDBSCAN(min_cluster_size=2, min_samples=1, prediction_data=True)
        umap_model = umap.UMAP(n_neighbors=5, n_components=2, min_dist=0.0, metric='cosine')
        topic_model = BERTopic(hdbscan_model=hdbscan_model, umap_model=umap_model, calculate_probabilities=True)
    
        labels, _ = topic_model.fit_transform(sentences)
    

    clusters = {}

    for claim, label in zip(sentences, labels):
        clusters.setdefault(label, []).append(claim)

    result = list(clusters.values())
    print(result)

    print('\n\n\n')

    return result


def detectClaims(clusters: list) -> dict:


    groupClusters = [""] * len(clusters)

    text = ""

    for i in range(len(clusters)):
        for j in range(len(clusters[i])):
            text = text + clusters[i][j] + " "
            groupClusters[i] += clusters[i][j] + " "
        groupClusters[i] = groupClusters[i][:-1]
    text = text[:-1]

    system_prompt = """
    You are helping extract verifiable claims from social media videos.
    I will give you the full transcipt for contextual purposes but just work with the sentences I want you to analyze.
    These sentences may not be coherent together but they all follow a theme.

    Instructions:
    1. Identify a **specific main theme** of the sentence group.
    2. Extract any **verifiable, specific, non-redundant factual claims**.
    3. Ignore: 
        - Subjective opinions (e.g., what someone feels, prefers, or thinks is fair)
        - Vague or anecdotal statements including statements without context
        - Private experiences (unless made by a public figure)
        - Claims relying solely on visuals or unclear references
    4. Each claim must be **specific, concise**, and **not just a rewording of another**.
    5. If a claim is exxagerated or speculative, rephrase it into a neutral, fact-checkable version.
    6. For each claim, write a **searchable question** with:
        - No stopwords
        - Neutral tone
        - Full relevent context
        - Keywords useful for Google search
        - Include a request for statistics or numerical data if relevent
    
    Return the result in this JSON format:
    {
        "theme": "Short theme",
        "claims": [
        { "id": 1, "text": claim 1, "query": query 1 }, 
        ...
        ]
    }

    If there are no claims, return exactly this: SKIP
    """

    user_prompt = """
    The full transcript (to be used for context only) is as follow: %s

    The sentence(s) to analyze are: %s 
    """

    JSON = {}

    for i in range(len(groupClusters)):

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt  % (text, groupClusters[i])}
            ],
            response_format = {"type" : "json_object"}
        )

        result = response.choices[0].message.content

        if result == "SKIP":
            continue

        resJSON = json.loads(result)

        JSON["Topic #" + str(i + 1)] = resJSON

    return JSON


def searchAndAnalyzeEvidence(JSON: dict) -> dict:
    googlecloud_api_key = os.getenv("GOOGLECLOUD_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")

    url = 'https://www.googleapis.com/customsearch/v1'


    system_prompt = """
    You are an AI fact-checker. You will recieve:
        - A factual claim
        - A list of Google search result snippets (titles, links, snippets)

    Your task:
    1. Determine whether the **claim is supported or contradicted** by the snippets.
    2. Base your judgement **primarily on the snippets** but you may make **basic, explicit inferences of simple calculations** when logically justified by the data.
    3. Look for **consistent patterns** across multiple sources.
    4. If the snippets do not supply clear or relevent evidence, return **"Insufficient Evidence"**

    Return the result in this JSON format:
    {
        "verdict": | "True" // fully supported
                   | "Likely True" // mostly supported, minor uncertainty
                   | "Likely False" // most contradicted, minor nuance
                   | "False" // clearly disproven
                   | "Insufficent Evidence" // not enough evidence or too mixed
                   ,
        "explanation": "A brief explanation of your reasoning. Try to use quotes and refer to sources by their name mentioning them. Do not mention the fact you are reading from sources/snippets/searches just say things as facts. Additionally if there is no relevent evidence simply say that.",
        "links": [
            "https://example.com/article1",
            ...
            // up to three links that best illustrate your verdict
        ]
    }
    """

    user_prompt = """
    Here is the claim: %s

    Here are the search results: %s 
    """

    topic_keys = list(JSON.keys())

    for topic_key in topic_keys:
        if not JSON[topic_key]["claims"]:
            del JSON[topic_key]
            continue


        updatedClaims = []


        for claim in JSON[topic_key]["claims"]:

            search_query = claim["query"]

            params = {
                'q': search_query,
                'key': googlecloud_api_key,
                'cx': search_engine_id
            }

            evidence = []

            response = requests.get(url, params=params)
            results = response.json().get("items", [])
            for i in range(len(results)):
                piece = {}
                piece["Article #"] = i + 1
                piece["title"] = results[i].get("title")
                piece["link"] = results[i].get("link")
                piece["snippet"] = results[i].get("snippet")
                evidence.append(piece)

            evStr = json.dumps(evidence, indent = 2)

            response = client.chat.completions.create(
                model="gpt-4.1",
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt  % (claim["text"], evStr)}
                ],
                response_format = {"type" : "json_object"}
            )

            evInterpJSON = response.choices[0].message.content

            evInterp = json.loads(evInterpJSON)

            updatedClaim = {
                "id": claim["id"],
                "text": claim["text"],
                "query": claim["query"],
                "verdict" : evInterp["verdict"],
                "explanation": evInterp["explanation"],
                "links": evInterp["links"]
            }

            updatedClaims.append(updatedClaim)

        JSON[topic_key]["claims"] = updatedClaims

    return JSON


def factChecker(link: str) -> dict:
    if link in cache.keys():
        verdict = cache[link]
    else:
        path = download_audio(link)
        transcription = transcribe(path) 
        coref_ = coref(transcription)
        corefSentences = splitSentences(coref_)
        clusters = cluster(corefSentences)
        claims = detectClaims(clusters)
        verdict = searchAndAnalyzeEvidence(claims)
        print(json.dumps(verdict, indent = 4))
        shutil.rmtree(tmpdir)
        cache[link] = verdict
    return verdict

def is_valid_url(link):
    result = urlparse(link)
    if not all([result.scheme in ('http', 'https'), result.netloc]):
        return False
    
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            ydl.extract_info(link, download=False)
            return True
    except Exception as e:
        return False

app = Flask(__name__)
CORS(app)

@app.route("/", methods=['POST'])
def fact_check():
    data = request.get_json()
    link = data.get("video_url")
    if not link or not is_valid_url(link):
        print(link)
        print(is_valid_url(link))
        return jsonify({"error": "Invalid or missing video URL. Please try again."}), 400
    result = factChecker(link)
    if not result:
        return jsonify({"message": "No verifiable claims found."})
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
