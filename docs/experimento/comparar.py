"""
Compara los resultados de las dos fases y genera:
  - Tabla en consola
  - comparacion.csv  (tabla lista para el informe)
  - grafico_latencia.png

Uso:
    python comparar.py
"""
import csv
import statistics

import matplotlib
matplotlib.use("Agg")  # sin ventana
import matplotlib.pyplot as plt


def leer_promedios(archivo):
    with open(archivo) as f:
        filas = list(csv.DictReader(f))
    return {
        k: statistics.mean(float(fila[k]) for fila in filas)
        for k in ("p50", "p95", "p99", "mean")
    }


def main():
    sin = leer_promedios("resultados_sin_cache.csv")
    con = leer_promedios("resultados_con_cache.csv")

    # ----- Tabla -----
    metricas = ["p50", "p95", "p99", "mean"]
    print(f"{'Métrica':8s} | {'Sin caché':>10s} | {'Con caché':>10s} | {'Mejora':>8s}")
    print("-" * 48)
    filas_csv = []
    for m in metricas:
        s, c = sin[m], con[m]
        mejora = (s - c) / s * 100 if s > 0 else 0
        print(f"{m:8s} | {s:10.2f} | {c:10.2f} | {mejora:7.1f}%")
        filas_csv.append({"metrica": m, "sin_cache_ms": round(s, 2),
                          "con_cache_ms": round(c, 2), "mejora_pct": round(mejora, 2)})

    with open("comparacion.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metrica", "sin_cache_ms", "con_cache_ms", "mejora_pct"])
        w.writeheader()
        w.writerows(filas_csv)
    print("\nEscrito: comparacion.csv")

    # ----- Gráfico -----
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(metricas))
    ancho = 0.35
    ax.bar([i - ancho/2 for i in x], [sin[m] for m in metricas],
           ancho, label="Sin caché", color="#d9534f")
    ax.bar([i + ancho/2 for i in x], [con[m] for m in metricas],
           ancho, label="Con caché", color="#5cb85c")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["p50", "p95", "p99", "media"])
    ax.set_ylabel("Latencia (ms)")
    ax.set_title("Latencia de GET /v1/disponibilidad/{fecha}\ncon y sin caché Redis")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig("grafico_latencia.png", dpi=150)
    print("Escrito: grafico_latencia.png")


if __name__ == "__main__":
    main()