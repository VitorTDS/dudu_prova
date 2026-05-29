import re


def split_sentences(text: str) -> list[str]:
    """Divide um trecho em frases legiveis."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def important_terms(question: str) -> set[str]:
    """Extrai termos uteis da pergunta para selecionar frases relevantes."""
    stopwords = {
        "a",
        "ao",
        "aos",
        "as",
        "com",
        "como",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "essa",
        "esse",
        "esta",
        "este",
        "o",
        "os",
        "ou",
        "para",
        "por",
        "quais",
        "qual",
        "que",
        "sobre",
        "um",
        "uma",
    }
    words = re.findall(r"\w+", question.lower())
    return {word for word in words if len(word) > 2 and word not in stopwords}


def sentence_score(sentence: str, terms: set[str]) -> int:
    """Pontua uma frase pela quantidade de termos da pergunta encontrados nela."""
    sentence_words = set(re.findall(r"\w+", sentence.lower()))
    return len(sentence_words.intersection(terms))


def select_relevant_sentences(references: list[dict], question: str = "", limit: int = 8) -> list[str]:
    """Seleciona frases relevantes e remove repeticoes simples."""
    terms = important_terms(question)
    candidates = []

    for reference in references:
        for sentence in split_sentences(reference.get("chunk", "")):
            if len(sentence) < 35:
                continue
            score = sentence_score(sentence, terms) + reference.get("score", 0)
            candidates.append({"sentence": sentence, "score": score})

    ordered = sorted(candidates, key=lambda item: item["score"], reverse=True)
    selected = []
    seen = set()

    for item in ordered:
        normalized = re.sub(r"\W+", " ", item["sentence"].lower()).strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append(item["sentence"])
        if len(selected) >= limit:
            break

    return selected


def generate_answer(question: str, references: list[dict], max_sentences: int = 6) -> str:
    """
    Gera uma resposta baseada apenas nos trechos recuperados.

    Sem modelo externo, a resposta e uma sintese extrativa: ela seleciona
    frases dos materiais que melhor combinam com a pergunta.
    """
    if not references:
        return (
            "Nao encontrei informacoes suficientes nos arquivos selecionados para "
            "responder. Tente usar termos que aparecem nos seus materiais."
        )

    selected = select_relevant_sentences(references, question, limit=max_sentences)
    if not selected:
        return (
            "Encontrei trechos relacionados, mas eles nao trazem uma resposta direta. "
            "Confira as referencias abaixo para avaliar o conteudo disponivel."
        )

    answer_body = " ".join(selected)
    return (
        "Com base nos materiais selecionados, a resposta mais provavel e:\n\n"
        f"{answer_body}\n\n"
        "Observacao: esta resposta foi montada somente a partir dos trechos "
        "encontrados nos seus arquivos, sem uso de internet ou API externa."
    )


def generate_summary(references: list[dict], question: str = "") -> str:
    """Gera um resumo em topicos a partir dos trechos recuperados."""
    sentences = select_relevant_sentences(references, question, limit=7)
    if not sentences:
        return "Nao encontrei trechos suficientes para gerar um resumo."

    lines = ["Resumo com base nos materiais selecionados:"]
    lines.extend(f"- {sentence}" for sentence in sentences)
    return "\n".join(lines)


def generate_flashcards(references: list[dict], question: str = "", limit: int = 6) -> str:
    """Cria flashcards simples usando frases dos materiais."""
    sentences = select_relevant_sentences(references, question, limit=limit)
    if not sentences:
        return "Nao encontrei trechos suficientes para gerar flashcards."

    cards = []
    for index, sentence in enumerate(sentences, start=1):
        words = re.findall(r"\w+", sentence)
        key_terms = [word for word in words if len(word) > 6]
        focus = key_terms[0] if key_terms else "este ponto"
        cards.append(f"{index}. Pergunta: O que o material afirma sobre {focus}?\nResposta: {sentence}")

    return "\n\n".join(cards)


def generate_quiz(references: list[dict], question: str = "", limit: int = 5) -> str:
    """Gera um simulado simples de verdadeiro ou falso."""
    sentences = select_relevant_sentences(references, question, limit=limit)
    if not sentences:
        return "Nao encontrei trechos suficientes para gerar um simulado."

    lines = ["Simulado rapido:"]
    for index, sentence in enumerate(sentences, start=1):
        lines.append(f"{index}. Verdadeiro ou falso: {sentence}")

    lines.append("\nGabarito: todas as afirmativas acima foram retiradas dos materiais selecionados.")
    return "\n".join(lines)
