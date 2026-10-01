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

Kojelauta yhdistää selaimesta suoraan Home Assistantiin websocket-yhteydellä ja näyttää
kamerakuvat HA:n allekirjoittamilla, minuutin voimassa olevilla linkeillä. HA:han ei
tarvita lisäosia eikä `configuration.yaml`-muutoksia.

**Käyttöönotto:**
1. HA:ssa: oma profiili (vasen alakulma) → **Suojaus** → **Pitkäikäiset käyttöoikeustunnukset**
   → **Luo tunnus** → kopioi tunnus.
2. Avaa **http://jarippeltola.com/kojelauta/** (huom. `http`, ei `https`) ja paina Kamerat-palstan **⚙**:
   - Osoite: `http://homeassistant.local`
   - Tunnus: liitä kopioimasi tunnus
3. Jos Chrome kysyy lupaa käyttää paikallisverkon laitteita, valitse **Salli**.

Tunnus tallentuu vain tämän selaimen muistiin, ei GitHubiin. "Unohda" poistaa sen.

**Rajoitukset:** toimii vain kotiverkossa, ja sivu pitää avata `http://`-osoitteella, koska
HA:lla ei ole https-osoitetta (selain ei salli https-sivun yhdistää http-osoitteeseen).
Siksi GitHubin Pagesissa *Enforce HTTPS* jätetään pois päältä. Jos kamerat halutaan näkyviin
myös kodin ulkopuolelta, HA tarvitsee https-osoitteen, esim. Cloudflare Tunnel
(`ha.jarippeltola.com`, HA-lisäosa *Cloudflared*), ja silloin osoitteeksi vaihdetaan se.
