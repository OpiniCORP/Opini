import asyncio
import json
import math
from typing import TypedDict

import httpx
import re


def extract_page_manifest(html):
    """extract javascript state data hidden in TripAdvisor HTML pages"""
    data = re.findall(r"pageManifest:({.+?})};", html, re.DOTALL)[0]
    return json.loads(data)

def extract_named_urql_cache(urql_cache: dict, pattern: str):
    """extract named urql response cache from hidden javascript state data"""
    data = json.loads(next(v["data"] for k, v in urql_cache.items() if pattern in v["data"]))
    return data



class Review(TypedDict):
    """storage type hint for review data"""
    id: str
    date: str
    rating: str
    title: str
    text: str
    votes: int
    language: str


def parse_reviews(html) -> Review:
    """Parse reviews from a review page"""
    page_data = extract_page_manifest(html)
    review_cache = extract_named_urql_cache(page_data["urqlCache"]["results"], '"reviewListPage"')
    parsed = []
    # review data contains loads of information, let's parse only the basic in this tutorial
    for review in review_cache["locations"][0]["reviewListPage"]["reviews"]:
        parsed.append(
            {
                "id": review["id"],
                "date": review["publishedDate"],
                "rating": review["rating"],
                "title": review["title"],
                "text": review["text"],
                "votes": review["helpfulVotes"],
                "language": review["language"],
            }
        )
    return parsed


async def scrape_hotel(url, session):
    """Scrape all hotel data: information, pricing and reviews"""
    first_page = await session.get(url)
    page_data = extract_page_manifest(first_page.text)
    _pricing_key = next(
        (key for key in page_data["redux"]["api"]["responses"] if "/hotelDetail" in key and "/heatMap" in key)
    )
    pricing_details = page_data["redux"]["api"]["responses"][_pricing_key]["data"]["items"]
    hotel_cache = extract_named_urql_cache(page_data["urqlCache"]["results"], '"locationDescription"')
    hotel_info = hotel_cache["locations"][0]

    # ------- NEW CODE ----------------
    # for reviews we first need to scrape multiple pages
    # so, first let's find total amount of pages
    total_reviews = hotel_info["reviewSummary"]["count"]
    _review_page_size = 10
    total_review_pages = int(math.ceil(total_reviews / _review_page_size))
    # then we can scrape all review pages concurrently
    # note: in review url "or" stands for "offset reviews"
    review_urls = [
        url.replace("-Reviews-", f"-Reviews-or{_review_page_size * i}-") for i in range(1, total_review_pages)
    ]
    assert len(set(review_urls)) == len(review_urls)
    review_responses = await asyncio.gather(*[session.get(url) for url in review_urls])
    reviews = []
    for response in [first_page, *review_responses]:
        reviews.extend(parse_reviews(response.text))
    # ---------------------------------

    hotel_data = {
        "info": hotel_info,
        "reviews": reviews,
    }
    return hotel_data


def save_to_json(data, filename):
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
        result = await scrape_hotel(
            "https://www.tripadvisor.fr/Hotel_Review-g187147-d2292234-Reviews-Le_VIP_Paris_Yacht_Hotel-Paris_Ile_de_France.html?spAttributionToken=MjA3MjMzNzc",
            session,
        )
        save_to_json(result, "output.json")


if __name__ == "__main__":
    asyncio.run(run())
