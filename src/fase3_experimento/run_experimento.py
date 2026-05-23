"""
Fase 3 — Runner do experimento de desambiguação

Para cada puzzle do dataset, executa dois modos:
  - baseline: LLM sem contexto ontológico
  - ontologia: LLM com contexto RAG da ontologia

Avalia com precisão, revocação e F1 por modo e por subgrupo
(setor não-financeiro / financeiro / outros).
"""

import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
DATA_DIR = OUTPUT_DIR / "fase3"
ONTOLOGIA_PATH = OUTPUT_DIR / "fase1" / "ontologia_base.json"
RESULTADO_PATH = DATA_DIR / "resultados.jsonl"
METRICAS_PATH = DATA_DIR / "metricas.json"

MODEL = "llama3.1:8b"
MAX_TOKENS = 32
MAX_WORKERS = 2

# Amostra para desenvolvimento; None = dataset completo
LIMITE_AMOSTRAS = None


def carregar_ontologia() -> dict:
    with open(ONTOLOGIA_PATH, encoding="utf-8") as file:
        return json.load(file)


def montar_contexto_ontologia(ont: dict) -> str:
    sinonimos = "\n".join(f"  - {s}" for s in ont["sinonimos"])
    return (
        "ONTOLOGIA DE DOMÍNIO — RECEITA BRUTA\n"
        f"Conceito canônico: {ont['conceito_canonico']}\n"
        f"Código CVM: {ont['codigo_cvm']}\n"
        "Descrições reconhecidas como sinônimos de Receita Bruta:\n"
        f"{sinonimos}\n\n"
        "Conceitos adjacentes que NÃO são Receita Bruta:\n"
        "  - Resultado Bruto (= lucro bruto após dedução do CPV, código 3.03)\n"
        "  - Receita Líquida (= receita após deduções fiscais e devoluções)\n"
        "  - Custo dos Bens e/ou Serviços Vendidos\n"
        "  - Despesas da Intermediação Financeira\n"
    )


def prompt_baseline(contas: list[str]) -> str:
    lista = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(contas))
    return (
        "Você é um especialista em contabilidade brasileira.\n"
        "A seguir estão as descrições das contas de uma DRE consolidada.\n"
        "Identifique qual delas representa a RECEITA BRUTA da empresa "
        "(o faturamento total antes de qualquer dedução).\n\n"
        f"Contas:\n{lista}\n\n"
        "Responda APENAS com o texto exato de uma das contas listadas acima, "
        "sem explicações adicionais."
    )


def prompt_com_ontologia(contas: list[str], contexto_ont: str) -> str:
    lista = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(contas))
    return (
        f"{contexto_ont}\n"
        "---\n"
        "Usando a ontologia acima, identifique qual das contas abaixo representa "
        "a RECEITA BRUTA da empresa.\n\n"
        f"Contas:\n{lista}\n\n"
        "Responda APENAS com o texto exato de uma das contas listadas acima, "
        "sem explicações adicionais."
    )


def chamar_llm(client: OpenAI, prompt: str) -> str:
    resposta = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    primeira_resposta = resposta.choices[0].message.content.strip()
    return primeira_resposta.splitlines()[0].strip()


def normalizar(texto: str) -> str:
    texto = texto.lower().strip().rstrip(".")
    texto = re.sub(r"^\d+\.\s*", "", texto)
    texto = re.sub(r"^conta:\s*", "", texto)
    return texto


def processar_puzzle(client: OpenAI, puzzle: dict, contexto_ont: str) -> dict:
    contas = puzzle["contas_ds"]
    gt = puzzle["receita_bruta_gt"]
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_base = ex.submit(chamar_llm, client, prompt_baseline(contas))
        fut_ont = ex.submit(chamar_llm, client, prompt_com_ontologia(contas, contexto_ont))
        pred_base = fut_base.result()
        pred_ont = fut_ont.result()
    return {
        "cnpj": puzzle["cnpj"],
        "empresa": puzzle["empresa"],
        "gt": gt,
        "pred_baseline": pred_base,
        "pred_ontologia": pred_ont,
        "acerto_baseline": normalizar(pred_base) == normalizar(gt),
        "acerto_ontologia": normalizar(pred_ont) == normalizar(gt),
    }


def eh_financeiro(gt: str) -> bool:
    return "Intermediação" in gt or "Seguradoras" in gt


class ContadorMetricas:
    def __init__(self):
        self._grupos = {
            "geral":              {"acertos_base": 0, "acertos_ont": 0, "total": 0},
            "nao_financeiro":     {"acertos_base": 0, "acertos_ont": 0, "total": 0},
            "financeiro_seguros": {"acertos_base": 0, "acertos_ont": 0, "total": 0},
        }

    def atualizar(self, resultado: dict) -> None:
        grupo = "financeiro_seguros" if eh_financeiro(resultado["gt"]) else "nao_financeiro"
        for g in ("geral", grupo):
            c = self._grupos[g]
            c["total"] += 1
            c["acertos_base"] += resultado["acerto_baseline"]
            c["acertos_ont"] += resultado["acerto_ontologia"]

    def to_dict(self) -> dict:
        metricas: dict = {"baseline": {}, "ontologia": {}}
        for grupo, c in self._grupos.items():
            if c["total"] == 0:
                continue
            metricas["baseline"][grupo] = {
                "acertos": c["acertos_base"],
                "total": c["total"],
                "acuracia": round(c["acertos_base"] / c["total"], 4),
            }
            metricas["ontologia"][grupo] = {
                "acertos": c["acertos_ont"],
                "total": c["total"],
                "acuracia": round(c["acertos_ont"] / c["total"], 4),
            }
        return metricas


def main():
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    ont = carregar_ontologia()
    contexto_ont = montar_contexto_ontologia(ont)

    puzzles = []
    with open(DATA_DIR / "dataset_disambiguacao.jsonl", encoding="utf-8") as f:
        for linha in f:
            puzzles.append(json.loads(linha))

    if LIMITE_AMOSTRAS:
        from collections import Counter
        contagem = Counter(p["receita_bruta_gt"] for p in puzzles)
        selecionados = []
        visto: dict[str, int] = defaultdict(int)
        for p in puzzles:
            gt = p["receita_bruta_gt"]
            quota = max(1, round(LIMITE_AMOSTRAS * contagem[gt] / len(puzzles)))
            if visto[gt] < quota:
                selecionados.append(p)
                visto[gt] += 1
            if len(selecionados) >= LIMITE_AMOSTRAS:
                break
        puzzles = selecionados

    print(f"Rodando experimento em {len(puzzles)} puzzles com modelo {MODEL} (workers={MAX_WORKERS})...")

    contador = ContadorMetricas()
    concluidos = 0

    with open(RESULTADO_PATH, "w", encoding="utf-8") as f_out:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(processar_puzzle, client, p, contexto_ont): p for p in puzzles}
            for fut in as_completed(futures):
                resultado = fut.result()
                f_out.write(json.dumps(resultado, ensure_ascii=False) + "\n")
                f_out.flush()
                contador.atualizar(resultado)
                concluidos += 1
                if concluidos % 20 == 0:
                    print(f"  {concluidos}/{len(puzzles)} processados")

    metricas = contador.to_dict()
    with open(METRICAS_PATH, "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)

    print("\n=== MÉTRICAS ===")
    for modo, grupos in metricas.items():
        print(f"\n[{modo.upper()}]")
        for grupo, vals in grupos.items():
            print(f"  {grupo}: {vals['acertos']}/{vals['total']} = {vals['acuracia']:.1%}")

    print(f"\nResultados salvos em {RESULTADO_PATH}")
    print(f"Métricas salvas em {METRICAS_PATH}")


if __name__ == "__main__":
    main()
