import requests
from dotenv import load_dotenv
import os
import json
from openai import OpenAI


load_dotenv()
googlecloud_api_key = os.getenv("GOOGLECLOUD_API_KEY")
search_engine_id = os.getenv("SEARCH_ENGINE_ID")

search_query = "People who plan on getting pregnant should not take Accutane"

url = 'https://www.googleapis.com/customsearch/v1'

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
print(evStr)

client = OpenAI()

prompt_template = """You are helping build a fact checking website.
You will be provided a claim along with google search results for that claim.
Your job is to decide whether the search results support or reject the claim.
The search results will be given in a json format as follows:
[
    {
    "Article #": 1
    "title": Title of article #1
    "link": Link to article #1
    "snippet": Snipped of article #1
    },
    {
    "Article #": 2
    "title": Title of article #2
    "link": Link to article #2
    "snippet": Snipped of article #2
    },
    {
    etc...
    }
]

Only base your answer on the information provided. Do not use any external or prior knowledge.
In your output do not reference that you have looked at articles just quote specific ones if needed.
Return the result in this JSON format:
{
    "Verdict": True, False, or Indecisive,
    "Explanation":
    "Links": [
        No more than 3 links to articles that follow the verdict.
    ]
}

Here is the claim: %s

Here is the search: %s 
"""


response = client.responses.create(
        model="gpt-4.1",
    
        input= prompt_template % (search_query, evStr)
    )


print(response.output_text)
