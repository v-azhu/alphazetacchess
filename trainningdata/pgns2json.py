#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pgns2json.py
把中国象棋 PGN 风格文件（ICCS 着法）转换为目标 JSON Lines 格式

用法:
    python pgns2json.py input.pgns output.json
"""

import re
import json
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional


def parse_pgn_content(content: str) -> List[Dict[str, Any]]:
    """解析整个文件，返回多盘棋列表"""
    # 按下一个 [Game 分割（兼容空行）
    games = re.split(r'(?=\n\[Game\s+"Chinese Chess"\])', content.strip())
    results = []
    for g in games:
        g = g.strip()
        if not g:
            continue
        parsed = parse_single_game(g)
        if parsed:
            results.append(parsed)
    return results


def parse_single_game(text: str) -> Optional[Dict[str, Any]]:
    """解析单盘棋"""
    # ---------- 1. 提取所有标签 ----------
    tags = {}
    for m in re.finditer(r'\[(\w+)\s+"([^"]*)"\]', text):
        tags[m.group(1)] = m.group(2)

    if not tags:
        return None

    # ---------- 2. 提取着法文本 ----------
    # 去掉所有标签后剩下的就是着法 + 结果
    moves_text = re.sub(r'\[.*?\]', '', text, flags=re.DOTALL).strip()
    # 去掉结尾的结果
    moves_text = re.sub(r'\s*(1-0|0-1|1/2-1/2|\*)\s*$', '', moves_text, flags=re.IGNORECASE)

    # ---------- 3. 解析 ICCS 着法 ----------
    # 匹配 C3-C4 或 c3-c4 这种格式
    move_re = re.compile(r'([A-Ia-i][0-9])\s*-\s*([A-Ia-i][0-9])', re.IGNORECASE)
    moves = move_re.findall(moves_text)
    iccs = ''.join(f'{a.lower()}{b.lower()}' for a, b in moves)

    # ---------- 4. 结果映射 ----------
    result_map = {
        '1-0': '1',
        '0-1': '0',
        '1/2-1/2': '2',
        '1/2': '2',
        '*': '2',
    }
    raw_result = tags.get('Result', '*').strip()
    result = result_map.get(raw_result, '2')

    # ---------- 5. 日期统一成 YYYYMMDD ----------
    date = tags.get('Date', '').replace('-', '').replace('.', '').replace('/', '')
    if len(date) >= 8 and date[:8].isdigit():
        date = date[:8]
    else:
        date = ''

    # ---------- 6. 棋手名字只保留人名 ----------
    def extract_name(full: str) -> str:
        if not full:
            return ''
        # "黑龙江 郭莉萍" → "郭莉萍"
        parts = full.strip().split()
        return parts[-1] if parts else full

    red_name = extract_name(tags.get('Red', ''))
    black_name = extract_name(tags.get('Black', ''))

    # ---------- 7. 构建 items ----------
    items = {
        "变例": "",
        "Type": "",                    # 完整对局一般为空或"全局"
        "权重": "0",                   # 没有来源时给 0
        "黑方单位": tags.get('BlackTeam', ''),
        "轮次": tags.get('Round', ''),
        "开局": tags.get('Opening', ''),
        "红方棋手": red_name,
        "黑方棋手": black_name,
        "红方单位": tags.get('RedTeam', ''),
        "比赛地点": tags.get('Site', '') if tags.get('Site', '') != '-' else '',
        "日期": date,
        "棋局结果": result,
        "比赛名称": tags.get('Event', ''),
        "Ecco": tags.get('ECO', tags.get('Ecco', '')),
    }

    # 可选：如果想记录步数
    if moves:
        items["步数"] = str(len(moves))

    # ---------- 8. 最终对象 ----------
    # 完整对局的 fen 在示例中几乎都是空字符串
    game = {
        "fen": "",                     # 完整对局通常为空
        "items": items,
        "iccs": iccs,
        "path": f"/qipu/{uuid.uuid4()}"
    }
    return game


def main():
    if len(sys.argv) != 3:
        print("用法: python pgns2json.py <input.pgns> <output.json>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"错误: 找不到输入文件 {input_path}")
        sys.exit(1)

    content = input_path.read_text(encoding='utf-8')
    games = parse_pgn_content(content)

    # 写出 JSON Lines（每行一个对象）
    with output_path.open('w', encoding='utf-8') as f:
        for g in games:
            f.write(json.dumps(g, ensure_ascii=False) + '\n')

    print(f"成功转换 {len(games)} 盘棋 → {output_path}")


if __name__ == '__main__':
    main()