// Kojelaudan uutisvälityspalvelin (Cloudflare Worker)
//
// Selain ei saa hakea Ylen, Iltalehden ja Verkkouutisten RSS-syötteitä suoraan
// (CORS-esto). Tämä Worker hakee syötteet, yhdistää ne, poistaa yli 24 tuntia
// vanhat ja palauttaa saman JSON-muodon kuin data/news.json.
// Vastaus välimuistitetaan Cloudflaren reunalla 5 minuutiksi.
// Käyttöönotto: ks. README.md, kohta "Uutisten välityspalvelin".

const FEEDS = {
  "Yle": ["https://yle.fi/rss/uutiset/tuoreimmat"],
  "Iltalehti": ["https://www.iltalehti.fi/rss/uutiset.xml",
                "https://www.iltalehti.fi/rss/rss.xml",
                "https://www.iltalehti.fi/rss.xml"],
  "Ilta-Sanomat": ["https://www.is.fi/rss/tuoreimmat.xml",
                   "https://www.is.fi/rss/kotimaa.xml"],
  "Verkkouutiset": ["https://www.verkkouutiset.fi/feed/"],
};
const MAX_AGE_S = 24 * 3600;   // yli vuorokauden vanhat uutiset pois
const MAX_NEWS = 300;
const CACHE_S = 300;           // reunavälimuisti 5 min
const UA = "Mozilla/5.0 (compatible; kojelauta/1.0; +https://jarippeltola.com/kojelauta/)";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
};

const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", shy: "­" };
function decode(s) {
  return s
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
      if (e[0] === "#") {
        const n = e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
        return Number.isFinite(n) ? String.fromCodePoint(n) : m;
      }
      return ENT[e.toLowerCase()] ?? m;
    })
    .trim();
}

function tag(block, ...names) {
  for (const n of names) {
    const m = block.match(new RegExp(`<${n}(?:\\s[^>]*)?>([\\s\\S]*?)</${n}>`, "i"));
    if (m && m[1].trim()) return decode(m[1]);
    const h = block.match(new RegExp(`<${n}\\s[^>]*href="([^"]+)"`, "i"));  // Atom <link href=.../>
    if (h) return decode(h[1]);
  }
  return "";
}

function parseFeed(xml, source) {
  const blocks = xml.match(/<item[\s>][\s\S]*?<\/item>/gi) || xml.match(/<entry[\s>][\s\S]*?<\/entry>/gi) || [];
  const out = [];
  for (const b of blocks) {
    const title = tag(b, "title");
    let link = tag(b, "link");
    const date = tag(b, "pubDate", "published", "updated", "dc:date");
    if (!title || !link) continue;
    link = link.replace("?origin=rss", "");
    const t = Date.parse(date);
    out.push({ source, title: decode(title), link, ts: Number.isFinite(t) ? t / 1000 : 0 });
  }
  return out;
}

async function getSource(name, urls) {
  let lastErr = "tyhjä syöte";
  for (const url of urls) {
    try {
      const r = await fetch(url, {
        headers: { "User-Agent": UA, "Accept": "application/rss+xml, application/xml, */*" },
        cf: { cacheTtl: 120 },
      });
      if (!r.ok) { lastErr = `${r.status} ${r.statusText}`; continue; }
      const items = parseFeed(await r.text(), name);
      if (items.length) return { items };
    } catch (e) {
      lastErr = e.message;
    }
  }
  return { error: `${name}: ${lastErr}` };
}

async function buildNews() {
  const results = await Promise.all(Object.entries(FEEDS).map(([n, u]) => getSource(n, u)));
  const cutoff = Date.now() / 1000 - MAX_AGE_S;
  const seen = new Set();
  const items = results.flatMap(r => r.items || [])
    .filter(it => it.ts >= cutoff)
    .sort((a, b) => b.ts - a.ts)
    .filter(it => !seen.has(it.link) && seen.add(it.link))
    .slice(0, MAX_NEWS);
  return {
    items,
    errors: results.filter(r => r.error).map(r => r.error),
    generated: new Date().toISOString(),
  };
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (request.method !== "GET") return new Response("Method not allowed", { status: 405, headers: CORS });

    const cache = caches.default;
    const key = new Request(new URL("/news", request.url).toString());
    const hit = await cache.match(key);
    if (hit) return hit;

    const res = new Response(JSON.stringify(await buildNews()), {
      headers: {
        ...CORS,
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": `public, max-age=${CACHE_S}`,
      },
    });
    ctx.waitUntil(cache.put(key, res.clone()));
    return res;
  },
};
