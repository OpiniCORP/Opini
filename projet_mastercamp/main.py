import asyncio
import json
import math
from typing import TypedDict

import httpx
import re


def extract_page_manifest(html):
    """Extrait les données de l'état JavaScript cachées dans les pages HTML de TripAdvisor"""
    match = re.search(r'(?<=pageManifest:)(.*?)(?=</script>)', html, re.DOTALL)
    if match:
        data = match.group(1)
        return json.loads(data)
    else:
        raise ValueError("Page manifest data not found.")


def extract_named_urql_cache(urql_cache: dict, pattern: str):
    """Extrait le cache de réponse urql nommé à partir des données d'état JavaScript cachées"""
    data = json.loads(next(v["data"] for k, v in urql_cache.items() if pattern in v["data"]))
    return data


class Review(TypedDict):
    """Type d'annotation pour le stockage des données des avis"""
    id: str
    date: str
    rating: str
    title: str
    text: str
    votes: int
    url: str
    language: str
    platform: str
    author_id: str
    author_name: str
    author_username: str


def parse_reviews(html) -> Review:
    """Analyse les avis à partir d'une page d'avis"""
    page_data = extract_page_manifest(html)
    review_cache = extract_named_urql_cache(page_data["urqlCache"]["results"], '"reviewListPage"')
    parsed = []
    # Nous ne récupérons que les informations de base dans cet exemple
    for review in review_cache["locations"][0]["reviewListPage"]["reviews"]:
        parsed.append(
            {
                "id": review["id"],
                "date": review["publishedDate"],
                "rating": review["rating"],
                "title": review["title"],
                "text": review["text"],
                "votes": review["helpfulVotes"],
                "url": review["route"]["url"],
                "language": review["language"],
                "platform": review["publishPlatform"],
                "author_id": review["userProfile"]["id"],
                "author_name": review["userProfile"]["displayName"],
                "author_username": review["userProfile"]["username"],
            }
        )
    return parsed


async def scrape_restaurant(url, session):
    """Récupère toutes les données d'un restaurant : informations, tarifs et avis"""
    first_page = await session.get(url)
    page_data = extract_page_manifest(first_page.text)
    restaurant_cache = extract_named_urql_cache(page_data["urqlCache"]["results"], '"restaurantDetailPage"')
    restaurant_info = restaurant_cache["locations"][0]

    # ------- CODE MODIFIÉ ----------------
    # Pour les avis, nous devons d'abord récupérer plusieurs pages
    # Donc, commençons par trouver le nombre total de pages
    total_reviews = restaurant_info["reviewSummary"]["count"]
    _review_page_size = 10
    total_review_pages = int(math.ceil(total_reviews / _review_page_size))
    # Ensuite, nous pouvons récupérer toutes les pages d'avis en parallèle
    # Remarque : dans l'URL des avis, "or" signifie "offset reviews"
    review_urls = [
        url.replace("-Reviews-", f"-Reviews-or{_review_page_size * i}-") for i in range(1, total_review_pages)
    ]
    assert len(set(review_urls)) == len(review_urls)
    review_responses = await asyncio.gather(*[session.get(url) for url in review_urls])
    reviews = []
    for response in [first_page, *review_responses]:
        reviews.extend(parse_reviews(response.text))
    # ---------------------------------

    restaurant_data = {
        "info": restaurant_info,
        "reviews": reviews,
    }
    return restaurant_data


def save_to_json(data, filename):
    """Enregistre les données au format JSON dans un fichier"""
    with open(filename, "w") as file:
        json.dump(data, file, indent=2)


async def run():
    limits = httpx.Limits(max_connections=5)
    BASE_HEADERS = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9,lt;q=0.8,et;q=0.7,de;q=0.6",
        "accept-encoding": "gzip, deflate, br",
    }
    async with httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(15.0), headers=BASE_HEADERS) as session:
        result = await scrape_restaurant(
            "https://www.tripadvisor.com/Restaurant_Review-g187147-d8770483-Reviews-Bouillon_Pigalle-Paris_Ile_de_France.html",
            session,
        )
        save_to_json(result, "output.json")


if __name__ == "__main__":
    asyncio.run(run())
