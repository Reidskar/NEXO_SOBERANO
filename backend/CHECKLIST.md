# Checklist de Conectores y Pruebas

Este documento acompaña al script `check_connectors.py` y reúne los elementos que deben estar operativos antes de pasar a la fase de ingestión:

1. **Credenciales**
   - `backend/auth/credenciales_google.json` (copiar desde `credenciales_google.json.example`).
   - `backend/auth/credenciales_microsoft.json` (copiar desde `credenciales_microsoft.json.example`).
   - Ambos archivos están en `.gitignore` y no deben versionarse.

2. **Token inicial**
   - Ejecutar:
     ```bash
     python -m services.connectors.google_connector
     ```
     - Google abrirá el navegador para autorizar la app.
     - Tras aceptar, `backend/auth/token_google.json` queda guardado.
   - Ejecutar:
     ```bash
     python -m services.connectors.microsoft_connector
     ```
     - Inicia el flujo OAuth de Microsoft y guarda `token_microsoft.json`.

3. **Verificar contenedores**
   - Ejecutar el script de verificación:
     ```bash
     python backend/check_connectors.py
     ```
   - Debe mostrar mensajes tipo:
     - `Google connector import: OK` y `Google Drive access: OK (N items)`.
     - `Microsoft connector import: OK` y `OneDrive access: OK`.
   - Los resultados JSON (`google_files.json`, `onedrive_root.json`, etc.) se guardan en `backend/checks/`.

4. **Endpoints FastAPI**
   - Levantar el backend (`python nexo_v2.py run` o `python backend/main.py`).
   - Probar en el navegador o `curl`:
     ```bash
     curl http://127.0.0.1:8000/drive/recent
     curl http://127.0.0.1:8000/agente/health
     ```
   - Devolverán JSON con datos o mensajes de error describe el problema.

5. **Carpetas de sincronización**
   - `NEXO_SOBERANO/documentos/` es la carpeta donde se almacenarán archivos descargados.
   - El orquestador (`nexo_v2.sincronizar_nube`) copia nuevos archivos ahí y los procesa.
   - Puedes inspeccionar manualmente Drive/OneDrive via web para confirmar archivos.

6. **Workflows internos**
   - La función `core.orquestador.OrquestadorCentral.sincronizar_conectores()` ya invoca ambos conectores y pasa nombres/IDs al pipeline.
   - El método `procesar_nuevo_archivo` muestra cómo se evalúan prioridades y se registra el gasto.

7. **Siguiente paso**
   - Una vez ambos servicios devuelvan datos y los endpoints estén accesibles, procede a integrar la ingestión real en el backend RAG (clasificador + vectorización).
   - Después de ello, ya puedes encender el frontend.

> Usa este archivo como checklist manual: marcar ✅ según vayas completando las tareas.
