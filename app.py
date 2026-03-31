"""AI商业参谋 - 高保真UI预览版（Streamlit）。"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import html
import os
import re
import time
import textwrap
from urllib.parse import quote_plus, urljoin
import xml.etree.ElementTree as ET

import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

from bosses import BOSSES
from events import TODAY_EVENTS
from mock_advisor import (
    get_action,
    get_mirofish,
    get_network_suggestion,
    match_events_for_boss,
    match_news_for_boss,
)


st.set_page_config(
    page_title="AI商业参谋 · Premium UI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


DEFAULT_NEWS = [
    {"id": "H01", "title": "国务院发布《数字经济促进高质量发展实施方案》", "category": "政策"},
    {"id": "H02", "title": "抖音电商宣布开放中小商家流量扶持计划，佣金降低30%", "category": "电商"},
    {"id": "H03", "title": "人民币汇率创近期新高，外贸企业成本压力上升", "category": "外汇"},
    {"id": "H04", "title": "DeepSeek新版本发布，企业AI应用成本降低60%", "category": "AI科技"},
    {"id": "H05", "title": "广交会春季展预注册开始，海外采购商同比增加30%", "category": "外贸"},
    {"id": "H06", "title": "教育部发布企业职业技能培训补贴新政，最高50万", "category": "政策"},
    {"id": "H07", "title": "新能源汽车2月销量同比增长45%，配件需求激增", "category": "新能源"},
    {"id": "H08", "title": "抖音直播整治违规行为，头部主播受限，中小卖家机会窗口", "category": "电商"},
    {"id": "H09", "title": "东南亚跨境电商市场规模突破1万亿，中国卖家占40%", "category": "跨境电商"},
    {"id": "H10", "title": "银行推出新型供应链金融，专为中小企业降低融资门槛", "category": "金融"},
    {"id": "H11", "title": "阿里云发布新一代企业AI助手，价格下调70%", "category": "AI科技"},
    {"id": "H12", "title": "餐饮行业复苏：一线城市客流量回升25%，商场招商积极", "category": "餐饮"},
    {"id": "H13", "title": "律师行业调查：60%律师开始使用AI辅助办案，效率提升3倍", "category": "法律科技"},
    {"id": "H14", "title": "设计行业报告：AI工具普及但创意价值仍依赖人工，报价可提升", "category": "设计"},
    {"id": "H15", "title": "广州制造业PMI连续3个月上升，订单回暖，配件需求明显", "category": "制造业"},
]


LOCAL_NEWS_RSS_SOURCES = [
    ("中国政府网政策", "https://www.gov.cn/zhengce/", "政策"),
    ("百度财经", "https://news.baidu.com/n?cmd=4&class=finannews&tn=rss", "金融"),
    ("百度民生", "https://news.baidu.com/n?cmd=4&class=civilnews&tn=rss", "政策"),
    ("36氪", "https://www.36kr.com/feed", "AI科技"),
    ("钛媒体", "https://www.tmtpost.com/rss.xml", "AI科技"),
]

GOOGLE_NEWS_QUERIES = [
    ("中小企业 政策", "政策"),
    ("抖音 电商 中小商家", "电商"),
    ("人民币 汇率 外贸", "外汇"),
    ("企业 AI 应用", "AI科技"),
    ("跨境电商 东南亚", "跨境电商"),
    ("供应链 金融 中小企业", "金融"),
    ("餐饮 连锁 商场", "餐饮"),
    ("法律科技 律师 AI", "法律科技"),
    ("制造业 PMI 订单", "制造业"),
    ("新能源汽车 配件", "新能源"),
]

LOCAL_EVENT_KEYWORDS = [
    "创业峰会",
    "跨境电商",
    "AI 论坛",
    "产业展会",
    "投融资路演",
]

EVENT_API_QUERIES = [
    "business summit",
    "entrepreneur forum",
    "cross-border ecommerce",
    "ai conference",
    "marketing growth",
]

EVENTBRITE_SEARCH_URL = "https://www.eventbriteapi.com/v3/events/search/"
TICKETMASTER_SEARCH_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

NEWS_CATEGORY_RULES = {
    "政策": ["政策", "补贴", "实施方案", "指导意见", "工信部", "国务院"],
    "电商": ["电商", "抖音", "直播", "小红书", "淘宝", "拼多多"],
    "外汇": ["汇率", "人民币", "美元", "外汇"],
    "AI科技": ["ai", "人工智能", "大模型", "deepseek", "智能体", "算法"],
    "外贸": ["外贸", "出口", "进口", "广交会", "海外订单"],
    "跨境电商": ["跨境", "东南亚", "出海", "shopee", "lazada"],
    "金融": ["金融", "融资", "信贷", "银行", "供应链金融"],
    "餐饮": ["餐饮", "连锁", "外卖", "堂食", "商场"],
    "法律科技": ["法律", "律所", "合规", "legaltech", "律师"],
    "设计": ["设计", "ui", "ux", "创意", "品牌设计"],
    "制造业": ["制造业", "工厂", "订单", "pmi", "产能"],
    "新能源": ["新能源", "新能源汽车", "电池", "光伏", "储能"],
}

EVENT_INDUSTRY_RULES = {
    "企业培训": ["培训", "hr", "人力", "企业管理", "职业技能", "组织发展"],
    "品牌策划": ["品牌", "营销", "内容", "私域", "新消费"],
    "外贸": ["外贸", "跨境", "东南亚", "出海", "广交会", "供应链"],
    "UI/UX设计": ["设计", "ui", "ux", "用户体验", "figma", "产品设计"],
    "餐饮": ["餐饮", "连锁", "堂食", "外卖", "预制菜", "选址"],
    "电商": ["电商", "抖音", "直播", "投流", "选款", "流量"],
    "汽车配件": ["汽配", "汽车配件", "新能源汽车", "配件", "b2b"],
    "HR猎头": ["招聘", "猎头", "人才", "高管", "人力"],
    "建材": ["建材", "装修", "工程", "地产", "市政"],
    "法律科技": ["法律", "律所", "合规", "legaltech", "融资"],
}

EVENT_MARKERS = ["峰会", "论坛", "沙龙", "路演", "训练营", "展会", "对接会", "大会", "报名", "活动"]

CITY_MARKERS = ["深圳", "上海", "广州", "北京", "杭州", "成都", "武汉", "南京", "苏州", "线上"]

NON_MAINLAND_LOCATION_MARKERS = [
    "香港",
    "澳门",
    "台湾",
    "海外",
    "新加坡",
    "马来西亚",
    "美国",
    "英国",
    "日本",
    "韩国",
    "欧洲",
    "北美",
    "澳大利亚",
]


def _google_rss_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"


def _strip_html_tags(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


def _parse_rss_items(url: str, max_items: int = 18) -> list[dict]:
    try:
        response = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0 BizAdvisor/1.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception:
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for node in channel.findall("item")[:max_items]:
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        description = _strip_html_tags(node.findtext("description") or "")
        pub_date = (node.findtext("pubDate") or "").strip()
        if not title:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "published": pub_date,
            }
        )
    return items


def _safe_get_text(url: str, timeout: int = 14) -> str:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 BizAdvisor/1.0"})
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        return response.text
    except Exception:
        return ""


def _clean_html_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_gov_policy_items(url: str, max_items: int = 14) -> list[dict]:
    html_text = _safe_get_text(url)
    if not html_text:
        return []

    pairs = re.findall(r'<a[^>]+href="([^"]*content_\d+\.htm)"[^>]*>(.*?)</a>', html_text, flags=re.I | re.S)
    if not pairs:
        return []

    ignored_titles = {
        "国务院部门网站",
        "地方政府网站",
        "驻港澳机构网站",
        "驻外机构",
        "关于本网",
        "网站声明",
        "联系我们",
        "中国政府网微博、微信",
        "微信",
    }

    policy_items: list[dict] = []
    seen_urls = set()
    for href, title_html in pairs:
        title = _clean_html_text(title_html)
        if not title or title in ignored_titles or len(title) < 8:
            continue

        full_url = urljoin(url, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        if "/zhengce/" not in full_url:
            continue

        policy_items.append(
            {
                "title": title,
                "link": full_url,
                "description": "中国政府网政策动态",
                "published": "",
            }
        )

        if len(policy_items) >= max_items:
            break

    return policy_items


def _infer_news_category(title: str, description: str, fallback: str) -> str:
    text = f"{title} {description}".lower()
    for category, keywords in NEWS_CATEGORY_RULES.items():
        if any(kw.lower() in text for kw in keywords):
            return category
    return fallback


def _detect_event_profile(title: str, description: str) -> tuple[list[str], list[str]]:
    text = f"{title} {description}".lower()
    keywords: list[str] = []
    industries: list[str] = []

    for industry, rule_keywords in EVENT_INDUSTRY_RULES.items():
        matched = [kw for kw in rule_keywords if kw.lower() in text]
        if matched:
            industries.append(industry)
            keywords.extend(matched[:2])

    if not keywords:
        keywords = ["中小企业", "增长", "合作"]
    if not industries:
        industries = ["企业服务"]

    # 去重并保序
    uniq_keywords = list(dict.fromkeys(keywords))[:5]
    uniq_industries = list(dict.fromkeys(industries))[:4]
    return uniq_keywords, uniq_industries


def _format_event_start(raw_time: str) -> str:
    if not raw_time:
        return "近期"

    candidate = raw_time.strip()
    try:
        dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        pass

    try:
        dt = parsedate_to_datetime(candidate)
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        pass

    if "T" in candidate:
        return candidate.replace("T", " ")[:16]
    return candidate[:16] if candidate else "近期"


def _normalize_event_text(text: str, max_len: int = 150) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return ""
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3].rstrip() + "..."


def _safe_api_get_json(url: str, *, params: dict | None = None, headers: dict | None = None) -> dict | None:
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=14,
            allow_redirects=True,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _infer_event_location(title: str, description: str, event_format: str, fallback_label: str) -> str:
    text = f"{title} {description}"
    for city in CITY_MARKERS:
        if city in text:
            if city == "线上":
                return "线上活动"
            return city
    return "线上活动" if event_format == "线上" else fallback_label


def _build_google_news_fallback(max_items: int = 16) -> list[dict]:
    seen_titles = set()
    news: list[dict] = []

    for query, fallback_category in GOOGLE_NEWS_QUERIES:
        url = _google_rss_url(query)
        for item in _parse_rss_items(url, max_items=12):
            normalized_title = item["title"].strip()
            if not normalized_title or normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)

            category = _infer_news_category(item["title"], item["description"], fallback_category)
            news.append(
                {
                    "id": f"R{len(news) + 1:02d}",
                    "title": item["title"],
                    "category": category,
                    "source": "Google News RSS（补充）",
                    "published": item["published"],
                    "url": item["link"],
                }
            )
            if len(news) >= max_items:
                return news

    return news


def _build_local_news(max_items: int = 24) -> list[dict]:
    seen_titles = set()
    news: list[dict] = []

    for source_name, source_url, fallback_category in LOCAL_NEWS_RSS_SOURCES:
        if source_name == "中国政府网政策":
            items = _parse_gov_policy_items(source_url, max_items=14)
        else:
            items = _parse_rss_items(source_url, max_items=16)

        for item in items:
            normalized_title = item["title"].strip()
            if not normalized_title or normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)

            category = _infer_news_category(item["title"], item["description"], fallback_category)
            if source_name == "中国政府网政策":
                category = "政策"

            news.append(
                {
                    "id": f"R{len(news) + 1:02d}",
                    "title": item["title"],
                    "category": category,
                    "source": source_name,
                    "published": item.get("published", ""),
                    "url": item.get("link", ""),
                }
            )
            if len(news) >= max_items:
                return news

    return news


def _build_live_news(max_items: int = 24) -> list[dict]:
    local_news = _build_local_news(max_items=max_items)
    if len(local_news) >= max_items:
        return local_news[:max_items]

    fallback_news = _build_google_news_fallback(max_items=max_items)
    if not local_news:
        return fallback_news[:max_items]

    seen_titles = {item["title"].strip() for item in local_news}
    merged = list(local_news)

    for item in fallback_news:
        title = item["title"].strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        merged.append(item)
        if len(merged) >= max_items:
            break

    for i, item in enumerate(merged, 1):
        item["id"] = f"R{i:02d}"
    return merged


def _event_from_eventbrite(raw_event: dict) -> dict | None:
    title = _normalize_event_text((raw_event.get("name") or {}).get("text", ""), max_len=90)
    if not title:
        return None

    summary = _normalize_event_text(raw_event.get("summary", ""), max_len=200)
    long_description = _normalize_event_text(((raw_event.get("description") or {}).get("text", "")), max_len=200)
    description = long_description or summary or "活动详情请点击官方页面查看。"
    event_format = "线上" if raw_event.get("online_event") else "线下"

    venue = raw_event.get("venue") or {}
    venue_address = _normalize_event_text((venue.get("address") or {}).get("localized_address_display", ""), max_len=40)
    location = _infer_event_location(title, description, event_format, venue_address or "线下活动（详见活动页）")

    start_info = raw_event.get("start") or {}
    end_info = raw_event.get("end") or {}
    start_at = start_info.get("local") or start_info.get("utc") or ""
    deadline = end_info.get("local") or end_info.get("utc") or ""

    keywords, industries = _detect_event_profile(title, description)
    text = f"{title} {description}".lower()
    high_value = any(marker in text for marker in EVENT_MARKERS) or any(
        marker in text for marker in ["summit", "conference", "forum", "expo", "roadshow"]
    )

    return {
        "title": title,
        "time": _format_event_start(start_at),
        "location": location,
        "format": event_format,
        "source": "api",
        "source_detail": "Eventbrite API",
        "keywords": keywords,
        "target_industries": industries,
        "description": description,
        "registration_deadline": _format_event_start(deadline) if deadline else "详见活动页",
        "value": "高" if high_value else "中",
        "url": raw_event.get("url", ""),
    }


def _event_from_ticketmaster(raw_event: dict) -> dict | None:
    title = _normalize_event_text(raw_event.get("name", ""), max_len=90)
    if not title:
        return None

    info = _normalize_event_text(raw_event.get("info", ""), max_len=200)
    note = _normalize_event_text(raw_event.get("pleaseNote", ""), max_len=200)
    description = info or note or "活动详情请点击官方页面查看。"
    text = f"{title} {description}".lower()
    event_format = "线上" if any(w in text for w in ["online", "virtual", "webinar", "livestream", "线上", "直播"]) else "线下"

    venue = ((raw_event.get("_embedded") or {}).get("venues") or [{}])[0]
    city = _normalize_event_text((venue.get("city") or {}).get("name", ""), max_len=24)
    venue_name = _normalize_event_text(venue.get("name", ""), max_len=40)
    country = _normalize_event_text((venue.get("country") or {}).get("name", ""), max_len=24)
    fallback_location = " · ".join(part for part in [city, venue_name, country] if part) or "线下活动（详见活动页）"
    location = _infer_event_location(title, description, event_format, fallback_location)

    start_info = (raw_event.get("dates") or {}).get("start") or {}
    start_at = start_info.get("dateTime") or ""
    if not start_at:
        local_date = start_info.get("localDate") or ""
        local_time = start_info.get("localTime") or ""
        if local_date and local_time:
            start_at = f"{local_date}T{local_time}"
        else:
            start_at = local_date

    keywords, industries = _detect_event_profile(title, description)
    high_value = any(marker in text for marker in EVENT_MARKERS) or any(
        marker in text for marker in ["summit", "conference", "forum", "expo", "roadshow"]
    )

    return {
        "title": title,
        "time": _format_event_start(start_at),
        "location": location,
        "format": event_format,
        "source": "api",
        "source_detail": "Ticketmaster Discovery API",
        "keywords": keywords,
        "target_industries": industries,
        "description": description,
        "registration_deadline": "详见活动页",
        "value": "高" if high_value else "中",
        "url": raw_event.get("url", ""),
    }


def _huodongxing_search_url(keyword: str) -> str:
    return f"https://www.huodongxing.com/search?kw={quote_plus(keyword)}"


def _extract_huodongxing_card_events(html_text: str, keyword: str) -> list[dict]:
    pattern = re.compile(
        r'<div class="search-tab-content-item-mesh".*?'
        r'href="(?P<href>/event/[^"]+)"[^>]*>.*?'
        r'<p class="activityTitle">(?P<title>.*?)</p>.*?'
        r'<div class="item-dress flex">\s*<p>(?P<time>.*?)</p>\s*<span>.*?'
        r'<span class="item-dress-pp">(?P<location>.*?)</span>',
        flags=re.I | re.S,
    )

    events: list[dict] = []
    for match in pattern.finditer(html_text):
        href = html.unescape(match.group("href") or "").strip()
        title = _clean_html_text(match.group("title") or "")
        event_time = _clean_html_text(match.group("time") or "")
        location = _clean_html_text(match.group("location") or "")

        if not href or not title:
            continue

        event_url = urljoin("https://www.huodongxing.com", href.split("?")[0])
        description = f"来自活动行本土活动源，检索关键词：{keyword}。"
        event_format = "线上" if any(w in f"{title} {location}" for w in ["线上", "直播", "webinar", "在线"]) else "线下"
        normalized_location = location or ("线上活动" if event_format == "线上" else "全国（以活动页为准）")

        keywords, industries = _detect_event_profile(title, description)
        text = f"{title} {description}".lower()
        high_value = any(marker in text for marker in EVENT_MARKERS)

        events.append(
            {
                "title": title,
                "time": event_time or "近期",
                "location": normalized_location,
                "format": event_format,
                "source": "local",
                "source_detail": "活动行（本土活动平台）",
                "keywords": keywords,
                "target_industries": industries,
                "description": description,
                "registration_deadline": "详见活动页",
                "value": "高" if high_value else "中",
                "url": event_url,
            }
        )

    return events


def _extract_huodongxing_quick_events(html_text: str, keyword: str) -> list[dict]:
    pattern = re.compile(
        r'<a class="late-publish-title"[^>]+href="(?P<href>/event/[^"]+)"[^>]*>(?P<title>.*?)</a>',
        flags=re.I | re.S,
    )

    events: list[dict] = []
    for match in pattern.finditer(html_text):
        href = html.unescape(match.group("href") or "").strip()
        title = _clean_html_text(match.group("title") or "")
        if not href or not title:
            continue

        event_url = urljoin("https://www.huodongxing.com", href.split("?")[0])
        description = f"来自活动行本土活动源，检索关键词：{keyword}。"
        event_format = "线上" if any(w in title for w in ["线上", "直播", "webinar", "在线"]) else "线下"
        keywords, industries = _detect_event_profile(title, description)
        text = f"{title} {description}".lower()
        high_value = any(marker in text for marker in EVENT_MARKERS)

        events.append(
            {
                "title": title,
                "time": "近期",
                "location": "全国（以活动页为准）",
                "format": event_format,
                "source": "local",
                "source_detail": "活动行（本土活动平台）",
                "keywords": keywords,
                "target_industries": industries,
                "description": description,
                "registration_deadline": "详见活动页",
                "value": "高" if high_value else "中",
                "url": event_url,
            }
        )

    return events


def _is_mainland_event(event: dict) -> bool:
    text = f"{event.get('title', '')} {event.get('location', '')}"
    return not any(marker in text for marker in NON_MAINLAND_LOCATION_MARKERS)


def _fetch_huodongxing_events(max_items: int = 18) -> list[dict]:
    collected: list[dict] = []
    seen_urls = set()

    for keyword in LOCAL_EVENT_KEYWORDS:
        url = _huodongxing_search_url(keyword)
        html_text = _safe_get_text(url, timeout=16)
        if not html_text:
            continue

        candidates = _extract_huodongxing_card_events(html_text, keyword)
        if not candidates:
            candidates = _extract_huodongxing_quick_events(html_text, keyword)

        for event in candidates:
            event_url = event.get("url", "")
            if not event_url or event_url in seen_urls:
                continue
            if not _is_mainland_event(event):
                continue
            seen_urls.add(event_url)
            collected.append(event)
            if len(collected) >= max_items:
                return collected

    return collected


def _fetch_eventbrite_events(api_token: str) -> list[dict]:
    collected: list[dict] = []
    headers = {"Authorization": f"Bearer {api_token}"}

    for query in EVENT_API_QUERIES:
        payload = _safe_api_get_json(
            EVENTBRITE_SEARCH_URL,
            params={
                "q": query,
                "sort_by": "date",
                "page_size": 10,
                "expand": "venue",
            },
            headers=headers,
        )
        if not payload:
            continue

        for raw_event in payload.get("events", []):
            status = (raw_event.get("status") or "").lower()
            if status and status not in {"live", "started"}:
                continue

            event = _event_from_eventbrite(raw_event)
            if event:
                collected.append(event)

    return collected


def _fetch_ticketmaster_events(api_key: str) -> list[dict]:
    collected: list[dict] = []

    for query in EVENT_API_QUERIES:
        payload = _safe_api_get_json(
            TICKETMASTER_SEARCH_URL,
            params={
                "apikey": api_key,
                "keyword": query,
                "size": 10,
                "sort": "date,asc",
                "locale": "*",
            },
        )
        if not payload:
            continue

        event_items = (payload.get("_embedded") or {}).get("events") or []
        for raw_event in event_items:
            event = _event_from_ticketmaster(raw_event)
            if event:
                collected.append(event)

    return collected


def _dedupe_live_events(events: list[dict], max_items: int) -> list[dict]:
    seen_titles = set()
    deduped: list[dict] = []

    for event in events:
        title_key = re.sub(r"\s+", " ", (event.get("title", "").lower())).strip()
        if not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(event)
        if len(deduped) >= max_items:
            break

    for i, event in enumerate(deduped, 1):
        event["id"] = f"rev{i:02d}"
    return deduped


def _build_live_events(max_items: int = 12) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    all_events: list[dict] = []

    local_events = _fetch_huodongxing_events(max_items=max_items * 2)
    if local_events:
        all_events.extend(local_events)
    else:
        warnings.append("本土活动源暂不可用")

    eventbrite_token = os.getenv("EVENTBRITE_API_TOKEN", "").strip()
    ticketmaster_key = os.getenv("TICKETMASTER_API_KEY", "").strip()

    if eventbrite_token:
        eventbrite_events = _fetch_eventbrite_events(eventbrite_token)
        if eventbrite_events:
            all_events.extend(eventbrite_events)
        else:
            warnings.append("Eventbrite API 暂未返回可用活动")

    if ticketmaster_key:
        ticketmaster_events = _fetch_ticketmaster_events(ticketmaster_key)
        if ticketmaster_events:
            all_events.extend(ticketmaster_events)
        else:
            warnings.append("Ticketmaster API 暂未返回可用活动")

    live_events = _dedupe_live_events(all_events, max_items=max_items)
    if not live_events:
        warnings.append("活动源暂不可用")

    return live_events, warnings


@st.cache_data(show_spinner=False)
def get_realtime_feeds(refresh_bucket: int) -> tuple[list[dict], list[dict], str, list[str]]:
    del refresh_bucket  # 作为缓存分桶键使用
    warnings = []

    live_news = _build_live_news(max_items=24)
    if not live_news:
        live_news = DEFAULT_NEWS.copy()
        warnings.append("新闻源暂不可用，已自动回退到内置热点")

    live_events, event_warnings = _build_live_events(max_items=12)
    if event_warnings:
        warnings.extend(event_warnings)
    if not live_events:
        live_events = TODAY_EVENTS.copy()
        warnings.append("活动 API 暂不可用，已自动回退到内置活动池")

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return live_news, live_events, updated_at, warnings


def block_html(template: str) -> str:
    """Normalize HTML blocks to avoid markdown treating indented tags as code."""
    return textwrap.dedent(template).strip()


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f5f5f7;
            --bg-2: #eef2f8;
            --surface: #ffffff;
            --surface-soft: #f8f9fc;
            --text-main: #1d1d1f;
            --text-muted: #6e6e73;
            --deep-blue: #0f3f79;
            --deep-blue-2: #174d8f;
            --champagne: #c7a96d;
            --teal: #1f9f98;
            --line: rgba(15, 63, 121, 0.12);
            --shadow: 0 20px 50px rgba(27, 46, 78, 0.08);
            --shadow-soft: 0 10px 28px rgba(27, 46, 78, 0.06);
        }

        .stApp {
            background:
                radial-gradient(1200px 520px at 90% -8%, rgba(15, 63, 121, 0.09), transparent 62%),
                radial-gradient(880px 440px at -5% 10%, rgba(199, 169, 109, 0.16), transparent 64%),
                linear-gradient(165deg, var(--bg) 0%, var(--bg-2) 100%);
            color: var(--text-main) !important;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", sans-serif;
        }

        .main .block-container {
            max-width: 1120px;
            padding-top: 1.1rem;
            padding-bottom: 2.8rem;
        }

        h1, h2, h3, h4 {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", sans-serif !important;
            color: var(--text-main) !important;
            letter-spacing: -0.01em;
            font-weight: 700 !important;
        }

        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.88);
            border-right: 1px solid rgba(15, 63, 121, 0.1);
            backdrop-filter: blur(14px);
        }

        [data-testid="stSidebar"] * {
            color: var(--text-main);
        }

        .stSelectbox label,
        .stTextArea label {
            color: #425466 !important;
            font-weight: 700;
            letter-spacing: 0;
        }

        .stTextArea textarea {
            border-radius: 14px !important;
            border: 1px solid rgba(15, 63, 121, 0.14) !important;
            background: #ffffff !important;
            color: var(--text-main) !important;
        }

        .stButton > button {
            border-radius: 999px !important;
            border: 0 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            padding: 0.42rem 1rem !important;
            background: linear-gradient(135deg, var(--deep-blue) 0%, var(--teal) 100%) !important;
            box-shadow: 0 10px 26px rgba(15, 63, 121, 0.2);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 34px rgba(15, 63, 121, 0.27);
        }

        .hero {
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 255, 0.95));
            border: 1px solid var(--line);
            border-radius: 30px;
            padding: 1.3rem 1.4rem 1.35rem;
            box-shadow: var(--shadow);
            overflow: hidden;
            position: relative;
            animation: fadeUp 0.7s ease both;
        }

        .hero::after {
            content: "";
            position: absolute;
            inset: -1px;
            border-radius: 30px;
            background: linear-gradient(120deg, rgba(15, 63, 121, 0.06), rgba(199, 169, 109, 0.16), rgba(31, 159, 152, 0.08));
            pointer-events: none;
        }

        .hero-grid {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 1rem;
            position: relative;
            z-index: 2;
        }

        .hero-title {
            font-size: clamp(1.65rem, 3vw, 2.75rem);
            line-height: 1.05;
            margin: 0 0 0.45rem;
            letter-spacing: -0.03em;
            color: #121519;
        }

        .hero-sub {
            color: var(--text-muted);
            margin-bottom: 0.92rem;
            line-height: 1.65;
            font-size: 1.01rem;
        }

        .hero-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
        }

        .hero-chip {
            background: #ffffff;
            border: 1px solid rgba(15, 63, 121, 0.14);
            color: #2f4667;
            border-radius: 999px;
            padding: 0.31rem 0.7rem;
            font-size: 0.83rem;
            font-weight: 700;
            box-shadow: 0 6px 16px rgba(15, 63, 121, 0.06);
        }

        .index-panel {
            background: linear-gradient(165deg, #ffffff, #f6f8fc);
            border-radius: 24px;
            border: 1px solid rgba(15, 63, 121, 0.12);
            padding: 0.9rem;
            text-align: center;
            position: relative;
            overflow: hidden;
            box-shadow: var(--shadow-soft);
        }

        .index-ring {
            width: 168px;
            height: 168px;
            margin: 0.1rem auto 0.45rem;
            border-radius: 50%;
            background:
                radial-gradient(circle at center, #ffffff 58%, transparent 59%),
                conic-gradient(var(--deep-blue) calc(var(--score) * 1%), var(--champagne) calc(var(--score) * 1%), rgba(152, 166, 185, 0.34) 0);
            display: grid;
            place-items: center;
            box-shadow: inset 0 0 24px rgba(15, 63, 121, 0.08), 0 8px 24px rgba(15, 63, 121, 0.08);
            animation: pulseGlow 2.8s ease-in-out infinite;
        }

        .index-number {
            font-family: "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 2.7rem;
            font-weight: 700;
            color: var(--deep-blue);
            line-height: 1;
            letter-spacing: -0.02em;
        }

        .index-label {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 0.28rem;
        }

        .section-title {
            margin: 1.15rem 0 0.3rem;
            font-size: clamp(1.15rem, 1.9vw, 1.56rem);
            letter-spacing: -0.01em;
            color: #1f2937;
        }

        .section-desc {
            color: var(--text-muted);
            margin-bottom: 0.65rem;
        }

        .split-title {
            margin: 0.85rem 0 0.25rem;
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--deep-blue);
            letter-spacing: -0.01em;
        }

        .split-desc {
            color: #667085;
            font-size: 0.88rem;
            margin-bottom: 0.46rem;
        }

        .timeline {
            position: relative;
            padding-left: 1.1rem;
            margin-top: 0.26rem;
        }

        .timeline::before {
            content: "";
            position: absolute;
            left: 0.23rem;
            top: 0.2rem;
            bottom: 0.2rem;
            width: 2px;
            background: linear-gradient(180deg, rgba(15, 63, 121, 0.4), rgba(31, 159, 152, 0.32));
        }

        .timeline-item {
            position: relative;
            margin-bottom: 0.7rem;
            background: var(--surface);
            border: 1px solid rgba(15, 63, 121, 0.1);
            border-radius: 16px;
            padding: 0.62rem 0.72rem 0.64rem;
            animation: fadeUp 0.58s ease both;
            animation-delay: var(--d, 0s);
            box-shadow: var(--shadow-soft);
        }

        .timeline-item::before {
            content: "";
            position: absolute;
            left: -1.04rem;
            top: 0.8rem;
            width: 11px;
            height: 11px;
            border-radius: 50%;
            border: 2px solid var(--deep-blue);
            background: #ffffff;
            box-shadow: 0 0 0 3px rgba(15, 63, 121, 0.1);
        }

        .timeline-top {
            display: flex;
            justify-content: space-between;
            gap: 0.6rem;
            align-items: center;
            margin-bottom: 0.28rem;
        }

        .timeline-time {
            font-family: "SF Pro Text", -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 1rem;
            color: var(--deep-blue);
            font-weight: 700;
            white-space: nowrap;
        }

        .priority {
            border-radius: 999px;
            font-size: 0.73rem;
            font-weight: 700;
            padding: 0.15rem 0.52rem;
            letter-spacing: 0.03em;
        }

        .p-high {
            color: #b42318;
            background: #ffe6e2;
            border: 1px solid #ffc3bb;
        }

        .p-mid {
            color: #8d5f10;
            background: #fff4dd;
            border: 1px solid #f4deb0;
        }

        .p-low {
            color: #0e766f;
            background: #e5f8f4;
            border: 1px solid #bdece3;
        }

        .timeline-title {
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 0.2rem;
        }

        .timeline-note {
            color: var(--text-muted);
            font-size: 0.88rem;
            line-height: 1.45;
        }

        .waterfall {
            column-count: 2;
            column-gap: 0.84rem;
        }

        .wf-card {
            break-inside: avoid;
            margin: 0 0 0.78rem;
            background: var(--surface);
            border: 1px solid rgba(15, 63, 121, 0.1);
            border-radius: 18px;
            padding: 0.72rem;
            box-shadow: var(--shadow-soft);
            animation: fadeUp 0.55s ease both;
            animation-delay: var(--d, 0s);
        }

        .wf-tag {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.74rem;
            border-radius: 999px;
            padding: 0.16rem 0.56rem;
            margin-bottom: 0.45rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }

        .tag-news {
            color: #75511b;
            background: #fdf4e4;
            border: 1px solid #f2dfbd;
        }

        .tag-event {
            color: #0f6d67;
            background: #e8f8f5;
            border: 1px solid #c7eee8;
        }

        .wf-title {
            font-weight: 800;
            color: #1f2937;
            margin-bottom: 0.3rem;
            line-height: 1.35;
        }

        .wf-meta {
            color: #6b7280;
            font-size: 0.82rem;
            margin-bottom: 0.35rem;
            line-height: 1.4;
        }

        .wf-reason,
        .wf-action {
            font-size: 0.9rem;
            line-height: 1.5;
            margin-top: 0.26rem;
        }

        .wf-reason {
            color: #334155;
        }

        .wf-action {
            color: #0d7d77;
            border-top: 1px dashed rgba(31, 159, 152, 0.3);
            padding-top: 0.35rem;
        }

        .model-card {
            background: linear-gradient(160deg, #ffffff, #f8fbff);
            border: 1px solid rgba(15, 63, 121, 0.11);
            border-radius: 20px;
            padding: 0.85rem;
            height: 100%;
            animation: fadeUp 0.6s ease both;
            box-shadow: var(--shadow-soft);
        }

        .model-title {
            font-size: 1rem;
            font-weight: 800;
            color: var(--deep-blue);
            margin-bottom: 0.38rem;
        }

        .model-body {
            color: #334155;
            line-height: 1.58;
            font-size: 0.92rem;
        }

        .model-metric {
            display: flex;
            gap: 0.55rem;
            margin-top: 0.5rem;
        }

        .metric-box {
            flex: 1;
            border: 1px solid rgba(15, 63, 121, 0.12);
            border-radius: 12px;
            padding: 0.45rem 0.5rem;
            background: #f7f9fc;
        }

        .metric-name {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-bottom: 0.1rem;
        }

        .metric-val {
            font-family: "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 1.06rem;
            color: var(--deep-blue-2);
            font-weight: 700;
        }

        .footer-note {
            color: #6e6e73;
            font-size: 0.85rem;
            margin-top: 0.8rem;
            text-align: center;
        }

        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes pulseGlow {
            0%, 100% { box-shadow: inset 0 0 24px rgba(15, 63, 121, 0.08), 0 0 0 rgba(31, 159, 152, 0.08); }
            50% { box-shadow: inset 0 0 24px rgba(15, 63, 121, 0.08), 0 0 20px rgba(31, 159, 152, 0.14); }
        }

        @media (max-width: 900px) {
            .hero-grid {
                grid-template-columns: 1fr;
            }

            .index-ring {
                width: 150px;
                height: 150px;
            }
        }

        @media (max-width: 600px) {
            .waterfall {
                column-count: 1;
            }
        }

        @media (max-width: 480px) {
            .main .block-container {
                padding: 0.65rem 0.72rem 2rem;
            }

            .hero {
                border-radius: 22px;
                padding: 0.92rem;
            }

            .hero-title {
                font-size: 1.55rem;
            }

            .index-ring {
                width: 132px;
                height: 132px;
            }

            .index-number {
                font-size: 2.2rem;
            }

            .timeline-item {
                padding: 0.55rem 0.6rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def priority_weight(level: str) -> int:
    order = {"高": 0, "中": 1, "低": 2}
    return order.get(level, 3)


def build_today_actions(boss: dict, matched_events: list[dict], matched_news: list[dict]) -> list[dict]:
    actions: list[dict] = []
    schedule = sorted(boss.get("today_schedule", []), key=lambda x: (priority_weight(x.get("priority", "低")), x.get("time", "99:99")))

    for item in schedule[:4]:
        actions.append(
            {
                "time": item.get("time", "今日"),
                "priority": item.get("priority", "中"),
                "title": item.get("title", "执行关键任务"),
                "reason": f"日程类型：{item.get('type', '任务')}，属于你今天的核心推进动作。",
            }
        )

    if matched_events:
        top_event = matched_events[0]
        kw = "、".join(top_event.get("matched_keywords", [])[:2]) or "行业机会"
        actions.append(
            {
                "time": "今天",
                "priority": "高" if top_event.get("value") == "高" else "中",
                "title": f"确认活动：{top_event['title']}",
                "reason": f"活动与你的「{kw}」高度匹配，适合用来拓展当下高价值连接。",
            }
        )

    if matched_news:
        top_news = matched_news[0]
        actions.append(
            {
                "time": "今天",
                "priority": "中" if top_news.get("score", 0) < 70 else "高",
                "title": f"商机动作：{get_action(top_news.get('category', '政策'))}",
                "reason": f"该动作来自「{top_news.get('title', '')[:22]}...」热点，利于当天形成可执行闭环。",
            }
        )

    unique_titles = set()
    deduped = []
    for act in actions:
        if act["title"] not in unique_titles:
            unique_titles.add(act["title"])
            deduped.append(act)
    return deduped[:6]


def compute_opportunity_index(schedule: list[dict], matched_events: list[dict], matched_news: list[dict]) -> tuple[int, str]:
    high_cnt = sum(1 for item in schedule if item.get("priority") == "高")
    deadline_cnt = sum(1 for item in schedule if item.get("type") == "截止日")
    top_news = matched_news[0].get("score", 20) if matched_news else 22

    event_component = min(len(matched_events) * 26, 100)
    schedule_component = min(high_cnt * 24 + deadline_cnt * 16 + len(schedule) * 7, 100)
    news_component = min(top_news + (8 if matched_news else 0), 100)

    idx = int(news_component * 0.52 + event_component * 0.24 + schedule_component * 0.24)
    idx = max(28, min(98, idx))

    if idx >= 78:
        level = "高机会窗口"
    elif idx >= 58:
        level = "可进攻区间"
    else:
        level = "稳健观察区"
    return idx, level


def render_hero(boss: dict, score: int, level: str, today_str: str) -> None:
    hero_html = block_html(
        f"""
        <section class="hero">
          <div class="hero-grid">
            <div>
              <div class="hero-title">今日机会指数仪表盘</div>
              <div class="hero-sub">{html.escape(today_str)} ｜ 为 {html.escape(boss['name'])} 定制。先执行关键动作，再放大高相关机会。</div>
              <div class="hero-chip-row">
                <span class="hero-chip">{html.escape(boss['industry'])}</span>
                <span class="hero-chip">{html.escape(boss['city'])}</span>
                <span class="hero-chip">目标：{html.escape(boss['current_goal'])}</span>
              </div>
            </div>
            <div class="index-panel">
              <div class="index-ring" style="--score:{score};">
                <div>
                  <div class="index-number">{score}</div>
                  <div class="index-label">机会指数 / 100</div>
                </div>
              </div>
              <div class="index-label" style="color:#173f74; font-weight:700;">状态：{html.escape(level)}</div>
            </div>
          </div>
        </section>
        """
    )
    st.markdown(hero_html, unsafe_allow_html=True)


def render_kpi_counter(schedule_count: int, event_count: int, news_count: int, score: int) -> None:
    html_block = f"""
    <style>
    .kpi-wrap {{
      display:grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 10px;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", sans-serif;
    }}
    .kpi-box {{
      background: linear-gradient(165deg, #ffffff, #f8fbff);
      border: 1px solid rgba(15, 63, 121, 0.12);
      border-radius: 18px;
      padding: 10px 12px;
      color: #1f2937;
      box-shadow: 0 10px 24px rgba(15, 63, 121, 0.08);
    }}
    .kpi-label {{ color:#6b7280; font-size:12px; margin-bottom:2px; }}
    .kpi-value {{ font-size:30px; line-height:1.05; font-family:-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif; color:#123f74; font-weight:700; letter-spacing:-0.02em; }}
    .kpi-suffix {{ font-size:13px; color:#1f9f98; margin-left:3px; }}
    @media (max-width: 640px) {{ .kpi-wrap {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
    </style>
    <div class="kpi-wrap">
      <div class="kpi-box"><div class="kpi-label">机会指数</div><div class="kpi-value"><span class="count" data-target="{score}">0</span><span class="kpi-suffix">/100</span></div></div>
      <div class="kpi-box"><div class="kpi-label">今日关键任务</div><div class="kpi-value"><span class="count" data-target="{schedule_count}">0</span><span class="kpi-suffix">项</span></div></div>
      <div class="kpi-box"><div class="kpi-label">可打活动</div><div class="kpi-value"><span class="count" data-target="{event_count}">0</span><span class="kpi-suffix">个</span></div></div>
      <div class="kpi-box"><div class="kpi-label">高相关热点</div><div class="kpi-value"><span class="count" data-target="{news_count}">0</span><span class="kpi-suffix">条</span></div></div>
    </div>
    <script>
      const nums = document.querySelectorAll('.count');
      nums.forEach((el) => {{
        const target = Number(el.dataset.target || 0);
        const start = performance.now();
        const dur = 1000;
        const tick = (ts) => {{
          const p = Math.min((ts - start) / dur, 1);
          const eased = 1 - Math.pow(1 - p, 3);
          el.textContent = String(Math.round(target * eased));
          if (p < 1) requestAnimationFrame(tick);
        }};
        requestAnimationFrame(tick);
      }});
    </script>
    """
    components.html(html_block, height=168)


def render_timeline(actions: list[dict]) -> None:
    st.markdown("<div class='section-title'>1. 今天该做什么</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-desc'>先执行最能推进目标的动作，确保一天有结果，而不是只有忙碌感。</div>", unsafe_allow_html=True)

    if not actions:
        st.info("当前没有可执行动作，建议先补充今日热点或切换老板画像。")
        return

    rows = []
    for idx, item in enumerate(actions, 1):
        pri = item.get("priority", "中")
        pri_class = "p-high" if pri == "高" else ("p-mid" if pri == "中" else "p-low")
        rows.append(
            block_html(
                f"""
                <div class="timeline-item" style="--d:{0.08 * idx:.2f}s;">
                  <div class="timeline-top">
                    <span class="timeline-time">{html.escape(item.get('time', '今天'))}</span>
                    <span class="priority {pri_class}">{html.escape(pri)}优先级</span>
                  </div>
                  <div class="timeline-title">{html.escape(item.get('title', '执行重点任务'))}</div>
                  <div class="timeline-note">{html.escape(item.get('reason', '围绕今日目标推进。'))}</div>
                </div>
                """
            )
        )

    block = "<div class='timeline'>" + "".join(rows) + "</div>"
    st.markdown(block, unsafe_allow_html=True)


def render_why_cards(matched_events: list[dict], matched_news: list[dict]) -> None:
    st.markdown("<div class='section-title'>2. 值得做</div>", unsafe_allow_html=True)

    has_events = bool(matched_events)
    has_news = bool(matched_news)

    if not has_events and not has_news:
        st.info("暂无高相关证据卡片，建议先增加一两条自定义热点来提高匹配度。")
        return

    if has_events:
        st.markdown("<div class='split-title'>什么值得做</div>", unsafe_allow_html=True)
        st.markdown("<div class='split-desc'>优先看今天能立刻触达的人和场景。</div>", unsafe_allow_html=True)

        event_cards: list[str] = []
        for idx, event in enumerate(matched_events, 1):
            matched_kw = "、".join(event.get("matched_keywords", [])[:3]) or "行业相关"
            event_cards.append(
                block_html(
                    f"""
                    <article class="wf-card" style="--d:{0.08 * idx:.2f}s;">
                                            <div class="wf-tag tag-event">什么值得做</div>
                      <div class="wf-title">{html.escape(event.get('title', '商业活动'))}</div>
                      <div class="wf-meta">{html.escape(event.get('time', '今日'))} ｜ {html.escape(event.get('format', '线上'))} ｜ {html.escape(event.get('location', '待确认'))}</div>
                      <div class="wf-reason">匹配理由：与你的「{html.escape(matched_kw)}」方向高度一致，且活动价值级别为 {html.escape(event.get('value', '中'))}。</div>
                      <div class="wf-action">建议动作：{html.escape(event.get('registration_deadline', '尽快确认报名'))}</div>
                    </article>
                    """
                )
            )

        st.markdown("<div class='waterfall'>" + "".join(event_cards) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='split-title'>什么值得做</div>", unsafe_allow_html=True)
        st.caption("今天暂无高匹配活动。")

    if has_news:
        st.markdown("<div class='split-title'>为什么值得做</div>", unsafe_allow_html=True)
        st.markdown("<div class='split-desc'>热点商机提供外部证据，说明这件事为什么现在就要做。</div>", unsafe_allow_html=True)

        news_cards: list[str] = []
        for idx, news in enumerate(matched_news, 1):
            score = int(news.get("score", 0))
            matched_kw = "、".join(news.get("matched", [])[:2]) or news.get("category", "资讯")
            action = get_action(news.get("category", "政策"))
            news_cards.append(
                block_html(
                    f"""
                    <article class="wf-card" style="--d:{0.08 * idx:.2f}s;">
                      <div class="wf-tag tag-news">热点商机</div>
                      <div class="wf-title">{html.escape(news.get('title', '行业热点'))}</div>
                      <div class="wf-meta">相关度 {score} 分 ｜ 类别：{html.escape(news.get('category', '资讯'))} ｜ 关键词：{html.escape(matched_kw)}</div>
                      <div class="wf-reason">机会解释：该热点与当前业务路径有直接连接，具备短期转化可能。</div>
                      <div class="wf-action">建议动作：{html.escape(action)}</div>
                    </article>
                    """
                )
            )

        st.markdown("<div class='waterfall'>" + "".join(news_cards) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='split-title'>为什么值得做</div>", unsafe_allow_html=True)
        st.caption("当前暂无高相关热点。")


def render_model_explainer(boss: dict, matched_news: list[dict]) -> None:
    st.markdown("<div class='section-title'>3. 模型解释与推演</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-desc'>最后再看模型层：给你一个联系人建议和MiroFish推演，辅助判断推进节奏。</div>", unsafe_allow_html=True)

    if not matched_news:
        st.info("暂无可解释的高相关热点，模型推演暂不触发。")
        return

    top_news = matched_news[0]
    network = get_network_suggestion(boss, top_news)
    relevance = "高相关" if top_news.get("score", 0) >= 60 else "中相关"
    miro = get_mirofish(top_news, relevance)

    left_col, right_col = st.columns(2)

    with left_col:
        if network:
            st.markdown(
                block_html(
                    f"""
                    <div class="model-card">
                      <div class="model-title">人脉建议</div>
                      <div class="model-body">建议联系：{html.escape(network['name'])}（{html.escape(network['role'])}）<br>
                      联系理由：{html.escape(network['reason'])}</div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                block_html(
                    """
                    <div class="model-card">
                      <div class="model-title">人脉建议</div>
                      <div class="model-body">当前画像缺少可联系人脉，建议先补充 3-5 位关键联系人用于后续提醒。</div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

    with right_col:
        advice = "推进" if miro.get("advice") == "推进" else "观察"
        st.markdown(
            block_html(
                f"""
                <div class="model-card">
                  <div class="model-title">MiroFish 快速推演</div>
                  <div class="model-body">最高价值商机：{html.escape(top_news.get('title', '重点热点')[:36])}...<br>
                  主要风险：{html.escape(miro.get('risk', '市场波动'))}<br>
                  AI建议：{html.escape(advice)}</div>
                  <div class="model-metric">
                    <div class="metric-box">
                      <div class="metric-name">时间窗口</div>
                      <div class="metric-val">{html.escape(miro.get('window', '2-3个月'))}</div>
                    </div>
                    <div class="metric-box">
                      <div class="metric-name">预估收益</div>
                      <div class="metric-val">{html.escape(miro.get('revenue', '¥5万 - ¥15万'))}</div>
                    </div>
                  </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )


inject_styles()

with st.sidebar:
    st.markdown("## 🧭 AI商业参谋")
    st.caption("浅色旗舰版 · Apple风格信息设计")
    st.divider()

    boss_options = {f"{b['name']} · {b['industry']}": b for b in BOSSES}
    selected_label = st.selectbox("选择老板画像", list(boss_options.keys()))
    selected_boss = boss_options[selected_label]

    st.divider()
    custom_news_text = st.text_area(
        "追加热点（每行一条）",
        placeholder="例如：\n广州某产业园给AI企业提供最高200万补贴\n抖音发布新类目冷启动扶持计划",
        height=128,
    )

    st.divider()
    refresh_minutes = st.selectbox("定时刷新频率（分钟）", [5, 10, 15, 30], index=1)
    if st_autorefresh is not None:
        st_autorefresh(interval=refresh_minutes * 60 * 1000, key="auto_refresh")

    refresh = st.button("刷新机会雷达", use_container_width=True)

    mode_caption = st.empty()
    count_caption = st.empty()
    update_caption = st.empty()
    warning_caption = st.empty()


refresh_bucket = int(time.time() // (refresh_minutes * 60))
if refresh:
    get_realtime_feeds.clear()
    st.toast("已手动刷新实时数据", icon="🔄")

live_news, live_events, live_updated_at, live_warnings = get_realtime_feeds(refresh_bucket)

mode_caption.caption(f"当前：实时联网模式（本土新闻/政策 + 本土活动，国际 API 可选补充；每 {refresh_minutes} 分钟自动刷新）")
count_caption.caption(f"系统热点 {len(live_news)} 条 · 活动池 {len(live_events)} 条")
update_caption.caption(f"更新时间：{live_updated_at}")
if live_warnings:
    warning_caption.caption("数据源降级：" + "；".join(live_warnings))


extra_news: list[dict] = []
if custom_news_text.strip():
    for i, line in enumerate(custom_news_text.strip().splitlines(), 1):
        text = line.strip()
        if text:
            extra_news.append({"id": f"C{i:02d}", "title": text, "category": "自定义"})

if refresh:
    st.toast("机会雷达已更新", icon="✨")

all_news = live_news + extra_news
matched_events = match_events_for_boss(selected_boss, live_events)
matched_news = match_news_for_boss(selected_boss, all_news)
schedule = selected_boss.get("today_schedule", [])

today_str = datetime.now().strftime("%Y年%m月%d日")
score, score_label = compute_opportunity_index(schedule, matched_events, matched_news)
actions = build_today_actions(selected_boss, matched_events, matched_news)

render_hero(selected_boss, score, score_label, today_str)

render_kpi_counter(
    schedule_count=len(actions),
    event_count=len(matched_events),
    news_count=len(matched_news),
    score=score,
)

render_timeline(actions)
render_why_cards(matched_events, matched_news)
render_model_explainer(selected_boss, matched_news)

st.markdown("<div class='footer-note'>AI商业参谋 · 高保真UI预览版 ｜ 信息顺序：做什么 → 为什么做 → 模型解释</div>", unsafe_allow_html=True)
