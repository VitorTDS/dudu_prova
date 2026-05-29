import re


BASES = {
    "Decimal": 10,
    "Binario": 2,
    "Octal": 8,
    "Hexadecimal": 16,
}


def parse_number(value: str, base_name: str) -> int:
    """Converte uma string em inteiro usando a base informada."""
    base = BASES[base_name]
    cleaned = value.strip().replace(" ", "").replace("_", "")
    if not cleaned:
        raise ValueError("Digite um numero para converter.")
    return int(cleaned, base)


def format_number(number: int, base_name: str) -> str:
    """Formata um inteiro na base de saida."""
    if base_name == "Decimal":
        return str(number)
    if base_name == "Binario":
        return bin(number)[2:]
    if base_name == "Octal":
        return oct(number)[2:]
    if base_name == "Hexadecimal":
        return hex(number)[2:].upper()
    raise ValueError("Base de saida invalida.")


def convert_base(value: str, from_base: str, to_base: str) -> dict:
    """Converte um numero entre decimal, binario, octal e hexadecimal."""
    decimal_value = parse_number(value, from_base)
    result = format_number(decimal_value, to_base)
    return {
        "input": value.strip(),
        "from_base": from_base,
        "to_base": to_base,
        "decimal_value": decimal_value,
        "result": result,
        "steps": build_conversion_steps(value.strip(), from_base, to_base, decimal_value, result),
    }


def build_conversion_steps(
    value: str,
    from_base: str,
    to_base: str,
    decimal_value: int,
    result: str,
) -> str:
    """Monta uma explicacao curta do calculo."""
    if from_base == to_base:
        return f"O numero ja esta em {to_base}: {result}."

    lines = [f"Numero informado: {value} em {from_base}."]
    if from_base != "Decimal":
        lines.append(f"Primeiro, convertemos para decimal: {value}({BASES[from_base]}) = {decimal_value}(10).")
    if to_base != "Decimal":
        lines.append(f"Depois, convertemos {decimal_value}(10) para {to_base}: {result}({BASES[to_base]}).")
    else:
        lines.append(f"Resultado em decimal: {decimal_value}.")
    lines.append(f"Resposta final: {result}.")
    return "\n".join(lines)


def logic_gate_result(gate: str, a: int, b: int | None = None) -> int:
    """Calcula a saida de uma porta logica."""
    gate = gate.upper()
    a = 1 if int(a) else 0
    b_value = None if b is None else 1 if int(b) else 0

    if gate == "NOT":
        return 0 if a else 1
    if b_value is None:
        raise ValueError("Essa porta precisa de duas entradas.")
    if gate == "AND":
        return 1 if a and b_value else 0
    if gate == "OR":
        return 1 if a or b_value else 0
    if gate == "NAND":
        return 0 if a and b_value else 1
    if gate == "NOR":
        return 0 if a or b_value else 1
    if gate == "XOR":
        return 1 if a != b_value else 0
    if gate == "XNOR":
        return 1 if a == b_value else 0
    raise ValueError("Porta logica invalida.")


def truth_table(gate: str) -> list[dict]:
    """Gera tabela verdade para uma porta logica."""
    gate = gate.upper()
    if gate == "NOT":
        return [{"A": a, "Saida": logic_gate_result(gate, a)} for a in (0, 1)]

    rows = []
    for a in (0, 1):
        for b in (0, 1):
            rows.append({"A": a, "B": b, "Saida": logic_gate_result(gate, a, b)})
    return rows


def find_matching_option(question_text: str, expected_result: str) -> str | None:
    """Procura uma alternativa que contenha exatamente o resultado calculado."""
    expected = expected_result.strip().upper()
    pattern = re.compile(r"^\s*([A-Ea-e])\s*[\)\.\-:]\s*(.+?)\s*$", re.MULTILINE)

    for match in pattern.finditer(question_text):
        label = match.group(1).upper()
        option_text = match.group(2).strip().upper()
        values = re.findall(r"[0-9A-F]+", option_text)
        if expected in values or option_text == expected:
            return label

    return None
