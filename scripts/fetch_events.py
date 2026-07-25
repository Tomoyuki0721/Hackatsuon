#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
気仙沼イベント情報収集スクリプト
毎週月曜日に GitHub Actions から実行される。
"""

import json
import os
import re
import smtplib
import sys
from datetime import date, datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urljoin

JST = timezone(timedelta(hours=9))
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
CONFIG_PATH = ROOT_DIR / "config" / "sites.json"
OUTPUT_PATH = ROOT_DIR / "data" / "events.json"
LOOKBACK_DAYS = 14   # 過去14日以内に投稿された記事を表示
LOOKAHEAD_DAYS = 60  # 未来60日以内のイベントも表示

# ── 依存ライブラリ（pip install requests beautifulsoup4 lxml feedparser python-dateutil）

try:
    import requests
    from bs4 import BeautifulSoup
    import feedparser
    from dateutil import parser as dateparser
except ImportError as e:
    print(f"[ERROR] 必要なライブラリが不足しています: {e}", file=sys.stderr)
    print("pip install requests beautifulsoup4 lxml feedparser python-dateutil", file=sys.stderr)
    sys.exit(1)


# ── 日付パーサー ──────────────────────────────────────────────

REIWA_BASE = 2018  # 令和元年 = 2019年


def parse_japanese_date(text: str) -> date | None:
    if not text:
        return None
    text = text.strip()

    # 令和X年M月D日
    m = re.search(r"令和\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", text)
    if m:
        y = REIWA_BASE + int(m.group(1))
        return date(y, int(m.group(2)), int(m.group(3)))

    # YYYY年M月D日
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # M月D日（曜日なし / 曜日あり）→ 今年 or 来年に補完
    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if m:
        mo, day = int(m.group(1)), int(m.group(2))
        today = date.today()
        try:
            d = date(today.year, mo, day)
            if d < today - timedelta(days=7):
                d = date(today.year + 1, mo, day)
            return d
        except ValueError:
            pass

    # YYYY/M/D または YYYY-M-D
    m = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # dateutil にフォールバック
    try:
        return dateparser.parse(text, fuzzy=True).date()
    except Exception:
        return None


# ── フェッチャー ─────────────────────────────────────────────

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; KesennumaEventsBot/1.0)"}


def fetch_rss(site: dict) -> list[dict]:
    events = []
    try:
        feed = feedparser.parse(site["url"])
        for entry in feed.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                from time import mktime
                published = date.fromtimestamp(mktime(entry.published_parsed))
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                from time import mktime
                published = date.fromtimestamp(mktime(entry.updated_parsed))

            summary = ""
            if hasattr(entry, "summary"):
                summary = BeautifulSoup(entry.summary, "lxml").get_text(" ", strip=True)[:200]

            events.append({
                "title": entry.get("title", "（タイトルなし）"),
                "date_start": published.isoformat() if published else None,
                "date_end": None,
                "description": summary,
                "url": entry.get("link", site["url"]),
                "source": site["name"],
            })
    except Exception as e:
        print(f"[WARN] RSS取得失敗 {site['name']}: {e}", file=sys.stderr)
    return events


def fetch_html(site: dict) -> list[dict]:
    events = []
    sel = site.get("selectors", {})
    base_url = site.get("base_url", site["url"])
    try:
        resp = requests.get(site["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "lxml")

        items = soup.select(sel.get("items", ""))
        if not items:
            print(f"[WARN] {site['name']}: セレクタ '{sel.get('items')}' で要素が見つかりません", file=sys.stderr)

        for item in items[:30]:
            def txt(s):
                el = item.select_one(s) if s else None
                return el.get_text(" ", strip=True) if el else ""

            title = txt(sel.get("title", ""))
            if not title:
                title = item.get_text(" ", strip=True)[:80]
            date_text = txt(sel.get("date", ""))
            description = txt(sel.get("description", ""))[:200]

            link_el = item.select_one(sel.get("link", "a"))
            href = link_el["href"] if link_el and link_el.has_attr("href") else site["url"]
            if not href.startswith("http"):
                href = urljoin(base_url, href)

            parsed_date = parse_japanese_date(date_text)

            events.append({
                "title": title,
                "date_start": parsed_date.isoformat() if parsed_date else None,
                "date_end": None,
                "description": description,
                "url": href,
                "source": site["name"],
            })
    except Exception as e:
        print(f"[WARN] HTML取得失敗 {site['name']}: {e}", file=sys.stderr)
    return events


# ── フィルター・ソート ────────────────────────────────────────

def filter_upcoming(events: list[dict]) -> list[dict]:
    today = date.today()
    oldest = today - timedelta(days=LOOKBACK_DAYS)   # 過去14日
    cutoff = today + timedelta(days=LOOKAHEAD_DAYS)  # 未来60日
    result = []
    for ev in events:
        ds = ev.get("date_start")
        if ds is None:
            result.append(ev)
            continue
        try:
            d = date.fromisoformat(ds)
            if oldest <= d <= cutoff:  # 過去14日〜未来60日の範囲
                result.append(ev)
        except ValueError:
            result.append(ev)
    return result


def sort_events(events: list[dict]) -> list[dict]:
    def key(ev):
        ds = ev.get("date_start") or "9999-12-31"
        return ds
    return sorted(events, key=key)


# ── メール送信 ───────────────────────────────────────────────

def format_date_ja(iso: str | None) -> str:
    if not iso:
        return "日時未定"
    try:
        d = date.fromisoformat(iso)
        weekdays = "月火水木金土日"
        w = weekdays[d.weekday()]
        return f"{d.year}年{d.month}月{d.day}日（{w}）"
    except Exception:
        return iso


def build_email_html(events: list[dict], site_url: str) -> str:
    if not events:
        body = "<p>今週〜来月のイベントはまだ登録されていません。</p>"
    else:
        cards = ""
        for ev in events:
            cards += f"""
            <div style="border:1px solid #ddd;border-radius:6px;padding:12px 16px;margin-bottom:12px;">
              <div style="font-size:13px;color:#2e6f8e;margin-bottom:4px;">{ev['source']}</div>
              <div style="font-size:16px;font-weight:700;margin-bottom:4px;">{ev['title']}</div>
              <div style="font-size:13px;color:#555;margin-bottom:6px;">{format_date_ja(ev.get('date_start'))}</div>
              <div style="font-size:13px;color:#333;margin-bottom:8px;">{ev.get('description','')}</div>
              <a href="{ev['url']}" style="font-size:13px;color:#c8451f;">詳細を見る →</a>
            </div>"""
        body = cards

    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"></head>
<body style="font-family:'Hiragino Kaku Gothic ProN',sans-serif;background:#f6f4ef;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;padding:24px;">
    <h1 style="font-size:20px;color:#1b2a3a;border-bottom:3px solid #c8451f;padding-bottom:8px;margin-bottom:16px;">
      気仙沼イベント情報
    </h1>
    <p style="font-size:13px;color:#888;margin-bottom:16px;">
      {date.today().year}年{date.today().month}月{date.today().day}日 更新
    </p>
    {body}
    <hr style="margin:24px 0;border:none;border-top:1px solid #eee;">
    <p style="font-size:12px;color:#aaa;text-align:center;">
      <a href="{site_url}" style="color:#2e6f8e;">サイトで全件表示</a>
    </p>
  </div>
</body></html>"""


def build_email_text(events: list[dict]) -> str:
    lines = [f"気仙沼イベント情報 ({date.today().isoformat()} 更新)\n"]
    if not events:
        lines.append("今週〜来月のイベントはまだ登録されていません。")
    for ev in events:
        lines.append(f"■ {ev['title']}")
        lines.append(f"  日程: {format_date_ja(ev.get('date_start'))}")
        lines.append(f"  情報元: {ev['source']}")
        lines.append(f"  URL: {ev['url']}")
        if ev.get("description"):
            lines.append(f"  {ev['description'][:100]}")
        lines.append("")
    return "\n".join(lines)


def send_email(events: list[dict]) -> None:
    user = os.environ.get("EMAIL_USER", "")
    password = os.environ.get("EMAIL_PASS", "")
    to_addr = os.environ.get("EMAIL_TO", "")
    site_url = os.environ.get("SITE_URL", "")

    if not (user and password and to_addr):
        print("[INFO] メール送信設定なし（EMAIL_USER / EMAIL_PASS / EMAIL_TO が未設定）。スキップ。")
        return

    print(f"[INFO] メール送信開始: {user} → {to_addr}")

    today = date.today()
    subject = f"【気仙沼イベント情報】{today.month}月{today.day}日 週のイベント（{len(events)}件）"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr

    msg.attach(MIMEText(build_email_text(events), "plain", "utf-8"))
    msg.attach(MIMEText(build_email_html(events, site_url), "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, to_addr, msg.as_string())
        print(f"[OK] メール送信完了 → {to_addr}")
    except Exception as e:
        print(f"[ERROR] メール送信失敗: {e}", file=sys.stderr)
        sys.exit(1)


# ── メイン ────────────────────────────────────────────────────

def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    sites = [s for s in config.get("sites", []) if s.get("enabled", False)]

    if not sites:
        print("[INFO] 有効なサイトが設定されていません。config/sites.json を確認してください。")

    all_events = []
    for site in sites:
        print(f"[INFO] 取得中: {site['name']}")
        if site.get("type") == "rss":
            events = fetch_rss(site)
        else:
            events = fetch_html(site)
        print(f"       → {len(events)} 件取得")
        all_events.extend(events)

    upcoming = sort_events(filter_upcoming(all_events))
    print(f"[INFO] 合計 {len(all_events)} 件 → 今後{LOOKAHEAD_DAYS}日以内 {len(upcoming)} 件")

    now_jst = datetime.now(JST).isoformat()
    output = {"updated": now_jst, "events": upcoming}
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {OUTPUT_PATH} を更新しました")

    send_email(upcoming)


if __name__ == "__main__":
    main()
