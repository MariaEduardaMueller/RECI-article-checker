# RECI-article-checker

Verificador de conformidade de artigos/manunscritos submetidos no site: https://seer.unisc.br/index.php/epidemiologia/issue/archive.



#### Como Executar
```bash
pip install -r requirements.txt
python src/main.py manuscrito.docx folha_de_rosto.docx --anexos pasta_anexos --id 21508 --saida relatorios
# opções: --sem-llm (Métodos por palavras-chave) | --modelo qwen2.5:7b-instruct | --modelo-checklist outro_modelo.docx
```

-----------------
#### Projeto da Bolsa de Iniciação Científica (PROBIC/FAPERGS) - UNISC


<img width="1167" height="376" alt="imagem" src="https://github.com/user-attachments/assets/f269dd31-2ea4-4035-9e13-76e8e07ef101" />
