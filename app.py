from pathlib import Path

import pandas as pd
import streamlit as st

from utils.answer_generator import (
    generate_answer,
    generate_flashcards,
    generate_quiz,
    generate_summary,
)
from utils.calculator import BASES, convert_base, find_matching_option, logic_gate_result, truth_table
from utils.material_manager import (
    delete_many_materials,
    document_type,
    filter_documents,
    list_subjects,
    update_material_subject,
)
from utils.pdf_reader import load_processed_documents, process_and_save_file
from utils.search import search_relevant_chunks
from utils.theme_downloader import (
    TRUSTED_DOMAINS,
    download_theme_material,
    download_urls_material,
    merge_trusted_domains,
)


BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def prepare_directories() -> None:
    """Garante que as pastas locais necessarias existem."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def parse_lines(text: str) -> list[str]:
    """Transforma texto com um item por linha em lista limpa."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_questions(text: str) -> list[str]:
    """Separa varias perguntas coladas no campo de texto."""
    questions = []
    for line in parse_lines(text):
        cleaned = line.strip()
        cleaned = cleaned.lstrip("-• ")
        cleaned = cleaned.strip()

        # Remove numeracao comum: 1. pergunta, 1) pergunta, 01 - pergunta.
        parts = cleaned.split(maxsplit=1)
        if parts:
            marker = parts[0].rstrip(".):-")
            if marker.isdigit() and len(parts) > 1:
                cleaned = parts[1].strip()

        if cleaned:
            questions.append(cleaned)

    return questions


def normalize_subject(subject: str) -> str:
    """Normaliza o nome da materia."""
    subject = " ".join(subject.strip().split())
    return subject or "Geral"


def show_documents_table(documents: list[dict]) -> None:
    """Mostra um resumo dos materiais processados."""
    if not documents:
        st.info("Nenhum material processado ainda. Envie PDF/TXT ou baixe um tema.")
        return

    rows = []
    for doc in documents:
        rows.append(
            {
                "Arquivo": doc["file_name"],
                "Materia": doc.get("subject", "Geral"),
                "Tipo": document_type(doc),
                "Fontes": len(doc.get("sources", [])),
                "Trechos": len(doc.get("chunks", [])),
                "Caracteres": len(doc.get("text", "")),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_sources(document: dict) -> None:
    """Mostra fontes de um material baixado da web."""
    sources = document.get("sources", [])
    if not sources:
        return

    for source in sources:
        st.markdown(
            f"- {source.get('source', 'Web')}: "
            f"[{source.get('title', source.get('url', 'fonte'))}]({source.get('url', '')})"
        )


def main() -> None:
    prepare_directories()
    st.set_page_config(
        page_title="Chat offline com meus materiais",
        page_icon="📚",
        layout="wide",
    )

    st.title("Chat offline com meus materiais")
    st.caption("Consulta local para estudar com PDFs, TXTs e materiais baixados por tema.")

    if "last_processed" not in st.session_state:
        st.session_state.last_processed = []

    documents = load_processed_documents(PROCESSED_DIR)
    subjects = list_subjects(documents)

    with st.sidebar:
        st.header("Materia")
        subject_options = subjects + ["Nova materia"]
        chosen_subject = st.selectbox(
            "Entrar na materia",
            options=subject_options if subject_options else ["Geral", "Nova materia"],
        )
        new_subject_name = ""
        if chosen_subject == "Nova materia":
            new_subject_name = st.text_input("Nome da nova materia", placeholder="Exemplo: Informatica")
            active_subject = normalize_subject(new_subject_name)
        else:
            active_subject = chosen_subject

        st.caption(f"Materia atual: {active_subject}")
        st.divider()

        st.header("Adicionar materiais")
        uploaded_files = st.file_uploader(
            "Enviar PDF ou TXT",
            type=["pdf", "txt"],
            accept_multiple_files=True,
            help="Os arquivos ficam em data/uploads e os textos processados em data/processed.",
        )

        if uploaded_files:
            processed_now = []
            for uploaded_file in uploaded_files:
                try:
                    result = process_and_save_file(
                        uploaded_file,
                        UPLOADS_DIR,
                        PROCESSED_DIR,
                        subject=active_subject,
                    )
                    processed_now.append(result["file_name"])
                    st.success(f"Processado: {result['file_name']}")
                except Exception as exc:
                    st.error(f"Erro ao processar {uploaded_file.name}: {exc}")
            st.session_state.last_processed = processed_now
            if processed_now:
                st.rerun()

        st.divider()
        st.header("Baixar por tema")
        themes_text = st.text_area(
            "Temas",
            placeholder="Um tema por linha\nExemplo:\nRevolucao Francesa\nFotossintese",
            height=110,
        )
        page_limit = st.slider("Paginas por tema", 1, 8, 3)
        include_wikipedia = st.checkbox("Incluir Wikipedia", value=True)
        include_trusted_web = st.checkbox("Incluir outras fontes confiaveis", value=True)

        extra_domains_text = st.text_area(
            "Dominios extras permitidos",
            placeholder="Um dominio por linha\nExemplo:\nportal.mec.gov.br",
            height=80,
        )
        extra_domains = parse_lines(extra_domains_text)

        with st.expander("Dominios usados"):
            st.write(", ".join(merge_trusted_domains(extra_domains)))

        if st.button("Baixar e armazenar temas"):
            themes = parse_lines(themes_text)
            if not themes:
                st.error("Digite pelo menos um tema.")
            elif not include_wikipedia and not include_trusted_web:
                st.error("Selecione pelo menos uma fonte.")
            else:
                downloaded = []
                for theme in themes:
                    try:
                        with st.spinner(f"Baixando material sobre: {theme}"):
                            document = download_theme_material(
                                theme=theme,
                                uploads_dir=UPLOADS_DIR,
                                processed_dir=PROCESSED_DIR,
                                page_limit=page_limit,
                                include_wikipedia=include_wikipedia,
                                include_trusted_web=include_trusted_web,
                                extra_domains=extra_domains,
                                subject=active_subject,
                            )
                        downloaded.append(document["file_name"])
                        st.success(f"Material salvo: {document['file_name']}")
                        with st.expander(f"Fontes baixadas para {theme}"):
                            render_sources(document)
                    except Exception as exc:
                        st.error(f"Erro ao baixar '{theme}': {exc}")

                if downloaded:
                    st.session_state.last_processed = downloaded
                    st.rerun()

        st.divider()
        st.header("Baixar por URL")
        urls_text = st.text_area(
            "URLs",
            placeholder="Uma URL por linha",
            height=90,
        )
        if st.button("Baixar URLs"):
            urls = parse_lines(urls_text)
            if not urls:
                st.error("Digite pelo menos uma URL.")
            else:
                try:
                    with st.spinner("Baixando URLs informadas..."):
                        document = download_urls_material(
                            urls=urls,
                            uploads_dir=UPLOADS_DIR,
                            processed_dir=PROCESSED_DIR,
                            extra_domains=extra_domains,
                            subject=active_subject,
                        )
                    st.session_state.last_processed = [document["file_name"]]
                    st.success(f"Material salvo: {document['file_name']}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro ao baixar URLs: {exc}")

        if st.button("Recarregar materiais"):
            st.rerun()

    documents = load_processed_documents(PROCESSED_DIR)
    subject_documents = filter_documents(documents, selected_subject=active_subject)

    left_col, right_col = st.columns([1, 2], gap="large")

    with left_col:
        st.subheader(f"Materiais de {active_subject}")
        show_documents_table(subject_documents)

        if st.session_state.last_processed:
            st.success("Ultimos processados: " + ", ".join(st.session_state.last_processed))

        with st.expander("Gerenciar materiais"):
            files_to_delete = st.multiselect(
                "Selecionar para apagar",
                options=[doc["file_name"] for doc in subject_documents],
            )
            confirm_delete = st.checkbox("Confirmo que quero apagar os materiais selecionados")
            if st.button("Apagar selecionados", disabled=not files_to_delete or not confirm_delete):
                removed_count = delete_many_materials(files_to_delete, UPLOADS_DIR, PROCESSED_DIR)
                st.success(f"{removed_count} arquivo(s) local(is) apagado(s).")
                st.rerun()

            st.divider()
            st.markdown("**Mover material para outra materia**")
            file_to_move = st.selectbox(
                "Material",
                options=[""] + [doc["file_name"] for doc in documents],
            )
            target_subject = st.text_input("Materia de destino", placeholder="Exemplo: Matematica")
            if st.button("Mover material", disabled=not file_to_move or not target_subject.strip()):
                updated = update_material_subject(file_to_move, normalize_subject(target_subject), PROCESSED_DIR)
                if updated:
                    st.success("Materia atualizada.")
                    st.rerun()
                else:
                    st.error("Nao foi possivel atualizar esse material.")

        with st.expander("Busca por palavra-chave"):
            keyword = st.text_input("Digite uma palavra ou termo")
            if keyword:
                matches = search_relevant_chunks(keyword, subject_documents, top_k=5)
                if matches:
                    for index, match in enumerate(matches, start=1):
                        st.markdown(f"**{index}. {match['file_name']}**")
                        st.write(match["chunk"])
                else:
                    st.warning("Nenhum trecho encontrado para esse termo.")

    with right_col:
        st.subheader("Estudar com os materiais")
        if not subject_documents:
            st.warning("Adicione pelo menos um material nesta materia para liberar perguntas e modos de estudo.")

        available_types = sorted({document_type(doc) for doc in subject_documents})
        selected_types = st.multiselect("Tipos usados", options=available_types, default=available_types)
        selected_files = st.multiselect(
            "Arquivos especificos",
            options=[doc["file_name"] for doc in subject_documents],
            help="Se ficar vazio, usa todos os arquivos dos tipos escolhidos.",
        )
        active_documents = filter_documents(
            subject_documents,
            selected_files=selected_files,
            selected_types=selected_types,
        )
        st.caption(f"{len(active_documents)} material(is) selecionado(s) para consulta.")

        mode = st.radio(
            "Modo",
            options=["Resposta", "Resumo", "Flashcards", "Simulado"],
            horizontal=True,
        )
        batch_mode = False
        if mode == "Resposta":
            batch_mode = st.checkbox("Responder varias perguntas de uma vez")

        question = st.text_area(
            "Perguntas" if batch_mode else "Pergunta ou foco do estudo",
            placeholder=(
                "Cole uma pergunta por linha\n"
                "1. O que e uma porta AND?\n"
                "2. Quando a porta OR vale 1?"
                if batch_mode
                else "Exemplo: Explique as causas principais desse tema."
            ),
            height=180 if batch_mode else 120,
            disabled=not active_documents,
        )
        top_k = st.slider("Quantidade de trechos de referencia", 1, 15, 6)

        if st.button("Gerar", type="primary"):
            if not active_documents:
                st.error("Selecione ou adicione pelo menos um material.")
            elif mode == "Resposta" and not question.strip():
                st.error("Digite uma pergunta para gerar uma resposta.")
            elif mode == "Resposta" and batch_mode and not parse_questions(question):
                st.error("Digite pelo menos uma pergunta por linha.")
            else:
                if mode == "Resposta" and batch_mode:
                    questions = parse_questions(question)
                    with st.spinner("Respondendo perguntas com os materiais selecionados..."):
                        for question_index, single_question in enumerate(questions, start=1):
                            references = search_relevant_chunks(
                                single_question,
                                active_documents,
                                top_k=top_k,
                            )
                            output = generate_answer(single_question, references)

                            st.markdown(f"### Pergunta {question_index}")
                            st.markdown(f"**{single_question}**")
                            st.write(output)

                            with st.expander(f"Referencias da pergunta {question_index}"):
                                if references:
                                    for index, ref in enumerate(references, start=1):
                                        st.markdown(
                                            f"**Referencia {index} - {ref['file_name']} "
                                            f"(relevancia: {ref.get('score', 0):.2f})**"
                                        )
                                        st.write(ref["chunk"])
                                else:
                                    st.info("Nenhum trecho relevante foi encontrado.")
                else:
                    query = question.strip() or "resumo pontos principais conceitos importantes"
                    with st.spinner("Buscando nos materiais selecionados..."):
                        references = search_relevant_chunks(query, active_documents, top_k=top_k)

                        if mode == "Resposta":
                            output = generate_answer(query, references)
                        elif mode == "Resumo":
                            output = generate_summary(references, query)
                        elif mode == "Flashcards":
                            output = generate_flashcards(references, query)
                        else:
                            output = generate_quiz(references, query)

                    st.markdown(f"### {mode}")
                    st.write(output)

                    st.markdown("### Trechos usados como referencia")
                    if references:
                        for index, ref in enumerate(references, start=1):
                            st.markdown(
                                f"**Referencia {index} - {ref['file_name']} "
                                f"(relevancia: {ref.get('score', 0):.2f})**"
                            )
                            st.write(ref["chunk"])
                    else:
                        st.info("Nenhum trecho relevante foi encontrado.")

    with st.expander("Leitor rapido de arquivo processado"):
        selected_file = st.selectbox(
            "Escolha um arquivo",
            options=[""] + [doc["file_name"] for doc in subject_documents],
        )
        if selected_file:
            selected_doc = next(doc for doc in subject_documents if doc["file_name"] == selected_file)
            render_sources(selected_doc)
            st.text_area("Texto extraido", selected_doc["text"], height=300)

    with st.expander("Calculadora de bases e portas logicas", expanded=False):
        calc_tab, options_tab, gates_tab = st.tabs(
            ["Conversao de bases", "Questao de alternativa", "Portas logicas"]
        )

        with calc_tab:
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                number_value = st.text_input("Numero", placeholder="Exemplo: 1011")
            with c2:
                from_base = st.selectbox("Base de entrada", options=list(BASES.keys()), index=1)
            with c3:
                to_base = st.selectbox("Base de saida", options=list(BASES.keys()), index=0)

            if st.button("Converter numero"):
                try:
                    conversion = convert_base(number_value, from_base, to_base)
                    st.success(f"Resultado: {conversion['result']}")
                    st.code(conversion["steps"], language="text")
                except Exception as exc:
                    st.error(f"Erro na conversao: {exc}")

        with options_tab:
            st.caption("Cole uma questao com alternativas. O app calcula e tenta marcar a alternativa correta.")
            option_question = st.text_area(
                "Questao",
                placeholder=(
                    "Exemplo:\n"
                    "Qual alternativa representa 1011 em decimal?\n"
                    "A) 9\nB) 10\nC) 11\nD) 12"
                ),
                height=150,
            )
            oc1, oc2, oc3 = st.columns([1, 1, 1])
            with oc1:
                option_number = st.text_input("Numero da questao", placeholder="1011")
            with oc2:
                option_from_base = st.selectbox(
                    "Base original",
                    options=list(BASES.keys()),
                    index=1,
                    key="option_from_base",
                )
            with oc3:
                option_to_base = st.selectbox(
                    "Converter para",
                    options=list(BASES.keys()),
                    index=0,
                    key="option_to_base",
                )

            if st.button("Resolver alternativa"):
                try:
                    conversion = convert_base(option_number, option_from_base, option_to_base)
                    option = find_matching_option(option_question, conversion["result"])
                    st.success(f"Resultado calculado: {conversion['result']}")
                    st.code(conversion["steps"], language="text")
                    if option:
                        st.info(f"Alternativa correspondente: {option}")
                    else:
                        st.warning("Nao encontrei uma alternativa que bata exatamente com o resultado.")
                except Exception as exc:
                    st.error(f"Erro ao resolver: {exc}")

        with gates_tab:
            gate = st.selectbox("Porta logica", options=["AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR"])
            gc1, gc2 = st.columns(2)
            with gc1:
                input_a = st.selectbox("Entrada A", options=[0, 1])
            with gc2:
                input_b = st.selectbox("Entrada B", options=[0, 1], disabled=gate == "NOT")

            if st.button("Calcular porta"):
                try:
                    result = logic_gate_result(gate, input_a, None if gate == "NOT" else input_b)
                    st.success(f"Saida: {result}")
                    table = truth_table(gate)
                    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
                except Exception as exc:
                    st.error(f"Erro na porta logica: {exc}")


if __name__ == "__main__":
    main()
