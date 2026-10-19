from datetime import datetime, timezone, timedelta
import feedparser
from src.config import NEWS_LOOKBACK_HOURS, NEWS_MAX_ITEMS

RSS_FEEDS = [
    "https://finance.yahoo.com/news/rssindex",
    "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=stock%20market&sort=date"
]

def fetch_top_us_news() -> list:
    articles = []
    seen_titles = set()
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=NEWS_LOOKBACK_HOURS)

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                
                norm_title = "".join(filter(str.isalnum, title.lower()))
                if not norm_title or norm_title in seen_titles:
                    continue
                
                pub_time = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                
                if pub_time and pub_time < cutoff_time:
                    continue

                seen_titles.add(norm_title)
                articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:300] if summary else title,
                    "published_at": pub_time.isoformat() if pub_time else None
                })
        except Exception:
            continue

    return articles[:NEWS_MAX_ITEMS]
