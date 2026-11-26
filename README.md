# HuellaVet - Laboratorio Local de Ciberseguridad

Aplicación web en Python y Flask para proyecto final (`127.0.0.1`).

## Requisitos y ejecución

1. Clonar el repositorio y entrar al directorio del proyecto:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd ProyectoFinal_Ciber
   ```

2. Crear y activar el entorno virtual dentro de `app_lab/`:
   - **Windows (PowerShell):**
     ```powershell
     python -m venv app_lab\venv
     .\app_lab\venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv app_lab/venv
     source app_lab/venv/bin/activate
     ```

3. Instalar las dependencias:
   ```bash
   pip install -r app_lab/requirements.txt
   ```

4. Ejecutar la aplicación:
   ```bash
   python app_lab/app.py
   ```

5. Abrir en el navegador: `http://127.0.0.1:5000/`


## Mejora Técnica — Parte B (Respaldo Cifrado y Verificación SHA-256)
Ubicación: `parte_b_mejora/respaldo_seguro.py`
- Generar respaldo cifrado y hashes: `python parte_b_mejora/respaldo_seguro.py respaldar`
- Simular ataque de ransomware: `python parte_b_mejora/respaldo_seguro.py simular_ransomware`
- Restaurar y verificar integridad SHA-256: `python parte_b_mejora/respaldo_seguro.py restaurar`
