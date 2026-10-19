"""Fetch and rank timestamped financial RSS items; no article text scraping."""
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
from src.config import NEWS_LOOKBACK_HOURS, NEWS_MAX_ITEMS

TOPICS = {
    "big_tech": 'Nvidia OR Microsoft OR Apple OR Alphabet OR Amazon OR Meta OR Tesla OR AMD OR semiconductor OR AI stocks',
    "us_market": 'US stocks OR Nasdaq futures OR Fed OR inflation OR US Treasury yields OR earnings',
    "global": 'China tariffs OR Japan yen OR ECB OR Middle East oil OR geopolitics stocks OR trade war',
    "sectors": 'energy stocks OR utilities stocks OR data center power OR banking stocks OR defense stocks',
}
BASE_FEEDS = [
    ("us_market", "https://finance.yahoo.com/news/rssindex"),
]

def _normalize(title):
    return re.sub(r"[^a-z0-9\u0e00-\u0e7f]", "", title.casefold())


def _published(entry):
    for prop in ("published_parsed", "updated_parsed"):
        value = entry.get(prop)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc)
    for prop in ("published", "updated"):
        value = entry.get(prop)
        if value:
            try:
                dt = parsedate_to_datetime(value)
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            except (TypeError, ValueError):
                pass
    return None


def fetch_top_us_news() -> list:
    """Return categorized, recent items. Unknown publication dates are excluded."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=NEWS_LOOKBACK_HOURS)
    feeds = BASE_FEEDS + [
        (category, "https://news.google.com/rss/search?q=" + quote_plus(query + " when:1d") + "&hl=en-US&gl=US&ceid=US:en")
        for category, query in TOPICS.items()
    ]
    seen = set()
    result = []
    for category, url in feeds:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "USMarketBrief/2.0"})
            for item in feed.entries:
                title = item.get("title", "").strip()
                link = item.get("link", "").strip()
                published = _published(item)
                key = _normalize(title)
                if not title or not link.startswith(("https://", "http://")) or not key or key in seen:
                    continue
                if published is None or published < cutoff or published > now + timedelta(minutes=10):
                    continue
                seen.add(key)
                raw_summary = re.sub(r"<[^>]+>", " ", item.get("summary", ""))
                result.append({
                    "id": f"news-{len(result)+1}",
                    "category": category,
                    "title": title,
                    "summary": re.sub(r"\s+", " ", raw_summary).strip()[:450],
                    "link": link,
                    "published_at": published.isoformat(),
                    "source": item.get("source", {}).get("title", "") if isinstance(item.get("source"), dict) else "",
                })
        except Exception as exc:
            print(f"[WARN] News feed failure ({category}): {exc}")
    result.sort(key=lambda item: item["published_at"], reverse=True)
    # Prevent one category dominating the AI context.
    grouped = {key: [] for key in TOPICS}
    for item in result:
        grouped.setdefault(item["category"], []).append(item)
    selected = []
    per_category = max(3, NEWS_MAX_ITEMS // len(TOPICS))
    for key in ("big_tech", "us_market", "global", "sectors"):
        selected.extend(grouped.get(key, [])[:per_category])
    selected = selected[:NEWS_MAX_ITEMS]
    for index, item in enumerate(selected, 1):
        item["id"] = f"news-{index}"
    print(f"[News] fetched={len(result)}, selected={len(selected)}, categories="
          + str({key: sum(i['category'] == key for i in selected) for key in TOPICS}))
    return selected
