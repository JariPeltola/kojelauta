# Kojelauta

Henkilökohtainen kojelauta: uutisotsikot (Yle, Iltalehti, Ilta-Sanomat, Verkkouutiset),
pörssisähkön hinta (Nord Pool, FI, sis. alv 25,5 %), Lahden sää seuraaville 24 tunnille,
rahastot ja Home Assistantin valvontakamerat (pysäytyskuvat muutaman sekunnin välein).

Sivun jako: uutiset 40 % · tilastot 30 % · kamerat 30 %.

## Miten tämä toimii

- `index.html` on itse sivu. GitHub Pages julkaisee sen osoitteeseen
  **https://jarippeltola.com/kojelauta/** (oma verkkotunnus, ks. alla).
- `.github/workflows/paivita.yml` ajaa `build.py`:n 10 minuutin välein. Se hakee uutiset
  ja sähkön hinnat tiedostoihin `data/*.json` ja julkaisee sivun uudelleen.
  (Selain ei saa hakea uutissyötteitä suoraan toisilta sivustoilta, siksi tämä välivaihe.)
- Sää haetaan suoraan selaimessa Open-Meteosta.
- Sivu hakee uudet tiedot itse 10 minuutin välein.

## Käyttöönotto

1. Luo GitHubissa uusi **julkinen** repo, esim. `kojelauta`.
2. Lataa kaikki tämän kansion tiedostot repoon (myös `.github`-kansio).
3. Repon **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. **Actions**-välilehti → *Päivitä kojelauta* → **Run workflow**.
5. Sivu aukeaa minuutin päästä osoitteesta `https://<käyttäjätunnus>.github.io/kojelauta/`.

## Muokkaus

`build.py`:n alussa ovat syöteosoitteet (`FEEDS`), alv-kanta (`VAT`) ja sijainti (`LAHTI`).
Sään sijainti on lisäksi `index.html`:ssä (`LAHTI`).

Huom: GitHub ajaa ajastetut työt parhaansa mukaan, ruuhka-aikoina ajo voi myöhästyä
5–20 minuuttia. Uutisten otsikkorivin "haettu"-aika muuttuu punaiseksi, jos tiedot ovat
yli 45 minuuttia vanhoja.

## Kamerat (Home Assistant)

Kamerakuvat haetaan selaimessa suoraan Home Assistantista (`/api/camera_proxy/<kamera>`).
HA:n osoite ja tunnus syötetään sivun **⚙**-painikkeesta, ja ne tallentuvat vain kyseisen
selaimen muistiin (localStorage). Repoon ei kirjoiteta mitään salaista.

### Oma verkkotunnus jarippeltola.com

Verkkotunnus on Cloudflaressa. Sivu näkyy osoitteessa `jarippeltola.com/kojelauta`, koska
oma verkkotunnus on asetettu GitHubin *käyttäjäsivulle* (repo `jaripeltola.github.io`):
silloin kaikki projektisivut, myös tämä, näkyvät polkuna sen alla.

1. GitHubissa julkinen repo **`jaripeltola.github.io`**, jossa on `index.html` (etusivu).
2. Sen repon **Settings → Pages → Custom domain**: `jarippeltola.com` → Save,
   ja kun sertifikaatti on valmis, **Enforce HTTPS**.
3. Cloudflare → jarippeltola.com → **DNS → Records**, kaikki tilassa *DNS only* (harmaa pilvi):

   | Tyyppi | Nimi | Arvo |
   |---|---|---|
   | A | `@` | 185.199.108.153 |
   | A | `@` | 185.199.109.153 |
   | A | `@` | 185.199.110.153 |
   | A | `@` | 185.199.111.153 |
   | CNAME | `www` | jaripeltola.github.io |

Vanha osoite `jaripeltola.github.io/kojelauta` ohjautuu tämän jälkeen automaattisesti uuteen.

### 1. HTTPS-osoite Home Assistantille

GitHub Pages on https-sivu, ja selain estää siltä yhteydet `http://`-osoitteisiin.
HA tarvitsee siis https-osoitteen, joka toimii myös kodin ulkopuolelta. Vaihtoehdot:

Käytössä: **Cloudflare Tunnel**, osoite `https://ha.jarippeltola.com`. HA:ssa
lisäosa *Cloudflared* (repo `https://github.com/homeassistant-apps/app-cloudflared`),
asetus `external_hostname: ha.jarippeltola.com`. Ensimmäisellä käynnistyksellä
lokin linkistä hyväksytään yhteys Cloudflareen.

Muut vaihtoehdot:

| Tapa | Hinta | Porttien avaus reitittimeen | Vaivattomuus |
|---|---|---|---|
| **Nabu Casa** (HA Cloud) | n. 7,5 €/kk | ei | helpoin: Asetukset → Home Assistant Cloud |
| **Cloudflare Tunnel** -lisäosa | ilmainen, vaatii oman verkkotunnuksen | ei | kohtalainen |
| **DuckDNS**-lisäosa + Let's Encrypt | ilmainen | kyllä (443 → 8123) | kohtalainen |

Cloudflare Tunnelia käytettäessä `configuration.yaml`:iin tarvitaan lisäksi:
```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 172.30.33.0/24
```

### 2. Salli Kojelauta-sivun haut (CORS)

Lisää `configuration.yaml`:iin (samaan `http:`-lohkoon, jos sellainen on jo) ja käynnistä HA uudelleen:
```yaml
http:
  cors_allowed_origins:
    - https://jarippeltola.com
```

### 3. Tunnus

Suositus: tee HA:han erillinen käyttäjä kojelaudalle (Asetukset → Ihmiset → Käyttäjät,
ei ylläpitäjäoikeuksia). Kirjaudu sillä, avaa profiili → **Suojaus** → **Pitkäikäiset
käyttöoikeustunnukset** → Luo tunnus. Kopioi tunnus Kojelaudan ⚙-asetuksiin.

### 4. Asetukset sivulla

- **Osoite:** `https://ha.jarippeltola.com`
- **Kamerat:** tyhjä = kaikki `camera.`-entiteetit, tai luettelo halutussa järjestyksessä,
  esim. `camera.etupiha, camera.piha`
- **Päivitysväli:** oletus 5 s. Kuvia ei haeta, kun välilehti on taustalla.

Kuvaa klikkaamalla se aukeaa isona. Kellonaika muuttuu punaiseksi, jos kamera ei ole
vastannut kolmeen päivityskertaan.

Huom: tunnus on tallessa selaimessa, joten käytä kamerasivua vain omilla laitteillasi.
"Unohda"-painike poistaa tunnuksen selaimesta.
