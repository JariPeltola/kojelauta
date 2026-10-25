# Kojelauta

Henkilökohtainen kojelauta: uutisotsikot (Yle, Iltalehti, Ilta-Sanomat, Verkkouutiset),
pörssisähkön hinta (Nord Pool, FI, sis. alv 25,5 %), Lahden sää seuraaville 24 tunnille,
ja rahastot.

Sivun jako: uutiset 60 % · tilastot 40 %.

Valvontakamerat ovat erillisellä, kirjautumisen takana olevalla sivulla
**https://jarippeltola.com/valvomo/** (repo `jaripeltola.github.io`, kansio `valvomo/`).

## Miten tämä toimii

- `index.html` on itse sivu. GitHub Pages julkaisee sen osoitteeseen
  **https://jarippeltola.com/kojelauta/** (oma verkkotunnus, ks. alla).
- `.github/workflows/paivita.yml` ajaa `build.py`:n 10 minuutin välein. Se hakee uutiset
  ja sähkön hinnat tiedostoihin `data/*.json` ja julkaisee sivun uudelleen.
  (Selain ei saa hakea uutissyötteitä suoraan toisilta sivustoilta, siksi tämä välivaihe.)
- Sää haetaan suoraan selaimessa Open-Meteosta.
- Sivu hakee uudet tiedot itse 10 minuutin välein (ja heti, kun välilehti tulee taas näkyviin).
- Yli 24 tuntia vanhat uutiset jätetään pois.

## Käyttöönotto

1. Luo GitHubissa uusi **julkinen** repo, esim. `kojelauta`.
2. Lataa kaikki tämän kansion tiedostot repoon (myös `.github`-kansio).
3. Repon **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. **Actions**-välilehti → *Päivitä kojelauta* → **Run workflow**.
5. Sivu aukeaa minuutin päästä osoitteesta `https://<käyttäjätunnus>.github.io/kojelauta/`.

## Muokkaus

`build.py`:n alussa ovat syöteosoitteet (`FEEDS`), alv-kanta (`VAT`) ja sijainti (`LAHTI`).
Sään sijainti on lisäksi `index.html`:ssä (`LAHTI`).

## Uutisten välityspalvelin (Cloudflare Worker)

GitHub ei takaa ajastettujen töiden ajoa: 10 minuutin ajastus toteutuu käytännössä usein
vain muutaman tunnin välein. Siksi uutiset haetaan ensisijaisesti pieneltä
Cloudflare Workerilta (`worker/uutiset.js`), joka hakee syötteet aina pyydettäessä
(reunavälimuisti 5 min). `data/news.json` jää varalle.

Käyttöönotto (kerran, ilmaisella Cloudflare-tilillä):

1. Cloudflare-hallintapaneeli → **Workers & Pages** → **Create** → **Create Worker**
   (Hello World -pohja), nimeksi esim. `kojelauta-uutiset` → **Deploy**.
2. **Edit code** → korvaa koodi tiedoston `worker/uutiset.js` sisällöllä → **Deploy**.
3. Kopioi Workerin osoite, esim. `https://kojelauta-uutiset.<tunnus>.workers.dev`,
   ja kirjoita se `index.html`:n riville `const NEWS_API = "";`.

Uutisten otsikkorivin "haettu"-aika muuttuu punaiseksi, jos tiedot ovat yli
25 minuuttia vanhoja (eli Worker ei vastaa ja ollaan GitHubin varatiedoston varassa).
