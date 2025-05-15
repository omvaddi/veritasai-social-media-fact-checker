from openai import OpenAI
client = OpenAI()
import json


clusters = [['what is a woman and why is it important that we understand the difference between men and women?', "well, it's sort of easy to answer for me because a woman is somebody that can have a baby under certain circumstances.", 'a woman can, a woman has a quality.', "a woman is a person who's much smarter than a man i've always found.", "a woman is a person that doesn't give a man even a chance of success.", "and a woman's a person that in many cases has been treated very badly because i think that what happens with this crazy, this crazy issue of men being able to play in women's sports is just ridiculous and very unfair to women and very demeaning to women.", "women are basically incredible people, do so much for our country and we love, we love our women and we're going to take care of our women."]]

groupClusters = [""] * len(clusters)

text = ""

for i in range(len(clusters)):
    for j in range(len(clusters[i])):
        text = text + clusters[i][j] + " "
        groupClusters[i] += clusters[i][j] + " "
    groupClusters[i] = groupClusters[i][:-1]
text = text[:-1]


prompt_template = """
You are helping extract verifiable claims from social media videos.
I will give you the full transcipt for contextual purposes but just work with the sentences I want you to analyze.
These sentences may not be coherent together but they all follow a theme.

For the sentence(s) provided, do the following:
1. Identify a **main theme**.
2. Extract any **fact-checkable claims** -- things that can be verified through trusted sources. Rephrase them into a short unbiased searchable phrase with key words.
3. Ignore all vague, subjective, opinion-based, and non-factual content. It is okay if no claims are found.

Return the result in this JSON format:
{
    "theme": "Short theme",
    "claims": [
    {
        "id": 1,
        "text": claim 1
    } 
    {
        "id": 2,
        "text": claim 2
    }
    {
        etc...
    }
    ]
}

If there are no fact-checkable claims, return exactly this:
SKIP

The full transcript (to be used for context only) is as follow: %s
The sentence(s) that need to analyze are as follows: %s 
"""

totalJSONStr = "{\n"

for i in range(len(groupClusters)):

    totalJSONStr += "\"Topic #" + str(i + 1) + "\":\n"

    response = client.responses.create(
        model="gpt-4.1",
    
        input= prompt_template % (text, groupClusters[i])
    )
    totalJSONStr += response.output_text

    if i != len(groupClusters) - 1:
        totalJSONStr += ","
    totalJSONStr += "\n"

    
totalJSONStr += "}"

print(totalJSONStr)

jsonData = json.loads(totalJSONStr)
print(jsonData['Topic #1'])



