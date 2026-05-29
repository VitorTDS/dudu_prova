import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from utils.pdf_reader import clean_text, split_text_into_chunks


WIKIPEDIA_API_URL = "https://pt.wikipedia.org/w/api.php"
DUCKDUCKGO_HTML_URL = "https://duckduckgo.com/html/"

TRUSTED_DOMAINS = [
    "gov.br",
    "edu.br",
    "usp.br",
    "unicamp.br",
    "unesp.br",
    "ufrj.br",
    "ufmg.br",
    "fiocruz.br",
    "scielo.br",
    "bvsalud.org",
    "brasilescola.uol.com.br",
    "mundoeducacao.uol.com.br",
    "todamateria.com.br",
    "infoescola.com",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
}


def safe_theme_name(theme: str) -> str:
    """Cria um nome de arquivo seguro a partir do tema digitado."""
    name = re.sub(r"[^A-Za-z0-9_. -]", "_", theme).strip()
    name = re.sub(r"\s+", "_", name)
    return name[:80] or "tema"


def merge_trusted_domains(extra_domains: list[str] | None = None) -> list[str]:
    """Combina dominios padrao com dominios informados pelo usuario."""
    domains = TRUSTED_DOMAINS.copy()
    for domain in extra_domains or []:
        cleaned = domain.strip().lower()
        cleaned = cleaned.removeprefix("https://").removeprefix("http://")
        cleaned = cleaned.split("/")[0].removeprefix("www.")
        if cleaned and cleaned not in domains:
            domains.append(cleaned)
    return domains


def domain_is_trusted(url: str, trusted_domains: list[str] | None = None) -> bool:
    """Confere se a URL pertence a um dominio permitido."""
    domains = trusted_domains or TRUSTED_DOMAINS
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower().removeprefix("www.")
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains)


def search_wikipedia_pages(theme: str, limit: int = 3) -> list[dict]:
    """Busca paginas da Wikipedia em portugues relacionadas ao tema."""
    response = requests.get(
        WIKIPEDIA_API_URL,
        params={
            "action": "query",
            "list": "search",
            "srsearch": theme,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        },
        headers=REQUEST_HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("query", {}).get("search", [])


def fetch_wikipedia_page_text(page_id: int) -> dict:
    """Baixa o texto simples de uma pagina da Wikipedia."""
    response = requests.get(
        WIKIPEDIA_API_URL,
        params={
            "action": "query",
            "prop": "extracts|info",
            "pageids": page_id,
            "explaintext": 1,
            "inprop": "url",
            "format": "json",
            "utf8": 1,
        },
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    page = pages.get(str(page_id), {})
    return {
        "title": page.get("title", "Sem titulo"),
        "url": page.get("fullurl", ""),
        "text": clean_text(page.get("extract", "")),
        "source": "Wikipedia",
    }


def normalize_search_result_url(url: str) -> str:
    """Converte redirecionamentos do buscador para a URL final."""
    if not url:
        return ""

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "uddg" in query:
        return unquote(query["uddg"][0])
    if url.startswith("//"):
        return f"https:{url}"
    return url


def search_trusted_web_pages(
    theme: str,
    limit: int = 5,
    trusted_domains: list[str] | None = None,
) -> list[dict]:
    """Busca paginas publicas em dominios confiaveis sem chave de API."""
    domains = trusted_domains or TRUSTED_DOMAINS
    domain_query = " ".join(f"site:{domain}" for domain in domains)
    query = f"{theme} {domain_query}"

    response = requests.get(
        DUCKDUCKGO_HTML_URL,
        params={"q": query},
        headers=REQUEST_HEADERS,
        timeout=25,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    seen_urls = set()

    for link in soup.select("a.result__a"):
        title = clean_text(link.get_text(" "))
        url = normalize_search_result_url(link.get("href", ""))
        if not url or url in seen_urls or not domain_is_trusted(url, domains):
            continue
        seen_urls.add(url)
        results.append({"title": title or url, "url": url})
        if len(results) >= limit:
            break

    return results


def make_url_slug(text: str) -> str:
    """Transforma texto em slug simples para testar URLs educacionais comuns."""
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    value = text.lower()
    for source, target in replacements.items():
        value = value.replace(source, target)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def quote_search(text: str) -> str:
    """Codifica texto para uso em URL de busca."""
    return requests.utils.quote(text)


def build_direct_candidate_urls(theme: str) -> list[dict]:
    """Cria URLs previsiveis de portais educacionais quando o buscador falha."""
    slug = make_url_slug(theme)
    return [
        {"title": f"{theme} - Toda Materia", "url": f"https://www.todamateria.com.br/{slug}/"},
        {
            "title": f"{theme} - Brasil Escola",
            "url": f"https://brasilescola.uol.com.br/busca?q={quote_search(theme)}",
        },
        {
            "title": f"{theme} - Mundo Educacao",
            "url": f"https://mundoeducacao.uol.com.br/busca?q={quote_search(theme)}",
        },
    ]


def extract_main_text_from_html(html: str) -> str:
    """Extrai texto principal de uma pagina HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        tag.decompose()

    candidates = soup.find_all(["article", "main"]) or [soup.body or soup]
    texts = []
    for candidate in candidates:
        paragraphs = candidate.find_all(["h1", "h2", "h3", "p", "li"])
        for paragraph in paragraphs:
            text = clean_text(paragraph.get_text(" "))
            if len(text) >= 40:
                texts.append(text)

    return clean_text("\n\n".join(texts))


def fetch_web_page_text(
    url: str,
    title: str = "",
    trusted_domains: list[str] | None = None,
) -> dict:
    """Baixa uma pagina web confiavel e extrai texto."""
    if not domain_is_trusted(url, trusted_domains):
        raise ValueError(f"Dominio nao permitido: {url}")

    response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        raise ValueError("A pagina nao e HTML textual.")

    text = extract_main_text_from_html(response.text)
    if not text:
        raise ValueError("Nenhum texto util foi encontrado na pagina.")

    page_title = title
    if not page_title:
        soup = BeautifulSoup(response.text, "html.parser")
        page_title = clean_text(soup.title.get_text(" ")) if soup.title else url

    return {
        "title": page_title or url,
        "url": url,
        "text": text,
        "source": urlparse(url).hostname or "Web",
    }


def dedupe_pages(pages: list[dict]) -> list[dict]:
    """Remove paginas repetidas por URL ou inicio do texto."""
    unique = []
    seen = set()
    for page in pages:
        text_key = re.sub(r"\W+", " ", page.get("text", "")[:1000].lower()).strip()
        key = (page.get("url", "").lower(), text_key)
        if key in seen:
            continue
        seen.add(key)
        unique.append(page)
    return unique


def build_theme_document(theme: str, pages: list[dict]) -> str:
    """Monta um texto unico com titulo, fonte e conteudo das paginas."""
    parts = [f"Tema pesquisado: {theme}"]
    for page in pages:
        if not page.get("text"):
            continue
        parts.append(
            "\n".join(
                [
                    "",
                    f"Fonte: {page.get('source', 'Web')} - {page['title']}",
                    f"URL: {page['url']}",
                    "",
                    page["text"],
                ]
            )
        )
    return clean_text("\n\n".join(parts))


def save_downloaded_document(
    file_name: str,
    title: str,
    pages: list[dict],
    uploads_dir: Path,
    processed_dir: Path,
    subject: str = "Geral",
) -> dict:
    """Salva TXT e JSON processado para um conjunto de paginas baixadas."""
    uploads_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    text = build_theme_document(title, pages)
    source_path = uploads_dir / file_name
    source_path.write_text(text, encoding="utf-8")

    document = {
        "file_name": file_name,
        "source_path": str(source_path),
        "subject": subject or "Geral",
        "theme": title,
        "sources": [
            {"source": page.get("source", "Web"), "title": page["title"], "url": page["url"]}
            for page in pages
        ],
        "text": text,
        "chunks": split_text_into_chunks(text),
    }

    processed_path = processed_dir / f"{Path(file_name).stem}.json"
    processed_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return document


def download_theme_material(
    theme: str,
    uploads_dir: Path,
    processed_dir: Path,
    page_limit: int = 3,
    include_wikipedia: bool = True,
    include_trusted_web: bool = True,
    extra_domains: list[str] | None = None,
    subject: str = "Geral",
) -> dict:
    """Baixa material de estudo e salva localmente."""
    theme = clean_text(theme)
    if not theme:
        raise ValueError("Digite um tema valido.")

    pages = []
    errors = []
    trusted_domains = merge_trusted_domains(extra_domains)

    if include_wikipedia:
        try:
            for result in search_wikipedia_pages(theme, limit=page_limit):
                page = fetch_wikipedia_page_text(result["pageid"])
                if page["text"]:
                    pages.append(page)
        except Exception as exc:
            errors.append(f"Wikipedia: {exc}")

    if include_trusted_web:
        try:
            web_results = search_trusted_web_pages(theme, page_limit, trusted_domains)
            if not web_results:
                web_results = build_direct_candidate_urls(theme)

            for result in web_results[:page_limit]:
                try:
                    page = fetch_web_page_text(result["url"], result["title"], trusted_domains)
                    pages.append(page)
                except Exception as exc:
                    errors.append(f"{result['url']}: {exc}")
        except Exception as exc:
            errors.append(f"Busca web: {exc}")

    pages = dedupe_pages(pages)
    if not pages:
        detail = " ".join(errors) if errors else "Nenhuma pagina foi encontrada."
        raise ValueError(f"Nenhum texto confiavel foi baixado. {detail}")

    file_name = f"tema_{safe_theme_name(theme)}.txt"
    return save_downloaded_document(file_name, theme, pages, uploads_dir, processed_dir, subject)


def download_urls_material(
    urls: list[str],
    uploads_dir: Path,
    processed_dir: Path,
    extra_domains: list[str] | None = None,
    subject: str = "Geral",
) -> dict:
    """Baixa URLs informadas manualmente e salva como um unico material."""
    trusted_domains = merge_trusted_domains(extra_domains)
    pages = []
    errors = []

    for url in urls:
        url = url.strip()
        if not url:
            continue
        try:
            pages.append(fetch_web_page_text(url, trusted_domains=trusted_domains))
        except Exception as exc:
            errors.append(f"{url}: {exc}")

    pages = dedupe_pages(pages)
    if not pages:
        detail = " ".join(errors) if errors else "Nenhuma URL valida foi informada."
        raise ValueError(f"Nenhum texto foi baixado das URLs. {detail}")

    title = pages[0]["title"] if len(pages) == 1 else "URLs manuais"
    file_name = f"url_{safe_theme_name(title)}.txt"
    return save_downloaded_document(file_name, title, pages, uploads_dir, processed_dir, subject)
