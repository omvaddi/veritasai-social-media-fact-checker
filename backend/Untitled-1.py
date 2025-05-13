from openai import OpenAI
client = OpenAI()


clusters = [['i have dealt with acne since i was in sixth grade.', 'still got scarring, but for the most part, i am cleared up.', 'number one, accutane.', 'if you get one or two pimples, do not take accutane.', 'accutane destroys your body.', 'but if you have severe acne, in my opinion, accutane is the only medication that works.', 'no serum, moisturizer, or face mask is gonna mimic the effects of accutane.', "and if you plan on getting pregnant anytime soon, don't take accutane as well."], ["guys, i promise guys, guys are still heterosexual if guys care about guys's skin.", "i don't know why you'd be getting pregnant, but i mean, shit, if you're getting pregnant, good for you.", 'number two, you gotta cut out the added sugars.', 'these eyes like to drink boba, but guess what?', "i don't really do boba as much anymore, or when i do, i get 0% sugar.", 'to suppress 0% sugar, i drink shit like kombucha.', 'i promise guys, kombucha tastes like dick at first, but after a while, you get used to kombucha and you like kombucha.', 'kombucha is also good for your gut health, okay?', 'guys, i promise you, you are still heterosexual if you drink kombucha.', 'i know this might hurt a lot of people, but stop getting shit like frat pastes, lattes, manchas, and hella sugar.', 'you gotta cut out the oily food like chips.', "in my opinion, insta-ramen, insta-ramen doesn't help as well.", 'listen, i love fried chicken, okay?', "you could lock me in a room with korean fried chicken and i'd come out looking like i just killed somebody, but korean fried chicken is too oily, so i have to give korean fried chicken up.", 'even at restaurants, it pains me to say, but when they ask me, do you want fries or a salad?', 'i say salad.', 'i promise my young guys out there, my young guys out there still look vagina if my young guys out there do.']]
groupClusters = [""] * len(clusters)

text = ""

for i in range(len(clusters)):
    for j in range(len(clusters[i])):
        text = text + clusters[i][j] + " "
        groupClusters[i] += clusters[i][j] + " "
    groupClusters[i] = groupClusters[i][:-1]
text = text[:-1]

print(text)

prompt_template = """
You are helping extract verifiable claims from social media videos.
I will give you the full transcipt for contextual purposes but just work with the sentences I want you to analyze.
These sentences may not be coherent together but they all follow a theme.

For the sentence(s) provided, do the following:
1. Identify a **main theme**.
2. Extract any **clear, fact-checkable claims** -- things that can be verified through trusted sources.
3. Ignore all vague, subjective, or opinion-based content.

Return the result in this JSON format:
{{
    "theme": "Short theme",
    "claims": ["Claim 1", "Claim 2", etc...]
}}

If there are no fact-checkable claims, return exactly this:
"SKIP"

The full transcipt (to be used for context only) is as follow: %s
The sentence(s) that need to analyze are as follows: %s 
"""


for c in groupClusters:
    response = client.responses.create(
        model="gpt-4.1",
    
        input= prompt_template % (text, c)
    )

    print(response.output_text)


