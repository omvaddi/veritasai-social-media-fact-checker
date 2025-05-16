import requests
from dotenv import load_dotenv
import os
import json
from openai import OpenAI

JSONStr = """
{
"Topic #1":
{
    "theme": "Definitions and perceptions of women, gender differences, and women's roles in society and sports",
    "claims": [
        {
            "id": 1, "text": "a woman is somebody that can have a baby under certain circumstances"
        },
        {
            "id": 2,
            "text": "men being able to play in women's sports is unfair to women"
        }
    ]
},
"Topic #2":
{
    "theme": "Le",
    "claims": [
        {
            "id": 1, "text": "7 people died during 9/11"
        },
        {
            "id": 2,
            "text": "9/11 occured in 2001"
        }
    ]
}
}
"""


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


data = json.loads(JSONStr)

for topic_key in data.keys():
    updatedClaims = []
    claim_id = 1
    for claim in data[topic_key]["claims"]:

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

    data[topic_key]["claims"] = updatedClaims

print(json.dumps(data, indent = 4))