# reci-checker

Verifica a conformidade de manuscritos (`.docx` **ou** `.pdf`) com o **Checklist da Revista RECI** e gera um relatório
no terminal, em **PDF colorido** (azul = atende, verde = parcial, amarelo = não atende) e em **JSON**.

## Instalação

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python src/main.py manuscrito.docx [folha_de_rosto.docx] [opções]

--anexos PASTA   confere a presença dos documentos obrigatórios (parecer CEP, declarações, avaliadores...)
--sem-llm        não usa o Ollama nos itens 36–42 (Métodos)
--modelo NOME    modelo do Ollama (padrão: qwen2.5:7b-instruct)
--saida PASTA    destino dos relatórios (padrão: ./relatorios)
```

Status: **A** atende · **AP** atende parcialmente · **NA** não atende · **NSA** não se aplica · **-** não verificado.

## Arquitetura

`document_model.py` lê `.docx` e `.pdf` e produz o mesmo modelo (`Document` → parágrafos → runs com negrito, itálico,
tamanho, fonte, sobrescrito; alinhamento e espaçamento; tabelas; imagens). Todas as verificações usam esse modelo,
então a regra é a mesma nos dois formatos. `checklist.py` registra os itens **na ordem e nas seções do Checklist**;
um erro em um item nunca derruba o relatório.

| Formato | O que é exato | O que é estimado |
|---|---|---|
| `.docx` | tudo (herança de estilos, espaçamento, bordas de tabelas, DPI das imagens) | — |
| `.pdf` | texto, fonte, tamanho, negrito, itálico, sobrescrito, imagens | alinhamento, espaçamento, divisão de parágrafos; tabelas/bordas/edição (itens 58, 128, 129 ficam "-") |

O item 13 reprova PDF por definição (a revista exige Word `.docx`), mas todo o resto é verificado.

## Itens

| Seção do Checklist | Itens |
|---|---|
| Categoria | 100 (10–25 referências dos últimos 5 anos) |
| Metadados | 1, 2, 3, 4, 5 |
| Documentos obrigatórios | 101–106 (por nome de arquivo, com `--anexos`) |
| Folha de rosto | 109, 10, 107 (e-mail), 108 (rede social), 11 |
| Formatação geral | 12, 13, 14, 110 (itálico em termos estrangeiros), 16, 111 (seções à esquerda), 18 |
| Títulos | 19, 23, 20, 21, 112 (só a 1ª letra maiúscula) |
| Resumos / Descritores | 113, 24–28 / 30–33 |
| Introdução | 114 (objetivo no último parágrafo, verbo no infinitivo), 115 (idêntico ao resumo) |
| Método | 36–42 (Ollama), 116 |
| Aspectos éticos | 117 (CEP), 118 (Res. 466/510/580), 119 (protocolo e data), 120 (CAAE) |
| Resultados | 121 (numeração), 122 (citadas no texto) |
| Discussão / Conclusão | 123, 124 (limitações no penúltimo parágrafo), 53 |
| Siglas | 125 (extenso na 1ª aparição), 126 (COVID-19/HIV/AIDS) |
| Tabelas e figuras | 54, 58, 127, 128, 129, 130 (DPI), 61, 132, 133, 131 |
| Citações no texto | 134 (sobrescrito, fim do parágrafo, sem parênteses), 135 (ordem, hífen, todas citadas) |
| Referências | 66, 136, 69, 137 (≥40% internacionais recentes), 71, 72, 73 |

Itens que dependem de julgamento humano (ortografia, ineditismo, DeCS, abreviação de periódicos...) aparecem no
final do relatório como "verificação manual".

## Correções em relação à versão anterior

- `cli.py` dizia aceitar PDF, mas só aceitava `.docx`; `docx_utils.py` usava `ET` sem importar; dependia de XML despejado em `resources/xml`.
- Item 73 aprovava mais de 3 autores antes de "et al" (o Checklist exige exatamente os três primeiros).
- Item 31 reprovava por separador (`;`), que pertence ao item 33.
- Itens 20/21/69 ignoravam formatação herdada de estilos (falsos negativos) e não checavam negrito indevido nos títulos secundários.
- Item 4 só reconhecia afiliações com palavras-chave fixas e UF por extenso; agora aceita sigla (PR) e outras instituições.
- O LLM recebia o manuscrito inteiro; agora recebe só a seção Métodos, com saída JSON forçada e falha graciosa.
- `nltk` removido (detecção de idioma embutida, funciona offline).

## Testes

`python tests/make_samples.py pasta/` gera um manuscrito correto e outro com erros; `pytest tests/` valida ambos (docx e PDF).

## Limitações conhecidas

Heurísticas: itálico de termos estrangeiros, siglas, objetivo/limitações, idioma das referências (pelo título) e
parágrafos em PDF (títulos centralizados consecutivos longos podem ser unidos). Trate o relatório como triagem, não como
decisão final.
