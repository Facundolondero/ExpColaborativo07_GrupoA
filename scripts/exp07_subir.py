"""Sube a Kaggle los csv de las corridas del Experimento 07 (Grupo A, Gerencial).

Por defecto NO sube nada: muestra el plan de lo que falta subir. Solo sube con --subir.

  python exp07_subir.py                          plan de todo lo pendiente (modo seco)
  python exp07_subir.py --semillas 150001        plan de una semilla
  python exp07_subir.py --semillas 150001 --subir   sube esa semilla (24 archivos)
  python exp07_subir.py --subir --max 88         sube como mucho 88 archivos y para

Desde el 29-oct, a pedido de Denicolay, se suben solo 6 cortes por corrida: los del notebook de a 100
(800 a 1300). Los archivos de los demas cortes quedan en la carpeta kaggle/ de cada corrida pero no se suben.

Orden de subida: semilla por semilla; dentro de cada semilla las 4 variantes; dentro de cada
variante los cortes de menor a mayor. Solo toma corridas terminadas (las que tienen PARAM.yml).

Cada envio queda registrado en envios_log.csv; un archivo registrado como OK no se vuelve a subir,
asi que el script se puede cortar y relanzar. Antes de subir consulta a Kaggle el cupo disponible
del dia (num_allowed_now) y no lo pasa.
"""
import argparse
import csv
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
RUNS = BASE / "runs"
LOG = BASE / "envios_log.csv"
COMPETENCIA = "labo-1-virtual-2026-manager"
ORDEN_VARIANTES = ["V0_todo", "V1_sinASPO", "V2_2021", "V3_ultimos4"]
# las 10 semillas del experimento: 5 de Facundo y 5 de Francisco (cada uno sube las suyas desde su cuenta)
ORDEN_SEMILLAS = [150001, 222247, 199999, 777781, 999983, 101929, 232327, 456791, 454451, 123457]
PATRON = re.compile(r"KA07_(?P<variante>.+)_s(?P<semilla>\d+)_(?P<envios>\d+)\.csv$")
CORTES_A_SUBIR = list(range(800, 1301, 100))
COLUMNAS_LOG = ["fecha_utc", "archivo", "variante", "semilla", "envios", "mensaje", "resultado", "detalle"]


def mensaje_de(a):
    """Mensaje del envio en Kaggle; exp07_bajar_puntajes.py lo usa para reconocer los envios."""
    return f"exp07 {a['variante']} s{a['semilla']} envios={a['envios']}"


def corridas_terminadas():
    return [(v, s) for s in ORDEN_SEMILLAS for v in ORDEN_VARIANTES
            if (RUNS / v / f"s{s}" / "PARAM.yml").exists()]


def listar_archivos():
    """Todos los csv de corridas terminadas, en el orden de subida."""
    archivos = []
    for semilla in ORDEN_SEMILLAS:
        for variante in ORDEN_VARIANTES:
            carpeta = RUNS / variante / f"s{semilla}"
            if not (carpeta / "PARAM.yml").exists():
                continue
            for archivo in sorted((carpeta / "kaggle").glob("KA07_*.csv"),
                                  key=lambda p: int(PATRON.match(p.name)["envios"])):
                m = PATRON.match(archivo.name)
                if int(m["envios"]) not in CORTES_A_SUBIR:
                    continue
                archivos.append({"archivo": archivo, "variante": variante,
                                 "semilla": semilla, "envios": int(m["envios"])})
    return archivos


def leer_log():
    """Nombres de archivo ya subidos con resultado OK."""
    if not LOG.exists():
        return set()
    with LOG.open(newline="", encoding="utf-8") as f:
        return {r["archivo"] for r in csv.DictReader(f) if r["resultado"] == "OK"}


def anotar_log(fila):
    nuevo = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_LOG)
        if nuevo:
            w.writeheader()
        w.writerow(fila)


def cupo_kaggle(timeout=90):
    """Cupo diario que informa Kaggle: (permitidos ahora, hechos hoy). None si no se pudo consultar.
    La consulta corre en un hilo con limite de tiempo: la API de Kaggle no tiene timeout propio y
    una vez dejo colgado al vigilante durante una hora."""
    import threading
    resultado = {}

    def consultar():
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
            api = KaggleApi()
            api.authenticate()
            lim = api.competition_get_submission_limits(COMPETENCIA)
            resultado["cupo"] = (int(lim.num_allowed_now), int(lim.num_today))
        except Exception as e:  # noqa: BLE001
            resultado["error"] = e

    h = threading.Thread(target=consultar, daemon=True)
    h.start()
    h.join(timeout)
    if h.is_alive():
        print(f"  (la consulta del cupo a Kaggle no respondio en {timeout} s)")
        return None
    if "cupo" not in resultado:
        print(f"  (no pude consultar el cupo en Kaggle: {resultado.get('error')})")
        return None
    return resultado["cupo"]


def subir_uno(archivo, mensaje, timeout=180):
    """Un submit con la CLI de Kaggle. Devuelve (ok, detalle)."""
    cmd = ["kaggle", "competitions", "submit", COMPETENCIA, "-f", str(archivo), "-m", mensaje]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        salida = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        # la CLI a veces no termina despues de "Successfully submitted"; me quedo con lo que imprimio
        salida = "".join(str(x or "") for x in (e.stdout, e.stderr)) + " [timeout]"
    salida = " ".join(l for l in salida.splitlines() if "outdated" not in l).strip()
    return ("Successfully submitted" in salida), salida[:300]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subir", action="store_true", help="sube de verdad (sin esto solo muestra el plan)")
    ap.add_argument("--semillas", nargs="*", type=int, help="semillas a subir (default: todas)")
    ap.add_argument("--variantes", nargs="*", help="variantes a subir (default: todas)")
    ap.add_argument("--max", type=int, default=100, help="maximo de archivos a subir en esta corrida (default 100)")
    ap.add_argument("--espera", type=int, default=30, help="segundos entre envios (default 30)")
    args = ap.parse_args()

    todos = listar_archivos()
    ya = leer_log()
    pendientes = [a for a in todos if a["archivo"].name not in ya]
    if args.semillas:
        pendientes = [a for a in pendientes if a["semilla"] in args.semillas]
    if args.variantes:
        pendientes = [a for a in pendientes if a["variante"] in args.variantes]

    print(f"Corridas terminadas: {len(todos)} archivos | ya subidos OK: {len(ya)} | pendientes con los filtros: {len(pendientes)}")
    por_semilla = {}
    for a in pendientes:
        por_semilla.setdefault(a["semilla"], {}).setdefault(a["variante"], 0)
        por_semilla[a["semilla"]][a["variante"]] += 1
    for semilla, d in por_semilla.items():
        print(f"  semilla {semilla}: " + ", ".join(f"{v} x{n}" for v, n in d.items()))

    if not pendientes:
        print("Nada pendiente.")
        return
    if not args.subir:
        print("\nMODO SECO: no se subio nada. Para subir, agregar --subir.")
        return

    cupo = cupo_kaggle()
    tope = args.max
    if cupo is not None:
        permitidos, hoy = cupo
        print(f"Cupo Kaggle: {permitidos} permitidos ahora ({hoy} hechos hoy)")
        tope = min(tope, permitidos)
    a_subir = pendientes[:tope]
    print(f"\nVoy a subir {len(a_subir)} archivos, con {args.espera} s entre envios "
          f"(~{len(a_subir) * (args.espera + 15) / 60:.0f} min)\n")

    errores_seguidos = 0
    for i, a in enumerate(a_subir, 1):
        mensaje = mensaje_de(a)
        ok, detalle = subir_uno(a["archivo"], mensaje)
        anotar_log({"fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "archivo": a["archivo"].name, "variante": a["variante"], "semilla": a["semilla"],
                    "envios": a["envios"], "mensaje": mensaje,
                    "resultado": "OK" if ok else "ERROR", "detalle": detalle})
        print(f"[{i}/{len(a_subir)}] {'OK   ' if ok else 'ERROR'} {a['archivo'].name}  {'' if ok else detalle}")
        errores_seguidos = 0 if ok else errores_seguidos + 1
        if errores_seguidos >= 3:
            print("Tres errores seguidos: paro. Revisar envios_log.csv (cupo agotado, red, kaggle.json).")
            sys.exit(1)
        if i < len(a_subir):
            time.sleep(args.espera)
    print("\nListo. Registro en", LOG.name)


if __name__ == "__main__":
    main()
