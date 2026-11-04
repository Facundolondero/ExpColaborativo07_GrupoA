"""Vigilante: sube a Kaggle las corridas del Experimento 07 a medida que van terminando.

Desde el 29-oct sube solo los 6 cortes de 800 a 1300 de a 100 (ver exp07_subir.py).
Cada ciclo (default: cada 15 minutos):
  1. busca archivos pendientes (no registrados como OK en envios_log.csv)
  2. consulta el cupo del dia en Kaggle y sube hasta (cupo - reserva), en el orden
     semilla -> variante -> corte, con 30 s entre envios (misma logica que exp07_subir.py)
  3. duerme; termina solo cuando las 40 corridas estan listas y todo subido

  python exp07_vigilar.py                 corre hasta terminar todo
  python exp07_vigilar.py --una-vez       hace un solo ciclo y termina
  python exp07_vigilar.py --semillas 150001 222247   solo esas semillas (p. ej. si el companero sube las otras)

Para frenarlo: crear un archivo llamado DETENER_vigilar.txt en esta carpeta (lo mira en cada ciclo
y entre envio y envio). El PID queda en vigilar_pid.txt. Todo lo que hace lo escribe en vigilar_log.txt.
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import exp07_subir  # noqa: E402

TOTAL_CORRIDAS = 40          # 4 variantes x 10 semillas
DETENER = BASE / "DETENER_vigilar.txt"
LOG = BASE / "vigilar_log.txt"


def log(msg):
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")


def hay_que_parar():
    return DETENER.exists()


def ciclo(args):
    """Un ciclo completo. Devuelve True si ya no queda nada por hacer."""
    todos = exp07_subir.listar_archivos()
    ya = exp07_subir.leer_log()
    pendientes = [a for a in todos if a["archivo"].name not in ya]
    if args.semillas:
        pendientes = [a for a in pendientes if a["semilla"] in args.semillas]
    terminadas = len(exp07_subir.corridas_terminadas())

    if not pendientes:
        if terminadas >= TOTAL_CORRIDAS:
            log(f"todo subido: {len(ya)} archivos OK de {terminadas} corridas. Fin.")
            return True
        log(f"nada pendiente por ahora ({terminadas}/{TOTAL_CORRIDAS} corridas terminadas, {len(ya)} archivos OK)")
        return False

    cupo = exp07_subir.cupo_kaggle()
    if cupo is None:
        log("no pude consultar el cupo; espero al proximo ciclo")
        return False
    permitidos, hoy = cupo
    tope = max(0, permitidos - args.reserva)
    if tope == 0:
        log(f"sin cupo por hoy ({hoy} hechos, {permitidos} permitidos, reserva {args.reserva}); "
            f"{len(pendientes)} pendientes; se renueva a las 21:00")
        return False

    a_subir = pendientes[:tope]
    log(f"{len(pendientes)} pendientes, cupo {permitidos} (reserva {args.reserva}): subo {len(a_subir)}")
    errores_seguidos = 0
    for i, a in enumerate(a_subir, 1):
        if hay_que_parar():
            log("encontre DETENER_vigilar.txt: paro")
            sys.exit(0)
        mensaje = exp07_subir.mensaje_de(a)
        ok, detalle = exp07_subir.subir_uno(a["archivo"], mensaje)
        exp07_subir.anotar_log({
            "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "archivo": a["archivo"].name, "variante": a["variante"], "semilla": a["semilla"],
            "envios": a["envios"], "mensaje": mensaje,
            "resultado": "OK" if ok else "ERROR", "detalle": detalle})
        log(f"[{i}/{len(a_subir)}] {'OK   ' if ok else 'ERROR'} {a['archivo'].name} {'' if ok else detalle}")
        errores_seguidos = 0 if ok else errores_seguidos + 1
        if errores_seguidos >= 3:
            log("tres errores seguidos: corto este ciclo y espero al proximo")
            return False
        if i < len(a_subir):
            time.sleep(args.espera)
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--una-vez", action="store_true", help="un solo ciclo")
    ap.add_argument("--semillas", nargs="*", type=int, help="solo estas semillas")
    ap.add_argument("--reserva", type=int, default=10, help="envios del dia que NO usa (default 10)")
    ap.add_argument("--espera", type=int, default=30, help="segundos entre envios (default 30)")
    ap.add_argument("--intervalo", type=int, default=15, help="minutos entre ciclos (default 15)")
    args = ap.parse_args()

    (BASE / "vigilar_pid.txt").write_text(str(os.getpid()))
    if DETENER.exists():
        DETENER.unlink()
    log(f"vigilante iniciado (pid {os.getpid()}, reserva {args.reserva}, cada {args.intervalo} min"
        f"{', semillas ' + str(args.semillas) if args.semillas else ''})")
    while True:
        try:
            listo = ciclo(args)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            log(f"error en el ciclo: {e!r}; sigo en el proximo")
            listo = False
        if listo or args.una_vez:
            break
        for _ in range(args.intervalo * 6):   # duermo de a 10 s para poder frenar rapido
            if hay_que_parar():
                log("encontre DETENER_vigilar.txt: paro")
                return
            time.sleep(10)


if __name__ == "__main__":
    main()
