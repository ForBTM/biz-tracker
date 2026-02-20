#!/usr/bin/env python3
"""
/biz/ Crypto Tracker
抓取 4chan /biz/ 板块，统计加密货币提及频率，生成 HTML 报告
用法：python biz_tracker.py
"""

import requests
import re
import json
from datetime import datetime
from collections import defaultdict
from html import escape

# ── 币种词典 ──────────────────────────────────────────────────────
COINS = {
    "BTC": "Bitcoin",       "ETH": "Ethereum",      "SOL": "Solana",
    "XRP": "Ripple",        "BNB": "BNB",            "ADA": "Cardano",
    "DOGE": "Dogecoin",     "AVAX": "Avalanche",     "DOT": "Polkadot",
    "MATIC": "Polygon",     "LINK": "Chainlink",     "UNI": "Uniswap",
    "ATOM": "Cosmos",       "LTC": "Litecoin",       "BCH": "Bitcoin Cash",
    "NEAR": "NEAR Protocol","ICP": "Internet Computer","VET": "VeChain",
    "FIL": "Filecoin",      "HBAR": "Hedera",        "ALGO": "Algorand",
    "XLM": "Stellar",       "ETC": "Ethereum Classic","SAND": "The Sandbox",
    "MANA": "Decentraland", "AXS": "Axie Infinity",  "THETA": "Theta",
    "EOS": "EOS",           "XTZ": "Tezos",          "FTM": "Fantom",
    "CAKE": "PancakeSwap",  "CRO": "Cronos",         "GRT": "The Graph",
    "ZEC": "Zcash",         "DASH": "Dash",           "XMR": "Monero",
    "SHIB": "Shiba Inu",    "PEPE": "Pepe",          "WIF": "dogwifhat",
    "BONK": "Bonk",         "FLOKI": "Floki",        "TRUMP": "TRUMP",
    "TRX": "TRON",          "SUI": "Sui",            "SEI": "Sei",
    "INJ": "Injective",     "ARB": "Arbitrum",       "OP": "Optimism",
    "TON": "Toncoin",       "APT": "Aptos",          "STX": "Stacks",
    "AAVE": "Aave",         "CRV": "Curve",          "MKR": "Maker",
    "SNX": "Synthetix",     "COMP": "Compound",      "YFI": "Yearn Finance",
    "SUSHI": "SushiSwap",   "WLD": "Worldcoin",      "FET": "Fetch.ai",
    "RENDER": "Render",     "TAO": "Bittensor",      "OCEAN": "Ocean Protocol",
    "JUP": "Jupiter",       "RAY": "Raydium",        "ORCA": "Orca",
    "BOME": "Book of Meme", "POPCAT": "Popcat",      "MEW": "Cat in a Dog World",
    "PENDLE": "Pendle",     "LDO": "Lido DAO",       "RPL": "Rocket Pool",
    "MOVE": "Movement",     "EIGEN": "EigenLayer",   "PYTH": "Pyth Network",
    "JTO": "Jito",          "NOT": "Notcoin",        "BLUR": "Blur",
    "IMX": "ImmutableX",
}

# 别名 → 标准 symbol
ALIASES = {
    "bitcoin": "BTC",    "satoshi": "BTC",     "sats": "BTC",
    "ethereum": "ETH",   "ether": "ETH",        "vitalik": "ETH",
    "solana": "SOL",     "ripple": "XRP",
    "dogecoin": "DOGE",  "shiba": "SHIB",       "shib": "SHIB",
    "pepe": "PEPE",      "cardano": "ADA",
    "polygon": "MATIC",  "avalanche": "AVAX",
    "chainlink": "LINK", "litecoin": "LTC",
    "monero": "XMR",     "tron": "TRX",
    "toncoin": "TON",    "trump": "TRUMP",
    "dogwifhat": "WIF",  "bonk": "BONK",
    "floki": "FLOKI",    "render": "RENDER",
    "bittensor": "TAO",  "worldcoin": "WLD",
    "arbitrum": "ARB",   "optimism": "OP",
    "injective": "INJ",  "jupiter": "JUP",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CryptoTracker/1.0)",
    "Accept": "application/json",
}

def extract_coins(text: str) -> list[str]:
    """从文本中提取所有提及的币种 symbol"""
    if not text:
        return []
    found = set()
    clean = re.sub(r'<[^>]+>', ' ', text)  # 去掉 HTML 标签

    # 别名匹配
    lower = clean.lower()
    for alias, sym in ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', lower):
            found.add(sym)

    # 大写 symbol 匹配（2-8个字母）
    for word in re.findall(r'\b[A-Z]{2,8}\b', clean):
        if word in COINS:
            found.add(word)

    return list(found)


def fetch_catalog() -> list[dict]:
    """抓取 /biz/ catalog"""
    print("📡 正在抓取 4chan /biz/ catalog...")
    url = "https://a.4cdn.org/biz/catalog.json"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    catalog = resp.json()
    threads = []
    for page in catalog:
        threads.extend(page.get("threads", []))
    print(f"   获取到 {len(threads)} 个帖子")
    return threads


def analyze(threads: list[dict]) -> tuple[dict, list[dict]]:
    """分析帖子，返回 (coin_counts, hot_threads)"""
    coin_counts = defaultdict(lambda: {"count": 0, "threads": []})
    hot_threads = []

    for t in threads:
        text = " ".join([
            t.get("sub", "") or "",
            t.get("com", "") or "",
        ])
        coins = extract_coins(text)
        for sym in coins:
            coin_counts[sym]["count"] += 1
            coin_counts[sym]["threads"].append(t.get("no"))

        if coins:
            hot_threads.append({
                "no": t.get("no"),
                "sub": t.get("sub") or (t.get("com") or "")[:80],
                "coins": coins,
                "replies": t.get("replies", 0),
            })

    hot_threads.sort(key=lambda x: x["replies"], reverse=True)
    return dict(coin_counts), hot_threads[:10]


def generate_html(coin_counts: dict, hot_threads: list, thread_count: int) -> str:
    """生成 HTML 报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sorted_coins = sorted(coin_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    total_mentions = sum(v["count"] for v in coin_counts.values())
    max_count = sorted_coins[0][1]["count"] if sorted_coins else 1
    top10 = sorted_coins[:10]

    # 生成排行榜行
    rows_html = ""
    for i, (sym, data) in enumerate(sorted_coins):
        count = data["count"]
        pct = count / total_mentions * 100 if total_mentions else 0
        bar_w = count / max_count * 100
        rank_labels = {0: "①", 1: "②", 2: "③"}
        rank_text = rank_labels.get(i, f"#{i+1}")
        rank_class = {0: "top1", 1: "top2", 2: "top3"}.get(i, "")
        full_name = COINS.get(sym, "")
        rows_html += f"""
        <div class="coin-row" style="animation-delay:{i*0.03}s">
          <div class="rank {rank_class}">{rank_text}</div>
          <div class="coin-name">
            <div>
              <div class="coin-symbol">{escape(sym)}</div>
              <div class="coin-full">{escape(full_name)}</div>
            </div>
          </div>
          <div class="coin-count">{count}</div>
          <div class="coin-bar-wrap">
            <div class="coin-bar-bg"><div class="coin-bar" style="width:{bar_w:.1f}%"></div></div>
          </div>
          <div class="coin-pct">{pct:.1f}%</div>
        </div>"""

    # 热度图
    heatmap_html = ""
    heat_colors = ["#00ff41","#00e838","#00d030","#00b828","#00a020",
                   "#008818","#007010","#005808","#004000","#002800"]
    hm_max = top10[0][1]["count"] if top10 else 1
    for i, (sym, data) in enumerate(top10):
        w = data["count"] / hm_max * 100
        color = heat_colors[min(i, len(heat_colors)-1)]
        heatmap_html += f"""
        <div class="hm-row">
          <div class="hm-label">{escape(sym)}</div>
          <div class="hm-bar">
            <div class="hm-fill" style="width:{w:.1f}%;background:{color};box-shadow:0 0 4px {color}40"></div>
          </div>
          <div class="hm-count">{data['count']}</div>
        </div>"""

    # 热帖列表
    threads_html = ""
    for t in hot_threads:
        tags = "".join(f'<span class="th-tag">{escape(c)}</span>' for c in t["coins"][:4])
        sub = escape(str(t["sub"])[:70])
        threads_html += f"""
        <div class="thread-item">
          <div class="th-coins">{tags}</div>
          <div class="th-sub">
            <a href="https://boards.4chan.org/biz/thread/{t['no']}" target="_blank">{sub}</a>
          </div>
          <div class="th-meta">{t['replies']} replies · #{t['no']}</div>
        </div>"""

    top_sym = sorted_coins[0][0] if sorted_coins else "—"
    top_cnt = sorted_coins[0][1]["count"] if sorted_coins else 0

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>/biz/ Crypto Tracker · {now}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Teko:wght@300;400;500&display=swap');
:root{{--bg:#0a0a0a;--panel:#111;--border:#1e1e1e;--border2:#2a2a2a;--green:#00ff41;--green2:#00cc33;--amber:#ffb000;--red:#ff3030;--text:#c8ffc8;--muted:#2a5a2a;--white:#e8ffe8;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--text);font-family:'Share Tech Mono',monospace;min-height:100vh;}}
body::before{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,65,0.015) 2px,rgba(0,255,65,0.015) 4px);pointer-events:none;z-index:9999;}}
body::after{{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,255,65,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,65,0.03) 1px,transparent 1px);background-size:32px 32px;pointer-events:none;z-index:0;}}
.wrap{{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:24px 20px 60px;}}
header{{border-bottom:1px solid var(--border2);padding-bottom:18px;margin-bottom:24px;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;}}
.logo{{font-family:'Teko',sans-serif;font-size:42px;font-weight:400;color:var(--green);line-height:1;letter-spacing:2px;text-shadow:0 0 20px rgba(0,255,65,0.5);}}
.logo span{{color:var(--amber);}}
.subtitle{{font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-top:4px;}}
.meta{{text-align:right;font-size:11px;color:var(--muted);line-height:1.8;}}
.meta strong{{color:var(--green);}}
.stats-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;}}
.sc{{background:var(--panel);border:1px solid var(--border);padding:14px;position:relative;overflow:hidden;}}
.sc::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:var(--green);opacity:.3;}}
.sl{{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:6px;}}
.sv{{font-family:'Teko',sans-serif;font-size:28px;color:var(--green);line-height:1;}}
.ss{{font-size:10px;color:var(--muted);margin-top:3px;}}
.sv.amber{{color:var(--amber);font-size:20px;}}
.main-layout{{display:grid;grid-template-columns:1fr 300px;gap:16px;}}
.board-header{{display:grid;grid-template-columns:40px 1fr 90px 80px 70px;padding:8px 14px;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--border2);margin-bottom:4px;}}
.coin-row{{display:grid;grid-template-columns:40px 1fr 90px 80px 70px;padding:10px 14px;border:1px solid transparent;transition:all .15s;animation:rowIn .3s ease both;}}
@keyframes rowIn{{from{{opacity:0;transform:translateX(-8px)}}to{{opacity:1;transform:translateX(0)}}}}
.coin-row:hover{{background:rgba(0,255,65,.03);border-color:var(--border);}}
.rank{{font-size:11px;color:var(--muted);display:flex;align-items:center;}}
.rank.top1{{color:var(--amber);text-shadow:0 0 8px rgba(255,176,0,.6);}}
.rank.top2{{color:#c0c0c0;}}.rank.top3{{color:#cd7f32;}}
.coin-name{{display:flex;align-items:center;gap:10px;}}
.coin-symbol{{font-family:'Teko',sans-serif;font-size:20px;color:var(--white);letter-spacing:1px;}}
.coin-full{{font-size:10px;color:var(--muted);margin-top:1px;}}
.coin-count{{font-family:'Teko',sans-serif;font-size:22px;color:var(--green);display:flex;align-items:center;text-shadow:0 0 8px rgba(0,255,65,.3);}}
.coin-bar-wrap{{display:flex;align-items:center;padding:0 8px;}}
.coin-bar-bg{{width:100%;height:4px;background:var(--border);border-radius:2px;overflow:hidden;}}
.coin-bar{{height:100%;background:linear-gradient(90deg,var(--green2),var(--green));border-radius:2px;box-shadow:0 0 6px rgba(0,255,65,.4);}}
.coin-pct{{font-size:11px;color:var(--muted);display:flex;align-items:center;justify-content:flex-end;}}
.sidebar{{display:flex;flex-direction:column;gap:14px;}}
.side-card{{background:var(--panel);border:1px solid var(--border);padding:16px;}}
.side-title{{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid var(--border);}}
.hm-row{{display:flex;align-items:center;gap:8px;margin-bottom:5px;}}
.hm-label{{font-size:10px;color:var(--muted);width:44px;text-align:right;flex-shrink:0;}}
.hm-bar{{flex:1;height:14px;background:var(--border);border-radius:1px;overflow:hidden;}}
.hm-fill{{height:100%;border-radius:1px;}}
.hm-count{{font-size:9px;color:var(--muted);width:28px;flex-shrink:0;}}
.thread-item{{padding:9px 0;border-bottom:1px solid var(--border);font-size:11px;line-height:1.5;}}
.thread-item:last-child{{border-bottom:none;}}
.th-coins{{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:4px;}}
.th-tag{{font-size:9px;padding:1px 6px;background:rgba(0,255,65,.07);border:1px solid rgba(0,255,65,.2);color:var(--green);letter-spacing:1px;}}
.th-sub a{{color:var(--text);text-decoration:none;}}
.th-sub a:hover{{color:var(--green);}}
.th-meta{{font-size:10px;color:var(--muted);margin-top:3px;}}
.footer{{margin-top:30px;padding-top:16px;border-top:1px solid var(--border);font-size:10px;color:var(--muted);text-align:center;letter-spacing:2px;}}
@media(max-width:800px){{.main-layout{{grid-template-columns:1fr;}}.stats-row{{grid-template-columns:repeat(2,1fr);}}.coin-row,.board-header{{grid-template-columns:36px 1fr 70px 60px;}}.coin-pct{{display:none;}}}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <div class="logo">/biz/<span>SCAN</span></div>
      <div class="subtitle">4chan /biz/ · 加密货币提及频率</div>
    </div>
    <div class="meta">
      生成时间：<strong>{now}</strong><br>
      数据来源：4chan /biz/ catalog<br>
      扫描帖子：<strong>{thread_count}</strong> 个
    </div>
  </header>

  <div class="stats-row">
    <div class="sc"><div class="sl">扫描帖子</div><div class="sv">{thread_count}</div><div class="ss">threads</div></div>
    <div class="sc"><div class="sl">识别币种</div><div class="sv">{len(coin_counts)}</div><div class="ss">unique coins</div></div>
    <div class="sc"><div class="sl">总提及次数</div><div class="sv">{total_mentions}</div><div class="ss">mentions</div></div>
    <div class="sc"><div class="sl">最热币种</div><div class="sv amber">{escape(top_sym)}</div><div class="ss">{top_cnt} mentions</div></div>
  </div>

  <div class="main-layout">
    <div class="leaderboard">
      <div class="board-header">
        <div>#</div><div>币种</div><div>提及数</div><div>分布</div><div>占比</div>
      </div>
      {rows_html}
    </div>
    <div class="sidebar">
      <div class="side-card">
        <div class="side-title">Top 10 热度图</div>
        <div class="heatmap">{heatmap_html}</div>
      </div>
      <div class="side-card">
        <div class="side-title">相关热帖（按回复数）</div>
        {threads_html}
      </div>
    </div>
  </div>

  <div class="footer">
    GENERATED BY /biz/ CRYPTO TRACKER · {now} · DATA FROM 4CHAN PUBLIC API
  </div>
</div>
</body>
</html>"""


def main():
    print("=" * 50)
    print("  /biz/ Crypto Tracker")
    print("=" * 50)

    try:
        threads = fetch_catalog()
        print("🔍 分析帖子...")
        coin_counts, hot_threads = analyze(threads)

        if not coin_counts:
            print("⚠ 未识别到任何币种提及")
            return

        # 打印排行榜到终端
        print(f"\n📊 识别到 {len(coin_counts)} 种币，共 {sum(v['count'] for v in coin_counts.values())} 次提及\n")
        print(f"{'排名':<6} {'符号':<8} {'全名':<22} {'提及数':>6}")
        print("-" * 46)
        sorted_coins = sorted(coin_counts.items(), key=lambda x: x[1]["count"], reverse=True)
        for i, (sym, data) in enumerate(sorted_coins[:20], 1):
            bar = "█" * min(data["count"], 30)
            print(f"  #{i:<4} {sym:<8} {COINS.get(sym,''):<22} {data['count']:>4}  {bar}")

        # 生成 HTML
        output_file = "index.html"
        html = generate_html(coin_counts, hot_threads, len(threads))
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"\n✅ 报告已生成：{output_file}")

    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误：{e}")
    except Exception as e:
        print(f"❌ 错误：{e}")
        raise


if __name__ == "__main__":
    main()
