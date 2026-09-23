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
import time
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
# Ensisijainen lähde on Nord Poolin oma rajapinta. Jos se ei vastaa, samat Nord Poolin
# Suomen hinnat haetaan Eleringin (Viron kantaverkkoyhtiö) rajapinnasta. Jos nekin
# puuttuvat, käytetään edellisen onnistuneen haun hintoja, ettei graafi tyhjene.
PREV_PRICE_URL = os.environ.get("PREV_PRICE_URL", "")


def fetch_retry(url, tries=3, timeout=30):
    for n in range(tries):
        try:
            return fetch(url, timeout=timeout)
        except Exception:
            if n == tries - 1:
                raise
            time.sleep(4 * (n + 1))


def _nordpool_day(d):
    url = ("https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
           f"?date={d.isoformat()}&market=DayAhead&deliveryArea=FI&currency=EUR")
    raw = fetch_retry(url)
    if not raw:
        return []  # päivän hintoja ei ole vielä julkaistu
    out = []
    for e in json.loads(raw).get("multiAreaEntries", []):
        eur_mwh = e.get("entryPerArea", {}).get("FI")
        if eur_mwh is None:
            continue
        s = datetime.fromisoformat(e["deliveryStart"].replace("Z", "+00:00"))
        t = datetime.fromisoformat(e["deliveryEnd"].replace("Z", "+00:00"))
        out.append((s, t, eur_mwh))
    return out


def _elering(start, end):
    fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    url = f"https://dashboard.elering.ee/api/nps/price?start={fmt(start)}&end={fmt(end)}"
    rows = json.loads(fetch_retry(url)).get("data", {}).get("fi", [])
    rows = sorted(rows, key=lambda r: r["timestamp"])
    out = []
    for i, r in enumerate(rows):
        s = datetime.fromtimestamp(r["timestamp"], timezone.utc)
        if i + 1 < len(rows):
            t = datetime.fromtimestamp(rows[i + 1]["timestamp"], timezone.utc)
        else:
            t = s + (out[-1][1] - out[-1][0] if out else timedelta(minutes=15))
        out.append((s, t, r["price"]))
    return out


def _point(s, t, eur_mwh):
    c_kwh = eur_mwh / 10.0                 # €/MWh → c/kWh
    if c_kwh > 0:                          # ALV lisätään vain positiiviseen hintaan
        c_kwh *= 1 + VAT
    return {"start": s.astimezone(TZ).isoformat(),
            "minutes": int((t - s).total_seconds() // 60),
            "price": round(c_kwh, 3)}


def _covers(points, a, b):
    """Kattavatko hinnat aikavälin a–b aukottomasti?"""
    t = a
    for k in sorted(points):
        if k > t:
            return False
        end = k + timedelta(minutes=points[k]["minutes"])
        if end > t:
            t = end
        if t >= b:
            return True
    return t >= b


def get_price():
    today = datetime.now(TZ).date()
    day_start = datetime.combine(today, datetime.min.time(), TZ)
    tomorrow = day_start + timedelta(days=1)
    window_end = day_start + timedelta(days=2)
    points, problems, source = {}, [], "Nord Pool"

    # 1) Nord Pool (toimituspäivä on CET-päivä → eilinen, tänään, huominen)
    for d in (today - timedelta(days=1), today, today + timedelta(days=1)):
        try:
            for s, t, v in _nordpool_day(d):
                points[s] = _point(s, t, v)
        except Exception as e:
            problems.append(f"Nord Pool {d}: {e}")

    # 2) Elering, jos tämän päivän hinnoissa on aukkoja (tai huominen jäi hakematta)
    if problems or not _covers(points, day_start, tomorrow):
        try:
            added = 0
            for s, t, v in _elering(day_start, window_end):
                if s not in points:
                    points[s] = _point(s, t, v)
                    added += 1
            if added:
                source = "Nord Pool / Elering"
        except Exception as e:
            problems.append(f"Elering: {e}")

    # 3) Edellinen onnistunut haku, jos tänään on yhä aukkoja
    if not _covers(points, day_start, tomorrow) and PREV_PRICE_URL:
        try:
            prev = json.loads(fetch_retry(PREV_PRICE_URL + f"?t={int(time.time())}", tries=2))
            for p in prev.get("points", []):
                s = datetime.fromisoformat(p["start"])
                if s >= day_start and s not in points:
                    points[s] = p
        except Exception as e:
            problems.append(f"edellinen haku: {e}")

    series = [points[k] for k in sorted(points) if day_start <= k < window_end]
    ok_today = _covers(points, day_start, tomorrow)
    for p in problems:
        print("  hinta:", p)
    return {"points": series, "vat": VAT, "source": source,
            # sivulle näytetään virhe vain, jos tämän päivän hinnoista puuttuu jotain
            "errors": [] if ok_today else (problems or ["tämän päivän hinnoissa on aukkoja"])}


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
