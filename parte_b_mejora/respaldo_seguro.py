import hashlib
import hmac
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "datos_clinica")
BACKUP_DIR = os.path.join(BASE_DIR, "boveda_respaldos")
CLAVE_MAESTRA = b"HuellaVet_ClaveSegura_2026!"


def calcular_sha256(ruta_archivo):
    sha256 = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        for bloque in iter(lambda: f.read(4096), b""):
            sha256.update(bloque)
    return sha256.hexdigest()


def cifrar_bytes(datos, clave, salt):
    key = hashlib.pbkdf2_hmac("sha256", clave, salt, 100_000, dklen=32)
    keystream = bytearray()
    contador = 0
    while len(keystream) < len(datos):
        bloque = hashlib.sha256(key + contador.to_bytes(4, "big")).digest()
        keystream.extend(bloque)
        contador += 1
    cifrado = bytes(a ^ b for a, b in zip(datos, keystream[: len(datos)]))
    firma = hmac.new(key, salt + cifrado, hashlib.sha256).digest()
    return salt + firma + cifrado


def descifrar_bytes(paquete, clave):
    salt, firma_guardada, cifrado = paquete[:16], paquete[16:48], paquete[48:]
    key = hashlib.pbkdf2_hmac("sha256", clave, salt, 100_000, dklen=32)
    firma_actual = hmac.new(key, salt + cifrado, hashlib.sha256).digest()
    if not hmac.compare_digest(firma_guardada, firma_actual):
        raise ValueError("ALERTA: El respaldo fue alterado o la clave no coincide.")
    keystream = bytearray()
    contador = 0
    while len(keystream) < len(cifrado):
        bloque = hashlib.sha256(key + contador.to_bytes(4, "big")).digest()
        keystream.extend(bloque)
        contador += 1
    return bytes(a ^ b for a, b in zip(cifrado, keystream[: len(cifrado)]))


def respaldar():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    hashes = {}
    zip_temp = os.path.join(BACKUP_DIR, "temp_huellavet.zip")

    with zipfile.ZipFile(zip_temp, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre in sorted(os.listdir(DATA_DIR)):
            ruta = os.path.join(DATA_DIR, nombre)
            if os.path.isfile(ruta) and nombre.endswith(".csv"):
                hashes[nombre] = calcular_sha256(ruta)
                zf.write(ruta, arcname=nombre)

    with open(zip_temp, "rb") as f:
        paquete_cifrado = cifrar_bytes(f.read(), CLAVE_MAESTRA, os.urandom(16))
    os.remove(zip_temp)

    ruta_enc = os.path.join(BACKUP_DIR, "respaldo_huellavet.enc")
    with open(ruta_enc, "wb") as f:
        f.write(paquete_cifrado)

    manifiesto = {
        "fecha_respaldo": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "archivo_cifrado": "respaldo_huellavet.enc",
        "hashes_sha256": hashes,
    }
    with open(os.path.join(BACKUP_DIR, "manifiesto_sha256.json"), "w", encoding="utf-8") as f:
        json.dump(manifiesto, f, indent=4)

    print("\n=== RESPALDO CIFRADO COMPLETADO ===")
    print(f"Fecha: {manifiesto['fecha_respaldo']}")
    print(f"Boveda: {ruta_enc}")
    for archivo, digest in hashes.items():
        print(f"  [SHA-256] {archivo}: {digest}")


def simular_ransomware():
    print("\n=== SIMULANDO ATAQUE DE RANSOMWARE EN HUELLAVET ===")
    for nombre in sorted(os.listdir(DATA_DIR)):
        ruta = os.path.join(DATA_DIR, nombre)
        if os.path.isfile(ruta) and nombre.endswith(".csv"):
            with open(ruta, "wb") as f:
                f.write(os.urandom(128))
            os.replace(ruta, ruta + ".LOCKED")
            print(f"  [SECUESTRADO] {nombre} -> {nombre}.LOCKED")

    nota = os.path.join(DATA_DIR, "LEEME_RESCATE.txt")
    with open(nota, "w", encoding="utf-8") as f:
        f.write("SUS EXPEDIENTES HAN SIDO CIFRADOS. PAGUE RESCATE PARA RECUPERARLOS.\n")
    print("  [NOTA DE RESCATE] Creada en datos_clinica\\LEEME_RESCATE.txt")


def restaurar():
    print("\n=== INICIANDO RECUPERACION Y VERIFICACION DE INTEGRIDAD ===")
    with open(os.path.join(BACKUP_DIR, "manifiesto_sha256.json"), "r", encoding="utf-8") as f:
        manifiesto = json.load(f)

    with open(os.path.join(BACKUP_DIR, manifiesto["archivo_cifrado"]), "rb") as f:
        datos_zip = descifrar_bytes(f.read(), CLAVE_MAESTRA)
    print("  [OK] Firma HMAC verificada y respaldo descifrado correctamente.")

    for nombre in os.listdir(DATA_DIR):
        os.remove(os.path.join(DATA_DIR, nombre))

    zip_temp = os.path.join(BACKUP_DIR, "restore_temp.zip")
    with open(zip_temp, "wb") as f:
        f.write(datos_zip)
    with zipfile.ZipFile(zip_temp, "r") as zf:
        zf.extractall(DATA_DIR)
    os.remove(zip_temp)

    for archivo, hash_esperado in manifiesto["hashes_sha256"].items():
        hash_actual = calcular_sha256(os.path.join(DATA_DIR, archivo))
        estado = "INTEGRO (100% COINCIDE)" if hash_actual == hash_esperado else "CORRUPTO"
        print(f"  [VERIFICACION SHA-256] {archivo}: {estado}")


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else ""
    if accion == "respaldar":
        respaldar()
    elif accion == "simular_ransomware":
        simular_ransomware()
    elif accion == "restaurar":
        restaurar()
    else:
        print("Uso: python respaldo_seguro.py [respaldar | simular_ransomware | restaurar]")
