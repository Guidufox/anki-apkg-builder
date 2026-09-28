# Immersion Deck Builder

Aplicación local —servida en el navegador— para crear tarjetas de japonés y exportar mazos `.apkg` compatibles con Anki.

**Web del proyecto:** <https://guidufox.github.io/anki-apkg-builder/>

- Funciona en **Windows y Linux**.
- Los datos permanecen en tu computadora.
- No requiere cuentas, OpenAI, ChatGPT, Codex ni una API cloud.
- La edición y exportación funcionan completamente offline.
- Cada entrada genera automáticamente tarjetas **Recognition** y **Recall**.

## Funciones

- Editor rápido con lista, formulario y preview Anki.
- Texto japonés Unicode y fuentes con fallback japonés.
- Crear, editar, borrar, duplicar y reordenar entradas.
- Búsqueda y filtro por tags.
- Importación TSV/CSV con preview.
- Detección de duplicados por `Japanese + Reading`; se omiten por defecto.
- Exportación `.apkg` real mediante `genanki`.
- IDs estables para reducir duplicaciones al regenerar un mazo.
- Persistencia automática en SQLite.
- Backup y restore mediante JSON.
- Escape de HTML/JavaScript introducido en los campos.
- Mazo demo incluido la primera vez.
- Integración opcional con un modelo local y browser agent; no es necesaria para usar el programa.

## Descargar

### Opción A: ZIP

En GitHub pulsa **Code → Download ZIP**, extrae el archivo y abre una terminal dentro de la carpeta extraída.

### Opción B: Git

```bash
git clone URL-DE-TU-REPOSITORIO.git
cd anki-apkg-builder
```

Sustituye `URL-DE-TU-REPOSITORIO.git` por la dirección que GitHub muestre en el botón **Code**.

## Requisitos

- Python 3.10 o superior.
- Un navegador moderno.
- Anki únicamente para importar y estudiar el `.apkg`; no tiene que estar abierto mientras creas el mazo.

Todo lo demás se instala dentro de `.venv/` en la propia carpeta del proyecto.

## Inicio rápido en Windows

1. Instala Python desde <https://www.python.org/downloads/windows/>.
2. Durante la instalación activa **Add Python to PATH**.
3. Descarga y extrae este repositorio.
4. Haz doble clic en `setup.bat`.
5. Cuando termine, haz doble clic en `run.bat`.
6. Deja abierta la terminal y visita <http://127.0.0.1:5000>.

También puedes usar PowerShell:

```powershell
.\setup.ps1
.\run.ps1
```

Si PowerShell bloquea scripts, usa los archivos `.bat`; aplican una excepción limitada a esa ejecución.

## Inicio rápido en Linux

En Debian, Ubuntu y distribuciones similares necesitas Python 3 con soporte para entornos virtuales. Desde el proyecto:

```bash
chmod +x setup.sh run.sh setup-browser.sh
./setup.sh
./run.sh
```

Abre <http://127.0.0.1:5000>.

No se usa `sudo`, no se modifica Python global y el servidor escucha solamente en `127.0.0.1`.

## Detener la aplicación

Pulsa `Ctrl+C` en la terminal donde se ejecuta. Los cambios se guardan automáticamente.

## Crear tarjetas

1. Cambia el nombre del mazo en la barra superior.
2. Pulsa `+` para añadir una entrada.
3. Completa expresión, lectura, significado, ejemplo, traducción, contexto y tags.
4. Escribe manualmente la oración incompleta y la respuesta de Recall.
5. Revisa Recognition y Recall en el panel derecho.

Ejemplo:

```text
Japanese: 覆う
Reading: おおう
Meaning: cubrir
Example: 霧が町を覆っている。
Translation: La niebla cubre el pueblo.
Context: Silent Hill f
Tags: silent-hill-f verb vocabulary
Cloze sentence: 霧が町を＿＿＿＿いる。
Cloze / answer: 覆って
```

No se infieren conjugaciones japonesas automáticamente.

## Importación masiva

Pulsa **Import** y pega TSV o CSV con estas siete columnas:

```text
Japanese  Reading  Meaning  Example  Translation  Context  Tags
```

Ejemplo TSV:

```text
覆う	おおう	cubrir	霧が町を覆っている。	La niebla cubre el pueblo.	Silent Hill f	silent-hill-f verb
```

Pulsa **Preview** antes de importar. Las filas que repitan `Japanese + Reading`, dentro del archivo o contra el mazo actual, aparecen marcadas y se omiten por defecto. Activa **Allow duplicate Japanese + Reading entries** solo cuando quieras otra entrada independiente de la misma expresión.

Los campos Recall importados quedan vacíos para completarlos manualmente.

## Exportar a Anki

Pulsa **Export .apkg**. El archivo se descarga y también queda en:

```text
exports/
```

En Anki abre **Archivo → Importar**, selecciona el `.apkg` y confirma.

Cada entrada genera dos tarjetas:

- **Recognition:** ejemplo y expresión → significado, lectura y traducción.
- **Recall:** significado y oración incompleta → respuesta y oración completa.

## Datos y backups

Los datos se guardan automáticamente en:

```text
data/anki_builder.sqlite3
```

Usa **Backup JSON** para una copia transportable y **Restore JSON** para recuperarla. Restore reemplaza el proyecto actual después de pedir confirmación.

Directorios generados localmente:

```text
data/                    Base, logs y perfil opcional
exports/                 Mazos APKG
.venv/                   Entorno Python local
.playwright/             Chromium opcional
```

Están ignorados por Git cuando contienen datos personales o archivos generados.

## Uso completamente offline

El editor, SQLite, TSV/CSV, JSON y APKG funcionan offline. En **Settings** deja apagados Network, Web y Browser. **DISABLE ALL NETWORK ACCESS** los apaga inmediatamente. No existe fallback hacia una IA cloud.

## Local AI y navegador — opcionales

No necesitas esta sección para crear mazos.

El proveedor opcional acepta endpoints loopback OpenAI-compatible u Ollama y rechaza URLs de IA externas.

Linux:

```bash
./setup-browser.sh
```

Windows:

```powershell
.\setup-browser.ps1
```

Después configura Base URL, Model name, API format, Context length y Timeout en **Settings**.

El navegador visible es el modo predeterminado. Usa un perfil separado en `data/browser-profile/`, una lista cerrada de acciones y confirmación humana para login, formularios, mensajes, compras, pagos, subidas, ejecutables, borrados, cuentas, credenciales o datos personales.

Las investigaciones crean propuestas editables con fuentes y nunca sobrescriben una tarjeta automáticamente.

## Tests

Linux:

```bash
.venv/bin/python -m pytest
```

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Las pruebas cubren CRUD, TSV/CSV, duplicados, backups, APKG real, Unicode, escape HTML, proveedor local, seguridad del navegador y propuestas.

## Actualizar

Con Git:

```bash
git pull
./setup.sh
```

En Windows, después de actualizar, ejecuta nuevamente `setup.bat`. Haz antes un Backup JSON y no borres `data/`.

## Desinstalar

1. Crea un Backup JSON y conserva los `.apkg` deseados.
2. Detén la aplicación.
3. Borra la carpeta del proyecto.

No instala servicios, cuentas, paquetes Python globales ni configuraciones globales.

## Publicar tu copia en GitHub

El repositorio ya está inicializado y tiene commits. Crea en GitHub un repositorio vacío, sin README ni `.gitignore`, y copia su URL.

Desde esta carpeta:

```bash
git remote add origin https://github.com/TU-USUARIO/anki-apkg-builder.git
git branch -M main
git push -u origin main
```

Si `origin` ya existe:

```bash
git remote set-url origin https://github.com/TU-USUARIO/anki-apkg-builder.git
git push -u origin main
```

GitHub puede pedir autenticación por navegador, token personal o SSH. Nunca subas `.venv/`, `data/`, `.playwright/`, `.local-chromium/` ni tus `.apkg`; `.gitignore` ya los excluye.

Después del push, cualquiera podrá usar **Code → Download ZIP** o `git clone` y seguir la sección de Windows/Linux sin instalar Bonsai.

## Limitaciones conocidas

- Es una aplicación local para una persona, sin autenticación multiusuario.
- El servidor incluido es apropiado para localhost, no para exponerlo directamente a Internet.
- Los clozes japoneses se completan manualmente.
- La investigación opcional depende del protocolo JSON del modelo y de los sitios consultados.
