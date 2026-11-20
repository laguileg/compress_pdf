#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPRESS PDF GUI
Herramienta con interfaz gráfica para reducir el tamaño de un PDF
recomprimiendo sus imágenes a JPEG (calidad y tamaño máximo ajustables)
y optimizando la estructura interna del archivo.

Lee:     un PDF elegido con el botón "Buscar..." (o pasado al abrir).
Genera:  <nombre>_compressAAMMDDHHMMSS.pdf en la misma carpeta del original
         (el original no se modifica). Si ocurre un error, el detalle
         técnico queda en compress_pdf_gui.log.

Recursos: assets/ con el logo y el ícono de la marca Prisma Sol (opcional).
Requiere: py -m pip install -r requirements.txt   (pikepdf, pillow)

Uso:
  py compress_pdf_gui.py
  py compress_pdf_gui.py "C:\\Docs\\informe.pdf"
  py compress_pdf_gui.py --help
"""

import argparse
import logging
import os
import sys
import threading
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

try:
    import pikepdf
    from pikepdf import Pdf, PdfImage
except ImportError:
    print("Falta la librería pikepdf. Instálala con:\n  py -m pip install pikepdf")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Falta la librería Pillow. Instálala con:\n  py -m pip install pillow")
    sys.exit(1)

VERSION = "1.1.0"
NOMBRE_APP = "Compress PDF"

if getattr(sys, "frozen", False):  # empaquetado como .exe con PyInstaller
    CARPETA_APP = Path(sys.executable).parent
else:
    CARPETA_APP = Path(__file__).parent
RUTA_LOG = CARPETA_APP / "compress_pdf_gui.log"

# delay=True: el .log solo se crea si de verdad ocurre un error.
logging.basicConfig(
    level=logging.WARNING,  # el .log es solo para errores y avisos
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(RUTA_LOG, encoding="utf-8", delay=True)],
)
log = logging.getLogger("compress_pdf")

# ─── Sistema de marca "Luciano Aguilera · Prisma Sol" ───
COLOR_VIOLETA = "#5B3DF5"          # protagonista: encabezado, botón principal
COLOR_VIOLETA_TEXTO = "#4F32E6"    # violeta para texto sobre fondos claros; hover
COLOR_SOL = "#FFD23F"              # acento: línea bajo el encabezado
COLOR_TINTA = "#17123A"
COLOR_LILA = "#EEEAFF"             # superficie tintada: registro, barra, resultado
COLOR_SURFACE = "#FAFAFC"          # fondo de la ventana
COLOR_SURFACE_RAISED = "#FFFFFF"   # campos y listas
COLOR_INK = "#17123A"              # texto principal
COLOR_INK_MUTED = "#57536B"        # texto secundario
COLOR_LINE = "#E5E3EE"             # bordes
COLOR_ON_VIOLETA = "#FFFFFF"
COLOR_EXITO = "#0E7A55"
COLOR_ALERTA = "#A35400"
COLOR_ERROR = "#C42B47"

# Urbanist para títulos y Inter para el resto; si no están instaladas, los respaldos del sistema.
FUENTES_TITULO = ("Urbanist", "Century Gothic", "Segoe UI")
FUENTES_TEXTO = ("Inter", "Segoe UI", "Arial")
FONT_PRIMARY = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_SECTION = ("Segoe UI", 12, "bold")
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_BIG = ("Segoe UI", 22, "bold")

CARPETA_RECURSOS = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
RUTA_LOGO = CARPETA_RECURSOS / "assets" / "logo-horizontal-negativo-violeta.png"
RUTA_ICONO = CARPETA_RECURSOS / "assets" / "isotipo-app.png"

TEXTO_AYUDA = """\
Cómo usar Compress PDF

1. Elige el PDF con "Buscar...".
2. Ajusta la calidad JPEG: menos calidad = archivo más liviano.
   75 es un buen equilibrio; bajo 40 se nota la pérdida.
3. Opcional: limita el ancho/alto máximo de las imágenes, o
   conviértelas a escala de grises para comprimir más.
4. Presiona "Comprimir PDF".

El resultado se guarda junto al original con otro nombre;
el PDF original nunca se modifica. Si el PDF casi no tiene
imágenes (solo texto), la reducción será pequeña.
"""


# ─── Línea de comandos ───
class FormateadorAyuda(argparse.RawDescriptionHelpFormatter):
    """Formateador de argparse con el encabezado 'uso:' en español."""

    def add_usage(self, usage, actions, groups, prefix=None):
        return super().add_usage(usage, actions, groups, prefix if prefix is not None else "uso: ")


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compress_pdf_gui.py",
        description="Reduce el tamaño de un PDF recomprimiendo sus imágenes, mediante una ventana gráfica.",
        epilog=(
            "Ejemplos:\n"
            "  py compress_pdf_gui.py\n"
            "      abre la ventana y eliges el PDF con \"Buscar...\"\n"
            '  py compress_pdf_gui.py "C:\\Docs\\informe.pdf"\n'
            "      abre la ventana con ese PDF ya seleccionado\n"
            "  py compress_pdf_gui.py --version\n"
            "      muestra la versión instalada"
        ),
        formatter_class=FormateadorAyuda,
        add_help=False,
    )
    parser._positionals.title = "argumentos posicionales"
    parser._optionals.title = "opciones"
    parser.add_argument("pdf", nargs="?", type=Path,
                        help="PDF a seleccionar al abrir (opcional, por defecto ninguno)")
    parser.add_argument("-h", "--help", action="help", help="muestra esta ayuda y termina")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}",
                        help="muestra la versión y termina")
    return parser


def configurar_fuentes(raiz: tk.Tk) -> None:
    """Usa la primera fuente de marca instalada en el equipo, o su respaldo."""
    global FONT_PRIMARY, FONT_BOLD, FONT_SECTION, FONT_TITLE, FONT_SMALL, FONT_BIG
    instaladas = set(tkfont.families(raiz))
    titulo = next((f for f in FUENTES_TITULO if f in instaladas), "Segoe UI")
    texto = next((f for f in FUENTES_TEXTO if f in instaladas), "Segoe UI")
    FONT_PRIMARY = (texto, 10)
    FONT_BOLD = (texto, 10, "bold")
    FONT_SECTION = (titulo, 12, "bold")
    FONT_TITLE = (titulo, 20, "bold")
    FONT_SMALL = (texto, 9)
    FONT_BIG = (titulo, 22, "bold")


# ─── Motor Compress PDF ───
class PDFCompressor:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    @staticmethod
    def recompress_image(img: PdfImage, quality: int = 75,
                         max_size: Optional[Tuple[int, int]] = (2048, 2048),
                         grayscale: bool = False) -> Tuple[bytes, Tuple[int, int], str]:
        """Recodifica una imagen del PDF a JPEG.

        Returns:
            (bytes JPEG, (ancho, alto), modo PIL "L" o "RGB")
        """
        pil = img.as_pil_image()
        if grayscale:
            pil = pil.convert("L")
        elif pil.mode not in ("RGB", "L"):
            pil = pil.convert("RGB")
        if max_size:
            pil.thumbnail(max_size, Image.LANCZOS)
        buf = BytesIO()
        pil.save(buf, format="JPEG", quality=max(1, min(100, quality)),
                 optimize=True, progressive=True, subsampling="4:2:0")
        return buf.getvalue(), pil.size, pil.mode

    @staticmethod
    def replace_image(xobj, jpeg_bytes: bytes, size: Tuple[int, int], mode: str) -> None:
        """Reemplaza el contenido de la imagen del PDF por el JPEG nuevo."""
        xobj.write(jpeg_bytes, filter=pikepdf.Name.DCTDecode)
        xobj.Width, xobj.Height = size
        xobj.ColorSpace = pikepdf.Name.DeviceGray if mode == "L" else pikepdf.Name.DeviceRGB
        xobj.BitsPerComponent = 8
        # Parámetros del formato anterior que ya no aplican al JPEG.
        for clave in ("/DecodeParms", "/Decode", "/Intent"):
            if clave in xobj:
                del xobj[clave]

    def compress_pdf(self, input_pdf: str, output_path: str,
                     quality: int = 75, max_width: int = 2048,
                     max_height: int = 2048, grayscale: bool = False,
                     structural_optimize: bool = True,
                     progress_cb=None) -> Tuple[str, int, int, int]:
        """
        Comprime un PDF.
        Returns: (output_path, images_processed, before_bytes, after_bytes)
        """
        in_path = Path(input_pdf).resolve()
        before_size = in_path.stat().st_size

        # Contar total de imágenes primero para progreso
        total_images = 0
        with Pdf.open(in_path) as pdf_count:
            for page in pdf_count.pages:
                resources = page.get("/Resources", {})
                xobjects = resources.get("/XObject", {})
                for name, xobj in xobjects.items():
                    try:
                        PdfImage(xobj)
                        total_images += 1
                    except Exception:
                        pass

        processed = 0
        current_img = 0

        with Pdf.open(in_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                if self.cancelled:
                    return output_path, 0, before_size, before_size

                resources = page.get("/Resources", {})
                xobjects = resources.get("/XObject", {})
                if not xobjects:
                    continue

                for name, xobj in list(xobjects.items()):
                    if self.cancelled:
                        return output_path, 0, before_size, before_size

                    try:
                        img = PdfImage(xobj)
                    except Exception:
                        continue

                    # Máscaras de 1 bit no son fotos: recomprimirlas a JPEG las arruinaría.
                    if img.image_mask or img.bits_per_component < 8:
                        current_img += 1
                        continue

                    try:
                        new_bytes, size, mode = self.recompress_image(
                            img, quality=quality,
                            max_size=(max_width, max_height),
                            grayscale=grayscale
                        )
                        # Solo se reemplaza si de verdad queda más liviana.
                        if len(new_bytes) < len(xobj.read_raw_bytes()):
                            self.replace_image(xobj, new_bytes, size, mode)
                            processed += 1
                    except Exception:
                        # Formatos de imagen poco comunes (JBIG2, CMYK con ICC, etc.) se dejan
                        # tal cual; se registran para poder revisarlos.
                        log.warning("Imagen %s de la página %d no se recomprimió", name, page_idx + 1,
                                    exc_info=True)

                    current_img += 1
                    if progress_cb and total_images > 0:
                        progress_cb(current_img, total_images,
                                    f"Imagen {current_img}/{total_images} (pág. {page_idx + 1})")

            save_kwargs = {}
            if structural_optimize:
                save_kwargs.update(
                    compress_streams=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                    linearize=False,
                )

            if progress_cb:
                progress_cb(total_images, total_images, "Guardando PDF optimizado...")

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            pdf.save(output_path, **save_kwargs)

        after_size = Path(output_path).stat().st_size
        return output_path, processed, before_size, after_size


# ─── GUI ───
class CompressPDFApp(tk.Tk):
    def __init__(self, pdf_inicial: Path | None = None):
        super().__init__()
        configurar_fuentes(self)
        self._poner_icono()
        self.title(f"{NOMBRE_APP} {VERSION}")
        self.geometry("620x790")
        self.configure(bg=COLOR_SURFACE)
        self.resizable(False, False)

        self.compressor = PDFCompressor()
        self.selected_file = tk.StringVar(value="")
        self.quality_var = tk.IntVar(value=75)
        self.max_w_var = tk.IntVar(value=2048)
        self.max_h_var = tk.IntVar(value=2048)
        self.grayscale_var = tk.BooleanVar(value=False)
        self.struct_opt_var = tk.BooleanVar(value=True)
        self.output_name_var = tk.StringVar(value="")
        self.output_path = None
        self.running = False

        self._build_menu()
        self._build_ui()

        if pdf_inicial and pdf_inicial.is_file():
            self._cargar_archivo(str(pdf_inicial.resolve()))

    # ── Menú ──
    def _build_menu(self):
        menubar = tk.Menu(self)
        menu_ayuda = tk.Menu(menubar, tearoff=0)
        menu_ayuda.add_command(label="Cómo usar", command=self._mostrar_ayuda)
        menu_ayuda.add_command(label="Acerca de", command=self._mostrar_acerca_de)
        menubar.add_cascade(label="Ayuda", menu=menu_ayuda)
        self.config(menu=menubar)

    def _mostrar_ayuda(self):
        messagebox.showinfo("Ayuda", TEXTO_AYUDA)

    def _mostrar_acerca_de(self):
        messagebox.showinfo("Acerca de",
                            f"{NOMBRE_APP} {VERSION}\n\nReduce el tamaño de PDF con imágenes.\n"
                            "Licencia MIT.")

    # ── Encabezado de marca ──
    def _build_header(self, titulo: str):
        header = tk.Frame(self, bg=COLOR_VIOLETA, padx=30, pady=18)
        header.pack(fill="x")
        try:
            self._logo_img = tk.PhotoImage(file=str(RUTA_LOGO))
            tk.Label(header, image=self._logo_img, bg=COLOR_VIOLETA).pack(anchor="w")
        except tk.TclError:
            log.warning("No se encontró el logo en %s; la ventana sigue sin él.", RUTA_LOGO)
        tk.Label(header, text=titulo, font=FONT_TITLE, fg=COLOR_ON_VIOLETA,
                 bg=COLOR_VIOLETA, anchor="w").pack(fill="x", pady=(12, 0))
        # Línea sol: el acento de la marca, una sola vez en la ventana.
        tk.Frame(self, bg=COLOR_SOL, height=4).pack(fill="x", pady=(0, 14))

    def _poner_icono(self):
        try:
            self._icono_img = tk.PhotoImage(file=str(RUTA_ICONO))
            self.iconphoto(True, self._icono_img)
        except tk.TclError:
            log.warning("No se encontró el ícono en %s.", RUTA_ICONO)

    # ── Build UI ──
    def _build_ui(self):
        self._build_header("Comprimir PDF")

        main = tk.Frame(self, bg=COLOR_SURFACE, padx=30)
        main.pack(fill="both", expand=True)

        # ── Selección de archivo ──
        self._section(main, "Archivo PDF")
        file_frame = tk.Frame(main, bg=COLOR_SURFACE)
        file_frame.pack(fill="x", pady=(0, 4))

        self.file_entry = tk.Entry(file_frame, textvariable=self.selected_file,
                                   font=FONT_PRIMARY, state="readonly",
                                   readonlybackground=COLOR_SURFACE_RAISED, fg=COLOR_INK,
                                   relief="flat", highlightthickness=1,
                                   highlightbackground=COLOR_LINE)
        self.file_entry.pack(side="left", fill="x", expand=True, ipady=4)

        btn_browse = tk.Button(file_frame, text="Buscar...", font=FONT_BOLD,
                               bg=COLOR_VIOLETA, fg=COLOR_ON_VIOLETA, activebackground=COLOR_VIOLETA_TEXTO,
                               activeforeground=COLOR_ON_VIOLETA, bd=0, padx=16, pady=4,
                               cursor="hand2", command=self._browse_file)
        btn_browse.pack(side="right", padx=(8, 0))

        self.file_info = tk.Label(main, text="", font=FONT_SMALL, fg=COLOR_INK_MUTED,
                                  bg=COLOR_SURFACE, anchor="w")
        self.file_info.pack(fill="x", pady=(0, 8))

        # ── Parámetros de compresión ──
        self._section(main, "Parámetros de compresión")

        params = tk.Frame(main, bg=COLOR_SURFACE)
        params.pack(fill="x", pady=(0, 4))

        # Calidad JPEG con slider
        tk.Label(params, text="Calidad JPEG (1-100):", font=FONT_PRIMARY,
                 fg=COLOR_INK_MUTED, bg=COLOR_SURFACE).grid(row=0, column=0, sticky="w", pady=2)

        slider_frame = tk.Frame(params, bg=COLOR_SURFACE)
        slider_frame.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=2)

        self.quality_slider = tk.Scale(slider_frame, from_=10, to=100,
                                       orient="horizontal", variable=self.quality_var,
                                       length=200, bg=COLOR_SURFACE, fg=COLOR_INK,
                                       troughcolor=COLOR_LILA, highlightthickness=0,
                                       sliderrelief="flat", activebackground=COLOR_VIOLETA,
                                       command=self._update_quality_hint)
        self.quality_slider.pack(side="left")

        self.quality_hint = tk.Label(slider_frame, text="Balanceado", font=FONT_SMALL,
                                     fg=COLOR_VIOLETA_TEXTO, bg=COLOR_SURFACE, width=14)
        self.quality_hint.pack(side="left", padx=(4, 0))

        # Max ancho
        tk.Label(params, text="Ancho máx. imágenes (px):", font=FONT_PRIMARY,
                 fg=COLOR_INK_MUTED, bg=COLOR_SURFACE).grid(row=1, column=0, sticky="w", pady=2)
        tk.Spinbox(params, from_=512, to=4096, increment=256,
                   textvariable=self.max_w_var, width=8, font=FONT_PRIMARY,
                   bg=COLOR_SURFACE_RAISED, buttonbackground=COLOR_LILA
                   ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=2)

        # Max alto
        tk.Label(params, text="Alto máx. imágenes (px):", font=FONT_PRIMARY,
                 fg=COLOR_INK_MUTED, bg=COLOR_SURFACE).grid(row=2, column=0, sticky="w", pady=2)
        tk.Spinbox(params, from_=512, to=4096, increment=256,
                   textvariable=self.max_h_var, width=8, font=FONT_PRIMARY,
                   bg=COLOR_SURFACE_RAISED, buttonbackground=COLOR_LILA
                   ).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=2)

        # Checkboxes
        checks = tk.Frame(main, bg=COLOR_SURFACE)
        checks.pack(fill="x", pady=(4, 4))

        tk.Checkbutton(checks, text="Escala de grises (pierde color, más compresión)",
                       variable=self.grayscale_var, font=FONT_PRIMARY,
                       bg=COLOR_SURFACE, fg=COLOR_INK, selectcolor=COLOR_SURFACE_RAISED,
                       activebackground=COLOR_SURFACE).pack(anchor="w")

        tk.Checkbutton(checks, text="Optimización estructural (recomendado)",
                       variable=self.struct_opt_var, font=FONT_PRIMARY,
                       bg=COLOR_SURFACE, fg=COLOR_INK, selectcolor=COLOR_SURFACE_RAISED,
                       activebackground=COLOR_SURFACE).pack(anchor="w")

        # ── Nombre salida ──
        self._section(main, "Archivo de salida")
        out_hint = tk.Label(main, text="Se guarda en la misma carpeta del PDF original.",
                            font=FONT_SMALL, fg=COLOR_INK_MUTED, bg=COLOR_SURFACE)
        out_hint.pack(anchor="w")

        self.entry_output = tk.Entry(main, textvariable=self.output_name_var,
                                     font=FONT_PRIMARY, bg=COLOR_SURFACE_RAISED, fg=COLOR_INK, relief="flat",
                                     highlightthickness=1, highlightbackground=COLOR_LINE,
                                     highlightcolor=COLOR_VIOLETA, width=45)
        self.entry_output.pack(fill="x", pady=(2, 8), ipady=3)

        # ── Barra progreso ──
        self.progress_label = tk.Label(main, text="", font=FONT_SMALL,
                                       fg=COLOR_INK_MUTED, bg=COLOR_SURFACE)
        self.progress_label.pack(fill="x", pady=(4, 2))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("App.Horizontal.TProgressbar",
                        troughcolor=COLOR_LILA, background=COLOR_VIOLETA, thickness=18)
        self.progress = ttk.Progressbar(main, style="App.Horizontal.TProgressbar",
                                        mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 6))

        # ── Resultado visual ──
        self.result_frame = tk.Frame(main, bg=COLOR_SURFACE)
        self.result_frame.pack(fill="x", pady=(0, 4))

        # ── Botones ──
        action_row = tk.Frame(main, bg=COLOR_SURFACE)
        action_row.pack(fill="x", pady=(2, 6))

        self.btn_compress = tk.Button(action_row, text="  Comprimir PDF  ", font=FONT_BOLD,
                                      bg=COLOR_VIOLETA, fg=COLOR_ON_VIOLETA, activebackground=COLOR_VIOLETA_TEXTO,
                                      activeforeground=COLOR_ON_VIOLETA, bd=0, padx=24, pady=8,
                                      cursor="hand2", command=self._run_compress)
        self.btn_compress.pack(side="left")

        self.btn_open_folder = tk.Button(action_row, text="Abrir carpeta", font=FONT_PRIMARY,
                                         bg=COLOR_LILA, fg=COLOR_VIOLETA_TEXTO,
                                         activebackground=COLOR_LINE,
                                         activeforeground=COLOR_VIOLETA_TEXTO, bd=0, padx=16, pady=8,
                                         cursor="hand2", state="disabled",
                                         command=self._open_output_folder)
        self.btn_open_folder.pack(side="right")

        # ── Log ──
        self.log_text = tk.Text(main, height=4, font=FONT_SMALL, bg=COLOR_LILA,
                                fg=COLOR_INK, bd=0, relief="flat", state="disabled",
                                wrap="word")
        self.log_text.pack(fill="x", pady=(4, 12))

    # ── Helpers ──
    def _section(self, parent, text):
        lbl = tk.Label(parent, text=text, font=FONT_SECTION, fg=COLOR_INK,
                       bg=COLOR_SURFACE, anchor="w")
        lbl.pack(fill="x", pady=(6, 2))

    def _update_quality_hint(self, val=None):
        q = self.quality_var.get()
        if q <= 30:
            hint, color = "Agresivo", COLOR_ERROR
        elif q <= 55:
            hint, color = "Alta compresión", COLOR_ALERTA
        elif q <= 75:
            hint, color = "Balanceado", COLOR_VIOLETA_TEXTO
        elif q <= 90:
            hint, color = "Alta calidad", COLOR_EXITO
        else:
            hint, color = "Mínima compresión", COLOR_INK_MUTED
        self.quality_hint.config(text=hint, fg=color)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Seleccionar PDF",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")]
        )
        if path:
            self._cargar_archivo(path)

    def _cargar_archivo(self, path: str):
        self.selected_file.set(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        try:
            with Pdf.open(path) as pdf:
                n_pages = len(pdf.pages)
            self.file_info.config(text=f"{n_pages} páginas  •  {size_mb:.2f} MB")
        except pikepdf.PdfError:
            log.exception("No se pudo leer el número de páginas de %s", path)
            self.file_info.config(text=f"{size_mb:.2f} MB  •  no se pudo leer el número de páginas")

        stem = Path(path).stem
        stamp = datetime.now().strftime("%y%m%d%H%M%S")
        self.output_name_var.set(f"{stem}_compress{stamp}.pdf")

    def _log(self, msg: str):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _update_progress(self, current, total, msg=""):
        if total > 0:
            pct = int(current / total * 100)
            self.progress["value"] = pct
        self.progress_label.config(text=msg)
        self.update_idletasks()

    def _show_result(self, before_bytes, after_bytes):
        # Limpiar frame resultado
        for w in self.result_frame.winfo_children():
            w.destroy()

        before_mb = before_bytes / (1024 * 1024)
        after_mb = after_bytes / (1024 * 1024)

        if after_bytes < before_bytes:
            ratio = (1 - after_bytes / before_bytes) * 100
            color = COLOR_EXITO
            icon = "📉"
        else:
            ratio = 0
            color = COLOR_ERROR
            icon = "⚠️"

        row = tk.Frame(self.result_frame, bg=COLOR_LILA, padx=12, pady=8)
        row.pack(fill="x", pady=(4, 0))

        tk.Label(row, text=f"{before_mb:.1f} MB", font=FONT_BOLD,
                 fg=COLOR_INK_MUTED, bg=COLOR_LILA).pack(side="left")
        tk.Label(row, text="  →  ", font=FONT_PRIMARY,
                 fg=COLOR_INK_MUTED, bg=COLOR_LILA).pack(side="left")
        tk.Label(row, text=f"{after_mb:.1f} MB", font=FONT_BOLD,
                 fg=color, bg=COLOR_LILA).pack(side="left")

        if ratio > 0:
            tk.Label(row, text=f"    {icon} -{ratio:.1f}%", font=FONT_BOLD,
                     fg=color, bg=COLOR_LILA).pack(side="left", padx=(8, 0))
        else:
            tk.Label(row, text=f"    {icon} Sin reducción", font=FONT_BOLD,
                     fg=color, bg=COLOR_LILA).pack(side="left", padx=(8, 0))

    def _open_output_folder(self):
        if self.output_path:
            folder = os.path.dirname(self.output_path)
            if os.path.isdir(folder):
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    os.system(f'open "{folder}"')
                else:
                    os.system(f'xdg-open "{folder}"')

    # ── Ejecutar compresión ──
    def _run_compress(self):
        if self.running:
            return

        pdf_path = self.selected_file.get()
        if not pdf_path or not os.path.isfile(pdf_path):
            messagebox.showwarning("Sin archivo", "Selecciona un PDF primero.")
            return

        out_name = self.output_name_var.get().strip()
        if not out_name:
            stem = Path(pdf_path).stem
            stamp = datetime.now().strftime("%y%m%d%H%M%S")
            out_name = f"{stem}_compress{stamp}.pdf"
        if not out_name.lower().endswith(".pdf"):
            out_name += ".pdf"

        out_dir = os.path.dirname(pdf_path)
        out_full = os.path.join(out_dir, out_name)

        if os.path.isfile(out_full):
            if not messagebox.askyesno("Archivo existe",
                                       f"{out_name} ya existe.\n¿Sobrescribir?"):
                return

        self.running = True
        self.btn_compress.config(state="disabled", text="  Comprimiendo...  ")
        self.btn_open_folder.config(state="disabled")
        self._clear_log()
        self.progress["value"] = 0
        for w in self.result_frame.winfo_children():
            w.destroy()

        self.compressor = PDFCompressor()

        def worker():
            try:
                def progress_cb(cur, tot, msg):
                    self.after(0, self._update_progress, cur, tot, msg)

                result_path, processed, before, after = self.compressor.compress_pdf(
                    input_pdf=pdf_path,
                    output_path=out_full,
                    quality=self.quality_var.get(),
                    max_width=self.max_w_var.get(),
                    max_height=self.max_h_var.get(),
                    grayscale=self.grayscale_var.get(),
                    structural_optimize=self.struct_opt_var.get(),
                    progress_cb=progress_cb
                )

                self.output_path = result_path

                def on_done():
                    self.progress["value"] = 100
                    self.progress_label.config(text="¡Listo!")
                    self._show_result(before, after)
                    self._log(f"✅ {processed} imágenes recomprimidas")
                    self._log(f"📄 {os.path.basename(result_path)}")
                    self._log(f"📁 {os.path.dirname(result_path)}")
                    self.btn_compress.config(state="normal", text="  Comprimir PDF  ")
                    self.btn_open_folder.config(state="normal")
                    self.running = False

                self.after(0, on_done)

            except Exception as e:
                log.exception("Error al comprimir %s", pdf_path)

                def on_error():
                    self._log(f"❌ Error: {e}")
                    self._log(f"Detalle técnico en: {RUTA_LOG}")
                    self.progress_label.config(text="Error")
                    self.btn_compress.config(state="normal", text="  Comprimir PDF  ")
                    self.running = False
                self.after(0, on_error)

        threading.Thread(target=worker, daemon=True).start()


def main() -> int:
    args = crear_parser().parse_args()
    app = CompressPDFApp(args.pdf)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
