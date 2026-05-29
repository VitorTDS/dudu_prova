from pathlib import Path
import json


def document_type(document: dict) -> str:
    """Classifica o material para facilitar filtros na interface."""
    file_name = document.get("file_name", "").lower()
    if document.get("theme"):
        return "Tema baixado"
    if file_name.endswith(".pdf"):
        return "PDF"
    if file_name.endswith(".txt"):
        return "TXT"
    return "Outro"


def filter_documents(
    documents: list[dict],
    selected_files: list[str] | None = None,
    selected_types: list[str] | None = None,
    selected_subject: str | None = None,
) -> list[dict]:
    """Filtra documentos por nome e tipo."""
    selected_files = selected_files or []
    selected_types = selected_types or []

    filtered = documents
    if selected_subject and selected_subject != "Todas":
        filtered = [doc for doc in filtered if doc.get("subject", "Geral") == selected_subject]
    if selected_files:
        filtered = [doc for doc in filtered if doc.get("file_name") in selected_files]
    if selected_types:
        filtered = [doc for doc in filtered if document_type(doc) in selected_types]

    return filtered


def list_subjects(documents: list[dict]) -> list[str]:
    """Lista materias existentes nos documentos."""
    subjects = {doc.get("subject", "Geral") or "Geral" for doc in documents}
    return sorted(subjects)


def update_material_subject(file_name: str, subject: str, processed_dir: Path) -> bool:
    """Atualiza a materia de um documento processado."""
    safe_name = Path(file_name).name
    processed_path = processed_dir / f"{Path(safe_name).stem}.json"
    if not processed_path.exists():
        return False

    document = json.loads(processed_path.read_text(encoding="utf-8"))
    document["subject"] = subject or "Geral"
    processed_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def delete_material(file_name: str, uploads_dir: Path, processed_dir: Path) -> list[Path]:
    """Remove o arquivo original e o JSON processado de um material."""
    removed = []
    safe_name = Path(file_name).name
    upload_path = uploads_dir / safe_name
    processed_path = processed_dir / f"{Path(safe_name).stem}.json"

    for path in (upload_path, processed_path):
        if path.exists() and path.is_file():
            path.unlink()
            removed.append(path)

    return removed


def delete_many_materials(file_names: list[str], uploads_dir: Path, processed_dir: Path) -> int:
    """Remove varios materiais selecionados e retorna quantos arquivos foram apagados."""
    removed_count = 0
    for file_name in file_names:
        removed_count += len(delete_material(file_name, uploads_dir, processed_dir))
    return removed_count
