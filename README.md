# Compress PDF

Herramienta de escritorio para **reducir el tamaño de un PDF** recomprimiendo sus imágenes a JPEG y optimizando su estructura interna. Ideal para PDF escaneados o con muchas fotos que superan el límite de un correo o un portal.

## Instalación (Windows, cmd)

```bat
git clone https://github.com/laguileg/compress_pdf.git
cd compress_pdf
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

## Uso

```bat
py compress_pdf_gui.py
py compress_pdf_gui.py "C:\Docs\informe.pdf"
py compress_pdf_gui.py --help
```

En la ventana: eliges el PDF, ajustas los parámetros y presionas *Comprimir PDF*. Al terminar muestra el tamaño antes → después y el % de reducción. El menú **Ayuda → Cómo usar** explica cada opción.

| Parámetro en la ventana | Por defecto | Efecto |
|---|---|---|
| Calidad JPEG (10–100) | 75 | Menos calidad = archivo más liviano. Bajo 40 se nota la pérdida. |
| Ancho / alto máximo (px) | 2048 | Las imágenes más grandes se achican a ese tamaño. |
| Escala de grises | No | Quita el color de las imágenes para comprimir más. |
| Optimización estructural | Sí | Comprime los objetos internos del PDF. |

| Opción de línea de comandos | Qué hace |
|---|---|
| `pdf` | PDF a seleccionar al abrir (opcional) |
| `-h`, `--help` | Muestra la ayuda |
| `--version` | Muestra la versión |

## Archivos que genera

- `<nombre>_compressAAMMDDHHMMSS.pdf` (nombre editable) en la misma carpeta del original. **El PDF original no se modifica.**
- `compress_pdf_gui.log` junto al script, **solo si ocurre un error** o una imagen no se pudo recomprimir.

## Problemas conocidos

- **PDF solo con texto**: casi no se reducen, porque lo que pesa en un PDF suelen ser las imágenes.
- **Imágenes en formatos poco comunes** (JBIG2, CMYK con perfil ICC) se dejan tal cual y se anotan en el `.log`.
- **Máscaras y dibujos de 1 bit** no se tocan, para no arruinar su calidad.
- Una imagen solo se reemplaza si la versión nueva queda más liviana que la original.

## Crear un .exe (opcional)

```bat
py -m pip install pyinstaller
pyinstaller --onefile --windowed --name compress_pdf compress_pdf_gui.py
```

El ejecutable queda en `dist\compress_pdf.exe`.

## Licencia

[MIT](LICENSE): puedes usar, modificar y compartir este código libremente, manteniendo el aviso de autoría.

## Historial

| Fecha | Versión | Cambios |
|---|---|---|
| 2026-11-11 | 1.0.0 | Primera versión pública. **Corrige la recompresión de imágenes**, que antes fallaba en silencio (solo se aplicaba la optimización estructural). Ayuda en español (`--help`, menú Ayuda), `--version`, PDF inicial por línea de comandos, registro de errores en `.log`. Ya no requiere `pypdf`. |
