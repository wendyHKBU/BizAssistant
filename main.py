"""
AI商业参谋 MVP
专为中国老板/一人公司/小企业主设计的AI决策伙伴

用法：
  python main.py --mock           # 免费模拟模式（不需要API Key）
  python main.py                  # 真实AI模式（需要API Key）
  python main.py --boss boss01 boss03 --mock   # 只模拟指定老板
  python main.py --list           # 列出所有老板

环境变量（真实AI模式需要）：
  ANTHROPIC_API_KEY               # 或在目录下创建 .env 文件
"""

import argparse
import os
import sys
import io
from datetime import datetime
from pathlib import Path

# 修复 Windows 终端中文+emoji编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ──────────────────────────────────────────────
# 今日热点新闻（每天更新这里）
# ──────────────────────────────────────────────
TODAY_NEWS = [
    {"id": "H01", "title": "国务院发布《数字经济促进高质量发展实施方案》", "category": "政策"},
    {"id": "H02", "title": "抖音电商宣布开放中小商家流量扶持计划，佣金降低30%", "category": "电商"},
    {"id": "H03", "title": "人民币汇率创近期新高，外贸企业成本压力上升", "category": "外汇"},
    {"id": "H04", "title": "DeepSeek新版本发布，企业AI应用成本降低60%", "category": "AI科技"},
    {"id": "H05", "title": "广交会春季展预注册开始，海外采购商同比增加30%", "category": "外贸"},
    {"id": "H06", "title": "教育部发布企业职业技能培训补贴新政，最高50万", "category": "政策"},
    {"id": "H07", "title": "新能源汽车2月销量同比增长45%，配件需求激增", "category": "新能源"},
    {"id": "H08", "title": "抖音直播整治违规行为，头部主播账号受限，中小卖家机会窗口", "category": "电商"},
    {"id": "H09", "title": "东南亚跨境电商市场规模突破1万亿，中国卖家占40%", "category": "跨境电商"},
    {"id": "H10", "title": "银行推出新型供应链金融产品，专为中小企业降低融资门槛", "category": "金融"},
    {"id": "H11", "title": "阿里云发布新一代企业AI助手，价格下调70%", "category": "AI科技"},
    {"id": "H12", "title": "餐饮行业复苏：一线城市客流量回升25%，商场招商积极", "category": "餐饮"},
    {"id": "H13", "title": "律师行业调查：60%律师开始使用AI辅助办案，效率提升3倍", "category": "法律科技"},
    {"id": "H14", "title": "设计行业报告：AI工具普及但创意价值仍依赖人工，报价可提升", "category": "设计"},
    {"id": "H15", "title": "广州制造业PMI连续3个月上升，订单回暖，配件需求明显", "category": "制造业"},
]


def load_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def list_bosses():
    from bosses import BOSSES
    print("\n当前系统中的10位AI老板：\n")
    for b in BOSSES:
        print(f"  {b['id']}  {b['name']}  |  {b['city']}  |  {b['industry']}")
    print()


def save_reports(reports: dict, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# AI商业参谋 · 商机早报\n")
        f.write(f"# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("=" * 60 + "\n\n")
        for name, report in reports.items():
            f.write(report)
            f.write("\n\n" + "=" * 60 + "\n\n")
    print(f"\n所有早报已保存至：{output_path}")


def run_mock(boss_ids: list | None, save: bool):
    """免费模拟模式——无需API Key。"""
    from bosses import BOSSES
    from mock_advisor import generate_all_mock_reports

    target = [b for b in BOSSES if not boss_ids or b["id"] in boss_ids]

    today_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    print(f"\n{'='*60}")
    print(f"  AI商业参谋 · 商机早报  {today_str}")
    print(f"  模式：模拟引擎（免费，无需API）")
    print(f"{'='*60}")
    print(f"  今日热点：{len(TODAY_NEWS)} 条  |  目标老板：{len(target)} 位\n")

    reports = generate_all_mock_reports(target, TODAY_NEWS)

    print(f"{'='*60}\n")
    for name, report in reports.items():
        print(report)
        print(f"\n{'─'*60}\n")

    if save:
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        filename = f"早报_模拟_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        save_reports(reports, str(output_dir / filename))


def run_ai(boss_ids: list | None, save: bool):
    """真实AI模式——调用Claude API。"""
    import anthropic
    from bosses import BOSSES
    from advisor import generate_all_reports

    api_key = load_api_key()
    if not api_key:
        print("错误：未找到 API Key，请创建 .env 文件或使用 --mock 模式")
        return

    client = anthropic.Anthropic(api_key=api_key)

    today_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    print(f"\n{'='*60}")
    print(f"  AI商业参谋 · 商机早报  {today_str}")
    print(f"  模式：Claude AI（真实智能分析）")
    print(f"{'='*60}\n")

    print("正在生成个性化早报...\n")
    reports = generate_all_reports(client, BOSSES, TODAY_NEWS, boss_ids)

    print(f"\n{'='*60}\n")
    for name, report in reports.items():
        print(report)
        print(f"\n{'─'*60}\n")

    if save:
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        filename = f"早报_AI_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        save_reports(reports, str(output_dir / filename))


def main():
    parser = argparse.ArgumentParser(
        description="AI商业参谋 - 每日商机早报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python main.py --mock                        # 免费模拟，全部10个老板
  python main.py --mock --boss boss01 boss06   # 只模拟王建国和赵敏
  python main.py                               # 真实AI模式（需要API Key）
  python main.py --list                        # 查看所有老板
        """,
    )
    parser.add_argument("--mock", action="store_true", help="免费模拟模式，无需API Key")
    parser.add_argument("--boss", nargs="+", metavar="BOSS_ID", help="指定老板ID")
    parser.add_argument("--list", action="store_true", help="列出所有老板")
    parser.add_argument("--no-save", action="store_true", help="不保存到文件")

    args = parser.parse_args()

    if args.list:
        list_bosses()
        return

    if args.mock:
        run_mock(boss_ids=args.boss, save=not args.no_save)
    else:
        run_ai(boss_ids=args.boss, save=not args.no_save)


if __name__ == "__main__":
    main()
