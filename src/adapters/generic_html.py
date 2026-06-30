import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RadarVPOMadrid/1.0; +https://github.com/)"
}


def fetch_clean_text(url: str, timeout: int = 20) -> str:
    """Descarga una URL y devuelve el texto 'significativo' (sin scripts/estilos/nav/footer)
    para poder hashearlo y detectar cambios reales de contenido, no de ruido (fecha del footer, etc.)."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()

    # Intentamos centrarnos en el contenido principal si existe un <main> o <article>
    main = soup.find("main") or soup.find("article") or soup.find(id="content") or soup
    text = main.get_text(separator=" ", strip=True)

    # Normalizamos espacios para evitar falsos positivos por formateo
    return " ".join(text.split())


def check(source: dict) -> dict:
    """Devuelve {'text': str, 'url': str} para el pipeline genérico."""
    text = fetch_clean_text(source["url"])
    return {"text": text, "url": source["url"]}
