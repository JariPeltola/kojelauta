# Kojelauta

Henkilökohtainen kojelauta: uutisotsikot (Yle, Iltalehti, Ilta-Sanomat, Verkkouutiset),
pörssisähkön hinta (Nord Pool, FI, sis. alv 25,5 %) ja Lahden sää seuraaville 24 tunnille.

## Miten tämä toimii

- `index.html` on itse sivu. GitHub Pages julkaisee sen osoitteeseen
  `https://<käyttäjätunnus>.github.io/<repon-nimi>/`.
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
