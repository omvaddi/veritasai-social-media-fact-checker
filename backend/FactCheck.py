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
import requests
from dotenv import load_dotenv
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

load_dotenv()

tmpdir = tempfile.mkdtemp()
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

nlp.add_pipe(
    "fastcoref", 
    config={'model_architecture': 'LingMessCoref', 'model_path': 'biu-nlp/lingmess-coref', 'device': 'cpu'}
)

def download_audio(url: str) -> str:
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        downloaded_path = ydl.prepare_filename(info)
        return downloaded_path


def transcribe(path: str) -> str:
    client = OpenAI()

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

    clustering = hdbscan.HDBSCAN(min_cluster_size=2, metric = 'euclidean')

    labels = clustering.fit_predict(embeddings)
    clusters = {}

    if not any(label != -1 for label in labels):
        return [sentences]

    for claim, label in zip(sentences, labels):
        if label == -1:
            continue
        clusters.setdefault(label, []).append(claim)

    return list(clusters.values())





def detectClaims(clusters: list) -> dict:

    client = OpenAI()

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

    For the sentence(s) provided, do the following:
    1. Identify a **main theme**.
    2. Extract any **claims that are verifiable by external sources** (e.g., studies, laws, statistics, expert consensus).
    3. Ignore: 
        - Subjective opinions (e.g., what someone feels, prefers, or things is fair).
        - Vague statements or advise without testable content.
        - Personal anecdotes or private experiences unless it's a public figure making them. 
    4. No claim should be just a rephrasal of a previous claim.
    5. If a claim is exxagerated, rephrase is into a neutral, fact-checkable version.
    6. Only include topics that contain at least one claim. Do not include any topic key if its "claims" list is empty.
    
    Return the result in this JSON format:
    {
        "theme": "Short theme",
        "claims": [
        { "id": 1, "text": claim 1 }, 
        { "id": 2, "text": claim 2 },
        { etc... }
        ]
    }

    If there are no fact-checkable claims, return exactly this: SKIP
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

    client = OpenAI()

    system_prompt = """
    You are an AI helping build a fact-checking tool.
    You will be given:
        - A claim
        - A list of Google search result snippets in JSON format

    The search results will be given in a json format as follows:
    [
        { "Article #": 1, "title": Title of article #1, "link": Link to article #1, "snippet": Snippet of article #1 },
        { "Article #": 2, "title": Title of article #2, "link": Link to article #2, "snippet": Snippet of article #2 },
        { etc... }
    ]

    Your job:
    1. Analyze whether the **claim is supported or contradicted** by the snippets.
    2. Make a decision based **only on the evidence provided** (do not guess beyond it).
    3. If some evidence clearly supports or refutes the claim, say so.
    4. If snippets do not provide enough relevent or clear evidence, choose "Indecisive".


    Return the result in this JSON format:
    {
        "verdict": "True" | "Likely True" | "Likely False" | "False" | "Indecisive" | True (Outdated), // try not to output indecisive but do it if the claim is an opinion (ex: makes comments on what is fair or just) or there is not enough evidence.
        "explanation": "A brief explanation of your reasoning. Try to use quotes and refer to sources by their name mentioning them. Do not mention the fact you are reading from sources/snippets/searches just say things as facts. Additionally if there is no relevent evidence simply say that.",
        "links": [
            "https://example.com/article1",
            "https://example.com/article2"
        ] // Use links are related to the verdict even if it is indecisive. Try to output 3 links, it is OK to output less.
    }
    """

    user_prompt = """
    Here is the claim: %s

    Here are the search results: %s 
    """


    for topic_key in JSON.keys():
        updatedClaims = []
        claim_id = 1
        for claim in JSON[topic_key]["claims"]:

            search_query = claim["text"]

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
                    {"role": "user", "content": user_prompt  % (search_query, evStr)}
                ],
                response_format = {"type" : "json_object"}
            )

            evInterpJSON = response.choices[0].message.content

            evInterp = json.loads(evInterpJSON)


            updatedClaim = {
                "id": claim["id"],
                "text": claim["text"],
                "verdict" : evInterp["verdict"],
                "explanation": evInterp["explanation"],
                "links": evInterp["links"]
            }

            updatedClaims.append(updatedClaim)

        JSON[topic_key]["claims"] = updatedClaims

    return JSON


def factChecker(link: str) -> dict:
    path = download_audio(link)
    transcription = transcribe(path) 
    coref_ = coref(transcription)
    corefSentences = splitSentences(coref_)
    clusters = cluster(corefSentences)
    claims = detectClaims(clusters)
    verdict = searchAndAnalyzeEvidence(claims)
    print(json.dumps(verdict, indent = 4))
    os.remove(path)
    return verdict


app = Flask(__name__)
CORS(app)

@app.route("/", methods=['POST'])
def fact_check():
    data = request.get_json()
    link = data.get("video_url")
    result = factChecker(link)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
