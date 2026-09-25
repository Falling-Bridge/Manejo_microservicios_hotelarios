"""
Experimento Competencia 6 — Latencia con vs sin caché.

Hipótesis:
    La caché Redis reduce el p95 de latencia de GET /v1/disponibilidad/{fecha}
    en al menos 60% respecto a sin caché, para consultas repetidas sobre la
    misma fecha.

Uso:
    python medir_latencia.py sin    # cuando CACHE_ENABLED=false en docker-compose.yml
    python medir_latencia.py con    # cuando CACHE_ENABLED=true

Salida:
    resultados_sin_cache.csv  o  resultados_con_cache.csv
"""
import csv
import os
import statistics
import sys
import time

import requests

API = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "clave-demo-123")
FECHA = "2026-02-01"
N = 2000          # peticiones medidas por repetición
WARMUP = 10      # peticiones descartadas al inicio de cada repetición
REPETICIONES = 3


def una_peticion(url, headers):
    t0 = time.perf_counter()
    r = requests.get(url, headers=headers)
    dt = (time.perf_counter() - t0) * 1000.0  # ms
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
    return dt


def medir_repeticion(url, headers):
    lats = []
    for i in range(N + WARMUP):
        dt = una_peticion(url, headers)
        if i >= WARMUP:
            lats.append(dt)
    return lats


def percentil(data, p):
    data = sorted(data)
    return data[min(len(data) - 1, int(len(data) * p))]


def resumir(lats):
    return {
        "p50":  round(statistics.median(lats), 3),
        "p95":  round(percentil(lats, 0.95), 3),
        "p99":  round(percentil(lats, 0.99), 3),
        "mean": round(statistics.mean(lats), 3),
        "min":  round(min(lats), 3),
        "max":  round(max(lats), 3),
    }


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("sin", "con"):
        print("Uso: python medir_latencia.py {sin|con}")
        sys.exit(1)

    fase = f"{sys.argv[1]}_cache"
    url = f"{API}/v1/disponibilidad/{FECHA}"
    headers = {"X-API-Key": API_KEY}

    # Verifica que la API responda antes de arrancar
    try:
        una_peticion(url, headers)
    except Exception as e:
        print(f"ERROR: la API no responde en {url}: {e}")
        print("Verifica que 'docker compose up -d' esté corriendo.")
        sys.exit(1)

    print(f"Fase: {fase}")
    print(f"URL: {url}")
    print(f"Peticiones por repetición: {N} (+ {WARMUP} de warm-up)")
    print(f"Repeticiones: {REPETICIONES}\n")

    filas = []
    for rep in range(1, REPETICIONES + 1):
        print(f"  Repetición {rep}/{REPETICIONES}...", end=" ", flush=True)
        lats = medir_repeticion(url, headers)
        r = resumir(lats)
        print(f"p50={r['p50']:.2f}  p95={r['p95']:.2f}  p99={r['p99']:.2f}  media={r['mean']:.2f} ms")
        filas.append({"fase": fase, "repeticion": rep, **r})

    archivo = f"resultados_{fase}.csv"
    with open(archivo, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    # Promedio de las 3 repeticiones
    prom = {k: statistics.mean(fila[k] for fila in filas)
            for k in ("p50", "p95", "p99", "mean", "min", "max")}
    print(f"\nPromedio {fase}:")
    print(f"  p50  = {prom['p50']:.2f} ms")
    print(f"  p95  = {prom['p95']:.2f} ms")
    print(f"  p99  = {prom['p99']:.2f} ms")
    print(f"  media= {prom['mean']:.2f} ms")
    print(f"\nEscrito: {archivo}")


if __name__ == "__main__":
    main()