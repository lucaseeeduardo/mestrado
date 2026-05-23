# Proposta de Pesquisa Acadêmica

## Tema
**Ontologia de Domínio para Desambiguação de Receita Bruta em Documentos Contábeis Heterogêneos:** Uma Abordagem Baseada em Conhecimento para Automação da Análise de Crédito.

---

## Problema de Pesquisa
A extração automatizada de indicadores financeiros em **Demonstrações do Resultado do Exercício (DRE)** enfrenta alta taxa de erro e alucinação devido à variabilidade estrutural e semântica dos documentos contábeis brasileiros. 

No contexto de antecipação de recebíveis, a automação de extração de dados é muito sensível, devido ao risco de crédito. Diante disso:

> **Como aumentar a precisão na identificação e extração do campo "Receita Bruta" em documentos não estruturados através de uma base de referência semântica que mitigue a ambiguidade terminológica?**

---

## Objetivos

### Objetivo Geral
Propor e avaliar um modelo de extração de dados orientado por ontologia (*Ontology-Based Information Extraction*) para a desambiguação semântica do indicador de **"Receita Bruta"** e validação por LLM's em DREs heterogêneas, visando a reconciliação automática de dados financeiros para suporte à decisão em operações de crédito.

### Objetivos Específicos
* **Mapear a Variabilidade Terminológica:** Identificar e catalogar as diferentes nomenclaturas e estruturas hierárquicas utilizadas para referenciar faturamento em uma base de dados real de documentos contábeis brasileiros.
* **Desenvolver a Ontologia de Domínio:** Modelar formalmente as classes, propriedades e relações semânticas do domínio contábil focado em receitas e deduções, utilizando padrões como **OWL (Web Ontology Language)**.
* **Implementar o Pipeline de Extração:** Integrar a ontologia proposta a modelos de linguagem (LLMs) ou técnicas de Processamento de Linguagem Natural (NLP) para guiar a extração de dados através de contexto especializado.
* **Avaliar o desempenho do modelo:** Validar a eficácia da extração por ontologia através de métricas de recuperação de informação, comparando-a com abordagens baseline (ex: LLM sem contexto ontológico).
---

## Metodologia de Pesquisa
A presente pesquisa classifica-se como **aplicada**, com abordagem mista (qualitativa e quantitativa)e o percurso metodológico divide-se em quatro fases:

1.  **Fase Exploratória e Coleta:** Levantamento bibliográfico sobre Engenharia de Ontologias e *Document AI*. Coleta de uma amostra de DREs (anonimizadas) para identificação dos padrões de escrita e termos sinônimos utilizados por diferentes escritórios contábeis.
2.  **Modelagem do Artefato:** Construção da ontologia utilizando o editor **Protégé**, definindo a taxonomia (ex: *Receita Bruta* como classe superior de *Receita de Vendas* e *Receita de Serviços*) e as regras de inferência (ex: $Faturamento Líquido = Receita Bruta - Deduções$).
3.  **Desenvolvimento Experimental:** Implementação de um protótipo em **Python** que utilize a técnica de *Retrieval-Augmented Generation* (RAG) ou *Prompt Engineering* estruturado, onde a ontologia fornece o esquema de validação para a extração realizada por um modelo de linguagem.
4.  **Análise de Resultados:** Teste de estresse do modelo com documentos "sujos" ou propositalmente ambíguos. A validação quantitativa será feita através do cálculo de erro médio entre o valor extraído e o valor real (*Ground Truth*), enquanto a qualitativa avaliará a capacidade do sistema em sinalizar discrepâncias entre a soma dos faturamentos mensais e o total anual do DRE.