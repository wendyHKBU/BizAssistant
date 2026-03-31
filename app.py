"""AI商业参谋 - 高保真UI预览版（Streamlit）。"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import hashlib
import html
import ipaddress
import json
import math
import os
import random
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
from exhibition_sources import OFFICIAL_EXHIBITION_CENTER_SOURCES
from events import TODAY_EVENTS
from mock_advisor import (
    ACTION_TEMPLATES,
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
    ("36氪", "https://www.36kr.com/feed", "AI科技"),
    ("钛媒体", "https://www.tmtpost.com/rss.xml", "AI科技"),
]

POLICY_NEWS_RSS_SOURCES = [
    ("中国政府网政策", "https://www.gov.cn/zhengce/"),
]

AUTHORITATIVE_POLICY_SOURCE_PORTALS = [
    ("中国政府网", "http://www.gov.cn"),
    ("外交部", "https://www.fmprc.gov.cn"),
    ("国防部", "http://www.mod.gov.cn"),
    ("国家发展和改革委员会", "https://www.ndrc.gov.cn"),
    ("教育部", "http://www.moe.gov.cn"),
    ("科学技术部", "https://www.most.gov.cn"),
    ("工业和信息化部", "https://www.miit.gov.cn"),
    ("国家民族事务委员会", "https://www.neac.gov.cn"),
    ("公安部", "https://www.mps.gov.cn"),
    ("民政部", "https://www.mca.gov.cn"),
    ("司法部", "https://www.moj.gov.cn"),
    ("财政部", "http://www.mof.gov.cn"),
    ("人力资源和社会保障部", "https://www.mohrss.gov.cn"),
    ("自然资源部", "https://www.mnr.gov.cn"),
    ("生态环境部", "https://www.mee.gov.cn"),
    ("住房和城乡建设部", "https://www.mohurd.gov.cn"),
    ("交通运输部", "https://www.mot.gov.cn"),
    ("水利部", "http://www.mwr.gov.cn"),
    ("农业农村部", "http://www.moa.gov.cn"),
    ("商务部", "http://www.mofcom.gov.cn"),
    ("文化和旅游部", "https://www.mct.gov.cn"),
    ("国家卫生健康委员会", "http://www.nhc.gov.cn"),
    ("退役军人事务部", "http://www.mva.gov.cn"),
    ("应急管理部", "https://www.mem.gov.cn"),
    ("人民银行", "http://www.pbc.gov.cn"),
    ("审计署", "https://www.audit.gov.cn"),
    ("国务院国有资产监督管理委员会", "http://www.sasac.gov.cn"),
    ("海关总署", "http://www.customs.gov.cn"),
    ("国家税务总局", "http://www.chinatax.gov.cn"),
    ("国家市场监督管理总局", "http://www.samr.gov.cn"),
    ("国家广播电视总局", "https://www.nrta.gov.cn"),
    ("国家体育总局", "https://www.sport.gov.cn"),
    ("国家统计局", "http://www.stats.gov.cn"),
    ("国家国际发展合作署", "http://www.cidca.gov.cn"),
    ("国家医疗保障局", "http://www.nhsa.gov.cn"),
    ("国务院参事室", "http://www.counsellor.gov.cn"),
    ("国家机关事务管理局", "http://www.ggj.gov.cn"),
    ("国务院港澳事务办公室", "https://www.hmo.gov.cn"),
    ("国务院台湾事务办公室", "http://www.gwytb.gov.cn"),
    ("国家互联网信息办公室", "http://www.cac.gov.cn"),
    ("国务院新闻办公室", "http://www.scio.gov.cn"),
    ("新华通讯社", "http://www.xinhuanet.com"),
    ("中国科学院", "http://www.cas.cn"),
    ("中国社会科学院", "http://www.cass.cn"),
    ("中国工程院", "http://www.cae.cn"),
    ("国务院发展研究中心", "http://www.drc.gov.cn"),
    ("中国气象局", "http://www.cma.gov.cn"),
    ("国家知识产权局", "https://www.cnipa.gov.cn"),
    ("北京市政府", "http://www.beijing.gov.cn"),
    ("上海市政府", "http://www.shanghai.gov.cn"),
    ("天津市政府", "http://www.tj.gov.cn"),
    ("重庆市政府", "http://www.cq.gov.cn"),
    ("河北省政府", "http://www.hebei.gov.cn"),
    ("山西省政府", "http://www.shanxi.gov.cn"),
    ("内蒙古自治区政府", "http://www.nmg.gov.cn"),
    ("辽宁省政府", "http://www.ln.gov.cn"),
    ("吉林省政府", "http://www.jl.gov.cn"),
    ("黑龙江省政府", "http://www.hlj.gov.cn"),
    ("江苏省政府", "http://www.jiangsu.gov.cn"),
    ("浙江省政府", "http://www.zj.gov.cn"),
    ("安徽省政府", "http://www.ah.gov.cn"),
    ("福建省政府", "http://www.fujian.gov.cn"),
    ("江西省政府", "http://www.jiangxi.gov.cn"),
    ("山东省政府", "http://www.shandong.gov.cn"),
    ("河南省政府", "http://www.henan.gov.cn"),
    ("湖北省政府", "http://www.hubei.gov.cn"),
    ("湖南省政府", "http://www.hunan.gov.cn"),
    ("广东省政府", "http://www.gd.gov.cn"),
    ("广西壮族自治区政府", "http://www.gxzf.gov.cn"),
    ("海南省政府", "http://www.hainan.gov.cn"),
    ("四川省政府", "http://www.sc.gov.cn"),
    ("贵州省政府", "http://www.guizhou.gov.cn"),
    ("云南省政府", "http://www.yn.gov.cn"),
    ("西藏自治区政府", "http://www.xizang.gov.cn"),
    ("陕西省政府", "http://www.shaanxi.gov.cn"),
    ("甘肃省政府", "http://www.gansu.gov.cn"),
    ("青海省政府", "http://www.qinghai.gov.cn"),
    ("宁夏回族自治区政府", "http://www.nx.gov.cn"),
    ("新疆维吾尔自治区政府", "http://www.xinjiang.gov.cn"),
    ("香港特别行政区政府", "https://www.gov.hk"),
    ("澳门特别行政区政府", "https://www.gov.mo"),
    ("人民网", "http://www.people.com.cn"),
    ("新华网", "http://www.xinhuanet.com"),
    ("央视网", "http://www.cctv.com"),
    ("中国网", "http://www.china.com.cn"),
    ("国际在线", "http://www.cri.cn"),
    ("中国日报网", "http://www.chinadaily.com.cn"),
    ("央广网", "http://www.cnr.cn"),
    ("中国新闻网", "http://www.chinanews.com"),
    ("中国青年网", "http://www.youth.cn"),
    ("光明网", "http://www.gmw.cn"),
    ("中国经济网", "http://www.ce.cn"),
    ("中国军网", "http://www.81.cn"),
    ("求是网", "http://www.qstheory.cn"),
    ("环球网", "http://www.huanqiu.com"),
    ("澎湃新闻", "https://www.thepaper.cn"),
    ("上观新闻", "https://www.shobserver.com"),
    ("封面新闻", "http://www.thecover.cn"),
    ("红星新闻", "http://www.cdsb.com"),
    ("浙江在线", "http://www.zjol.com.cn"),
    ("南方网", "http://www.southcn.com"),
    ("东方网", "http://www.eastday.com"),
    ("华龙网", "http://www.cqnews.net"),
    ("四川在线", "http://www.scol.com.cn"),
    ("大众网", "http://www.dzwww.com"),
    ("红网", "http://www.rednet.cn"),
    ("36氪", "https://www.36kr.com"),
    ("钛媒体", "https://www.tmtpost.com"),
    ("新浪", "https://www.sina.com.cn"),
    ("腾讯新闻", "https://news.qq.com"),
    ("网易新闻", "https://news.163.com"),
    ("搜狐新闻", "https://www.sohu.com"),
    ("凤凰网", "https://www.ifeng.com"),
    ("界面新闻", "https://www.jiemian.com"),
    ("虎嗅", "https://www.huxiu.com"),
    ("第一财经", "https://www.yicai.com"),
    ("财新网", "https://www.caixin.com"),
    ("21世纪经济报道", "https://www.21jingji.com"),
    ("每日经济新闻", "https://www.nbd.com.cn"),
    ("观察者网", "https://www.guancha.cn"),
    ("中央纪委国家监委", "https://www.ccdi.gov.cn"),
    ("中共中央党校（国家行政学院）", "https://www.ccps.gov.cn"),
    ("中国文明网", "http://www.wenming.cn"),
    ("学习强国", "https://www.xuexi.cn"),
]

POLICY_SOURCE_BATCH_SIZE = 18
POLICY_SOURCE_PER_SITE = 2
POLICY_TITLE_EXTRA_MARKERS = [
    "政策",
    "通知",
    "通告",
    "公告",
    "意见",
    "办法",
    "细则",
    "方案",
    "措施",
    "实施",
    "扶持",
    "补贴",
    "申报",
    "征求意见",
    "管理规定",
    "指导",
]
POLICY_TITLE_EXCLUDE_MARKERS = [
    "首页",
    "联系我们",
    "网站地图",
    "版权",
    "隐私",
    "客户端",
    "登录",
    "注册",
    "下载",
]
POLICY_GENERIC_SECTION_TITLES = {
    "政策",
    "政策法规",
    "政策文件",
    "政策解读",
    "通知",
    "通知公告",
    "公告",
    "新闻",
    "新闻中心",
    "信息公开",
    "政务公开",
    "工作动态",
    "更多",
}
POLICY_DETAIL_URL_BLOCK_MARKERS = [
    "/index",
    "/list",
    "/column",
    "/channel",
    "/node",
    "/zt",
    "/special",
    "/search",
    "/sitemap",
]
POLICY_DETAIL_VERIFY_TIMEOUT = 4

SOURCE_HOME_URL_MAP = {
    "中国政府网政策": "https://www.gov.cn/zhengce/",
    "新浪财经（实时）": "https://finance.sina.com.cn/",
    "36氪": "https://www.36kr.com/",
    "钛媒体": "https://www.tmtpost.com/",
}
for portal_name, portal_url in AUTHORITATIVE_POLICY_SOURCE_PORTALS:
    SOURCE_HOME_URL_MAP.setdefault(portal_name, portal_url)

SINA_ROLL_API_URL = "https://feed.mix.sina.com.cn/api/roll/get"
SINA_POLICY_ROLL_LIDS = [1686, 1687]
SINA_POLICY_TITLE_MARKERS = [
    "政策",
    "国务院",
    "财政",
    "税",
    "监管",
    "发改委",
    "央行",
    "人民银行",
    "金融监管",
    "社保",
    "补贴",
    "消费",
    "投资",
    "外贸",
    "中小企业",
]

HUODONGJIA_EVENT_API_URL = "https://www.huodongjia.com/api/v1/event/info/list"
HUODONGJIA_SIGN_SALT = "huodongjia_v2_salt_888"

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

HUODONGJIA_EVENT_KEYWORDS = [
    "会议",
    "论坛",
    "峰会",
    "商务",
    "创业",
    "培训",
]

EVENT_DISCOVERY_PLATFORMS = [
    {"name": "百格活动", "domain": "bagevent.com", "url": "https://www.bagevent.com"},
    {"name": "会腾软件", "domain": "huitengsoft.com", "url": "https://www.huitengsoft.com"},
    {"name": "互动吧", "domain": "hudongba.com", "url": "https://www.hudongba.com"},
    {"name": "活动行", "domain": "huodongxing.com", "url": "https://www.huodongxing.com"},
    {"name": "31会议", "domain": "31huiyi.com", "url": "https://www.31huiyi.com"},
    {"name": "快会务", "domain": "kuaihuiwu.com", "url": "https://www.kuaihuiwu.com"},
    {"name": "会会", "domain": "huihui521.com", "url": "https://www.huihui521.com"},
    {"name": "活动家", "domain": "huodongjia.com", "url": "https://www.huodongjia.com"},
]

WECHAT_EVENT_CHANNEL_TOPICS = [
    ("地方媒体公众号", "地方媒体 活动 论坛 展会"),
    ("校园公众号", "校园 讲座 创业 大赛 活动"),
    ("活动平台联动号", "活动平台 联动 会务 通知"),
    ("会展中心公众号", "会展中心 排期 展会 论坛"),
]

WECHAT_EXHIBITION_CENTER_SOURCES = [
    {"city": "北京", "center": "国家会议中心", "query": "国家会议中心 展会 排期 活动"},
    {"city": "上海", "center": "上海新国际博览中心", "query": "上海新国际博览中心 展会 排期 活动"},
    {"city": "广州", "center": "广交会展馆", "query": "广交会展馆 会展 排期 活动"},
    {"city": "深圳", "center": "深圳会展中心", "query": "深圳会展中心 展会 排期 活动"},
    {"city": "杭州", "center": "杭州国际博览中心", "query": "杭州国际博览中心 展会 排期 活动"},
    {"city": "成都", "center": "成都世纪城新国际会展中心", "query": "成都世纪城新国际会展中心 展会 排期 活动"},
]

WECHAT_EVENT_EXTRA_MARKERS = ["会展", "展览", "博览会", "博览", "发布会", "推介会", "招商会"]

EXHIBITION_CENTER_FETCH_BATCH_SIZE = 16
EXHIBITION_CENTER_PER_SITE_LIMIT = 2
EXHIBITION_CENTER_TITLE_MARKERS = [
    "展会",
    "展览",
    "博览",
    "博览会",
    "会展",
    "交易会",
    "博览城",
    "峰会",
    "论坛",
    "大会",
    "展讯",
    "排期",
]
EXHIBITION_CENTER_TITLE_EXCLUDE_MARKERS = [
    "首页",
    "联系我们",
    "关于我们",
    "版权",
    "隐私",
    "登录",
    "注册",
    "下载",
    "导航",
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

EN_CITY_TO_CN = {
    "beijing": "北京",
    "shanghai": "上海",
    "guangzhou": "广州",
    "shenzhen": "深圳",
    "hangzhou": "杭州",
    "nanjing": "南京",
    "suzhou": "苏州",
    "chengdu": "成都",
    "chongqing": "重庆",
    "wuhan": "武汉",
    "xian": "西安",
    "xi'an": "西安",
    "tianjin": "天津",
    "changsha": "长沙",
    "zhengzhou": "郑州",
    "qingdao": "青岛",
    "ningbo": "宁波",
    "xiamen": "厦门",
    "hefei": "合肥",
    "fuzhou": "福州",
    "dongguan": "东莞",
    "foshan": "佛山",
    "jinan": "济南",
}

CITY_12306_STATION_CODES = {
    "北京": "BJP",
    "上海": "SHH",
    "广州": "GZQ",
    "深圳": "SZQ",
    "杭州": "HZH",
    "南京": "NJH",
    "苏州": "SZH",
    "成都": "CDW",
    "重庆": "CQW",
    "武汉": "WHN",
    "西安": "XAY",
    "天津": "TJP",
    "长沙": "CSQ",
    "郑州": "ZZF",
    "青岛": "QDK",
    "宁波": "NGH",
    "厦门": "XMS",
    "合肥": "HFH",
    "福州": "FZS",
    "济南": "JNK",
}

MAX_TRAVEL_HOURS = 2.0
EXTENDED_EVENT_TRAVEL_BUFFER_HOURS = 1.0
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


def _normalize_url_with_base(raw_url: str, base_url: str = "") -> str:
    url = html.unescape(str(raw_url or "")).strip()
    if not url:
        return ""

    if url.startswith("javascript:") or url.startswith("#"):
        return ""

    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = urljoin(base_url, url) if base_url else ""
    elif not re.match(r"^https?://", url):
        url = urljoin(base_url, url) if base_url else ""

    if not url:
        return ""
    if not re.match(r"^https?://", url):
        return ""

    return url


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


def _extract_profile_terms(text: str) -> list[str]:
    terms = re.findall(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{2,}", (text or "").lower())
    ignored = {
        "公司",
        "团队",
        "方向",
        "行业",
        "服务",
        "业务",
        "客户",
        "老板",
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


def _safe_api_post_json(
    url: str,
    *,
    payload: dict | None = None,
    headers: dict | None = None,
    timeout: int = 14,
) -> dict | None:
    try:
        response = requests.post(
            url,
            json=payload or {},
            headers=headers,
            timeout=timeout,
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
        highway_toll = 0.0
    elif distance_km <= 260:
        mode = "高铁/城际交通"
        travel_hours = 0.65 + distance_km / 210
        transport_cost = 35.0 + distance_km * 0.48
        highway_toll = max(8.0, distance_km * 0.28)
    else:
        mode = "航班+地面交通"
        travel_hours = 2.3 + distance_km / 650
        transport_cost = 260.0 + distance_km * 0.8
        highway_toll = max(18.0, distance_km * 0.22)

    time_cost = travel_hours * TIME_VALUE_PER_HOUR_RMB
    total_cost = transport_cost + time_cost
    return {
        "travel_mode": mode,
        "travel_hours": round(travel_hours, 2),
        "distance_km": round(distance_km, 1),
        "transport_cost_rmb": round(transport_cost, 0),
        "highway_toll_rmb": round(highway_toll, 0),
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
    event_copy["highway_toll_rmb"] = 0.0
    event_copy["time_cost_rmb"] = 0.0
    event_copy["total_trip_cost_rmb"] = 0.0
    event_copy["travel_brief"] = "线上参加，交通成本≈¥0"
    event_copy["travel_note"] = "线上参加，交通约 ¥0，高速过路费约 ¥0。"
    return event_copy


def apply_ip_proximity_filter(
    events: list[dict],
    max_travel_hours: float = MAX_TRAVEL_HOURS,
    preferred_city: str = "",
) -> tuple[list[dict], dict, list[str]]:
    warnings: list[str] = []
    if not events:
        return [], {"enabled": False}, warnings

    client_ip = _extract_client_ip()
    geo = _lookup_ip_geo(client_ip) if client_ip else {"ok": False}
    preferred_city_norm = _canonical_city_name(preferred_city)

    anchor_mode = "ip"
    anchor_city = ""
    if preferred_city_norm and preferred_city_norm in MAJOR_CITY_COORDS:
        anchor_mode = "manual_city"
        anchor_city = preferred_city_norm
        user_lat, user_lon = MAJOR_CITY_COORDS[preferred_city_norm]
    else:
        if not client_ip:
            warnings.append("未识别到用户IP，暂未启用1-2小时路程硬过滤")
            return [{**event} for event in events], {"enabled": False}, warnings

        if not geo.get("ok"):
            warnings.append("用户IP定位失败，暂未启用1-2小时路程硬过滤")
            return [{**event} for event in events], {"enabled": False, "ip": client_ip}, warnings

        user_lat = float(geo.get("lat"))
        user_lon = float(geo.get("lon"))
        anchor_city = _canonical_city_name(str(geo.get("city", "")))

    city_scope = _build_reachable_city_scope(user_lat, user_lon, max_travel_hours=max_travel_hours)
    allowed_cities = {item["city"] for item in city_scope}
    extended_limit = max_travel_hours + EXTENDED_EVENT_TRAVEL_BUFFER_HOURS

    filtered: list[dict] = []
    extended_candidates: list[dict] = []
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

        coords = MAJOR_CITY_COORDS.get(event_city)
        if not coords:
            unknown_offline_count += 1
            continue

        city_lat, city_lon = coords
        distance = _haversine_km(user_lat, user_lon, city_lat, city_lon)
        trip = _estimate_trip(distance)

        event_copy = {**event}
        event_copy["event_city"] = event_city
        event_copy.update(trip)
        event_copy["travel_brief"] = f"单程 {trip['travel_hours']:.1f} 小时，交通约 ¥{trip['transport_cost_rmb']:.0f}"
        event_copy["travel_note"] = (
            f"单程约 {trip['travel_hours']:.1f} 小时（{trip['travel_mode']}），"
            f"交通约 ¥{trip['transport_cost_rmb']:.0f}，高速过路费约 ¥{trip['highway_toll_rmb']:.0f}。"
        )

        if event_city in allowed_cities and trip["travel_hours"] <= max_travel_hours:
            filtered.append(event_copy)
        elif trip["travel_hours"] <= extended_limit:
            event_copy["extended_reach"] = True
            extended_candidates.append(event_copy)
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

    if not filtered and extended_candidates:
        extended_candidates.sort(
            key=lambda item: (
                0 if item.get("value") == "高" else 1,
                float(item.get("travel_hours", 99) or 99),
            )
        )
        picked = {**extended_candidates[0]}
        detail = str(picked.get("source_detail", "本土活动源")).strip()
        if "稍远可达" not in detail:
            picked["source_detail"] = f"{detail} · 稍远可达"
        filtered.append(picked)
        warnings.append(
            f"已启用保底补位：补充1条单程≤{extended_limit:.1f}小时的活动（优先行业一致与高价值）"
        )

    if not filtered:
        warnings.append("IP硬过滤后暂无可达活动，建议优先线上活动或放宽城市圈")

    nearest_city = _nearest_major_city(user_lat, user_lon)
    normalized_city = _canonical_city_name(str(geo.get("city", "")))
    profile = {
        "enabled": True,
        "ip": client_ip,
        "city": anchor_city or normalized_city or geo.get("city", ""),
        "anchor_mode": anchor_mode,
        "anchor_city": anchor_city or normalized_city or geo.get("city", ""),
        "input_city": preferred_city_norm,
        "ip_city": normalized_city or geo.get("city", ""),
        "region": geo.get("region", ""),
        "country": geo.get("country", ""),
        "provider": geo.get("provider", ""),
        "lat": user_lat,
        "lon": user_lon,
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


def _looks_like_policy_title(title: str) -> bool:
    text = _clean_html_text(title)
    if not text or len(text) < 6:
        return False

    if any(marker in text for marker in POLICY_TITLE_EXCLUDE_MARKERS):
        return False

    if text in POLICY_GENERIC_SECTION_TITLES:
        return False

    markers = POLICY_TITLE_EXTRA_MARKERS + SINA_POLICY_TITLE_MARKERS
    return any(marker in text for marker in markers)


def _looks_like_policy_detail_url(raw_url: str) -> bool:
    url = _normalize_url_with_base(raw_url)
    if not url:
        return False

    lower = url.lower()
    if re.match(r"^https?://[^/]+/?$", lower):
        return False

    path = re.sub(r"^https?://[^/]+", "", lower)
    if not path or path == "/":
        return False

    blocked = any(marker in path for marker in POLICY_DETAIL_URL_BLOCK_MARKERS)
    has_id_hint = bool(re.search(r"(?:content|article|detail|doc|show|view)[_\-/]?\d{3,}", lower))
    has_query_id = bool(re.search(r"[?&](?:id|docid|articleid|contentid)=\d+", lower))
    has_date_path = bool(re.search(r"/(?:19|20)\d{2}[/-]\d{1,2}[/-]\d{1,2}", lower))
    has_html = bool(re.search(r"\.(?:html?|shtml|php)(?:\?|$)", lower))

    if blocked and not (has_id_hint or has_query_id or has_date_path):
        return False

    if has_id_hint or has_query_id or has_date_path:
        return True

    if has_html and not re.search(r"/(?:index|list|channel|column|node)[_.-]?", lower):
        return True

    path_segments = [seg for seg in path.split("/") if seg]
    if len(path_segments) >= 3 and any(re.search(r"\d{4,}", seg) for seg in path_segments):
        return True

    return False


def _extract_html_page_title(html_text: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html_text or "", flags=re.I | re.S)
    if not match:
        return ""
    return _clean_html_text(match.group(1) or "")


def _normalize_policy_title_for_match(text: str) -> str:
    clean = _clean_html_text(text)
    if not clean:
        return ""

    for sep in ["|", "-", "_", "—", "–", "｜"]:
        if sep in clean:
            clean = clean.split(sep)[0]
    clean = re.sub(r"[\s\u3000]+", "", clean)
    clean = re.sub(r"[\[\]【】()（）<>《》\-_:：,，。！？!?.]", "", clean)
    return clean[:80]


def _is_policy_title_consistent(anchor_title: str, page_title: str) -> bool:
    left = _normalize_policy_title_for_match(anchor_title)
    right = _normalize_policy_title_for_match(page_title)
    if not left or not right:
        return False

    if left in right or right in left:
        return True

    left_terms = set(_extract_profile_terms(left))
    right_terms = set(_extract_profile_terms(right))
    if left_terms and right_terms:
        overlap = len(left_terms & right_terms) / max(1, len(left_terms))
        if overlap >= 0.5:
            return True

    left_bigrams = {left[i:i + 2] for i in range(max(1, len(left) - 1))} if len(left) > 1 else {left}
    right_bigrams = {right[i:i + 2] for i in range(max(1, len(right) - 1))} if len(right) > 1 else {right}
    union = left_bigrams | right_bigrams
    if not union:
        return False
    jaccard = len(left_bigrams & right_bigrams) / len(union)
    return jaccard >= 0.35


def _verify_policy_link_title(anchor_title: str, detail_url: str) -> bool:
    if not _looks_like_policy_detail_url(detail_url):
        return False

    html_text = _safe_get_text(detail_url, timeout=POLICY_DETAIL_VERIFY_TIMEOUT)
    if not html_text:
        return False

    page_title = _extract_html_page_title(html_text)
    if not page_title:
        return False

    return _is_policy_title_consistent(anchor_title, page_title)


def _extract_policy_items_from_portal(portal_name: str, portal_url: str, max_items: int = 2) -> list[dict]:
    html_text = _safe_get_text(portal_url, timeout=8)
    if not html_text:
        return []

    anchor_pattern = re.compile(r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<title>.*?)</a>', flags=re.I | re.S)
    collected: list[dict] = []
    seen_titles = set()

    portal_host = re.sub(r"^https?://", "", portal_url).split("/")[0].lower()

    for match in anchor_pattern.finditer(html_text):
        title = _clean_html_text(match.group("title") or "")
        if not _looks_like_policy_title(title):
            continue

        title_key = re.sub(r"\s+", " ", title.lower()).strip()
        if title_key in seen_titles:
            continue

        href = _normalize_url_with_base(match.group("href") or "", portal_url)
        if not href:
            continue

        if not _looks_like_policy_detail_url(href):
            continue

        href_host = re.sub(r"^https?://", "", href).split("/")[0].lower()
        if portal_host and href_host and (portal_host not in href_host and href_host not in portal_host):
            # 尽量保证是同一权威站点内链接，避免聚合页跨站跳转带来的噪声。
            continue

        if not _verify_policy_link_title(title, href):
            continue

        seen_titles.add(title_key)
        collected.append(
            {
                "title": title,
                "link": href,
                "description": f"来自{portal_name}官方发布。",
                "published": "",
            }
        )
        if len(collected) >= max_items:
            break

    return collected


def _build_authoritative_policy_portal_news(max_items: int = 20) -> list[dict]:
    portals = AUTHORITATIVE_POLICY_SOURCE_PORTALS
    if not portals:
        return []

    batch_size = min(POLICY_SOURCE_BATCH_SIZE, len(portals))
    seed = int(datetime.now().strftime("%Y%m%d%H"))
    start = seed % len(portals)

    selected_portals = [portals[(start + idx) % len(portals)] for idx in range(batch_size)]

    news: list[dict] = []
    seen_titles = set()
    for portal_name, portal_url in selected_portals:
        items = _extract_policy_items_from_portal(portal_name, portal_url, max_items=POLICY_SOURCE_PER_SITE)
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            title_key = re.sub(r"\s+", " ", title.lower()).strip()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            news.append(
                {
                    "id": f"R{len(news) + 1:02d}",
                    "title": title,
                    "category": "政策",
                    "source": portal_name,
                    "published": str(item.get("published", "")),
                    "url": str(item.get("link", "")),
                }
            )

            if len(news) >= max_items:
                return news

    return news


def _build_city_policy_news(preferred_city: str, max_items: int = 6) -> list[dict]:
    city = _canonical_city_name(preferred_city)
    if not city:
        return []

    direct_portals = [
        (portal_name, portal_url)
        for portal_name, portal_url in AUTHORITATIVE_POLICY_SOURCE_PORTALS
        if city in portal_name and "政府" in portal_name
    ]
    fallback_portals = [
        (portal_name, portal_url)
        for portal_name, portal_url in AUTHORITATIVE_POLICY_SOURCE_PORTALS
        if city in portal_name
    ]

    portal_candidates = direct_portals or fallback_portals
    if not portal_candidates:
        return []

    seed = int(datetime.now().strftime("%Y%m%d%H"))
    start = seed % len(portal_candidates)
    ordered = [portal_candidates[(start + idx) % len(portal_candidates)] for idx in range(len(portal_candidates))]

    news: list[dict] = []
    seen_titles = set()
    for portal_name, portal_url in ordered[:3]:
        items = _extract_policy_items_from_portal(portal_name, portal_url, max_items=2)
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue

            title_key = re.sub(r"\s+", " ", title.lower()).strip()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            news.append(
                {
                    "id": f"R{len(news) + 1:02d}",
                    "title": title,
                    "category": "政策",
                    "source": f"{portal_name}（{city}同城）",
                    "published": str(item.get("published", "")),
                    "url": str(item.get("link", "")),
                }
            )
            if len(news) >= max_items:
                return news

    return news


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


def _policy_news_title_hit(title: str) -> bool:
    return any(marker in title for marker in SINA_POLICY_TITLE_MARKERS)


def _parse_sina_policy_items(max_items: int = 10) -> list[dict]:
    collected: list[dict] = []
    seen_titles = set()
    request_headers = {"User-Agent": "Mozilla/5.0 BizAdvisor/1.0"}

    for lid in SINA_POLICY_ROLL_LIDS:
        payload = _safe_api_get_json(
            SINA_ROLL_API_URL,
            params={"pageid": 155, "lid": lid, "num": 24, "page": 1},
            headers=request_headers,
        )
        result = (payload or {}).get("result") or {}
        status = (result.get("status") or {}).get("code")
        if status != 0:
            continue

        for raw in result.get("data") or []:
            title = _clean_html_text(str(raw.get("title") or ""))
            if not title or title in seen_titles or not _policy_news_title_hit(title):
                continue

            link = str(raw.get("url") or raw.get("wapurl") or "").strip()
            if not link:
                continue

            published = ""
            ctime = raw.get("ctime") or raw.get("intime")
            try:
                published = datetime.fromtimestamp(int(ctime)).strftime("%Y-%m-%d %H:%M")
            except Exception:
                published = ""

            seen_titles.add(title)
            collected.append(
                {
                    "title": title,
                    "link": link,
                    "description": "新浪财经实时滚动（政策/宏观）",
                    "published": published,
                }
            )
            if len(collected) >= max_items:
                return collected

    return collected


def _build_policy_only_news(max_items: int = 8) -> list[dict]:
    seen_titles = set()
    news: list[dict] = []

    authoritative_portal_news = _build_authoritative_policy_portal_news(max_items=max_items * 3)
    for item in authoritative_portal_news:
        title = item.get("title", "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        news.append(
            {
                "id": f"R{len(news) + 1:02d}",
                "title": title,
                "category": "政策",
                "source": item.get("source", "权威站点"),
                "published": item.get("published", ""),
                "url": item.get("url", ""),
            }
        )
        if len(news) >= max_items:
            return news

    for source_name, source_url in POLICY_NEWS_RSS_SOURCES:
        if source_name == "中国政府网政策":
            items = _parse_gov_policy_items(source_url, max_items=18)
        else:
            items = _parse_rss_items(source_url, max_items=18)

        for item in items:
            title = item.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            news.append(
                {
                    "id": f"R{len(news) + 1:02d}",
                    "title": title,
                    "category": "政策",
                    "source": source_name,
                    "published": item.get("published", ""),
                    "url": item.get("link", ""),
                }
            )
            if len(news) >= max_items:
                return news

    sina_items = _parse_sina_policy_items(max_items=max_items)
    for item in sina_items:
        title = item.get("title", "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        news.append(
            {
                "id": f"R{len(news) + 1:02d}",
                "title": title,
                "category": "政策",
                "source": "新浪财经（实时）",
                "published": item.get("published", ""),
                "url": item.get("link", ""),
            }
        )
        if len(news) >= max_items:
            break

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


def _build_live_news(max_items: int = 24, preferred_city: str = "") -> list[dict]:
    preferred_city_norm = _canonical_city_name(preferred_city)
    policy_quota = min(max_items, max(6, max_items // 3))
    city_policy_news = _build_city_policy_news(preferred_city_norm, max_items=min(6, max(2, max_items // 4)))
    policy_news = _build_policy_only_news(max_items=policy_quota)
    local_news = _build_local_news(max_items=max_items * 2)

    merged: list[dict] = []
    seen_titles = set()

    for batch in [city_policy_news, policy_news, local_news]:
        for item in batch:
            title = item.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            merged.append(item)
            if len(merged) >= max_items:
                break
        if len(merged) >= max_items:
            break

    if preferred_city_norm:
        city_hits: list[dict] = []
        others: list[dict] = []
        for item in merged:
            text = f"{item.get('title', '')} {item.get('source', '')}"
            if preferred_city_norm in text:
                city_hits.append(item)
            else:
                others.append(item)
        merged = city_hits + others

    for i, item in enumerate(merged[:max_items], 1):
        item["id"] = f"R{i:02d}"
    return merged[:max_items]


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


def _stable_json_data(raw: object) -> object:
    if isinstance(raw, dict):
        return {key: _stable_json_data(raw[key]) for key in sorted(raw)}
    if isinstance(raw, list):
        return [_stable_json_data(item) for item in raw]
    return raw


def _build_huodongjia_signature(payload: dict | None = None) -> dict:
    payload_text = ""
    if payload:
        payload_text = json.dumps(_stable_json_data(payload), ensure_ascii=False, separators=(",", ":"))

    timestamp = str(int(time.time() * 1000))
    nonce = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=12))
    signature_base = f"{payload_text}{timestamp}{nonce}{HUODONGJIA_SIGN_SALT}"
    signature = hashlib.md5(signature_base.encode("utf-8")).hexdigest()

    return {
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }


def _event_from_huodongjia(raw_event: dict, keyword: str) -> dict | None:
    title = _normalize_event_text(raw_event.get("event_name", ""), max_len=90)
    if not title:
        return None

    begin_time = str(raw_event.get("begin_time") or "")
    city_name = _normalize_event_text(raw_event.get("city_name", ""), max_len=16)
    venue_name = _normalize_event_text(raw_event.get("venue_name", ""), max_len=36)

    location_parts = [city_name]
    if venue_name and venue_name != city_name:
        location_parts.append(venue_name)
    fallback_location = " · ".join(part for part in location_parts if part) or "全国（以活动页为准）"

    event_text = f"{title} {fallback_location}".lower()
    event_format = "线上" if any(w in event_text for w in ["线上", "直播", "webinar", "online", "腾讯会议", "zoom"]) else "线下"
    location = _infer_event_location(title, fallback_location, event_format, fallback_location)

    price_text = "详见活动页"
    try:
        min_price = float(raw_event.get("min_price") or 0)
        price_text = "免费" if min_price <= 0 else f"¥{int(min_price)} 起"
    except Exception:
        pass

    description = f"来自活动家本土商务会议源，检索关键词：{keyword}，参考票价：{price_text}。"
    keywords, industries = _detect_event_profile(title, description)
    high_value = any(marker in f"{title} {description}".lower() for marker in EVENT_MARKERS)

    event_uuid = str(raw_event.get("event_uuid") or "").strip()
    event_url = f"https://www.huodongjia.com/event-{event_uuid}.html" if event_uuid else ""

    return {
        "title": title,
        "time": _format_event_start(begin_time),
        "location": location,
        "format": event_format,
        "source": "local",
        "source_detail": "活动家（本土商务会议）",
        "keywords": keywords,
        "target_industries": industries,
        "description": description,
        "registration_deadline": _format_event_start(begin_time) if begin_time else "详见活动页",
        "value": "高" if high_value else "中",
        "url": event_url,
    }


def _fetch_huodongjia_events(max_items: int = 18) -> list[dict]:
    collected: list[dict] = []
    seen_urls = set()
    query_keywords = list(dict.fromkeys(LOCAL_EVENT_KEYWORDS + HUODONGJIA_EVENT_KEYWORDS))

    base_headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 BizAdvisor/1.0",
        "Origin": "https://www.huodongjia.com",
        "Referer": "https://www.huodongjia.com/business",
    }

    for keyword in query_keywords:
        payload = {
            "page": 1,
            "page_size": 8,
            "cat_type": 1,
            "keyword": keyword,
        }
        headers = {**base_headers, **_build_huodongjia_signature(payload)}
        response = _safe_api_post_json(
            HUODONGJIA_EVENT_API_URL,
            payload=payload,
            headers=headers,
            timeout=16,
        )
        if not response:
            continue
        if int(response.get("code", 0) or 0) != 200:
            continue

        rows = ((response.get("data") or {}).get("data") or [])
        for raw_event in rows:
            event = _event_from_huodongjia(raw_event, keyword)
            if not event:
                continue
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


def _is_mainland_event(event: dict) -> bool:
    text = f"{event.get('title', '')} {event.get('location', '')}"
    return not any(marker in text for marker in NON_MAINLAND_LOCATION_MARKERS)


def _build_baidu_site_search_url(domain: str, keyword: str, city_hint: str = "") -> str:
    query = " ".join(part for part in [f"site:{domain}", city_hint, keyword, "活动"] if part)
    return f"https://www.baidu.com/s?wd={quote_plus(query)}"


def _build_wechat_search_url(topic_query: str, city_hint: str = "") -> str:
    query = " ".join(part for part in [city_hint, topic_query] if part)
    return f"https://weixin.sogou.com/weixin?type=2&query={quote_plus(query)}"


def _normalize_wechat_result_url(raw_url: str) -> str:
    url = html.unescape(str(raw_url or "")).strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("/"):
        url = urljoin("https://weixin.sogou.com", url)
    return url


def _looks_like_wechat_event_title(title: str) -> bool:
    text = re.sub(r"\s+", "", str(title or "")).strip()
    if len(text) < 8:
        return False

    marker_pool = EVENT_MARKERS + WECHAT_EVENT_EXTRA_MARKERS
    return any(marker in text for marker in marker_pool)


def _extract_wechat_event_time(title: str, context_text: str = "") -> str:
    text = f"{title} {context_text}"

    ymd_match = re.search(r"(20\d{2})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})", text)
    if ymd_match:
        try:
            dt = datetime(int(ymd_match.group(1)), int(ymd_match.group(2)), int(ymd_match.group(3)))
            return dt.strftime("%m-%d")
        except Exception:
            pass

    md_match = re.search(r"(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*(?:日|号)?", text)
    if md_match:
        month = int(md_match.group(1))
        day = int(md_match.group(2))
        try:
            year = datetime.now().year
            dt = datetime(year, month, day)
            if dt.date() < datetime.now().date():
                dt = datetime(year + 1, month, day)
            return dt.strftime("%m-%d")
        except Exception:
            pass

    return "待确认（公众号）"


def _extract_wechat_exhibition_events(
    html_text: str,
    city: str,
    center_name: str,
    max_items: int = 3,
) -> list[dict]:
    if not html_text:
        return []

    anchor_pattern = re.compile(r'<a[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>', flags=re.I | re.S)
    collected: list[dict] = []
    seen_titles = set()

    for match in anchor_pattern.finditer(html_text):
        href = _normalize_wechat_result_url(match.group("href") or "")
        if not href:
            continue
        if "mp.weixin.qq.com" not in href and "weixin.sogou.com/link?" not in href:
            continue

        title = _clean_html_text(match.group("title") or "")
        if not title or not _looks_like_wechat_event_title(title):
            continue

        title_key = re.sub(r"\s+", " ", title.lower()).strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        context_raw = html_text[max(0, match.start() - 280): min(len(html_text), match.end() + 320)]
        context_text = _clean_html_text(context_raw)
        event_time = _extract_wechat_event_time(title, context_text)

        raw_text = f"{title} {context_text}".lower()
        event_format = "线上" if any(w in raw_text for w in ["线上", "直播", "webinar", "在线"]) else "线下"
        location = "线上" if event_format == "线上" else f"{city}（{center_name}公众号）"
        description = (
            f"来源：{city}{center_name}微信公众号线索。"
            "建议点击原文确认场馆、日期和报名方式。"
        )

        keywords, industries = _detect_event_profile(title, description)
        high_value = any(marker in f"{title} {context_text}" for marker in EVENT_MARKERS)

        collected.append(
            {
                "title": title,
                "time": event_time,
                "location": location,
                "format": event_format,
                "source": "wechat",
                "source_detail": f"微信公众号（{center_name}）",
                "keywords": keywords,
                "target_industries": industries,
                "description": description,
                "registration_deadline": "详见公众号原文",
                "value": "高" if high_value else "中",
                "url": href,
            }
        )

        if len(collected) >= max_items:
            break

    return collected


def _same_canonical_city(city_a: str, city_b: str) -> bool:
    left = _canonical_city_name(city_a)
    right = _canonical_city_name(city_b)
    return bool(left and right and left == right)


def _source_city_priority_rank(source_city: str, preferred_city: str) -> tuple[int, float]:
    source = _canonical_city_name(source_city)
    preferred = _canonical_city_name(preferred_city)

    if not preferred:
        return 2, 9999.0
    if source and source == preferred:
        return 0, 0.0

    if source in MAJOR_CITY_COORDS and preferred in MAJOR_CITY_COORDS:
        src_lat, src_lon = MAJOR_CITY_COORDS[source]
        pref_lat, pref_lon = MAJOR_CITY_COORDS[preferred]
        distance = _haversine_km(src_lat, src_lon, pref_lat, pref_lon)
        trip = _estimate_trip(distance)
        travel_hours = float(trip.get("travel_hours", 99.0) or 99.0)
        if travel_hours <= 2.5:
            return 1, travel_hours
        if travel_hours <= 4.0:
            return 2, travel_hours
        return 3, travel_hours

    return 3, 9999.0


def _rotate_list(items: list[dict], offset: int) -> list[dict]:
    if not items:
        return []
    shift = offset % len(items)
    return items[shift:] + items[:shift]


def _prioritize_exhibition_sources(
    sources: list[dict[str, str]],
    preferred_city: str,
    seed: int,
) -> list[dict[str, str]]:
    if not sources:
        return []

    preferred = _canonical_city_name(preferred_city)
    if not preferred:
        return _rotate_list(list(sources), seed)

    same_city: list[dict[str, str]] = []
    nearby_city: list[dict[str, str]] = []
    midrange_city: list[dict[str, str]] = []
    other_city: list[dict[str, str]] = []

    for source in sources:
        rank, _ = _source_city_priority_rank(str(source.get("city", "")), preferred)
        if rank == 0:
            same_city.append(source)
        elif rank == 1:
            nearby_city.append(source)
        elif rank == 2:
            midrange_city.append(source)
        else:
            other_city.append(source)

    prioritized = (
        _rotate_list(same_city, seed)
        + _rotate_list(nearby_city, seed)
        + _rotate_list(midrange_city, seed)
        + _rotate_list(other_city, seed)
    )
    return prioritized


def _fetch_wechat_exhibition_center_events(max_items: int = 8, preferred_city: str = "") -> tuple[list[dict], list[str]]:
    collected: list[dict] = []
    warnings: list[str] = []
    seen_urls = set()

    source_seed = int(datetime.now().strftime("%Y%m%d%H"))
    prioritized_sources = _prioritize_exhibition_sources(
        WECHAT_EXHIBITION_CENTER_SOURCES,
        preferred_city=preferred_city,
        seed=source_seed,
    )

    for source in prioritized_sources:
        query_url = _build_wechat_search_url(source["query"], city_hint=source["city"])
        html_text = _safe_get_text(query_url, timeout=9)
        if not html_text:
            continue

        per_site_limit = 4 if _same_canonical_city(source.get("city", ""), preferred_city) else 3

        candidates = _extract_wechat_exhibition_events(
            html_text,
            city=source["city"],
            center_name=source["center"],
            max_items=per_site_limit,
        )
        for event in candidates:
            event_url = str(event.get("url", "")).strip()
            if event_url and event_url in seen_urls:
                continue
            if event_url:
                seen_urls.add(event_url)
            collected.append(event)
            if len(collected) >= max_items:
                return collected, warnings

    if not collected:
        warnings.append("会展中心公众号线索暂未返回可解析活动（可能受平台反爬限制）")

    return collected, warnings


def _interleave_event_sources(source_buckets: list[list[dict]], max_items: int) -> list[dict]:
    merged: list[dict] = []
    index = 0

    while len(merged) < max_items:
        progressed = False
        for bucket in source_buckets:
            if index < len(bucket):
                merged.append(bucket[index])
                progressed = True
                if len(merged) >= max_items:
                    break

        if not progressed:
            break
        index += 1

    return merged


def _looks_like_exhibition_event_title(title: str) -> bool:
    text = _clean_html_text(title)
    if not text or len(text) < 6:
        return False

    if any(marker in text for marker in EXHIBITION_CENTER_TITLE_EXCLUDE_MARKERS):
        return False

    if any(marker in text for marker in EXHIBITION_CENTER_TITLE_MARKERS):
        return True

    return bool(re.search(r"\d{1,2}[月\-/.]\d{1,2}", text) and ("展" in text or "会" in text))


def _extract_exhibition_event_time(title: str, context_text: str = "") -> str:
    text = f"{title} {context_text}"

    ymd_match = re.search(r"(20\d{2})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})", text)
    if ymd_match:
        try:
            dt = datetime(int(ymd_match.group(1)), int(ymd_match.group(2)), int(ymd_match.group(3)))
            return dt.strftime("%m-%d")
        except Exception:
            pass

    md_match = re.search(r"(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*(?:日|号)?", text)
    if md_match:
        month = int(md_match.group(1))
        day = int(md_match.group(2))
        try:
            now = datetime.now()
            dt = datetime(now.year, month, day)
            if dt.date() < now.date():
                dt = datetime(now.year + 1, month, day)
            return dt.strftime("%m-%d")
        except Exception:
            pass

    return "待确认（官网排期）"


def _extract_official_exhibition_events(
    html_text: str,
    source: dict[str, str],
    max_items: int = 2,
) -> list[dict]:
    if not html_text:
        return []

    city = str(source.get("city", "")).strip() or "本地"
    center_name = str(source.get("center", "会展中心")).strip() or "会展中心"
    base_url = str(source.get("schedule_url") or source.get("site") or "").strip()

    anchor_pattern = re.compile(r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<title>.*?)</a>', flags=re.I | re.S)
    collected: list[dict] = []
    seen_titles = set()

    for match in anchor_pattern.finditer(html_text):
        title = _clean_html_text(match.group("title") or "")
        if not _looks_like_exhibition_event_title(title):
            continue

        title_key = re.sub(r"\s+", " ", title.lower()).strip()
        if title_key in seen_titles:
            continue

        href = _normalize_url_with_base(match.group("href") or "", base_url)
        if not href:
            continue

        context_raw = html_text[max(0, match.start() - 240): min(len(html_text), match.end() + 320)]
        context_text = _clean_html_text(context_raw)
        event_time = _extract_exhibition_event_time(title, context_text)

        raw_text = f"{title} {context_text}".lower()
        event_format = "线上" if any(w in raw_text for w in ["线上", "直播", "webinar", "在线"]) else "线下"
        location = "线上" if event_format == "线上" else f"{city} · {center_name}"
        description = f"来源：{city}{center_name}官网展会排期，建议点击官方链接确认展位与报名信息。"

        keywords, industries = _detect_event_profile(title, description)
        high_value = any(marker in f"{title} {context_text}" for marker in EVENT_MARKERS) or any(
            marker in title for marker in ["展会", "博览会", "交易会", "峰会", "论坛"]
        )

        seen_titles.add(title_key)
        collected.append(
            {
                "title": _normalize_event_text(title, max_len=96),
                "time": event_time,
                "location": location,
                "format": event_format,
                "source": "official_exhibition",
                "source_detail": f"会展中心官网排期（{center_name}）",
                "keywords": keywords,
                "target_industries": industries,
                "description": description,
                "registration_deadline": "详见官网排期页",
                "value": "高" if high_value else "中",
                "url": href,
            }
        )

        if len(collected) >= max_items:
            break

    return collected


def _is_official_exhibition_event(event: dict) -> bool:
    source = str(event.get("source", "")).strip().lower()
    detail = str(event.get("source_detail", "")).strip()
    return source == "official_exhibition" or "会展中心官网排期" in detail or "官网排期入口" in detail


def _build_official_exhibition_fallback_event(source: dict[str, str]) -> dict:
    city = str(source.get("city", "")).strip() or "本地"
    center_name = str(source.get("center", "会展中心")).strip() or "会展中心"
    schedule_url = str(source.get("schedule_url") or source.get("site") or "").strip()

    title = f"{city}{center_name}近期展会排期（官方入口）"
    description = "来源：会展中心官网排期入口。若结构化列表未返回，可先进入官方页查看最新展会日历与报名信息。"
    keywords, industries = _detect_event_profile(title, description)

    return {
        "title": _normalize_event_text(title, max_len=96),
        "time": "近期",
        "location": f"{city} · {center_name}",
        "format": "线下",
        "source": "official_exhibition",
        "source_detail": f"会展中心官网排期（{center_name}） · 官网排期入口",
        "keywords": keywords,
        "target_industries": industries,
        "description": description,
        "registration_deadline": "请进入官网排期入口确认",
        "value": "中",
        "url": schedule_url,
        "is_fallback": True,
    }


def _fetch_official_exhibition_center_events(max_items: int = 24, preferred_city: str = "") -> tuple[list[dict], list[str]]:
    sources = OFFICIAL_EXHIBITION_CENTER_SOURCES
    if not sources:
        return [], ["会展中心官网源为空"]

    preferred_city_norm = _canonical_city_name(preferred_city)
    batch_base = EXHIBITION_CENTER_FETCH_BATCH_SIZE + (8 if preferred_city_norm else 0)
    batch_size = min(batch_base, len(sources))
    seed = int(datetime.now().strftime("%Y%m%d%H"))
    prioritized_sources = _prioritize_exhibition_sources(sources, preferred_city=preferred_city_norm, seed=seed)
    selected_sources = prioritized_sources[:batch_size]

    collected: list[dict] = []
    warnings: list[str] = []
    seen_titles = set()
    seen_urls = set()
    fallback_count = 0

    for source in selected_sources:
        fetch_url = str(source.get("schedule_url") or source.get("site") or "").strip()
        if not fetch_url:
            continue

        per_site_limit = EXHIBITION_CENTER_PER_SITE_LIMIT + (1 if _same_canonical_city(source.get("city", ""), preferred_city_norm) else 0)
        fallback_allowed = (
            _same_canonical_city(source.get("city", ""), preferred_city_norm)
            if preferred_city_norm
            else len(collected) < 3
        )

        html_text = _safe_get_text(fetch_url, timeout=7)
        candidates: list[dict] = []
        if html_text:
            candidates = _extract_official_exhibition_events(
                html_text,
                source=source,
                max_items=per_site_limit,
            )

        if not candidates and fallback_allowed:
            fallback_event = _build_official_exhibition_fallback_event(source)
            if fallback_event.get("url"):
                candidates = [fallback_event]

        for event in candidates:
            title_key = re.sub(r"\s+", " ", str(event.get("title", "")).lower()).strip()
            event_url = str(event.get("url", "")).strip()

            if title_key and title_key in seen_titles:
                continue
            if event_url and event_url in seen_urls:
                continue
            if not _is_mainland_event(event):
                continue

            if title_key:
                seen_titles.add(title_key)
            if event_url:
                seen_urls.add(event_url)

            collected.append(event)
            if event.get("is_fallback"):
                fallback_count += 1
            if len(collected) >= max_items:
                if fallback_count:
                    warnings.append(f"会展中心官网结构化抓取受限，已补充 {fallback_count} 条官网排期入口直达")
                if preferred_city_norm:
                    local_cnt = sum(1 for item in collected if _same_canonical_city(_extract_event_city(item), preferred_city_norm))
                    warnings.append(f"已按{preferred_city_norm}优先抓取会展中心官网，补充活动 {len(collected)} 条（本地{local_cnt}条）")
                else:
                    warnings.append(f"已补充会展中心官网排期活动 {len(collected)} 条")
                return collected, warnings

    if collected:
        if fallback_count:
            warnings.append(f"会展中心官网结构化抓取受限，已补充 {fallback_count} 条官网排期入口直达")
        if preferred_city_norm:
            local_cnt = sum(1 for item in collected if _same_canonical_city(_extract_event_city(item), preferred_city_norm))
            warnings.append(f"已按{preferred_city_norm}优先抓取会展中心官网，补充活动 {len(collected)} 条（本地{local_cnt}条）")
        else:
            warnings.append(f"已补充会展中心官网排期活动 {len(collected)} 条")
    else:
        if preferred_city_norm:
            warnings.append(f"会展中心官网排期暂未返回可解析活动（优先城市：{preferred_city_norm}，可能受站点结构或反爬限制）")
        else:
            warnings.append("会展中心官网排期暂未返回可解析活动（可能受站点结构或反爬限制）")

    return collected, warnings


def _fetch_platform_portal_events(max_items: int = 10) -> list[dict]:
    entries: list[dict] = []
    query_keywords = list(dict.fromkeys(HUODONGJIA_EVENT_KEYWORDS + ["会展", "路演", "沙龙"]))

    for platform in EVENT_DISCOVERY_PLATFORMS:
        for keyword in query_keywords[:2]:
            title = f"{platform['name']}商机入口：{keyword}"
            description = (
                f"来自{platform['name']}平台检索入口，可按关键词快速发现商业活动。"
                f"来源域名：{platform['domain']}。"
            )
            keywords, industries = _detect_event_profile(title, description)
            entries.append(
                {
                    "title": title,
                    "time": "持续更新",
                    "location": "全国（平台检索）",
                    "format": "线上",
                    "source": "portal",
                    "source_detail": f"{platform['name']}（活动信息获取平台）",
                    "keywords": keywords,
                    "target_industries": industries,
                    "description": description,
                    "registration_deadline": "详见平台页",
                    "value": "中",
                    "url": _build_baidu_site_search_url(platform["domain"], keyword, city_hint=""),
                }
            )
            if len(entries) >= max_items:
                return entries

    return entries


def _fetch_wechat_channel_events(max_items: int = 4) -> list[dict]:
    entries: list[dict] = []
    for channel_name, query in WECHAT_EVENT_CHANNEL_TOPICS:
        title = f"微信公众号线索：{channel_name}"
        description = (
            "公众号活动信息受平台授权与反爬策略限制，不做直接抓取；"
            "已提供检索入口用于发现本地会展/论坛/校园活动。"
        )
        keywords, industries = _detect_event_profile(title, description)
        entries.append(
            {
                "title": title,
                "time": "持续更新",
                "location": "本地/线上",
                "format": "线上",
                "source": "portal",
                "source_detail": "微信公众号活动线索入口",
                "keywords": keywords,
                "target_industries": industries,
                "description": description,
                "registration_deadline": "详见检索结果",
                "value": "中",
                "url": _build_wechat_search_url(query),
            }
        )
        if len(entries) >= max_items:
            break

    return entries


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


def _build_live_events(max_items: int = 12, preferred_city: str = "") -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    all_events: list[dict] = []
    preferred_city_norm = _canonical_city_name(preferred_city)

    huodongxing_events = _fetch_huodongxing_events(max_items=max_items * 2)
    huodongjia_events = _fetch_huodongjia_events(max_items=max_items * 2)
    wechat_exhibition_events, wechat_warnings = _fetch_wechat_exhibition_center_events(
        max_items=max(max_items, 8),
        preferred_city=preferred_city_norm,
    )
    official_exhibition_events, official_warnings = _fetch_official_exhibition_center_events(
        max_items=max(max_items * 2, 24),
        preferred_city=preferred_city_norm,
    )

    mixed_events = _interleave_event_sources(
        [official_exhibition_events, huodongxing_events, huodongjia_events, wechat_exhibition_events],
        max_items=max_items * 4,
    )
    if mixed_events:
        all_events.extend(mixed_events)

    if not huodongxing_events and not huodongjia_events and not wechat_exhibition_events and not official_exhibition_events:
        warnings.append("本土活动源暂不可用（活动行/活动家/会展中心官网/公众号均未返回可用活动）")

    if official_warnings:
        warnings.extend(official_warnings)

    if wechat_warnings:
        warnings.extend(wechat_warnings)
    elif wechat_exhibition_events:
        warnings.append(f"已补充会展中心公众号线索 {len(wechat_exhibition_events)} 条")

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

    current_live = _dedupe_live_events(all_events, max_items=max_items)
    if len(current_live) < max_items:
        shortage = max_items - len(current_live)
        portal_events = _fetch_platform_portal_events(max_items=min(12, max(4, shortage * 2)))
        wechat_events = _fetch_wechat_channel_events(max_items=min(6, max(2, shortage)))
        if portal_events:
            all_events.extend(portal_events)
        if wechat_events:
            all_events.extend(wechat_events)
        if portal_events or wechat_events:
            warnings.append("真实活动不足，已补充活动信息获取平台与公众号线索入口")

    live_events = _dedupe_live_events(all_events, max_items=max_items)
    if not live_events:
        warnings.append("活动源暂不可用")

    return live_events, warnings


@st.cache_data(show_spinner=False)
def get_realtime_feeds(refresh_bucket: int, preferred_city: str = "") -> tuple[list[dict], list[dict], str, list[str]]:
    del refresh_bucket  # 作为缓存分桶键使用
    preferred_city = _canonical_city_name(preferred_city)
    warnings = []

    live_news = _build_live_news(max_items=24, preferred_city=preferred_city)
    if not live_news:
        live_news = DEFAULT_NEWS.copy()
        warnings.append("新闻源暂不可用，已自动回退到内置热点")

    live_events, event_warnings = _build_live_events(max_items=12, preferred_city=preferred_city)
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

        .wf-detail-link {
            font-size: 0.86em;
            font-family: "SF Mono", "Menlo", "Consolas", monospace;
            font-weight: 600;
            color: #0a66c2;
            text-decoration: none;
            margin-left: 0.32rem;
            white-space: nowrap;
        }

        .wf-detail-link:hover {
            text-decoration: underline;
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

        .wf-action a {
            color: #0a66c2;
            font-weight: 700;
            text-decoration: none;
            margin-right: 0.35rem;
        }

        .wf-action a:hover {
            text-decoration: underline;
        }

        .wf-links {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.36rem;
        }

        .wf-link {
            display: inline-flex;
            align-items: center;
            padding: 0.16rem 0.55rem;
            border-radius: 999px;
            border: 1px solid rgba(10, 102, 194, 0.2);
            background: #f2f8ff;
            font-size: 0.8rem;
        }

        .wf-ai-line {
            margin-top: 0.36rem;
            display: flex;
            gap: 0.34rem;
            overflow-x: auto;
            white-space: nowrap;
            padding-bottom: 0.14rem;
            scrollbar-width: thin;
        }

        .wf-ai-chip {
            display: inline-block;
            border: 1px solid rgba(15, 63, 121, 0.16);
            border-radius: 999px;
            background: #f8fbff;
            padding: 0;
            min-width: max-content;
        }

        .wf-ai-chip summary {
            cursor: pointer;
            color: #0f3f79;
            font-size: 0.8rem;
            font-weight: 700;
            list-style: none;
            padding: 0.18rem 0.62rem;
        }

        .wf-ai-chip summary::-webkit-details-marker {
            display: none;
        }

        .wf-ai-chip[open] {
            border-radius: 14px;
            padding-bottom: 0.28rem;
        }

        .wf-ai-content {
            margin-top: 0.06rem;
            color: #334155;
            font-size: 0.82rem;
            line-height: 1.45;
            white-space: normal;
            padding: 0 0.62rem;
            max-width: 420px;
        }

        .goal-preview {
            margin-top: 0.28rem;
            border: 1px solid rgba(15, 63, 121, 0.16);
            border-radius: 14px;
            background: linear-gradient(180deg, #ffffff, #f8fbff);
            padding: 0.46rem 0.54rem;
        }

        .goal-label {
            color: #0f3f79;
            font-size: 0.78rem;
            font-weight: 700;
            margin-top: 0.2rem;
        }

        .goal-label:first-child {
            margin-top: 0;
        }

        .goal-line {
            color: #334155;
            font-size: 0.86rem;
            line-height: 1.45;
            margin-top: 0.12rem;
        }

        .model-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.84rem;
            margin-top: 0.28rem;
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

            .model-grid {
                grid-template-columns: 1fr;
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


def _infer_boss_news_preferences(boss: dict) -> set[str]:
    text = " ".join([boss.get("industry", ""), boss.get("current_goal", ""), " ".join(boss.get("keywords", []))]).lower()
    prefs: set[str] = set()
    for category, keywords in NEWS_CATEGORY_RULES.items():
        if any(str(keyword).lower() in text for keyword in keywords):
            prefs.add(category)
    return prefs


def _infer_boss_event_preferences(boss: dict) -> set[str]:
    text = " ".join([boss.get("industry", ""), boss.get("current_goal", ""), " ".join(boss.get("keywords", []))]).lower()
    prefs: set[str] = set()
    for industry_name, keywords in EVENT_INDUSTRY_RULES.items():
        if industry_name.lower() in text or any(str(keyword).lower() in text for keyword in keywords):
            prefs.add(industry_name.lower())
    return prefs


def _build_boss_profile_terms(boss: dict) -> list[str]:
    raw_terms: list[str] = []
    raw_terms.extend(_extract_profile_terms(str(boss.get("industry", ""))))
    raw_terms.extend(_extract_profile_terms(str(boss.get("current_goal", ""))))
    for kw in boss.get("keywords", []):
        raw_terms.extend(_extract_profile_terms(str(kw)))

    deduped: list[str] = []
    seen = set()
    for term in raw_terms:
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        deduped.append(term)
    return deduped


def _match_profile_terms(text: str, terms: list[str], limit: int = 6) -> list[str]:
    hits: list[str] = []
    seen = set()
    for term in terms:
        if not term or term in seen:
            continue
        if term in text:
            seen.add(term)
            hits.append(term)
        if len(hits) >= limit:
            break
    return hits


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

    news_terms = _extract_profile_terms(text)
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
    return min(24, int(overlap * 2 + jaccard * 40))


def _news_relevance_score(boss: dict, item: dict) -> tuple[int, list[str]]:
    ignore_keywords = [kw.lower() for kw in boss.get("ignore_keywords", [])]
    boss_keywords = [kw.lower() for kw in boss.get("keywords", [])]
    profile_terms = _build_boss_profile_terms(boss)
    news_prefs = _infer_boss_news_preferences(boss)
    city = _canonical_city_name(str(boss.get("city", "")))

    title = str(item.get("title", ""))
    category = str(item.get("category", ""))
    description = str(item.get("description", ""))
    source = str(item.get("source", ""))
    text = f"{title} {category} {description} {source}".lower()

    if any(ig and ig in text for ig in ignore_keywords):
        return -1, []

    keyword_hits = _match_profile_terms(text, boss_keywords, limit=4)
    term_hits = _match_profile_terms(text, profile_terms, limit=6)
    extra_term_hits = [term for term in term_hits if term not in keyword_hits]
    semantic_score = _semantic_overlap_score(profile_terms, text)

    score = 0
    score += len(keyword_hits) * 24
    score += len(extra_term_hits) * 9
    score += semantic_score

    if category in news_prefs:
        score += 18
    if category == "政策" and (category in news_prefs or keyword_hits or semantic_score >= 8):
        score += 6
    if city and city in text:
        score += 10
    if any(marker in source for marker in ["中国政府网", "百度民生", "新华社", "人民网"]):
        score += 8

    unrelated_hits = 0
    for cat, markers in NEWS_CATEGORY_RULES.items():
        if cat == category or cat in news_prefs:
            continue
        if any(str(marker).lower() in text for marker in markers[:4]):
            unrelated_hits += 1
    score -= min(24, unrelated_hits * 8)

    if category and news_prefs and category not in news_prefs and not keyword_hits and semantic_score < 6:
        score -= 22
    if category == "政策" and "政策" not in news_prefs and not keyword_hits and semantic_score < 8:
        score -= 16

    if not keyword_hits and not extra_term_hits and semantic_score < 8 and category not in news_prefs:
        score -= 24

    score = max(0, min(96, score))
    matched = list(dict.fromkeys(keyword_hits + extra_term_hits))[:3]
    if semantic_score >= 10 and not matched:
        matched = _match_profile_terms(text, profile_terms, limit=2)
    if category in news_prefs and category and category not in matched:
        matched.append(category)

    return score, matched[:3]


def _event_relevance_score(boss: dict, event: dict) -> tuple[int, list[str]]:
    ignore_keywords = [kw.lower() for kw in boss.get("ignore_keywords", [])]
    boss_keywords = [kw.lower() for kw in boss.get("keywords", [])]
    profile_terms = _build_boss_profile_terms(boss)
    event_prefs = _infer_boss_event_preferences(boss)
    city = _canonical_city_name(str(boss.get("city", "")))

    event_keywords = [str(kw).lower() for kw in event.get("keywords", [])]
    event_industries = [str(ind).lower() for ind in event.get("target_industries", [])]
    is_official_exhibition = _is_official_exhibition_event(event)
    text = (
        f"{event.get('title', '')} {event.get('description', '')} {event.get('location', '')} "
        f"{' '.join(event_keywords)} {' '.join(event_industries)}"
    ).lower()

    if any(ig and ig in text for ig in ignore_keywords):
        return -1, []

    keyword_hits = _match_profile_terms(text, boss_keywords, limit=4)
    term_hits = _match_profile_terms(text, profile_terms, limit=6)
    extra_term_hits = [term for term in term_hits if term not in keyword_hits]

    industry_hits = 0
    for pref in event_prefs:
        if any(pref in ind or ind in pref for ind in event_industries):
            industry_hits += 1

    score = 0
    score += min(36, industry_hits * 24)
    score += len(keyword_hits) * 18
    score += len(extra_term_hits) * 8
    if is_official_exhibition:
        # 官方会展排期通常描述偏简短，给一个温和基线，避免被过早过滤。
        score += 12

    location_text = f"{event.get('title', '')} {event.get('location', '')}"
    if city and city in location_text:
        score += 10
        if is_official_exhibition:
            score += 4
    if _is_online_event(event):
        score += 4
    if float(event.get("travel_hours", 9) or 9) <= MAX_TRAVEL_HOURS:
        score += 8
    if event.get("value") == "高":
        score += 6
    if event.get("source") == "portal":
        score -= 4

    unrelated_hits = 0
    for industry_name, markers in EVENT_INDUSTRY_RULES.items():
        industry_key = industry_name.lower()
        if industry_key in event_prefs:
            continue
        if any(str(marker).lower() in text for marker in markers[:4]):
            unrelated_hits += 1
    if is_official_exhibition:
        score -= min(10, unrelated_hits * 3)
    else:
        score -= min(16, unrelated_hits * 4)

    if event_industries and industry_hits == 0 and not keyword_hits:
        score -= 4 if is_official_exhibition else 10

    score = max(0, min(98, score))
    matched = list(dict.fromkeys(keyword_hits + extra_term_hits))[:3]
    if not matched and is_official_exhibition:
        city_hint = _extract_event_city(event)
        matched = [term for term in [city_hint, "会展资源"] if term][:2]
    if not matched and event_industries:
        matched = [event_industries[0][:8]]

    return score, matched[:3]


def _news_relevance_tier(boss: dict, item: dict) -> int:
    score, _ = _news_relevance_score(boss, item)
    if score < 0:
        return -1
    if score >= 52:
        return 2
    if score >= 30:
        return 1
    return 0


def _event_relevance_tier(boss: dict, event: dict) -> int:
    score, _ = _event_relevance_score(boss, event)
    if score < 0:
        return -1
    if score >= 52:
        return 2
    if score >= 26:
        return 1
    return 0


def _event_rank_key(event: dict) -> tuple[int, int, int]:
    value_weight = 1 if event.get("value") == "高" else 0
    reachable = 1 if float(event.get("travel_hours", 9) or 9) <= MAX_TRAVEL_HOURS else 0
    online = 1 if _is_online_event(event) else 0
    return (value_weight, reachable, online)


def _build_industry_event_pool(boss: dict, events: list[dict], top_n: int = 18, min_secondary: int = 2) -> list[dict]:
    deduped: list[dict] = []
    seen_titles = set()
    for event in events:
        title_key = re.sub(r"\s+", " ", str(event.get("title", "")).lower()).strip()
        if not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(event)

    primary: list[tuple[int, tuple[int, int, int], dict]] = []
    secondary: list[tuple[int, tuple[int, int, int], dict]] = []
    for event in deduped:
        relevance_score, matched = _event_relevance_score(boss, event)
        if relevance_score < 0:
            continue
        tier = _event_relevance_tier(boss, event)
        if tier <= 0:
            continue

        event_copy = {
            **event,
            "score": max(int(event.get("score", 0) or 0), min(96, int(relevance_score))),
            "matched_keywords": event.get("matched_keywords") or (matched[:3] if matched else [boss.get("industry", "行业相关")[:8]]),
        }
        rank_key = _event_rank_key(event_copy)

        if tier >= 2:
            primary.append((int(event_copy["score"]), rank_key, event_copy))
        elif tier == 1:
            secondary.append((int(event_copy["score"]), rank_key, event_copy))

    primary.sort(key=lambda item: (item[0], item[1]), reverse=True)
    secondary.sort(key=lambda item: (item[0], item[1]), reverse=True)

    selected: list[dict] = []
    if primary:
        selected.extend(item[2] for item in primary[:top_n])
        if len(selected) < top_n:
            selected.extend(item[2] for item in secondary[: top_n - len(selected)])
    elif secondary:
        keep = max(1, min(min_secondary, len(secondary), top_n))
        selected.extend(item[2] for item in secondary[:keep])

    return selected[:top_n]


def _build_industry_news_pool(boss: dict, news_items: list[dict], top_n: int = 24, min_secondary: int = 2) -> list[dict]:
    deduped: list[dict] = []
    seen_titles = set()
    for item in news_items:
        title_key = re.sub(r"\s+", " ", str(item.get("title", "")).lower()).strip()
        if not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(item)

    primary: list[tuple[int, dict]] = []
    secondary: list[tuple[int, dict]] = []
    for item in deduped:
        relevance_score, matched = _news_relevance_score(boss, item)
        if relevance_score < 0:
            continue
        tier = _news_relevance_tier(boss, item)
        if tier <= 0:
            continue

        news_copy = {
            **item,
            "score": max(int(item.get("score", 0) or 0), min(95, int(relevance_score))),
            "matched": item.get("matched") or (matched[:3] if matched else [str(item.get("category", "行业热点"))]),
        }

        if tier >= 2:
            primary.append((int(news_copy["score"]), news_copy))
        elif tier == 1:
            secondary.append((int(news_copy["score"]), news_copy))

    primary.sort(key=lambda item: item[0], reverse=True)
    secondary.sort(key=lambda item: item[0], reverse=True)

    selected: list[dict] = []
    if primary:
        selected.extend(item[1] for item in primary[:top_n])
        if len(selected) < top_n:
            selected.extend(item[1] for item in secondary[: top_n - len(selected)])
    elif secondary:
        keep = max(1, min(min_secondary, len(secondary), top_n))
        selected.extend(item[1] for item in secondary[:keep])

    return selected[:top_n]


def _infer_goal_domain(boss: dict) -> str:
    text = " ".join([boss.get("industry", ""), " ".join(boss.get("keywords", [])), boss.get("current_goal", "")]).lower()
    rules = [
        ("餐饮", ["餐饮", "门店", "连锁", "预制菜", "外卖"]),
        ("品牌", ["品牌", "营销", "内容", "私域", "新消费"]),
        ("企业培训", ["培训", "管理咨询", "hr", "组织发展"]),
        ("外贸", ["外贸", "跨境", "出口", "东南亚", "供应链"]),
        ("设计", ["设计", "ui", "ux", "用户体验"]),
        ("电商", ["电商", "直播", "抖音", "流量", "选款"]),
        ("汽配", ["汽配", "汽车配件", "新能源", "b2b", "出口"]),
        ("猎头", ["猎头", "招聘", "人才", "高管", "hr"]),
        ("建材", ["建材", "工程", "装修", "地产", "采购"]),
        ("法律科技", ["法律", "律所", "合规", "saas", "融资"]),
    ]
    for domain, markers in rules:
        if any(marker in text for marker in markers):
            return domain
    return "通用"


def _generate_smart_goal(
    boss: dict,
    news_items: list[dict],
    events: list[dict],
    seed: int = 0,
    style_mode: str = "平衡（推荐）",
) -> str:
    domain = _infer_goal_domain(boss)
    city = _canonical_city_name(boss.get("city", "")) or "本地"
    primary_keyword = (boss.get("keywords") or ["核心业务"])[0]
    goal_preference = str(boss.get("goal_preference", "")).strip()

    related_news = [item for item in news_items if _news_relevance_tier(boss, item) >= 1]
    related_events = [item for item in events if _event_relevance_tier(boss, item) >= 1]
    hot_category = "行业"
    for item in related_news:
        cat = str(item.get("category", "")).strip()
        if cat:
            hot_category = cat
            break

    goal_packs = {
        "餐饮": [
            {
                "headline": "在{city}打出可复制的门店增长样板",
                "action": "7天内完成3家目标门店拜访并确认1次试点合作",
                "stretch": "14天内沉淀1个可展示案例并带来2个转介绍线索",
            },
            {
                "headline": "围绕{primary_keyword}拿下{city}连锁客户首单",
                "action": "本周完成2位决策人面谈并提交可执行报价方案",
                "stretch": "本月将核心门店转化率提升8%-12%",
            },
        ],
        "品牌": [
            {
                "headline": "在{city}做出1个能被传播的品牌增长案例",
                "action": "本周完成2次高质量客户触达并锁定1个提案机会",
                "stretch": "14天内实现1个可公开展示的品牌合作成果",
            },
            {
                "headline": "围绕{primary_keyword}切入高客单品牌客户",
                "action": "7天内提交2版差异化方案并推进1次复盘会",
                "stretch": "本月新增2个稳定付费客户",
            },
        ],
        "企业培训": [
            {
                "headline": "在{city}拿下企业培训场景的标杆客户",
                "action": "本周完成2次关键决策人沟通并推进1个试讲",
                "stretch": "14天内形成1个可复制签单脚本",
            },
            {
                "headline": "围绕{primary_keyword}缩短培训项目成交周期",
                "action": "7天内锁定1个明确预算客户并提交落地排期",
                "stretch": "本月把需求到签约周期压缩20%",
            },
        ],
        "外贸": [
            {
                "headline": "在{city}跑通一条外贸新增询盘链路",
                "action": "本周完成2个高潜海外客户触达并推进1轮报价",
                "stretch": "14天内形成1个可复用出海获客模板",
            },
            {
                "headline": "围绕{primary_keyword}拿下跨境高价值客户",
                "action": "7天内完善报价与交付优势并完成1次视频洽谈",
                "stretch": "本月实现1笔新增出口订单",
            },
        ],
        "设计": [
            {
                "headline": "在{city}拿下1个设计升级标杆项目",
                "action": "本周完成2个潜在客户方案演示并确定1次试合作",
                "stretch": "14天内沉淀1个可展示前后对比案例",
            },
            {
                "headline": "围绕{primary_keyword}做出可量化的设计价值",
                "action": "7天内输出1版带业务指标的改版提案",
                "stretch": "本月推动1个项目进入长期合作",
            },
        ],
        "电商": [
            {
                "headline": "在{city}打通电商增长的可复制打法",
                "action": "本周跑完1轮选品与投放小闭环并复盘关键数据",
                "stretch": "14天内将核心商品转化率提升10%",
            },
            {
                "headline": "围绕{primary_keyword}拿下高潜流量窗口",
                "action": "7天内完成2次素材迭代并验证1条高ROI链路",
                "stretch": "本月新增1个稳定放量品类",
            },
        ],
        "汽配": [
            {
                "headline": "在{city}拿下汽配出海的关键合作机会",
                "action": "本周完成2个B2B客户深聊并推进1轮样品报价",
                "stretch": "14天内确定1个稳定海外渠道合作意向",
            },
            {
                "headline": "围绕{primary_keyword}放大交付与价格优势",
                "action": "7天内优化报价包并完成1次关键客户提案",
                "stretch": "本月实现1笔新增高毛利订单",
            },
        ],
        "猎头": [
            {
                "headline": "在{city}打造中高端岗位交付样板",
                "action": "本周提交2位高匹配候选人并推进1次面试",
                "stretch": "14天内拿到1个独家职位合作",
            },
            {
                "headline": "围绕{primary_keyword}提高候选人与职位匹配效率",
                "action": "7天内扩容候选人池并完成2次客户需求澄清",
                "stretch": "本月将推荐到面试转化率提升15%",
            },
        ],
        "建材": [
            {
                "headline": "在{city}拿下工程采购的高价值项目",
                "action": "本周完成2家项目方拜访并推进1轮商务谈判",
                "stretch": "14天内形成1个可成交项目清单",
            },
            {
                "headline": "围绕{primary_keyword}提升建材项目成交确定性",
                "action": "7天内优化账期与回款条款并提交1个正式报价",
                "stretch": "本月新增1个长期供货合作",
            },
        ],
        "法律科技": [
            {
                "headline": "在{city}打出法律科技落地标杆",
                "action": "本周完成1次产品演示并推进1个试点场景",
                "stretch": "14天内沉淀1个可公开案例",
            },
            {
                "headline": "围绕{primary_keyword}切入高价值法务需求",
                "action": "7天内完成2次关键客户访谈并提交落地方案",
                "stretch": "本月拿下1个稳定续费客户",
            },
        ],
        "通用": [
            {
                "headline": "在{city}聚焦{primary_keyword}拿下关键增长突破",
                "action": "本周完成2次高质量客户触达并推进1个明确商机",
                "stretch": "14天内形成1个可复制增长闭环",
            },
            {
                "headline": "围绕{hot_category}窗口抢占先机",
                "action": "7天内完成1轮方案验证并拿到关键反馈",
                "stretch": "本月沉淀1个可对外展示的增长成果",
            },
        ],
    }

    style_options = {"稳健落地", "平衡（推荐）", "高势能冲刺"}
    normalized_style = style_mode if style_mode in style_options else "平衡（推荐）"

    rng_seed = seed + sum(ord(ch) for ch in f"{boss.get('name', '')}-{city}-{domain}-{normalized_style}-{goal_preference}")
    rng = random.Random(rng_seed)
    pack = rng.choice(goal_packs.get(domain, goal_packs["通用"]))
    headline = pack["headline"].format(city=city, primary_keyword=primary_keyword, hot_category=hot_category)
    action = pack["action"].format(city=city, primary_keyword=primary_keyword, hot_category=hot_category)
    stretch = pack["stretch"].format(city=city, primary_keyword=primary_keyword, hot_category=hot_category)

    event_name = ""
    if related_events:
        event_name = str(related_events[0].get("title", "")).strip()
    if event_name and normalized_style != "稳健落地" and rng.random() > 0.45:
        headline = f"借势「{event_name[:20]}」抢占关键窗口"

    goal_lines: list[str] = ["目标：", headline, "落地动作：", action]
    if normalized_style != "稳健落地":
        goal_lines.extend(["冲刺目标：", stretch])

    if goal_preference:
        goal_lines.extend(["目标偏好：", goal_preference])

    return "\n".join(goal_lines)


def _generate_distinct_smart_goal(
    boss: dict,
    news_items: list[dict],
    events: list[dict],
    base_seed: int,
    style_mode: str,
    previous_goal: str = "",
    force_new: bool = False,
) -> tuple[str, int]:
    offsets = [0, 11, 23, 37, 53, 71, 97, 131]
    last_goal = str(previous_goal or "").strip()

    fallback_goal = ""
    fallback_seed = base_seed

    for offset in offsets:
        candidate_seed = base_seed + offset
        candidate_goal = _generate_smart_goal(
            boss,
            news_items,
            events,
            seed=candidate_seed,
            style_mode=style_mode,
        )
        if not force_new:
            return candidate_goal, candidate_seed

        if not last_goal or candidate_goal.strip() != last_goal:
            return candidate_goal, candidate_seed

        fallback_goal = candidate_goal
        fallback_seed = candidate_seed

    if fallback_goal:
        focus_tags = [
            "先拿下决策人会面",
            "先拿到可展示案例",
            "先拿到首个试点客户",
            "先跑通最小成交闭环",
        ]
        tag = focus_tags[(base_seed + len(last_goal)) % len(focus_tags)]
        goal_lines = [line for line in fallback_goal.splitlines() if line.strip()]
        goal_lines.extend(["本次刷新侧重点：", tag])
        return "\n".join(goal_lines), fallback_seed + 1

    return _generate_smart_goal(boss, news_items, events, seed=base_seed, style_mode=style_mode), base_seed


def _goal_headline_text(goal_text: str) -> str:
    lines = [line.strip() for line in str(goal_text or "").splitlines() if line.strip()]
    for line in lines:
        if line.endswith("："):
            continue
        return _normalize_event_text(line, max_len=32)
    return _normalize_event_text(str(goal_text or "今日目标"), max_len=32)


def _goal_preview_html(goal_text: str) -> str:
    lines = [line.strip() for line in str(goal_text or "").splitlines() if line.strip()]
    if not lines:
        return '<div class="goal-preview"><div class="goal-line">暂无目标</div></div>'

    chunks: list[str] = []
    for line in lines:
        if line.endswith("："):
            chunks.append(f'<div class="goal-label">{html.escape(line)}</div>')
        else:
            chunks.append(f'<div class="goal-line">{html.escape(line)}</div>')
    return '<div class="goal-preview">' + "".join(chunks) + "</div>"


def _fallback_news_candidates(boss: dict, news_items: list[dict], top_n: int = 4) -> list[dict]:
    scored: list[tuple[int, int, dict]] = []
    for item in news_items:
        relevance_score, matched = _news_relevance_score(boss, item)
        if relevance_score < 0:
            continue

        tier = _news_relevance_tier(boss, item)
        if tier <= 0:
            continue

        news_copy = {
            **item,
            "score": max(int(item.get("score", 0) or 0), min(84, int(relevance_score))),
            "matched": item.get("matched") or (matched[:3] if matched else [str(item.get("category", "行业热点"))]),
        }
        scored.append((tier, int(news_copy["score"]), news_copy))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    primary = [item for tier, _, item in scored if tier >= 2]
    secondary = [item for tier, _, item in scored if tier == 1]
    selected: list[dict] = []

    if primary:
        selected.extend(primary[:top_n])
        if len(selected) < top_n:
            selected.extend(secondary[: top_n - len(selected)])
    elif secondary:
        keep = max(1, min(2, top_n, len(secondary)))
        selected.extend(secondary[:keep])

    return selected[:top_n]


def _fallback_event_candidates(boss: dict, events: list[dict], top_n: int = 3) -> list[dict]:
    scored: list[tuple[int, int, tuple[int, int, int], dict]] = []
    for event in events:
        relevance_score, matched = _event_relevance_score(boss, event)
        if relevance_score < 0:
            continue

        tier = _event_relevance_tier(boss, event)
        if tier <= 0:
            continue

        event_copy = {
            **event,
            "score": max(int(event.get("score", 0) or 0), min(86, int(relevance_score))),
            "matched_keywords": event.get("matched_keywords") or (matched[:3] if matched else [boss.get("industry", "行业相关")[:8]]),
        }
        scored.append((tier, int(event_copy["score"]), _event_rank_key(event_copy), event_copy))

    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

    primary = [item for tier, _, _, item in scored if tier >= 2]
    secondary = [item for tier, _, _, item in scored if tier == 1]
    selected: list[dict] = []

    if primary:
        selected.extend(primary[:top_n])
        if len(selected) < top_n:
            selected.extend(secondary[: top_n - len(selected)])
    elif secondary:
        keep = max(1, min(2, top_n, len(secondary)))
        selected.extend(secondary[:keep])

    return selected[:top_n]


def _minimum_industry_consistent_events(boss: dict, events: list[dict], top_n: int = 1) -> list[dict]:
    deduped: list[dict] = []
    seen_titles = set()
    for event in events or []:
        key = re.sub(r"\s+", " ", str(event.get("title", "")).lower()).strip()
        if not key or key in seen_titles:
            continue
        seen_titles.add(key)
        deduped.append(event)

    event_prefs = _infer_boss_event_preferences(boss)
    scored: list[tuple[int, int, int, tuple[int, int, int], dict]] = []

    for event in deduped:
        relevance_score, matched = _event_relevance_score(boss, event)
        if relevance_score < 0:
            continue

        travel_hours = float(event.get("travel_hours", 99) or 99)
        if (not _is_online_event(event)) and travel_hours > (MAX_TRAVEL_HOURS + EXTENDED_EVENT_TRAVEL_BUFFER_HOURS):
            continue

        event_industries = [str(ind).lower() for ind in event.get("target_industries", [])]
        industry_fit = 0
        for pref in event_prefs:
            if any(pref in ind or ind in pref for ind in event_industries):
                industry_fit = 1
                break

        tier = _event_relevance_tier(boss, event)
        base_floor = 34 if industry_fit else 26
        event_copy = {
            **event,
            "score": min(92, max(int(event.get("score", 0) or 0), int(relevance_score), base_floor if tier <= 0 else 0)),
            "matched_keywords": event.get("matched_keywords") or (matched[:3] if matched else [boss.get("industry", "行业相关")[:8]]),
        }
        if event_copy.get("extended_reach"):
            detail = str(event_copy.get("source_detail", "本土活动源")).strip()
            if "稍远可达" not in detail:
                event_copy["source_detail"] = f"{detail} · 稍远可达"

        scored.append((industry_fit, tier, int(event_copy["score"]), _event_rank_key(event_copy), event_copy))

    if not scored:
        return []

    scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
    return [item[4] for item in scored[:top_n]]


def _ensure_exhibition_event_visibility(
    boss: dict,
    matched_events: list[dict],
    candidate_events: list[dict],
    max_items: int = 3,
) -> tuple[list[dict], bool]:
    current = [{**item} for item in (matched_events or [])]
    if any(_is_official_exhibition_event(event) for event in current):
        return current[:max_items], False

    seen_titles = {
        re.sub(r"\s+", " ", str(item.get("title", "")).lower()).strip()
        for item in current
        if str(item.get("title", "")).strip()
    }

    official_candidates: list[tuple[int, int, tuple[int, int, int], dict]] = []
    for event in candidate_events or []:
        if not _is_official_exhibition_event(event):
            continue

        title_key = re.sub(r"\s+", " ", str(event.get("title", "")).lower()).strip()
        if not title_key or title_key in seen_titles:
            continue

        relevance_score, matched = _event_relevance_score(boss, event)
        if relevance_score < 0:
            continue

        tier = _event_relevance_tier(boss, event)
        base_floor = 36 if tier <= 0 else 0
        event_copy = {
            **event,
            "score": min(94, max(int(event.get("score", 0) or 0), int(relevance_score), base_floor)),
            "matched_keywords": event.get("matched_keywords") or (matched[:3] if matched else ["会展资源"]),
        }
        detail = str(event_copy.get("source_detail", "会展中心官网排期")).strip()
        if "官方入口" not in detail:
            event_copy["source_detail"] = f"{detail} · 官方入口"

        official_candidates.append((tier, int(event_copy["score"]), _event_rank_key(event_copy), event_copy))

    if not official_candidates:
        return current[:max_items], False

    official_candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    best_official = official_candidates[0][3]

    if len(current) < max_items:
        current.append(best_official)
    else:
        ranking: list[tuple[int, int, tuple[int, int, int], int]] = []
        for idx, event in enumerate(current):
            tier = _event_relevance_tier(boss, event)
            score = int(event.get("score", 0) or 0)
            ranking.append((tier, score, _event_rank_key(event), idx))
        ranking.sort(key=lambda item: (item[0], item[1], item[2]))
        replace_idx = ranking[0][3]
        current[replace_idx] = best_official

    current.sort(key=lambda item: (int(item.get("score", 0) or 0), _event_rank_key(item)), reverse=True)
    return current[:max_items], True


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

    scored: list[tuple[int, int, int, dict]] = []
    for event in deduped:
        if not _is_online_event(event):
            continue

        tier = _event_relevance_tier(boss, event)
        if tier < 0:
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

        scored.append((tier, 1 if city_match else 0, int(event_copy["score"]), event_copy))

    scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    selected = [item[3] for item in scored[:top_n]]

    if len(selected) < top_n:
        backup_events = _build_industry_event_pool(boss, TODAY_EVENTS, top_n=8, min_secondary=2)
        for event in backup_events:
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


def _minimum_local_policy_news(news_items: list[dict], top_n: int = 2, boss: dict | None = None) -> list[dict]:
    boss_ref = boss or {}
    boss_keywords = [kw.lower() for kw in boss_ref.get("keywords", [])]
    news_prefs = _infer_boss_news_preferences(boss_ref) if boss_ref else set()

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
        relevance_score, matched = _news_relevance_score(boss_ref, item)
        if relevance_score < 0:
            continue

        category = str(item.get("category", ""))
        title_lower = str(item.get("title", "")).lower()
        kw_hits = sum(1 for kw in boss_keywords if kw and kw in title_lower)
        pref_hit = bool(news_prefs and category in news_prefs)

        # 强约束：既不命中关键词也不命中偏好，且语义分偏低，则不进入最小展示池。
        if boss_keywords and kw_hits == 0 and not pref_hit and relevance_score < 30:
            continue
        if relevance_score < 24 and not pref_hit:
            continue

        bonus = 0
        if pref_hit:
            bonus += 8
        if kw_hits:
            bonus += min(12, kw_hits * 6)
        if category == "政策" and "政策" in news_prefs:
            bonus += 4

        news_copy = {
            **item,
            "score": max(int(item.get("score", 0) or 0), min(88, int(relevance_score) + bonus)),
            "matched": item.get("matched") or (matched[:3] if matched else ([category] if category else ["行业热点"])),
            "source": item.get("source") or "本土热点源",
        }

        tier = 3 if (kw_hits >= 1 or relevance_score >= 58) else (2 if (pref_hit or relevance_score >= 38) else 1)
        scored.append((tier, int(news_copy["score"]), news_copy))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [item[2] for item in scored[:top_n]]

    if len(selected) < top_n:
        selected_titles = {
            re.sub(r"\s+", " ", str(item.get("title", "")).lower()).strip()
            for item in selected
        }

        default_candidates: list[dict] = []
        if news_prefs:
            default_candidates.extend([item for item in DEFAULT_NEWS if item.get("category") in news_prefs])
        default_candidates.extend([item for item in DEFAULT_NEWS if item.get("category") != "政策"])
        if "政策" in news_prefs:
            default_candidates.extend([item for item in DEFAULT_NEWS if item.get("category") == "政策"])

        for item in default_candidates:
            if len(selected) >= top_n:
                break
            title_key = re.sub(r"\s+", " ", str(item.get("title", "")).lower()).strip()
            if not title_key or title_key in selected_titles:
                continue
            selected_titles.add(title_key)
            category = str(item.get("category", "行业热点"))
            selected.append(
                {
                    **item,
                    "score": max(int(item.get("score", 0) or 0), 48),
                    "matched": [category],
                    "source": "内置行业样本",
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
        top_action = str(top_news.get("action_text") or get_action(top_news.get("category", "政策")))
        actions.append(
            {
                "time": "今天",
                "priority": "中" if top_news.get("score", 0) < 70 else "高",
                "title": f"商机动作：{top_action}",
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


def _reprioritize_actions(actions: list[dict], seed: int) -> list[dict]:
    if not actions:
        return []

    level_map = {"低": 1, "中": 2, "高": 3}
    reverse_map = {1: "低", 2: "中", 3: "高"}
    updated: list[dict] = []

    for idx, action in enumerate(actions):
        action_copy = {**action}
        title = str(action_copy.get("title", ""))
        base_level = level_map.get(str(action_copy.get("priority", "中")), 2)

        # 仅在刷新智能目标时做轻量重排，优先级变化幅度限制在 +/-1。
        drift = ((seed + idx * 17 + sum(ord(ch) for ch in title[:6])) % 3) - 1
        new_level = max(1, min(3, base_level + drift))
        action_copy["priority"] = reverse_map[new_level]

        reason = str(action_copy.get("reason", "")).strip()
        if drift != 0 and reason:
            action_copy["reason"] = reason + " 已根据最新目标节奏重排优先级。"
        updated.append(action_copy)

    updated.sort(key=lambda item: (priority_weight(item.get("priority", "低")), item.get("time", "99:99")))
    return updated


def _attach_news_actions(news_items: list[dict], seed: int = 0) -> list[dict]:
    enriched: list[dict] = []
    for idx, item in enumerate(news_items):
        item_copy = {**item}
        if not str(item_copy.get("action_text", "")).strip():
            category = str(item_copy.get("category", "政策"))
            templates = ACTION_TEMPLATES.get(category) or ACTION_TEMPLATES.get("政策", [])
            if templates:
                picker = random.Random(seed + idx * 31 + sum(ord(ch) for ch in str(item_copy.get("title", ""))[:12]))
                item_copy["action_text"] = templates[picker.randrange(len(templates))]
            else:
                item_copy["action_text"] = get_action(category)
        enriched.append(item_copy)
    return enriched


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


def render_hero(boss: dict, score: int, level: str, today_str: str, city_display: str, goal_hint: str) -> None:
    hero_html = block_html(
        f"""
        <section class="hero">
          <div class="hero-grid">
            <div>
                            <div class="hero-title">今日商机指数仪表盘</div>
                            <div class="hero-sub">{html.escape(today_str)} ｜ 为 {html.escape(boss['name'])} 定制。</div>
              <div class="hero-chip-row">
                <span class="hero-chip">{html.escape(boss['industry'])}</span>
                                <span class="hero-chip">城市：{html.escape(city_display)}</span>
                                <span class="hero-chip">目标：{html.escape(goal_hint)}</span>
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
            <div class="kpi-box"><div class="kpi-label">可执行活动</div><div class="kpi-value"><span class="count" data-target="{event_count}">0</span><span class="kpi-suffix">个</span></div></div>
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
    st.markdown("<div class='split-title'>今天该做什么</div>", unsafe_allow_html=True)
    st.markdown("<div class='split-desc'>先执行最能推进目标的动作，确保一天有结果，而不是只有忙碌感。</div>", unsafe_allow_html=True)

    if not actions:
        st.info("当前没有可执行动作，建议先补充今日热点或切换老板画像。")
        return

    action_payload = [
        {
            "time": str(item.get("time", "今天")),
            "priority": str(item.get("priority", "中")),
            "type": str(item.get("type", "")),
            "title": str(item.get("title", "执行重点任务")),
            "reason": str(item.get("reason", "围绕今日目标推进。")),
        }
        for item in actions
    ]

    html_block = f"""
    <style>
        .gesture-tip {{
            color:#667085;
            font-size:12px;
            margin: 0 0 8px 2px;
        }}
        .gesture-wrap {{
            position: relative;
            padding-left: 1.12rem;
        }}
        .gesture-wrap::before {{
            content:"";
            position:absolute;
            left:0.23rem;
            top:0.2rem;
            bottom:0.2rem;
            width:2px;
            background:linear-gradient(180deg, rgba(15,63,121,0.4), rgba(31,159,152,0.32));
        }}
        .gesture-item {{
            position: relative;
            margin-bottom: 10px;
            background: #ffffff;
            border: 1px solid rgba(15,63,121,0.1);
            border-radius: 16px;
            padding: 10px 12px;
            box-shadow: 0 10px 24px rgba(15, 63, 121, 0.07);
            user-select:none;
            touch-action: pan-y;
        }}
        .gesture-item::before {{
            content:"";
            position:absolute;
            left:-1.03rem;
            top:0.84rem;
            width:11px;
            height:11px;
            border-radius:50%;
            border:2px solid #0f3f79;
            background:#fff;
            box-shadow:0 0 0 3px rgba(15,63,121,0.1);
        }}
        .gesture-top {{
            display:flex;
            justify-content:space-between;
            gap:8px;
            align-items:center;
            margin-bottom:4px;
        }}
        .gesture-meta-left {{
            display:flex;
            align-items:center;
            gap:6px;
            min-width:0;
        }}
        .gesture-time {{
            color:#0f3f79;
            font-weight:700;
            font-size:15px;
        }}
        .gesture-type {{
            display:inline-flex;
            align-items:center;
            padding:1px 6px;
            border-radius:999px;
            font-size:11px;
            font-weight:700;
            color:#155e75;
            background:rgba(21, 94, 117, 0.1);
            border:1px solid rgba(21, 94, 117, 0.2);
        }}
        .gesture-title {{
            color:#1f2937;
            font-weight:700;
            margin-bottom:3px;
        }}
        .gesture-note {{
            color:#6e6e73;
            font-size:13px;
            line-height:1.45;
        }}
        .gesture-pri {{
            border-radius:999px;
            font-size:12px;
            font-weight:700;
            padding:2px 8px;
            cursor:pointer;
            background:#fff;
        }}
        .p-high {{ color:#b42318; background:#ffe6e2; border:1px solid #ffc3bb; }}
        .p-mid {{ color:#8d5f10; background:#fff4dd; border:1px solid #f4deb0; }}
        .p-low {{ color:#0e766f; background:#e5f8f4; border:1px solid #bdece3; }}
        .gesture-hint {{
            color:#0f6d67;
            font-size:12px;
            margin-top:2px;
        }}
    </style>
    <div class="gesture-tip">手势操作：右滑新增日程（可填时间与事项），左滑删除日程，点击“高/中/低优先级”切换优先级。</div>
    <div id="gesture-timeline" class="gesture-wrap"></div>
    <div id="gesture-hint" class="gesture-hint"></div>
    <script>
        const root = document.getElementById('gesture-timeline');
        const hint = document.getElementById('gesture-hint');
        let items = {json.dumps(action_payload, ensure_ascii=False)};

        const priClass = (p) => p === '高' ? 'p-high' : (p === '低' ? 'p-low' : 'p-mid');
        const esc = (s) => String(s || '').replace(/[&<>"']/g, (m) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]));
        const typeRules = [
            {{ type: '截止日', keywords: ['截止', 'ddl', '到期', '交付', '报名截止', '申报截止', '递交'] }},
            {{ type: '活动', keywords: ['活动', '展会', '会展', '论坛', '峰会', '路演', '沙龙', '大会'] }},
            {{ type: '沟通', keywords: ['联系', '沟通', '拜访', '约见', '电话', '微信', '跟进', '对接'] }},
            {{ type: '材料', keywords: ['材料', '文案', '方案', '报价', '合同', '清单', 'ppt', '计划书'] }},
            {{ type: '复盘', keywords: ['复盘', '测算', '分析', '报表', '预算', '现金流', '评估'] }},
        ];

        function showHint(text) {{
            hint.textContent = text;
            setTimeout(() => {{
                if (hint.textContent === text) hint.textContent = '';
            }}, 1800);
        }}

        function cyclePriority(current) {{
            if (current === '高') return '中';
            if (current === '中') return '低';
            return '高';
        }}

        function priorityRank(level) {{
            if (level === '高') return 0;
            if (level === '中') return 1;
            if (level === '低') return 2;
            return 3;
        }}

        function parseTimeRank(raw) {{
            const text = String(raw || '').trim();
            const hm = text.match(/([01]?[0-9]|2[0-3]):([0-5][0-9])/);
            if (hm) {{
                return Number(hm[1]) * 60 + Number(hm[2]);
            }}
            if (text.includes('今天')) return 24 * 60;
            if (text.includes('明天')) return 48 * 60;
            if (text.includes('待确认')) return 72 * 60;
            return 60 * 60;
        }}

        function reorderItemsByPriority() {{
            items = items
                .map((item, idx) => ({{ ...item, __idx: idx }}))
                .sort((a, b) => {{
                    const priDiff = priorityRank(a.priority) - priorityRank(b.priority);
                    if (priDiff !== 0) return priDiff;

                    const timeDiff = parseTimeRank(a.time) - parseTimeRank(b.time);
                    if (timeDiff !== 0) return timeDiff;

                    return a.__idx - b.__idx;
                }})
                .map((item) => {{
                    const {{ __idx, ...rest }} = item;
                    return rest;
                }});
        }}

        function normalizeTimeInput(raw) {{
            const text = String(raw || '').trim();
            if (!text) return '今天';

            const hm = text.match(/^([01]?[0-9]|2[0-3]):([0-5][0-9])$/);
            if (hm) return `${{hm[1].padStart(2, '0')}}:${{hm[2]}}`;

            return text.slice(0, 18);
        }}

        function inferScheduleType(text) {{
            const content = String(text || '').toLowerCase();
            for (const rule of typeRules) {{
                if (rule.keywords.some((kw) => content.includes(kw.toLowerCase()))) {{
                    return rule.type;
                }}
            }}
            return '推进';
        }}

        function inferPriorityByType(taskType) {{
            if (taskType === '截止日') return '高';
            if (taskType === '材料') return '高';
            if (taskType === '活动') return '中';
            if (taskType === '沟通') return '中';
            if (taskType === '复盘') return '中';
            return '中';
        }}

        function buildReasonByType(taskType) {{
            if (taskType === '截止日') return '该事项属于时间敏感任务，建议先锁定完成节点。';
            if (taskType === '活动') return '该事项属于机会触达动作，建议明确对象并安排会后跟进。';
            if (taskType === '沟通') return '该事项属于关系推进动作，建议先定义沟通目标与下一步承诺。';
            if (taskType === '材料') return '该事项属于成交准备动作，建议同步整理资料与关键数字。';
            if (taskType === '复盘') return '该事项属于数据校准动作，建议输出结论并回写到明日计划。';
            return '该事项已加入今日清单，建议定义可验收结果。';
        }}

        function estimateFrameHeight() {{
            const base = 96;
            const perItem = 102;
            const minHeight = 210;
            const maxHeight = 1800;
            return Math.max(minHeight, Math.min(maxHeight, base + Math.max(1, items.length) * perItem));
        }}

        function syncFrameHeight() {{
            const target = estimateFrameHeight();
            try {{
                window.parent.postMessage(
                    {{ isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: target }},
                    '*'
                );
            }} catch (e) {{}}

            try {{
                if (window.frameElement) {{
                    window.frameElement.style.height = `${{target}}px`;
                }}
            }} catch (e) {{}}
        }}

        function askForNewSchedule(baseTime) {{
            const timeText = window.prompt('新增日程时间（例如 09:30 / 今天下午 / 明天 10:00）', baseTime || '今天');
            if (timeText === null) return null;

            const taskText = window.prompt('新增事项（例如 跟进张总确认联合活动）', '');
            if (taskText === null) return null;

            const task = String(taskText || '').trim();
            if (!task) {{
                showHint('事项不能为空，已取消新增');
                return null;
            }}

            return {{
                time: normalizeTimeInput(timeText),
                task,
            }};
        }}

        function render() {{
            reorderItemsByPriority();
            root.innerHTML = '';
            items.forEach((item, idx) => {{
                const itemType = item.type || inferScheduleType(`${{item.title || ''}} ${{item.reason || ''}}`);
                const card = document.createElement('div');
                card.className = 'gesture-item';
                card.innerHTML = `
                    <div class="gesture-top">
                        <div class="gesture-meta-left">
                            <span class="gesture-time">${{esc(item.time)}}</span>
                            <span class="gesture-type">${{esc(itemType)}}</span>
                        </div>
                        <button type="button" class="gesture-pri ${{priClass(item.priority)}}" title="点击切换优先级">${{esc(item.priority)}}优先级</button>
                    </div>
                    <div class="gesture-title">${{esc(item.title)}}</div>
                    <div class="gesture-note">${{esc(item.reason)}}</div>
                `;

                const priorityBadge = card.querySelector('.gesture-pri');
                if (priorityBadge) {{
                    priorityBadge.addEventListener('click', (event) => {{
                        event.preventDefault();
                        event.stopPropagation();
                        items[idx].priority = cyclePriority(items[idx].priority || '中');
                        reorderItemsByPriority();
                        render();
                        showHint('已切换优先级');
                    }});
                }}

                let startX = 0;

                card.addEventListener('touchstart', (e) => {{
                    startX = e.touches[0].clientX;
                }}, {{passive:true}});

                card.addEventListener('touchend', (e) => {{
                    const endX = (e.changedTouches && e.changedTouches[0]) ? e.changedTouches[0].clientX : startX;
                    const deltaX = endX - startX;

                    if (deltaX > 72) {{
                        const draft = askForNewSchedule(items[idx].time || '今天');
                        if (!draft) {{
                            showHint('已取消新增');
                            return;
                        }}

                        const taskType = inferScheduleType(draft.task);
                        const newItem = {{
                            time: draft.time,
                            priority: inferPriorityByType(taskType),
                            type: taskType,
                            title: `${{taskType}}：${{draft.task}}`,
                            reason: buildReasonByType(taskType),
                        }};
                        items.splice(idx + 1, 0, newItem);
                        reorderItemsByPriority();
                        render();
                        showHint(`已新增日程（${{taskType}}）`);
                    }} else if (deltaX < -72) {{
                        if (items.length > 1) {{
                            items.splice(idx, 1);
                            reorderItemsByPriority();
                            render();
                            showHint('已左滑删除日程');
                        }} else {{
                            showHint('至少保留1条日程');
                        }}
                    }}
                }}, {{passive:true}});

                root.appendChild(card);
            }});

            syncFrameHeight();
        }}

        window.addEventListener('resize', () => syncFrameHeight());
        render();
    </script>
    """
    height = max(210, min(1800, 96 + max(1, len(actions)) * 102))
    components.html(html_block, height=height, scrolling=False)


def _safe_target_city_name(event: dict) -> str:
    return str(event.get("event_city") or event.get("location") or "目的地").strip() or "目的地"


def _canonical_city_name(city_text: str) -> str:
    city = str(city_text or "").strip()
    if not city:
        return ""

    english_key = re.sub(r"[^a-z]", "", city.lower())
    if english_key in EN_CITY_TO_CN:
        return EN_CITY_TO_CN[english_key]

    if city in MAJOR_CITY_COORDS:
        return city
    if city in MAJOR_CITY_ALIASES:
        return MAJOR_CITY_ALIASES[city]

    for alias, canonical in MAJOR_CITY_ALIASES.items():
        if alias in city:
            return canonical

    for canonical in MAJOR_CITY_COORDS:
        if canonical in city:
            return canonical

    if city.endswith("市") and city[:-1] in MAJOR_CITY_COORDS:
        return city[:-1]

    for key, value in EN_CITY_TO_CN.items():
        if key in english_key:
            return value

    return city


def _guess_train_date(event: dict) -> str:
    raw_time = str(event.get("time", "")).strip()
    now = datetime.now()

    ymd_match = re.search(r"(20\d{2})[年\-/.](\d{1,2})[月\-/.](\d{1,2})", raw_time)
    if ymd_match:
        try:
            dt = datetime(int(ymd_match.group(1)), int(ymd_match.group(2)), int(ymd_match.group(3)))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    md_match = re.search(r"(\d{1,2})[月\-/.](\d{1,2})", raw_time)
    if md_match:
        month = int(md_match.group(1))
        day = int(md_match.group(2))
        try:
            dt = datetime(now.year, month, day)
            if dt.date() < now.date():
                dt = datetime(now.year + 1, month, day)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    return now.strftime("%Y-%m-%d")


def _build_12306_ticket_url(origin_city: str, target_city: str, event: dict) -> str:
    from_city = _canonical_city_name(origin_city) or "北京"
    to_city = _canonical_city_name(target_city) or "上海"
    from_code = CITY_12306_STATION_CODES.get(from_city, "")
    to_code = CITY_12306_STATION_CODES.get(to_city, "")

    fs = f"{from_city},{from_code}" if from_code else from_city
    ts = f"{to_city},{to_code}" if to_code else to_city
    date_str = _guess_train_date(event)

    return (
        "https://kyfw.12306.cn/otn/leftTicket/init"
        f"?linktypeid=dc&fs={quote_plus(fs)}&ts={quote_plus(ts)}&date={quote_plus(date_str)}&flag=N,N,Y"
    )


def _build_travel_entries(event: dict, geo_profile: dict | None = None) -> list[dict]:
    profile = geo_profile or {}
    origin_city = str(profile.get("city") or profile.get("nearest_major_city") or "出发地")
    target_city = _safe_target_city_name(event)
    distance_km = float(event.get("distance_km", 0) or 0)
    mode = str(event.get("travel_mode", ""))
    is_online = str(event.get("format", "")) == "线上" or "线上" in str(event.get("location", ""))

    if is_online:
        return []

    entries: list[dict] = []

    if "高铁" in mode or "城际" in mode or (30 < distance_km <= 320):
        entries.append(
            {
                "label": "高铁买票",
                "url": _build_12306_ticket_url(origin_city, target_city, event),
            }
        )

    if distance_km <= 60:
        entries.append(
            {
                "label": "打车入口",
                "url": f"https://uri.amap.com/navigation?mode=car&from={quote_plus(origin_city)}&to={quote_plus(target_city)}&src=BizAdvisor",
            }
        )
    elif distance_km <= 260:
        entries.append(
            {
                "label": "城际打车入口",
                "url": f"https://uri.amap.com/navigation?mode=car&from={quote_plus(origin_city)}&to={quote_plus(target_city)}&src=BizAdvisor",
            }
        )
    else:
        entries.append(
            {
                "label": "航班比价入口",
                "url": "https://flights.ctrip.com/",
            }
        )

    if distance_km > 0:
        entries.append(
            {
                "label": "公交/地铁入口",
                "url": f"https://uri.amap.com/navigation?mode=bus&from={quote_plus(origin_city)}&to={quote_plus(target_city)}&src=BizAdvisor",
            }
        )

    return entries[:4]


def _event_detail_url(event: dict) -> str:
    event_url = str(event.get("url", "")).strip()
    if event_url:
        return event_url

    title = _normalize_event_text(str(event.get("title", "活动详情")), max_len=72)
    location = _normalize_event_text(str(event.get("location", "")), max_len=32)
    query = " ".join(part for part in [title, location, "活动", "报名"] if part)
    return f"https://www.baidu.com/s?wd={quote_plus(query)}"


def _news_detail_url(news: dict) -> str:
    category = _normalize_event_text(str(news.get("category", "政策")), max_len=16)
    raw_link = str(news.get("link") or news.get("url") or "").strip()
    if raw_link:
        normalized = _normalize_url_with_base(raw_link)
        if normalized:
            if category != "政策" or _looks_like_policy_detail_url(normalized):
                return normalized

    source_name = str(news.get("source", "")).strip()
    if source_name and source_name in SOURCE_HOME_URL_MAP:
        return SOURCE_HOME_URL_MAP[source_name]

    if category == "政策":
        return "https://www.gov.cn/zhengce/"
    if category == "AI科技":
        return "https://www.36kr.com/"
    if category == "金融":
        return "https://finance.sina.com.cn/"
    return "https://www.xinhuanet.com/"


def _to_html_multiline(text: str) -> str:
    return html.escape(str(text or "")).replace("\n", "<br>")


def _build_policy_action_texts(news: dict) -> dict:
    title = _normalize_event_text(str(news.get("title", "相关政策")), max_len=56)
    category = str(news.get("category", "政策")).strip() or "政策"
    matched_terms = [str(term).strip() for term in news.get("matched", []) if str(term).strip()]
    matched = "、".join(matched_terms[:2]) or category
    focus = matched_terms[0] if matched_terms else matched

    day_seed = int(datetime.now().strftime("%Y%m%d"))
    seed = day_seed + sum(ord(ch) for ch in f"{title}|{category}|{matched}")
    rng = random.Random(seed)

    summary_templates = [
        "政策细则速读：{title}\n重点看三件事：{matched}相关资格边界、材料清单、时间窗口。\n建议动作：今天先做资格自测，明天补材料，后天锁申报节点。",
        "政策重点提炼：{title}\n和{matched}最相关的是门槛条件、补贴范围、申报顺序。\n建议动作：先判断能不能拿，再决定投入多少人力推进。",
        "这条政策建议别只看标题：{title}\n真正影响结果的是{matched}对应的细则条款与截止节奏。\n建议动作：先拉一页核对表，把是否可申报讲清楚。",
    ]
    summary = rng.choice(summary_templates).format(title=title, matched=matched)

    topic_tag = re.sub(r"\s+", "", focus)[:8] or category
    moments_openers = [
        "今天刷到一条{category}新动态：{title}",
        "刚看到一条值得圈内人留意的{category}信息：{title}",
        "这条{category}我建议别划走：{title}",
        "给正在做业务推进的朋友报个信：{title}",
    ]
    moments_insights = [
        "它和我们最近推进的{matched}方向高度相关，不是围观新闻，是真可能落地。",
        "这条不是“看看就过”，对{matched}的节奏和预算会有直接影响。",
        "如果你也在做{matched}，这条信息基本属于“早知道就少踩坑”的级别。",
        "和{matched}对得上，属于可以立刻拆解动作的政策，不是空泛口号。",
    ]
    moments_actions = [
        "我准备这周先把资格条件和材料清单跑一遍，能上就立刻排期。",
        "我会先做一版1页纸决策清单：能不能报、值不值得报、谁来报。",
        "接下来先做资格自测，再看补贴力度，最后决定是否投入申报。",
        "这周先把流程摸透，先跑最短路径，不在无效环节耗时间。",
    ]
    moments_hooks = [
        "你们更关心哪块：A资格门槛 B补贴额度 C申报流程？",
        "如果只能先做一步，你会选资格自测还是先约政策窗口？",
        "要不要我把关键条款做成一张图，方便你直接转给团队？",
        "你觉得这条对{matched}是短期机会，还是长期红利？",
    ]
    moments_closings = [
        "需要完整版清单的，留言“要模板”，我整理后发你。",
        "同频的朋友可以一起复盘，我把实操踩坑点同步出来。",
        "转给正在做{matched}的朋友，可能帮他少走一轮弯路。",
        "我会持续跟进实操结果，有新变化再同步。",
    ]
    hashtag_templates = [
        "#政策机会 #{category} #{topic_tag}",
        "#{category}动态 #老板决策 #{topic_tag}",
        "#实操复盘 #政策解读 #{topic_tag}",
    ]

    moments_lines = [
        rng.choice(moments_openers).format(category=category, title=title),
        rng.choice(moments_insights).format(matched=matched),
        rng.choice(moments_actions),
        rng.choice(moments_hooks).format(matched=matched),
        rng.choice(moments_closings).format(matched=matched),
    ]
    if rng.random() >= 0.35:
        moments_lines.append(rng.choice(hashtag_templates).format(category=category, topic_tag=topic_tag))
    moments_copy = "\n".join(moments_lines)

    friend_styles = [
        {
            "call": "姐妹",
            "insight": "这条和你在做的{matched}挺贴，不是热闹新闻，是真能省成本。",
            "ask": "你要不要把{focus}这块先拉个清单？我今晚帮你过一遍。",
        },
        {
            "call": "家人",
            "insight": "我看了下，这条对{matched}的节奏挺关键，越早看越占先手。",
            "ask": "你要是愿意，我给你做个“能不能报”的快速判断版。",
        },
        {
            "call": "兄弟",
            "insight": "和你最近推进的{matched}方向对得上，感觉有搞头。",
            "ask": "晚点我发你三条重点，你十分钟就能判断值不值。",
        },
        {
            "call": "搭子",
            "insight": "这条政策我觉得能直接影响{matched}这块，值得马上看。",
            "ask": "要不咱俩明天抽20分钟，把材料路径一起过一遍？",
        },
        {
            "call": "老板",
            "insight": "这条对{matched}挺关键，尤其是门槛和申报窗口这两块。",
            "ask": "我先给你做个简版判断：可申报/暂不申报/需补条件，你看这样行不行？",
        },
    ]
    friend_style = friend_styles[seed % len(friend_styles)]
    friend_note = (
        f"{friend_style['call']}，我刚看到个政策：{title}。\n"
        f"{friend_style['insight'].format(matched=matched)}\n"
        f"{friend_style['ask'].format(focus=focus)}"
    )

    finance_steps = (
        "融资材料整理步骤：\n"
        "1) 导出近3个月对公流水与回单；\n"
        "2) 整理近3个月营收/成本/净利润；\n"
        "3) 汇总应收应付与存货；\n"
        "4) 准备营业执照、纳税记录、主要合同；\n"
        "5) 打包成一份资料包并标注更新日期。"
    )

    cashflow_steps = (
        "现金流测算步骤：\n"
        "1) 先算当前月净现金流 = 现金流入 - 现金流出；\n"
        "2) 假设融资后新增月利息和还款额；\n"
        "3) 重算融资后月净现金流；\n"
        "4) 对比两者差值，得到现金流改善额度。"
    )

    finance_service = "需要客服协助整理？可留言：客服协助-融资材料-联系方式，我们会优先安排专员。"
    cashflow_service = "需要专员协助测算？可留言：客服协助-现金流测算-联系方式，我们会优先安排支持。"

    return {
        "summary": summary,
        "moments": moments_copy,
        "friend": friend_note,
        "finance_steps": finance_steps,
        "cashflow_steps": cashflow_steps,
        "finance_service": finance_service,
        "cashflow_service": cashflow_service,
    }


def _build_action_tool_items(action_text: str, news: dict) -> list[dict]:
    action = str(action_text or "")
    text_bank = _build_policy_action_texts(news)
    items: list[dict] = []
    seen_labels = set()

    def add_item(label: str, key: str) -> None:
        if label in seen_labels:
            return
        content = str(text_bank.get(key, "")).strip()
        if not content:
            return
        seen_labels.add(label)
        items.append({"label": label, "content": content})

    if any(marker in action for marker in ["政策", "细则", "申请条件", "申请资格", "补贴", "监管"]):
        add_item("政策细则摘要", "summary")

    if any(marker in action for marker in ["朋友圈", "小红书", "发一条", "内容", "分享"]):
        add_item("朋友圈文案", "moments")

    if any(marker in action for marker in ["朋友", "客户", "联系", "转发", "询问"]):
        add_item("好友通知文案", "friend")

    if any(marker in action for marker in ["流水", "融资", "信贷", "申请材料", "银行"]):
        add_item("融资材料整理步骤", "finance_steps")
        add_item("联系客服协助整理", "finance_service")

    if any(marker in action for marker in ["现金流", "改善多少", "测算", "计算"]):
        add_item("现金流测算步骤", "cashflow_steps")
        add_item("联系客服协助测算", "cashflow_service")

    if not items:
        add_item("政策细则摘要", "summary")
        add_item("朋友圈文案", "moments")

    return items


def render_why_cards(matched_events: list[dict], matched_news: list[dict], user_geo_profile: dict | None = None) -> None:
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
            source_detail = str(event.get("source_detail", "")).strip()
            source_line = f"<div class=\"wf-action\">来源：{html.escape(source_detail)}</div>" if source_detail else ""
            event_url = _event_detail_url(event)
            deadline_text = str(event.get("registration_deadline", "尽快确认报名")).strip() or "尽快确认报名"
            deadline_line = ""
            if deadline_text and deadline_text != "详见活动页":
                deadline_line = f"<div class=\"wf-action\">报名信息：{html.escape(deadline_text)}</div>"

            travel_entries = _build_travel_entries(event, geo_profile=user_geo_profile)
            travel_entry_html = ""
            if travel_entries:
                links = "".join(
                    f"<a class=\"wf-link\" href=\"{html.escape(item['url'])}\" target=\"_blank\" rel=\"noopener noreferrer\">{html.escape(item['label'])}</a>"
                    for item in travel_entries
                )
                travel_entry_html = f"<div class=\"wf-action wf-links\">出行入口：{links}</div>"

            event_cards.append(
                block_html(
                    f"""
                    <article class="wf-card" style="--d:{0.08 * idx:.2f}s;">
                                            <div class="wf-tag tag-event">什么值得做</div>
                                            <div class="wf-title">{html.escape(event.get('title', '商业活动'))}<a class="wf-detail-link" href="{html.escape(event_url)}" target="_blank" rel="noopener noreferrer">详见活动页</a></div>
                      <div class="wf-meta">{html.escape(event.get('time', '今日'))} ｜ {html.escape(event.get('format', '线上'))} ｜ {html.escape(event.get('location', '待确认'))}</div>
                      <div class="wf-reason">匹配理由：与你的「{html.escape(matched_kw)}」方向高度一致，且活动价值级别为 {html.escape(event.get('value', '中'))}。</div>
                                            {source_line}
                                            {deadline_line}
                      {travel_line}
                      {travel_entry_html}
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
            action = str(news.get("action_text") or get_action(news.get("category", "政策")))
            news_url = _news_detail_url(news)
            tool_items = _build_action_tool_items(action, news)
            tool_line = "".join(
                f'<details class="wf-ai-chip"><summary>{html.escape(item["label"])}</summary><div class="wf-ai-content">{_to_html_multiline(item["content"])}</div></details>'
                for item in tool_items
            )
            news_cards.append(
                block_html(
                    f"""
                    <article class="wf-card" style="--d:{0.08 * idx:.2f}s;">
                      <div class="wf-tag tag-news">热点商机</div>
                      <div class="wf-title">{html.escape(news.get('title', '行业热点'))}<a class="wf-detail-link" href="{html.escape(news_url)}" target="_blank" rel="noopener noreferrer">政策详情页</a></div>
                      <div class="wf-meta">相关度 {score} 分 ｜ 类别：{html.escape(news.get('category', '资讯'))} ｜ 关键词：{html.escape(matched_kw)}</div>
                      <div class="wf-reason">机会解释：该热点与当前业务路径有直接连接，具备短期转化可能。</div>
                      <div class="wf-action">{html.escape(action)}</div>
                      <div class="wf-ai-line">{tool_line}</div>
                    </article>
                    """
                )
            )

        st.markdown("<div class='waterfall'>" + "".join(news_cards) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='split-title'>为什么值得做</div>", unsafe_allow_html=True)
        st.caption("当前暂无高相关热点。")


def render_model_explainer(boss: dict, matched_news: list[dict], seed: int = 0) -> None:
    st.markdown("<div class='split-title'>商机推演</div>", unsafe_allow_html=True)
    st.markdown("<div class='split-desc'>给你一个联系人建议和商机推演，辅助判断推进节奏。</div>", unsafe_allow_html=True)

    if not matched_news:
        st.info("暂无可解释的高相关热点，模型推演暂不触发。")
        return

    pivot = 0
    if len(matched_news) > 1 and seed:
        pivot = abs(int(seed)) % len(matched_news)
    top_news = matched_news[pivot]
    network = get_network_suggestion(boss, top_news)
    relevance = "高相关" if top_news.get("score", 0) >= 60 else "中相关"
    miro = get_mirofish(top_news, relevance)

    if network:
        network_html = block_html(
            f"""
            <div class="model-card">
              <div class="model-title">人脉建议</div>
              <div class="model-body">建议联系：{html.escape(network['name'])}（{html.escape(network['role'])}）<br>
              联系理由：{html.escape(network['reason'])}</div>
            </div>
            """
        )
    else:
        network_html = block_html(
            """
            <div class="model-card">
              <div class="model-title">人脉建议</div>
              <div class="model-body">当前画像缺少可联系人脉，建议先补充 3-5 位关键联系人用于后续提醒。</div>
            </div>
            """
        )

    advice = "推进" if miro.get("advice") == "推进" else "观察"
    miro_html = block_html(
        f"""
        <div class="model-card">
          <div class="model-title">快速推演</div>
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
    )

    st.markdown(
        block_html(
            f"""
            <div class="model-grid">
              {network_html}
              {miro_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


inject_styles()

if "smart_goal_seed" not in st.session_state:
    st.session_state["smart_goal_seed"] = int(time.time())
if "live_context_cache" not in st.session_state:
    st.session_state["live_context_cache"] = {}
if "last_auto_goal" not in st.session_state:
    st.session_state["last_auto_goal"] = ""
if "recommendation_cache" not in st.session_state:
    st.session_state["recommendation_cache"] = {}

with st.sidebar:
    st.markdown("## 🧭 AI商业参谋")
    st.caption("浅色旗舰版 · Apple风格信息设计")
    st.divider()

    boss_options = {f"{b['name']} · {b['industry']}": b for b in BOSSES}
    selected_label = st.selectbox("选择老板画像", list(boss_options.keys()))
    selected_boss_base = boss_options[selected_label]

    manual_city_input = st.text_input(
        "城市（IP识别或手动输入）",
        value="",
        placeholder="留空则优先使用IP识别",
    )

    goal_input_mode = st.selectbox("目标来源", ["智能推荐筛选", "手动输入"], index=0)
    goal_style_mode = st.selectbox(
        "目标风格",
        ["平衡（推荐）", "稳健落地", "高势能冲刺"],
        index=0,
        disabled=(goal_input_mode == "手动输入"),
    )
    goal_preference_input = st.text_input(
        "目标偏好（可选）",
        value="",
        placeholder="例如：高客单、短周期、可公开案例",
    )
    manual_goal_input = ""
    goal_preview = st.empty()
    if goal_input_mode == "手动输入":
        manual_goal_input = st.text_input(
            "手动目标",
            value="",
            placeholder="例如：拓展新能源/科技客户，建立AI时代差异化",
        )
        st.caption("手动输入时，目标风格与偏好不参与生成。")
    else:
        st.caption("目标：可以手动输入或智能推荐筛选")
    refresh_goal = st.button("刷新智能目标", use_container_width=True)
    if refresh_goal:
        st.session_state["smart_goal_seed"] = int(st.session_state.get("smart_goal_seed", 0)) + 17

    selected_boss = dict(selected_boss_base)
    if goal_preference_input.strip() and goal_input_mode != "手动输入":
        selected_boss["goal_preference"] = goal_preference_input.strip()
    if goal_input_mode == "手动输入" and manual_goal_input.strip():
        selected_boss["current_goal"] = manual_goal_input.strip()

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
preferred_fetch_city = _canonical_city_name(manual_city_input.strip()) or _canonical_city_name(str(selected_boss_base.get("city", "")).strip())
if refresh:
    get_realtime_feeds.clear()
    st.toast("已手动刷新实时数据", icon="🔄")

live_cache = st.session_state.get("live_context_cache") or {}
cached_bucket = int(live_cache.get("refresh_bucket", -1)) if isinstance(live_cache, dict) else -1
cached_pref_city = _canonical_city_name(str(live_cache.get("preferred_fetch_city", ""))) if isinstance(live_cache, dict) else ""
can_reuse_live_context = bool(
    refresh_goal and not refresh and cached_bucket == refresh_bucket and cached_pref_city == preferred_fetch_city
)

if can_reuse_live_context:
    live_news = [{**item} for item in (live_cache.get("live_news") or [])]
    live_events = [{**item} for item in (live_cache.get("live_events") or [])]
    live_events_raw = [{**item} for item in (live_cache.get("live_events_raw") or live_events)]
    live_updated_at = str(live_cache.get("live_updated_at", ""))
    live_warnings = list(live_cache.get("live_warnings") or [])
    user_geo_profile = dict(live_cache.get("user_geo_profile") or {"enabled": False})
    st.toast("已快速刷新智能目标（复用当前实时数据）", icon="⚡")
else:
    live_news_raw, live_events_raw, live_updated_at, live_warnings_raw = get_realtime_feeds(
        refresh_bucket,
        preferred_city=preferred_fetch_city,
    )
    live_warnings = list(live_warnings_raw)

    live_events, user_geo_profile, geo_warnings = apply_ip_proximity_filter(
        live_events_raw,
        max_travel_hours=MAX_TRAVEL_HOURS,
        preferred_city=preferred_fetch_city,
    )
    if geo_warnings:
        live_warnings.extend(geo_warnings)

    live_news = [{**item} for item in live_news_raw]
    st.session_state["live_context_cache"] = {
        "refresh_bucket": refresh_bucket,
        "live_news": [{**item} for item in live_news],
        "live_events": [{**item} for item in live_events],
        "live_events_raw": [{**item} for item in live_events_raw],
        "live_updated_at": live_updated_at,
        "live_warnings": list(live_warnings),
        "user_geo_profile": dict(user_geo_profile),
        "preferred_fetch_city": preferred_fetch_city,
    }

if user_geo_profile.get("enabled"):
    city = _canonical_city_name(user_geo_profile.get("anchor_city") or user_geo_profile.get("city") or user_geo_profile.get("nearest_major_city") or "") or "未知城市"
    region = user_geo_profile.get("region", "")
    if user_geo_profile.get("anchor_mode") == "manual_city":
        ip_city = _canonical_city_name(str(user_geo_profile.get("ip_city", "")))
        ip_note = f"；IP参考：{ip_city}" if ip_city else ""
        geo_caption.caption(f"地址过滤：按{city}启用1-2小时硬过滤{ip_note}")
    else:
        geo_caption.caption(f"IP定位：{city}{(' · ' + region) if region else ''}（已启用1-2小时硬过滤）")
    scope_cities = user_geo_profile.get("scope_cities", [])
    if scope_cities:
        scope_caption.caption("可达大城市：" + "、".join(scope_cities[:6]))
    else:
        scope_caption.caption("可达大城市：暂无（仅保留线上活动）")
else:
    if _canonical_city_name(manual_city_input.strip()):
        geo_caption.caption("地址过滤：手动城市暂不在可计算范围，已回退为全量活动")
    else:
        geo_caption.caption("IP定位：未识别（暂未启用1-2小时硬过滤）")
    scope_caption.caption("")

manual_city = _canonical_city_name(manual_city_input.strip())
resolved_city = manual_city
if not resolved_city:
    resolved_city = _canonical_city_name(str(user_geo_profile.get("city") or user_geo_profile.get("nearest_major_city") or "").strip())
if resolved_city:
    selected_boss["city"] = resolved_city

hero_city_display = resolved_city or "IP识别或手动输入"
hero_goal_hint = _goal_headline_text(selected_boss.get("current_goal", ""))

mode_caption.caption(f"当前：实时联网模式（本土新闻/政策 + 本土活动；手动城市优先，未填则按IP进行路程过滤；每 {refresh_minutes} 分钟自动刷新）")
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
industry_event_pool = _build_industry_event_pool(selected_boss, live_events, top_n=max(12, len(live_events) or 12), min_secondary=2)
industry_news_pool = _build_industry_news_pool(selected_boss, all_news, top_n=max(24, len(all_news) or 24), min_secondary=2)

smart_goal_text, goal_seed_used = _generate_distinct_smart_goal(
    selected_boss,
    industry_news_pool or all_news,
    industry_event_pool or live_events,
    base_seed=int(st.session_state.get("smart_goal_seed", 0)),
    style_mode=goal_style_mode,
    previous_goal=str(st.session_state.get("last_auto_goal", "")),
    force_new=bool(refresh_goal),
)
if goal_input_mode == "手动输入" and manual_goal_input.strip():
    selected_boss["current_goal"] = manual_goal_input.strip()
else:
    selected_boss["current_goal"] = smart_goal_text
    st.session_state["smart_goal_seed"] = int(goal_seed_used)
    st.session_state["last_auto_goal"] = smart_goal_text
    goal_preview.markdown(_goal_preview_html(smart_goal_text), unsafe_allow_html=True)

hero_goal_hint = _goal_headline_text(selected_boss.get("current_goal", ""))

recommendation_key = json.dumps(
    {
        "boss": selected_label,
        "city": resolved_city,
        "custom_news": custom_news_text.strip(),
        "refresh_bucket": refresh_bucket,
        "goal_mode": goal_input_mode,
        "manual_goal": manual_goal_input.strip(),
    },
    ensure_ascii=False,
    sort_keys=True,
)

reco_cache = st.session_state.get("recommendation_cache") or {}
reuse_recommendation = bool(refresh_goal and not refresh and reco_cache.get("key") == recommendation_key)

if reuse_recommendation:
    matched_events = [{**item} for item in (reco_cache.get("matched_events") or [])]
    matched_news = [{**item} for item in (reco_cache.get("matched_news") or [])]
    matched_news = _attach_news_actions(matched_news, seed=int(st.session_state.get("smart_goal_seed", 0)))
    if matched_events or matched_news:
        st.toast("已极速刷新：仅重排任务优先级与商机推演", icon="⚡")
    else:
        reuse_recommendation = False

if not reuse_recommendation:
    matched_events = match_events_for_boss(selected_boss, industry_event_pool or live_events)
    matched_news = match_news_for_boss(selected_boss, industry_news_pool or all_news)

    if not matched_events and (industry_event_pool or live_events):
        matched_events = _fallback_event_candidates(selected_boss, industry_event_pool or live_events, top_n=3)
        live_warnings.append("活动严格匹配结果为空，已启用行业相关宽松推荐")

    if not matched_events:
        guaranteed_industry_events = _minimum_industry_consistent_events(
            selected_boss,
            industry_event_pool or live_events,
            top_n=1,
        )
        if guaranteed_industry_events:
            matched_events = guaranteed_industry_events
            live_warnings.append("已启用活动保底：至少展示1条行业一致活动（可接受稍远距离）")

    if not matched_news and (industry_news_pool or all_news):
        matched_news = _fallback_news_candidates(selected_boss, industry_news_pool or all_news, top_n=4)
        live_warnings.append("热点严格匹配结果为空，已启用行业相关宽松推荐")

    if not matched_events:
        backup_events = _build_industry_event_pool(selected_boss, TODAY_EVENTS, top_n=8, min_secondary=2)
        guaranteed_events, full_city_online = _minimum_online_city_events(
            selected_boss,
            industry_event_pool or live_events,
            backup_events or TODAY_EVENTS,
            top_n=1,
        )
        if guaranteed_events:
            matched_events = guaranteed_events
            if full_city_online:
                live_warnings.append("已启用最小展示保障：固定展示1条同城线上活动")
            else:
                live_warnings.append("已启用最小展示保障：强相关不足，已用次级相关线上活动补齐1条")

    if not matched_news:
        guaranteed_news = _minimum_local_policy_news(industry_news_pool + all_news + live_news + DEFAULT_NEWS, top_n=2, boss=selected_boss)
        if guaranteed_news:
            matched_news = guaranteed_news
            live_warnings.append("已启用最小展示保障：固定展示2条行业相关热点")

    exhibition_candidates = list(industry_event_pool or []) + list(live_events or [])
    matched_events, exhibition_injected = _ensure_exhibition_event_visibility(
        selected_boss,
        matched_events,
        exhibition_candidates,
        max_items=3,
    )
    if exhibition_injected:
        live_warnings.append("已补充1条会展中心官网活动，便于直接核验官方排期")

    matched_news = _attach_news_actions(matched_news, seed=refresh_bucket + int(st.session_state.get("smart_goal_seed", 0)))
    st.session_state["recommendation_cache"] = {
        "key": recommendation_key,
        "matched_events": [{**item} for item in matched_events],
        "matched_news": [{**item} for item in matched_news],
    }

if live_warnings:
    warning_caption.caption("系统提示：" + "；".join(dict.fromkeys(live_warnings)))

schedule = selected_boss.get("today_schedule", [])

today_str = datetime.now().strftime("%Y年%m月%d日")
score, score_label = compute_opportunity_index(schedule, matched_events, matched_news)
actions = build_today_actions(selected_boss, matched_events, matched_news)
if refresh_goal and not refresh:
    actions = _reprioritize_actions(actions, seed=int(st.session_state.get("smart_goal_seed", 0)))

render_hero(selected_boss, score, score_label, today_str, hero_city_display, hero_goal_hint)

render_kpi_counter(
    schedule_count=len(actions),
    event_count=len(matched_events),
    news_count=len(matched_news),
    score=score,
)

render_timeline(actions)
render_why_cards(matched_events, matched_news, user_geo_profile=user_geo_profile)
model_seed = int(st.session_state.get("smart_goal_seed", 0)) if (refresh_goal and not refresh) else 0
render_model_explainer(selected_boss, matched_news, seed=model_seed)

st.markdown("<div class='footer-note'>AI商业参谋 版权所有 盗版必究</div>", unsafe_allow_html=True)
