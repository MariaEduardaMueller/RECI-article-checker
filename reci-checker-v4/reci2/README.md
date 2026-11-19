# reci-checker (checklist “texto dois”)

Confere manuscritos **Word (.docx)** da RECI contra o novo Checklist (`resources/Checklist_modelo.docx`).
PDF e outros formatos **não** são aceitos (a revista só recebe Word). Detecção de plágio fica fora (outro software).

## Uso
```bash
pip install -r requirements.txt
python src/main.py manuscrito.docx folha_de_rosto.docx --anexos pasta_anexos --id 21508 --saida relatorios
# opções: --sem-llm (Métodos por palavras-chave) | --modelo qwen2.5:7b-instruct | --modelo-checklist outro_modelo.docx
```

## O que é gerado (em `--saida`)
| Arquivo | Conteúdo |
|---|---|
| `<nome>_checklist.docx` | O próprio Checklist da RECI preenchido (X colorido por status), com as alterações abaixo e os links “Clique aqui para baixar: …” preservados. Cada comentário indica **seção e nº do parágrafo** a corrigir. |
| `<nome>_checklist.json` | Mesmos resultados, mais a lista de comentários por trecho. |
| `<nome>_comentado.docx` | Cópia do artigo **com comentários do Word** ancorados nos trechos a alterar. O texto não é modificado (conferido em teste). |

## Alterações em relação ao Checklist-modelo
* Citações numéricas: sobrescritas, **ao final da frase (após o ponto)** — não precisa ser ao final do parágrafo.
* Resumos: **máximo 256 palavras**.
* Referências: **sem “Disponível em:”/“Available from/at:”/“Acesso em”** — somente o link (e o link deve estar em hiperlink).
* A seção “Contribuição dos autores” **não é mais cobrada**.
* **CEP, protocolo/data e CAAE**: exigidos nos Métodos, exceto se o texto declarar a dispensa (ex.: “dispensado do número do CAAE”, “dados de domínio público”). Dispensa do CAAE/número não dispensa o parecer; dispensa de apreciação ética dispensa tudo (itens ficam “Não se aplica”).
* Termos: **Covid-19, HIV, Aids** (conforme o novo modelo).

## Itens novos do Checklist implementados
espaçamento 1,5 nos títulos das seções · recuo de 1,5 cm · idioma do 1º título = idioma do texto · sem citação de autores nos resumos (e por seção) ·
menções a tabelas/figuras só entre parênteses ao final do parágrafo · N (%) na mesma coluna e sem “%” · siglas abaixo da tabela (fonte 10) · sem linha de total ·
figura centralizada · gráficos em tom azul (amostragem de pixels) · legendas de gráficos **abaixo** · e-mail **e endereço** do autor correspondente · >6 autores → 3 + et al · designação familiar (Neto, Júnior…).

## Limites
Itens que exigem julgamento humano saem como “Verificar manualmente” (ortografia, DeCS, clareza, sequência lógica, comparação com a literatura, título na plataforma).
Métodos/ética/siglas/origem das referências usam heurísticas (palavras-chave, idioma do título): revise os “NA”/“AP” antes de enviar ao autor.
O número de linha do Word não é calculável fora do Word; os comentários trazem seção + nº do parágrafo + trecho.

## Revisão por IA (Ollama)
Itens que eram "verificar manualmente" agora são avaliados por IA quando o Ollama está ativo: Introdução breve, objetividade dos Métodos,
sequência dos Resultados, comparação com a literatura, conclusão x objetivos, clareza do título, descritores (DeCS), clareza das tabelas,
abreviação dos periódicos e **ortografia** (com comentários no trecho). Respostas marcadas com `[IA]`; onde o código já avaliava, a IA só rebaixa A→AP.
Sem Ollama nada quebra: os itens continuam manuais. Opções: `--modelo qwen2.5:7b-instruct` (ou outro), `--sem-llm`, `--sem-ortografia`.
Continuam manuais por natureza: título na plataforma, ineditismo e conteúdo/assinatura dos anexos.

## Site (local ou Render)
O usuário envia **somente o manuscrito (.docx)**. Folha de rosto, anexos, plágio e cadastro do título na plataforma ficam fora do escopo (status "Fora do escopo",
sem marcação no Checklist). A IA vem **desligada por padrão**: sem ela, os itens de julgamento são respondidos por código (`src/heuristics.py`,
comentários marcados com `[código]`), então o resultado não traz itens em "verificar manualmente".

### Rodar localmente
```bash
pip install -r requirements.txt
python web/app.py          # ou iniciar_site.bat (Windows) / ./iniciar_site.sh
```
Abre `http://127.0.0.1:5000`. Para usar a IA, mantenha o Ollama aberto com o modelo (`ollama pull llama3.2:3b`) e marque "Também verificar com IA".

### Publicar no Render (gratuito)
1. Coloque a pasta do projeto num repositório do GitHub (inclua `resources/Checklist_modelo.docx`).
2. No Render: **New + > Blueprint** (usa o `render.yaml`) ou **New + > Web Service** com:
   Build `pip install -r requirements.txt` · Start `gunicorn --chdir web app:app --workers 1 --threads 4 --timeout 300 --bind 0.0.0.0:$PORT` ·
   Health check `/healthz` · variável `PYTHON_VERSION=3.12.7`.
3. Defina a variável **`SITE_PASSWORD`** (usuário `reci`): sem ela o site fica aberto a qualquer pessoa. Os manuscritos são inéditos.
4. Limites do plano gratuito: 512 MB de RAM e 0,1 CPU; o serviço **dorme após 15 min sem uso** (o primeiro acesso demora ~1 min); disco temporário (os arquivos
   somem ao reiniciar; a limpeza automática apaga após 2 h). **Não há IA no Render gratuito**: a opção fica desabilitada e o site usa só regras de código.
   Se apontar `OLLAMA_HOST` para um Ollama seu, a opção é habilitada.

## Idiomas: português, inglês e espanhol
Os artigos podem estar em português, inglês ou espanhol. O idioma é detectado pelo texto (`common.work_lang`) e as regras acompanham:
legendas (Tabela/Table/Tabla, Figura/Figure, Gráfico/Chart), objetivo ("aim … to", "objetivo … infinitivo"), Métodos, ética (ethics committee/IRB, datas em inglês e espanhol),
limitações, itálico de termos estrangeiros (em inglês, termos ingleses não são "estrangeiros") e ordem dos resumos (o primeiro deve ser o do idioma do artigo).

## Pontos em aberto (ajustáveis em `src/common.py`)
* `REQUIRE_LEFT_ALIGN_ABSTRACTS = False`: resumo/descritores justificados aparecem só como *observação*, sem reprovar (aguarda confirmação da coordenação).
* `ALLOW_CITE_AFTER_COMMA = True`: citação logo após vírgula/ponto e vírgula é aceita; no meio da frase continua sendo apontada.
* O limite de 15 palavras vale para o **título principal**; as traduções não têm limite próprio.
* Referências institucionais (ex.: "Brasil. Ministério da Saúde."), legislação, manuais, teses e livros não exigem DOI nem "Sobrenome Iniciais".
* "Comparação com a literatura" (Discussão) fica para o revisor: o código só informa indícios.
