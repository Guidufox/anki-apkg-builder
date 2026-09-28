# Immersion Deck Builder

Aplicación local para Debian que crea tarjetas de japonés, las guarda en SQLite y exporta un paquete `.apkg` importable directamente en Anki. Cada entrada genera dos tarjetas: **Recognition** y **Recall**. No usa OpenAI, Codex, ChatGPT ni ninguna API cloud.

La edición, importación, backups y exportación Anki funcionan totalmente offline. La investigación web es un subsistema opcional: un modelo Bonsai/Qwen local decide acciones de un navegador Playwright restringido.

## Setup exacto en Debian

Requisitos del sistema: Python 3 con soporte para `venv` y una sesión gráfica si se desea usar el navegador visible. Desde este directorio:

```bash
chmod +x setup.sh run.sh
./setup.sh
```

El script crea `.venv/`, instala allí Flask, genanki, pytest y Playwright, y descarga Chromium dentro de `.playwright/`. Si ese CDN no responde, descarga los paquetes de Debian sin instalarlos y los extrae en `.local-chromium/`. No usa `sudo` ni modifica Python global. Para instalar la aplicación sin Chromium:

```bash
SKIP_BROWSER_INSTALL=1 ./setup.sh
```

La parte Anki funciona aunque Playwright o Chromium no estén disponibles.

## Ejecutar y detener

```bash
./run.sh
```

Abrir <http://127.0.0.1:5000>. El servidor escucha exclusivamente en `127.0.0.1`. Para detenerlo, volver a la terminal y pulsar `Ctrl+C`.

## Uso básico

- El nombre del mazo y todos los campos se guardan automáticamente.
- Cada entrada produce dos tarjetas Anki. La oración cloze y su respuesta son manuales: no se infieren conjugaciones.
- La lista permite buscar, filtrar por tags, duplicar, borrar, arrastrar y reordenar.
- **Import** acepta TSV o CSV de siete columnas: `Japanese, Reading, Meaning, Example, Translation, Context, Tags`. Siempre muestra preview antes de importar.
- **Export .apkg** descarga el archivo y también lo deja en `exports/`.
- El texto del usuario se escapa antes de entrar en Anki y se representa con `textContent` en la web; no se ejecuta HTML o JavaScript de las tarjetas.

Los IDs del modelo y del deck son deterministas. Los GUID de las notas se mantienen al editar o restaurar el proyecto, reduciendo duplicados al regenerar el mazo.

## Backup y restore

**Backup JSON** descarga el proyecto completo. **Restore JSON** reemplaza el proyecto actual por el backup después de pedir confirmación. Estos backups no dependen de Anki.

Los datos activos están en:

- `data/anki_builder.sqlite3`: mazo, tarjetas, settings, propuestas, fuentes y logs.
- `exports/`: paquetes `.apkg` generados.
- `data/browser-profile/`: perfil separado del navegador agente.
- `data/screenshots/`: capturas solicitadas por el agente.

Conviene guardar copias del JSON fuera del proyecto antes de una actualización importante.

## Conectar Bonsai/Qwen local

Abrir **Settings → Local AI & Privacy** y configurar:

1. **API format: OpenAI-compatible** para llama.cpp, vLLM, LM Studio u otro servidor compatible.
2. **Base URL**, por ejemplo `http://127.0.0.1:8080/v1`.
3. **Model name**, por ejemplo `bonsai` o el identificador expuesto por el servidor.
4. **Context length** y **Timeout**.
5. Activar Local AI, Network, Web y Browser, guardar y usar **Test Local AI**.

Para el formato OpenAI-compatible se espera:

```text
POST {base_url}/chat/completions
GET  {base_url}/models
```

Para Ollama, seleccionar **Ollama** y usar normalmente `http://127.0.0.1:11434`:

```text
POST {base_url}/api/chat
GET  {base_url}/api/tags
```

La aplicación rechaza cualquier endpoint de IA que no sea `localhost`, `127.0.0.1` o una dirección IP loopback. No existe fallback cloud, clave API ni integración OpenAI alojada. Para comprobar que la inferencia es local, apaga Internet, ejecuta el endpoint Bonsai/Qwen en loopback y pulsa **Test Local AI**; el editor y el exportador siguen funcionando aunque la prueba falle.

## Browser agent y privacidad

El flujo es: **Bonsai/Qwen local → controlador local → herramientas permitidas → Chromium local → web**. En una tarjeta, pulsar **Research with Local AI**. El agente muestra URL, tarea, última acción, próxima acción y estado. Puede pausarse, continuarse o detenerse.

El navegador es visible por defecto. Headless solo se activa explícitamente en Settings. Sus únicas acciones son navegar, buscar, hacer clic, escribir, desplazar, leer DOM visible/enlaces, tomar capturas, volver, abrir/cerrar pestañas y esperar. No recibe shell, filesystem general, sudo, SSH ni ejecución arbitraria.

Antes de login, envío/publicación, compra/pago, subida, borrado, cambios de cuenta, aceptación de términos, credenciales o datos personales, el controlador presenta una confirmación. El contenido escrito con la acción `type` no se guarda en logs.

La investigación crea una propuesta editable con resumen, significado, ejemplo, notas y fuentes (título, URL, fecha y fragmento). **Nunca modifica la tarjeta automáticamente**. `Accept` copia la propuesta visible al editor; `Reject` la descarta.

### Red y modo completamente offline

- Los tres indicadores de Privacy muestran Web, Browser y Network como ON/OFF.
- **DISABLE ALL NETWORK ACCESS** detiene el agente y apaga acceso web y automatización.
- Para modo completamente offline, deje Network, Web y Browser en OFF. Local AI puede permanecer configurada pero ninguna investigación se iniciará. La creación, edición, importación, backup y exportación `.apkg` siguen disponibles.

### Perfil del navegador

El perfil predeterminado es `data/browser-profile/`, aislado del navegador personal. No se copian cookies o sesiones. Settings permite escribir otro perfil de forma explícita y muestra una advertencia; hacerlo puede exponer sus sesiones al agente.

Para borrar completamente el perfil predeterminado, cierre la aplicación y ejecute desde este directorio:

```bash
rm -rf -- data/browser-profile
```

Esta operación elimina de forma irreversible cookies, caché e historial del perfil del agente. No afecta Firefox/Chrome personal.

Los logs se consultan en **Settings → Recent agent logs** y se guardan en SQLite. Incluyen timestamp, tarea, URL, acción y resultado, pero omiten el texto introducido en campos.

## Tests

```bash
.venv/bin/python -m pytest
```

Las pruebas cubren deck y CRUD, orden, TSV/CSV, backup/restore, paquete APKG real (SQLite interno y notas esperadas), escape HTML, proveedor local, fallo de IA, modos browser/red desactivados, allowlist, confirmación sensible y propuestas de investigación.

## Actualizar

Después de copiar o traer una versión nueva del proyecto:

```bash
./setup.sh
.venv/bin/python -m pytest
```

`setup.sh` reutiliza el entorno local y actualiza dependencias según los archivos del proyecto. Haga antes un **Backup JSON**. No borre `data/` si quiere conservar el mazo.

## Desinstalar

1. Detener con `Ctrl+C`.
2. Guardar un Backup JSON y los `.apkg` deseados.
3. Eliminar este directorio del proyecto completo desde su carpeta padre.

No hay servicio, usuario, paquete Python global ni configuración global que desinstalar.

## Limitaciones conocidas

- La calidad de investigación depende de que el modelo local siga el protocolo JSON y del contenido accesible de cada web.
- CAPTCHAs, paywalls y páginas muy dinámicas pueden requerir control humano.
- La detección de acciones sensibles combina las declaraciones del modelo con reglas conservadoras; revise siempre la ventana visible y use Pause/Stop si algo no coincide con la tarea.
- No se infieren conjugaciones ni clozes japoneses automáticamente.
