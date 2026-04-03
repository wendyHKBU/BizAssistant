"""
AI商业参谋 - 模拟引擎（无需API，免费运行）
用关键词匹配 + 预设模板生成真实感早报，用于验证业务逻辑
包含：热点匹配 + 今日日程分析 + 商业活动推荐
"""

import random
import re
from datetime import datetime


# ── 行动建议模板库（按类别） ──────────────────────────────
ACTION_TEMPLATES = {
    "政策": [
        "今天在朋友圈发一条关于该政策与自己业务结合的简评，引发客户咨询",
        "整理该政策申请条件，发给最近联系的3位相关客户，主动提供价值",
        "研究该政策细则，看自己是否符合申请资格，准备申请材料",
    ],
    "电商": [
        "在抖音/小红书搜索该话题热度，判断是否值得测试一条内容",
        "联系你的运营合作伙伴，讨论是否可以借势做一波活动",
        "分析竞争对手是否已经在行动，找到差异化切入点",
    ],
    "AI科技": [
        "注册试用该AI工具，测试是否能降低你的某项业务成本",
        "整理自己哪些日常工作可以被AI替代，计算节省的时间成本",
        "与你的技术合作伙伴讨论如何将该技术接入现有业务流程",
    ],
    "外贸": [
        "在阿里国际站/Made-in-China更新产品页面，针对该市场需求优化描述",
        "联系你的海外买家，主动询问他们对该趋势的看法和采购计划",
        "研究目标市场的认证要求，看是否有新的准入机会",
    ],
    "金融": [
        "联系你的开户银行客户经理，询问该产品申请条件",
        "整理公司近3个月流水，准备融资/信贷申请材料",
        "计算引入该融资方案后，现金流可以改善多少",
    ],
    "餐饮": [
        "今天去附近同类餐厅观察客流量，记录高峰时段和客单价",
        "联系商场招商部门，询问目前空铺情况和入驻条件",
        "在大众点评/美团更新菜单和图片，提升搜索权重",
    ],
    "新能源": [
        "调研该细分市场的主要采购商，建立目标客户名单",
        "参加即将举办的新能源行业展会，收集竞争对手信息",
        "与现有客户讨论该趋势，看是否有合作新业务的机会",
    ],
    "法律科技": [
        "在LinkedIn/脉脉更新你的产品介绍，强调该场景的解决方案",
        "联系你认识的律所合伙人，询问他们对该工具的看法",
        "准备一份针对该痛点的产品演示，用于下次客户拜访",
    ],
    "设计": [
        "在作品集中加入AI辅助设计的案例，强调人工创意的不可替代性",
        "给老客户发一份AI时代设计价值白皮书，引导提价讨论",
        "尝试用AI工具提升某个环节效率，把节省的时间投入创意",
    ],
    "跨境电商": [
        "在速卖通/Shopee开设该市场店铺，测试选品需求",
        "联系海外仓服务商，询问目标市场仓储费用和时效",
        "研究目标市场的爆款产品，分析是否与你现有品类匹配",
    ],
    "外汇": [
        "联系银行锁定近3个月汇率，降低汇率波动风险",
        "重新核算现有订单利润率，调整报价策略",
        "与财务讨论是否需要做外汇套保",
    ],
    "制造业": [
        "联系近期没有下单的老客户，询问当前采购需求",
        "更新产能和交货期信息，主动发给有意向的客户",
        "评估是否需要提前备库，把握订单回暖窗口",
    ],
}

# ── MiroFish推演模板 ──────────────────────────────────────
MIROFISH_TEMPLATES = {
    "高相关": {
        "window": ["2-3个月", "3-4个月", "4-6个月"],
        "revenue_low": [3, 5, 8, 10, 15],
        "revenue_high": [10, 20, 30, 50, 80],
        "risk": [
            "竞争对手同步行动，先发优势窗口有限",
            "政策落地执行细节待确认，存在不确定性",
            "客户决策周期较长，需提前布局",
            "市场需求真实性需进一步验证",
        ],
        "advice": "推进",
    },
    "中相关": {
        "window": ["1-2个月", "2-3个月"],
        "revenue_low": [1, 2, 3],
        "revenue_high": [5, 8, 12],
        "risk": [
            "与主营业务关联度有限，需要额外资源投入",
            "时机尚早，建议先观察1-2周再决策",
        ],
        "advice": "观察",
    },
}


def _extract_terms(text: str) -> list[str]:
    terms = re.findall(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{2,}", (text or "").lower())
    ignored = {
        "公司",
        "团队",
        "顾问",
        "老板",
        "方向",
        "行业",
        "服务",
        "业务",
        "客户",
        "增长",
        "提升",
        "推进",
        "机会",
        "合作",
        "项目",
        "计划",
        "当前",
        "今日",
    }
    return [term for term in terms if term not in ignored]


def _keyword_parts(keyword: str) -> list[str]:
    kw = (keyword or "").lower().strip()
    if len(kw) < 4:
        return [kw] if kw else []
    return list(dict.fromkeys([kw[:2], kw[-2:], kw[:3], kw[-3:]]))


def _term_ngrams(term: str, n: int = 2) -> set[str]:
    clean = re.sub(r"\s+", "", str(term or "").lower())
    if not clean:
        return set()
    if len(clean) <= n:
        return {clean}
    return {clean[i:i + n] for i in range(len(clean) - n + 1)}


def _semantic_overlap_score(profile_terms: list[str], text: str) -> int:
    if not profile_terms:
        return 0

    news_terms = _extract_terms(text)
    if not news_terms:
        return 0

    profile_tokens: set[str] = set()
    for term in profile_terms[:20]:
        profile_tokens.update(_term_ngrams(term, n=2))

    news_tokens: set[str] = set()
    for term in news_terms[:28]:
        news_tokens.update(_term_ngrams(term, n=2))

    if not profile_tokens or not news_tokens:
        return 0

    overlap = len(profile_tokens & news_tokens)
    if overlap <= 0:
        return 0

    union_size = len(profile_tokens | news_tokens)
    jaccard = (overlap / union_size) if union_size else 0
    return min(22, int(overlap * 2 + jaccard * 36))


def _infer_news_category_preferences(boss: dict) -> set[str]:
    text = " ".join([boss.get("industry", ""), boss.get("current_goal", ""), " ".join(boss.get("keywords", []))]).lower()
    prefs: set[str] = set()

    rules = {
        "政策": ["政策", "补贴", "监管", "合规", "政府", "国办"],
        "电商": ["电商", "抖音", "直播", "私域", "选款", "流量"],
        "AI科技": ["ai", "人工智能", "算法", "大模型", "科技"],
        "外贸": ["外贸", "出口", "进口", "跨境", "广交会", "东南亚"],
        "跨境电商": ["跨境", "东南亚", "出海", "海外", "shopee", "lazada"],
        "金融": ["金融", "融资", "信贷", "汇率", "银行", "资金"],
        "餐饮": ["餐饮", "堂食", "外卖", "连锁", "预制菜"],
        "法律科技": ["法律", "律所", "合规", "法务", "legaltech"],
        "设计": ["设计", "ui", "ux", "用户体验", "创意"],
        "制造业": ["制造", "工厂", "产能", "订单", "汽配", "建材", "工程"],
        "新能源": ["新能源", "汽车", "电池", "光伏", "储能"],
    }

    for category, keywords in rules.items():
        if any(keyword in text for keyword in keywords):
            prefs.add(category)

    return prefs


def match_news_for_boss(boss: dict, news_items: list[dict]) -> list[dict]:
    """为老板匹配相关新闻，返回带评分的列表。"""
    scored = []
    boss_keywords = [kw.lower() for kw in boss["keywords"]]
    ignore_keywords = [kw.lower() for kw in boss["ignore_keywords"]]
    industry_terms = _extract_terms(boss.get("industry", ""))
    goal_terms = _extract_terms(boss.get("current_goal", ""))[:8]
    category_preferences = _infer_news_category_preferences(boss)
    category_pref_lowers = {str(cat).lower() for cat in category_preferences}
    profile_terms = _extract_terms(
        " ".join(
            [
                boss.get("industry", ""),
                boss.get("current_goal", ""),
                " ".join(boss.get("keywords", [])),
            ]
        )
    )

    for news in news_items:
        title = str(news["title"]).lower()
        raw_category = str(news.get("category", ""))
        category = raw_category.lower()
        description = str(news.get("description", "")).lower()
        source = str(news.get("source", "")).lower()
        full_text = f"{title} {category} {description} {source}"

        # 检查忽略词
        if any(ig in full_text for ig in ignore_keywords):
            continue

        # 计算相关度分数
        score = 0
        matched_keywords = []

        for kw in boss_keywords:
            if kw in full_text:
                score += 24
                matched_keywords.append(kw)
            else:
                parts = _keyword_parts(kw)
                if any(part and part in full_text for part in parts):
                    score += 8
                    matched_keywords.append(kw)

        semantic_score = _semantic_overlap_score(profile_terms, full_text)
        score += semantic_score

        # 类别偏好加分，避免“抓到了但全空白”
        if category in category_pref_lowers:
            score += 10
        if category == "政策" and (category in category_pref_lowers or semantic_score >= 8 or matched_keywords):
            score += 5

        # 行业匹配加分
        for word in industry_terms:
            if len(word) > 1 and word in title:
                score += 14
                break

        # 目标相关加分
        goal_words = boss.get("current_goal", "").lower()
        for kw in boss_keywords[:3]:
            if kw in goal_words and kw in title:
                score += 10
        for term in goal_terms:
            if term in title:
                score += 6
                break

        # 强惩罚：类别不在偏好且缺少语义命中时，直接降分。
        if category and category_pref_lowers and category not in category_pref_lowers and not matched_keywords and semantic_score < 6:
            score -= 22
        if category == "政策" and "政策" not in category_pref_lowers and not matched_keywords and semantic_score < 8:
            score -= 16
        if not matched_keywords and semantic_score < 6 and category not in category_pref_lowers:
            score -= 18

        if score >= 24:
            scored.append({
                **news,
                "score": min(score, 98),
                "matched": list(dict.fromkeys(matched_keywords))[:4],
            })

    # 按分数排序，取前5条
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:5]


def get_action(category: str) -> str:
    """获取随机行动建议。"""
    templates = ACTION_TEMPLATES.get(category, ACTION_TEMPLATES["政策"])
    return random.choice(templates)


def get_mirofish(top_news: dict, relevance: str = "高相关") -> dict:
    """生成MiroFish推演报告。"""
    tmpl = MIROFISH_TEMPLATES.get(relevance, MIROFISH_TEMPLATES["高相关"])
    revenue_low = random.choice(tmpl["revenue_low"])
    revenue_high = random.choice(tmpl["revenue_high"])
    while revenue_high <= revenue_low:
        revenue_high = random.choice(tmpl["revenue_high"])

    return {
        "window": random.choice(tmpl["window"]),
        "revenue": f"¥{revenue_low}万 - ¥{revenue_high}万",
        "risk": random.choice(tmpl["risk"]),
        "advice": tmpl["advice"],
    }


def get_network_suggestion(boss: dict, top_news: dict) -> dict | None:
    """根据热点推荐最适合联系的人脉。"""
    if not boss.get("contacts"):
        return None

    # 优先推荐长时间未联系的
    contacts = sorted(boss["contacts"], key=lambda c: c["days_since_contact"], reverse=True)
    best = contacts[0]

    # 生成联系理由
    reasons = [
        f"距上次联系已 {best['days_since_contact']} 天，趁此热点正好有话题切入",
        f"今日「{top_news['title'][:15]}...」热点与其业务高度相关，借势联系自然",
        f"该热点可能影响对方决策，主动分享体现你的信息价值",
    ]

    return {
        "name": best["name"],
        "role": best["role"],
        "days": best["days_since_contact"],
        "reason": random.choice(reasons),
    }


def match_events_for_boss(boss: dict, events: list[dict]) -> list[dict]:
    """为老板匹配今日可参加的商业活动。"""
    matched = []
    boss_keywords = [kw.lower() for kw in boss["keywords"]]
    ignore_keywords = [kw.lower() for kw in boss["ignore_keywords"]]
    industry_terms = _extract_terms(boss.get("industry", ""))
    boss_city = boss.get("city", "")

    for event in events:
        title = (event["title"] + " " + event["description"]).lower()

        # 检查忽略词
        if any(ig in title for ig in ignore_keywords):
            continue

        # 计算匹配分数
        score = 0
        matched_keywords = []
        for kw in boss_keywords:
            if kw in title or any(kw in ek.lower() for ek in event["keywords"]):
                score += 20
                matched_keywords.append(kw)
            else:
                parts = _keyword_parts(kw)
                if any(part and (part in title or any(part in ek.lower() for ek in event.get("keywords", []))) for part in parts):
                    score += 8
                    matched_keywords.append(kw)

        # 行业匹配
        industry = boss.get("industry", "").lower()
        for ind in event.get("target_industries", []):
            ind_lower = ind.lower()
            if any(word in ind_lower or ind_lower in word for word in industry_terms):
                score += 18
                break

        if boss_city and boss_city in event.get("location", ""):
            score += 10
        if event.get("format") == "线上":
            score += 4
        if event.get("value") == "高":
            score += 4

        if score >= 12:
            matched.append({
                **event,
                "score": min(score, 99),
                "matched_keywords": list(dict.fromkeys(matched_keywords))[:3],
            })

    matched.sort(key=lambda x: x["score"], reverse=True)
    return matched[:3]


def analyze_schedule(boss: dict) -> dict:
    """分析今日日程，提取关键信息。"""
    schedule = boss.get("today_schedule", [])
    if not schedule:
        return {"count": 0, "high_priority": [], "types": []}

    high_priority = [s for s in schedule if s.get("priority") == "高"]
    deadlines = [s for s in schedule if s.get("type") == "截止日"]
    visit_types = list({s["type"] for s in schedule})

    return {
        "count": len(schedule),
        "high_priority": high_priority,
        "deadlines": deadlines,
        "types": visit_types,
        "busiest_hour": schedule[0]["time"] if schedule else None,
    }


def generate_mock_report(boss: dict, news_items: list[dict], events: list[dict] = None) -> str:
    """为单个老板生成模拟早报（含日程+活动+热点）。"""
    matched_news = match_news_for_boss(boss, news_items)
    matched_events = match_events_for_boss(boss, events or [])
    schedule_info = analyze_schedule(boss)

    today = datetime.now().strftime("%m月%d日")
    lines = [f"📋 {boss['name']}的商机早报 · {today}\n"]

    # ── 模块1：今日日程 ──────────────────────────────
    schedule = boss.get("today_schedule", [])
    if schedule:
        lines.append("【今日日程】")
        for item in schedule:
            priority_tag = "🔴" if item["priority"] == "高" else ("🟡" if item["priority"] == "中" else "⚪")
            lines.append(f"  {priority_tag} {item['time']}  {item['title']}  [{item['type']}]")
        if schedule_info["deadlines"]:
            lines.append(f"  ⚠️  今日截止：{'、'.join(d['title'][:10] for d in schedule_info['deadlines'])}")
        lines.append("")

    # ── 模块2：今日可参加活动 ──────────────────────────
    if matched_events:
        lines.append("【今日商业活动】")
        for ev in matched_events:
            value_tag = "🌟" if ev["value"] == "高" else "✨"
            lines.append(f"  {value_tag} {ev['title']}")
            lines.append(f"     {ev['time']}  |  {ev['format']}  |  来源：{ev['source_detail']}")
            lines.append(f"     {ev['description'][:40]}...")
            lines.append(f"     报名：{ev['registration_deadline']}")
            kw_str = "、".join(ev["matched_keywords"][:2]) if ev["matched_keywords"] else "行业相关"
            lines.append(f"     → 匹配原因：与你的「{kw_str}」方向高度相关")
            lines.append("")
    else:
        lines.append("【今日商业活动】\n  暂无高匹配活动\n")

    # ── 模块3：热点与商机 ──────────────────────────────
    if not matched_news:
        lines.append("【热点商机】\n  暂无高相关热点\n")
        return "\n".join(lines)

    lines.append("【热点商机】")
    for news in matched_news:
        emoji = "🔴" if news["score"] >= 70 else "🟡"
        category = news.get("category", "资讯")
        action = get_action(category)
        lines.append(f"  {emoji} {news['title']}")
        lines.append(f"     相关度：{news['score']}分  |  类别：{category}")
        lines.append(f"     → 与「{'、'.join(news['matched'][:2]) if news['matched'] else category}」匹配")
        lines.append(f"     → 行动：{action}")
        lines.append("")

    # 人脉提醒
    top = matched_news[0]
    network = get_network_suggestion(boss, top)
    if network:
        lines.append("【人脉提醒】")
        lines.append(f"  👥 建议联系：{network['name']}（{network['role']}）")
        lines.append(f"     → {network['reason']}")
        lines.append("")

    # MiroFish推演
    relevance = "高相关" if top["score"] >= 60 else "中相关"
    miro = get_mirofish(top, relevance)
    lines.append("【MiroFish推演】")
    lines.append(f"  🔮 最高价值商机：{top['title'][:25]}...")
    lines.append(f"     → 时间窗口：{miro['window']}")
    lines.append(f"     → 预估收益：{miro['revenue']}")
    lines.append(f"     → 主要风险：{miro['risk']}")
    lines.append(f"     → AI建议：{'✅ 推进' if miro['advice'] == '推进' else '👀 观察'}")

    return "\n".join(lines)


def generate_all_mock_reports(bosses: list[dict], news_items: list[dict], events: list[dict] = None) -> dict[str, str]:
    """批量生成模拟早报。"""
    results = {}
    for boss in bosses:
        results[boss["name"]] = generate_mock_report(boss, news_items, events)
    return results
