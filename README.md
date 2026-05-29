# Chat offline com meus materiais

Sistema local em Python para estudar com PDFs, arquivos TXT e materiais baixados por tema ou URL.

O app nao usa OpenAI API nem qualquer modelo externo. As respostas sao geradas localmente por busca TF-IDF com `scikit-learn` e sintese extrativa dos trechos encontrados.

## Estrutura

```text
app.py
requirements.txt
README.md
data/
  uploads/
  processed/
utils/
  answer_generator.py
  material_manager.py
  pdf_reader.py
  search.py
  theme_downloader.py
```

## Instalar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Rodar

```powershell
streamlit run app.py
```

Se o comando `streamlit` nao for reconhecido:

```powershell
python -m streamlit run app.py
```

## Funcionalidades

- Upload de PDF e TXT.
- Extracao de texto com `pypdf`.
- Salvamento dos arquivos originais em `data/uploads`.
- Salvamento dos textos processados em `data/processed`.
- Busca por palavra-chave.
- Perguntas respondidas apenas com base nos materiais selecionados.
- Exibicao dos trechos usados como referencia.
- Filtro por tipo de material: PDF, TXT ou tema baixado.
- Separacao por materia, com escolha da materia antes de estudar.
- Selecao de arquivos especificos para responder.
- Exclusao de materiais salvos.
- Movimento de materiais entre materias.
- Download por tema usando Wikipedia e dominios confiaveis.
- Download manual por URL.
- Dominios extras permitidos, configurados pela interface.
- Modos de estudo: Resposta, Resumo, Flashcards e Simulado.
- Calculadora offline de conversao de bases.
- Resolucao de alternativas simples por resultado calculado.
- Tabela verdade e saida de portas logicas.

## Baixar materiais por tema

Primeiro escolha a materia na barra lateral. Depois use **Baixar por tema**:

1. Digite um tema por linha.
2. Escolha quantas paginas baixar por tema.
3. Marque Wikipedia e/ou outras fontes confiaveis.
4. Se quiser, adicione dominios extras permitidos.
5. Clique em **Baixar e armazenar temas**.

O app usa internet apenas nessa etapa de coleta. Depois que o material e salvo, as perguntas funcionam offline.

## Materias

Na barra lateral, escolha em **Entrar na materia** qual materia quer estudar. Todos os filtros, perguntas, resumos e simulados passam a usar apenas os materiais daquela materia.

Para criar uma materia nova, selecione **Nova materia** e digite o nome. O proximo PDF, TXT, tema ou URL baixado sera salvo nessa materia.

Materiais antigos sem materia ficam em **Geral**. Use **Gerenciar materiais** para mover um arquivo para outra materia.

## Baixar por URL

Use **Baixar por URL** quando voce ja souber quais paginas quer salvar.

Por seguranca, a URL precisa estar em um dominio permitido. Para liberar um novo site, adicione o dominio no campo **Dominios extras permitidos**.

## Observacoes

- PDFs escaneados como imagem podem nao retornar texto, pois OCR nao foi incluido.
- O Google nao e usado diretamente porque automacao de resultados do Google normalmente exige API propria ou pode ser bloqueada.
- As respostas sao extrativas: o app reorganiza frases dos seus materiais, evitando inventar conteudo fora das fontes salvas.
- Para baixar temas novos, precisa de internet. Para consultar materiais ja salvos, nao precisa.
- A calculadora de bases e portas logicas nao depende dos PDFs; ela usa regras fixas para ajudar em questoes de calculo.
