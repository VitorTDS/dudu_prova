import json
import re
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def clean_text(text: str) -> str:
    """Remove excesso de espaços e quebras de linha do texto extraído."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text_into_chunks(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    """
    Divide o texto em trechos menores para facilitar a busca.

    O overlap preserva um pouco de contexto entre um trecho e o próximo.
    """
    if not text:
        return []

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        start = max(end - overlap, start + 1)

    return chunks


def extract_text_from_pdf(file_obj: BinaryIO) -> str:
    """Extrai texto de um arquivo PDF usando pypdf."""
    reader = PdfReader(file_obj)
    pages_text = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages_text.append(page_text)
        except Exception as exc:
            pages_text.append(f"[Erro ao ler página {page_number}: {exc}]")

    return clean_text("\n\n".join(pages_text))


def extract_text_from_txt(file_obj: BinaryIO) -> str:
    """Extrai texto de TXT tentando encodings comuns."""
    raw = file_obj.read()

    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return clean_text(raw.decode(encoding))
        except UnicodeDecodeError:
            continue

    raise ValueError("Não foi possível decodificar o arquivo TXT.")


def extract_text_from_file(file_obj: BinaryIO, file_name: str) -> str:
    """Escolhe o extrator correto com base na extensão do arquivo."""
    extension = Path(file_name).suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_obj)
    if extension == ".txt":
        return extract_text_from_txt(file_obj)

    raise ValueError(f"Formato não suportado: {extension}")


def safe_file_name(file_name: str) -> str:
    """Cria um nome de arquivo seguro para salvar localmente."""
    name = Path(file_name).name
    return re.sub(r"[^A-Za-z0-9_. -]", "_", name).strip()


def process_and_save_file(
    uploaded_file,
    uploads_dir: Path,
    processed_dir: Path,
    subject: str = "Geral",
) -> dict:
    """
    Salva o arquivo original e grava um JSON com texto extraído e trechos.

    O objeto uploaded_file vem do Streamlit e se comporta como um arquivo binário.
    """
    file_name = safe_file_name(uploaded_file.name)
    extension = Path(file_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Envie apenas arquivos PDF ou TXT.")

    uploads_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    original_path = uploads_dir / file_name
    original_path.write_bytes(uploaded_file.getbuffer())

    uploaded_file.seek(0)
    text = extract_text_from_file(uploaded_file, file_name)

    if not text:
        raise ValueError("Nenhum texto foi extraído do arquivo.")

    document = {
        "file_name": file_name,
        "source_path": str(original_path),
        "subject": subject or "Geral",
        "text": text,
        "chunks": split_text_into_chunks(text),
    }

    processed_path = processed_dir / f"{Path(file_name).stem}.json"
    processed_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return document


def load_processed_documents(processed_dir: Path) -> list[dict]:
    """Carrega todos os JSONs já processados."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    documents = []

    for json_path in sorted(processed_dir.glob("*.json")):
        try:
            document = json.loads(json_path.read_text(encoding="utf-8"))
            if document.get("text") and document.get("chunks"):
                document.setdefault("subject", "Geral")
                documents.append(document)
        except Exception:
            # Ignora arquivos corrompidos para manter o app funcionando.
            continue

    return documents
