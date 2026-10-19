from datetime import datetime, timezone, timedelta
import feedparser
from dateutil import parser as date_parser
from src.config import NEWS_LOOKBACK_HOURS, BIG_TECH_KEYWORDS, GLOBAL_KEYWORDS, TIMEZONE

RSS_FEEDS = [
    {"url": "https://finance.yahoo.com/news/rssindex", "source": "Yahoo Finance"},
    {"url": "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=stock%20market&sort=date", "source": "CNBC"},
    {"url": "https://feeds.content.dowjones.io/public/rss/mw_topstories", "source": "MarketWatch"}
]

def _classify_article(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    
    # 1. เช็ก Big Tech & AI อย่างเข้มงวด (ต้องพูดถึงบริษัทหรือกลุ่มเทคฯ โดยตรง)
    if any(k in text for k in BIG_TECH_KEYWORDS):
        return "tech"
        
    # 2. เช็ก Global Impact (กระทบผ่านจีน/ยุโรป/น้ำมัน/ห่วงโซ่อุปทาน)
    if any(k in text for k in GLOBAL_KEYWORDS):
        return "global"
        
    return "macro"

def fetch_categorized_news() -> dict:
    seen_titles = set()
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=NEWS_LOOKBACK_HOURS)

    categorized = {
        "tech": [],
        "global": [],
        "macro": []
    }

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()

                if not title or not link:
                    continue

                # Deduplication โดยใช้ตัวอักษรของชื่อข่าว
                norm_title = "".join(filter(str.isalnum, title.lower()))
                if norm_title in seen_titles:
                    continue

                # วันเวลาเผยแพร่
                pub_dt = None
                if entry.get("published"):
                    try:
                        pub_dt = date_parser.parse(entry.published)
                        if pub_dt.tzinfo is None:
                            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass
                elif hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                # กรองข่าวที่เก่าเกินกำหนด
                if pub_dt and pub_dt < cutoff_time:
                    continue

                pub_th_str = pub_dt.astimezone(TIMEZONE).strftime("%d/%m %H:%M น.") if pub_dt else "ล่าสุด"

                seen_titles.add(norm_title)
                category = _classify_article(title, summary)

                categorized[category].append({
                    "title": title,
                    "link": link,
                    "summary": summary[:250] if summary else title,
                    "source": feed_info["source"],
                    "published_at_th": pub_th_str
                })
        except Exception:
            continue

    # จำกัดจำนวนข่าวเพื่อไม่ให้รก
    return {
        "tech": categorized["tech"][:3],
        "global": categorized["global"][:2],
        "macro": categorized["macro"][:4]
    }