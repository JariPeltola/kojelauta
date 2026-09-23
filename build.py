#!/usr/bin/env python3
"""Hakee kojelaudan datan ja kirjoittaa sen JSON-tiedostoiksi.

GitHub Actions ajaa tämän 10 minuutin välein (.github/workflows/paivita.yml)
ja julkaisee tuloksen GitHub Pagesiin sivun index.html viereen.
Käsin:  python build.py _site
Vain Pythonin vakiokirjasto, ei asennettavia paketteja.
"""
import html
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Helsinki")
except Exception:  # Windowsissa tzdata voi puuttua → käytetään koneen omaa aikavyöhykettä
    TZ = datetime.now().astimezone().tzinfo
VAT = 0.255            # Suomen yleinen arvonlisävero (25,5 %)
MAX_NEWS = 120

# Jokaiselle lähteelle voi antaa useita osoitteita: ensimmäinen toimiva käytetään.
FEEDS = {
    "Yle": ["https://yle.fi/rss/uutiset/tuoreimmat"],
    "Iltalehti": ["https://www.iltalehti.fi/rss/uutiset.xml",
                  "https://www.iltalehti.fi/rss/rss.xml",
                  "https://www.iltalehti.fi/rss.xml"],
    "Ilta-Sanomat": ["https://www.is.fi/rss/tuoreimmat.xml",
                     "https://www.is.fi/rss/kotimaa.xml"],
    "Verkkouutiset": ["https://www.verkkouutiset.fi/feed/"],
}

LAHTI = (60.9827, 25.6615)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status == 204:
            return b""
        return r.read()


# ---------- uutiset ----------
def _text(el, *names):
    for n in names:
        found = el.find(n)
        if found is not None:
            if found.text and found.text.strip():
                return found.text.strip()
            if found.get("href"):
                return found.get("href")
    return ""


def _parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def parse_feed(xml_bytes, source):
    root = ET.fromstring(xml_bytes)
    atom = "{http://www.w3.org/2005/Atom}"
    items = root.findall(".//item") or root.findall(f".//{atom}entry")
    out = []
    for it in items:
        title = _text(it, "title", f"{atom}title")
        link = _text(it, "link", f"{atom}link")
        date = _parse_date(_text(it, "pubDate", f"{atom}updated", f"{atom}published",
                                 "{http://purl.org/dc/elements/1.1/}date"))
        if not title or not link:
            continue
        link = link.replace("?origin=rss", "")
        out.append({
            "source": source,
            "title": html.unescape(title),
            "link": link,
            "ts": date.timestamp() if date else 0,
        })
    return out


def get_news():
    items, errors = [], []
    for name, urls in FEEDS.items():
        last_err = None
        for url in urls:
            try:
                got = parse_feed(fetch(url), name)
                if got:
                    items += got
                    last_err = None
                    break
                last_err = "tyhjä syöte"
            except Exception as e:  # yksi rikki mennyt syöte ei kaada muita
                last_err = e
        if last_err:
            errors.append(f"{name}: {last_err}")
    seen, unique = set(), []
    for it in sorted(items, key=lambda x: x["ts"], reverse=True):
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        unique.append(it)
    return {"items": unique[:MAX_NEWS], "errors": errors}


# ---------- pörssisähkö (Nord Pool, hinta-alue FI) ----------
def get_price():
    today = datetime.now(TZ).date()
    points, errors = {}, []
    # Nord Poolin toimituspäivä on CET-päivä; haetaan eilinen–huominen,
    # jotta Suomen vuorokausi tulee kokonaan mukaan.
    for d in (today - timedelta(days=1), today, today + timedelta(days=1)):
        url = ("https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
               f"?date={d.isoformat()}&market=DayAhead&deliveryArea=FI&currency=EUR")
        try:
            raw = fetch(url)
            if not raw:
                continue  # huomisen hinnat eivät vielä julkaistu
            data = json.loads(raw)
            for e in data.get("multiAreaEntries", []):
                eur_mwh = e.get("entryPerArea", {}).get("FI")
                if eur_mwh is None:
                    continue
                start = datetime.fromisoformat(e["deliveryStart"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(e["deliveryEnd"].replace("Z", "+00:00"))
                c_kwh = eur_mwh / 10.0            # €/MWh → c/kWh
                if c_kwh > 0:                      # ALV lisätään vain positiiviseen hintaan
                    c_kwh *= 1 + VAT
                points[start] = {
                    "start": start.astimezone(TZ).isoformat(),
                    "minutes": int((end - start).total_seconds() // 60),
                    "price": round(c_kwh, 3),
                }
        except Exception as e:
            errors.append(f"{d}: {e}")
    # näytetään kuluvan päivän alusta eteenpäin (Suomen aikaa)
    day_start = datetime.combine(today, datetime.min.time(), TZ)
    series = [points[k] for k in sorted(points) if k >= day_start]
    return {"points": series, "vat": VAT, "errors": errors}


# ---------- sää (Open-Meteo, Lahti) ----------
def get_weather():
    lat, lon = LAHTI
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}"
           "&hourly=temperature_2m,precipitation,weather_code,wind_speed_10m"
           "&wind_speed_unit=ms&timezone=Europe%2FHelsinki&forecast_hours=25")
    data = json.loads(fetch(url))
    h = data["hourly"]
    return {
        "times": h["time"],
        "temp": h["temperature_2m"],
        "precip": h["precipitation"],
        "code": h["weather_code"],
        "wind": h["wind_speed_10m"],
    }



# ---------- kirjoitus ----------
def main(out_dir):
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()
    failed = []
    for name, fn in (("news", get_news), ("price", get_price), ("weather", get_weather)):
        try:
            payload = fn()
        except Exception as e:
            payload = {"error": str(e)}
            failed.append(name)
        payload["generated"] = generated
        with open(os.path.join(data_dir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        print(f"{name}: {'VIRHE ' + payload['error'] if 'error' in payload else 'ok'}")
    return failed


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "_site")
