"""
AI商业参谋 - 核心AI处理模块
使用 Claude API 为每位老板生成个性化商机早报
"""

import anthropic
import json


def generate_daily_report(client: anthropic.Anthropic, boss: dict, news_items: list[dict]) -> str:
    """
    为单个老板生成个性化商机早报。

    Args:
        client: Anthropic 客户端
        boss: 老板档案字典
        news_items: 今日热点新闻列表，每条包含 id/title/category

    Returns:
        格式化的商机早报字符串
    """
    news_text = "\n".join(
        f"[{n['id']}] {n['title']}（类别：{n.get('category', '未分类')}）"
        for n in news_items
    )

    contacts_text = "\n".join(
        f"- {c['name']}（{c['role']}）：{c['days_since_contact']}天未联系"
        for c in boss.get("contacts", [])
    )

    prompt = f"""你是"AI商业参谋"，专为中国老板提供精准商机情报。

## 老板档案
姓名：{boss['name']}，{boss['age']}岁
城市：{boss['city']}
行业：{boss['industry']}（{boss['company_size']}）
当前目标：{boss['current_goal']}
核心痛点：{' / '.join(boss['pain_points'])}
关注关键词：{' / '.join(boss['keywords'])}
忽略词：{' / '.join(boss['ignore_keywords'])}

## 人脉状态
{contacts_text if contacts_text else '暂无人脉记录'}

## 今日热点（共{len(news_items)}条）
{news_text}

## 你的任务
1. **过滤**：从上述热点中，选出与该老板业务高度相关的3-5条（忽略与忽略词相关的内容）
2. **评分**：每条给出相关度分数（0-100）和一句话理由
3. **行动建议**：每条热点给出1个具体可执行的行动（今天就能做的）
4. **人脉提醒**：结合热点，指出最应该联系的1位人脉，说明为什么现在联系最合适
5. **MiroFish快速推演**：对最高分热点做30秒推演：时间窗口、预估收益、主要风险

## 输出格式
使用以下固定格式输出（方便后续解析）：

📋 {boss['name']}的商机早报 · 今日

[相关热点]
🔴 [热点ID] 标题  相关度：XX分
→ 理由：一句话
→ 行动：今天具体做什么

（重复3-5条）

[人脉提醒]
👥 建议联系：姓名（角色）
→ 原因：为什么现在联系

[MiroFish推演]
🔮 最高价值商机：热点标题
→ 时间窗口：X个月
→ 预估收益：¥XX万 - ¥XX万
→ 主要风险：一句话
→ AI建议：推进 / 观察 / 暂不行动"""

    # 使用 claude-haiku-4-5 做批量处理（成本优化），用户可在此改为 claude-opus-4-6
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def generate_all_reports(
    client: anthropic.Anthropic,
    bosses: list[dict],
    news_items: list[dict],
    boss_ids: list[str] | None = None,
) -> dict[str, str]:
    """
    为多位老板批量生成早报。

    Args:
        client: Anthropic 客户端
        bosses: 老板档案列表
        news_items: 今日热点新闻
        boss_ids: 指定只处理哪些老板（None = 全部）

    Returns:
        {boss_name: report_text} 字典
    """
    results = {}

    target_bosses = bosses
    if boss_ids:
        target_bosses = [b for b in bosses if b["id"] in boss_ids]

    for i, boss in enumerate(target_bosses, 1):
        print(f"  [{i}/{len(target_bosses)}] 正在生成 {boss['name']} 的早报...", end="", flush=True)
        try:
            report = generate_daily_report(client, boss, news_items)
            results[boss["name"]] = report
            print(" ✓")
        except Exception as e:
            print(f" ✗ 错误: {e}")
            results[boss["name"]] = f"[生成失败: {e}]"

    return results


def save_reports(reports: dict[str, str], output_path: str) -> None:
    """保存所有早报到文件。"""
    from datetime import datetime

    today = datetime.now().strftime("%Y年%m月%d日")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# AI商业参谋 · 商机早报\n")
        f.write(f"# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("=" * 60 + "\n\n")

        for name, report in reports.items():
            f.write(report)
            f.write("\n\n" + "=" * 60 + "\n\n")

    print(f"\n所有早报已保存至：{output_path}")
