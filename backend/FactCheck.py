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
import requests
from dotenv import load_dotenv
import json

warnings.filterwarnings("ignore", category = FutureWarning)

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
    2. Extract any **fact-checkable claims** -- things that can be verified through trusted sources or a google search. 
    3. Do not include anything the speaker says about their personal lives unless they are a public figure and their claims can be fact checked. 
    5. Be aware some claims may be hyperbolic so rephrase them into balanced claims (ex: you need to cut out sugars for clear skin -> cutting out sugar helps with clear skin).
    4. Ignore all vague, subjective, opinion-based, and non-factual content. It is OK if no claims are found.

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
    load_dotenv()
    googlecloud_api_key = os.getenv("GOOGLECLOUD_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")

    url = 'https://www.googleapis.com/customsearch/v1'

    client = OpenAI()

    system_prompt = """You are helping build a fact checking website.
    You will be provided a claim along with google search results for that claim.
    Your job is to decide whether the search results support or reject the claim.
    The search results will be given in a json format as follows:
    [
        { "Article #": 1, "title": Title of article #1, "link": Link to article #1, "snippet": Snippet of article #1 },
        { "Article #": 2, "title": Title of article #2, "link": Link to article #2, "snippet": Snippet of article #2 },
        { etc... }
    ]

    Only base your answer on the information provided. Do not use any external or prior knowledge.
    In your explanation do not reference that you have looked at articles just quote specific ones if needed.
    Make it seem as though you have an answer and are not looking at snippets.
    Return the result in this JSON format:
    {
        "verdict": "True" | "False" | "Indecisive", // output indecisive if the claim is an opinion (ex: makes comments on what is fair or just) or there is not enough evidence.
        "explanation": "A brief explanation of your reasoning.",
        "links": [
            "https://example.com/article1",
            "https://example.com/article2"
        ] // Use links that support the verdict. Output no more than three links.
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






if __name__ == "__main__":
    test_url = "https://www.instagram.com/reel/DF9HjexvbDM/?igsh=MTViNG5zdmF0YnJ3bA=="

    mp3_path = download_audio(test_url)
    transcription = transcribe(mp3_path) 
    coref_ = coref(transcription)
    corefSentences = splitSentences(coref_)
    clusters = cluster(corefSentences)
    claims = detectClaims(clusters)

    verdict = searchAndAnalyzeEvidence(claims)
    print(json.dumps(verdict, indent = 4))



    os.remove(mp3_path)