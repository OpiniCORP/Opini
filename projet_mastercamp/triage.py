import json

# Lecture du fichier JSON
with open('output.json') as file:
    data = json.load(file)


for info in ["locationId","accommodationType","parent","parents","locationDescription","businessAdvantageData","writeUserReviewUrl",
             "reviewSummary","accommodationCategory","popIndexDetails","detail","heroPhoto"] :
        data["info"].pop(info)


print(data)
