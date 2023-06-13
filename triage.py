import json

# Lecture du fichier JSON
with open('output.json') as file:
    data = json.load(file)


for info in ["locationId","accommodationType","parent","parents","locationDescription","businessAdvantageData","writeUserReviewUrl",
             "reviewSummary","accommodationCategory","popIndexDetails","detail","heroPhoto"] :
        data["info"].pop(info)

data_normalized = {
  "info": {
    "name": data["info"]["name"],
    },
  "reviews":{

  }
}

for review in data["reviews"]:
    id = review["id"]
    data_normalized["reviews"][id] = review
    data_normalized["reviews"][id].pop("id")


print(data_normalized)