"""AI商业参谋 - 高保真UI预览版（Streamlit）。"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import html
import ipaddress
import math
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

MAJOR_CITY_COORDS = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "杭州": (30.2741, 120.1551),
    "南京": (32.0603, 118.7969),
    "苏州": (31.2989, 120.5853),
    "成都": (30.5728, 104.0668),
    "重庆": (29.5630, 106.5516),
    "武汉": (30.5928, 114.3055),
    "西安": (34.3416, 108.9398),
    "天津": (39.3434, 117.3616),
    "长沙": (28.2282, 112.9388),
    "郑州": (34.7466, 113.6254),
    "青岛": (36.0671, 120.3826),
    "宁波": (29.8683, 121.5440),
    "厦门": (24.4798, 118.0894),
    "合肥": (31.8206, 117.2272),
    "福州": (26.0745, 119.2965),
    "东莞": (23.0207, 113.7518),
    "佛山": (23.0215, 113.1214),
    "济南": (36.6512, 117.1201),
}

MAJOR_CITY_ALIASES = {
    "北京市": "北京",
    "上海市": "上海",
    "广州市": "广州",
    "深圳市": "深圳",
    "杭州市": "杭州",
    "南京市": "南京",
    "苏州市": "苏州",
    "成都市": "成都",
    "重庆市": "重庆",
    "武汉市": "武汉",
    "西安市": "西安",
    "天津市": "天津",
    "长沙市": "长沙",
    "郑州市": "郑州",
    "青岛市": "青岛",
    "宁波市": "宁波",
    "厦门市": "厦门",
    "合肥市": "合肥",
    "福州市": "福州",
    "东莞市": "东莞",
    "佛山市": "佛山",
    "济南市": "济南",
}

MAX_TRAVEL_HOURS = 2.0
TIME_VALUE_PER_HOUR_RMB = 220


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


def _is_public_ip(ip_text: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip_text)
    except Exception:
        return False
    return not (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def _extract_public_ipv4(raw_text: str) -> str:
    if not raw_text:
        return ""
    candidates = re.findall(r"(?:\d{1,3}\.){3}\d{1,3}", raw_text)
    for ip_text in candidates:
        if _is_public_ip(ip_text):
            return ip_text
    return ""


def _get_request_headers() -> dict:
    headers: dict = {}

    try:
        context_headers = getattr(getattr(st, "context", None), "headers", None)
        if context_headers:
            headers.update(dict(context_headers))
    except Exception:
        pass

    if headers:
        return headers

    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers

        websocket_headers = _get_websocket_headers() or {}
        headers.update(dict(websocket_headers))
    except Exception:
        pass

    return headers


def _extract_client_ip() -> str:
    headers = _get_request_headers()
    if not headers:
        return ""

    normalized = {str(k).lower(): str(v) for k, v in headers.items()}
    for key in [
        "x-forwarded-for",
        "x-real-ip",
        "cf-connecting-ip",
        "x-client-ip",
        "x-original-forwarded-for",
    ]:
        ip_text = _extract_public_ipv4(normalized.get(key, ""))
        if ip_text:
            return ip_text

    return ""


@st.cache_data(show_spinner=False)
def _lookup_ip_geo(ip_text: str) -> dict:
    if not ip_text:
        return {"ok": False}

    primary = _safe_api_get_json(f"https://ipwho.is/{ip_text}")
    if primary and primary.get("success"):
        try:
            lat = float(primary.get("latitude"))
            lon = float(primary.get("longitude"))
        except Exception:
            lat = None
            lon = None

        if lat is not None and lon is not None:
            return {
                "ok": True,
                "ip": ip_text,
                "city": (primary.get("city") or "").strip(),
                "region": (primary.get("region") or "").strip(),
                "country": (primary.get("country_code") or "").strip(),
                "lat": lat,
                "lon": lon,
                "provider": "ipwho.is",
            }

    secondary = _safe_api_get_json(f"https://ipapi.co/{ip_text}/json/")
    if secondary and not secondary.get("error"):
        try:
            lat = float(secondary.get("latitude"))
            lon = float(secondary.get("longitude"))
        except Exception:
            lat = None
            lon = None

        if lat is not None and lon is not None:
            return {
                "ok": True,
                "ip": ip_text,
                "city": (secondary.get("city") or "").strip(),
                "region": (secondary.get("region") or "").strip(),
                "country": (secondary.get("country_code") or "").strip(),
                "lat": lat,
                "lon": lon,
                "provider": "ipapi.co",
            }

    return {"ok": False, "ip": ip_text}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def _estimate_trip(distance_km: float) -> dict:
    if distance_km <= 30:
        mode = "市内交通"
        travel_hours = max(0.35, 0.25 + distance_km / 35)
        transport_cost = max(12.0, distance_km * 2.2)
    elif distance_km <= 260:
        mode = "高铁/城际交通"
        travel_hours = 0.65 + distance_km / 210
        transport_cost = 35.0 + distance_km * 0.48
    else:
        mode = "航班+地面交通"
        travel_hours = 2.3 + distance_km / 650
        transport_cost = 260.0 + distance_km * 0.8

    time_cost = travel_hours * TIME_VALUE_PER_HOUR_RMB
    total_cost = transport_cost + time_cost
    return {
        "travel_mode": mode,
        "travel_hours": round(travel_hours, 2),
        "distance_km": round(distance_km, 1),
        "transport_cost_rmb": round(transport_cost, 0),
        "time_cost_rmb": round(time_cost, 0),
        "total_trip_cost_rmb": round(total_cost, 0),
    }


def _extract_event_city(event: dict) -> str:
    text = f"{event.get('location', '')} {event.get('title', '')}"
    for alias, canonical in MAJOR_CITY_ALIASES.items():
        if alias in text:
            return canonical
    for city in MAJOR_CITY_COORDS:
        if city in text:
            return city
    return ""


def _nearest_major_city(lat: float, lon: float) -> dict:
    best_city = ""
    best_distance = float("inf")
    for city, (city_lat, city_lon) in MAJOR_CITY_COORDS.items():
        distance = _haversine_km(lat, lon, city_lat, city_lon)
        if distance < best_distance:
            best_distance = distance
            best_city = city
    return {"city": best_city, "distance_km": round(best_distance, 1)}


def _build_reachable_city_scope(lat: float, lon: float, max_travel_hours: float) -> list[dict]:
    reachable: list[dict] = []
    for city, (city_lat, city_lon) in MAJOR_CITY_COORDS.items():
        distance = _haversine_km(lat, lon, city_lat, city_lon)
        plan = _estimate_trip(distance)
        if plan["travel_hours"] <= max_travel_hours:
            reachable.append({"city": city, **plan})

    reachable.sort(key=lambda item: (item.get("travel_hours", 99), item.get("distance_km", 9999)))
    return reachable


def _attach_online_trip_fields(event: dict) -> dict:
    event_copy = {**event}
    event_copy["event_city"] = "线上"
    event_copy["travel_mode"] = "线上参加"
    event_copy["travel_hours"] = 0.0
    event_copy["distance_km"] = 0.0
    event_copy["transport_cost_rmb"] = 0.0
    event_copy["time_cost_rmb"] = 0.0
    event_copy["total_trip_cost_rmb"] = 0.0
    event_copy["travel_brief"] = "线上参加，交通成本≈¥0"
    event_copy["travel_note"] = "线上参加，交通成本约 ¥0，时间成本为通勤 0 小时。"
    return event_copy


def apply_ip_proximity_filter(events: list[dict], max_travel_hours: float = MAX_TRAVEL_HOURS) -> tuple[list[dict], dict, list[str]]:
    warnings: list[str] = []
    if not events:
        return [], {"enabled": False}, warnings

    client_ip = _extract_client_ip()
    if not client_ip:
        warnings.append("未识别到用户IP，暂未启用1-2小时路程硬过滤")
        return [{**event} for event in events], {"enabled": False}, warnings

    geo = _lookup_ip_geo(client_ip)
    if not geo.get("ok"):
        warnings.append("用户IP定位失败，暂未启用1-2小时路程硬过滤")
        return [{**event} for event in events], {"enabled": False, "ip": client_ip}, warnings

    user_lat = float(geo.get("lat"))
    user_lon = float(geo.get("lon"))

    city_scope = _build_reachable_city_scope(user_lat, user_lon, max_travel_hours=max_travel_hours)
    allowed_cities = {item["city"] for item in city_scope}

    filtered: list[dict] = []
    far_events: list[dict] = []
    unknown_offline_count = 0

    for event in events:
        text = f"{event.get('format', '')} {event.get('location', '')}"
        is_online = "线上" in text or event.get("format") == "线上"
        if is_online:
            filtered.append(_attach_online_trip_fields(event))
            continue

        event_city = _extract_event_city(event)
        if not event_city:
            unknown_offline_count += 1
            continue

        city_lat, city_lon = MAJOR_CITY_COORDS[event_city]
        distance = _haversine_km(user_lat, user_lon, city_lat, city_lon)
        trip = _estimate_trip(distance)

        event_copy = {**event}
        event_copy["event_city"] = event_city
        event_copy.update(trip)
        event_copy["travel_brief"] = f"单程 {trip['travel_hours']:.1f} 小时，交通约 ¥{trip['transport_cost_rmb']:.0f}"
        event_copy["travel_note"] = (
            f"单程约 {trip['travel_hours']:.1f} 小时（{trip['travel_mode']}），"
            f"交通约 ¥{trip['transport_cost_rmb']:.0f}，时间成本约 ¥{trip['time_cost_rmb']:.0f}。"
        )

        if event_city in allowed_cities and trip["travel_hours"] <= max_travel_hours:
            filtered.append(event_copy)
        else:
            far_events.append(event_copy)

    if unknown_offline_count:
        warnings.append(f"有 {unknown_offline_count} 个线下活动未识别城市，已按硬过滤剔除")

    if far_events:
        nearest = min(far_events, key=lambda item: item.get("travel_hours", 99))
        warnings.append(
            f"已剔除 {len(far_events)} 个超出{max_travel_hours:.0f}小时范围的线下活动；"
            f"最近一项单程约 {nearest.get('travel_hours', 0):.1f} 小时，交通约 ¥{nearest.get('transport_cost_rmb', 0):.0f}"
        )

    if not filtered:
        warnings.append("IP硬过滤后暂无可达活动，建议优先线上活动或放宽城市圈")

    nearest_city = _nearest_major_city(user_lat, user_lon)
    profile = {
        "enabled": True,
        "ip": client_ip,
        "city": geo.get("city", ""),
        "region": geo.get("region", ""),
        "country": geo.get("country", ""),
        "provider": geo.get("provider", ""),
        "nearest_major_city": nearest_city.get("city", ""),
        "nearest_major_city_distance_km": nearest_city.get("distance_km", 0),
        "scope_cities": [item["city"] for item in city_scope[:8]],
    }
    return filtered, profile, warnings


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
        warnings.append("活动源暂不可用，已自动回退到内置活动池")

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


def _fallback_news_candidates(boss: dict, news_items: list[dict], top_n: int = 4) -> list[dict]:
    ignore_keywords = [kw.lower() for kw in boss.get("ignore_keywords", [])]
    boss_keywords = [kw.lower() for kw in boss.get("keywords", [])]
    city = boss.get("city", "")

    scored: list[dict] = []
    for item in news_items:
        title = str(item.get("title", ""))
        category = str(item.get("category", ""))
        title_lower = title.lower()
        category_lower = category.lower()

        if any(ig in title_lower or ig in category_lower for ig in ignore_keywords):
            continue

        score = 8
        matched: list[str] = []

        for kw in boss_keywords:
            if kw and (kw in title_lower or kw in category_lower):
                score += 14
                matched.append(kw)

        if city and city in title:
            score += 8

        # 政策/行业热点默认给基础分，避免长期空白
        if category in {"政策", "金融", "AI科技", "电商", "外贸", "跨境电商", "制造业", "新能源", "法律科技"}:
            score += 8

        scored.append(
            {
                **item,
                "score": min(68, score),
                "matched": list(dict.fromkeys(matched))[:3] or [category or "行业热点"],
            }
        )

    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    return scored[:top_n]


def _fallback_event_candidates(boss: dict, events: list[dict], top_n: int = 3) -> list[dict]:
    ignore_keywords = [kw.lower() for kw in boss.get("ignore_keywords", [])]
    boss_keywords = [kw.lower() for kw in boss.get("keywords", [])]
    city = boss.get("city", "")

    scored: list[dict] = []
    for event in events:
        text = f"{event.get('title', '')} {event.get('description', '')}".lower()
        if any(ig in text for ig in ignore_keywords):
            continue

        score = 10
        matched_keywords: list[str] = []
        for kw in boss_keywords:
            if kw and (kw in text or any(kw in str(ek).lower() for ek in event.get("keywords", []))):
                score += 12
                matched_keywords.append(kw)

        if city and city in str(event.get("location", "")):
            score += 10
        if event.get("format") == "线上":
            score += 6
        if event.get("value") == "高":
            score += 6
        if float(event.get("travel_hours", 9) or 9) <= MAX_TRAVEL_HOURS:
            score += 8

        scored.append(
            {
                **event,
                "score": min(66, int(score)),
                "matched_keywords": list(dict.fromkeys(matched_keywords))[:3] or ["同城/低成本可达"],
            }
        )

    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    return scored[:top_n]


def _is_online_event(event: dict) -> bool:
    text = f"{event.get('format', '')} {event.get('location', '')}".lower()
    return (
        event.get("format") == "线上"
        or "线上" in text
        or "直播" in text
        or "webinar" in text
        or "online" in text
        or "腾讯会议" in text
        or "zoom" in text
    )


def _minimum_online_city_events(boss: dict, primary_events: list[dict], backup_events: list[dict], top_n: int = 2) -> tuple[list[dict], bool]:
    city = boss.get("city", "")
    merged = list(primary_events) + list(backup_events)

    deduped: list[dict] = []
    seen_titles = set()
    for event in merged:
        title_key = re.sub(r"\s+", " ", str(event.get("title", "")).lower()).strip()
        if not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(event)

    scored: list[tuple[int, int, dict]] = []
    for event in deduped:
        if not _is_online_event(event):
            continue

        event_copy = {**event}
        if "travel_note" not in event_copy:
            event_copy = _attach_online_trip_fields(event_copy)

        text = f"{event_copy.get('title', '')} {event_copy.get('location', '')} {event_copy.get('description', '')}"
        city_match = bool(city and city in text)
        base_score = 54 if city_match else 38
        if event_copy.get("value") == "高":
            base_score += 6

        event_copy["score"] = max(int(event_copy.get("score", 0) or 0), min(base_score, 72))
        event_copy["matched_keywords"] = event_copy.get("matched_keywords") or ([f"{city}线上"] if city_match else ["线上可达"])
        detail = str(event_copy.get("source_detail", "本土活动源"))
        suffix = "同城线上保障" if city_match else "全国线上补位"
        event_copy["source_detail"] = f"{detail} · {suffix}"
        if not event_copy.get("registration_deadline"):
            event_copy["registration_deadline"] = "详见活动页"

        scored.append((1 if city_match else 0, int(event_copy["score"]), event_copy))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [item[2] for item in scored[:top_n]]

    if len(selected) < top_n:
        for event in TODAY_EVENTS:
            if len(selected) >= top_n:
                break
            if not _is_online_event(event):
                continue
            if any(re.sub(r"\s+", " ", str(event.get("title", "")).lower()).strip() == re.sub(r"\s+", " ", str(s.get("title", "")).lower()).strip() for s in selected):
                continue

            event_copy = _attach_online_trip_fields(event)
            text = f"{event_copy.get('title', '')} {event_copy.get('location', '')} {event_copy.get('description', '')}"
            city_match = bool(city and city in text)
            event_copy["score"] = 50 if city_match else 42
            event_copy["matched_keywords"] = [f"{city}线上"] if city_match else ["线上可达"]
            event_copy["source_detail"] = str(event_copy.get("source_detail", "内置活动池")) + " · 最小展示保障"
            selected.append(event_copy)

    city_online_count = 0
    if city:
        for event in selected:
            text = f"{event.get('title', '')} {event.get('location', '')} {event.get('description', '')}"
            if city in text:
                city_online_count += 1

    return selected[:top_n], city_online_count >= top_n


def _minimum_local_policy_news(news_items: list[dict], top_n: int = 2) -> list[dict]:
    source_weight = {
        "中国政府网政策": 30,
        "百度民生": 24,
        "百度财经": 18,
    }

    deduped: list[dict] = []
    seen_titles = set()
    for item in news_items:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        key = re.sub(r"\s+", " ", title.lower()).strip()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        deduped.append(item)

    scored: list[tuple[int, int, dict]] = []
    for item in deduped:
        category = str(item.get("category", ""))
        if category != "政策":
            continue

        source = str(item.get("source", ""))
        weight = source_weight.get(source, 12)
        base_score = 38 + weight // 2
        news_copy = {
            **item,
            "score": max(int(item.get("score", 0) or 0), min(base_score, 70)),
            "matched": item.get("matched") or ["本土政策"],
            "source": source or "本土政策源",
        }
        scored.append((weight, int(news_copy["score"]), news_copy))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [item[2] for item in scored[:top_n]]

    if len(selected) < top_n:
        for item in DEFAULT_NEWS:
            if len(selected) >= top_n:
                break
            if item.get("category") != "政策":
                continue
            if any(str(item.get("title", "")).strip() == str(s.get("title", "")).strip() for s in selected):
                continue
            selected.append(
                {
                    **item,
                    "score": 46,
                    "matched": ["本土政策"],
                    "source": "内置政策样本",
                }
            )

    return selected[:top_n]


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
        travel_brief = top_event.get("travel_brief", "")
        reason = f"活动与你的「{kw}」高度匹配，适合用来拓展当下高价值连接。"
        if travel_brief:
            reason += f" 到场成本：{travel_brief}。"
        actions.append(
            {
                "time": "今天",
                "priority": "高" if top_event.get("value") == "高" else "中",
                "title": f"确认活动：{top_event['title']}",
                "reason": reason,
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
            travel_note = event.get("travel_note", "")
            travel_line = f"<div class=\"wf-action\">到场成本：{html.escape(travel_note)}</div>" if travel_note else ""
            event_cards.append(
                block_html(
                    f"""
                    <article class="wf-card" style="--d:{0.08 * idx:.2f}s;">
                                            <div class="wf-tag tag-event">什么值得做</div>
                      <div class="wf-title">{html.escape(event.get('title', '商业活动'))}</div>
                      <div class="wf-meta">{html.escape(event.get('time', '今日'))} ｜ {html.escape(event.get('format', '线上'))} ｜ {html.escape(event.get('location', '待确认'))}</div>
                      <div class="wf-reason">匹配理由：与你的「{html.escape(matched_kw)}」方向高度一致，且活动价值级别为 {html.escape(event.get('value', '中'))}。</div>
                      <div class="wf-action">建议动作：{html.escape(event.get('registration_deadline', '尽快确认报名'))}</div>
                      {travel_line}
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
    geo_caption = st.empty()
    scope_caption = st.empty()
    warning_caption = st.empty()


refresh_bucket = int(time.time() // (refresh_minutes * 60))
if refresh:
    get_realtime_feeds.clear()
    st.toast("已手动刷新实时数据", icon="🔄")

live_news, live_events, live_updated_at, live_warnings = get_realtime_feeds(refresh_bucket)
live_warnings = list(live_warnings)

live_events, user_geo_profile, geo_warnings = apply_ip_proximity_filter(live_events, max_travel_hours=MAX_TRAVEL_HOURS)
if geo_warnings:
    live_warnings.extend(geo_warnings)

if user_geo_profile.get("enabled"):
    city = user_geo_profile.get("city") or user_geo_profile.get("nearest_major_city") or "未知城市"
    region = user_geo_profile.get("region", "")
    geo_caption.caption(f"IP定位：{city}{(' · ' + region) if region else ''}（已启用1-2小时硬过滤）")
    scope_cities = user_geo_profile.get("scope_cities", [])
    if scope_cities:
        scope_caption.caption("可达大城市：" + "、".join(scope_cities[:6]))
    else:
        scope_caption.caption("可达大城市：暂无（仅保留线上活动）")
else:
    geo_caption.caption("IP定位：未识别（暂未启用1-2小时硬过滤）")
    scope_caption.caption("")

mode_caption.caption(f"当前：实时联网模式（本土新闻/政策 + 本土活动 + IP路程硬过滤；每 {refresh_minutes} 分钟自动刷新）")
count_caption.caption(f"系统热点 {len(live_news)} 条 · 活动池 {len(live_events)} 条")
update_caption.caption(f"更新时间：{live_updated_at}")
if live_warnings:
    warning_caption.caption("系统提示：" + "；".join(live_warnings))


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

if not matched_events and live_events:
    matched_events = _fallback_event_candidates(selected_boss, live_events, top_n=3)
    live_warnings.append("活动严格匹配结果为空，已启用同城/低出行成本宽松推荐")

if not matched_news and all_news:
    matched_news = _fallback_news_candidates(selected_boss, all_news, top_n=4)
    live_warnings.append("热点严格匹配结果为空，已启用行业热点宽松推荐")

if not matched_events:
    guaranteed_events, full_city_online = _minimum_online_city_events(selected_boss, live_events, TODAY_EVENTS, top_n=2)
    if guaranteed_events:
        matched_events = guaranteed_events
        if full_city_online:
            live_warnings.append("已启用最小展示保障：固定展示2条同城线上活动")
        else:
            live_warnings.append("已启用最小展示保障：同城线上不足，已用全国线上活动补齐2条")

if not matched_news:
    guaranteed_news = _minimum_local_policy_news(all_news + live_news + DEFAULT_NEWS, top_n=2)
    if guaranteed_news:
        matched_news = guaranteed_news
        live_warnings.append("已启用最小展示保障：固定展示2条本土政策热点")

if live_warnings:
    warning_caption.caption("系统提示：" + "；".join(dict.fromkeys(live_warnings)))

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
