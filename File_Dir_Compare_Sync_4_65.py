# File/Dir Compare & Sync by Roby 77
import os, re, json, unicodedata, time, threading, concurrent.futures, datetime, stat, subprocess, platform, shutil, tkinter as tk, traceback, fnmatch, hashlib, webbrowser, base64
from tkinter import ttk, filedialog, messagebox, simpledialog, font as tkfont

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _cartella_dati():
    """Cartella delle impostazioni, fuori da quella dello script.

    Windows: %APPDATA%\\MediaDirFileCompare; altri sistemi: ~/.config/MediaDirFileCompare.
    Se non è possibile crearla si ripiega sulla cartella dello script."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    cartella = os.path.join(base, "MediaDirFileCompare")
    try:
        os.makedirs(cartella, exist_ok=True)
        return cartella
    except OSError:
        return APP_DIR


DATA_DIR = _cartella_dati()
FILE_IMPOSTAZIONI = ("mediadirfile-settings.txt", "confronto_cartelle_filtri.txt",
                     "mediadirfile-ultima-destinazione.txt", "mediadirfile-button-style.txt",
                     "mediadirfile-sync-subfolder.txt")


def _migra_impostazioni():
    """Primo avvio dopo lo spostamento: copia le impostazioni dalla cartella dello script alla
    nuova cartella (solo se mancano lì). I vecchi file non vengono toccati né più usati."""
    if os.path.normcase(DATA_DIR) == os.path.normcase(APP_DIR):
        return
    for nome in FILE_IMPOSTAZIONI:
        vecchio, nuovo = os.path.join(APP_DIR, nome), os.path.join(DATA_DIR, nome)
        try:
            if os.path.isfile(vecchio) and not os.path.exists(nuovo):
                shutil.copy2(vecchio, nuovo)
        except OSError:
            pass


_migra_impostazioni()
CONFIG_FILE = os.path.join(DATA_DIR, "mediadirfile-settings.txt")
FILTER_CONFIG_FILE = os.path.join(DATA_DIR, "confronto_cartelle_filtri.txt")
LAST_DESTINATION_FILE = os.path.join(DATA_DIR, "mediadirfile-ultima-destinazione.txt")
PROFILI_FILE = os.path.join(DATA_DIR, "mediadirfile-profili.json")
# Versione 4.36: nuova grafica "Moderno" (temi moderno scuro/chiaro + stile pulsanti 7)
# Versione 4.37: Sincronizza 1→2 non si ferma più con "Confronto non disponibile in cache"
# Versione 4.38: Sincronizza 1→2 può creare la cartella di destinazione se non esiste (con conferma)
# Versione 4.39: Sincronizza 1→2 crea la sottocartella con il nome della sorgente nella destinazione (opzione)
# Versione 4.40: più spazio tra icona e nome dei file (stessa larghezza delle icone cartella)
# Versione 4.41: voce di menu "Filtri" rinominata "File da escludere"
# Versione 4.42: pulsanti principali con angoli arrotondati (PulsanteArrotondato, raggio in RAGGIO_PULSANTI)
# Versione 4.43: tutti i pulsanti principali hanno la stessa altezza
# Versione 4.44: pulsanti principali leggermente più grandi (font 11, spaziatura 18/10)
# Versione 4.45: impostazioni in %APPDATA%\MediaDirFileCompare (migrazione automatica dei file esistenti)
# Versione 4.46: riconoscimento file spostati/rinominati nella sincronizzazione; velocità, tempo residuo e notifica finale
# Versione 4.47: l'etichetta [CARTELLA MANCANTE] sta prima del nome (con nomi lunghi veniva tagliata dalla colonna)
# Versione 4.48: [CARTELLA MANCANTE] di nuovo dopo il nome; con nomi lunghi il nome viene accorciato con "…" per tenerla visibile
# Versione 4.49: rimossi i temi "Old style" (doppioni di Tema scuro/chiaro)
# Versione 4.50: tradotta la scritta "Risultati:" (italiano/inglese)
# Versione 4.51: cambio lingua dopo una scansione: tradotte anche [CARTELLA MANCANTE] e «File mancante» già presenti negli alberi
# Versione 4.52: rimosso lo stile pulsanti 2 "Piatto e minimale" (chi lo aveva salvato passa allo stile 1)
# Versione 4.53: "Stile moderno 2026" è la prima voce del dialogo Stile pulsanti
# Versione 4.54: corretta la conversione del tema Old style salvato (diventa Tema scuro/chiaro)
# Versione 4.55: profili con nome (sorgente + destinazione) dal pulsante «Profili»
# Versione 4.56: la preparazione della sincronizzazione si può annullare (X, Esc o pulsante Annulla)
# Versione 4.57: la X della finestra di copia/sincronizzazione chiede se interrompere o continuare con la finestra chiusa
# Versione 4.58: dopo un'interruzione il riepilogo conta e elenca anche i file rimasti da copiare
# Versione 4.59: dopo un'interruzione la schermata principale mostra in rosso «INTERROTTA» invece di «Confronto completato!»
# Versione 4.60: il programma si chiama «File/Dir Compare & Sync by Roby 77» (il file ora è File_Dir_Compare_Sync_4_60.py)
# Versione 4.61: [CARTELLA MANCANTE] simmetrica: compare sul pannello in cui la cartella manca (anche in sorgente)
# Versione 4.62: nuovo filtro «Nomi simili» (copie, (1), maiuscole/minuscole, accenti) nella finestra Filtra
# Versione 4.63: la finestra Rinomina propone il nome attuale (selezionato senza estensione)
# Versione 4.64: la rinomina accetta anche un cambio di sole maiuscole/minuscole (es. Atpc -> ATPC)
# Versione 4.65: la sincronizzazione allinea in destinazione i nomi che differiscono solo per maiuscole/minuscole
APP_VERSION = "4.65"
# Scansione di sorgente e destinazione in parallelo. Se le due cartelle stanno sullo stesso
# volume la scansione resta sequenziale (su un disco meccanico due letture simultanee
# fanno saltare la testina e possono essere più lente); metti True per forzare il parallelo.
SCANSIONE_PARALLELA_STESSO_DISCO = False
TEMI_SCURI = ("modern", "dark", "blue", "green", "purple", "darkgray")


def _mescola_colori(c1, c2, r):
    """Miscela due colori #rrggbb: r=0 -> c1, r=1 -> c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * r) for x, y in zip(a, b))
FONT_ETICHETTE_PERCORSI = ("Segoe UI", 11, "bold")

LOG_ERRORI_FILE = "confronto_cartelle_errori.log"
ATTESA_RIPROVA_SECONDI = 1.5          # attesa prima del secondo tentativo su file bloccati
STATO_MANCANTE, STATO_DIVERSO, STATO_ERRORE_LETTURA = "Mancante", "Diverso", "Errore lettura"
STATO_DATA_DIVERSA = "Data diversa"
IS_WINDOWS = os.name == "nt"
FILE_ATTRIBUTE_NORMAL = 0x80
# Attributi Windows impostabili con SetFileAttributesW: sola lettura, nascosto,
# sistema, archivio, temporaneo, offline, non indicizzato.
ATTRIBUTI_COPIABILI = 0x1 | 0x2 | 0x4 | 0x20 | 0x100 | 0x1000 | 0x2000


class ErroreVerificaHash(IOError):
    """Il contenuto copiato non coincide con la sorgente (SHA-256 diverso)."""


def _win_imposta_attributi(percorso, attributi):
    """Imposta gli attributi di un file su Windows (no-op sugli altri sistemi)."""
    if not IS_WINDOWS:
        return False
    import ctypes
    if not ctypes.windll.kernel32.SetFileAttributesW(str(percorso), int(attributi)):
        raise ctypes.WinError()
    return True


def _win_esegui_come_admin(programma, parametri):
    """Avvia un programma come amministratore (UAC), attende la fine e restituisce il codice di uscita."""
    import ctypes
    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD), ("hIconOrMonitor", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]

    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = programma
    info.lpParameters = parametri
    info.nShow = 0  # SW_HIDE
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        raise ctypes.WinError()  # 1223 = l'utente ha annullato la richiesta UAC
    kernel32 = ctypes.windll.kernel32
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    try:
        kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
        codice = wintypes.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(codice))
        return codice.value
    finally:
        kernel32.CloseHandle(info.hProcess)


def format_size(b):
    if b == "" or b is None: return ""
    try: b = int(b)
    except: return str(b)
    segno = "-" if b < 0 else ""
    b = abs(b)
    for u in ['B','KB','MB','GB','TB']:
        if b < 1024.0: return f"{segno}{b:.2f} {u}"
        b /= 1024.0
    return f"{segno}{b:.2f} PB"

_RE_COPIA_DI = re.compile(r"^(?:copia di|copy of)\s+")
_RE_NUMERO_FINALE = re.compile(r"[\s_.\-]*\(\d+\)\s*$")
# «copia»/«copy» come parola a sé (anche dopo «_» o «-»), ma non dentro «photocopy»
_RE_COPIA_FINALE = re.compile(r"[\s_.\-]*(?<![^\W_])(?:copia|copy)(?![^\W_])(?:[\s_.\-]*\(?\d+\)?)?\s*$")


def chiave_nome_simile(nome):
    """Forma normalizzata di un nome file per riconoscere copie e varianti.

    Ignora maiuscole/minuscole, accenti, punteggiatura e spazi multipli, i suffissi
    «(1)», «- Copia», «copy», «_copy 2» e il prefisso «Copia di». L'estensione resta
    parte della chiave: «brano.flac» e «brano.mp3» non sono varianti."""
    base, estensione = os.path.splitext(nome)
    b = unicodedata.normalize("NFKD", base)
    b = "".join(c for c in b if not unicodedata.combining(c)).casefold()
    b = _RE_COPIA_DI.sub("", b)
    for _ in range(6):
        nuovo = _RE_COPIA_FINALE.sub("", _RE_NUMERO_FINALE.sub("", b))
        if nuovo == b:
            break
        b = nuovo
    b = re.sub(r"[\W_]+", " ", b).strip()
    return (b or base.casefold()) + estensione.casefold()


def trova_chiavi_nomi_simili(chiavi):
    """Chiavi (percorsi relativi) di file con nome simile a un altro file della STESSA cartella."""
    gruppi = {}
    for chiave in chiavi:
        cartella, nome = os.path.split(chiave)
        gruppi.setdefault((cartella.casefold(), chiave_nome_simile(nome)), set()).add(chiave)
    return {k for gruppo in gruppi.values() if len(gruppo) >= 2 for k in gruppo}


def format_durata(secondi):
    """Durata leggibile: 45 s, 3 min 12 s, 1 h 05 min."""
    try:
        secondi = max(0, int(round(secondi)))
    except (TypeError, ValueError):
        return ""
    if secondi < 60:
        return f"{secondi} s"
    if secondi < 3600:
        return f"{secondi // 60} min {secondi % 60:02d} s"
    return f"{secondi // 3600} h {(secondi % 3600) // 60:02d} min"


def format_date(t):
    if not t: return ""
    try: return datetime.datetime.fromtimestamp(float(t)).strftime('%Y-%m-%d %H:%M:%S')
    except: return ""

TEMES = {
    # Grafica moderna: superfici piatte, bordi sottili, un solo colore d'accento.
    "modern": {"bg": "#0e1116", "fg": "#e7eaf0", "entry_bg": "#171c24", "tree_bg": "#12161d", "tree_fg": "#cdd5e0", "mancante": "#f87171", "diverso": "#fbbf24", "ok": "#e7eaf0", "b_t": "#818cf8", "t_bg": "#171c24", "t_fg": "#e7eaf0", "accent": "#6366f1", "surface": "#151a22", "border": "#252d39", "muted": "#8b95a5"},
    "modern_light": {"bg": "#f5f6f8", "fg": "#111827", "entry_bg": "#ffffff", "tree_bg": "#ffffff", "tree_fg": "#1f2937", "mancante": "#dc2626", "diverso": "#b45309", "ok": "#111827", "b_t": "#4f46e5", "t_bg": "#ffffff", "t_fg": "#111827", "accent": "#4f46e5", "surface": "#ffffff", "border": "#e3e7ed", "muted": "#6b7280"},
    "dark": {"bg": "#0b1624", "fg": "#e6f0ff", "entry_bg": "#10243a", "tree_bg": "#081321", "tree_fg": "#d9e8fb", "mancante": "#ff6b6b", "diverso": "#ffca28", "ok": "#ffffff", "b_t": "#ffb300", "t_bg": "#2d2d3a", "t_fg": "#ffffff"},
    "light": {"bg": "#eef3f8", "fg": "#172b43", "entry_bg": "#ffffff", "tree_bg": "#ffffff", "tree_fg": "#263b53", "mancante": "#dc2626", "diverso": "#d97706", "ok": "#0f172a", "b_t": "#ff9800", "t_bg": "#ffffff", "t_fg": "#1e293b"},
    # Temi aggiuntivi ispirati ai render: blu, verde, viola e grigio scuro.
    "blue": {"bg": "#071b35", "fg": "#e6f4ff", "entry_bg": "#0b2d54", "tree_bg": "#062344", "tree_fg": "#d8efff", "mancante": "#fb7185", "diverso": "#fbbf24", "ok": "#e0f2fe", "b_t": "#38bdf8", "t_bg": "#0b2d54", "t_fg": "#e6f4ff"},
    "green": {"bg": "#062b2a", "fg": "#d9fff5", "entry_bg": "#0b3d3a", "tree_bg": "#052523", "tree_fg": "#d1fae5", "mancante": "#fb7185", "diverso": "#fbbf24", "ok": "#ecfdf5", "b_t": "#34d399", "t_bg": "#0b3d3a", "t_fg": "#ecfdf5"},
    "purple": {"bg": "#1b1033", "fg": "#f3e8ff", "entry_bg": "#2b1850", "tree_bg": "#160d2b", "tree_fg": "#f3e8ff", "mancante": "#fb7185", "diverso": "#fbbf24", "ok": "#faf5ff", "b_t": "#c084fc", "t_bg": "#2b1850", "t_fg": "#faf5ff"},
    "darkgray": {"bg": "#202a35", "fg": "#edf2f7", "entry_bg": "#2c3947", "tree_bg": "#18212b", "tree_fg": "#e2e8f0", "mancante": "#fb7185", "diverso": "#fbbf24", "ok": "#f8fafc", "b_t": "#94a3b8", "t_bg": "#2c3947", "t_fg": "#f8fafc"}
}
# --- Icone per tipo di file, disegnate dal programma (nessuna dipendenza esterna) ---
# Larghezza 23 = quella dell'icona cartella: nomi allineati e ~9 px liberi dopo il disegno.
ICONA_W, ICONA_H = 23, 18
ICONE_FILE = {
    # categoria: (colore pagina, glifo bianco)
    "audio":    ("#a855f7", ("...###.", "...#..#", "...#...", "...#...", ".###...", ".###...")),
    "video":    ("#ec4899", ("#......", "###....", "#####..", "#######", "#####..", "###....", "#......")),
    "immagine": ("#14b8a6", (".......", "...#...", "..###..", ".#####.", "#######")),
    "documento": ("#3b82f6", ("#######", ".......", "#######", ".......", "#####..")),
    "foglio":   ("#16a34a", ("###.###", ".......", "###.###", ".......", "###.###")),
    "archivio": ("#a16207", ("...#...", "..##...", "...##..", "..##...", "...##..", "..##...")),
    "codice":   ("#475569", (".#...#.", "#.....#", "#.....#", "#.....#", ".#...#.")),
    "eseguibile": ("#0ea5e9", (".#####.", "#.....#", "#.###.#", "#.....#", ".#####.")),
    "generico": ("#94a3b8", (".......", "#####..", ".......", "#####..")),
}
_EST_PER_CATEGORIA = {
    "audio": "mp3 flac wav aac ogg m4a wma aiff aif opus ape alac mid midi",
    "video": "mp4 mkv avi mov wmv flv webm m4v mpg mpeg",
    "immagine": "jpg jpeg png gif bmp tif tiff webp svg heic ico raw cr2 nef arw psd",
    "documento": "pdf doc docx odt rtf txt md ppt pptx odp epub log",
    "foglio": "xls xlsx csv ods tsv",
    "archivio": "zip rar 7z tar gz bz2 xz iso cab",
    "codice": "py js html htm css json xml ini cfg bat ps1 sh c cpp h java cs sql yml yaml",
    "eseguibile": "exe msi dll sys",
}
EST_CATEGORIA = {"." + e: cat for cat, elenco in _EST_PER_CATEGORIA.items() for e in elenco.split()}


def rette_icona(categoria):
    """Rettangoli (x0, y0, x1, y1, colore) che compongono l'icona; solo righe orizzontali."""
    colore, glifo = ICONE_FILE.get(categoria, ICONE_FILE["generico"])
    bordo = _mescola_colori(colore, "#000000", 0.38)
    piega = _mescola_colori(colore, "#ffffff", 0.6)
    x0, x1, y0, y1, f = 2, 13, 1, 16, 4
    gw, gh = len(glifo[0]), len(glifo)
    gx = x0 + (x1 - x0 + 1 - gw) // 2
    gy = y0 + (y1 - y0 + 1 - gh) // 2 + 2
    righe = []
    for y in range(y0, y1 + 1):
        riga = []
        for x in range(x0, x1 + 1):
            d = (x1 - x) + (y - y0)
            if d < f:
                c = None                                   # angolo tagliato
            elif d == f:
                c = bordo                                  # diagonale della piega
            elif x > x1 - f and y < y0 + f:
                c = piega                                  # lembo piegato
            elif x in (x0, x1) or y in (y0, y1):
                c = bordo
            else:
                c = colore
                gxx, gyy = x - gx, y - gy
                if 0 <= gyy < gh and 0 <= gxx < gw and glifo[gyy][gxx] == "#":
                    c = "#ffffff"
            riga.append(c)
        # unisce i pixel consecutivi dello stesso colore
        i = 0
        while i < len(riga):
            if riga[i] is None:
                i += 1
                continue
            j = i
            while j + 1 < len(riga) and riga[j + 1] == riga[i]:
                j += 1
            righe.append((x0 + i, y, x0 + j + 1, y + 1, riga[i]))
            i = j + 1
    return righe


# --- Pulsanti con angoli arrotondati --------------------------------------------------
RAGGIO_PULSANTI = 10   # raggio degli angoli in pixel (0-2 = quasi squadrato)
# Dimensioni dei pulsanti principali nello stile moderno (prima: font 10, spaziatura 14/8).
PULSANTI_FONT, PULSANTI_PADX, PULSANTI_PADY = 11, 18, 10
_FONT_CACHE = {}


def _font_tk(specifica):
    chiave = str(specifica)
    f = _FONT_CACHE.get(chiave)
    if f is None:
        f = _FONT_CACHE[chiave] = tkfont.Font(font=specifica)
    return f


class PulsanteArrotondato(tk.Canvas):
    """Pulsante con angoli arrotondati disegnato su un Canvas.

    Accetta e restituisce le stesse opzioni di tk.Button usate dal programma (text, command,
    image, compound, bg, fg, activebackground, disabledforeground, font, padx, pady, state,
    highlightthickness, highlightbackground, cursor, takefocus) e supporta cget(), config(),
    invoke(), bind() e pack(). Le opzioni senza significato per un pulsante disegnato
    (relief, bd, ...) vengono ignorate."""

    _tag_legato = False
    _ALIAS = {"foreground": "fg", "background": "bg", "borderwidth": "bd"}

    def __init__(self, master, **opzioni):
        self._o = {
            "text": "", "command": None, "image": None, "compound": "left",
            "fg": "white", "bg": "#2563eb", "activebackground": None, "activeforeground": None,
            "disabledforeground": None, "font": ("Segoe UI", 10, "bold"), "padx": 14, "pady": 8,
            "state": "normal", "raggio": RAGGIO_PULSANTI, "altezza_fissa": 0,
            "highlightthickness": 0, "highlightbackground": None,
        }
        self._dy = 0
        self._premuto = False
        self._con_focus = False
        cursore = opzioni.pop("cursor", "hand2")
        focus = opzioni.pop("takefocus", True)
        super().__init__(master, bd=0, highlightthickness=0, relief="flat",
                         cursor=cursore, takefocus=focus)
        self.configure(**opzioni)
        if not PulsanteArrotondato._tag_legato:
            for sequenza, funzione in (
                    ("<ButtonPress-1>", PulsanteArrotondato._ev_premi),
                    ("<ButtonRelease-1>", PulsanteArrotondato._ev_rilascia),
                    ("<Configure>", PulsanteArrotondato._ev_dimensione),
                    ("<FocusIn>", PulsanteArrotondato._ev_focus_in),
                    ("<FocusOut>", PulsanteArrotondato._ev_focus_out),
                    ("<KeyRelease-space>", PulsanteArrotondato._ev_tasto),
                    ("<Return>", PulsanteArrotondato._ev_tasto)):
                self.bind_class("PulsanteArrotondato", sequenza, funzione)
            PulsanteArrotondato._tag_legato = True
        # Tag di binding separato: bind() sul widget (hover, tooltip) non lo sostituisce.
        tag = list(self.bindtags())
        tag.insert(1, "PulsanteArrotondato")
        self.bindtags(tuple(tag))

    # --- API compatibile con tk.Button -------------------------------------------------
    def configure(self, cnf=None, **kw):
        if isinstance(cnf, str):
            return self.cget(cnf)
        if cnf:
            kw = {**cnf, **kw}
        if not kw:
            return super().configure()
        cambiato = False
        passa = {}
        for chiave, valore in kw.items():
            chiave = self._ALIAS.get(chiave, chiave)
            if chiave in self._o:
                if chiave in ("padx", "pady", "highlightthickness", "raggio", "altezza_fissa"):
                    try:
                        valore = int(float(valore))
                    except (TypeError, ValueError):
                        continue
                self._o[chiave] = valore
                cambiato = True
            elif chiave in ("cursor", "takefocus"):
                passa[chiave] = valore
            # relief, bd, highlightcolor, anchor, ... : ignorate
        if passa:
            super().configure(**passa)
        if cambiato:
            self._aggiorna_dimensioni()
            self._ridisegna()
        return None

    config = configure

    def cget(self, chiave):
        chiave = self._ALIAS.get(chiave, chiave)
        if chiave in self._o:
            return self._o[chiave]
        if chiave == "relief":
            return "flat"
        if chiave == "bd":
            return 0
        return super().cget(chiave)

    __getitem__ = cget

    def invoke(self):
        if str(self._o["state"]) == "disabled":
            return None
        comando = self._o["command"]
        return comando() if comando else None

    def flash(self):
        pass

    def aggiorna_sfondo(self):
        """Ridisegna dopo un cambio di tema (il colore dietro gli angoli segue il contenitore)."""
        self._ridisegna()

    # --- misure e disegno ----------------------------------------------------------------
    def _hex(self, colore, predefinito="#000000"):
        try:
            r, g, b = self.winfo_rgb(colore)
            return "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)
        except (tk.TclError, TypeError, ValueError, AttributeError):
            return predefinito

    def _sfondo_genitore(self):
        try:
            return self._hex(self.master.cget("bg"), "#000000")
        except (tk.TclError, AttributeError):
            return "#000000"

    def _larghezza_immagine(self):
        img = self._o["image"]
        try:
            return (img.width(), img.height()) if img else (0, 0)
        except (tk.TclError, AttributeError):
            return (0, 0)

    def _dimensioni_richieste(self):
        f = _font_tk(self._o["font"])
        testo = str(self._o["text"] or "")
        larg_t = f.measure(testo) if testo else 0
        larg_i, alt_i = self._larghezza_immagine()
        spazio = 8 if (larg_i and testo) else 0
        larghezza = int(self._o["padx"]) * 2 + larg_i + spazio + larg_t
        altezza = int(self._o["pady"]) * 2 + max(f.metrics("linespace"), alt_i)
        if int(self._o["altezza_fissa"] or 0) > 0:
            altezza = int(self._o["altezza_fissa"])   # altezza uniforme imposta dal programma
        return max(larghezza, 8), max(altezza, 8)

    def _aggiorna_dimensioni(self):
        larghezza, altezza = self._dimensioni_richieste()
        super().configure(width=larghezza, height=altezza)

    def _rettangolo(self, x1, y1, x2, y2, r, riempimento, contorno="", **extra):
        y1 += self._dy
        y2 += self._dy
        p = [x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y1 + r,
             x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
             x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1]
        return self.create_polygon(p, smooth=True, fill=riempimento, outline=contorno, **extra)

    def _ridisegna(self):
        o = self._o
        larghezza, altezza = self.winfo_width(), self.winfo_height()
        richiesta = self._dimensioni_richieste()
        if larghezza <= 1:
            larghezza = richiesta[0]
        if altezza <= 1:
            altezza = richiesta[1]
        # Se il contenitore concede più altezza del previsto, il pulsante resta dell'altezza
        # uniforme e viene centrato in verticale (così tutti i pulsanti risultano uguali).
        fissa = int(o["altezza_fissa"] or 0)
        self._dy = 0
        if fissa and altezza > fissa:
            self._dy = (altezza - fissa) // 2
            altezza = fissa
        sfondo = self._sfondo_genitore()
        super().configure(bg=sfondo)
        self.delete("all")
        disabilitato = str(o["state"]) == "disabled"
        riempimento = self._hex(o["bg"], "#2563eb")
        if self._premuto and not disabilitato:
            riempimento = _mescola_colori(riempimento, "#000000", 0.2)
        if disabilitato:
            colore_testo = (self._hex(o["disabledforeground"]) if o["disabledforeground"]
                            else _mescola_colori(self._hex(o["fg"], "#ffffff"), riempimento, 0.55))
        else:
            colore_testo = self._hex(o["fg"], "#ffffff")
        r = max(1, min(int(o["raggio"]), altezza // 2, larghezza // 2))
        spessore = int(o["highlightthickness"] or 0)
        if spessore > 0 and o["highlightbackground"]:
            self._rettangolo(0, 0, larghezza - 1, altezza - 1, r, self._hex(o["highlightbackground"]))
            self._rettangolo(spessore, spessore, larghezza - 1 - spessore, altezza - 1 - spessore,
                             max(1, r - spessore), riempimento)
        else:
            # Bordo di 1 px a metà tra pulsante e sfondo: ammorbidisce gli angoli (Canvas senza antialiasing).
            self._rettangolo(0, 0, larghezza - 1, altezza - 1, r, _mescola_colori(riempimento, sfondo, 0.5))
            self._rettangolo(1, 1, larghezza - 2, altezza - 2, max(1, r - 1), riempimento)
        if self._con_focus and not disabilitato:
            self._rettangolo(3, 3, larghezza - 4, altezza - 4, max(1, r - 3), "",
                             contorno=colore_testo, dash=(2, 2))
        testo = str(o["text"] or "")
        larg_i, _alt_i = self._larghezza_immagine()
        centro_y = altezza / 2 + self._dy
        larg_t = _font_tk(o["font"]).measure(testo) if testo else 0
        spazio = 8 if (larg_i and testo) else 0
        x = larghezza / 2 - (larg_i + spazio + larg_t) / 2
        if larg_i:
            self.create_image(x, centro_y, image=o["image"], anchor="w")
            x += larg_i + spazio
        if testo:
            self.create_text(x, centro_y, text=testo, font=o["font"], fill=colore_testo, anchor="w")

    # --- eventi (tag di binding dedicato) -------------------------------------------------
    @staticmethod
    def _ev_premi(e):
        b = e.widget
        if isinstance(b, PulsanteArrotondato) and str(b._o["state"]) != "disabled":
            b._premuto = True
            b._ridisegna()

    @staticmethod
    def _ev_rilascia(e):
        b = e.widget
        if not isinstance(b, PulsanteArrotondato):
            return
        era_premuto = b._premuto
        b._premuto = False
        b._ridisegna()
        if era_premuto and 0 <= e.x < b.winfo_width() and 0 <= e.y < b.winfo_height():
            b.invoke()

    @staticmethod
    def _ev_dimensione(e):
        if isinstance(e.widget, PulsanteArrotondato):
            e.widget._ridisegna()

    @staticmethod
    def _ev_focus_in(e):
        if isinstance(e.widget, PulsanteArrotondato):
            e.widget._con_focus = True
            e.widget._ridisegna()

    @staticmethod
    def _ev_focus_out(e):
        if isinstance(e.widget, PulsanteArrotondato):
            e.widget._con_focus = False
            e.widget._ridisegna()

    @staticmethod
    def _ev_tasto(e):
        if isinstance(e.widget, PulsanteArrotondato):
            e.widget.invoke()


class EtichettaStato(tk.Label):
    """Riga di stato principale. `avviso()` mostra un messaggio in rosso che resta finché il
    testo non viene sostituito da un altro (poi il colore torna quello del tema)."""

    def __init__(self, master, **kw):
        self._testo_avviso = None
        self._colore_normale = None
        super().__init__(master, **kw)

    def avviso(self, testo, colore="#dc2626"):
        if self._testo_avviso is None:
            self._colore_normale = str(self.cget("fg"))
        self._testo_avviso = testo
        super().configure(text=testo, fg=colore)

    def in_avviso(self):
        return self._testo_avviso is not None

    def configure(self, cnf=None, **kw):
        if isinstance(cnf, dict):
            kw, cnf = {**cnf, **kw}, None
        if self._testo_avviso is not None:
            for chiave in ("fg", "foreground"):
                if chiave in kw:
                    self._colore_normale = kw.pop(chiave)   # il tema cambia: l'avviso resta rosso
            if "text" in kw and kw["text"] != self._testo_avviso:
                self._testo_avviso = None                    # nuovo testo: fine dell'avviso
                kw["fg"] = self._colore_normale
        return super().configure(cnf, **kw)

    config = configure


class CopiaInterrotta(Exception):
    """Sollevata per fermare una copia su richiesta dell'utente."""


class Tooltip:
    """Mostra una breve spiegazione quando il puntatore resta su un widget."""
    def __init__(self, widget, testo, delay=500):
        self.widget = widget
        self.testo = testo
        self.delay = delay
        self._after_id = None
        self._window = None
        widget.bind("<Enter>", self._programma, add="+")
        widget.bind("<Leave>", self._nascondi, add="+")
        widget.bind("<ButtonPress>", self._nascondi, add="+")

    def _programma(self, event=None):
        self._cancella_timer()
        self._after_id = self.widget.after(self.delay, self._mostra)

    def _mostra(self):
        self._after_id = None
        if self._window or not self.testo:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self._window = tk.Toplevel(self.widget)
            self._window.wm_overrideredirect(True)
            self._window.wm_geometry(f"+{x}+{y}")
            tk.Label(self._window, text=self.testo, justify="left",
                     bg="#111827", fg="#f3f4f6", relief="flat", bd=0,
                     highlightthickness=1, highlightbackground="#374151",
                     font=("Segoe UI", 9), padx=10, pady=6, wraplength=360).pack()
        except tk.TclError:
            self._window = None

    def _cancella_timer(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _nascondi(self, event=None):
        self._cancella_timer()
        if self._window is not None:
            try:
                self._window.destroy()
            except tk.TclError:
                pass
            self._window = None


class AppConfrontoCartelle:
    def __init__(self, root):
        self.root = root; self.current_theme = "modern"; self.filtro_mancanti_attivo = False; self.filtro_data_diversa_attivo = False; self.filtro_data_recente_attivo = False; self.filtro_data_vecchia_attivo = False; self.filtro_dimensione_diversa_attivo = False; self.lock_sync = False
        self.root.title(f"File/Dir Compare & Sync by Roby 77 - {APP_VERSION}"); self.root.geometry("1540x920"); self.root.minsize(1100, 680)
        # Avvia la finestra massimizzata (a tutto schermo disponibile, senza modalità fullscreen).
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass
        self._cattura_default_tk()
        self._nodi_cartella_mancante = {}; self._nodi_cartella_mancante1 = {}
        self.cronologia_c1, self.cronologia_c2, self.folder_cache = [], [], {}
        self.stile_pulsanti = self._carica_stile_pulsanti()
        self.var_sync_sottocartella = tk.BooleanVar(value=self._carica_sync_sottocartella())
        self.profili = self._carica_profili()
        self.sort_by = "name"; self.sort_reverse = False
        self.filtri_esclusione = []
        self._copia_interrotta = threading.Event(); self._copia_nascosta = False; self._avviso_dopo_confronto = None
        self.is_scanning = False; self._confronto_eseguito = False; self._cancel_scan = threading.Event(); self._preview_dopo_confronto = False; self._preview_in_corso = False; self.style = ttk.Style(); self.style.theme_use("clam")
        # Icona cartella disegnata dall'app: gialla in modo coerente su Windows/Linux,
        # senza dipendere dalle emoji del font installato.
        self.folder_icon = tk.PhotoImage(width=23, height=14)
        self.folder_icon.put("#d99a00", to=(1, 2, 7, 5))
        self.folder_icon.put("#ffd54a", to=(1, 4, 15, 13))
        self.folder_icon.put("#f2b705", to=(1, 5, 14, 12))
        self.folder_icon.put("#ffe27a", to=(2, 5, 14, 6))
        self.folder_icon.put("#b77900", to=(1, 12, 15, 13))

        # Carattere leggibile anche nell’elenco a discesa dei percorsi.
        root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 12))
        self.frame_top = tk.Frame(root, padx=15, pady=5); self.frame_top.pack(fill="x")
        self.f_barra = tk.Frame(self.frame_top); self.f_barra.pack(fill="x", pady=(18, 8))
        # I selettori sono raggruppati verticalmente per rendere espliciti i ruoli.
        self.frame_sorgente = tk.Frame(self.f_barra)
        self.frame_sorgente.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.lbl_sorgente = tk.Label(self.frame_sorgente, text="Sorgente", font=FONT_ETICHETTE_PERCORSI, anchor="w")
        self.frame_sorgente.configure(height=62)
        self.frame_sorgente.pack_propagate(False)
        self.lbl_sorgente.place(x=0, y=-8, relwidth=1.0, height=24)
        self.riga_sorgente = tk.Frame(self.frame_sorgente)
        self.riga_sorgente.place(x=0, y=25, relwidth=1.0, height=34)
        self.combo_c1 = ttk.Combobox(self.riga_sorgente, font=("Segoe UI", 12), height=12); self.combo_c1.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=3)
        self.btn_cartella1 = tk.Canvas(self.riga_sorgente, width=32, height=30, bg="#475569", highlightthickness=0, cursor="hand2")
        self.btn_cartella1.pack(side="left", padx=(2, 4))
        self._disegna_icona_cartella(self.btn_cartella1)
        self.btn_cartella1.bind("<Button-1>", lambda event: self.sfoglia_cartella(1))
        tk.Label(self.f_barra, text="⇄", font=("Segoe UI Symbol", 20, "bold")).pack(side="left", padx=4, pady=(12, 0))
        self.frame_destinazione = tk.Frame(self.f_barra)
        self.frame_destinazione.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.lbl_destinazione = tk.Label(self.frame_destinazione, text="Destinazione", font=FONT_ETICHETTE_PERCORSI, anchor="w")
        self.frame_destinazione.configure(height=62)
        self.frame_destinazione.pack_propagate(False)
        self.lbl_destinazione.place(x=0, y=-8, relwidth=1.0, height=24)
        self.riga_destinazione = tk.Frame(self.frame_destinazione)
        self.riga_destinazione.place(x=0, y=25, relwidth=1.0, height=34)
        self.combo_c2 = ttk.Combobox(self.riga_destinazione, font=("Segoe UI", 12), height=12); self.combo_c2.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=3)
        self.btn_cartella2 = tk.Canvas(self.riga_destinazione, width=32, height=30, bg="#475569", highlightthickness=0, cursor="hand2")
        self.btn_cartella2.pack(side="left", padx=(2, 4))
        self._disegna_icona_cartella(self.btn_cartella2)
        self.btn_cartella2.bind("<Button-1>", lambda event: self.sfoglia_cartella(2))
        tk.Button(self.f_barra, text="⌫", command=self.elimina_cronologia, bg="#334155", fg="#f1f5f9", activebackground="#475569", activeforeground="white", font=("Segoe UI Symbol", 14, "bold"), relief="flat", bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=(0, 5), anchor="s", pady=(0, 7))
        self.btn_cancella_cronologia = self.f_barra.winfo_children()[-1]
        self.btn_impostazioni_stile = tk.Button(
            self.f_barra, text="⚙  Stile pulsanti", command=self.apri_impostazioni_stile,
            bg="#334155", fg="white", activebackground="#475569", activeforeground="white",
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0, padx=9, pady=5, cursor="hand2"
        )
        self.btn_impostazioni_stile.pack(side="left", padx=(0, 5), anchor="s", pady=(0, 7))
        self.btn_tema = tk.Button(
            self.f_barra, text="◐  Menu temi  ▾", command=self.mostra_menu_tema,
            bg="#475569", fg="white", activebackground="#64748b",
            activeforeground="white", font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0, padx=9, pady=5, cursor="hand2"
        )
        self.btn_tema.pack(side="left", padx=(0, 5), anchor="s", pady=(0, 7))
        self.btn_lingua = tk.Button(
            self.f_barra, text="🇬🇧 English", command=self.cambia_lingua,
            bg="#0f766e", fg="white", activebackground="#115e59",
            activeforeground="white", font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2"
        )
        self.btn_lingua.pack(side="left", anchor="s", pady=(0, 7))
        # Menu unico per le preferenze dell'interfaccia.
        self.menu_impostazioni = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 10))
        self.menu_impostazioni.add_command(label="◐  Temi", command=self.mostra_menu_tema)
        self.menu_impostazioni.add_command(label="🎨  Stile pulsanti", command=self.apri_impostazioni_stile)
        self.menu_impostazioni.add_command(label="⛃  File da escludere", command=self.apri_finestra_filtri)
        self.menu_impostazioni.add_checkbutton(
            label="📁  Sincronizza dentro una cartella con il nome della sorgente",
            variable=self.var_sync_sottocartella, command=self._salva_sync_sottocartella)
        self.menu_impostazioni.add_command(label="🌐  Lingua / Language", command=self.cambia_lingua)
        self.btn_profili = tk.Button(
            self.f_barra, text="★  Profili ▾", command=self.mostra_menu_profili,
            bg="#334155", fg="white", activebackground="#475569", activeforeground="white",
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0, padx=10, pady=5, cursor="hand2"
        )
        self.btn_profili.pack(side="left", padx=(0, 5), anchor="s", pady=(0, 7))
        self.btn_impostazioni = tk.Button(
            self.f_barra, text="⚙  Impostazioni ▾", command=self.mostra_menu_impostazioni,
            bg="#334155", fg="white", activebackground="#475569", activeforeground="white",
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0, padx=10, pady=5, cursor="hand2"
        )
        self.btn_impostazioni.pack(side="left", padx=(0, 5), anchor="s", pady=(0, 7))
        # Le tre voci sono ora raccolte nel menu Impostazioni.
        self.btn_impostazioni_stile.pack_forget()
        self.btn_tema.pack_forget()
        self.btn_lingua.pack_forget()
        self.btn_aiuto = tk.Button(
            self.f_barra, text="?", command=self.apri_aiuto_contatti,
            bg="#1d4ed8", fg="white", activebackground="#1e40af",
            activeforeground="white", font=("Segoe UI", 11, "bold"),
            relief="flat", bd=0, width=3, padx=5, pady=5, cursor="hand2"
        )
        self.btn_aiuto.pack(side="left", padx=(6, 0), anchor="s", pady=(0, 7))
        self.lingua = "it"
        self.albero_attivo = None
        self.nodo_attivo = None
        self.menu_tema = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 11))
        self.menu_tema.add_command(label="✦  Moderno scuro", command=lambda: self.scegli_tema("modern"))
        self.menu_tema.add_command(label="✧  Moderno chiaro", command=lambda: self.scegli_tema("modern_light"))
        self.menu_tema.add_separator()
        self.menu_tema.add_command(label="☾  Tema scuro", command=lambda: self.scegli_tema("dark"))
        self.menu_tema.add_command(label="☼  Tema chiaro", command=lambda: self.scegli_tema("light"))
        self.menu_tema.add_command(label="🔵  Tema blu", command=lambda: self.scegli_tema("blue"))
        self.menu_tema.add_command(label="🟢  Tema verde", command=lambda: self.scegli_tema("green"))
        self.menu_tema.add_command(label="🟣  Tema viola", command=lambda: self.scegli_tema("purple"))
        self.menu_tema.add_command(label="◼  Tema grigio scuro", command=lambda: self.scegli_tema("darkgray"))
        self.frame_ctrl = tk.Frame(root, padx=25, pady=2); self.frame_ctrl.pack(fill="x")
        self.lbl_status = EtichettaStato(self.frame_ctrl, text="Pronto per la scansione", font=("Arial", 14, "bold")); self.lbl_status.pack(side="left")
        # Riga dedicata alle dimensioni: sempre visibile sotto lo stato.
        self.frame_dimensioni = tk.Frame(root, pady=4)
        self.frame_dimensioni.pack(fill="x")
        self.lbl_dimensione_c1 = tk.Label(
            self.frame_dimensioni, text="Sorgente: in attesa della scansione",
            font=("Arial", 11, "bold"), anchor="w"
        )
        self.lbl_dimensione_c1.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.lbl_dimensione_c2 = tk.Label(
            self.frame_dimensioni, text="Da confrontare: in attesa della scansione",
            font=("Arial", 11, "bold"), anchor="e"
        )
        self.lbl_dimensione_c2.pack(side="right", fill="x", expand=True, padx=(0, 25))
        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=100, mode="determinate", style="Green.Horizontal.TProgressbar"); self.progress_bar.pack(fill="x", padx=25, pady=4)

        fa = tk.Frame(root, pady=7); fa.pack(fill="x", padx=18)
        f_pulsanti_centrati = tk.Frame(fa); f_pulsanti_centrati.pack(anchor="center")
        # Stile pulsanti aggiornato: spaziatura uniforme, contrasto elevato e cursore interattivo.
        btn_style = {
            "relief": "flat", "bd": 0, "highlightthickness": 0,
            "font": ("Segoe UI", 12, "bold"), "pady": 9, "padx": 16,
            "fg": "white", "cursor": "hand2", "takefocus": True
        }

        gruppo_confronto = tk.LabelFrame(f_pulsanti_centrati, text="Confronto e visualizzazione", padx=12, pady=6, font=("Segoe UI", 9, "bold"))
        gruppo_confronto.pack(side="left", padx=4, pady=0, anchor="n")
        self.btn_avvia = PulsanteArrotondato(gruppo_confronto, bg="#2563eb", text="▶ Confronta", **btn_style, command=self.avvia_confronto); self.btn_avvia.pack(side="left", padx=2)
        self.btn_refresh = PulsanteArrotondato(gruppo_confronto, bg="#7c3aed", text="↻ Aggiorna", **btn_style, command=self.forza_refresh)  # mantenuto internamente per compatibilità; non mostrato
        # Icona cursori di regolazione, ispirata all'immagine fornita dall'utente.
        self._icona_filtra = tk.PhotoImage(data="iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAhklEQVR4nGNgGOqAEZ/k/////8MVMjLiVYsLMBFjODY+sQDFVeiGqKW8gbNvzREhzWCoj+E+INeFuADMPLgF5IYxLgAzD6eh2HxEjiNwRjK6YeT6kOxgITYJ4/QBsYZj4yMDvMkUHyCUhEdAMsUHSEnCZEUyKUl4tDTFbfDwT6ZDpjSlOQAAXI9dIt+BP/QAAAAASUVORK5CYII=")
        self.btn_filtra = PulsanteArrotondato(
            gruppo_confronto, text="Filtra", image=self._icona_filtra, compound="left",
            command=self.apri_finestra_filtra_visualizzazione,
            bg="#2563eb", activebackground="#3b82f6", activeforeground="white",
            **btn_style
        )
        self.btn_filtra.pack(side="left", padx=2)
        self.btn_espandi = PulsanteArrotondato(gruppo_confronto, bg="#059669", text="＋ Espandi", **btn_style, command=self.toggle_espandi_comprimi); self.btn_espandi.pack(side="left", padx=2)
        self.btn_stop = PulsanteArrotondato(gruppo_confronto, text="■ Stop scansione", bg="#b91c1c", activebackground="#991b1b", activeforeground="#ffffff", disabledforeground="#f3f4f6", **btn_style, command=self.annulla_scansione, state="disabled"); self.btn_stop.pack(side="left", padx=2)

        gruppo_sicurezza = tk.LabelFrame(f_pulsanti_centrati, text="Copia e sicurezza", padx=5, pady=4, font=("Segoe UI", 9, "bold"))
        gruppo_sicurezza.pack(side="left", padx=4, pady=0, anchor="n")
        self.btn_copia_tutto = PulsanteArrotondato(gruppo_sicurezza, bg="#0f766e", text="⇢ Copia modifiche", **btn_style, command=self.copia_tutte_modifiche_sinistra_destra); self.btn_copia_tutto.pack(side="left", padx=2)
        self.btn_sincronizza = PulsanteArrotondato(gruppo_sicurezza, bg="#b45309", text="⇢ Sincronizza 1 → 2", **btn_style, command=self.sincronizza_sinistra_destra); self.btn_sincronizza.pack(side="left", padx=2)
        self.btn_anteprima = PulsanteArrotondato(gruppo_sicurezza, bg="#0369a1", text="◉ Anteprima", **btn_style, command=self.anteprima_differenze); self.btn_anteprima.pack(side="left", padx=2)
        self.btn_spazio = PulsanteArrotondato(gruppo_sicurezza, bg="#64748b", text="▣ Spazio libero", **btn_style, command=self.verifica_spazio_libero); self.btn_spazio.pack(side="left", padx=2)

        # Feedback hover sobrio: schiarisce il pulsante al passaggio del mouse.
        # Non modifica i comandi né gli stati abilitato/disabilitato.
        for _btn, _hover in (
            (self.btn_avvia, "#3b82f6"),
            (self.btn_filtra, "#3b82f6"),
            (self.btn_espandi, "#10b981"),
            (self.btn_stop, "#dc2626"),
            (self.btn_copia_tutto, "#0d9488"), (self.btn_sincronizza, "#d97706"), (self.btn_anteprima, "#0284c7"),
            (self.btn_spazio, "#94a3b8")
        ):
            _btn.bind("<Enter>", lambda _e, b=_btn, c=_hover: b.config(
                bg=getattr(b, "_hover_bg", c) if str(b.cget("state")) != "disabled" else b.cget("bg")
            ))
            _btn.bind("<Leave>", lambda _e, b=_btn: b.config(
                bg=b._base_bg if hasattr(b, "_base_bg") else b.cget("bg")
            ))
            _btn._base_bg = _btn.cget("bg")
        self._applica_stile_pulsanti()
        # Uniforma l’altezza effettiva dopo che Tkinter ha calcolato le dimensioni
        # richieste da font, icona e stile corrente. Si riapplica anche ai cambi stile.
        self.root.after_idle(self._uniforma_altezza_pulsante_filtra)

        gruppo_filtro = tk.LabelFrame(f_pulsanti_centrati, text="Ricerca", padx=5, pady=4, font=("Segoe UI", 9, "bold"))
        gruppo_filtro.pack(side="left", padx=4, fill="y", anchor="n")
        tk.Label(gruppo_filtro, text="FILTRA NOME:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(2, 4))
        self.var_search = tk.StringVar(); self.var_search.trace_add("write", lambda *args: self.esegui_ricerca_testo())
        self.entry_search = ttk.Entry(gruppo_filtro, textvariable=self.var_search, font=("Segoe UI", 11, "bold"), width=18, style="Search.TEntry"); self.entry_search.pack(side="left", padx=(2, 3), ipady=4)

        # Suggerimenti al passaggio del mouse per pulsanti, icone e filtro.
        suggerimenti = [
            (self.f_barra.winfo_children()[1], "Sfoglia e scegli la cartella sorgente (sinistra)."),
            (self.f_barra.winfo_children()[5], "Elimina la cronologia delle cartelle recenti."),
            (self.f_barra.winfo_children()[6], "Svuota la cache usata per accelerare il confronto."),
            (self.btn_tema, "Scegli il tema: moderno, scuro, chiaro o colorato."),
            (self.btn_profili, self._t("Profili: salva e richiama coppie sorgente → destinazione con un nome.",
                                       "Profiles: save and recall named source → destination pairs.")),
            (self.btn_filtra, "Filtra solo la visualizzazione di entrambi gli alberi per dimensione, data o mancanti."),
            (self.btn_lingua, "Passa l'interfaccia tra italiano e inglese."),
            (self.btn_aiuto, "Apri i contatti per segnalazioni e richieste."),
            (self.btn_avvia, "Confronta le due cartelle selezionate e mostra file mancanti o diversi."),
            (self.btn_espandi, "Espande tutte le cartelle; se sono già espanse, le comprime."),
            (self.btn_stop, "Annulla la scansione delle cartelle in corso."),
            (self.btn_copia_tutto, "Copia da sinistra a destra tutti i file mancanti o diversi. Chiede conferma prima di procedere."),
            (self.btn_sincronizza, "Rende la cartella destra uguale alla sinistra: copia gli aggiornamenti ed elimina dalla destra gli elementi extra, dopo conferma."),
            (self.btn_anteprima, "Mostra prima della copia i file mancanti o diversi e lo spazio necessario, senza modificare i file."),
            (self.btn_spazio, "Controlla lo spazio libero nella cartella di destinazione."),
            (self.entry_search, "Digita parte di un nome per filtrare gli elementi mostrati."),
        ]
        for widget, testo in suggerimenti:
            Tooltip(widget, testo)

        # Porta la barra di riepilogo sotto i gruppi di pulsanti, come richiesto.
        for _barra in (self.frame_ctrl, self.frame_dimensioni):
            _barra.pack_forget()
        self.progress_bar.pack_forget()
        self.frame_ctrl.pack(fill="x")
        self.frame_dimensioni.pack(fill="x")
        self.progress_bar.pack(fill="x", padx=25, pady=4)

        self.ft = tk.Frame(root); self.ft.pack(fill="both", expand=True, padx=15, pady=5)
        self.frame_tree1 = tk.LabelFrame(self.ft, text=" Struttura Cartella 1 (Sorgente) ", padx=5, pady=5); self.frame_tree1.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.tree1 = ttk.Treeview(self.frame_tree1, columns=("size", "modified"), show="tree headings"); self.tree1.pack(side="left", fill="both", expand=True)
        sb1 = ttk.Scrollbar(self.frame_tree1, orient="vertical", command=self.tree1.yview); sb1.pack(side="right", fill="y"); self.tree1.configure(yscrollcommand=sb1.set)
        self.frame_tree2 = tk.LabelFrame(self.ft, text=" Struttura Cartella 2 (Destinazione) ", padx=5, pady=5); self.frame_tree2.pack(side="right", fill="both", expand=True, padx=(5, 0))
        self.tree2 = ttk.Treeview(self.frame_tree2, columns=("size", "modified"), show="tree headings"); self.tree2.pack(side="left", fill="both", expand=True)
        sb2 = ttk.Scrollbar(self.frame_tree2, orient="vertical", command=self.tree2.yview); sb2.pack(side="right", fill="y"); self.tree2.configure(yscrollcommand=sb2.set)

        self.menu_mouse = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 12))
        for name, t in [("tree1", self.tree1), ("tree2", self.tree2)]:
            t.column("#0", width=340, anchor="w"); t.column("size", width=110, anchor="e"); t.column("modified", width=160, anchor="center")
            t.bind("<Configure>", self._su_ridimensiona_albero_destro, add="+")
            t.bind("<Button-3>", self.mostra_menu_contestuale)
            # Se l'app non ha alcun widget focalizzato, la rotellina non viene recapitata.
            t.bind("<Enter>", lambda e, tree=t: tree.focus_set() if self.root.focus_get() is None else None, add="+")
            # Unico gestore della rotellina: "break" blocca il binding di classe di Tk,
            # che altrimenti scorre in aggiunta (anche sull'albero con il focus invece
            # che su quello sotto il puntatore) e fa tornare indietro la vista.
            t.bind("<MouseWheel>", self._scroll_rotellina_globale)
            # l'aggiornamento dell'albero al termine di una copia.
            # Supporto per configurazioni Tk/X11 che inviano Button-4/5.
            # Doppio clic sui file supportati li apre con l'app predefinita del sistema.
            t.bind("<Double-1>", lambda e, tree=t: self.apri_file_associato(tree, e), add="+")
            # Ricorda quale albero contiene la selezione corrente.
            t.bind("<Button-1>", self._imposta_albero_attivo, add="+")
            t.bind("<Button-1>", self._annulla_soppressione_sync_al_click, add="+")
            t.bind("<<TreeviewSelect>>", self._imposta_albero_attivo, add="+")
            t.bind("<<TreeviewSelect>>", self.sincronizza_selezione_cartella, add="+")
            # Associa Canc direttamente a entrambi gli alberi: in questo modo
            # la cancellazione funziona anche quando il focus è sul nodo/cartella.
            t.bind("<Delete>", lambda e, tree=t: self.elimina_selezione_albero(tree), add="+")
            t.bind("<KP_Delete>", lambda e, tree=t: self.elimina_selezione_albero(tree), add="+")
            t.bind("<Button-1>", lambda e, tree=t: self._memorizza_ancora_clic(tree, e), add="+")
            t.bind("<Shift-Up>", lambda e, tree=t: self._estendi_selezione_tastiera(tree, -1))
            t.bind("<Shift-Down>", lambda e, tree=t: self._estendi_selezione_tastiera(tree, 1))
            for tasto in ("<Up>", "<Down>"):
                t.bind(tasto, lambda e, tree=t: tree.after_idle(self._memorizza_ancora_focus, tree), add="+")
            t.heading("#0", text="Nome del File / Sottocartella", command=lambda: self.imposta_ordinamento("name"))
            t.heading("size", text="Dimensione", command=lambda: self.imposta_ordinamento("size"))
            t.heading("modified", text="Ultima Modifica", command=lambda: self.imposta_ordinamento("modified"))
        self.tree1.bind("<<TreeviewOpen>>", lambda e: self.sincronizza_evento_espansione(self.tree1, self.tree2, True))
        self.tree1.bind("<<TreeviewClose>>", lambda e: self.sincronizza_evento_espansione(self.tree1, self.tree2, False))
        self.tree2.bind("<<TreeviewOpen>>", lambda e: self.sincronizza_evento_espansione(self.tree2, self.tree1, True))
        self.tree2.bind("<<TreeviewClose>>", lambda e: self.sincronizza_evento_espansione(self.tree2, self.tree1, False))
        for _tree in (self.tree1, self.tree2):
            _tree.bind("<<TreeviewOpen>>", lambda e: self.root.after_idle(self._aggiorna_pulsante_espandi_comprimi), add="+")
            _tree.bind("<<TreeviewClose>>", lambda e: self.root.after_idle(self._aggiorna_pulsante_espandi_comprimi), add="+")
        # Su Windows l'evento può seguire il focus e non il widget puntato.
        self.root.bind_all("<MouseWheel>", self._scroll_rotellina_globale, add="+")
        self.root.bind_all("<Button-4>", lambda e: self._scroll_rotellina_globale_x11(e, -1), add="+")
        self.root.bind_all("<Button-5>", lambda e: self._scroll_rotellina_globale_x11(e, 1), add="+")
        self.menu_mouse.add_command(label="⌕ Apri percorso file", command=self.azione_apri_percorso); self.menu_mouse.add_separator()
        self.menu_mouse.add_command(label="⇢ Copia da 1 a 2", command=lambda: self.avvia_copia_file(1))
        self.menu_mouse.add_command(label="⇠ Copia da 2 a 1", command=lambda: self.avvia_copia_file(2))
        self.menu_mouse.add_separator()
        self.menu_mouse.add_command(label="✎ Rinomina", command=self.azione_rinomina); self.menu_mouse.add_command(label="× Elimina", command=self.azione_elimina)
        self.menu_mouse.add_separator()
        self.menu_mouse.add_command(label="🛡 Ripara permessi (amministratore)", command=self.azione_ripara_permessi)
        self.menu_mouse.add_separator()
        self.menu_mouse.add_command(label="↻ Aggiorna solo questa cartella", command=self.aggiorna_cartella_selezionata)
        # bind_all permette a Canc di funzionare anche se il focus è su un altro
        # widget; l'handler interviene soltanto quando è attivo un albero e c'è selezione.
        self.root.bind_all("<Delete>", self.elimina_con_tasto_canc, add="+")
        self.root.bind_all("<KP_Delete>", self.elimina_con_tasto_canc, add="+")
        # Scorciatoie globali: le azioni di copia rispettano l'albero attivo.
        self.root.bind_all("<F5>", self._scorciatoia_aggiorna, add="+")
        self.root.bind_all("<Control-f>", self._scorciatoia_cerca, add="+")
        self.root.bind_all("<Control-F>", self._scorciatoia_cerca, add="+")
        self.root.bind_all("<F2>", self._scorciatoia_rinomina, add="+")
        self.root.bind_all("<Control-Shift-C>", self._scorciatoia_copia_selezionata, add="+")
        self.root.bind_all("<Control-Shift-c>", self._scorciatoia_copia_selezionata, add="+")
        self.root.bind_all("<Control-Shift-M>", self._scorciatoia_copia_differenze, add="+")
        self.root.bind_all("<Control-Shift-m>", self._scorciatoia_copia_differenze, add="+")
        self.root.bind_all("<Control-Shift-P>", self._scorciatoia_anteprima, add="+")
        self.root.bind_all("<Control-Shift-p>", self._scorciatoia_anteprima, add="+")
        self.root.bind_all("<Control-Shift-R>", self._scorciatoia_aggiorna_cartella, add="+")
        self.root.bind_all("<Control-Shift-r>", self._scorciatoia_aggiorna_cartella, add="+")
        self.root.bind_all("<Control-Shift-E>", self._scorciatoia_espandi, add="+")
        self.root.bind_all("<Control-Shift-e>", self._scorciatoia_espandi, add="+")
        self.root.bind_all("<Control-Shift-F>", self._scorciatoia_filtri, add="+")
        self.root.bind_all("<Control-Shift-f>", self._scorciatoia_filtri, add="+")
        # Ogni nuova finestra secondaria (Filtri, Anteprima, Impostazioni...) viene adattata al tema.
        self.root.bind_all("<Map>", self._su_mappa_finestra, add="+")
        self._applica_layout_dashboard(); self.applica_tema(); self.carica_cronologia_da_disco(); self.carica_ultima_destinazione(); self.carica_filtri_da_disco()

    def _applica_layout_dashboard(self):
        """Riorganizza i widget esistenti in una dashboard a tre colonne."""
        # Barra superiore: percorsi e tema in una scheda compatta.
        self.frame_top.configure(padx=18, pady=8)
        self.f_barra.pack_configure(pady=(12, 8))
        self.frame_ctrl.pack_configure(padx=22, pady=(0, 2))
        self.frame_dimensioni.pack_configure(padx=22, pady=(0, 4))
        self.progress_bar.pack_configure(padx=22, pady=(0, 5))
        # Comandi in una fascia dedicata, con ricerca allineata a destra.
        for child in self.frame_ctrl.winfo_children():
            child.pack_configure(pady=3)
        for tree in (self.tree1, self.tree2):
            tree.configure(selectmode="extended")
        # Crea un pannello riepilogativo centrale fra i due alberi.
        self.frame_tree1.pack_forget(); self.frame_tree2.pack_forget()
        self.frame_tree1.configure(text="  SORGENTE  ", padx=8, pady=8, labelanchor="nw")
        self.frame_tree2.configure(text="  DESTINAZIONE  ", padx=8, pady=8, labelanchor="nw")
        self.frame_tree1.pack(side="left", fill="both", expand=True, padx=(0, 7), pady=4)
        self.panel_summary = tk.Frame(self.ft, width=210, padx=14, pady=16, bd=1, relief="solid")
        self.panel_summary.pack(side="left", fill="y", padx=5, pady=4)
        self.panel_summary.pack_propagate(False)
        tk.Label(self.panel_summary, text="⇄", font=("Segoe UI Symbol", 26, "bold"), fg="#38bdf8").pack(pady=(3, 0))
        tk.Label(self.panel_summary, text="Risultati:", font=("Segoe UI", 14, "bold")).pack(pady=(0, 14))
        tk.Label(self.panel_summary, text="Legenda confronto", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        self.summary_counts = {}
        self.legenda_simboli = []
        for key, symbol, label in (("identici", "●", "Elementi identici"), ("diversi", "▲", "Elementi diversi"), ("mancanti", "●", "Elementi mancanti")):
            row = tk.Frame(self.panel_summary); row.pack(fill="x", pady=5)
            simbolo_lbl = tk.Label(row, text=symbol, font=("Segoe UI", 13, "bold")); simbolo_lbl.pack(side="left", padx=(0, 7))
            self.legenda_simboli.append((key, simbolo_lbl))
            tk.Label(row, text=label, font=("Segoe UI", 11, "bold"), anchor="w", justify="left", wraplength=112).pack(side="left", fill="x", expand=True)
            count = tk.Label(row, text="—", font=("Segoe UI", 10, "bold"), width=5, anchor="e")
            count.pack(side="right")
            self.summary_counts[key] = count
            if key == "identici":
                count.configure(cursor="hand2")
                count.bind("<Button-1>", lambda _event: self.attiva_filtro_identici_da_conteggio())
                simbolo_lbl.configure(cursor="hand2")
                simbolo_lbl.bind("<Button-1>", lambda _event: self.attiva_filtro_identici_da_conteggio())
            elif key == "mancanti":
                count.configure(cursor="hand2", fg="#ff4d4f")
                count.bind("<Button-1>", lambda _event: self.attiva_filtro_mancanti_da_conteggio())
                simbolo_lbl.configure(cursor="hand2")
                simbolo_lbl.bind("<Button-1>", lambda _event: self.attiva_filtro_mancanti_da_conteggio())
        tk.Label(self.panel_summary, text="● Dimensione file diversa (giallo)", font=("Segoe UI", 9, "bold"), fg="#facc15", anchor="w", justify="left", wraplength=175).pack(fill="x", pady=(5, 0))
        ttk.Separator(self.panel_summary, orient="horizontal").pack(fill="x", pady=14)
        self.summary_status = tk.Label(self.panel_summary, text="In attesa del confronto", font=("Segoe UI", 14, "bold"), anchor="w", justify="left", wraplength=190)
        self.summary_status.pack(fill="x", pady=(0, 8))
        # Nel riepilogo dei temi chiaro/scuro non mostriamo le dimensioni delle cartelle.
        tk.Label(self.panel_summary, text="Suggerimento\nSeleziona un elemento per usare copia, rinomina o elimina.", font=("Segoe UI", 9), justify="left", wraplength=175).pack(side="top", anchor="w", pady=(8, 0))

        # Fascia orizzontale usata esclusivamente dal tema Old style.
        self.panel_old_summary = tk.Frame(self.root, padx=10, pady=6, bd=1, relief="solid")
        tk.Label(self.panel_old_summary, text="Risultati:", font=("Segoe UI", 11, "bold")).pack(side="left", padx=(2, 14))
        self.old_summary_counts = {}
        categorie = (("identici", "Uguali:"), ("mancanti", "Mancanti:"), ("dimensione", "Dimensione diversa:"), ("data_recente", "Data più recente:"), ("data_vecchia", "Data più vecchia:"))
        for key, label in categorie:
            group = tk.Frame(self.panel_old_summary)
            group.pack(side="left", padx=18)
            colore = {"identici":"#f2f2f2", "dimensione":"#facc15", "data_vecchia":"#d97706", "data_recente":"#16a34a", "mancanti":"#ff4d4f"}[key]
            tk.Label(group, text=label, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 4))
            count = tk.Label(group, text="—", font=("Segoe UI", 11, "bold"), width=6, anchor="w", fg=colore)
            count.pack(side="left")
            self.old_summary_counts[key] = count
            if key == "identici":
                count.configure(cursor="hand2")
                count.bind("<Button-1>", lambda _event: self.attiva_filtro_identici_da_conteggio())
            elif key == "mancanti":
                count.configure(cursor="hand2")
                count.bind("<Button-1>", lambda _event: self.attiva_filtro_mancanti_da_conteggio())
            elif key in ("data_vecchia", "data_recente"):
                count.configure(cursor="hand2")
                count.bind("<Button-1>", lambda _event, k=key: self.attiva_filtro_data_da_conteggio(k))
            elif key == "dimensione":
                count.configure(cursor="hand2")
                count.bind("<Button-1>", lambda _event: self.attiva_filtro_dimensione_da_conteggio())
        self.old_summary_status = tk.Label(self.panel_old_summary, text="", font=("Segoe UI", 12, "bold"), anchor="w")
        # Barra legenda separata, come nel mockup: colori e significato sempre visibili.
        self.panel_summary_legend = tk.Frame(self.root, padx=10, pady=6, bd=1, relief="solid")
        legenda = (("#f2f2f2", "Bianco = file uguali"),
                   ("#facc15", "Giallo = dimensione diversa"),
                   ("#16a34a", "Verde = data più recente"),
                   ("#d97706", "Arancione = data più vecchia"),
                   ("#ff4d4f", "Rosso = file mancanti"))
        self.summary_legend_labels = []
        for colore, testo_legenda in legenda:
            gruppo = tk.Frame(self.panel_summary_legend)
            gruppo.pack(side="left", fill="x", expand=True, padx=8)
            punto = tk.Label(gruppo, text="●", font=("Segoe UI", 11, "bold"), fg=colore)
            punto.pack(side="left", padx=(0, 5))
            testo_lbl = tk.Label(gruppo, text=testo_legenda, font=("Segoe UI", 9))
            testo_lbl.pack(side="left")
            self.summary_legend_labels.append((gruppo, punto, testo_lbl))
        # Nel riepilogo non mostriamo lo spazio occupato da sorgente e destinazione.
        self.frame_tree2.pack(side="left", fill="both", expand=True, padx=(7, 0), pady=4)
        # L'altezza della finestra viene sfruttata dagli alberi; riduce il rumore visivo.
        self.ft.pack_configure(padx=14, pady=(2, 8))

    def _scorciatoia_aggiorna(self, event=None):
        self.forza_refresh()
        return "break"

    def _scorciatoia_cerca(self, event=None):
        self.entry_search.focus_set()
        self.entry_search.selection_range(0, "end")
        return "break"

    def _scorciatoia_rinomina(self, event=None):
        if self.albero_attivo in (self.tree1, self.tree2) and self._nodi_selezionati():
            self.azione_rinomina()
        return "break"

    def _scorciatoia_copia_selezionata(self, event=None):
        if self.albero_attivo not in (self.tree1, self.tree2) or not self._nodi_selezionati():
            messagebox.showinfo(self._t("Copia elemento", "Copy item"),
                                self._t("Seleziona prima un file o una cartella in uno dei due alberi.",
                                        "Select a file or folder in one of the trees first."))
            return "break"
        self.avvia_copia_file(1 if self.albero_attivo is self.tree1 else 2)
        return "break"

    def _scorciatoia_copia_differenze(self, event=None):
        self.copia_tutte_modifiche_sinistra_destra()
        return "break"

    def _scorciatoia_anteprima(self, event=None):
        self.anteprima_differenze()
        return "break"

    def _scorciatoia_aggiorna_cartella(self, event=None):
        self.aggiorna_cartella_selezionata()
        return "break"

    def _scorciatoia_espandi(self, event=None):
        self.espandi_tutto()
        return "break"

    def _scorciatoia_filtri(self, event=None):
        self.apri_finestra_filtri()
        return "break"

    def _annulla_soppressione_sync_al_click(self, event):
        # Un nuovo clic esplicito dell'utente deve sempre poter selezionare un'altra riga.
        if getattr(self, "_sync_suppress_tree", None) is event.widget:
            self._sync_suppress_tree = None

    def _imposta_albero_attivo(self, event):
        tree = event.widget
        if tree in (self.tree1, self.tree2):
            self.albero_attivo = tree
            selezione = tree.selection()
            if selezione:
                self.nodo_attivo = selezione[0]

    def imposta_ordinamento(self, col):
        if self.sort_by == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_by = col
            # Il nome parte da A-Z; dimensione e data mantengono il default decrescente.
            self.sort_reverse = (col != "name")
        self.rigenera_alberi_da_cache()

    def _nome_volume(self, percorso):
        """Restituisce l'etichetta del volume Windows, anche per percorsi inseriti a mano."""
        percorso = str(percorso or "").strip().strip('"')
        if not percorso:
            return ""
        try:
            import ctypes
            import ntpath
            # Usa la radice Windows indipendentemente dal sistema da cui viene analizzato il codice.
            drive, _ = ntpath.splitdrive(percorso)
            if not drive or not drive.endswith(":"):
                return ""
            radice = drive + "\\\\"
            etichetta = ctypes.create_unicode_buffer(261)
            fs_name = ctypes.create_unicode_buffer(261)
            serial = ctypes.c_ulong()
            max_component = ctypes.c_ulong()
            flags = ctypes.c_ulong()
            kernel32 = ctypes.windll.kernel32
            ok = kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(radice), etichetta, len(etichetta),
                ctypes.byref(serial), ctypes.byref(max_component),
                ctypes.byref(flags), fs_name, len(fs_name))
            return etichetta.value.strip() if ok else ""
        except Exception:
            return ""

    def _unc_per_unita_mappata(self, percorso):
        """Restituisce l'UNC associato a un'unità di rete mappata, se disponibile."""
        percorso = str(percorso or "").strip().strip('"')
        try:
            import ctypes
            import ntpath
            drive, _ = ntpath.splitdrive(percorso)
            if not drive or not drive.endswith(":"):
                return ""
            buffer = ctypes.create_unicode_buffer(2048)
            dimensione = ctypes.c_ulong(len(buffer))
            risultato = ctypes.windll.mpr.WNetGetConnectionW(
                ctypes.c_wchar_p(drive.upper()), buffer, ctypes.byref(dimensione))
            return buffer.value.strip() if risultato == 0 else ""
        except Exception:
            return ""

    def _testo_combobox_percorso(self, percorso):
        """Visualizza UNC per le unità mappate mantenendo invariato il percorso reale."""
        percorso = str(percorso or "").strip()
        if not percorso:
            return ""
        import ntpath
        drive, resto = ntpath.splitdrive(percorso)
        unc = self._unc_per_unita_mappata(percorso)
        if drive and unc:
            # Esempio: Z:\Video -> Z: [\\NAS\Archivio]\Video
            return f"{drive} [{unc}]{resto}"
        nome = self._nome_volume(percorso)
        if drive and nome:
            return f"{drive} [{nome}]{resto}"
        return percorso

    def safe_combobox_get(self, combo):
        val = combo.get()
        if not val and combo.cget('values'):
            try: val = combo.cget('values')[0]
            except Exception: pass
        val = val.strip() if val else ""
        # Elimina solo l'etichetta visuale aggiunta dopo la lettera dell'unità.
        import re
        return re.sub(r"^([A-Za-z]:) \[[^]]+\]", r"\1", val)

    def sincronizza_selezione_cartella(self, event=None):
        """Sincronizza la cartella selezionata senza bloccare l'evento Tkinter."""
        sorgente = event.widget if event is not None else self.albero_attivo
        if sorgente not in (self.tree1, self.tree2) or getattr(self, "lock_sync", False):
            return
        # Ignora l'evento di selezione generato dalla sincronizzazione automatica:
        # altrimenti i due alberi possono richiamarsi a vicenda e impedire nuovi clic.
        if getattr(self, "_sync_suppress_tree", None) is sorgente:
            self._sync_suppress_tree = None
            return
        # Tkinter può generare più eventi di selezione ravvicinati: accorpiamoli
        # e svolgiamo la sincronizzazione a ciclo UI concluso.
        if getattr(self, "_sync_cartella_pending", False):
            self._sync_cartella_tree = sorgente
            return
        self._sync_cartella_pending = True
        self._sync_cartella_tree = sorgente

        def esegui_sync():
            self._sync_cartella_pending = False
            tree_sorgente = getattr(self, "_sync_cartella_tree", sorgente)
            try:
                if getattr(self, "lock_sync", False):
                    return
                selezione = tree_sorgente.selection()
                if not selezione:
                    return
                nodo = selezione[0]
                # Sincronizza solo le cartelle, non i file.
                if not tree_sorgente.get_children(nodo):
                    return
                destinazione = self.tree2 if tree_sorgente is self.tree1 else self.tree1
                relativo = self.ricava_chiave_relativa(tree_sorgente, nodo)
                if relativo is None:
                    return

                parti = relativo.split(os.sep) if relativo else []
                parent = ""
                trovato = None
                # Evita scansioni ripetute: ogni livello viene cercato solo tra
                # i figli del genitore corrispondente.
                for indice, parte in enumerate(parti):
                    trovato = next(
                        (c for c in destinazione.get_children(parent)
                         if destinazione.item(c, "text") == parte),
                        None
                    )
                    if trovato is None:
                        return
                    # Apri ogni livello del percorso nel pannello opposto,
                    # incluso il genitore immediato della cartella selezionata.
                    if parent:
                        destinazione.item(parent, open=True)
                    parent = trovato

                if trovato:
                    # Non aprire automaticamente il nodo selezionato: così un clic
                    # su una cartella già aperta non annulla la sua chiusura.
                    # L'apertura/chiusura speculare è gestita da <<TreeviewOpen/Close>>.
                    # Evita di ripetere la sincronizzazione quando l'albero
                    # destinatario emette <<TreeviewSelect>> per questa selezione.
                    selezione_dest = destinazione.selection()
                    # Se la cartella è già l'unica selezionata nell'albero opposto non
                    # rifare selection_set: genererebbe un nuovo <<TreeviewSelect>> che
                    # riavvia la sincronizzazione nel verso inverso (ping-pong infinito),
                    # con yview_moveto/see a ogni giro che annullano lo scroll della rotellina.
                    if tuple(selezione_dest) == (trovato,):
                        return
                    if not selezione_dest or trovato not in selezione_dest:
                        self._sync_suppress_tree = destinazione
                    self.lock_sync = True
                    try:
                        destinazione.selection_set(trovato)
                        destinazione.focus(trovato)
                        destinazione.see(trovato)
                        # Allinea verticalmente la cartella corrispondente:
                        # dopo l'espansione, la riga selezionata non deve restare
                        # in fondo al pannello opposto.
                        def allinea_cartella():
                            try:
                                if not destinazione.exists(trovato):
                                    return
                                righe_visibili = []
                                def raccogli_visibili(parent=""):
                                    for elemento in destinazione.get_children(parent):
                                        righe_visibili.append(elemento)
                                        if destinazione.item(elemento, "open"):
                                            raccogli_visibili(elemento)
                                raccogli_visibili()
                                if trovato not in righe_visibili or not righe_visibili:
                                    return
                                bbox = destinazione.bbox(trovato)
                                altezza_riga = max(1, bbox[3] if bbox else 20)
                                righe_view = max(1, destinazione.winfo_height() // altezza_riga)
                                indice = righe_visibili.index(trovato)
                                frazione = max(0.0, min(1.0,
                                    (indice - max(0, righe_view // 3)) / max(1, len(righe_visibili))))
                                destinazione.yview_moveto(frazione)
                            except (tk.TclError, ValueError):
                                pass
                        destinazione.after_idle(allinea_cartella)
                    finally:
                        self.lock_sync = False
            except (tk.TclError, ValueError, OSError):
                self.lock_sync = False

        try:
            sorgente.after_idle(esegui_sync)
        except tk.TclError:
            self._sync_cartella_pending = False

    def sincronizza_evento_espansione(self, sorgente, destinazione, espandi=True):
        """Sincronizza l'apertura e porta la cartella corrispondente in evidenza."""
        if self.lock_sync:
            return
        self.lock_sync = True
        try:
            sel = sorgente.focus()
            if not sel:
                selezione = sorgente.selection()
                sel = selezione[0] if selezione else ""
            if not sel:
                return
            rel = self.ricava_chiave_relativa(sorgente, sel)
            if not rel:
                return

            def trova_percorso(tree, relativo):
                parti = relativo.split(os.sep) if relativo else []
                parent = ""
                trovato = None
                for parte in parti:
                    def nome_nodo(item):
                        # Le cartelle mostrano l'icona gialla prima del nome:
                        # per la sincronizzazione confrontiamo solo il nome reale.
                        testo = tree.item(item, "text") or ""
                        if testo.startswith("📁  "):
                            testo = testo[4:]
                        elif testo.startswith("📁 "):
                            testo = testo[2:]
                        return testo
                    trovato = next((c for c in tree.get_children(parent)
                                    if nome_nodo(c) == parte), None)
                    if trovato is None:
                        return None
                    if parent:
                        tree.item(parent, open=True)
                    parent = trovato
                return trovato

            spec = trova_percorso(destinazione, rel)
            if spec:
                destinazione.item(spec, open=espandi)
                # Evidenzia la stessa cartella anche nell'albero opposto e
                # porta la riga al centro dell'area visibile.
                # Evita selection_set se già selezionata (vedi sincronizza_selezione_cartella).
                if tuple(destinazione.selection()) != (spec,):
                    destinazione.selection_set(spec)
                destinazione.focus(spec)
                destinazione.see(spec)

                def centra_riga():
                    try:
                        if not destinazione.exists(spec):
                            return
                        righe_visibili = []
                        def raccogli(parent=""):
                            for nodo in destinazione.get_children(parent):
                                righe_visibili.append(nodo)
                                if destinazione.item(nodo, "open"):
                                    raccogli(nodo)
                        raccogli()
                        if spec not in righe_visibili or not righe_visibili:
                            return
                        altezza_riga = max(1, destinazione.bbox(spec)[3] if destinazione.bbox(spec) else 20)
                        altezza_view = max(altezza_riga, destinazione.winfo_height())
                        righe_view = max(1, altezza_view // altezza_riga)
                        indice = righe_visibili.index(spec)
                        totale = len(righe_visibili)
                        frazione = max(0.0, min(1.0, (indice - righe_view // 2) / max(1, totale)))
                        destinazione.yview_moveto(frazione)
                    except (tk.TclError, ValueError):
                        pass
                destinazione.after_idle(centra_riga)
        except (tk.TclError, ValueError, OSError):
            pass
        finally:
            self.lock_sync = False

    def salva_cronologia_su_disco(self):
        """Salva cronologia e filtri nello stesso file di configurazione."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write("--- C1 ---\n" + "".join(f"{p}\n" for p in self.cronologia_c1))
                f.write("--- C2 ---\n" + "".join(f"{p}\n" for p in self.cronologia_c2))
                f.write("--- FILTRI ---\n" + "".join(f"{r}\n" for r in self.filtri_esclusione))
                f.write("--- TEMA ---\n" + self.current_theme + "\n")
                f.write("--- ULTIMA DESTINAZIONE ---\n" + getattr(self, "ultima_destinazione", "") + "\n")
        except OSError: pass

    def carica_cronologia_da_disco(self):
        if not os.path.exists(CONFIG_FILE): return
        try:
            sezione, c1_l, c2_l, filtri, tema_salvato, destinazione_salvata = None, [], [], [], None, ""
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for riga in f:
                    r = riga.rstrip("\r\n")
                    if r == "--- C1 ---": sezione = 1
                    elif r == "--- C2 ---": sezione = 2
                    elif r == "--- FILTRI ---": sezione = 3
                    elif r == "--- TEMA ---": sezione = 4
                    elif r == "--- ULTIMA DESTINAZIONE ---": sezione = 5
                    elif r and sezione == 4 and (r in TEMES or r in ("classic66", "classic_light")): tema_salvato = r
                    elif r and sezione == 5: destinazione_salvata = r
                    elif r and sezione == 1: c1_l.append(r)
                    elif r and sezione == 2: c2_l.append(r)
                    elif r.strip() and sezione == 3 and not r.strip().startswith("#"): filtri.append(r.strip())
            self.cronologia_c1, self.cronologia_c2 = c1_l[:10], c2_l[:10]
            self.ultima_destinazione = destinazione_salvata.strip()
            if filtri:
                self.filtri_esclusione = filtri
            tema_salvato = {"classic66": "dark", "classic_light": "light"}.get(tema_salvato, tema_salvato)  # Old style rimosso
            if tema_salvato in TEMES:
                self.current_theme = tema_salvato
            if self.cronologia_c1: self.combo_c1['values'] = [self._testo_combobox_percorso(p) for p in self.cronologia_c1]; self.combo_c1.set(self._testo_combobox_percorso(self.cronologia_c1[0]))
            if self.cronologia_c2: self.combo_c2['values'] = [self._testo_combobox_percorso(p) for p in self.cronologia_c2]; self.combo_c2.set(self._testo_combobox_percorso(self.cronologia_c2[0]))
            if tema_salvato in TEMES:
                self.applica_tema()
        except (OSError, UnicodeError): pass

    def elimina_cronologia(self):
        if messagebox.askyesno("Cronologia", "Vuoi cancellare tutte le ultime cartelle utilizzate?"):
            self.cronologia_c1.clear(); self.cronologia_c2.clear(); self.combo_c1.set(""); self.combo_c2.set(""); self.combo_c1['values'] = []; self.combo_c2['values'] = []
            # Conserva tema e filtri: cancella solo i percorsi recenti.
            self.salva_cronologia_su_disco()
            messagebox.showinfo("Successo", "Cronologia cartelle eliminata!")

    def mostra_menu_contestuale(self, event):
        t = event.widget
        i = t.identify_row(event.y)
        if not i:
            return "break"
        # Seleziona la riga cliccata e ricorda quale albero ha aperto il menu.
        if i not in t.selection():
            t.selection_set(i)
        t.focus(i)
        self.albero_attivo = t
        self.nodo_attivo = i
        multipla = len(t.selection()) > 1
        self.menu_mouse.entryconfig(5, state="disabled" if multipla else "normal")  # Rinomina
        # Usa gli indici delle voci, non le etichette: così le icone/testi
        # non possono causare TclError quando vengono abilitate/disabilitate.
        if t == self.tree1:
            self.menu_mouse.entryconfig(2, state="normal")
            self.menu_mouse.entryconfig(3, state="disabled")
        else:
            self.menu_mouse.entryconfig(2, state="disabled")
            self.menu_mouse.entryconfig(3, state="normal")
        try:
            self.menu_mouse.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_mouse.grab_release()
        return "break"
    def elimina_selezione_albero(self, tree):
        """Elimina il file o la cartella selezionata nell'albero indicato."""
        if tree not in (self.tree1, self.tree2):
            return "break"
        selezione = tree.selection()
        if not selezione:
            # Se il clic è sul nodo ma Tk non ha aggiornato selection() ancora,
            # usa l'elemento sotto il puntatore/focus quando disponibile.
            try:
                focus_item = tree.focus()
                if focus_item and tree.exists(focus_item):
                    selezione = (focus_item,)
            except tk.TclError:
                pass
        if not selezione:
            return "break"
        self.albero_attivo = tree
        self.nodo_attivo = selezione[0]
        self.azione_elimina()  # Richiede sempre conferma, anche per le cartelle.
        return "break"

    def elimina_con_tasto_canc(self, event=None):
        """Gestisce Canc a livello finestra e inoltra all'albero attivo."""
        widget = getattr(event, "widget", None) if event is not None else None
        focus = self.root.focus_get()
        # Il bind sull'albero gestisce già Canc; evita un secondo dialogo di conferma.
        if widget in (self.tree1, self.tree2):
            return
        # Non cancellare file/cartelle mentre si scrive in un campo di testo.
        for candidato in (widget, focus):
            if isinstance(candidato, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox, tk.Listbox)):
                return
        tree = focus if focus in (self.tree1, self.tree2) else getattr(self, "albero_attivo", None)
        return self.elimina_selezione_albero(tree)

    def _memorizza_ancora_clic(self, tree, event):
        """Il clic senza Maiusc fissa il punto di partenza della selezione da tastiera."""
        if event.state & 0x0001:  # Maiusc premuto: l'ancora resta quella precedente
            return
        riga = tree.identify_row(event.y)
        if riga:
            self._ancore_selezione = getattr(self, "_ancore_selezione", {})
            self._ancore_selezione[tree] = riga

    def _memorizza_ancora_focus(self, tree):
        """Dopo freccia su/giù senza Maiusc, l'ancora segue la riga attiva."""
        try:
            focus = tree.focus()
        except tk.TclError:
            return
        if focus:
            self._ancore_selezione = getattr(self, "_ancore_selezione", {})
            self._ancore_selezione[tree] = focus

    @staticmethod
    def _righe_visibili(tree):
        """Righe visibili dall'alto in basso (figli solo delle cartelle aperte)."""
        righe = []
        def _visita(parent):
            for item in tree.get_children(parent):
                righe.append(item)
                if tree.item(item, "open"):
                    _visita(item)
        _visita("")
        return righe

    def _estendi_selezione_tastiera(self, tree, direzione):
        """Maiusc+freccia: seleziona tutte le righe tra l'ancora e la nuova riga attiva."""
        righe = self._righe_visibili(tree)
        if not righe:
            return "break"
        indice = {item: i for i, item in enumerate(righe)}
        focus = tree.focus()
        if focus not in indice:
            selezione = [i for i in tree.selection() if i in indice]
            focus = selezione[-1] if selezione else righe[0]
        ancore = getattr(self, "_ancore_selezione", {})
        ancora = ancore.get(tree)
        if ancora not in indice:
            ancora = focus
            self._ancore_selezione = ancore
            ancore[tree] = ancora
        nuova = righe[max(0, min(len(righe) - 1, indice[focus] + direzione))]
        da, a = sorted((indice[ancora], indice[nuova]))
        tree.selection_set(righe[da:a + 1])
        tree.focus(nuova)
        tree.see(nuova)
        self.albero_attivo = tree
        self.nodo_attivo = nuova
        return "break"

    def _nodi_selezionati(self):
        """Nodi selezionati nell'albero attivo, senza i discendenti di nodi già selezionati."""
        tree = getattr(self, "albero_attivo", None)
        if tree is None:
            return []
        try:
            selezione = list(tree.selection())
        except tk.TclError:
            selezione = []
        if not selezione and getattr(self, "nodo_attivo", None):
            selezione = [self.nodo_attivo]
        insieme = set(selezione)
        risultato = []
        for item in selezione:
            padre = tree.parent(item)
            while padre and padre not in insieme:
                padre = tree.parent(padre)
            if not padre:
                risultato.append(item)
        return risultato

    def _percorsi_selezionati(self):
        """Percorsi reali esistenti degli elementi selezionati (esclude 'Non presente')."""
        percorsi = []
        for item in self._nodi_selezionati():
            p = self.ricava_percorso_reale(self.albero_attivo, item)
            if p and os.path.lexists(p) and p not in percorsi:
                percorsi.append(p)
        return percorsi

    @staticmethod
    def _elenco_breve(voci, massimo=10):
        testo = "\n".join(f"• {v}" for v in voci[:massimo])
        if len(voci) > massimo:
            testo += f"\n… (+{len(voci) - massimo})"
        return testo

    def ricava_chiave_relativa(self, tree, item_id):
        parti = []
        while item_id: parti.insert(0, tree.item(item_id, "text")); item_id = tree.parent(item_id)
        return os.path.join(*parti) if parti else ""

    def ricava_percorso_reale(self, tree, item_id):
        base = self.safe_combobox_get(self.combo_c1) if tree == self.tree1 else self.safe_combobox_get(self.combo_c2)
        rel = self.ricava_chiave_relativa(tree, item_id)
        if not rel:
            return ""
        # Alcune viste includono nel percorso relativo anche il nodo radice.
        # Rimuove quel primo componente quando coincide con il nome della radice,
        # altrimenti il percorso può diventare, ad esempio, .../Pictures/Pictures.
        base_norm = os.path.normpath(base) if base else ""
        rel_norm = os.path.normpath(rel)
        nome_radice = os.path.basename(base_norm.rstrip(os.sep)) if base_norm else ""
        if nome_radice:
            parti_rel = rel_norm.split(os.sep)
            if parti_rel and os.path.normcase(parti_rel[0]) == os.path.normcase(nome_radice):
                parti_rel = parti_rel[1:]
                rel_norm = os.path.join(*parti_rel) if parti_rel else ""
        if not rel_norm or rel_norm == ".":
            return base_norm
        return os.path.normpath(os.path.join(base_norm, rel_norm)) if base_norm else rel_norm

    def apri_file_associato(self, tree, event=None):
        """Apre al doppio clic immagini JPG/JPEG/TIF/TIFF/WEBP e documenti TXT, PDF e DOCX."""
        try:
            if event is not None:
                item = tree.identify_row(event.y)
                if not item:
                    return
                tree.selection_set(item)
                self.albero_attivo = tree
                self.nodo_attivo = item
            else:
                selezione = tree.selection()
                if not selezione:
                    return
                item = selezione[0]
            percorso = self.ricava_percorso_reale(tree, item)
            if not percorso or not os.path.isfile(percorso):
                return
            if os.path.splitext(percorso)[1].casefold() not in (".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".png", ".bmp", ".txt", ".pdf", ".docx"):
                return
            percorso = os.path.abspath(os.path.normpath(percorso))
            if platform.system() == "Windows":
                os.startfile(percorso)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", percorso])
            else:
                subprocess.Popen(["xdg-open", percorso])
        except Exception as e:
            messagebox.showerror("Errore apertura file", f"Impossibile aprire il file selezionato:\n{e}")

    def azione_apri_percorso(self):
        if not hasattr(self, 'albero_attivo') or not self.nodo_attivo:
            return
        p = self.ricava_percorso_reale(self.albero_attivo, self.nodo_attivo)
        if not p:
            messagebox.showwarning("Attenzione", "Seleziona un file o una cartella.")
            return
        p = os.path.abspath(os.path.normpath(p))
        if not os.path.exists(p):
            messagebox.showwarning("Attenzione", f"Il percorso non esiste:\n{p}")
            return
        try:
            if platform.system() == "Windows":
                if os.path.isfile(p):
                    # Passa a Explorer il percorso tra virgolette: funziona anche con spazi.
                    subprocess.Popen(f'explorer.exe /select,"{p}"')
                else:
                    # Avvia direttamente la cartella selezionata, senza passare da una shell.
                    os.startfile(p)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-R", p] if os.path.isfile(p) else ["open", p])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(p) if os.path.isfile(p) else p])
        except Exception as e:
            messagebox.showerror("Errore apertura percorso", f"Impossibile aprire:\n{p}\n\n{e}")

    # ------------------------------------------------------------------
    # Copia: ogni file è gestito singolarmente, un errore non blocca
    # più l'intera operazione; contenuto e data/attributi sono separati.
    # ------------------------------------------------------------------
    def _t(self, it, en):
        """Restituisce il testo nella lingua corrente dell'interfaccia."""
        return en if getattr(self, "lingua", "it") == "en" else it

    @staticmethod
    def _percorso_log_errori():
        return os.path.join(APP_DIR, LOG_ERRORI_FILE)

    def _registra_errore_copia(self, percorso, errore, ignorato=False, livello=None):
        """Registra errori e avvisi di copia in un log accanto al programma."""
        try:
            etichetta = livello or ("IGNORATO" if ignorato else "ERRORE")
            descrizione = errore if isinstance(errore, str) else f"{type(errore).__name__}: {errore}"
            with open(self._percorso_log_errori(), "a", encoding="utf-8") as log:
                log.write(f"[{datetime.datetime.now().isoformat(sep=' ', timespec='seconds')}] ")
                log.write(f"{etichetta} | {percorso} | {descrizione}\n")
        except Exception:
            # Un problema di scrittura del log non deve interrompere la copia.
            pass

    def apri_log_errori(self, parent=None):
        percorso = self._percorso_log_errori()
        if not os.path.exists(percorso):
            messagebox.showinfo(self._t("Log errori", "Error log"),
                                self._t("Il log non contiene ancora nessuna voce.", "The log is still empty."),
                                parent=parent)
            return
        try:
            if platform.system() == "Windows":
                os.startfile(percorso)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", percorso])
            else:
                subprocess.Popen(["xdg-open", percorso])
        except Exception as e:
            messagebox.showerror(self._t("Errore apertura log", "Cannot open log"), f"{percorso}\n\n{e}", parent=parent)

    @staticmethod
    def _ignora_file_cache(percorso_cartella, nomi):
        """Esclude solo le voci .@__thumb; Thumbs.db viene copiato normalmente."""
        return [nome for nome in nomi if ".@__thumb" in nome.casefold()]

    @staticmethod
    def _is_file_cache(percorso):
        return os.path.basename(percorso).casefold() == "thumbs.db" or ".@__thumb" in percorso.casefold()

    @staticmethod
    def _stessa_dimensione(src, dst):
        """True se dst è un file normale con la stessa dimensione in byte di src.

        Regola: un file di destinazione con la stessa dimensione NON viene
        sovrascritto, anche se la data di modifica è diversa.
        """
        try:
            if os.path.islink(dst) or not os.path.isfile(dst):
                return False
            return os.stat(src).st_size == os.stat(dst).st_size
        except OSError:
            return False

    @staticmethod
    def _stessa_dimensione_e_data(src, dst):
        """True se dimensione e data di modifica coincidono."""
        try:
            if os.path.islink(dst) or not os.path.isfile(dst):
                return False
            ss, ds = os.stat(src), os.stat(dst)
            return ss.st_size == ds.st_size and ss.st_mtime == ds.st_mtime
        except OSError:
            return False

    def _chiedi_sovrascrittura_stessa_dimensione(self, src, dst, nome):
        """Chiede una sola volta per operazione cosa fare con tutti i file
        di pari dimensione ma data diversa. Sì = sovrascrivi tutti; No = salta tutti."""
        decisione = getattr(self, "_decisione_stessa_dimensione_copia", None)
        if decisione is not None:
            return decisione

        evento = threading.Event()
        risposta = {"sovrascrivi": False}

        def domanda():
            try:
                try:
                    data_src = format_date(os.path.getmtime(src))
                    data_dst = format_date(os.path.getmtime(dst))
                except OSError:
                    data_src, data_dst = "?", "?"
                testo = self._t(
                    f"Il file ha la stessa dimensione ma una data di modifica diversa.\\n\\n"
                    f"File: {nome}\\n\\nSorgente: {data_src}\\nDestinazione: {data_dst}\\n\\n"
                    "Vuoi sovrascrivere il file di destinazione?\\n\\nSì = Sovrascrivi   No = Salta",
                    f"The file has the same size but a different modification date.\\n\\n"
                    f"File: {nome}\\n\\nSource: {data_src}\\nDestination: {data_dst}\\n\\n"
                    "Overwrite the destination file?\\n\\nYes = Overwrite   No = Skip")
                risposta["sovrascrivi"] = messagebox.askyesno(
                    self._t("File con stessa dimensione", "Same-size file"), testo, parent=self.root)
            except Exception:
                risposta["sovrascrivi"] = False
            finally:
                evento.set()

        self.root.after(0, domanda)
        evento.wait()
        # Memorizza la scelta per tutta l'operazione: anche False (No) è una
        # decisione valida e non deve provocare una nuova domanda per ogni file.
        self._decisione_stessa_dimensione_copia = risposta["sovrascrivi"]
        return risposta["sovrascrivi"]

    @staticmethod
    def _errore_temporaneo(errore):
        """Errori per cui ha senso riprovare (file bloccato, antivirus, sola lettura)."""
        return isinstance(errore, PermissionError) or getattr(errore, "winerror", None) in (5, 32, 33)

    def _motivo_errore(self, errore):
        """Traduce un'eccezione in un motivo leggibile per il riepilogo."""
        winerror = getattr(errore, "winerror", None)
        if isinstance(errore, ErroreVerificaHash):
            return self._t("Verifica SHA-256 non riuscita", "SHA-256 check failed")
        if winerror in (32, 33):
            return self._t("File in uso", "File in use")
        if winerror == 5 or isinstance(errore, PermissionError):
            return self._t("Accesso negato", "Access denied")
        if isinstance(errore, FileNotFoundError):
            return self._t("File non trovato", "File not found")
        if winerror in (39, 112) or getattr(errore, "errno", None) == 28:
            return self._t("Spazio insufficiente", "Not enough space")
        return f"{type(errore).__name__}: {errore}"

    def _chiedi_verifica_hash_copia(self):
        """Chiede se verificare anche il contenuto con SHA-256 (operazione più lenta)."""
        scelta = messagebox.askyesno(
            self._t("Verifica della copia", "Copy verification"),
            self._t(
                "Dopo la copia verrà sempre verificata la dimensione del file.\n\n"
                "Vuoi eseguire anche il controllo SHA-256 del contenuto? È più affidabile, ma può richiedere molto tempo su file grandi o dischi lenti.",
                "File size will always be checked after copying.\n\n"
                "Also verify file contents with SHA-256? This is more reliable but may take longer for large files or slow drives."
            ),
            default="no"
        )
        self._verifica_hash_copia = bool(scelta)

    def avvia_copia_file(self, src_tree):
        if self.is_scanning: return
        c1, c2 = self.safe_combobox_get(self.combo_c1), self.safe_combobox_get(self.combo_c2)
        if not self._verifica_cartelle_accessibili(c1, c2):
            return
        base_src, base_dst = (c1, c2) if src_tree == 1 else (c2, c1)
        coppie = []
        for item in self._nodi_selezionati():
            rel = self.ricava_chiave_relativa(self.albero_attivo, item)
            if rel and os.path.exists(os.path.join(base_src, rel)):
                coppie.append((rel, os.path.join(base_src, rel), os.path.join(base_dst, rel)))
        if not coppie: return
        # Ogni nuova operazione di copia deve chiedere nuovamente la decisione
        # per i file di pari dimensione ma data diversa.
        self._decisione_stessa_dimensione_copia = None
        if len(coppie) > 1:
            self._avvia_copia_multipla(coppie, c1, c2, base_dst)
            return
        rel, src, dst = coppie[0]
        try:
            if os.path.samefile(src, dst):
                messagebox.showwarning(self._t("Copia non necessaria", "Copy not needed"),
                                       self._t("Sorgente e destinazione indicano lo stesso elemento.",
                                               "Source and destination point to the same item."))
                return
        except OSError:
            pass
        # Stessa dimensione e stessa data: salta subito. Se la dimensione è
        # uguale ma la data differisce, la domanda viene fatta dal worker di copia:
        # chiedere qui bloccherebbe il thread principale mentre attende root.after.
        stessa_dimensione_data_diversa = (
            os.path.isfile(src) and self._stessa_dimensione(src, dst)
            and not self._stessa_dimensione_e_data(src, dst)
        )
        if os.path.isfile(src) and self._stessa_dimensione_e_data(src, dst):
            messagebox.showinfo(self._t("Nessuna copia necessaria", "No copy needed"),
                                self._t(f"Il file di destinazione ha già la stessa dimensione e la stessa data; verrà saltato:\n\n{rel}",
                                        f"The destination file already has the same size and date; it will be skipped:\n\n{rel}"))
            return
        if os.path.exists(dst) and not stessa_dimensione_data_diversa:
            domanda = (self._t(f"La cartella esiste già. Verranno copiati solo i file mancanti o con dimensione diversa.\n\nProcedere?\n\n'{rel}'",
                               f"The folder already exists. Only missing files or files with a different size will be copied.\n\nContinue?\n\n'{rel}'")
                       if os.path.isdir(src) else
                       self._t(f"Elemento esistente. Vuoi sovrascriverlo?\n\n'{rel}'",
                               f"Item already exists. Overwrite it?\n\n'{rel}'"))
            if not messagebox.askyesno(self._t("Sovrascrivi", "Overwrite"), domanda): return
        self._chiedi_verifica_hash_copia()
        self.lbl_status.config(text=self._t("Copia in corso...", "Copying..."))
        # Finestra di avanzamento anche per la copia singola dal menu contestuale.
        self._crea_finestra_avanzamento_copia(self._t("Copia elemento selezionato", "Copy selected item"))
        threading.Thread(target=self._worker_copia, args=([("", src, dst)], c1, c2, dst), daemon=True).start()

    def _avvia_copia_multipla(self, coppie, c1, c2, base_dst):
        """copia di più elementi selezionati con una sola conferma."""
        try:
            if os.path.samefile(coppie[0][1], coppie[0][2]):
                messagebox.showwarning(self._t("Copia non necessaria", "Copy not needed"),
                                       self._t("Sorgente e destinazione indicano lo stesso elemento.",
                                               "Source and destination point to the same item."))
                return
        except OSError:
            pass
        nomi = [rel for rel, _s, _d in coppie]
        domanda = self._t(
            f"Copiare {len(coppie)} elementi selezionati?\n\n{self._elenco_breve(nomi)}\n\n"
            "I file mancanti o con dimensione diversa verranno copiati (sovrascrivendo quelli esistenti); "
            "quelli con la stessa dimensione vengono saltati.",
            f"Copy {len(coppie)} selected items?\n\n{self._elenco_breve(nomi)}\n\n"
            "Missing files or files with a different size will be copied (overwriting existing ones); "
            "files with the same size are skipped.")
        if not messagebox.askyesno(self._t("Copia elementi selezionati", "Copy selected items"), domanda):
            return
        self._chiedi_verifica_hash_copia()
        self.lbl_status.config(text=self._t("Copia in corso...", "Copying..."))
        self._crea_finestra_avanzamento_copia(self._t(f"Copia di {len(coppie)} elementi selezionati",
                                                      f"Copy of {len(coppie)} selected items"))
        threading.Thread(target=self._worker_copia, args=(coppie, c1, c2, base_dst), daemon=True).start()

    def _crea_finestra_avanzamento_copia(self, titolo):
        self._copia_interrotta.clear()
        self._copia_nascosta = False
        self.finestra_copia = tk.Toplevel(self.root)
        self.finestra_copia.title(titolo)
        self.finestra_copia.protocol("WM_DELETE_WINDOW", self._chiedi_chiusura_finestra_copia)
        # Finestra più larga: i percorsi di rete sono spesso molto lunghi.
        self.finestra_copia.geometry("1100x480")
        self.finestra_copia.minsize(850, 360)
        self.finestra_copia.transient(self.root)
        self.finestra_copia.resizable(True, True)
        tk.Label(self.finestra_copia, text=titolo, font=("Arial", 11, "bold")).pack(anchor="w", padx=8, pady=(7, 2))
        self.lbl_file_copia = tk.Label(self.finestra_copia, text=self._t("Preparazione...", "Preparing..."),
                                       anchor="w", justify="left", wraplength=1020, font=("Arial", 10))
        self.lbl_file_copia.pack(fill="x", padx=8, pady=2)
        self.barra_progresso_copia = ttk.Progressbar(
            self.finestra_copia, orient="horizontal", mode="determinate", maximum=100,
            style="BlueCopy.Horizontal.TProgressbar"
        )
        self.barra_progresso_copia.pack(fill="x", padx=8, pady=(2, 5))
        self._copia_byte_totali = 0
        self._copia_byte_completati = 0
        self._copia_byte_ultimo_aggiornamento = 0
        self._copia_file_totali = 0
        self._copia_file_elaborati = 0
        contenitore_lista = tk.Frame(self.finestra_copia)
        contenitore_lista.pack(fill="both", expand=True, padx=8, pady=(1, 6))
        contenitore_lista.rowconfigure(0, weight=1)
        contenitore_lista.columnconfigure(0, weight=1)
        self.lista_file_copiati = tk.Listbox(
            contenitore_lista, height=10, font=("Arial", 10),
            xscrollcommand=lambda *args: barra_orizzontale.set(*args)
        )
        self.lista_file_copiati.grid(row=0, column=0, sticky="nsew")
        barra_lista = ttk.Scrollbar(contenitore_lista, orient="vertical", command=self.lista_file_copiati.yview)
        barra_lista.grid(row=0, column=1, sticky="ns")
        barra_orizzontale = ttk.Scrollbar(contenitore_lista, orient="horizontal", command=self.lista_file_copiati.xview)
        barra_orizzontale.grid(row=1, column=0, sticky="ew")
        self.lista_file_copiati.configure(yscrollcommand=barra_lista.set, xscrollcommand=barra_orizzontale.set)
        # La rotellina scorre la lista anche quando il puntatore è sopra di essa.
        self.lista_file_copiati.bind("<MouseWheel>", lambda e: self.lista_file_copiati.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.lista_file_copiati.bind("<Button-4>", lambda e: self.lista_file_copiati.yview_scroll(-1, "units"))
        self.lista_file_copiati.bind("<Button-5>", lambda e: self.lista_file_copiati.yview_scroll(1, "units"))
        # Posiziona la finestra al centro della finestra principale.
        self.finestra_copia.update_idletasks()
        try:
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - self.finestra_copia.winfo_width()) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - self.finestra_copia.winfo_height()) // 2)
            self.finestra_copia.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _reimposta_byte_copia(self, totale, percorso):
        self._copia_t0 = time.monotonic()
        self._copia_campioni = []          # (istante, byte completati) per la velocità recente
        self._copia_byte_totali = totale
        self._copia_byte_completati = 0
        self._copia_byte_ultimo_aggiornamento = 0
        self.root.after(0, self._mostra_progresso_byte_copia, 0, 0, totale, percorso)

    def _aggiorna_byte_copia(self, quanti, percorso):
        """Aggiorna la barra in modo limitato per non rallentare il trasferimento."""
        self._copia_byte_completati = max(0, self._copia_byte_completati + quanti)
        if quanti < 0:
            # Tentativo annullato (es. riprova): riallinea senza aggiornare la GUI.
            self._copia_byte_ultimo_aggiornamento = self._copia_byte_completati
            return
        soglia = max(1024 * 1024, self._copia_byte_totali // 200)
        if (self._copia_byte_completati - self._copia_byte_ultimo_aggiornamento >= soglia
                or self._copia_byte_completati >= self._copia_byte_totali):
            self._copia_byte_ultimo_aggiornamento = self._copia_byte_completati
            totale = self._copia_byte_totali
            completati = self._copia_byte_completati
            percentuale = 100 if totale <= 0 else min(100, completati * 100 / totale)
            self.root.after(0, self._mostra_progresso_byte_copia,
                            percentuale, completati, totale, percorso)

    def _mostra_progresso_byte_copia(self, percentuale, completati, totale, percorso):
        try:
            if not self.finestra_copia.winfo_exists():
                return
            self.barra_progresso_copia.configure(value=percentuale)
            if getattr(self, "_copia_nascosta", False):
                self.progress_bar.config(value=percentuale)
                self.lbl_status.config(text=self._t(f"Operazione in corso in background… {percentuale:.0f}%",
                                                   f"Operation running in the background… {percentuale:.0f}%"))
            self.lbl_file_copia.config(
                text=self._t("Progresso", "Progress") + f": {percentuale:.1f}% ({format_size(completati)} / {format_size(totale)})"
                     + self._testo_velocita_e_tempo(completati, totale) + f"\nFile: {percorso}"
            )
        except (tk.TclError, AttributeError):
            pass

    def _testo_velocita_e_tempo(self, completati, totale):
        """Riga «Velocità · Trascorso · Rimanente» (vuota finché i dati non sono affidabili)."""
        try:
            adesso = time.monotonic()
            trascorso = adesso - self._copia_t0
            campioni = self._copia_campioni
            campioni.append((adesso, completati))
            # velocità sugli ultimi ~15 secondi: più reattiva della media complessiva
            while len(campioni) > 2 and adesso - campioni[0][0] > 15:
                campioni.pop(0)
            t_prima, b_prima = campioni[0]
            velocita = (completati - b_prima) / (adesso - t_prima) if adesso - t_prima >= 1 else 0
            if velocita <= 0 and trascorso >= 2 and completati > 0:
                velocita = completati / trascorso
            if trascorso < 2 or velocita <= 0 or completati <= 0:
                return ""
            parti = [self._t("Velocità", "Speed") + f": {format_size(velocita)}/s",
                     self._t("Trascorso", "Elapsed") + f": {format_durata(trascorso)}"]
            if totale > completati:
                parti.append(self._t("Rimanente", "Remaining") + f": ~{format_durata((totale - completati) / velocita)}")
            return "\n" + "  ·  ".join(parti)
        except (AttributeError, TypeError, ZeroDivisionError):
            return ""

    @staticmethod
    def _sha256_file(percorso):
        """Calcola SHA-256 leggendo il file a blocchi, senza caricarlo tutto in memoria."""
        digest = hashlib.sha256()
        with open(percorso, "rb") as file:
            for blocco in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(blocco)
        return digest.hexdigest()

    def _verifica_copia_sha256(self, src, dst):
        """Confronta l'hash della sorgente e della copia; solleva errore se non coincidono."""
        if self._sha256_file(src) != self._sha256_file(dst):
            raise ErroreVerificaHash(f"Verifica SHA-256 NON RIUSCITA: il contenuto differisce. Sorgente: {src} | Destinazione: {dst}")
        return True

    @staticmethod
    def _prepara_sovrascrittura(dst):
        """Prepara la destinazione senza cancellare un file normale.

        Su NTFS è frequente avere Write ma non Delete (es. E:\\Flac):
        os.remove fallisce con Accesso negato, mentre la scrittura funziona.
        Toglie la sola lettura (e su Windows anche nascosto/sistema, che
        bloccano la riscrittura di file come Thumbs.db).
        """
        if not os.path.lexists(dst):
            return
        if os.path.isfile(dst) and not os.path.islink(dst):
            if IS_WINDOWS:
                try:
                    _win_imposta_attributi(dst, FILE_ATTRIBUTE_NORMAL)
                except OSError:
                    pass
            try:
                os.chmod(dst, os.stat(dst).st_mode | stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass
            return
        if os.path.isdir(dst) and not os.path.islink(dst):
            shutil.rmtree(dst)
            return
        os.remove(dst)

    def _scrivi_dati(self, src, dst):
        """Scrive SOLO il contenuto del file (nessuna data/attributo)."""
        esisteva = os.path.isfile(dst) and not os.path.islink(dst)
        scritti = 0
        with open(src, "rb") as origine:
            try:
                # 'r+b' riapre il file esistente invece di ricrearlo: su Windows evita
                # l'Accesso negato sui file nascosti/di sistema e non richiede il
                # permesso di eliminazione. 'truncate' elimina eventuali byte in eccesso.
                with open(dst, "r+b" if esisteva else "wb") as destinazione:
                    while True:
                        if not esisteva and self._copia_interrotta.is_set():
                            raise CopiaInterrotta()
                        blocco = origine.read(1024 * 1024)
                        if not blocco:
                            break
                        destinazione.write(blocco)
                        scritti += len(blocco)
                        self._aggiorna_byte_copia(len(blocco), dst)
                    destinazione.truncate()
            except BaseException:
                if scritti:
                    self._aggiorna_byte_copia(-scritti, dst)
                if not esisteva:
                    try:
                        os.remove(dst)  # non lasciare copie parziali di file nuovi
                    except OSError:
                        pass
                raise

    def _scrivi_dati_con_riprova(self, src, dst):
        """Se il file è bloccato (antivirus, altro programma) riprova una volta."""
        try:
            self._scrivi_dati(src, dst)
        except OSError as errore:
            if not self._errore_temporaneo(errore):
                raise
            self._registra_errore_copia(dst, errore, livello="RIPROVO")
            time.sleep(ATTESA_RIPROVA_SECONDI)
            self._prepara_sovrascrittura(dst)
            self._scrivi_dati(src, dst)

    def _applica_metadati(self, src, dst):
        """Applica data e attributi dopo la copia. Gli errori diventano solo avvisi."""
        avvisi = []
        try:
            shutil.copystat(src, dst)
        except OSError as errore:
            try:
                st = os.stat(src)
                os.utime(dst, ns=(st.st_atime_ns, st.st_mtime_ns))
                avvisi.append(self._t("Attributi non applicati", "Attributes not applied") + f" ({self._motivo_errore(errore)})")
            except OSError as errore_data:
                avvisi.append(self._t("Data e attributi non applicati", "Date and attributes not applied") + f" ({self._motivo_errore(errore_data)})")
        if IS_WINDOWS:
            try:
                attributi = getattr(os.stat(src), "st_file_attributes", 0) & ATTRIBUTI_COPIABILI
                _win_imposta_attributi(dst, attributi or FILE_ATTRIBUTE_NORMAL)
            except OSError as errore:
                avvisi.append(self._t("Attributi Windows non applicati", "Windows attributes not applied") + f" ({self._motivo_errore(errore)})")
        return avvisi

    def _aggiungi_interrotti(self, risultato, nomi):
        """Registra come «non copiati» i file che l'interruzione ha lasciato da copiare."""
        motivo = self._t("Interrotto dall'utente", "Stopped by the user")
        risultato["non_copiati"].extend((nome, motivo) for nome in nomi)
        risultato["interrotta"] = True

    @staticmethod
    def _nome_con_prefisso(prefisso, relativo):
        return os.path.join(prefisso, relativo) if prefisso else relativo

    def _nomi_da_piani(self, piani):
        """Nomi dei file ancora da copiare in una lista di piani (rel, src, dst, analisi)."""
        nomi = []
        for rel, src, _dst, analisi in piani:
            if analisi is None:
                nomi.append(rel or os.path.basename(src))
            else:
                nomi.extend(self._nome_con_prefisso(rel, r) for r, _d, _st in analisi["elementi"])
        return nomi

    def _nuovo_risultato(self):
        return {"copiati": [], "saltati": [], "non_copiati": [], "avvisi": [], "ignorati": [], "interrotta": False}

    def _copia_un_file(self, src, dst, risultato, nome=None):
        """Copia un singolo file. Non solleva mai eccezioni: aggiorna `risultato`
        e restituisce la riga da mostrare nella finestra di avanzamento."""
        nome = nome or src
        try:
            if self._stessa_dimensione(src, dst):
                if self._stessa_dimensione_e_data(src, dst):
                    risultato["saltati"].append(nome)
                    return "= " + nome + self._t("  (dimensione e data uguali, saltato)", "  (same size and date, skipped)")
                if not self._chiedi_sovrascrittura_stessa_dimensione(src, dst, nome):
                    risultato["saltati"].append(nome)
                    return "= " + nome + self._t("  (saltato su richiesta)", "  (skipped by user)")
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            self._prepara_sovrascrittura(dst)
            self._scrivi_dati_con_riprova(src, dst)
            # Controllo rapido sempre attivo: dimensione sorgente e destinazione.
            dimensione_src = os.path.getsize(src)
            dimensione_dst = os.path.getsize(dst)
            if dimensione_src != dimensione_dst:
                raise IOError(
                    self._t("Verifica dimensione non riuscita", "File size verification failed")
                    + f": sorgente={dimensione_src}, destinazione={dimensione_dst}"
                )
            # Il controllo più costoso viene eseguito solo se richiesto dall'utente.
            if getattr(self, "_verifica_hash_copia", False):
                self._verifica_copia_sha256(src, dst)
            avvisi = self._applica_metadati(src, dst)
            for avviso in avvisi:
                risultato["avvisi"].append((nome, avviso))
                self._registra_errore_copia(dst, avviso, livello="AVVISO")
            risultato["copiati"].append(nome)
            verifica = self._t("dimensione e SHA-256 OK", "size and SHA-256 OK") if getattr(self, "_verifica_hash_copia", False) else self._t("dimensione OK", "size OK")
            return ("⚠ " if avvisi else "✔ ") + nome + f"  ({verifica})"
        except CopiaInterrotta:
            raise
        except Exception as errore:
            cache = self._is_file_cache(src)
            self._registra_errore_copia(src, errore, ignorato=cache)
            motivo = self._motivo_errore(errore)
            if cache:
                risultato["ignorati"].append((nome, motivo))
            else:
                risultato["non_copiati"].append((nome, motivo))
            return "✖ " + nome + f"  — {motivo}"

    def _prepara_cartella_destinazione(self, dst_dir, radice):
        """Crea la cartella di destinazione senza seguire link simbolici.

        Restituisce True oppure il motivo per cui non è stato possibile crearla.
        """
        try:
            rel = os.path.relpath(dst_dir, radice)
            corrente = radice
            if rel != ".":
                for parte in rel.split(os.sep):
                    corrente = os.path.join(corrente, parte)
                    # Un link o un file al posto della cartella potrebbe far scrivere
                    # fuori dall'albero scelto: viene sostituito da una cartella reale.
                    if os.path.lexists(corrente) and (os.path.islink(corrente) or not os.path.isdir(corrente)):
                        try:
                            os.unlink(corrente)
                        except OSError:
                            os.rmdir(corrente)
            os.makedirs(dst_dir, exist_ok=True)
            return True
        except Exception as errore:
            self._registra_errore_copia(dst_dir, errore)
            return self._t("Cartella non creabile", "Folder cannot be created") + f" ({self._motivo_errore(errore)})"

    def _copia_da_analisi(self, sorgente, destinazione, analisi, risultato, prefisso=""):
        """Copia i file indicati da _scansiona_copia, uno per volta, senza fermarsi agli errori.

        `prefisso` è il percorso relativo mostrato davanti ai nomi nel riepilogo.
        """
        cartelle_pronte = {}
        in_attesa = []

        def _cartella_ok(dst_dir):
            if dst_dir not in cartelle_pronte:
                cartelle_pronte[dst_dir] = self._prepara_cartella_destinazione(dst_dir, destinazione)
            return cartelle_pronte[dst_dir]

        esito_radice = _cartella_ok(destinazione)
        if esito_radice is not True:
            raise RuntimeError(f"{destinazione}: {esito_radice}")
        for rel_dir in analisi["cartelle_mancanti"]:
            esito = _cartella_ok(os.path.join(destinazione, rel_dir))
            rel_dir = os.path.join(prefisso, rel_dir) if prefisso else rel_dir
            if esito is not True:
                risultato["non_copiati"].append((rel_dir + os.sep, esito))
                in_attesa.append("✖ " + rel_dir + os.sep + f"  — {esito}")

        self._copia_file_totali = len(analisi["elementi"])
        self._copia_file_elaborati = 0
        self.root.after(0, self._aggiorna_contatore_file_copia, 0, self._copia_file_totali, "")
        elementi_da_copiare = analisi["elementi"]
        for indice, (relativo_analisi, _dimensione, stato) in enumerate(elementi_da_copiare):
            if self._copia_interrotta.is_set():
                self._aggiungi_interrotti(risultato, [self._nome_con_prefisso(prefisso, r)
                                                      for r, _d, _st in elementi_da_copiare[indice:]])
                break
            src_file = os.path.join(sorgente, relativo_analisi)
            dst_file = os.path.join(destinazione, relativo_analisi)
            relativo = os.path.join(prefisso, relativo_analisi) if prefisso else relativo_analisi
            if stato == STATO_ERRORE_LETTURA:
                motivo = self._t("Errore lettura sorgente", "Source read error")
                risultato["non_copiati"].append((relativo, motivo))
                riga = "✖ " + relativo + f"  — {motivo}"
            else:
                esito = _cartella_ok(os.path.dirname(dst_file))
                if esito is not True:
                    risultato["non_copiati"].append((relativo, esito))
                    riga = "✖ " + relativo + f"  — {esito}"
                else:
                    try:
                        riga = self._copia_un_file(src_file, dst_file, risultato, relativo)
                    except CopiaInterrotta:
                        # il file in corso (copia parziale rimossa) e tutti quelli dopo restano da copiare
                        self._aggiungi_interrotti(risultato, [self._nome_con_prefisso(prefisso, r)
                                                              for r, _d, _st in elementi_da_copiare[indice:]])
                        break
            in_attesa.append(riga)
            # Aggiorna la GUI ogni 20 file invece di inserirli uno per volta.
            if len(in_attesa) >= 20:
                blocco, in_attesa = in_attesa, []
                self._copia_file_elaborati += len(blocco)
                self.root.after(0, self._aggiorna_avanzamento_copia_batch, blocco, len(risultato["copiati"]))
                self.root.after(0, self._aggiorna_contatore_file_copia, self._copia_file_elaborati, self._copia_file_totali, blocco[-1] if blocco else "")
        if in_attesa:
            self._copia_file_elaborati += len(in_attesa)
            self.root.after(0, self._aggiorna_avanzamento_copia_batch, in_attesa, len(risultato["copiati"]))
            self.root.after(0, self._aggiorna_contatore_file_copia, self._copia_file_elaborati, self._copia_file_totali, in_attesa[-1])

    def _worker_copia(self, coppie, c1, c2, destinazione_riepilogo=None):
        """Copia uno o più elementi: coppie = [(nome_relativo, src, dst), ...]."""
        risultato = self._nuovo_risultato()
        piani = []
        totale = 0
        for indice_coppia, (rel, src, dst) in enumerate(coppie):
            try:
                if self._copia_interrotta.is_set():
                    raise CopiaInterrotta()
                if os.path.isdir(src):
                    # Non eliminare la cartella di destinazione: copia solo file mancanti
                    # o con dimensione diversa e conserva gli elementi presenti solo lì.
                    analisi = self._scansiona_copia(src, dst, applica_filtri=False)
                    risultato["saltati"].extend([None] * analisi["saltati"])
                    totale += analisi["totale"]
                    piani.append((rel, src, dst, analisi))
                else:
                    try:
                        totale += os.path.getsize(src)
                    except OSError:
                        pass
                    piani.append((rel, src, dst, None))
            except CopiaInterrotta:
                # elementi non ancora analizzati: restano da copiare
                self._aggiungi_interrotti(risultato, [r or os.path.basename(sr) for r, sr, _d in coppie[indice_coppia:]])
                break
            except Exception as e:
                self._registra_errore_copia(src, e, ignorato=False)
                risultato["non_copiati"].append((rel or src, self._motivo_errore(e)))
        self._reimposta_byte_copia(totale, coppie[0][1])
        for indice_piano, (rel, src, dst, analisi) in enumerate(piani):
            if self._copia_interrotta.is_set():
                self._aggiungi_interrotti(risultato, self._nomi_da_piani(piani[indice_piano:]))
                break
            try:
                if analisi is not None:
                    self._copia_da_analisi(src, dst, analisi, risultato, prefisso=rel)
                else:
                    riga = self._copia_un_file(src, dst, risultato, rel or os.path.basename(src))
                    self.root.after(0, self._aggiorna_avanzamento_copia_batch, [riga], len(risultato["copiati"]))
            except CopiaInterrotta:
                self._aggiungi_interrotti(risultato, self._nomi_da_piani(piani[indice_piano:]))
                break
            except Exception as e:
                self._registra_errore_copia(src, e, ignorato=False)
                risultato["non_copiati"].append((rel or src, self._motivo_errore(e)))
        def completato():
            self._chiudi_finestra_copia()
            # Aggiorna automaticamente il ramo in cui è stato copiato il file.
            # Per una copia multipla, destinazione_riepilogo è la cartella di destinazione;
            # per una copia singola è il percorso del file appena copiato.
            try:
                destinazione = destinazione_riepilogo or coppie[0][2]
                if os.path.isdir(destinazione):
                    cartella_dest = destinazione
                else:
                    cartella_dest = os.path.dirname(destinazione)
                radice_dest = None
                for radice in (c1, c2):
                    try:
                        if os.path.commonpath([os.path.abspath(cartella_dest), os.path.abspath(radice)]) == os.path.abspath(radice):
                            radice_dest = radice
                            break
                    except (ValueError, OSError):
                        continue
                if radice_dest:
                    rel_dir_refresh = os.path.relpath(cartella_dest, radice_dest)
                    if rel_dir_refresh == ".":
                        rel_dir_refresh = ""
                    self.lbl_status.config(text=self._t("Copia completata. Aggiornamento della cartella…",
                                                        "Copy finished. Refreshing destination folder…"))
                    self.is_scanning = True
                    self.btn_stop.config(state="normal")
                    self._cancel_scan.clear()
                    threading.Thread(target=self._worker_aggiorna_sottocartella,
                                     args=(c1, c2, rel_dir_refresh), daemon=True).start()
                else:
                    self.lbl_status.config(text=self._t("Copia completata.", "Copy finished."))
            except Exception:
                self.lbl_status.config(text=self._t("Copia completata.", "Copy finished."))
            # Per la copia di un singolo file, evita la grande finestra riepilogativa
            # se l'operazione è riuscita senza errori: il risultato è già evidente
            # dalla finestra di avanzamento e dalla barra di stato. Mostra i dettagli
            # solo se ci sono problemi o avvisi; per copie multiple conserva il riepilogo.
            riepilogo_necessario = (
                len(coppie) > 1 or bool(risultato["non_copiati"])
                or bool(risultato["avvisi"]) or bool(risultato["ignorati"]) or risultato.get("interrotta")
            )
            if riepilogo_necessario:
                self._mostra_riepilogo_copia(
                    risultato, self._t("Riepilogo copia elementi" if len(coppie) > 1 else "Dettagli copia elemento",
                                       "Items copy summary" if len(coppie) > 1 else "Copy item details"),
                    (self._t("Copia INTERROTTA dall'utente: gli elementi non ancora copiati sono stati lasciati com'erano.\n",
                             "Copy STOPPED by the user: items not copied yet were left as they were.\n") if risultato.get("interrotta") else "")
                    + self._t("La cartella di destinazione è stata aggiornata automaticamente.",
                              "The destination folder has been refreshed automatically."),
                    destinazione_riepilogo)
        self.root.after(0, completato)

    def _notifica_fine_operazione(self):
        """Se la finestra non è in primo piano: lampeggia nella barra delle applicazioni e suona."""
        try:
            if self.root.focus_displayof() is not None:
                return  # l'utente sta guardando il programma
        except (tk.TclError, KeyError):
            pass
        try:
            if not IS_WINDOWS:
                self.root.bell()
                return
            import ctypes
            from ctypes import wintypes

            class FLASHWINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.UINT), ("hwnd", wintypes.HWND),
                            ("dwFlags", wintypes.DWORD), ("uCount", wintypes.UINT),
                            ("dwTimeout", wintypes.DWORD)]
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            # FLASHW_ALL | FLASHW_TIMERNOFG: lampeggia finché la finestra non torna in primo piano
            info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 0x0F, 0, 0)
            ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except (ImportError, RuntimeError):
                pass
        except (OSError, AttributeError, tk.TclError):
            pass

    def _mostra_riepilogo_copia(self, risultato, titolo, nota="", destinazione=None):
        """Finestra finale: copiati, saltati (stessa dimensione), non copiati con motivo, avvisi."""
        self._notifica_fine_operazione()
        copiati = len(risultato["copiati"])
        saltati = len(risultato["saltati"])
        non_copiati = risultato["non_copiati"]
        avvisi = risultato["avvisi"]
        ignorati = risultato["ignorati"]
        finestra = tk.Toplevel(self.root)
        finestra.title(titolo)
        finestra.geometry("820x500")
        finestra.transient(self.root)
        finestra.bind("<Destroy>", lambda e, w=finestra: self._ripristina_focus_principale() if e.widget is w else None, add="+")
        interrotta = bool(risultato.get("interrotta"))
        if interrotta:
            intestazione = self._t("Operazione interrotta dall'utente", "Operation stopped by the user")
        elif not non_copiati:
            intestazione = self._t("Copia completata", "Copy completed")
        else:
            intestazione = self._t("Copia completata con file non copiati", "Copy completed with files not copied")
        tk.Label(finestra, text=intestazione, font=("Segoe UI", 15, "bold"),
                 fg="#dc2626" if (non_copiati or interrotta) else None).pack(anchor="w", padx=12, pady=(12, 4))
        motivo_stop = self._t("Interrotto dall'utente", "Stopped by the user")
        n_interrotti = sum(1 for _nome, motivo in non_copiati if motivo == motivo_stop)
        if interrotta:
            righe_non_copiati = [
                self._t("File non copiati (operazione interrotta)", "Files not copied (operation stopped)") + f": {n_interrotti}",
                self._t("File non copiati per errore", "Files not copied because of errors") + f": {len(non_copiati) - n_interrotti}",
            ]
        else:
            righe_non_copiati = [self._t("File non copiati", "Files not copied") + f": {len(non_copiati)}"]
        righe = [
            self._t("File copiati", "Files copied") + f": {copiati}",
            self._t("File saltati (stessa dimensione)", "Files skipped (same size)") + f": {saltati}",
            *righe_non_copiati,
            self._t("Avvisi (data/attributi non applicati)", "Warnings (date/attributes not applied)") + f": {len(avvisi)}",
        ]
        if ignorati:
            righe.append(self._t("File cache ignorati (Thumbs.db / .@__thumb)", "Cache files ignored (Thumbs.db / .@__thumb)") + f": {len(ignorati)}")
        tk.Label(finestra, text="\n".join(righe), justify="left", anchor="w").pack(fill="x", padx=12, pady=4)
        area = tk.Frame(finestra); area.pack(fill="both", expand=True, padx=12, pady=8)
        elenco = tk.Listbox(area, font=("Consolas", 9))
        sb = ttk.Scrollbar(area, orient="vertical", command=elenco.yview); elenco.configure(yscrollcommand=sb.set)
        elenco.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        for nome, motivo in non_copiati:
            elenco.insert("end", f"✖ [{self._t('NON COPIATO', 'NOT COPIED')}] {nome}  — {motivo}")
        for nome, avviso in avvisi:
            elenco.insert("end", f"⚠ [{self._t('AVVISO', 'WARNING')}] {nome}  — {avviso}")
        for nome, motivo in ignorati:
            elenco.insert("end", f"· [{self._t('IGNORATO', 'IGNORED')}] {nome}  — {motivo}")
        if not (non_copiati or avvisi or ignorati):
            elenco.insert("end", self._t("Nessun errore o avviso.", "No errors or warnings."))
        if nota:
            tk.Label(finestra, text=nota, justify="left", anchor="w", wraplength=780).pack(fill="x", padx=12)
        riga = tk.Frame(finestra); riga.pack(fill="x", padx=12, pady=10)
        tk.Button(riga, text=self._t("Chiudi", "Close"), command=finestra.destroy).pack(side="right", padx=4)
        tk.Button(riga, text=self._t("Apri log", "Open log"),
                  command=lambda: self.apri_log_errori(finestra)).pack(side="right", padx=4)
        negati = [n for n, motivo in non_copiati if motivo == self._t("Accesso negato", "Access denied")]
        if IS_WINDOWS and destinazione and negati:
            tk.Button(riga, text=self._t("🛡 Ripara permessi destinazione (amministratore)…",
                                         "🛡 Repair destination permissions (administrator)…"),
                      bg="#b45309", fg="white",
                      command=lambda: self.avvia_ripara_permessi(destinazione, parent=finestra)).pack(side="left", padx=4)
        return finestra

    def _aggiorna_preparazione_copia(self, testo):
        """Mostra attività durante la scansione iniziale, evitando l'impressione di blocco."""
        try:
            if self.finestra_copia.winfo_exists():
                self.lbl_file_copia.config(text=testo)
        except (tk.TclError, AttributeError):
            pass

    def _scansiona_copia(self, sorgente, destinazione, applica_filtri=True, aggiorna_progresso=None):
        """Elenca i file da copiare; opzionalmente aggiorna la GUI durante la scansione."""
        elementi, cartelle_mancanti = [], []
        totale = saltati = 0
        cartelle_esaminate = file_esaminati = 0
        for radice, cartelle, file in os.walk(sorgente):
            if self._copia_interrotta.is_set():
                raise CopiaInterrotta()
            cartelle_esaminate += 1
            file_esaminati += len(file)
            if aggiorna_progresso and (cartelle_esaminate == 1 or cartelle_esaminate % 20 == 0 or file_esaminati % 500 < len(file)):
                aggiorna_progresso(cartelle_esaminate, file_esaminati)
            rel_dir = os.path.relpath(radice, sorgente)

            def _rel(nome, rel_dir=rel_dir):
                return nome if rel_dir == "." else os.path.join(rel_dir, nome)

            def _incluso(nome):
                return ".@__thumb" not in nome.casefold() and not (applica_filtri and self._percorso_escluso(_rel(nome)))

            cartelle[:] = sorted(d for d in cartelle if _incluso(d))
            dst_dir = destinazione if rel_dir == "." else os.path.join(destinazione, rel_dir)
            if rel_dir != "." and not os.path.isdir(dst_dir):
                cartelle_mancanti.append(rel_dir)
            for nome in sorted(f for f in file if _incluso(f)):
                src_file = os.path.join(radice, nome)
                if os.path.islink(src_file):
                    continue
                relativo = _rel(nome)
                dst_file = os.path.join(destinazione, relativo)
                try:
                    st = os.stat(src_file, follow_symlinks=False)
                    if self._stessa_dimensione_e_data(src_file, dst_file):
                        saltati += 1
                        continue
                    if not os.path.lexists(dst_file):
                        stato = STATO_MANCANTE
                    else:
                        try:
                            dst_stat = os.stat(dst_file, follow_symlinks=False)
                            # Distinguere la causa reale: contenuto di dimensione
                            # diversa oppure stessa dimensione ma data differente.
                            stato = (STATO_DIVERSO if st.st_size != dst_stat.st_size
                                     else STATO_DATA_DIVERSA)
                        except OSError:
                            stato = STATO_ERRORE_LETTURA
                    elementi.append((relativo, st.st_size, stato))
                    totale += st.st_size
                except OSError:
                    elementi.append((relativo, 0, STATO_ERRORE_LETTURA))
        return {"elementi": elementi, "totale": totale, "saltati": saltati, "cartelle_mancanti": cartelle_mancanti}

    def _analizza_copia(self, sorgente, destinazione):
        """Calcola i file mancanti/diversi e lo spazio richiesto, rispettando i filtri."""
        analisi = self._scansiona_copia(sorgente, destinazione)
        return analisi["elementi"], analisi["totale"]

    def _etichetta_stato(self, stato):
        return {
            STATO_MANCANTE: self._t("Mancante", "Missing"),
            STATO_DIVERSO: self._t("Dimensione diversa", "Different size"),
            STATO_DATA_DIVERSA: self._t("Data diversa", "Different date"),
            STATO_ERRORE_LETTURA: self._t("Errore lettura", "Read error"),
        }.get(stato, stato)

    def _percorsi_copia_validi(self, consenti_destinazione_mancante=False):
        sorgente = os.path.abspath(os.path.normpath(self.safe_combobox_get(self.combo_c1)))
        destinazione = os.path.abspath(os.path.normpath(self.safe_combobox_get(self.combo_c2)))
        if not self._verifica_cartelle_accessibili(sorgente, destinazione, consenti_destinazione_mancante):
            return None, None
        try:
            if os.path.samefile(sorgente, destinazione):
                messagebox.showerror(self._t("Percorsi non validi", "Invalid paths"),
                                     self._t("La cartella sorgente e quella destinazione coincidono.",
                                             "Source and destination folders are the same."))
                return None, None
        except OSError:
            pass
        return sorgente, destinazione

    def verifica_spazio_libero(self):
        # Non eseguire un'analisi ricorsiva sincrona prima del confronto: su
        # dischi grandi o unità di rete può bloccare la finestra per molto tempo.
        if self.is_scanning:
            messagebox.showwarning(
                self._t("Operazione in corso", "Operation in progress"),
                self._t("Attendi il completamento della scansione o della copia in corso.",
                        "Wait for the current scan or copy to finish."))
            return
        sorgente, destinazione = self._percorsi_copia_validi()
        if not sorgente or not destinazione:
            return
        if self._cerca_cache(sorgente) is None or self._cerca_cache(destinazione) is None:
            messagebox.showinfo(
                self._t("Scansione necessaria", "Scan required"),
                self._t(
                    "Prima di verificare lo spazio libero, seleziona le cartelle e premi «Confronta».\n"
                    "Al termine della scansione potrai controllare lo spazio necessario.",
                    "Before checking free space, select the folders and click “Compare”.\n"
                    "After the scan finishes, you can check the required space."))
            return
        try:
            analisi = self._scansiona_copia(sorgente, destinazione)
            elementi, richiesti = analisi["elementi"], analisi["totale"]
            libero = shutil.disk_usage(destinazione).free
            differenza = libero - richiesti
            if self.lingua == "en":
                stato = "Enough space" if differenza >= 0 else "Not enough space"
                testo = (f"{stato}\n\nFiles to copy/update: {len(elementi)}\nFiles skipped (same size): {analisi['saltati']}\n"
                         f"Estimated space needed: {format_size(richiesti)}\nFree space on destination: {format_size(libero)}\n"
                         f"Estimated margin after copy: {format_size(differenza)}\n\n"
                         "The estimate uses file sizes; files with the same size are not copied.")
            else:
                stato = "Spazio sufficiente" if differenza >= 0 else "Spazio insufficiente"
                testo = (f"{stato}\n\nFile da copiare/aggiornare: {len(elementi)}\nFile saltati (stessa dimensione): {analisi['saltati']}\n"
                         f"Spazio stimato necessario: {format_size(richiesti)}\nSpazio libero sulla destinazione: {format_size(libero)}\n"
                         f"Margine stimato dopo la copia: {format_size(differenza)}\n\n"
                         "La stima usa la dimensione dei file; quelli con la stessa dimensione non vengono copiati.")
            messagebox.showinfo(self._t("Verifica spazio libero", "Free space check"), testo)
        except Exception as e:
            messagebox.showerror(self._t("Errore verifica spazio", "Free space check error"), str(e))

    def anteprima_differenze(self):
        """Calcola l'anteprima in background, mantenendo reattiva la finestra principale."""
        if self.is_scanning:
            messagebox.showwarning(self._t("Operazione in corso", "Operation in progress"),
                                   self._t("Attendi il completamento della scansione o della copia in corso.",
                                           "Wait for the current scan or copy to finish."))
            return
        if getattr(self, "_preview_in_corso", False):
            return
        sorgente, destinazione = self._percorsi_copia_validi()
        if not sorgente or not destinazione:
            return
        chiavi_cache = {os.path.abspath(os.path.normpath(k)) for k in self.folder_cache}
        if sorgente not in chiavi_cache or destinazione not in chiavi_cache:
            if self._preview_dopo_confronto:
                self._preview_dopo_confronto = False
                messagebox.showerror(self._t("Anteprima non disponibile", "Preview unavailable"),
                    self._t("La scansione è terminata senza creare la cache di entrambe le cartelle. Controlla i percorsi e riprova.",
                            "The scan finished without creating cache entries for both folders. Check the paths and try again."))
                return
            self._preview_dopo_confronto = True
            self.avvia_confronto()
            return

        self._preview_in_corso = True
        attesa = tk.Toplevel(self.root)
        attesa.title(self._t("Preparazione anteprima", "Preparing preview"))
        attesa.transient(self.root)
        attesa.resizable(False, False)
        attesa.protocol("WM_DELETE_WINDOW", lambda: None)
        contenuto = tk.Frame(attesa, padx=22, pady=18)
        contenuto.pack(fill="both", expand=True)
        tk.Label(contenuto, text=self._t("Analisi delle differenze in corso…", "Analyzing differences…"),
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(contenuto, text=self._t("La scansione può richiedere tempo con cartelle grandi o dischi di rete. Il programma resta utilizzabile.",
                                        "Large folders or network drives may take time. The application should remain responsive."),
                 justify="left", wraplength=430).pack(anchor="w", pady=(0, 10))
        barra = ttk.Progressbar(contenuto, mode="indeterminate", length=420)
        barra.pack(fill="x")
        barra.start(12)
        attesa.update_idletasks()
        try:
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - attesa.winfo_reqwidth()) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - attesa.winfo_reqheight()) // 2)
            attesa.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

        def lavoro():
            try:
                analisi = self._scansiona_copia(sorgente, destinazione)
                libero = shutil.disk_usage(destinazione).free
                risultato = (analisi, libero, None)
            except Exception as e:
                risultato = (None, None, str(e))
            def conclusione():
                self._preview_in_corso = False
                try:
                    barra.stop()
                    if attesa.winfo_exists(): attesa.destroy()
                except tk.TclError:
                    pass
                analisi, libero, errore = risultato
                if errore:
                    messagebox.showerror(self._t("Errore anteprima", "Preview error"), errore)
                    return
                self._mostra_anteprima_differenze(sorgente, destinazione, analisi, libero)
            try:
                self.root.after(0, conclusione)
            except tk.TclError:
                pass
        threading.Thread(target=lavoro, daemon=True).start()

    def _mostra_anteprima_differenze(self, sorgente, destinazione, analisi, libero):
        elementi, richiesti = analisi["elementi"], analisi["totale"]
        finestra = tk.Toplevel(self.root)
        finestra.title(self._t("Anteprima differenze prima della copia", "Preview of differences before copying"))
        finestra.geometry("760x520")
        finestra.transient(self.root)
        tk.Label(finestra, text=self._t(f"Anteprima: {len(elementi)} file da copiare o aggiornare",
                                        f"Preview: {len(elementi)} files to copy or update"),
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        tk.Label(finestra, text=self._t(
            f"Da: {sorgente}\nA: {destinazione}\nSpazio richiesto stimato: {format_size(richiesti)} | Libero: {format_size(libero)}\nFile saltati perché hanno già la stessa dimensione: {analisi['saltati']}",
            f"From: {sorgente}\nTo: {destinazione}\nEstimated space needed: {format_size(richiesti)} | Free: {format_size(libero)}\nFiles skipped because they already have the same size: {analisi['saltati']}"),
            justify="left", anchor="w", wraplength=720).pack(fill="x", padx=12, pady=4)
        area = tk.Frame(finestra); area.pack(fill="both", expand=True, padx=12, pady=8)
        elenco = tk.Listbox(area, font=("Consolas", 9))
        sb = ttk.Scrollbar(area, orient="vertical", command=elenco.yview); elenco.configure(yscrollcommand=sb.set)
        elenco.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        for relativo, dimensione, stato in elementi:
            elenco.insert("end", f"[{self._etichetta_stato(stato)}] {relativo}  ({format_size(dimensione)})")
        if not elementi:
            elenco.insert("end", self._t("Nessun file da copiare: i file mancano o hanno già la stessa dimensione.",
                                         "No files to copy: all files already exist with the same size."))
        if richiesti > libero:
            tk.Label(finestra, text=self._t("ATTENZIONE: lo spazio libero sembra insufficiente.",
                                            "WARNING: free space seems insufficient."),
                     fg="#dc2626", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12)
        riga = tk.Frame(finestra); riga.pack(fill="x", padx=12, pady=10)
        tk.Button(riga, text=self._t("Chiudi", "Close"), command=finestra.destroy).pack(side="right", padx=4)
        tk.Button(riga, text=self._t("Procedi con la copia…", "Proceed with copy…"), bg="#0f766e", fg="white",
                  command=lambda: (finestra.destroy(), self.copia_tutte_modifiche_sinistra_destra())).pack(side="right", padx=4)

    def copia_tutte_modifiche_sinistra_destra(self):
        """Copia da sinistra a destra file mancanti o con dimensione diversa, senza cancellare extra a destra."""
        if self.is_scanning:
            messagebox.showwarning(self._t("Operazione in corso", "Operation in progress"),
                                   self._t("Attendi il completamento della scansione o della copia in corso.",
                                           "Wait for the current scan or copy to finish."))
            return
        sorgente = os.path.abspath(os.path.normpath(self.safe_combobox_get(self.combo_c1)))
        destinazione = os.path.abspath(os.path.normpath(self.safe_combobox_get(self.combo_c2)))
        if not self._verifica_cartelle_accessibili(sorgente, destinazione):
            return
        # Controlla prima che le cartelle non siano la stessa. samefile può fallire
        # su alcuni filesystem/percorsi: in tal caso proseguiamo con il controllo
        # lessicale, invece di bloccare la copia con un falso errore.
        try:
            if os.path.samefile(sorgente, destinazione):
                messagebox.showerror(self._t("Percorsi non validi", "Invalid paths"),
                                     self._t("La cartella sorgente e quella destinazione coincidono.",
                                             "Source and destination folders are the same."))
                return
        except OSError:
            pass

        # Evita copie ricorsive quando una cartella è contenuta nell'altra.
        # commonpath solleva ValueError, ad esempio, se i percorsi sono su unità
        # Windows diverse: in quel caso sono percorsi distinti e si può procedere.
        sorgente_norm = os.path.normcase(os.path.realpath(sorgente))
        destinazione_norm = os.path.normcase(os.path.realpath(destinazione))
        try:
            comune = os.path.commonpath([sorgente_norm, destinazione_norm])
        except ValueError:
            comune = None  # Unità/volumi differenti: non sono annidati.
        if comune is not None and comune in (sorgente_norm, destinazione_norm):
            messagebox.showerror(
                self._t("Percorsi non validi", "Invalid paths"),
                self._t("La sorgente e la destinazione non possono essere la stessa cartella o contenute una nell'altra.",
                        "Source and destination cannot be the same folder or contained in one another.")
            )
            return

        conferma = self._t(
            "Copiare dalla cartella di sinistra a quella di destra i file mancanti o diversi?\n\n"
            f"SORGENTE:\n{sorgente}\n\nDESTINAZIONE:\n{destinazione}\n\n"
            "I file con dimensione diversa verranno sovrascritti. Per i file con la stessa dimensione ma data diversa verrà chiesto una sola volta se sovrascriverli tutti o saltarli tutti.\n"
            "Gli elementi presenti solo a destra NON verranno eliminati.",
            "Copy missing or different files from left to right?\n\n"
            f"SOURCE:\n{sorgente}\n\nDESTINATION:\n{destinazione}\n\n"
            "Files with a different size will be overwritten. For files with the same size but a different date, you will be asked once whether to overwrite all of them or skip all of them.\n"
            "Items present only on the right will NOT be deleted."
        )
        if not messagebox.askyesno(self._t("Conferma copia completa", "Confirm full copy"), conferma):
            return
        self._chiedi_verifica_hash_copia()
        # La scelta per i file di uguale dimensione e data diversa vale per questa
        # intera operazione di copia; verrà richiesta di nuovo alla prossima copia.
        self._decisione_stessa_dimensione_copia = None
        self.is_scanning = True
        self.lbl_status.config(text=self._t("Copia modifiche da sinistra a destra in corso...",
                                            "Copying changes from left to right..."))
        for b in [self.btn_avvia, self.btn_refresh, self.btn_espandi]:
            b.config(state="disabled")

        # Finestra di avanzamento: mostra in tempo reale i file copiati/aggiornati.
        self._crea_finestra_avanzamento_copia(self._t("Copia da sinistra a destra", "Copy from left to right"))

        threading.Thread(
            target=self._worker_copia_tutte_modifiche,
            args=(sorgente, destinazione),
            daemon=True
        ).start()

    def sincronizza_sinistra_destra(self):
        """Avvia la preparazione del piano in background, senza bloccare Tkinter."""
        if self.is_scanning:
            messagebox.showwarning(self._t("Operazione in corso", "Operation in progress"),
                self._t("Attendi il completamento della scansione o della copia in corso.",
                        "Wait for the current scan or copy to finish."))
            return
        sorgente, destinazione = self._percorsi_copia_validi(consenti_destinazione_mancante=True)
        if not sorgente or not destinazione:
            return
        # Con l'opzione attiva, sorgente ...\1\Arma e destinazione ...\3 diventano ...\3\Arma
        # (cartella creata se manca). Se la destinazione ha già lo stesso nome non cambia nulla.
        self._sync_destinazione_scelta = None
        nome_sorgente = os.path.basename(sorgente.rstrip("\\/"))
        if (self.var_sync_sottocartella.get() and nome_sorgente
                and os.path.normcase(nome_sorgente)
                != os.path.normcase(os.path.basename(destinazione.rstrip("\\/")))):
            self._sync_destinazione_scelta = destinazione
            destinazione = os.path.join(destinazione, nome_sorgente)
        src_real = os.path.normcase(os.path.realpath(sorgente))
        dst_real = os.path.normcase(os.path.realpath(destinazione))
        try:
            comune = os.path.commonpath([src_real, dst_real])
        except ValueError:
            comune = None
        if comune in (src_real, dst_real):
            messagebox.showerror(self._t("Percorsi non validi", "Invalid paths"),
                self._t("La sorgente e la destinazione non possono essere uguali o contenute una nell'altra.",
                        "Source and destination cannot be the same folder or nested inside one another."))
            return

        # Mostra subito una finestra di preparazione e lascia la scansione ricorsiva
        # (particolarmente lenta sulle condivisioni di rete) a un thread dedicato.
        self.is_scanning = True
        self.lbl_status.config(text=self._t("Preparazione piano di sincronizzazione…",
                                            "Preparing synchronization plan…"))
        finestra_attesa = tk.Toplevel(self.root)
        finestra_attesa.title(self._t("Preparazione sincronizzazione", "Preparing synchronization"))
        finestra_attesa.transient(self.root)
        finestra_attesa.resizable(False, False)
        frame_attesa = ttk.Frame(finestra_attesa, padding=18)
        frame_attesa.pack(fill="both", expand=True)
        ttk.Label(frame_attesa, text=self._t(
            "Analisi di sorgente e destinazione in corso.\nLe cartelle di rete possono richiedere tempo.",
            "Inspecting source and destination.\nNetwork folders may take some time."),
            justify="left").pack(anchor="w", pady=(0, 12))
        barra_attesa = ttk.Progressbar(frame_attesa, mode="indeterminate", length=320)
        barra_attesa.pack(fill="x")
        barra_attesa.start(12)
        annullata = threading.Event()

        def annulla(_evento=None):
            """X, Esc o «Annulla»: ferma la scansione in corso e chiude la finestra subito."""
            if annullata.is_set():
                return
            annullata.set()
            self._cancel_scan.set()
            self.lbl_status.config(text=self._t("Annullamento della preparazione in corso…",
                                                "Cancelling the preparation…"))
            try:
                barra_attesa.stop()
                finestra_attesa.destroy()
            except tk.TclError:
                pass
        ttk.Button(frame_attesa, text=self._t("Annulla", "Cancel"), command=annulla).pack(anchor="e", pady=(14, 0))
        finestra_attesa.protocol("WM_DELETE_WINDOW", annulla)
        finestra_attesa.bind("<Escape>", annulla)
        finestra_attesa.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - finestra_attesa.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - finestra_attesa.winfo_height()) // 2)
        finestra_attesa.geometry(f"+{x}+{y}")

        def prepara():
            try:
                piano, errore = self._prepara_piano_sincronizzazione(sorgente, destinazione), None
            except Exception as e:
                piano, errore = None, e
            if annullata.is_set():
                # Se l'utente ha annullato, il piano (anche se completo) viene scartato.
                self.root.after(0, self._preparazione_annullata, finestra_attesa, barra_attesa)
            else:
                self.root.after(0, self._fine_preparazione_sincronizzazione,
                               finestra_attesa, barra_attesa, sorgente, destinazione, piano, errore)
        threading.Thread(target=prepara, daemon=True).start()

    def _preparazione_annullata(self, finestra_attesa, barra_attesa):
        """Chiusura ordinata dopo un annullamento: la scansione si è fermata, nessuna modifica fatta."""
        for azione in (barra_attesa.stop, finestra_attesa.destroy):
            try:
                azione()
            except tk.TclError:
                pass
        self._cancel_scan.clear()
        self.is_scanning = False
        self.lbl_status.config(text=self._t("Preparazione della sincronizzazione annullata. Nessuna modifica eseguita.",
                                            "Synchronization preparation cancelled. No changes made."))

    def _prepara_piano_sincronizzazione(self, sorgente, destinazione):
        """Riusa il confronto in cache e ricontrolla solo gli elementi coinvolti."""
        # Se la cache manca (es. dopo aver salvato i filtri o dopo una copia) la scansione
        # viene rifatta qui, nel thread di lavoro: non serve premere prima Confronta.
        # Una cartella vuota è valida: {} non significa "cache assente".
        self._cancel_scan.clear()
        d1 = self._cerca_cache(sorgente)
        if d1 is None:
            d1 = self.analizza_directory_fast(sorgente)
        if not os.path.isdir(destinazione):
            d2 = {}  # destinazione ancora da creare: equivale a una cartella vuota (non va in cache)
        else:
            d2 = self._cerca_cache(destinazione)
            if d2 is None:
                d2 = self.analizza_directory_fast(destinazione)
        if d1 is None or d2 is None:
            raise RuntimeError("Scansione delle cartelle non completata. Riprova.")

        def valido(rel, info):
            nome = os.path.basename(rel)
            return (".@__thumb" not in nome.casefold()
                    and not self._percorso_escluso(rel)
                    and isinstance(info, dict)
                    and info.get("type") in ("file", "dir"))

        chiavi1 = {os.path.normcase(os.path.normpath(k)): (k, v)
                   for k, v in d1.items() if valido(k, v)}
        chiavi2 = {os.path.normcase(os.path.normpath(k)): (k, v)
                   for k, v in d2.items() if valido(k, v)}

        da_copiare = []
        extra = []
        extra_dirs = []
        # Le chiavi del confronto individuano i candidati; le verifiche I/O
        # sono limitate ai file che il confronto ha segnalato come differenti
        # o presenti soltanto da un lato.
        for chiave, (rel, info1) in chiavi1.items():
            info2_pair = chiavi2.get(chiave)
            src = os.path.join(sorgente, rel)
            if info1.get("type") == "dir":
                if info2_pair is None or info2_pair[1].get("type") != "dir":
                    continue
                continue
            if info1.get("type") != "file":
                continue
            tipo = None
            if info2_pair is None or info2_pair[1].get("type") != "file":
                tipo = "nuovo"
            else:
                info2 = info2_pair[1]
                try:
                    s1, t1 = os.stat(src), os.stat(os.path.join(destinazione, info2_pair[0]))
                    # Se la cache indica differenza, ricontrolla solo questo file.
                    cache_diversa = (
                        int(info1.get("size", -1)) != int(info2.get("size", -2))
                        or abs(float(info1.get("mtime", 0)) - float(info2.get("mtime", 0))) > 2
                    )
                    if cache_diversa:
                        dst_path = os.path.join(destinazione, info2_pair[0])
                        sd = os.stat(dst_path)
                        if s1.st_size != sd.st_size:
                            tipo = "aggiornamento — dimensione diversa"
                        elif abs(s1.st_mtime - sd.st_mtime) > 2:
                            if s1.st_mtime > sd.st_mtime:
                                tipo = "aggiornamento — stessa dimensione, sorgente più recente"
                            else:
                                tipo = "aggiornamento — stessa dimensione, sorgente più vecchia (sovrascrive la data più recente in destinazione)"
                except OSError:
                    tipo = "verifica necessaria"
            if tipo:
                da_copiare.append((rel, tipo))

        for chiave, (rel, info2) in chiavi2.items():
            if chiave not in chiavi1 and info2.get("type") == "file":
                dst = os.path.join(destinazione, rel)
                # Ricontrollo mirato: se il file non esiste più, non inserirlo nel piano.
                if os.path.isfile(dst):
                    extra.append(dst)
            elif chiave not in chiavi1 and info2.get("type") == "dir":
                extra_dirs.append(rel)

        # Verifica finale dei file candidati all'eliminazione: mantieni soltanto
        # quelli che esistono ancora. Nessuna scansione ricorsiva della rete.
        verificati = []
        for p in extra:
            if self._cancel_scan.is_set():
                raise RuntimeError("Operazione annullata.")
            if os.path.isfile(p):
                verificati.append(p)
        extra = verificati
        extra_dirs = sorted(extra_dirs, key=lambda x: (x.count(os.sep), x), reverse=True)
        spostamenti = self._trova_spostamenti(destinazione, chiavi1, chiavi2, da_copiare, extra)
        rinomine = self._trova_rinomine_maiuscole(chiavi1, chiavi2)
        if spostamenti:
            nuovi_spostati = {rel for rel, _vecchio in spostamenti}
            vecchi_spostati = {vecchio for _rel, vecchio in spostamenti}
            da_copiare = [(rel, tipo) for rel, tipo in da_copiare
                          if not (tipo == "nuovo" and rel in nuovi_spostati)]
            extra = [p for p in extra if p not in vecchi_spostati]
        return {"extra": extra, "da_copiare": da_copiare, "extra_dirs": extra_dirs,
                "spostamenti": spostamenti, "rinomine_maiuscole": rinomine}

    @staticmethod
    def _trova_rinomine_maiuscole(chiavi1, chiavi2):
        """Elementi presenti da entrambi i lati il cui nome differisce solo per maiuscole/minuscole.

        Su Windows «Atpc» e «ATPC» sono lo stesso nome, quindi il confronto li considera uguali e
        non fa nulla: qui si prepara la rinomina in destinazione perché ricalchi la sorgente.
        Restituisce [(percorso relativo in destinazione, nuovo nome, è_cartella)]: prima i file,
        poi le cartelle dalle più profonde."""
        file_, cartelle = [], []
        for chiave, (rel1, info1) in chiavi1.items():
            coppia = chiavi2.get(chiave)
            if coppia is None:
                continue
            rel2, info2 = coppia
            tipo = info1.get("type")
            if tipo != info2.get("type") or tipo not in ("file", "dir"):
                continue
            nuovo_nome, nome_attuale = os.path.basename(rel1), os.path.basename(rel2)
            if nuovo_nome != nome_attuale:
                (cartelle if tipo == "dir" else file_).append((rel2, nuovo_nome, tipo == "dir"))
        cartelle.sort(key=lambda voce: (voce[0].count(os.sep), voce[0]), reverse=True)
        return sorted(file_) + cartelle

    def _applica_rinomine_maiuscole(self, destinazione, rinomine, risultato):
        """Esegue le rinomine di sole maiuscole in destinazione; gli errori diventano avvisi."""
        eseguite = 0
        for rel, nuovo_nome, _cartella in rinomine:
            percorso = os.path.join(destinazione, rel)
            try:
                if not os.path.lexists(percorso):
                    continue
                genitore = os.path.dirname(percorso)
                if nuovo_nome in os.listdir(genitore):
                    continue  # già con le maiuscole giuste
                self._rinomina_solo_maiuscole(percorso, os.path.join(genitore, nuovo_nome))
                eseguite += 1
            except OSError as errore:
                risultato["avvisi"].append((rel, self._t("Nome non allineato", "Name not aligned")
                                            + f" ({self._motivo_errore(errore)})"))
        return eseguite

    def _trova_spostamenti(self, destinazione, chiavi1, chiavi2, da_copiare, extra):
        """Abbina file «nuovi» della sorgente a file «extra» della destinazione che sono
        in realtà gli stessi file spostati o rinominati: stessa dimensione (>0) e stessa data
        (±2 s). Gli abbinamenti ambigui (più candidati da un lato) vengono scartati.
        Restituisce [(percorso relativo nuovo, percorso assoluto vecchio in destinazione)]."""
        info_sorgente = {rel: info for rel, info in chiavi1.values()}
        info_dest = {os.path.join(destinazione, rel): info for rel, info in chiavi2.values()}
        nuovi, vecchi = {}, {}
        for rel, tipo in da_copiare:
            info = info_sorgente.get(rel)
            if tipo == "nuovo" and info:
                try:
                    dimensione, data = int(info.get("size", 0)), float(info.get("mtime", 0))
                except (TypeError, ValueError):
                    continue
                if dimensione > 0:
                    nuovi.setdefault(dimensione, []).append((rel, data))
        for percorso in extra:
            info = info_dest.get(percorso)
            if info:
                try:
                    dimensione, data = int(info.get("size", 0)), float(info.get("mtime", 0))
                except (TypeError, ValueError):
                    continue
                if dimensione > 0:
                    vecchi.setdefault(dimensione, []).append((percorso, data))
        trovati = []
        for dimensione, elenco_nuovi in nuovi.items():
            elenco_vecchi = vecchi.get(dimensione)
            if not elenco_vecchi:
                continue
            for rel, data in elenco_nuovi:
                candidati = [(p, d) for p, d in elenco_vecchi if abs(d - data) <= 2]
                if len(candidati) != 1:
                    continue  # nessun abbinamento, oppure ambiguo
                percorso, data_vecchio = candidati[0]
                concorrenti = [r for r, d in elenco_nuovi if abs(d - data_vecchio) <= 2]
                if len(concorrenti) == 1:
                    trovati.append((rel, percorso))
        return trovati

    @staticmethod
    def _firma_rapida(percorso, dimensione):
        """SHA-256 di tre blocchi da 64 KB (inizio, centro, fine): conferma che due file
        abbinati per dimensione e data hanno davvero lo stesso contenuto, senza leggerli tutti."""
        digest = hashlib.sha256()
        blocco = 64 * 1024
        with open(percorso, "rb") as f:
            digest.update(f.read(blocco))
            if dimensione > 2 * blocco:
                f.seek(max(0, dimensione // 2 - blocco // 2))
                digest.update(f.read(blocco))
                f.seek(-blocco, 2)
                digest.update(f.read(blocco))
        return digest.hexdigest()

    def _sposta_in_destinazione(self, sorgente, relativo, vecchio, nuovo):
        """Sposta/rinomina `vecchio` in `nuovo` (entrambi in destinazione) se il contenuto
        coincide con il file sorgente. True se eseguito; False => si userà la copia normale."""
        src = os.path.join(sorgente, relativo)
        try:
            if (os.path.islink(src) or os.path.islink(vecchio) or not os.path.isfile(src)
                    or not os.path.isfile(vecchio) or os.path.lexists(nuovo)):
                return False
            dimensione = os.path.getsize(src)
            if dimensione != os.path.getsize(vecchio):
                return False
            if self._firma_rapida(src, dimensione) != self._firma_rapida(vecchio, dimensione):
                return False
            cartella = os.path.dirname(nuovo)
            if cartella:
                os.makedirs(cartella, exist_ok=True)
            os.rename(vecchio, nuovo)   # non sovrascrive: se esiste già solleva un errore
            return True
        except OSError:
            return False

    def _fine_preparazione_sincronizzazione(self, finestra_attesa, barra_attesa,
                                            sorgente, destinazione, piano, errore):
        try:
            barra_attesa.stop()
            finestra_attesa.destroy()
        except tk.TclError:
            pass
        if errore is not None:
            self.is_scanning = False
            self.lbl_status.config(text=self._t("Preparazione sincronizzazione non riuscita",
                                                "Synchronization preparation failed"))
            messagebox.showerror(self._t("Errore scansione", "Scan error"), self._t(
                f"Impossibile verificare tutte le cartelle; nessuna modifica eseguita.\n{errore}",
                f"Could not inspect all folders; no changes made.\n{errore}"))
            return
        extra = piano["extra"]
        da_copiare = piano["da_copiare"]
        extra_dirs = piano["extra_dirs"]
        def descrizione_operazione(tipo):
            # Spiegazioni esplicite: la sincronizzazione è sempre 1 → 2,
            # quindi anche una sorgente più vecchia sostituisce il file in destinazione.
            traduzioni = {
                "nuovo": ("Nuovo file: copia da 1 a 2", "New file: copy from 1 to 2"),
                "aggiornamento": ("Aggiornamento: copia da 1 a 2", "Update: copy from 1 to 2"),
                "aggiornamento — dimensione diversa": ("Dimensione diversa: sovrascrive la destinazione con il file sorgente", "Different size: overwrite destination with source file"),
                "aggiornamento — stessa dimensione, sorgente più recente": ("Stessa dimensione, sorgente più recente: sovrascrive la destinazione", "Same size, source is newer: overwrite destination"),
                "aggiornamento — stessa dimensione, sorgente più vecchia (sovrascrive la data più recente in destinazione)": ("ATTENZIONE: stessa dimensione, sorgente più vecchia; la sincronizzazione sovrascriverà il file più recente in destinazione", "WARNING: same size, source is older; synchronization will overwrite the newer destination file"),
                "verifica necessaria": ("Verifica necessaria: controllare manualmente prima di copiare", "Verification needed: check manually before copying"),
            }
            coppia = traduzioni.get(tipo)
            if coppia:
                return self._t(coppia[0], coppia[1])
            return tipo

        def lista_preview(voci, limite=20):
            righe = [f"• {nome} — {descrizione_operazione(tipo)}" for nome, tipo in voci[:limite]]
            if len(voci) > limite:
                righe.append(self._t(f"… e altri {len(voci)-limite}", f"… and {len(voci)-limite} more"))
            return "\n".join(righe) if righe else self._t("(nessun elemento)", "(none)")
        spostamenti = piano.get("spostamenti", [])
        rinomine = piano.get("rinomine_maiuscole", [])
        copie_preview = lista_preview(sorted(da_copiare))
        eliminazioni_preview = lista_preview([(os.path.relpath(x, destinazione), "elimina file") for x in extra])
        directory_preview = lista_preview([(x, "directory extra; rimossa solo se vuota") for x in extra_dirs])
        testo = self._t(
            f"PIANO DI SINCRONIZZAZIONE 1 → 2\n\nSORGENTE (protetta):\n{sorgente}\n\nDESTINAZIONE (modificata):\n{destinazione}\n\nCOPIE / AGGIORNAMENTI PREVISTI: {len(da_copiare)}\n{copie_preview}\n\nELIMINAZIONI PREVISTE — FILE: {len(extra)}\n{eliminazioni_preview}\n\nDIRECTORY EXTRA: {len(extra_dirs)}\n{directory_preview}\n\nLe directory saranno rimosse soltanto se vuote; nessuna eliminazione verrà eseguita se la copia fallisce. Controlla il piano prima di confermare.",
            f"SYNC PLAN 1 → 2\n\nSOURCE (protected):\n{sorgente}\n\nDESTINATION (will be changed):\n{destinazione}\n\nCOPIES / UPDATES PLANNED: {len(da_copiare)}\n{copie_preview}\n\nPLANNED DELETIONS — FILES: {len(extra)}\n{eliminazioni_preview}\n\nEXTRA DIRECTORIES: {len(extra_dirs)}\n{directory_preview}\n\nDirectories are removed only if empty; no deletions are performed if copying fails. Review the plan before confirming.")
        if spostamenti:
            righe_sp = [f"• {os.path.relpath(vecchio, destinazione)}  →  {nuovo_rel}"
                        for nuovo_rel, vecchio in spostamenti[:20]]
            if len(spostamenti) > 20:
                righe_sp.append(self._t(f"… e altri {len(spostamenti) - 20}", f"… and {len(spostamenti) - 20} more"))
            marcatore = self._t("COPIE / AGGIORNAMENTI PREVISTI", "COPIES / UPDATES PLANNED")
            sezione = self._t(
                f"FILE SPOSTATI O RINOMINATI: {len(spostamenti)} (verranno spostati in destinazione, senza copiarli di nuovo)\n",
                f"MOVED OR RENAMED FILES: {len(spostamenti)} (they will be moved inside the destination, not copied again)\n"
            ) + "\n".join(righe_sp) + "\n\n"
            testo = testo.replace(marcatore, sezione + marcatore, 1)
        if rinomine:
            righe_rn = [f"• {os.path.basename(rel)}  →  {nuovo}" for rel, nuovo, _c in rinomine[:20]]
            if len(rinomine) > 20:
                righe_rn.append(self._t(f"… e altri {len(rinomine) - 20}", f"… and {len(rinomine) - 20} more"))
            marcatore = self._t("COPIE / AGGIORNAMENTI PREVISTI", "COPIES / UPDATES PLANNED")
            sezione = self._t(
                f"NOMI DA ALLINEARE (solo maiuscole/minuscole): {len(rinomine)} (verranno rinominati in destinazione come nella sorgente)\n",
                f"NAMES TO ALIGN (letter case only): {len(rinomine)} (they will be renamed in the destination to match the source)\n"
            ) + "\n".join(righe_rn) + "\n\n"
            testo = testo.replace(marcatore, sezione + marcatore, 1)
        scelta = getattr(self, "_sync_destinazione_scelta", None)
        if scelta:
            nome_sotto = os.path.basename(destinazione)
            testo = self._t(
                f"Sincronizzazione nella cartella «{nome_sotto}» dentro la destinazione scelta:\n{scelta}\n"
                f"(Opzione disattivabile da Impostazioni.)\n\n",
                f"Synchronizing into the «{nome_sotto}» folder inside the chosen destination:\n{scelta}\n"
                f"(You can turn this off in Settings.)\n\n") + testo
        destinazione_mancante = not os.path.isdir(destinazione)
        if destinazione_mancante:
            testo = self._t(
                f"LA CARTELLA DI DESTINAZIONE NON ESISTE: VERRÀ CREATA\n{destinazione}\n\n",
                f"THE DESTINATION FOLDER DOES NOT EXIST: IT WILL BE CREATED\n{destinazione}\n\n") + testo
        finestra = tk.Toplevel(self.root)
        finestra.title(self._t("Conferma sincronizzazione", "Confirm synchronization"))
        finestra.transient(self.root)
        finestra.resizable(True, True)
        finestra.geometry("1100x780")
        finestra.minsize(850, 600)
        finestra.grab_set()
        contenitore = ttk.Frame(finestra, padding=14)
        contenitore.pack(fill="both", expand=True)
        ttk.Label(contenitore, text=self._t("ATTENZIONE — operazione con eliminazioni",
            "WARNING — operation includes deletions"), font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(0, 8))
        testo_box = tk.Text(contenitore, wrap="word", height=28, width=110, font=("TkDefaultFont", 10))
        barra_testo = ttk.Scrollbar(contenitore, orient="vertical", command=testo_box.yview)
        testo_box.configure(yscrollcommand=barra_testo.set)
        barra_testo.pack(side="right", fill="y")
        testo_box.pack(side="left", fill="both", expand=True)
        testo_box.insert("1.0", testo)
        testo_box.tag_configure("avviso_nuova_destinazione", foreground="#e87500", font=("TkDefaultFont", 10, "bold"))
        if destinazione_mancante:
            testo_box.tag_add("avviso_nuova_destinazione", "1.0", "2.end")
        # Evidenzia in arancione gli avvisi in cui la sorgente è più vecchia:
        # la sincronizzazione sovrascriverà un file più recente in destinazione.
        testo_box.tag_configure("avviso_sorgente_piu_vecchia", foreground="#e87500", font=("TkDefaultFont", 10, "bold"))
        for avviso in (
            "ATTENZIONE: stessa dimensione, sorgente più vecchia; la sincronizzazione sovrascriverà il file più recente in destinazione",
            "WARNING: same size, source is older; synchronization will overwrite the newer destination file",
        ):
            inizio = "1.0"
            while True:
                posizione = testo_box.search(avviso, inizio, stopindex="end")
                if not posizione:
                    break
                fine = f"{posizione}+{len(avviso)}c"
                testo_box.tag_add("avviso_sorgente_piu_vecchia", posizione, fine)
                inizio = fine
        testo_box.configure(state="disabled")
        presa_visione = tk.BooleanVar(value=False)
        ttk.Checkbutton(finestra, text=self._t("Ho compreso i rischi e confermo la sincronizzazione.",
            "I understand the risks and confirm synchronization."), variable=presa_visione).pack(anchor="w", padx=18, pady=(10, 4))
        esito_conferma = {"conferma": False}
        pulsanti = ttk.Frame(finestra, padding=(14, 8, 14, 14))
        pulsanti.pack(fill="x")
        ttk.Button(pulsanti, text=self._t("Annulla", "Cancel"), command=finestra.destroy).pack(side="right", padx=(6, 0))
        btn_ok = ttk.Button(pulsanti, text=self._t("OK — Sincronizza", "OK — Synchronize"), state="disabled")
        btn_ok.pack(side="right")
        def aggiorna_conferma(*_):
            btn_ok.configure(state="normal" if presa_visione.get() else "disabled")
        def conferma_e_chiudi():
            if presa_visione.get():
                esito_conferma["conferma"] = True
                finestra.destroy()
        presa_visione.trace_add("write", aggiorna_conferma)
        btn_ok.configure(command=conferma_e_chiudi)
        finestra.protocol("WM_DELETE_WINDOW", finestra.destroy)
        finestra.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - finestra.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - finestra.winfo_height()) // 2)
        finestra.geometry(f"+{x}+{y}")
        self.root.wait_window(finestra)
        if not esito_conferma["conferma"]:
            self.is_scanning = False
            self.lbl_status.config(text=self._t("Sincronizzazione annullata", "Synchronization cancelled"))
            return
        self._destinazione_creata_ora = None
        if destinazione_mancante:
            try:
                os.makedirs(destinazione, exist_ok=True)
            except OSError as errore:
                self.is_scanning = False
                self.lbl_status.config(text=self._t("Sincronizzazione annullata", "Synchronization cancelled"))
                messagebox.showerror(self._t("Cartella di destinazione", "Destination folder"), self._t(
                    f"Impossibile creare la cartella di destinazione; nessuna modifica eseguita.\n{destinazione}\n\n{errore}",
                    f"Could not create the destination folder; no changes made.\n{destinazione}\n\n{errore}"))
                return
            self._destinazione_creata_ora = destinazione
        self._chiedi_verifica_hash_copia()
        self._decisione_stessa_dimensione_copia = None
        self.lbl_status.config(text=self._t("Sincronizzazione 1 → 2 in corso…", "Synchronizing 1 → 2…"))
        for b in [self.btn_avvia, self.btn_refresh, self.btn_espandi, self.btn_copia_tutto, self.btn_sincronizza]:
            b.config(state="disabled")
        self._crea_finestra_avanzamento_copia(self._t("Sincronizza 1 → 2", "Synchronize 1 → 2"))
        threading.Thread(target=self._worker_sincronizza_sinistra_destra,
                         args=(sorgente, destinazione, extra, da_copiare, spostamenti, rinomine), daemon=True).start()

    def _worker_sincronizza_sinistra_destra(self, sorgente, destinazione, extra, da_copiare, spostamenti=(), rinomine=()):
        risultato = self._nuovo_risultato()
        errore_generale = None
        eliminati = 0
        spostati = 0
        rinominati = 0
        try:
            # 1) File spostati/rinominati: si rinominano in destinazione dopo aver confermato
            #    il contenuto. Se qualcosa non torna, tornano alla copia normale + eliminazione.
            if spostamenti:
                self.root.after(0, self._aggiorna_preparazione_copia,
                                self._t("Spostamento dei file rinominati…", "Moving renamed files…"))
                da_copiare = list(da_copiare)
                extra = list(extra)
                for indice_sp, (relativo, vecchio) in enumerate(spostamenti):
                    if self._copia_interrotta.is_set():
                        self._aggiungi_interrotti(risultato, [r for r, _v in spostamenti[indice_sp:]])
                        break
                    if self._sposta_in_destinazione(sorgente, relativo, vecchio,
                                                    os.path.join(destinazione, relativo)):
                        spostati += 1
                    else:
                        da_copiare.append((relativo, "nuovo"))
                        extra.append(vecchio)
            # Non ripetere la scansione ricorsiva completa della rete: la fase di
            # preparazione ha già letto la cache e ricontrollato i candidati.
            # Qui si ricontrollano solo i file da copiare, per intercettare modifiche
            # avvenute mentre l'utente leggeva la conferma.
            self.root.after(0, self._aggiorna_preparazione_copia,
                            self._t("Verifica finale dei file da copiare…", "Final check of files to copy…"))
            elementi = []
            totale = 0
            for indice, (relativo, tipo) in enumerate(da_copiare, 1):
                src_file = os.path.join(sorgente, relativo)
                dst_file = os.path.join(destinazione, relativo)
                try:
                    st_src = os.stat(src_file, follow_symlinks=False)
                    if os.path.islink(src_file) or not os.path.isfile(src_file):
                        continue
                    if os.path.isfile(dst_file):
                        st_dst = os.stat(dst_file, follow_symlinks=False)
                        if (st_src.st_size == st_dst.st_size
                                and abs(st_src.st_mtime - st_dst.st_mtime) <= 2):
                            continue
                        stato = (STATO_DIVERSO if st_src.st_size != st_dst.st_size
                                 else STATO_DATA_DIVERSA)
                    else:
                        stato = STATO_MANCANTE
                    elementi.append((relativo, st_src.st_size, stato))
                    totale += st_src.st_size
                except OSError:
                    elementi.append((relativo, 0, STATO_ERRORE_LETTURA))
                if indice == 1 or indice % 25 == 0 or indice == len(da_copiare):
                    self.root.after(0, self._aggiorna_preparazione_copia,
                        self._t(f"Verifica finale… {indice}/{len(da_copiare)} file", f"Final check… {indice}/{len(da_copiare)} files"))
            analisi = {"elementi": elementi, "totale": totale, "saltati": 0, "cartelle_mancanti": []}
            self._copia_file_totali = len(analisi["elementi"])
            self._copia_file_elaborati = 0
            self.root.after(0, self._aggiorna_contatore_file_copia, 0, self._copia_file_totali, "")
            self._reimposta_byte_copia(analisi["totale"], sorgente)
            self._copia_da_analisi(sorgente, destinazione, analisi, risultato)
            if self._copia_interrotta.is_set():
                risultato["interrotta"] = True
            if rinomine and not risultato.get("interrotta"):
                rinominati = self._applica_rinomine_maiuscole(destinazione, rinomine, risultato)
            if risultato.get("interrotta"):
                errore_generale = self._t("sincronizzazione interrotta dall'utente; per sicurezza non è stato eliminato nulla.",
                                          "synchronization stopped by the user; for safety nothing was deleted.")
            elif risultato["non_copiati"]:
                errore_generale = "Alcuni file non sono stati copiati; per sicurezza non è stato eliminato nulla."
            else:
                for percorso in extra:
                    try:
                        if os.path.isfile(percorso) or os.path.islink(percorso):
                            os.remove(percorso)
                            eliminati += 1
                    except OSError as e:
                        self._registra_errore_copia(percorso, e, ignorato=False)
                        risultato["non_copiati"].append((percorso, self._motivo_errore(e)))
                # Elimina le directory extra rimaste vuote, dal basso verso l'alto.
                # Le directory che esistono anche nella sorgente vengono conservate.
                if not risultato["non_copiati"]:
                    dst_real = os.path.normcase(os.path.realpath(destinazione))
                    def percorso_relativo_norm(percorso, radice):
                        rel = os.path.relpath(percorso, radice)
                        return os.path.normcase(os.path.normpath(rel))
                    directory_sorgente = set()
                    for radice, cartelle, _ in os.walk(sorgente):
                        rel_dir = os.path.relpath(radice, sorgente)
                        cartelle[:] = [d for d in cartelle
                            if ".@__thumb" not in d.casefold()
                            and not self._percorso_escluso(d if rel_dir == "." else os.path.join(rel_dir, d))
                            and not os.path.islink(os.path.join(radice, d))]
                        for d in cartelle:
                            directory_sorgente.add(percorso_relativo_norm(os.path.join(radice, d), sorgente))
                    for radice, cartelle, _ in os.walk(destinazione, topdown=False):
                        if os.path.normcase(os.path.realpath(radice)) == dst_real:
                            continue  # Non rimuovere mai la radice di destinazione.
                        rel = percorso_relativo_norm(radice, destinazione)
                        rel_dir = os.path.dirname(rel)
                        nome = os.path.basename(radice)
                        rel_parent = os.path.relpath(os.path.dirname(radice), destinazione)
                        if (".@__thumb" in nome.casefold()
                                or self._percorso_escluso(rel)
                                or rel in directory_sorgente):
                            continue
                        try:
                            contenuto = os.listdir(radice)
                            # Windows può creare desktop.ini anche nelle cartelle
                            # ormai extra. Se è l'unico elemento rimasto, rimuovilo
                            # per consentire la pulizia della cartella (che non esiste
                            # nella sorgente e non è esclusa dai filtri).
                            if (len(contenuto) == 1
                                    and contenuto[0].casefold() == "desktop.ini"):
                                desktop_ini = os.path.join(radice, contenuto[0])
                                if os.path.isfile(desktop_ini) and not os.path.islink(desktop_ini):
                                    os.remove(desktop_ini)
                                    eliminati += 1
                                contenuto = os.listdir(radice)
                            if not contenuto:
                                os.rmdir(radice)
                        except OSError as e:
                            # Directory non vuote, protette o non eliminabili: lasciare intatto.
                            pass
        except Exception as e:
            errore_generale = str(e)
            self._registra_errore_copia(sorgente, e, ignorato=False)
            risultato["non_copiati"].append((sorgente, self._motivo_errore(e)))
        finally:
            self.folder_cache.pop(sorgente, None)
            self.folder_cache.pop(destinazione, None)
        def completato():
            self.is_scanning = False
            for b in [self.btn_avvia, self.btn_refresh, self.btn_espandi, self.btn_copia_tutto, self.btn_sincronizza]:
                b.config(state="normal")
            self._chiudi_finestra_copia()
            sp_it = f", {spostati} spostati" if spostati else ""
            sp_en = f", {spostati} moved" if spostati else ""
            testo_interruzione = self._t(
                f"Sincronizzazione INTERROTTA: {len(risultato['copiati'])} copiati{sp_it}, {len(risultato['non_copiati'])} non copiati, nessun file eliminato",
                f"Synchronization STOPPED: {len(risultato['copiati'])} copied{sp_en}, {len(risultato['non_copiati'])} not copied, nothing deleted")
            if risultato.get("interrotta"):
                self.lbl_status.avviso(testo_interruzione)
            else:
                self.lbl_status.config(text=self._t(f"Sincronizzazione terminata: {len(risultato['copiati'])} copiati{sp_it}, {eliminati} eliminati",
                                                    f"Synchronization finished: {len(risultato['copiati'])} copied{sp_en}, {eliminati} deleted"))
            try:
                if (os.path.normcase(os.path.normpath(self.safe_combobox_get(self.combo_c2)))
                        != os.path.normcase(os.path.normpath(destinazione))):
                    self.combo_c2.set(destinazione)  # così Confronta mostra le cartelle appena sincronizzate
            except (tk.TclError, AttributeError):
                pass
            self.avvia_confronto()
            if risultato.get("interrotta"):
                # Il confronto di aggiornamento lascia comunque il suo risultato negli alberi, ma
                # alla sua fine la riga di stato mostra l'interruzione (in rosso), non «completato».
                if self.is_scanning:
                    self._avviso_dopo_confronto = testo_interruzione
                else:
                    self.lbl_status.avviso(testo_interruzione)
            nota = self._t(f"File eliminati dalla destinazione: {eliminati}.", f"Files deleted from destination: {eliminati}.")
            if rinominati:
                nota = self._t(f"Nomi allineati alla sorgente (maiuscole/minuscole): {rinominati}.\n",
                               f"Names aligned with the source (letter case): {rinominati}.\n") + nota
            if spostati:
                nota = self._t(f"File spostati/rinominati in destinazione (senza ricopiarli): {spostati}.\n",
                               f"Files moved/renamed in the destination (not copied again): {spostati}.\n") + nota
            creata = getattr(self, "_destinazione_creata_ora", None)
            if creata:
                nota = self._t(f"Cartella di destinazione creata: {creata}.", f"Destination folder created: {creata}.") + "\n" + nota
                self._destinazione_creata_ora = None
            if errore_generale:
                nota += "\n" + self._t("Eliminazioni non eseguite o sincronizzazione incompleta: ", "Deletions skipped or synchronization incomplete: ") + errore_generale
            self._mostra_riepilogo_copia(risultato, self._t("Riepilogo sincronizzazione", "Synchronization summary"), nota, destinazione)
        self.root.after(0, completato)

    def _chiedi_chiusura_finestra_copia(self):
        """X sulla finestra di avanzamento: interrompere l'operazione, lasciarla continuare
        con la finestra nascosta, oppure tornare alla finestra."""
        if self._copia_interrotta.is_set():
            return  # interruzione già richiesta: si attende la fine del file in corso
        scelta = {"valore": None}
        dialogo = tk.Toplevel(self.finestra_copia)
        dialogo.title(self._t("Operazione in corso", "Operation in progress"))
        dialogo.transient(self.finestra_copia)
        dialogo.resizable(False, False)
        tk.Label(dialogo, justify="left", padx=22, pady=16, font=("Segoe UI", 10), text=self._t(
            "L'operazione è ancora in corso.\n\nVuoi interromperla oppure lasciarla continuare con la finestra chiusa?\n"
            "(Se la interrompi, nessun file già copiato viene annullato e in una sincronizzazione non viene eliminato nulla.)",
            "The operation is still running.\n\nDo you want to stop it, or let it keep running with the window closed?\n"
            "(If you stop it, files already copied are kept and a synchronization deletes nothing.)")).pack()
        riga = tk.Frame(dialogo)
        riga.pack(pady=(0, 14))

        def scegli(valore):
            scelta["valore"] = valore
            dialogo.destroy()
        for testo, valore in ((self._t("Interrompi l'operazione", "Stop the operation"), "interrompi"),
                              (self._t("Chiudi la finestra e continua", "Close window and keep running"), "continua"),
                              (self._t("Torna alla finestra", "Back to the window"), None)):
            tk.Button(riga, text=testo, command=lambda v=valore: scegli(v), padx=12, pady=5).pack(side="left", padx=5)
        dialogo.protocol("WM_DELETE_WINDOW", lambda: scegli(None))
        dialogo.bind("<Escape>", lambda _e: scegli(None))
        try:
            dialogo.update_idletasks()
            x = self.finestra_copia.winfo_rootx() + max(0, (self.finestra_copia.winfo_width() - dialogo.winfo_width()) // 2)
            y = self.finestra_copia.winfo_rooty() + max(0, (self.finestra_copia.winfo_height() - dialogo.winfo_height()) // 2)
            dialogo.geometry(f"+{x}+{y}")
            dialogo.grab_set()
        except tk.TclError:
            pass
        self.root.wait_window(dialogo)
        if scelta["valore"] == "interrompi":
            self._interrompi_copia()
        elif scelta["valore"] == "continua":
            self._nascondi_finestra_copia()

    def _interrompi_copia(self):
        self._copia_interrotta.set()
        try:
            self.lbl_file_copia.config(text=self._t(
                "Interruzione in corso… (si ferma al termine del file in elaborazione)",
                "Stopping… (it will stop when the current file is done)"))
        except (tk.TclError, AttributeError):
            pass
        self.lbl_status.config(text=self._t("Interruzione dell'operazione in corso…", "Stopping the operation…"))

    def _nascondi_finestra_copia(self):
        """La finestra sparisce ma l'operazione continua: avanzamento nella barra principale;
        il pulsante Stop permette comunque di interromperla."""
        try:
            self.finestra_copia.withdraw()
        except (tk.TclError, AttributeError):
            return
        self._copia_nascosta = True
        self.lbl_status.config(text=self._t("Operazione in corso in background… (Stop per interromperla)",
                                            "Operation running in the background… (Stop to cancel it)"))
        self.btn_stop.config(state="normal")

    def _chiudi_finestra_copia(self):
        """Chiude la finestra di progresso al termine della copia."""
        if self._copia_nascosta:
            try:
                self.btn_stop.config(state="disabled")   # era stato riattivato per la copia in background
            except (tk.TclError, AttributeError):
                pass
        self._copia_nascosta = False
        self._copia_interrotta.clear()
        try:
            if self.finestra_copia.winfo_exists():
                self.finestra_copia.destroy()
        except (tk.TclError, AttributeError):
            pass
        # Distruggendo un Toplevel che aveva il focus, Tk resta senza widget
        # focalizzato e su Windows la rotellina (<MouseWheel>) non arriva più.
        self._ripristina_focus_principale()

    def _ripristina_focus_principale(self, *_):
        """Riporta il focus di tastiera/rotellina sull'albero attivo (o sulla finestra principale)."""
        def _ripristina():
            try:
                if self.root.focus_get() is not None:
                    return
                self.root.focus_force()
                tree = getattr(self, "albero_attivo", None)
                if tree not in (self.tree1, self.tree2):
                    tree = self.tree1
                tree.focus_set()
            except (tk.TclError, AttributeError, KeyError):
                pass
        try:
            self.root.after_idle(_ripristina)
            self.root.after(150, _ripristina)
        except (tk.TclError, AttributeError):
            pass

    def _aggiorna_avanzamento_copia(self, percorso, completato=False, errore=None):
        """Aggiorna la finestra di avanzamento nel thread principale di Tkinter."""
        try:
            if not self.finestra_copia.winfo_exists():
                return
            if errore:
                self.lbl_file_copia.config(text=self._t("Errore", "Error") + f": {errore}")
            elif completato:
                self.lbl_file_copia.config(text=self._t("Copia completata", "Copy completed") + f": {percorso}")
            else:
                self.lbl_file_copia.config(text=self._t("Copia/aggiornamento in corso", "Copying/updating") + f":\n{percorso}")
                self.lista_file_copiati.insert("end", percorso)
                self.lista_file_copiati.see("end")
        except (tk.TclError, AttributeError):
            # L'utente potrebbe aver chiuso la finestra durante la copia.
            pass

    def _aggiorna_contatore_file_copia(self, elaborati, totale, ultimo=""):
        """Mostra un avanzamento per numero di file, indipendente dalla dimensione."""
        try:
            if not self.finestra_copia.winfo_exists():
                return
            percentuale = 100 if totale <= 0 else min(100, elaborati * 100 / totale)
            self.lbl_file_copia.config(
                text=self._t("File elaborati", "Files processed") + f": {elaborati} / {totale} ({percentuale:.1f}%)"
                     + (f"\n" + self._t("Ultimo", "Last") + f": {ultimo}" if ultimo else "")
            )
        except (tk.TclError, AttributeError):
            pass

    def _aggiorna_avanzamento_copia_batch(self, percorsi, totale):
        """Aggiorna la lista in blocco per ridurre il lavoro della GUI durante copie grandi."""
        try:
            if not self.finestra_copia.winfo_exists():
                return
            if percorsi:
                self.lbl_file_copia.config(
                    text=self._t("File copiati/aggiornati", "Files copied/updated") + f": {totale}\n"
                         + self._t("Ultimo", "Last") + f": {percorsi[-1]}"
                )
                self.lista_file_copiati.insert("end", *percorsi)
                self.lista_file_copiati.see("end")
        except (tk.TclError, AttributeError):
            pass

    def _worker_copia_tutte_modifiche(self, sorgente, destinazione):
        risultato = self._nuovo_risultato()
        errore_generale = None
        try:
            # Stessa regola dell'Anteprima: mancanti o con dimensione diversa.
            self.root.after(0, self._aggiorna_preparazione_copia,
                            self._t("Analisi delle cartelle in corso...", "Scanning folders..."))
            analisi = self._scansiona_copia(
                sorgente, destinazione,
                aggiorna_progresso=lambda cartelle, file: self.root.after(
                    0, self._aggiorna_preparazione_copia,
                    self._t(f"Analisi in corso... cartelle: {cartelle}, file esaminati: {file}",
                            f"Scanning... folders: {cartelle}, files checked: {file}"))
            )
            risultato["saltati"].extend([None] * analisi["saltati"])
            self._copia_file_totali = len(analisi["elementi"])
            self._copia_file_elaborati = 0
            self.root.after(0, self._aggiorna_contatore_file_copia, 0, self._copia_file_totali, "")
            self._reimposta_byte_copia(analisi["totale"], sorgente)
            self._copia_da_analisi(sorgente, destinazione, analisi, risultato)
        except CopiaInterrotta:
            risultato["interrotta"] = True
        except Exception as e:
            # Solo errori che impediscono di proseguire (es. sorgente non leggibile).
            self._registra_errore_copia(sorgente, e, ignorato=False)
            errore_generale = str(e)
            risultato["non_copiati"].append((sorgente, self._motivo_errore(e)))
        self.folder_cache.pop(sorgente, None)
        self.folder_cache.pop(destinazione, None)

        def completato():
            self.is_scanning = False
            for b in [self.btn_avvia, self.btn_refresh, self.btn_espandi]:
                b.config(state="normal")
            copiati = len(risultato["copiati"])
            non_copiati = len(risultato["non_copiati"])
            testo_interruzione = self._t(f"Copia INTERROTTA: {copiati} copiati, {non_copiati} non copiati",
                                         f"Copy STOPPED: {copiati} copied, {non_copiati} not copied")
            if risultato.get("interrotta"):
                self.lbl_status.avviso(testo_interruzione)
            else:
                self.lbl_status.config(text=self._t(f"Copia completata: {copiati} copiati, {non_copiati} non copiati",
                                                    f"Copy finished: {copiati} copied, {non_copiati} not copied"))
            self._chiudi_finestra_copia()
            if errore_generale is None:
                self.avvia_confronto()
                if risultato.get("interrotta"):
                    if self.is_scanning:
                        self._avviso_dopo_confronto = testo_interruzione
                    else:
                        self.lbl_status.avviso(testo_interruzione)
            nota = self._t("Gli elementi presenti solo a destra sono stati mantenuti.",
                           "Items present only on the right were kept.")
            if risultato.get("interrotta"):
                nota = self._t("Copia INTERROTTA dall'utente: gli elementi non ancora copiati sono stati lasciati com'erano.\n",
                               "Copy STOPPED by the user: items not copied yet were left as they were.\n") + nota
            if errore_generale:
                nota = self._t("Copia interrotta", "Copy interrupted") + f": {errore_generale}\n" + nota
            self._mostra_riepilogo_copia(risultato, self._t("Riepilogo copia modifiche", "Copy changes summary"), nota, destinazione)
        self.root.after(0, completato)

    @staticmethod
    def _rinomina_solo_maiuscole(vecchio, nuovo):
        """Cambia solo maiuscole/minuscole passando da un nome temporaneo: funziona su qualsiasi
        file system (NTFS, FAT, condivisioni di rete) e, se il secondo passaggio fallisce,
        ripristina il nome originale."""
        temporaneo = os.path.join(os.path.dirname(vecchio), f".rinomina_{os.urandom(6).hex()}.tmp")
        os.rename(vecchio, temporaneo)
        try:
            os.rename(temporaneo, nuovo)
        except OSError:
            os.rename(temporaneo, vecchio)
            raise

    def _chiedi_nuovo_nome(self, titolo, prompt, nome_attuale, cartella=False):
        """Finestra «Rinomina»: il campo contiene già il nome attuale. Per i file è selezionata solo
        la parte prima dell'estensione, così scrivendo si cambia il nome e `.flac` resta."""
        risultato = {"valore": None}
        dialogo = tk.Toplevel(self.root)
        dialogo.title(titolo)
        dialogo.transient(self.root)
        dialogo.resizable(False, False)
        tk.Label(dialogo, text=prompt, justify="left", anchor="w", padx=16, pady=10).pack(fill="x")
        variabile = tk.StringVar(value=nome_attuale)
        campo = tk.Entry(dialogo, textvariable=variabile, width=60, font=("Segoe UI", 10))
        campo.pack(padx=16, fill="x")

        def conferma(_evento=None):
            risultato["valore"] = variabile.get()
            dialogo.destroy()

        def annulla(_evento=None):
            dialogo.destroy()
        riga = tk.Frame(dialogo)
        riga.pack(fill="x", padx=16, pady=12)
        tk.Button(riga, text=self._t("Annulla", "Cancel"), command=annulla, padx=14, pady=4).pack(side="right")
        tk.Button(riga, text="OK", command=conferma, padx=18, pady=4).pack(side="right", padx=(0, 8))
        base, estensione = os.path.splitext(nome_attuale)
        fine_selezione = len(nome_attuale) if (cartella or not estensione or not base) else len(base)
        campo.focus_set()
        campo.selection_range(0, fine_selezione)
        campo.icursor(fine_selezione)
        dialogo.bind("<Return>", conferma)
        dialogo.bind("<Escape>", annulla)
        dialogo.protocol("WM_DELETE_WINDOW", annulla)
        try:
            dialogo.update_idletasks()
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dialogo.winfo_width()) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dialogo.winfo_height()) // 3)
            dialogo.geometry(f"+{x}+{y}")
            dialogo.grab_set()
        except tk.TclError:
            pass
        self.root.wait_window(dialogo)
        return risultato["valore"]

    def azione_rinomina(self):
        if not hasattr(self, 'albero_attivo') or not self.nodo_attivo:
            return
        if len(self._nodi_selezionati()) > 1:
            messagebox.showwarning(self._t("Rinomina", "Rename"),
                                   self._t("Seleziona un solo elemento da rinominare.", "Select a single item to rename."))
            return
        vp = self.ricava_percorso_reale(self.albero_attivo, self.nodo_attivo)
        if not vp or not os.path.lexists(vp):
            return
        nn = self._chiedi_nuovo_nome(
            self._t("Rinomina", "Rename"),
            self._t(f"Nuovo nome per '{os.path.basename(vp)}':", f"New name for '{os.path.basename(vp)}':"),
            os.path.basename(vp), cartella=os.path.isdir(vp))
        if nn is None:
            return
        nn = nn.strip()
        # Il campo accetta esclusivamente un nome, non un percorso: impedisce
        # di rinominare/spostare file fuori dalla cartella selezionata.
        separatori = {os.sep, os.altsep} - {None}
        if (not nn or nn in (".", "..") or "\x00" in nn
                or any(sep in nn for sep in separatori)
                or (os.name == "nt" and (":" in nn or nn.endswith((".", " "))))):
            messagebox.showwarning("Nome non valido", "Inserisci un nome file o cartella valido, senza percorsi.")
            return
        destinazione = os.path.join(os.path.dirname(vp), nn)
        if nn == os.path.basename(vp):
            return  # nome identico: niente da fare
        # Su Windows «Atpc» e «ATPC» sono lo stesso nome: se cambiano solo le maiuscole non è
        # un conflitto con un altro elemento ma una rinomina valida.
        solo_maiuscole = (os.path.normcase(os.path.abspath(destinazione))
                          == os.path.normcase(os.path.abspath(vp)))
        if not solo_maiuscole and os.path.lexists(destinazione):
            messagebox.showwarning("Nome già esistente", "Esiste già un file o una cartella con questo nome.")
            return
        try:
            if solo_maiuscole:
                self._rinomina_solo_maiuscole(vp, destinazione)
            else:
                os.rename(vp, destinazione)
            self.folder_cache.clear()
            self.avvia_confronto()
        except Exception as e:
            messagebox.showerror("Errore rinomina", f"Errore:\n{e}")

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    @staticmethod
    def _account_corrente():
        utente = os.environ.get("USERNAME", "")
        dominio = os.environ.get("USERDOMAIN", "")
        return f"{dominio}\\{utente}" if dominio else utente

    def _comando_ripara_permessi(self, percorso):
        """Parametri per cmd.exe: rende l'utente proprietario e gli concede il
        controllo completo. /setowner e /grant non dipendono dalla lingua di Windows."""
        return f'/s /c "{self._comando_icacls(percorso)}"'

    def _parametri_ripara_permessi(self, percorsi, limite=7000):
        """più percorsi in un'unica richiesta UAC; divide in blocchi se la riga è troppo lunga."""
        blocchi, corrente = [], []
        for percorso in percorsi:
            comando = self._comando_icacls(percorso)
            if corrente and len(" & ".join(corrente + [comando])) > limite:
                blocchi.append(corrente); corrente = []
            corrente.append(comando)
        if corrente:
            blocchi.append(corrente)
        return [f'/s /c "{" & ".join(blocco)}"' for blocco in blocchi]

    def _comando_icacls(self, percorso):
        account = self._account_corrente()
        percorso = os.path.normpath(percorso)
        if os.path.isdir(percorso) and not os.path.islink(percorso):
            ricorsivo, diritti = " /T", "(OI)(CI)F"
        else:
            ricorsivo, diritti = "", "F"
        # /s (in _comando_ripara_permessi): cmd toglie solo le virgolette esterne.
        return (f'icacls "{percorso}" /setowner "{account}"{ricorsivo} /C /Q & '
                f'icacls "{percorso}" /grant "{account}:{diritti}"{ricorsivo} /C /Q')

    def _ripara_permessi_admin(self, percorsi):
        """Esegue la riparazione con privilegi di amministratore (richiesta UAC).

        Accetta un percorso o un elenco. Blocca fino al termine.
        Restituisce (ok, messaggio).
        """
        if isinstance(percorsi, str):
            percorsi = [percorsi]
        if not IS_WINDOWS:
            return False, self._t("Disponibile solo su Windows", "Windows only")
        etichetta = percorsi[0] + (f" (+{len(percorsi) - 1})" if len(percorsi) > 1 else "")
        codici = []
        for parametri in self._parametri_ripara_permessi(percorsi):
            self._registra_errore_copia(etichetta, f"cmd.exe {parametri}", livello="RIPARA PERMESSI")
            try:
                codici.append(_win_esegui_come_admin("cmd.exe", parametri))
            except OSError as errore:
                if getattr(errore, "winerror", None) == 1223:
                    return False, self._t("Operazione annullata (UAC)", "Cancelled (UAC)")
                return False, str(errore)
        codice = next((c for c in codici if c != 0), 0)
        if codice != 0:
            self._registra_errore_copia(etichetta, f"icacls codice uscita {codice}", livello="RIPARA PERMESSI")
        return codice == 0, (self._t("Permessi riparati", "Permissions repaired") if codice == 0
                             else self._t(f"icacls ha segnalato errori (codice {codice})", f"icacls reported errors (code {codice})"))

    def _conferma_ripara_permessi(self, percorsi, parent=None):
        if isinstance(percorsi, str):
            percorsi = [percorsi]
        elenco = percorsi[0] if len(percorsi) == 1 else self._elenco_breve(percorsi)
        return messagebox.askyesno(
            self._t("Ripara permessi (amministratore)", "Repair permissions (administrator)"),
            self._t("Windows nega l'accesso: i file appartengono probabilmente a un altro utente o a un'altra "
                    "installazione di Windows (succede con dischi spostati da un altro PC).\n\n"
                    f"{elenco}\n\nVuoi rendere il tuo utente ({self._account_corrente()}) proprietario e dargli il "
                    "controllo completo? Windows chiederà la conferma come amministratore (UAC). "
                    "Su cartelle grandi può richiedere qualche minuto.",
                    "Windows denies access: the files probably belong to another user or another Windows "
                    "installation (common with drives moved from another PC).\n\n"
                    f"{elenco}\n\nMake your user ({self._account_corrente()}) the owner and grant full control? "
                    "Windows will ask for administrator confirmation (UAC). Large folders may take a few minutes."),
            parent=parent)

    def avvia_ripara_permessi(self, percorsi, parent=None, al_termine=None):
        """Ripara i permessi in un thread, senza bloccare l'interfaccia."""
        if isinstance(percorsi, str):
            percorsi = [percorsi]
        percorsi = [p for p in percorsi if p and os.path.lexists(p)]
        if not percorsi:
            return
        if not self._conferma_ripara_permessi(percorsi, parent):
            return
        self.lbl_status.config(text=self._t("Riparazione permessi in corso...", "Repairing permissions..."))

        def lavoro():
            ok, messaggio = self._ripara_permessi_admin(percorsi)

            def fine():
                self.lbl_status.config(text=messaggio)
                self.folder_cache.clear()
                testo = messaggio + "\n\n" + (percorsi[0] if len(percorsi) == 1 else self._elenco_breve(percorsi))
                if ok:
                    testo += self._t("\n\nOra puoi ripetere la copia o l'eliminazione.",
                                     "\n\nYou can now retry the copy or delete.")
                    messagebox.showinfo(self._t("Ripara permessi", "Repair permissions"), testo, parent=parent)
                else:
                    testo += self._t("\n\nDettagli nel log.", "\n\nDetails in the log.")
                    messagebox.showwarning(self._t("Ripara permessi", "Repair permissions"), testo, parent=parent)
                if al_termine:
                    al_termine(ok)
            self.root.after(0, fine)
        threading.Thread(target=lavoro, daemon=True).start()

    def azione_ripara_permessi(self):
        if not getattr(self, 'albero_attivo', None):
            return
        self.avvia_ripara_permessi(self._percorsi_selezionati())

    def _elimina_tutti(self, percorsi):
        errori = []
        for percorso in percorsi:
            if os.path.lexists(percorso):
                errori.extend(self._elimina_percorso(percorso))
        return errori

    def azione_elimina(self):
        """Elimina l'elemento o gli elementi selezionati: selezione multipla)."""
        if not getattr(self, 'albero_attivo', None):
            return
        percorsi = self._percorsi_selezionati()
        if not percorsi:
            return
        if len(percorsi) == 1:
            domanda = self._t(f"Eliminare permanentemente?\n\n{percorsi[0]}", f"Delete permanently?\n\n{percorsi[0]}")
        else:
            domanda = self._t(f"Eliminare permanentemente {len(percorsi)} elementi?\n\n{self._elenco_breve(percorsi)}",
                              f"Delete {len(percorsi)} items permanently?\n\n{self._elenco_breve(percorsi)}")
        if not messagebox.askyesno(self._t("Elimina", "Delete"), domanda):
            return
        try:
            errori = self._elimina_tutti(percorsi)
            # Accesso negato persistente (es. NTFS con permesso "Scrittura" ma senza
            # "Eliminazione"): chiede se concedere il permesso al proprio utente.
            if errori and IS_WINDOWS and any(self._errore_temporaneo(e) for _, e in errori):
                rimasti = [p for p in percorsi if os.path.lexists(p)]
                elenco = rimasti[0] if len(rimasti) == 1 else self._elenco_breve(rimasti)
                if rimasti and messagebox.askyesno(
                        self._t("Accesso negato", "Access denied"),
                        self._t("Windows non consente di eliminare: probabilmente al tuo utente "
                                "manca il permesso «Eliminazione» su questo disco o cartella.\n\n"
                                f"{elenco}\n\nVuoi concedere al tuo utente il permesso di eliminazione e riprovare?",
                                "Windows does not allow deleting: your user probably lacks the «Delete» "
                                "permission on this drive or folder.\n\n"
                                f"{elenco}\n\nGrant your user the delete permission and try again?")):
                    falliti = []
                    for p in rimasti:
                        ok, dettagli = self._concedi_permesso_eliminazione(p)
                        if not ok:
                            self._registra_errore_copia(p, f"icacls non riuscito: {dettagli}")
                            falliti.append(p)
                    if falliti and self._conferma_ripara_permessi(falliti):
                        ok_admin, messaggio = self._ripara_permessi_admin(falliti)
                        if not ok_admin:
                            self._registra_errore_copia(falliti[0], messaggio, livello="RIPARA PERMESSI")
                    errori = self._elimina_tutti(rimasti)
            for percorso, errore in errori:
                self._registra_errore_copia(percorso, errore)
            self.folder_cache.clear()
            self.avvia_confronto()
            if errori:
                righe = "\n".join(f"• {p} — {self._motivo_errore(e)}" for p, e in errori[:10])
                if len(errori) > 10:
                    righe += "\n…" + self._t(f" e altri {len(errori) - 10}", f" and {len(errori) - 10} more")
                messagebox.showerror(
                    self._t("Errore eliminazione", "Delete error"),
                    self._t(f"Non è stato possibile eliminare {len(errori)} elemento/i:\n\n{righe}\n\n"
                            "Suggerimenti: chiudi i programmi che usano il file, avvia il programma come amministratore "
                            "oppure controlla Proprietà › Sicurezza della cartella. Dettagli nel log "
                            f"{LOG_ERRORI_FILE}.",
                            f"Could not delete {len(errori)} item(s):\n\n{righe}\n\n"
                            "Tips: close programs using the file, run the program as administrator "
                            "or check the folder's Properties › Security. Details in the log "
                            f"{LOG_ERRORI_FILE}."))
        except Exception as e:
            self._registra_errore_copia(percorsi[0], e)
            messagebox.showerror(self._t("Errore eliminazione", "Delete error"), f"Errore:\n{e}")

    def _sblocca_per_eliminazione(self, p):
        """Toglie sola lettura (e su Windows nascosto/sistema) prima di eliminare."""
        if IS_WINDOWS:
            try:
                _win_imposta_attributi(p, FILE_ATTRIBUTE_NORMAL)
            except OSError:
                pass
        try:
            modo = stat.S_IWRITE | stat.S_IREAD
            if os.path.isdir(p) and not os.path.islink(p):
                modo |= stat.S_IEXEC
            os.chmod(p, modo)
        except OSError:
            pass

    def _rimuovi_voce(self, p):
        """Rimuove un file, un link o una cartella vuota.

        Se Windows risponde Accesso negato/File in uso: toglie gli attributi e
        riprova, poi riprova ancora dopo una breve attesa (antivirus, anteprime).
        """
        if os.path.islink(p):
            rimuovi = os.rmdir if (IS_WINDOWS and os.path.isdir(p)) else os.remove
        elif os.path.isdir(p):
            rimuovi = os.rmdir
        else:
            rimuovi = os.remove
        for tentativo in range(3):
            try:
                rimuovi(p)
                return
            except FileNotFoundError:
                return
            except OSError as errore:
                if not self._errore_temporaneo(errore) or tentativo == 2:
                    raise
                if tentativo == 0:
                    self._sblocca_per_eliminazione(p)
                else:
                    time.sleep(ATTESA_RIPROVA_SECONDI)

    def _elimina_percorso(self, tp):
        """Elimina file o cartella senza fermarsi al primo errore.

        Restituisce l'elenco (percorso, errore) degli elementi non eliminati.
        """
        errori = []
        if os.path.isdir(tp) and not os.path.islink(tp):
            # Dal basso verso l'alto; i link a cartelle sono rimossi come link.
            for radice, cartelle, file in os.walk(tp, topdown=False):
                for nome in file + cartelle:
                    p = os.path.join(radice, nome)
                    if nome in cartelle and os.path.isdir(p) and not os.path.islink(p):
                        try:
                            if os.listdir(p):
                                continue  # contiene elementi non eliminati: già segnalati
                        except OSError:
                            pass
                    try:
                        self._rimuovi_voce(p)
                    except OSError as errore:
                        errori.append((p, errore))
            if errori:
                return errori
        try:
            self._rimuovi_voce(tp)
        except OSError as errore:
            errori.append((tp, errore))
        return errori

    @staticmethod
    def _concedi_permesso_eliminazione(tp):
        """Concede al proprio utente Windows il permesso di eliminazione (icacls).

        Funziona se l'utente è proprietario del file/cartella o è amministratore.
        """
        if not IS_WINDOWS:
            return False, "solo Windows"
        utente = os.environ.get("USERNAME", "")
        dominio = os.environ.get("USERDOMAIN", "")
        account = f"{dominio}\\{utente}" if dominio else utente
        if os.path.isdir(tp) and not os.path.islink(tp):
            comando = ["icacls", tp, "/grant", f"{account}:(OI)(CI)(D,DC)", "/T", "/C", "/Q"]
        else:
            comando = ["icacls", tp, "/grant", f"{account}:(D)"]
        try:
            esito = subprocess.run(comando, capture_output=True, text=True, creationflags=0x08000000)
            return esito.returncode == 0, (esito.stdout + esito.stderr).strip()
        except Exception as errore:
            return False, str(errore)

    def svuota_cache(self):
        """Invalida la cache e ricostruisce i dati, evitando una GUI scollegata dalla cache."""
        if self.is_scanning:
            messagebox.showinfo("Cache", "Attendi il completamento della scansione prima di aggiornare la cache.")
            return
        self.folder_cache.clear()
        c1, c2 = self.safe_combobox_get(self.combo_c1), self.safe_combobox_get(self.combo_c2)
        if c1 and c2 and os.path.isdir(c1) and os.path.isdir(c2):
            self.avvia_confronto()
        else:
            self.rigenera_alberi_da_cache()
            messagebox.showinfo("Cache", "Cache svuotata. Seleziona due cartelle e premi Confronta per ricostruirla.")

    def _imposta_filtro_conteggio(self, filtro):
        """Attiva un solo filtro alla volta; un secondo clic ripristina tutti gli elementi."""
        attributi = (
            "filtro_identici_attivo",
            "filtro_mancanti_attivo",
            "filtro_dimensione_diversa_attivo",
            "filtro_data_diversa_attivo",
            "filtro_data_recente_attivo",
            "filtro_data_vecchia_attivo",
            "filtro_nomi_simili_attivo",
        )
        era_attivo = bool(getattr(self, filtro, False))
        for nome in attributi:
            setattr(self, nome, False)
        # Se il filtro cliccato era già attivo, rimangono tutti spenti.
        if not era_attivo:
            setattr(self, filtro, True)
        self.rigenera_alberi_da_cache()

    def attiva_filtro_identici_da_conteggio(self):
        """Il conteggio Uguali alterna la visualizzazione dei soli file identici e tutti i file."""
        self._imposta_filtro_conteggio("filtro_identici_attivo")

    def attiva_filtro_mancanti_da_conteggio(self):
        """Il conteggio Mancanti alterna filtro mancanti e visualizzazione completa."""
        self._imposta_filtro_conteggio("filtro_mancanti_attivo")

    def filtra_solo_mancanti(self):
        """Compatibilità con il pulsante: alterna mancanti e visualizzazione completa."""
        self.attiva_filtro_mancanti_da_conteggio()

    def attiva_filtro_dimensione_da_conteggio(self):
        """Mostra solo file con dimensione diversa; secondo clic ripristina tutti i file."""
        self._imposta_filtro_conteggio("filtro_dimensione_diversa_attivo")

    def attiva_filtro_data_da_conteggio(self, tipo="data_recente"):
        """Filtra separatamente date recenti e vecchie; secondo clic ripristina tutti i file."""
        attributo = "filtro_data_recente_attivo" if tipo == "data_recente" else "filtro_data_vecchia_attivo"
        self._imposta_filtro_conteggio(attributo)

    def _nodo_mancante(self, tree, item):
        """Restituisce vero esclusivamente per i file mancanti."""
        tags = tree.item(item, "tags")
        return "mancante" in tags or "mancante_sorgente" in tags

    def _filtra_alberi_solo_identici(self):
        """Mostra solo file identici (stessa dimensione e data) e le cartelle antenate."""
        for tree in (self.tree1, self.tree2):
            def _visibile(item):
                children = list(tree.get_children(item))
                discendente_identico = False
                for child in children:
                    if _visibile(child):
                        discendente_identico = True
                tags = tree.item(item, "tags")
                # Le cartelle hanno l'icona dedicata; i file identici hanno il tag cartella_ok.
                is_folder = bool(tree.item(item, "image"))
                file_identico = (not is_folder) and ("cartella_ok" in tags or "cartella_ok_alt" in tags)
                rilevante = file_identico or discendente_identico
                if not rilevante:
                    tree.detach(item)
                elif is_folder and discendente_identico:
                    tree.item(item, open=True)
                return rilevante
            for root_item in list(tree.get_children("")):
                _visibile(root_item)

    def _filtra_alberi_mancanti_diversi(self):
        """Mostra solo elementi mancanti; conserva le cartelle antenate necessarie."""
        for tree in (self.tree1, self.tree2):
            def _v(item):
                children = list(tree.get_children(item))
                # Prima filtra i discendenti: una cartella mancante non deve far
                # comparire automaticamente tutti i file presenti al suo interno.
                figlio_rilevante = False
                for child in children:
                    if _v(child):
                        figlio_rilevante = True
                tags = tree.item(item, "tags")
                is_missing = "mancante" in tags or "mancante_sorgente" in tags
                rilevante = is_missing or figlio_rilevante
                if not rilevante:
                    tree.detach(item)
                return rilevante
            for r in list(tree.get_children("")):
                _v(r)

    def _filtra_alberi_solo_data_diversa(self, tag_data=None):
        """Mostra file con data diversa, oppure solo più recenti/più vecchi, e le cartelle antenate."""
        for tree in (self.tree1, self.tree2):
            def _v(item):
                children = list(tree.get_children(item))
                figlio_rilevante = False
                for child in children:
                    if _v(child):
                        figlio_rilevante = True
                tags = tree.item(item, "tags")
                is_date_diff = (tag_data in tags) if tag_data else any(tag in ("data_diversa", "data_piu_nuova", "data_piu_vecchia") for tag in tags)
                rilevante = is_date_diff or figlio_rilevante
                if not rilevante:
                    tree.detach(item)
                return rilevante
            for root_item in list(tree.get_children("")):
                _v(root_item)

    def _filtra_alberi_solo_dimensione_diversa(self):
        """Conserva i file con dimensione diversa e le cartelle che li contengono."""
        for tree in (self.tree1, self.tree2):
            def _visibile(item):
                children = list(tree.get_children(item))
                discendente = False
                for child in children:
                    if _visibile(child):
                        discendente = True
                tags = tree.item(item, "tags")
                size_diff = "diverso" in tags
                rilevante = size_diff or discendente
                if not rilevante:
                    tree.detach(item)
                elif discendente:
                    tree.item(item, open=True)
                return rilevante
            for root_item in list(tree.get_children("")):
                _visibile(root_item)

    def _filtra_alberi_nomi_simili(self):
        """Conserva i file con nome simile a un altro della stessa cartella e le cartelle che li contengono."""
        simili = getattr(self, "_nodi_simili", ((), ()))
        for tree, insieme in ((self.tree1, simili[0]), (self.tree2, simili[1])):
            def _visibile(item):
                discendente = False
                for child in list(tree.get_children(item)):
                    if _visibile(child):
                        discendente = True
                rilevante = item in insieme or discendente
                if not rilevante:
                    tree.detach(item)
                elif discendente:
                    tree.item(item, open=True)
                return rilevante
            for radice in list(tree.get_children("")):
                _visibile(radice)

    def _filtra_alberi_per_testo(self, chiave):
        for tree in (self.tree1, self.tree2):
            def _filtra(item):
                figli = tree.get_children(item)
                discendente_corrisponde = False
                for figlio in figli:
                    if _filtra(figlio):
                        discendente_corrisponde = True
                nome = tree.item(item, "text").casefold()
                nodi_tree = getattr(self, "_nodi_cartella_mancante1" if tree is self.tree1 else "_nodi_cartella_mancante", {})
                if item in nodi_tree:
                    nome = nodi_tree[item][0].casefold()  # nome reale, non accorciato
                corrisponde = chiave in nome or discendente_corrisponde
                if corrisponde:
                    if figli:
                        tree.item(item, open=True)
                    return True
                tree.detach(item)
                return False
            for radice in list(tree.get_children("")):
                _filtra(radice)

    def _applica_filtri_visualizzazione(self):
        if getattr(self, "filtro_identici_attivo", False):
            self._filtra_alberi_solo_identici()
        elif self.filtro_mancanti_attivo:
            self._filtra_alberi_mancanti_diversi()
        elif self.filtro_data_recente_attivo:
            self._filtra_alberi_solo_data_diversa("data_piu_nuova")
        elif self.filtro_data_vecchia_attivo:
            self._filtra_alberi_solo_data_diversa("data_piu_vecchia")
        elif self.filtro_data_diversa_attivo:
            self._filtra_alberi_solo_data_diversa()
        elif getattr(self, "filtro_dimensione_diversa_attivo", False):
            self._filtra_alberi_solo_dimensione_diversa()
        elif getattr(self, "filtro_nomi_simili_attivo", False):
            self._filtra_alberi_nomi_simili()
        chiave = self.entry_search.get().strip().casefold()
        if chiave:
            self._filtra_alberi_per_testo(chiave)

        # Se un filtro o la ricerca non lascia elementi visibili, mostra un
        # messaggio nel solo pannello rimasto vuoto (Sorgente e/o Destinazione).
        filtro_attivo = any((
            getattr(self, "filtro_identici_attivo", False),
            self.filtro_mancanti_attivo,
            self.filtro_data_recente_attivo,
            self.filtro_data_vecchia_attivo,
            self.filtro_data_diversa_attivo,
            getattr(self, "filtro_dimensione_diversa_attivo", False),
            getattr(self, "filtro_nomi_simili_attivo", False),
            bool(chiave),
        ))
        testo_vuoto = self._t("Nessun risultato trovato", "No results found")
        for tree in (self.tree1, self.tree2):
            # Rimuove sempre l'etichetta precedente, anche quando il filtro viene tolto.
            label_vuoto = getattr(tree, "_label_nessun_risultato", None)
            if label_vuoto is not None:
                try:
                    label_vuoto.destroy()
                except Exception:
                    pass
                tree._label_nessun_risultato = None

            # Non contare come risultati eventuali righe-segnaposto già presenti.
            children = list(tree.get_children(""))
            risultati_reali = [
                item for item in children
                if "nessun_risultato" not in tree.item(item, "tags")
            ]

            if filtro_attivo and not risultati_reali:
                # Elimina un eventuale segnaposto precedente e usa un overlay
                # centrato sull'intero riquadro Treeview.
                for item in children:
                    if "nessun_risultato" in tree.item(item, "tags"):
                        tree.delete(item)

                import tkinter as tk
                label_vuoto = tk.Label(
                    tree,
                    text=testo_vuoto,
                    foreground="#9ca3af",
                    background=(
                        __import__("tkinter").ttk.Style(tree).lookup("Treeview", "background")
                        or tree.master.cget("background")
                    ),
                    font=("Segoe UI", 13, "bold"),
                    bd=0,
                    anchor="center",
                )
                label_vuoto.place(relx=0.5, rely=0.5, anchor="center")
                tree._label_nessun_risultato = label_vuoto

    def esegui_ricerca_testo(self):
        # Ricostruisce gli alberi dalla cache, poi riapplica filtro mancanti e ricerca.
        # Debounce: la ricostruzione parte solo dopo una breve pausa nella digitazione,
        # invece di rifare entrambi gli alberi a ogni singolo carattere.
        id_precedente = getattr(self, "_ricerca_after_id", None)
        if id_precedente is not None:
            try:
                self.root.after_cancel(id_precedente)
            except tk.TclError:
                pass
        self._ricerca_after_id = self.root.after(300, self._esegui_ricerca_testo_ora)

    def _esegui_ricerca_testo_ora(self):
        self._ricerca_after_id = None
        self.rigenera_alberi_da_cache()

    def aggiungi_a_cronologia(self, l, combo, p):
        if not p: return
        if p in l: l.remove(p)
        l.insert(0, p)
        if len(l) > 10: l.pop()
        combo['values'] = [self._testo_combobox_percorso(x) for x in l]; combo.set(self._testo_combobox_percorso(p)); self.salva_cronologia_su_disco()
        if combo is self.combo_c2:
            self.salva_ultima_destinazione(p)

    def _disegna_icona_cartella(self, canvas):
        """Disegna un'icona cartella gialla, indipendente dagli emoji di Windows."""
        # Icona compatta (circa 18 x 14 px), proporzionata alle icone dei menu.
        canvas.create_polygon(6, 8, 13, 8, 16, 11, 25, 11, 25, 22, 6, 22,
                              fill="#FACC15", outline="#EAB308", width=1)
        canvas.create_polygon(5, 11, 26, 11, 24, 23, 7, 23,
                              fill="#FBBF24", outline="#EAB308", width=1)
        canvas.create_line(7, 14, 24, 14, fill="#FEF08A", width=1)

    def salva_ultima_destinazione(self, percorso):
        """Salva l'ultima destinazione nel file settings unificato."""
        self.ultima_destinazione = os.path.abspath(percorso) if percorso else ""
        self.salva_cronologia_su_disco()

    def carica_ultima_destinazione(self):
        """Legge la destinazione da settings; importa il vecchio file se necessario."""
        percorso = getattr(self, "ultima_destinazione", "").strip()
        try:
            # Retrocompatibilità: importa la destinazione dal file storico solo se
            # il file settings non contiene ancora una destinazione.
            if not percorso and os.path.isfile(LAST_DESTINATION_FILE):
                with open(LAST_DESTINATION_FILE, "r", encoding="utf-8") as f:
                    percorso = f.read().strip()
                if percorso:
                    self.ultima_destinazione = os.path.abspath(percorso)
                    self.salva_cronologia_su_disco()
            if percorso and os.path.isdir(percorso):
                if percorso not in self.cronologia_c2:
                    self.cronologia_c2.insert(0, percorso)
                    self.cronologia_c2 = self.cronologia_c2[:10]
                self.combo_c2['values'] = [self._testo_combobox_percorso(x) for x in self.cronologia_c2]
                self.combo_c2.set(self._testo_combobox_percorso(percorso))
        except (OSError, UnicodeError):
            pass

    def sfoglia_cartella(self, n):
        """Seleziona una cartella; se cambia la destinazione dopo un confronto, lo ripete."""
        combo = self.combo_c1 if n == 1 else self.combo_c2
        cronologia = self.cronologia_c1 if n == 1 else self.cronologia_c2
        destinazione_precedente = os.path.normcase(os.path.normpath(self.safe_combobox_get(self.combo_c2))) if self.safe_combobox_get(self.combo_c2) else ""
        iniziale = self.safe_combobox_get(combo)
        if not iniziale or not os.path.isdir(iniziale):
            iniziale = os.path.expanduser("~")
        c = filedialog.askdirectory(parent=self.root, title="Seleziona cartella", initialdir=iniziale, mustexist=True)
        if c:
            # Non riutilizza il vecchio valore della combobox: salva esattamente
            # la cartella scelta, normalizzata per il sistema operativo.
            c = os.path.normpath(os.path.abspath(c))
            combo.set(self._testo_combobox_percorso(c))
            self.aggiungi_a_cronologia(cronologia, combo, c)
            if n == 2:
                self.salva_ultima_destinazione(c)
                destinazione_nuova = os.path.normcase(os.path.normpath(c))
                # Se l'utente cambia destinazione dopo un confronto già completato,
                # avvia automaticamente una nuova scansione con il percorso appena scelto.
                if (destinazione_nuova != destinazione_precedente
                        and self._confronto_eseguito and not self.is_scanning):
                    self.root.after_idle(self.avvia_confronto)

    def apri_aiuto_contatti(self):
        """Mostra aiuto e contatti nella lingua attualmente selezionata."""
        en = self.lingua == "en"
        titolo = "Help & Contacts" if en else "Aiuto e contatti"
        finestra = tk.Toplevel(self.root)
        finestra.title(titolo)
        finestra.transient(self.root)
        finestra.resizable(False, False)
        finestra.configure(padx=22, pady=18)

        tk.Label(
            finestra, text=titolo, font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            finestra,
            text="Keyboard shortcuts" if en else "Scorciatoie da tastiera",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 5))
        if en:
            scorciatoie = (
                "F5 — Refresh comparison\n"
                "Ctrl+F — Search for a file\n"
                "F2 — Rename selected item\n"
                "Del — Delete selected item\n"
                "Ctrl+Shift+C — Copy selected item to the opposite folder\n"
                "Ctrl+Shift+M — Copy differences from left to right\n"
                "Ctrl+Shift+P — Preview differences\n"
                "Ctrl+Shift+R — Refresh selected folder\n"
                "Ctrl+Shift+E — Expand all folders\n"
                "Ctrl+Shift+F — Open Files to exclude"
            )
            testo_contatti = ("Have suggestions, ideas to improve the program, change requests, "
                              "or a technical issue to report?\n\nContact me by email:")
            istruzione_email = "Click the address to open your email application."
            chiudi = "Close"
        else:
            scorciatoie = (
                "F5 — Aggiorna il confronto\n"
                "Ctrl+F — Cerca un file\n"
                "F2 — Rinomina l'elemento selezionato\n"
                "Canc — Elimina l'elemento selezionato\n"
                "Ctrl+Maiusc+C — Copia l'elemento selezionato nella cartella opposta\n"
                "Ctrl+Maiusc+M — Copia le differenze da sinistra a destra\n"
                "Ctrl+Maiusc+P — Anteprima delle differenze\n"
                "Ctrl+Maiusc+R — Aggiorna la cartella selezionata\n"
                "Ctrl+Maiusc+E — Espande tutte le cartelle\n"
                "Ctrl+Maiusc+F — Apre la finestra File da escludere"
            )
            testo_contatti = ("Hai suggerimenti, idee per migliorare il programma, richieste di modifica "
                              "oppure vuoi segnalare un problema tecnico?\n\nPer contattarmi via email:")
            istruzione_email = "Clicca sull'indirizzo per aprire il programma di posta."
            chiudi = "Chiudi"

        tk.Label(
            finestra, text=scorciatoie, font=("Segoe UI", 9),
            justify="left", wraplength=430, anchor="w"
        ).pack(anchor="w", pady=(0, 14))
        tk.Label(
            finestra, text=testo_contatti,
            font=("Segoe UI", 10), justify="left", wraplength=430
        ).pack(anchor="w", pady=(0, 8))

        email = tk.Label(
            finestra, text="roby77dopa@gmail.com", fg="#2563eb",
            font=("Segoe UI", 11, "underline"), cursor="hand2"
        )
        email.pack(anchor="w", pady=(0, 14))
        email.bind("<Button-1>", lambda _event: webbrowser.open("mailto:roby77dopa@gmail.com"))

        tk.Label(
            finestra, text=istruzione_email,
            font=("Segoe UI", 9), fg="#64748b", wraplength=430, justify="left"
        ).pack(anchor="w", pady=(0, 16))
        tk.Button(
            finestra, text=chiudi, command=finestra.destroy,
            padx=14, pady=5, cursor="hand2"
        ).pack(anchor="e")
        finestra.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - finestra.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - finestra.winfo_height()) // 2)
        finestra.geometry(f"+{x}+{y}")

    def _carica_sync_sottocartella(self):
        """Opzione: Sincronizza 1→2 lavora dentro <destinazione>\\<nome sorgente> (default: attiva)."""
        try:
            with open(os.path.join(DATA_DIR, "mediadirfile-sync-subfolder.txt"), "r", encoding="utf-8") as f:
                return f.read().strip() != "0"
        except OSError:
            return True

    def _salva_sync_sottocartella(self):
        try:
            with open(os.path.join(DATA_DIR, "mediadirfile-sync-subfolder.txt"), "w", encoding="utf-8") as f:
                f.write("1" if self.var_sync_sottocartella.get() else "0")
        except OSError as exc:
            messagebox.showwarning("Impostazioni", f"Impossibile salvare l'impostazione: {exc}", parent=self.root)

    def _carica_stile_pulsanti(self):
        """Legge lo stile della barra comandi, conservandolo tra gli avvii."""
        percorso = os.path.join(DATA_DIR, "mediadirfile-button-style.txt")
        try:
            valore = open(percorso, "r", encoding="utf-8").read().strip()
            if valore == "2":
                return 1  # stile "piatto e minimale" rimosso: passa allo stile 1
            return int(valore) if valore in {str(i) for i in range(1, 8)} else 7
        except (OSError, ValueError):
            return 7

    def _salva_stile_pulsanti(self):
        try:
            with open(os.path.join(DATA_DIR, "mediadirfile-button-style.txt"), "w", encoding="utf-8") as f:
                f.write(str(self.stile_pulsanti))
        except OSError as exc:
            messagebox.showwarning("Impostazioni", f"Impossibile salvare lo stile: {exc}", parent=self.root)

    def _uniforma_altezza_pulsante_filtra(self):
        """Porta tutti i pulsanti principali alla stessa altezza.

        L'altezza di riferimento è la maggiore tra i pulsanti di solo testo; Filtra (con
        icona) viene adattato a quella, senza ingrandire gli altri."""
        try:
            nomi = ("btn_avvia", "btn_filtra", "btn_espandi", "btn_stop", "btn_copia_tutto",
                    "btn_sincronizza", "btn_anteprima", "btn_spazio", "btn_refresh")
            pulsanti = [getattr(self, n, None) for n in nomi]
            pulsanti = [b for b in pulsanti if b is not None and b.winfo_exists()]
            if not pulsanti:
                return
            for b in pulsanti:
                b.configure(altezza_fissa=0)      # altezza naturale (font + spaziatura)
            try:
                self.btn_filtra.pack_configure(ipady=0)
            except (tk.TclError, AttributeError):
                pass
            self.root.update_idletasks()
            solo_testo = [b for b in pulsanti if b is not getattr(self, "btn_filtra", None)]
            target = max(b.winfo_reqheight() for b in solo_testo)
            for b in pulsanti:
                b.configure(altezza_fissa=target)
        except (tk.TclError, AttributeError):
            pass

    def _applica_stile_pulsanti(self):
        """Applica uno degli stili grafici ai pulsanti principali senza cambiare i comandi."""
        stile = getattr(self, "stile_pulsanti", 1)
        if stile == 7:
            self._applica_stile_pulsanti_moderno()
            return
        # Lo stile scelto viene applicato sia ai comandi di confronto sia a Copia e sicurezza.
        pulsanti = [self.btn_avvia, self.btn_refresh, self.btn_filtra,
                    self.btn_espandi, self.btn_stop,
                    self.btn_copia_tutto, self.btn_anteprima, self.btn_spazio]
        colori = ["#1677f2", "#7c3aed", "#1677f2", "#059669", "#64748b", "#0f766e", "#0369a1", "#64748b"]
        if stile == 3:  # icone grandi
            colori = ["#0878f9", "#7138ed", "#0878f9", "#00a86b", "#58728c", "#087e75", "#056da6", "#58728c"]
        elif stile == 4:  # schede contornate
            colori = ["#0b2237", "#21182f", "#0b2237", "#092d27", "#1d2938", "#092d2b", "#09283a", "#1d2938"]
        elif stile == 5:  # stati attivi/contrasto sobrio
            colori = ["#1479ff", "#39305e", "#1479ff", "#135747", "#334155", "#104b46", "#173e59", "#334155"]
        elif stile == 6:  # gradient-like palette (Tkinter non supporta gradienti nativi)
            colori = ["#0099f7", "#8b35e8", "#0099f7", "#00bd83", "#91a7bd", "#00a99a", "#0787c9", "#91a7bd"]
        for i, (b, colore) in enumerate(zip(pulsanti, colori)):
            try:
                if stile == 3:
                    b.configure(font=("Segoe UI", 11, "bold"), padx=14, pady=10, relief="flat", bd=0,
                                highlightthickness=0, bg=colore, activebackground=colore)
                elif stile == 4:
                    b.configure(font=("Segoe UI", 10, "bold"), padx=12, pady=7, relief="solid", bd=1,
                                highlightthickness=1, highlightbackground=colore, bg=colore, activebackground=colore)
                elif stile == 5:
                    b.configure(font=("Segoe UI", 10, "bold"), padx=12, pady=7, relief="raised", bd=1,
                                highlightthickness=1 if i == 0 else 0, highlightbackground="#38bdf8",
                                bg=colore, activebackground=colore)
                else:
                    b.configure(font=("Segoe UI", 10, "bold"), padx=12, pady=7, relief="flat", bd=0,
                                highlightthickness=0, bg=colore, activebackground=colore)
                b._base_bg = colore
            except tk.TclError:
                pass
        try:
            # Rendi la scritta Filtra più leggibile rispetto alla dimensione precedente.
            # La regolazione dell'altezza viene poi riallineata ai pulsanti principali.
            self.btn_filtra.configure(font=("Segoe UI", 14, "bold"))
            self.root.after_idle(self._uniforma_altezza_pulsante_filtra)
        except (tk.TclError, AttributeError):
            pass

    def _palette_moderna(self):
        """Colori (sfondo, testo, hover) dei ruoli dei pulsanti nello stile moderno."""
        t = TEMES.get(self.current_theme, TEMES["modern"])
        dark = self.current_theme in TEMI_SCURI
        accent = t.get("accent", "#3b82f6")
        if dark:
            pal = {"neutro": ("#1d2431", "#e5e9f0", "#2a3445"),
                   "ok": ("#12332b", "#6ee7b7", "#194538"),
                   "warn": ("#3b2d12", "#fcd34d", "#4d3b17"),
                   "danger": ("#3d1f26", "#fca5a5", "#522831"),
                   "primario": (accent, "#ffffff", _mescola_colori(accent, "#ffffff", 0.18))}
        else:
            pal = {"neutro": ("#e9edf3", "#1f2937", "#dbe1ea"),
                   "ok": ("#d1fae5", "#065f46", "#a7f3d0"),
                   "warn": ("#fef3c7", "#92400e", "#fde68a"),
                   "danger": ("#fee2e2", "#b91c1c", "#fecaca"),
                   "primario": (accent, "#ffffff", _mescola_colori(accent, "#000000", 0.14))}
        return pal

    def _applica_stile_pulsanti_moderno(self):
        """Stile 7: un solo comando primario, gli altri in toni sobri; hover morbido."""
        pal = self._palette_moderna()
        ruoli = (
            (self.btn_avvia, "primario"), (self.btn_filtra, "neutro"), (self.btn_espandi, "neutro"),
            (self.btn_stop, "danger"), (self.btn_refresh, "neutro"), (self.btn_copia_tutto, "ok"),
            (self.btn_sincronizza, "warn"), (self.btn_anteprima, "neutro"), (self.btn_spazio, "neutro"),
        )
        for b, ruolo in ruoli:
            bg_c, fg_c, hover = pal[ruolo]
            try:
                b.configure(bg=bg_c, fg=fg_c, activebackground=hover, activeforeground=fg_c,
                            disabledforeground=_mescola_colori(fg_c, bg_c, 0.55),
                            font=("Segoe UI", PULSANTI_FONT, "bold"), padx=PULSANTI_PADX,
                            pady=PULSANTI_PADY, relief="flat", bd=0, highlightthickness=0)
                b._base_bg = bg_c
                b._hover_bg = hover
            except tk.TclError:
                pass
        self.root.after_idle(self._uniforma_altezza_pulsante_filtra)

    def _stile_barra_secondaria(self, moderno):
        """Pulsanti piccoli della barra percorsi: moderni oppure colori originali."""
        t = TEMES.get(self.current_theme, TEMES["dark"])
        if moderno:
            neutro, testo, hover = self._palette_moderna()["neutro"]
            accent = t.get("accent", "#3b82f6")
            stile_btn = {
                self.btn_impostazioni: (neutro, testo, hover),
                self.btn_profili: (neutro, testo, hover),
                self.btn_cancella_cronologia: (neutro, testo, hover),
                self.btn_aiuto: (accent, "#ffffff", _mescola_colori(accent, "#ffffff", 0.18)),
            }
            canvas_bg = neutro
        else:
            stile_btn = {
                self.btn_impostazioni: ("#334155", "white", "#475569"),
                self.btn_profili: ("#334155", "white", "#475569"),
                self.btn_cancella_cronologia: ("#334155", "#f1f5f9", "#475569"),
                self.btn_aiuto: ("#1d4ed8", "white", "#1e40af"),
            }
            canvas_bg = "#475569"
        for b, (bg_c, fg_c, hover) in stile_btn.items():
            try:
                b.configure(bg=bg_c, fg=fg_c, activebackground=hover, activeforeground=fg_c)
            except tk.TclError:
                pass
        for c in (self.btn_cartella1, self.btn_cartella2):
            try:
                c.configure(bg=canvas_bg)
            except tk.TclError:
                pass

    def apri_impostazioni_stile(self):
        """Dialogo impostazioni per scegliere e salvare uno dei sei stili."""
        finestra = tk.Toplevel(self.root)
        finestra.title("Impostazioni - stile pulsanti")
        finestra.transient(self.root)
        finestra.resizable(False, False)
        finestra.configure(padx=18, pady=14)
        tk.Label(finestra, text="Scegli lo stile della barra dei comandi", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 10))
        var = tk.IntVar(value=self.stile_pulsanti)
        opzioni = [
            (7, "Stile moderno 2026 — un solo comando primario, toni sobri"),
            (1, "Stile moderno — icone e testo, colori vivaci"),
            (3, "Stile con icone grandi — pulsanti più visibili"),
            (4, "Stile a schede — bordi contornati"),
            (5, "Stile con stati attivi — evidenziazione del comando principale"),
            (6, "Stile con gradienti — palette vivace (simulata con colori pieni)"),
        ]
        for numero, testo in opzioni:
            tk.Radiobutton(finestra, text=testo, variable=var, value=numero,
                           font=("Segoe UI", 10), anchor="w", padx=4, pady=4).pack(fill="x", anchor="w")
        riga = tk.Frame(finestra)
        riga.pack(fill="x", pady=(12, 0))
        def applica():
            self.stile_pulsanti = var.get()
            self._applica_stile_pulsanti()
            self._salva_stile_pulsanti()
            self.applica_tema()
            finestra.destroy()
        tk.Button(riga, text="Applica", command=applica, bg="#1677f2", fg="white",
                  font=("Segoe UI", 10, "bold"), relief="flat", padx=16, pady=6).pack(side="right", padx=(6, 0))
        tk.Button(riga, text="Annulla", command=finestra.destroy,
                  font=("Segoe UI", 10), padx=12, pady=6).pack(side="right")
        finestra.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - finestra.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - finestra.winfo_height()) // 2)
        finestra.geometry(f"+{x}+{y}")

    def _cattura_default_tk(self):
        """Memorizza i colori predefiniti dei widget Tk, per riconoscere quelli non personalizzati."""
        self._tk_default = {}
        for cls in (tk.Frame, tk.LabelFrame, tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton,
                    tk.Entry, tk.Text, tk.Listbox, tk.Scale, tk.Spinbox, tk.Scrollbar):
            try:
                w = cls(self.root)
                dati = {}
                for opzione in ("bg", "fg"):
                    try:
                        dati[opzione] = str(w.cget(opzione))
                    except tk.TclError:
                        pass
                self._tk_default[w.winfo_class()] = dati
                w.destroy()
            except tk.TclError:
                pass

    def _su_mappa_finestra(self, event):
        w = event.widget
        if isinstance(w, str) or w is self.root:
            return
        try:
            if w.winfo_class() != "Toplevel" or w.overrideredirect():
                return
        except (tk.TclError, AttributeError):
            return
        self._stila_finestra(w)
        # Secondo passaggio per i widget aggiunti subito dopo la comparsa della finestra.
        try:
            w.after(150, lambda w=w: self._stila_finestra(w))
        except tk.TclError:
            pass

    def _stila_finestre_aperte(self):
        for w in self.root.winfo_children():
            try:
                if w.winfo_class() == "Toplevel" and not w.overrideredirect():
                    self._stila_finestra(w)
            except tk.TclError:
                pass

    def _stila_finestra(self, finestra):
        """Applica il tema corrente a una finestra secondaria.

        Cambia solo i widget con i colori Tk predefiniti: quelli già colorati a mano
        (pulsanti blu, etichette rosse, ecc.) conservano il loro colore."""
        try:
            if not finestra.winfo_exists():
                return
        except tk.TclError:
            return
        t = TEMES.get(self.current_theme, TEMES["dark"])
        dark = self.current_theme in TEMI_SCURI
        bg, fg, campo = t["bg"], t["fg"], t["entry_bg"]
        accent = t.get("accent", "#3b82f6")
        bordo = t.get("border", "#3b4b60" if dark else "#d7dee8")
        neutro_bg, neutro_fg, hover = self._palette_moderna()["neutro"]
        default = getattr(self, "_tk_default", {})

        def predefinito(w, opzione):
            try:
                corrente = str(w.cget(opzione))
            except tk.TclError:
                return False
            classe = w.winfo_class()
            base = default.get(classe) or default.get("Frame", {})
            return corrente == base.get(opzione) or corrente == getattr(w, "_tema_" + opzione, None)

        def imposta(w, **opzioni):
            for chiave, valore in opzioni.items():
                try:
                    w.configure(**{chiave: valore})
                except tk.TclError:
                    continue
                setattr(w, "_tema_" + chiave, valore)

        def visita(w):
            try:
                classe = w.winfo_class()
                if classe in ("Toplevel", "Frame", "Labelframe", "Label", "Message"):
                    if predefinito(w, "bg"):
                        imposta(w, bg=bg)
                    if classe in ("Label", "Labelframe", "Message") and predefinito(w, "fg"):
                        imposta(w, fg=fg)
                elif classe in ("Checkbutton", "Radiobutton"):
                    if predefinito(w, "bg"):
                        imposta(w, bg=bg, activebackground=bg, highlightthickness=0)
                    if predefinito(w, "fg"):
                        imposta(w, fg=fg, activeforeground=fg)
                    imposta(w, selectcolor=campo)
                elif classe == "Button":
                    if predefinito(w, "bg"):
                        imposta(w, bg=neutro_bg, fg=neutro_fg, activebackground=hover,
                                activeforeground=neutro_fg, relief="flat", bd=0, highlightthickness=0,
                                disabledforeground=_mescola_colori(neutro_fg, neutro_bg, 0.55),
                                cursor="hand2")
                elif classe in ("Entry", "Spinbox", "Text", "Listbox"):
                    if predefinito(w, "bg"):
                        imposta(w, bg=campo, fg=fg, relief="flat", highlightthickness=1,
                                highlightbackground=bordo, highlightcolor=accent,
                                selectbackground=accent, selectforeground="#ffffff",
                                bd=4 if classe in ("Entry", "Spinbox") else 0)
                        if classe != "Listbox":
                            imposta(w, insertbackground=fg)
                        if classe == "Text":
                            imposta(w, padx=8, pady=6)
                elif classe == "Scale":
                    if predefinito(w, "bg"):
                        imposta(w, bg=bg, fg=fg, troughcolor=campo, activebackground=bordo,
                                highlightthickness=0)
                elif classe == "Scrollbar":
                    if predefinito(w, "bg"):
                        imposta(w, bg=bordo, troughcolor=bg, activebackground=t.get("muted", fg),
                                highlightthickness=0, bd=0)
                for figlio in w.winfo_children():
                    visita(figlio)
            except tk.TclError:
                pass

        visita(finestra)

    # --- Profili: coppie sorgente/destinazione con un nome --------------------------------
    def _carica_profili(self):
        try:
            with open(PROFILI_FILE, "r", encoding="utf-8") as f:
                dati = json.load(f)
        except (OSError, ValueError):
            return []
        elenco = dati.get("profili", []) if isinstance(dati, dict) else dati
        profili = []
        for p in elenco if isinstance(elenco, list) else []:
            if isinstance(p, dict) and str(p.get("nome", "")).strip():
                profili.append({"nome": str(p["nome"]).strip(),
                                "sorgente": str(p.get("sorgente", "")),
                                "destinazione": str(p.get("destinazione", ""))})
        profili.sort(key=lambda p: p["nome"].casefold())
        return profili

    def _salva_profili(self):
        self.profili.sort(key=lambda p: p["nome"].casefold())
        try:
            temporaneo = PROFILI_FILE + ".tmp"
            with open(temporaneo, "w", encoding="utf-8") as f:
                json.dump({"versione": 1, "profili": self.profili}, f, ensure_ascii=False, indent=2)
            os.replace(temporaneo, PROFILI_FILE)   # scrittura atomica: nessun file a metà
            return True
        except OSError as errore:
            messagebox.showwarning(self._t("Profili", "Profiles"), self._t(
                f"Impossibile salvare i profili: {errore}", f"Could not save the profiles: {errore}"), parent=self.root)
            return False

    def _indice_profilo(self, nome, escludi=None):
        chiave = nome.casefold()
        for i, p in enumerate(self.profili):
            if i != escludi and p["nome"].casefold() == chiave:
                return i
        return None

    @staticmethod
    def _pulisci_nome_profilo(testo):
        return " ".join(str(testo or "").split())[:60]

    def mostra_menu_profili(self):
        """Menu del pulsante Profili: richiama un profilo, salva i percorsi attuali, rinomina, elimina."""
        menu = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 10))
        if self.profili:
            for p in self.profili:
                menu.add_command(label=p["nome"], command=lambda n=p["nome"]: self._carica_profilo(n))
        else:
            menu.add_command(label=self._t("(nessun profilo salvato)", "(no saved profiles)"), state="disabled")
        menu.add_separator()
        menu.add_command(label=self._t("💾  Salva i percorsi attuali come profilo…", "💾  Save current paths as a profile…"),
                         command=self._salva_profilo_corrente)
        rinomina = tk.Menu(menu, tearoff=0, font=("Segoe UI", 10))
        elimina = tk.Menu(menu, tearoff=0, font=("Segoe UI", 10))
        for p in self.profili:
            rinomina.add_command(label=p["nome"], command=lambda n=p["nome"]: self._rinomina_profilo(n))
            elimina.add_command(label=p["nome"], command=lambda n=p["nome"]: self._elimina_profilo(n))
        stato = "normal" if self.profili else "disabled"
        menu.add_cascade(label=self._t("✎  Rinomina profilo", "✎  Rename profile"), menu=rinomina, state=stato)
        menu.add_cascade(label=self._t("🗑  Elimina profilo", "🗑  Delete profile"), menu=elimina, state=stato)
        try:
            x = self.btn_profili.winfo_rootx()
            y = self.btn_profili.winfo_rooty() + self.btn_profili.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _salva_profilo_corrente(self):
        sorgente = self.safe_combobox_get(self.combo_c1)
        destinazione = self.safe_combobox_get(self.combo_c2)
        if not sorgente or not destinazione:
            messagebox.showinfo(self._t("Profili", "Profiles"), self._t(
                "Imposta prima la cartella sorgente e quella di destinazione.",
                "Set the source and destination folders first."), parent=self.root)
            return
        nome = simpledialog.askstring(
            self._t("Salva profilo", "Save profile"),
            self._t("Nome del profilo (es. Backup Film Maria):", "Profile name (e.g. Movies backup):")
            + f"\n\n{sorgente}\n→ {destinazione}", parent=self.root)
        if nome is None:
            return
        nome = self._pulisci_nome_profilo(nome)
        if not nome:
            messagebox.showinfo(self._t("Profili", "Profiles"), self._t(
                "Il nome del profilo non può essere vuoto.", "The profile name cannot be empty."), parent=self.root)
            return
        nuovo = {"nome": nome, "sorgente": sorgente, "destinazione": destinazione}
        esistente = self._indice_profilo(nome)
        if esistente is not None:
            if not messagebox.askyesno(self._t("Profili", "Profiles"), self._t(
                    f"Esiste già un profilo «{self.profili[esistente]['nome']}». Sovrascriverlo?",
                    f"A profile named «{self.profili[esistente]['nome']}» already exists. Overwrite it?"), parent=self.root):
                return
            nuovo["nome"] = self.profili[esistente]["nome"]   # si conserva il nome originale
            self.profili[esistente] = nuovo
        else:
            self.profili.append(nuovo)
        if self._salva_profili():
            self.lbl_status.config(text=self._t(f"Profilo «{nome}» salvato.", f"Profile «{nome}» saved."))

    def _carica_profilo(self, nome):
        if getattr(self, "is_scanning", False):
            messagebox.showinfo(self._t("Profili", "Profiles"), self._t(
                "Attendi la fine dell'operazione in corso.", "Wait for the current operation to finish."), parent=self.root)
            return
        indice = self._indice_profilo(nome)
        if indice is None:
            return
        p = self.profili[indice]
        self.combo_c1.set(self._testo_combobox_percorso(p["sorgente"]))
        self.combo_c2.set(self._testo_combobox_percorso(p["destinazione"]))
        self.lbl_status.config(text=self._t(
            f"Profilo «{p['nome']}» caricato. Premi Confronta per avviare la scansione.",
            f"Profile «{p['nome']}» loaded. Press Compare to start the scan."))

    def _rinomina_profilo(self, nome):
        indice = self._indice_profilo(nome)
        if indice is None:
            return
        nuovo_nome = simpledialog.askstring(self._t("Rinomina profilo", "Rename profile"),
                                            self._t("Nuovo nome:", "New name:"),
                                            initialvalue=self.profili[indice]["nome"], parent=self.root)
        if nuovo_nome is None:
            return
        nuovo_nome = self._pulisci_nome_profilo(nuovo_nome)
        if not nuovo_nome:
            return
        if self._indice_profilo(nuovo_nome, escludi=indice) is not None:
            messagebox.showwarning(self._t("Profili", "Profiles"), self._t(
                f"Esiste già un profilo chiamato «{nuovo_nome}».", f"A profile named «{nuovo_nome}» already exists."),
                parent=self.root)
            return
        self.profili[indice]["nome"] = nuovo_nome
        self._salva_profili()

    def _elimina_profilo(self, nome):
        indice = self._indice_profilo(nome)
        if indice is None:
            return
        if messagebox.askyesno(self._t("Elimina profilo", "Delete profile"), self._t(
                f"Eliminare il profilo «{self.profili[indice]['nome']}»?\n(Le cartelle non vengono toccate.)",
                f"Delete the profile «{self.profili[indice]['nome']}»?\n(The folders are not touched.)"), parent=self.root):
            del self.profili[indice]
            self._salva_profili()

    def mostra_menu_impostazioni(self):
        """Apre il menu che raggruppa temi, stile pulsanti e lingua."""
        try:
            x = self.btn_impostazioni.winfo_rootx()
            y = self.btn_impostazioni.winfo_rooty() + self.btn_impostazioni.winfo_height()
            self.menu_impostazioni.tk_popup(x, y)
        finally:
            try:
                self.menu_impostazioni.grab_release()
            except tk.TclError:
                pass

    def mostra_menu_tema(self):
        """Mostra le scelte esplicite per il tema dell'interfaccia."""
        try:
            x = self.btn_tema.winfo_rootx()
            y = self.btn_tema.winfo_rooty() + self.btn_tema.winfo_height()
            self.menu_tema.tk_popup(x, y)
        finally:
            try:
                self.menu_tema.grab_release()
            except tk.TclError:
                pass

    def scegli_tema(self, tema):
        if tema not in TEMES:
            return
        self.current_theme = tema
        if tema in ("modern", "modern_light") and getattr(self, "stile_pulsanti", 1) != 7:
            self.stile_pulsanti = 7
            self._salva_stile_pulsanti()
        self.applica_tema()
        self.salva_cronologia_su_disco()

    def toggle_tema(self):
        # Mantiene disponibile il vecchio comportamento per eventuali richiami interni.
        self.scegli_tema("light" if self.current_theme == "dark" else "dark")

    def applica_tema(self):
        """Applica una veste grafica più uniforme, leggibile e moderna."""
        t = TEMES[self.current_theme]
        bg, fg = t["bg"], t["fg"]
        dark = self.current_theme in TEMI_SCURI
        modern = self.current_theme in ("modern", "modern_light")

        # La barra usa i conteggi reali già calcolati e non mostra le dimensioni su disco.
        if hasattr(self, "panel_summary"):
            self.frame_tree1.pack_forget(); self.frame_tree2.pack_forget()
            self.panel_summary.pack_forget(); self.panel_old_summary.pack_forget()
            self.frame_tree1.grid_forget(); self.frame_tree2.grid_forget()
            self.panel_summary.grid_forget(); self.panel_old_summary.grid_forget()
            self.frame_tree1.pack(side="left", fill="both", expand=True, padx=(0, 7), pady=4)
            self.frame_tree2.pack(side="left", fill="both", expand=True, padx=(7, 0), pady=4)
            # Barra riepilogo e legenda sotto la toolbar e sopra gli alberi, come nel mockup.
            self.panel_old_summary.pack(fill="x", padx=14, pady=(2, 4), before=self.ft)
        panel = "#293241" if dark else "#ffffff"
        muted = t.get("muted", "#aab7c4" if dark else "#64748b")
        accent = t.get("accent", "#3b82f6")
        card_bg = t.get("surface", "#0d2033" if dark else "#ffffff")
        card_border = t.get("border", "#23415e" if dark else "#cbd5e1")
        self.root.configure(bg=bg)
        if hasattr(self, "panel_summary_legend"):
            legend_bg = card_bg
            self.panel_summary_legend.configure(bg=legend_bg, highlightbackground=card_border)
            for gruppo, punto, testo_lbl in getattr(self, "summary_legend_labels", []):
                gruppo.configure(bg=legend_bg)
                punto.configure(bg=legend_bg)
                testo_lbl.configure(bg=legend_bg, fg=fg)
        if hasattr(self, "panel_old_summary"):
            row_bg = card_bg
            self.panel_old_summary.configure(bg=row_bg, highlightbackground=card_border)
            colori_riepilogo = {"identici": ("#374151" if not dark else "#f2f2f2"), "dimensione": "#facc15", "data_vecchia": "#d97706", "data_recente": "#16a34a", "mancanti": "#ff4d4f", "diversi": "#facc15"}
            for w in self.panel_old_summary.winfo_children():
                try:
                    if isinstance(w, tk.Frame):
                        w.configure(bg=row_bg)
                        for c in w.winfo_children():
                            c.configure(bg=row_bg, fg=fg)
                            if isinstance(c, tk.Label):
                                testo_c = c.cget("text")
                                if testo_c in ("●", "▲"):
                                    c.configure(fg=("#ffb020" if testo_c == "▲" else fg))
                    elif isinstance(w, tk.Label): w.configure(bg=row_bg, fg=fg)
                except tk.TclError: pass
            # Indicatori e numeri colorati per lettura immediata.
            for key, count_label in getattr(self, "old_summary_counts", {}).items():
                try: count_label.configure(fg=colori_riepilogo.get(key, fg), bg=row_bg)
                except tk.TclError: pass
            for key, symbol_label in getattr(self, "legenda_simboli", []):
                if symbol_label.master == self.panel_old_summary or symbol_label.master.master == self.panel_old_summary:
                    try: symbol_label.configure(fg=colori_riepilogo.get(key, fg), bg=row_bg)
                    except tk.TclError: pass
        if hasattr(self, "panel_summary"):
            self.panel_summary.configure(bg=card_bg, highlightbackground=card_border)
            for w in self.panel_summary.winfo_children():
                try:
                    if isinstance(w, tk.Frame):
                        w.configure(bg=card_bg)
                        for c in w.winfo_children(): c.configure(bg=card_bg, fg=fg)
                    elif isinstance(w, tk.Label): w.configure(bg=card_bg, fg=fg)
                except tk.TclError: pass
        # Simboli della legenda con gli stessi colori usati negli alberi.
        colori_legenda = {"identici": t["ok"], "diversi": t["diverso"], "mancanti": t["mancante"]}
        try:
            self.old_size_legend.configure(fg="#fdba74" if dark else "#c2410c")
        except (tk.TclError, AttributeError):
            pass
        try:
            # La voce esplicativa indica il colore arancione usato per le differenze di dimensione.
            for widget in self.panel_summary.winfo_children():
                if isinstance(widget, tk.Label) and "Dimensione file diversa" in widget.cget("text"):
                    widget.configure(fg="#fdba74" if dark else "#c2410c")
        except tk.TclError:
            pass
        try:
            for widget in self.panel_summary.winfo_children():
                if isinstance(widget, tk.Label) and "Solo data diversa" in widget.cget("text"):
                    widget.configure(fg="#7dd3fc" if dark else "#0369a1")
        except tk.TclError:
            pass
        for key, simbolo_lbl in getattr(self, "legenda_simboli", []):
            try:
                simbolo_lbl.configure(fg=colori_legenda[key])
            except tk.TclError:
                pass

        # Sfondo e tipografia coerenti anche per i contenitori annidati.
        def _stila_discendenti(parent):
            for widget in parent.winfo_children():
                # I pannelli riepilogo hanno colori della legenda: non sovrascriverli.
                if widget in (getattr(self, "panel_summary", None), getattr(self, "panel_old_summary", None)):
                    continue
                try:
                    if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                        widget.configure(bg=bg)
                        if isinstance(widget, tk.LabelFrame):
                            if modern:
                                widget.configure(fg=muted, font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                                                 highlightthickness=1, highlightbackground=card_border,
                                                 highlightcolor=card_border)
                            else:
                                widget.configure(fg=fg, font=("Segoe UI", 10, "bold"),
                                                 highlightbackground="#3b4b60" if dark else "#d7dee8")
                    elif isinstance(widget, tk.Label):
                        if widget in (getattr(self, "lbl_sorgente", None), getattr(self, "lbl_destinazione", None)):
                            # Il font è definito una sola volta alla creazione del widget.
                            widget.configure(bg=bg, fg=fg)
                        else:
                            widget.configure(bg=bg, fg=fg, font=("Segoe UI", 10))
                    elif isinstance(widget, tk.Button):
                        # I pulsanti principali hanno caratteri e spaziatura maggiori;
                        # gli altri pulsanti mantengono le dimensioni compatte.
                        pulsanti_principali = (
                            getattr(self, "btn_avvia", None), getattr(self, "btn_refresh", None),
                            getattr(self, "btn_espandi", None),
                            getattr(self, "btn_stop", None), getattr(self, "btn_copia_tutto", None),
                            getattr(self, "btn_sincronizza", None), getattr(self, "btn_anteprima", None),
                            getattr(self, "btn_spazio", None),
                        )
                        principale = widget in pulsanti_principali
                        widget.configure(
                            font=("Segoe UI", 12 if principale else 9, "bold"),
                            relief="flat", bd=0,
                            padx=max(16 if principale else 8, int(widget.cget("padx"))),
                            pady=max(9 if principale else 5, int(widget.cget("pady"))),
                            cursor="hand2", activeforeground="white", takefocus=True
                        )
                    elif isinstance(widget, PulsanteArrotondato):
                        widget.aggiorna_sfondo()
                        if widget is getattr(self, "btn_filtra", None):
                            widget.configure(font=("Segoe UI", 9, "bold"),
                                             padx=max(8, int(widget.cget("padx"))),
                                             pady=max(5, int(widget.cget("pady"))))
                        else:
                            widget.configure(font=("Segoe UI", 12, "bold"),
                                             padx=max(16, int(widget.cget("padx"))),
                                             pady=max(9, int(widget.cget("pady"))))
                    elif isinstance(widget, tk.Entry):
                        widget.configure(font=("Segoe UI", 10), relief="flat", bd=0,
                                         highlightthickness=1,
                                         highlightbackground="#526174" if dark else "#cbd5e1",
                                         highlightcolor=accent)
                except (tk.TclError, TypeError, ValueError):
                    pass
                _stila_discendenti(widget)
        _stila_discendenti(self.root)
        # Campi cartella e ricerca.
        for combo in (self.combo_c1, self.combo_c2):
            self.style.configure("TCombobox", fieldbackground=t["entry_bg"],
                                 background=t["entry_bg"], foreground=fg,
                                 arrowcolor=fg, arrowsize=24, padding=(8, 6))
            self.style.map("TCombobox", fieldbackground=[("readonly", t["entry_bg"])],
                           foreground=[("readonly", fg)])
        self.style.configure("Search.TEntry", fieldbackground=t["entry_bg"],
                             foreground=fg, insertcolor=fg, padding=(8, 2),
                             borderwidth=1, relief="flat")
        self.style.map("Search.TEntry", fieldbackground=[("readonly", t["entry_bg"])],
                       foreground=[("disabled", fg)])

        # Barre e tabelle con più contrasto, spaziatura e selezione evidente.
        self.style.configure("Green.Horizontal.TProgressbar", troughcolor=t["tree_bg"],
                             background="#10b981", bordercolor=bg,
                             lightcolor="#10b981", darkcolor="#10b981", thickness=12)
        # Barra di avanzamento blu dedicata alla copia da 1 a 2 / da 2 a 1.
        self.style.configure("BlueCopy.Horizontal.TProgressbar", troughcolor=t["tree_bg"],
                             background="#2589ff", bordercolor=bg,
                             lightcolor="#2589ff", darkcolor="#2589ff", thickness=12)
        self.style.configure("Treeview", background=t["tree_bg"], foreground=t["tree_fg"],
                             fieldbackground=t["tree_bg"], rowheight=29, borderwidth=0,
                             font=("Segoe UI", 10), padding=(3, 2))
        self.style.map("Treeview", background=[("selected", accent)],
                       foreground=[("selected", "#ffffff")])
        self.style.configure("Treeview.Heading",
                             background="#334155" if dark else "#e2e8f0",
                             foreground="#f8fafc" if dark else "#1e293b",
                             font=("Segoe UI", 9, "bold"), padding=(9, 9), relief="flat")
        self.style.map("Treeview.Heading", background=[("active", "#475569" if dark else "#cbd5e1")])
        self.style.configure("TScrollbar", background="#475569" if dark else "#cbd5e1",
                             troughcolor=bg, bordercolor=bg, arrowcolor=fg)
        # Widget ttk usati nelle finestre secondarie (Frame, Label, Checkbutton, Button, Separator).
        for nome_stile in ("TFrame", "TLabelframe"):
            self.style.configure(nome_stile, background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg)
        self.style.configure("TCheckbutton", background=bg, foreground=fg)
        self.style.map("TCheckbutton", background=[("active", bg)], foreground=[("disabled", muted)])
        self.style.configure("TSeparator", background=card_border)
        self.style.configure("TButton", background=t["entry_bg"], foreground=fg, bordercolor=card_border,
                             lightcolor=t["entry_bg"], darkcolor=t["entry_bg"], focuscolor=accent,
                             padding=(12, 6), relief="flat")
        self.style.map("TButton", background=[("active", card_border)], foreground=[("disabled", muted)])
        if modern:
            # Look moderno: righe alte e arieggiate, intestazioni piatte, campi con bordo sottile
            # che si colora d'accento al focus, barra di avanzamento sottile.
            self.style.configure("Treeview", rowheight=32, font=("Segoe UI", 10), padding=(4, 2),
                                 bordercolor=card_border, lightcolor=t["tree_bg"], darkcolor=t["tree_bg"])
            self.style.configure("Treeview.Heading", background=card_bg, foreground=muted,
                                 font=("Segoe UI", 9, "bold"), padding=(12, 10), relief="flat",
                                 bordercolor=card_border, lightcolor=card_bg, darkcolor=card_bg)
            self.style.map("Treeview.Heading", background=[("active", card_border)],
                           foreground=[("active", fg)])
            self.style.configure("TScrollbar", background=card_border, troughcolor=bg, bordercolor=bg,
                                 lightcolor=bg, darkcolor=bg, arrowcolor=muted, relief="flat", gripcount=0)
            self.style.map("TScrollbar", background=[("active", muted)])
            self.style.configure("Green.Horizontal.TProgressbar", troughcolor=card_border, background=accent,
                                 bordercolor=bg, lightcolor=accent, darkcolor=accent, thickness=6)
            self.style.configure("TCombobox", bordercolor=card_border, lightcolor=t["entry_bg"],
                                 darkcolor=t["entry_bg"], arrowsize=16, padding=(10, 7))
            self.style.map("TCombobox", bordercolor=[("focus", accent)], lightcolor=[("focus", accent)],
                           darkcolor=[("focus", accent)])
            self.style.configure("Search.TEntry", bordercolor=card_border, lightcolor=t["entry_bg"],
                                 darkcolor=t["entry_bg"], padding=(10, 4))
            self.style.map("Search.TEntry", bordercolor=[("focus", accent)], lightcolor=[("focus", accent)],
                           darkcolor=[("focus", accent)])
            self.root.option_add("*TCombobox*Listbox.background", t["entry_bg"])
            self.root.option_add("*TCombobox*Listbox.foreground", fg)
            self.root.option_add("*TCombobox*Listbox.selectBackground", accent)
            self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

        fnt_stato = ("Segoe UI", 13, "bold") if modern else ("Arial", 14, "bold")
        fnt_dim = ("Segoe UI", 10, "bold") if modern else ("Arial", 11, "bold")
        fg_dim = muted if modern else fg
        self.lbl_status.configure(bg=bg, fg=fg, font=fnt_stato)
        self.lbl_dimensione_c1.configure(bg=bg, fg=fg_dim, font=fnt_dim)
        self.lbl_dimensione_c2.configure(bg=bg, fg=fg_dim, font=fnt_dim)
        for frame in (self.frame_tree1, self.frame_tree2):
            frame.configure(bg=bg, fg=(muted if modern else fg),
                            highlightbackground=(card_border if modern else ("#3b4b60" if dark else "#d7dee8")),
                            highlightthickness=1)
        # Evidenziazione differenze: colore del testo + sfondo tenue, così lo stato
        # resta immediatamente riconoscibile anche con elenchi molto lunghi.
        if dark:
            sfondo_mancante = "#4a252b"
            sfondo_dimensione = "#665500"  # giallo scuro: dimensione diversa
            sfondo_nuova = "#14532d"       # verde scuro: data più recente
            sfondo_vecchia = "#633b16"     # arancione scuro: data più vecchia
            sfondo_ok = t["tree_bg"]
            testo_dimensione = "#fde047"
            testo_nuova = "#86efac"
            testo_vecchia = "#fdba74"
        else:
            sfondo_mancante = "#ffe4e6"
            sfondo_dimensione = "#fef08a"  # giallo tenue: dimensione diversa
            sfondo_nuova = "#dcfce7"       # verde tenue: data più recente
            sfondo_vecchia = "#ffedd5"     # arancione tenue: data più vecchia
            sfondo_ok = t["tree_bg"]
            testo_dimensione = "#854d0e"
            testo_nuova = "#166534"
            testo_vecchia = "#c2410c"
        if modern:
            # Evidenziazioni più tenui: tinta morbida + testo leggibile.
            if dark:
                sfondo_mancante, sfondo_dimensione, sfondo_nuova, sfondo_vecchia = "#34202a", "#352e17", "#142e26", "#35271a"
                testo_dimensione, testo_nuova, testo_vecchia = "#fcd34d", "#6ee7b7", "#fdba74"
            else:
                sfondo_mancante, sfondo_dimensione, sfondo_nuova, sfondo_vecchia = "#fee2e2", "#fef3c7", "#d1fae5", "#ffedd5"
                testo_dimensione, testo_nuova, testo_vecchia = "#92400e", "#065f46", "#c2410c"
        for tree in (self.tree1, self.tree2):
            tree.tag_configure("mancante", foreground=("#ff4d4f" if not dark else "#ff7375"), background=sfondo_mancante)
            # Presente solo nella sorgente: testo azzurro, nessuno sfondo colorato.
            tree.tag_configure("mancante_sorgente", foreground=("#0369a1" if not dark else "#7dd3fc"), background=t["tree_bg"])
            # Dimensione diversa = giallo.
            tree.tag_configure("diverso", foreground=testo_dimensione, background=sfondo_dimensione)
            # La data più recente è verde; quella più vecchia è arancione.
            tree.tag_configure("data_diversa", foreground=testo_vecchia, background=sfondo_vecchia)
            tree.tag_configure("data_piu_nuova", foreground=testo_nuova, background=sfondo_nuova)
            tree.tag_configure("data_piu_vecchia", foreground=testo_vecchia, background=sfondo_vecchia)
            tree.tag_configure("cartella_ok", foreground=t["ok"], background=sfondo_ok)
            # Riga "alternata": stesso aspetto, sfondo appena più marcato (3-5%).
            tree.tag_configure("cartella_ok_alt", foreground=t["ok"],
                               background=_mescola_colori(sfondo_ok, t["fg"], 0.05 if dark else 0.035))
            # Le differenze di data non colorano più le cartelle.
            tree.tag_configure("cartella_diff", foreground=t["tree_fg"], background=t["tree_bg"])
            # Cartella presente su entrambi i lati ma con almeno un file mancante:
            # arancione; il singolo file mancante resta rosso.
            tree.tag_configure("cartella_file_mancante", foreground=("#d97706" if not dark else "#fdba74"), background=t["tree_bg"])
        tema_label = {
            "dark": "◐ Tema: Scuro ▾", "light": "◐ Tema: Chiaro ▾",
            "blue": "◐ Tema: Blu ▾", "green": "◐ Tema: Verde ▾",
            "purple": "◐ Tema: Viola ▾", "darkgray": "◐ Tema: Grigio scuro ▾",
            "modern": "◐ Tema: Moderno scuro ▾", "modern_light": "◐ Tema: Moderno chiaro ▾"
        }.get(self.current_theme, "◐ Tema ▾")
        self.btn_tema.configure(
            text=tema_label,
            bg="#475569" if dark else "#2563eb", fg="white",
            activebackground="#64748b" if dark else "#1d4ed8",
            activeforeground="white")
        moderno_attivo = getattr(self, "stile_pulsanti", 1) == 7
        if moderno_attivo:
            self._applica_stile_pulsanti_moderno()
        self._stile_barra_secondaria(moderno_attivo)
        self._stila_finestre_aperte()
        self.root.after_idle(self._uniforma_altezza_pulsante_filtra)

    def cambia_lingua(self):
        """Alterna le etichette principali dell'interfaccia tra italiano e inglese."""
        it_en = {
            "◐ Tema ▾": "◐ Theme ▾", "◐ Tema: Scuro ▾": "◐ Theme: Dark ▾", "◐ Tema: Chiaro ▾": "◐ Theme: Light ▾",
            "◐ Tema: Classico v66 ▾": "◐ Theme: Classic v66 ▾",
            "☾  Tema scuro": "☾  Dark theme", "☼  Tema chiaro": "☼  Light theme",
            "☾  Tema scuro (default)": "☾  Dark theme (default)", "🔵  Tema blu": "🔵  Blue theme",
            "🟢  Tema verde": "🟢  Green theme", "🟣  Tema viola": "🟣  Purple theme",
            "◼  Tema grigio scuro": "◼  Dark gray theme",
            "✦  Moderno scuro": "✦  Modern dark", "✧  Moderno chiaro": "✧  Modern light",
            "◐ Tema: Moderno scuro ▾": "◐ Theme: Modern dark ▾", "◐ Tema: Moderno chiaro ▾": "◐ Theme: Modern light ▾",
            "Pronto per la scansione": "Ready to scan",
            "Confronto completato!": "Comparison complete!",
            "Confronto completato": "Comparison complete",
            "Scansione in corso…": "Scan in progress…",
            "Sorgente: in attesa della scansione": "Source: waiting to scan",
            "Da confrontare: in attesa della scansione": "Target: waiting to scan",
            "file": "files", "directory": "folders", "byte": "bytes",
            "Spazio libero": "Free space",
            "▶ Confronta": "▶ Compare", "↻ Aggiorna": "↻ Refresh",
            "≠ Solo mancanti": "≠ Differences only", "≠ Solo differenze": "≠ Differences only", "＋ Espandi": "＋ Expand",
            "− Comprimi": "− Collapse", "■ STOP SCANSIONE": "■ STOP SCAN",
            "⇢ Copia modifiche": "⇢ Copy changes", "◉ Anteprima": "◉ Preview",
            "▣ Spazio libero": "▣ Free space", "⛃  File da escludere": "⛃  Files to exclude", "Filtra": "Filter",
            "FILTRA NOME:": "FILTER NAME:",
            "  SORGENTE  ": "  SOURCE  ", "  DESTINAZIONE  ": "  DESTINATION  ",
            "Nome del File / Sottocartella": "File / Subfolder name", "Dimensione": "Size",
            "Ultima Modifica": "Last modified", "⌕ Apri percorso file": "⌕ Open file location",
            "⇢ Copia da 1 a 2": "⇢ Copy from 1 to 2", "⇠ Copia da 2 a 1": "⇠ Copy from 2 to 1",
            "✎ Rinomina": "✎ Rename", "× Elimina": "× Delete",
            "🛡 Ripara permessi (amministratore)": "🛡 Repair permissions (administrator)",
            "RIEPILOGO FILE/DIRECTORY": "FILE/DIRECTORY SUMMARY", "RIEPILOGO": "SUMMARY", "Legenda confronto": "Comparison legend",
            "Elementi identici": "Identical items", "Elementi diversi": "Different items",
            "Elementi mancanti": "Missing items", "In attesa del confronto": "Waiting for comparison",
            "Risultati:": "Results:", "Uguali:": "Identical:", "Mancanti:": "Missing:",
            "Dimensione diversa:": "Different size:", "Data più recente:": "Newer date:",
            "Data più vecchia:": "Older date:", "Bianco = file uguali": "White = identical files",
            "Giallo = dimensione diversa": "Yellow = different file size",
            "Verde = data più recente": "Green = newer modification date",
            "Arancione = data più vecchia": "Orange = older modification date",
            "Rosso = file mancanti": "Red = missing files",
            "DIMENSIONI": "SIZES", "Sorgente\nIn attesa": "Source\nWaiting",
            "Da confrontare\nIn attesa": "Target\nWaiting",
            "Suggerimento\nSeleziona un elemento per usare copia, rinomina o elimina.": "Tip\nSelect an item to copy, rename or delete.",
            "Sorgente": "Source", "Destinazione": "Destination",
            "⚙  Stile pulsanti": "⚙  Button style", "◐  Menu temi  ▾": "◐  Themes  ▾",
            "⚙  Impostazioni ▾": "⚙  Settings ▾", "◐  Temi": "◐  Themes",
            "🎨  Stile pulsanti": "🎨  Button style", "🌐  Lingua / Language": "🌐  Language",
            "★  Profili ▾": "★  Profiles ▾",
            "📁  Sincronizza dentro una cartella con il nome della sorgente": "📁  Sync into a folder named like the source",
            "◐  Temi": "◐  Themes", "Stile pulsanti": "Button style",
            "Confronto e visualizzazione": "Comparison and display", "Copia e sicurezza": "Copy and safety",
            "Ricerca": "Search", "● Solo mancanti": "● Missing only",
            "■ Stop scansione": "■ Stop scan", "⇢ Sincronizza 1 → 2": "⇢ Sync 1 → 2",
            " Struttura Cartella 1 (Sorgente) ": " Folder structure 1 (Source) ",
            " Struttura Cartella 2 (Destinazione) ": " Folder structure 2 (Destination) ",
            "  SORGENTE  ": "  SOURCE  ", "  DESTINAZIONE  ": "  DESTINATION  ",
            "● Dimensione file diversa (giallo)": "● Different file size (yellow)",
            "● Data più recente (verde)": "● Newer date (green)",
            "● Data più vecchia (arancione)": "● Older date (orange)",
            "● File mancante (rosso)": "● Missing file (red)",
            "Cronologia": "History", "Successo": "Success", "Attenzione": "Warning",
            "Errore": "Error", "Nome non valido": "Invalid name", "Nome già esistente": "Name already exists",
            "Vuoi cancellare tutte le ultime cartelle utilizzate?": "Do you want to clear the history of recently used folders?",
            "Cronologia cartelle eliminata!": "Folder history cleared!",
            "Seleziona un file o una cartella.": "Select a file or folder.",
            "Inserisci un nome file o cartella valido, senza percorsi.": "Enter a valid file or folder name, without path separators.",
            "Esiste già un file o una cartella con questo nome.": "A file or folder with this name already exists.",
        }
        en_it = {v: k for k, v in it_en.items()}
        mapping = it_en if self.lingua == "it" else en_it
        self.lingua = "en" if self.lingua == "it" else "it"
        def aggiorna(widget):
            try:
                for prop in ("text",):
                    valore = widget.cget(prop)
                    if valore in mapping:
                        widget.configure(**{prop: mapping[valore]})
            except (tk.TclError, TypeError):
                pass
            for child in widget.winfo_children():
                aggiorna(child)
        aggiorna(self.root)
        for menu in (self.menu_impostazioni, self.menu_tema, self.menu_mouse):
            try:
                ultimo = menu.index("end")
            except tk.TclError:
                continue
            for i in range((ultimo if ultimo is not None else -1) + 1):
                # Le voci separatore non hanno "label": gestite una per una.
                try:
                    label = menu.entrycget(i, "label")
                    if label in mapping:
                        menu.entryconfigure(i, label=mapping[label])
                except (tk.TclError, TypeError):
                    pass
        for tree in (self.tree1, self.tree2):
            for col in ("#0", "size", "modified"):
                label = tree.heading(col, "text")
                # Mantiene l'indicatore di ordinamento se presente.
                suffisso = label[-1] if label.endswith((" ▲", " ▼")) else ""
                base = label[:-2] if suffisso else label
                if base in mapping:
                    tree.heading(col, text=mapping[base] + (" " + suffisso if suffisso else ""))
        self._aggiorna_testi_albero_per_lingua()
        self.btn_lingua.configure(text="🇮🇹 Italiano" if self.lingua == "en" else "🇬🇧 English")
        self.root.title(f"File/Dir Compare & Sync by Roby 77 - {APP_VERSION}" + (" - English" if self.lingua == "en" else " - Italiano"))

        # Le etichette del riepilogo vengono composte dinamicamente dopo la scansione
        # e quindi non sono intercettate dalla traduzione delle etichette statiche.
        # Aggiornarle esplicitamente quando si cambia lingua, senza rifare la scansione.
        if getattr(self, "_confronto_eseguito", False):
            try:
                d1 = self._recupera_cache_per_percorso(self.safe_combobox_get(self.combo_c1))
                d2 = self._recupera_cache_per_percorso(self.safe_combobox_get(self.combo_c2))
                self._aggiorna_dimensioni_totali(d1, d2)
                self.summary_status.config(text=self._t(
                    f"Confronto completato\n{len(d1)} elementi sorgente · {len(d2)} destinazione\nNota: un file può avere sia dimensione sia data diverse.",
                    f"Comparison complete\n{len(d1)} source items · {len(d2)} target items\nNote: a file may differ in both size and date."
                ))
                self.old_summary_status.config(text=self._t(
                    f"Confronto completato · {len(d1)} elementi sorgente / {len(d2)} destinazione · i conteggi dimensione/data sono indipendenti",
                    f"Comparison complete · {len(d1)} source items / {len(d2)} target items · size/date counts are independent"
                ))
                if not self.lbl_status.in_avviso():
                    self.lbl_status.config(text=self._t("Confronto completato!", "Comparison complete!"))
            except (tk.TclError, AttributeError, TypeError):
                pass

    def _aggiorna_testi_albero_per_lingua(self):
        """Dopo un cambio di lingua: traduce i testi composti durante il confronto
        («File mancante», «[CARTELLA MANCANTE]») senza rifare la scansione."""
        nuovo = self._t("File mancante", "Missing file")
        da_sostituire = {"File mancante", "Missing file"} - {nuovo}
        for tree in (self.tree1, self.tree2):
            try:
                pila = [""]
                while pila:
                    genitore = pila.pop()
                    for item in tree.get_children(genitore):
                        valori = tree.item(item, "values")
                        if valori and str(valori[0]) in da_sostituire:
                            tree.set(item, "size", nuovo)
                        pila.append(item)
            except tk.TclError:
                pass
        self._adatta_etichette_cartelle_mancanti()

    def _ie(self, tree, item, exp=True):
        tree.item(item, open=exp)
        for c in tree.get_children(item): self._ie(tree, c, exp)

    def _ci_sono_cartelle_espanso(self):
        """True solo quando tutte le cartelle espandibili di entrambi gli alberi sono aperte."""
        trovata_cartella_espandibile = False

        def tutte_aperte(tree, parent=""):
            nonlocal trovata_cartella_espandibile
            for item in tree.get_children(parent):
                figli = tree.get_children(item)
                if figli:
                    trovata_cartella_espandibile = True
                    if not tree.item(item, "open"):
                        return False
                if not tutte_aperte(tree, item):
                    return False
            return True

        return (tutte_aperte(self.tree1) and tutte_aperte(self.tree2)
                and trovata_cartella_espandibile)

    def _aggiorna_pulsante_espandi_comprimi(self, event=None):
        """Mostra Comprimi soltanto quando tutte le cartelle espandibili sono aperte."""
        try:
            espanso = self._ci_sono_cartelle_espanso()
            if getattr(self, "stile_pulsanti", 1) == 7:
                self.btn_espandi.config(text="− Comprimi" if espanso else "＋ Espandi")
            elif espanso:
                self.btn_espandi.config(text="− Comprimi", bg="#4b5563")
                self.btn_espandi._base_bg = "#4b5563"
            else:
                self.btn_espandi.config(text="＋ Espandi", bg="#059669")
                self.btn_espandi._base_bg = "#059669"
        except (tk.TclError, AttributeError):
            pass

    def toggle_espandi_comprimi(self):
        # La decisione dipende dal comando mostrato sul pulsante, non dal fatto
        # che esista almeno una cartella aperta: dopo un confronto può esserci
        # una singola cartella già aperta, ma Espandi deve comunque espanderle tutte.
        try:
            comprimi = "Comprimi" in self.btn_espandi.cget("text") or "Collapse" in self.btn_espandi.cget("text")
        except (tk.TclError, AttributeError):
            comprimi = False
        if comprimi:
            self.comprimi_tutto()
        else:
            self.espandi_tutto()
        self._aggiorna_pulsante_espandi_comprimi()

    def espandi_tutto(self):
        for t in [self.tree1, self.tree2]:
            for i in t.get_children(''): self._ie(t, i, True)
        self._aggiorna_pulsante_espandi_comprimi()

    def comprimi_tutto(self):
        for t in [self.tree1, self.tree2]:
            for i in t.get_children(''): self._ie(t, i, False)
        self._aggiorna_pulsante_espandi_comprimi()
    def conta_elementi_totali(self, p):
        c = 0
        try:
            for r, ds, fs in os.walk(p):
                if self._cancel_scan.is_set():
                    break
                ds[:] = [d for d in ds if ".@__thumb" not in d]
                fs = [f for f in fs if ".@__thumb" not in f]
                c += len(ds) + len(fs)
        except Exception:
            pass
        return c

    def analizza_directory_fast(self, path, callback=None):
        if self._cancel_scan.is_set():
            return None
        if path in self.folder_cache:
            return self.folder_cache[path]
        # Evita un passaggio preliminare con os.walk: su dischi USB/rete
        # significava leggere due volte l'intero albero prima di mostrare i risultati.
        # La scansione unica aggiorna la barra in modo progressivo, senza un totale
        # noto in anticipo (che richiederebbe proprio quel secondo passaggio).
        struttura, stato = {}, {"l": 0}
        if self._cancel_scan.is_set():
            return None
        regole = self._regole_esclusione_compilate()
        sep = os.sep
        def _ricorsivo(cp, prefisso):
            if self._cancel_scan.is_set():
                return
            try:
                with os.scandir(cp) as it:
                    for entry in it:
                        if self._cancel_scan.is_set():
                            return
                        nome = entry.name
                        if ".@__thumb" in nome:
                            continue
                        # Percorso relativo costruito in modo incrementale: os.path.relpath
                        # (abspath + split) per ogni voce era molto costoso su alberi grandi.
                        rp = nome if not prefisso else prefisso + sep + nome
                        if regole:
                            # Le cartelle antenate sono già state controllate: basta il
                            # percorso completo e l'ultimo componente.
                            rel_cf = rp.replace("\\", "/").casefold()
                            nome_cf = nome.casefold()
                            if any(m(rel_cf) or m(nome_cf) for m in regole):
                                continue
                        stato["l"] += 1
                        if callback and stato["l"] % 100 == 0:
                            # Avanzamento indiretto: cresce senza bloccare al 100%
                            # prima che la scansione sia davvero terminata.
                            progresso = min(99.0, 100.0 * stato["l"] / (stato["l"] + 500.0))
                            callback(progresso)
                        if entry.is_dir(follow_symlinks=False):
                            struttura[rp] = {"type": "dir", "size": "", "mtime": ""}
                            _ricorsivo(entry.path, rp)
                        else:
                            try:
                                s_d = entry.stat()
                                struttura[rp] = {"type": "file", "size": s_d.st_size, "mtime": s_d.st_mtime}
                            except OSError:
                                struttura[rp] = {"type": "file", "size": 0, "mtime": 0}
            except OSError:
                pass
        _ricorsivo(path, "")
        if callback:
            callback(99.0)
        if self._cancel_scan.is_set():
            return None
        self.folder_cache[path] = struttura
        return struttura

    def _regole_esclusione_compilate(self):
        """Regole di esclusione già normalizzate e compilate (ricalcolate solo se cambiano)."""
        chiave = tuple(self.filtri_esclusione)
        if getattr(self, "_regole_escl_chiave", None) != chiave:
            compilate = []
            for regola in chiave:
                r = regola.strip().replace("\\", "/")
                if r:
                    compilate.append(re.compile(fnmatch.translate(r.casefold())).match)
            self._regole_escl = compilate
            self._regole_escl_chiave = chiave
        return self._regole_escl

    def _icona_per_file(self, nome):
        """Icona (PhotoImage, creata una sola volta per categoria) in base all'estensione."""
        categoria = EST_CATEGORIA.get(os.path.splitext(nome)[1].lower(), "generico")
        icone = self.__dict__.setdefault("_icone_file", {})
        img = icone.get(categoria)
        if img is None:
            img = tk.PhotoImage(width=ICONA_W, height=ICONA_H)
            for x0, y0, x1, y1, colore in rette_icona(categoria):
                img.put(colore, to=(x0, y0, x1, y1))
            icone[categoria] = img
        return img

    def _percorso_escluso(self, percorso_relativo):
        """True se il nome/percorso corrisponde a una regola di esclusione."""
        rel = str(percorso_relativo).replace("\\", "/").strip("/")
        parti = rel.split("/") if rel else []
        for regola in self.filtri_esclusione:
            regola = regola.strip().replace("\\", "/")
            if not regola:
                continue
            if fnmatch.fnmatchcase(rel.casefold(), regola.casefold()):
                return True
            if any(fnmatch.fnmatchcase(parte.casefold(), regola.casefold()) for parte in parti):
                return True
        return False

    def carica_filtri_da_disco(self):
        """Legge i filtri dal config condiviso; migra il vecchio file se necessario."""
        try:
            if os.path.exists(CONFIG_FILE):
                sezione = None
                filtri_config = []
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    for riga in f:
                        r = riga.rstrip("\r\n")
                        if r in ("--- C1 ---", "--- C2 ---", "--- TEMA ---"):
                            # Le sezioni successive non fanno parte dell'elenco filtri.
                            sezione = r
                        elif r == "--- FILTRI ---":
                            sezione = r
                        elif sezione == "--- FILTRI ---" and r.strip() and not r.strip().startswith("#"):
                            filtri_config.append(r.strip())
                if filtri_config:
                    self.filtri_esclusione = filtri_config
                    return
            # Migrazione compatibile: importa le regole dal vecchio file separato.
            if os.path.exists(FILTER_CONFIG_FILE):
                with open(FILTER_CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.filtri_esclusione = [r.strip() for r in f if r.strip() and not r.strip().startswith("#")]
                self.salva_cronologia_su_disco()
        except (OSError, UnicodeError):
            pass

    def salva_filtri_su_disco(self):
        """Salva cronologia e filtri insieme nel file di configurazione principale."""
        self.salva_cronologia_su_disco()

    def apri_finestra_filtra_visualizzazione(self):
        """Apre i filtri di sola visualizzazione; un solo criterio può essere attivo."""
        finestra = tk.Toplevel(self.root)
        finestra.title("Filtra visualizzazione" if self.lingua != "en" else "Filter display")
        finestra.transient(self.root)
        finestra.resizable(False, False)
        finestra.configure(padx=16, pady=12)
        finestra.geometry("410x300")

        titolo = "Filtra entrambi gli alberi" if self.lingua != "en" else "Filter both trees"
        descrizione = (
            "I filtri modificano solo ciò che viene mostrato: non cambiano i file né le operazioni di copia."
            if self.lingua != "en" else
            "Filters only change what is displayed; they do not change files or copy operations."
        )
        tk.Label(finestra, text=titolo, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 4))
        tk.Label(finestra, text=descrizione, font=("Segoe UI", 9), wraplength=375, justify="left").pack(anchor="w", pady=(0, 10))

        area = tk.Frame(finestra)
        area.pack(fill="x")
        stato_filtri = (
            ("filtro_dimensione_diversa_attivo", "Dimensione diversa", "Different size"),
            ("filtro_data_diversa_attivo", "Data diversa", "Different date"),
            ("filtro_mancanti_attivo", "File mancanti", "Missing files"),
            ("filtro_nomi_simili_attivo", "Nomi simili (copie, (1), maiuscole)", "Similar names (copies, (1), case)"),
        )
        pulsanti = {}

        def aggiorna_pulsanti():
            for attributo, it, en in stato_filtri:
                attivo = bool(getattr(self, attributo, False))
                testo = en if self.lingua == "en" else it
                pulsanti[attributo].configure(
                    text=("✓ " if attivo else "○ ") + testo,
                    bg="#0f766e" if attivo else "#475569",
                    activebackground="#115e59" if attivo else "#64748b",
                    fg="white", activeforeground="white"
                )

        def attiva(attributo):
            self._imposta_filtro_conteggio(attributo)
            aggiorna_pulsanti()

        for attributo, it, en in stato_filtri:
            pulsante = tk.Button(
                area, text=it, font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                padx=10, pady=6, cursor="hand2", anchor="w",
                command=lambda a=attributo: attiva(a)
            )
            pulsante.pack(fill="x", pady=2)
            pulsanti[attributo] = pulsante

        fondo = tk.Frame(finestra)
        fondo.pack(fill="x", pady=(10, 0))
        tk.Button(
            fondo, text=("Mostra tutto" if self.lingua != "en" else "Show all"),
            command=lambda: (self._azzera_filtri_visualizzazione(), aggiorna_pulsanti()),
            relief="flat", padx=10, pady=5
        ).pack(side="left")
        tk.Button(fondo, text=("Chiudi" if self.lingua != "en" else "Close"), command=finestra.destroy,
                  relief="flat", padx=12, pady=5).pack(side="right")
        aggiorna_pulsanti()

    def _azzera_filtri_visualizzazione(self):
        """Disattiva i filtri di confronto usati per la sola visualizzazione."""
        for nome in (
            "filtro_identici_attivo", "filtro_mancanti_attivo",
            "filtro_dimensione_diversa_attivo", "filtro_data_diversa_attivo",
            "filtro_data_recente_attivo", "filtro_data_vecchia_attivo",
            "filtro_nomi_simili_attivo",
        ):
            setattr(self, nome, False)
        self.rigenera_alberi_da_cache()

    def apri_finestra_filtri(self):
        """Gestione semplice dei filtri: aggiunta rapida, rimozione e salvataggio."""
        finestra = tk.Toplevel(self.root)
        finestra.title("File da escludere")
        finestra.transient(self.root)
        finestra.resizable(True, True)
        finestra.configure(padx=14, pady=12)
        finestra.geometry("560x430")

        tk.Label(finestra, text="File da escludere", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 3))
        tk.Label(
            finestra,
            text="Aggiungi nomi o modelli da ignorare durante scansione e copia. Esempi: Thumbs.db, *.tmp, *.log, cache",
            font=("Segoe UI", 9), justify="left", wraplength=520
        ).pack(anchor="w", pady=(0, 10))

        contenuto = tk.Frame(finestra)
        contenuto.pack(fill="both", expand=True)
        lista_frame = tk.Frame(contenuto)
        lista_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(lista_frame, orient="vertical")
        lista = tk.Listbox(lista_frame, font=("Consolas", 10), height=10, selectmode=tk.EXTENDED,
                           activestyle="dotbox", yscrollcommand=scrollbar.set, exportselection=False)
        scrollbar.config(command=lista.yview)
        lista.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        regole = list(self.filtri_esclusione)
        for regola in regole:
            lista.insert(tk.END, regola)

        inserimento = tk.Frame(finestra)
        inserimento.pack(fill="x", pady=(10, 4))
        voce = tk.StringVar()
        entry = ttk.Entry(inserimento, textvariable=voce, font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        entry.insert(0, "")

        def aggiorna_stato():
            stato.config(text=f"{lista.size()} regole")

        def aggiungi(valore=None):
            testo = (valore if valore is not None else voce.get()).strip()
            if not testo:
                return
            elementi = [lista.get(i) for i in range(lista.size())]
            if any(x.casefold() == testo.casefold() for x in elementi):
                voce.set("")
                return
            lista.insert(tk.END, testo)
            lista.selection_clear(0, tk.END)
            lista.selection_set(tk.END)
            lista.see(tk.END)
            voce.set("")
            aggiorna_stato()
            if valore is None:
                entry.focus_set()

        def rimuovi_selezionati():
            selezionati = list(lista.curselection())
            for i in reversed(selezionati):
                lista.delete(i)
            aggiorna_stato()

        entry.bind("<Return>", lambda _e: aggiungi())
        tk.Button(inserimento, text="Aggiungi", command=aggiungi, relief="flat", padx=10).pack(side="left")

        rapidi = tk.Frame(finestra)
        rapidi.pack(fill="x", pady=(3, 4))
        tk.Label(rapidi, text="Aggiunta rapida:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        for modello in ("Thumbs.db", "desktop.ini", "*.tmp", "*.log"):
            tk.Button(rapidi, text=modello, command=lambda m=modello: aggiungi(m), relief="groove", padx=5).pack(side="left", padx=2)
        tk.Button(rapidi, text="Rimuovi selezionati", command=rimuovi_selezionati, relief="flat", padx=8).pack(side="right")

        fondo = tk.Frame(finestra)
        fondo.pack(fill="x", pady=(8, 0))
        stato = tk.Label(fondo, text=f"{len(regole)} regole", anchor="w")
        stato.pack(side="left", fill="x", expand=True)

        def salva():
            nuove_regole = [lista.get(i).strip() for i in range(lista.size()) if lista.get(i).strip()]
            precedenti = self.filtri_esclusione[:]
            try:
                self.filtri_esclusione = nuove_regole
                self.salva_filtri_su_disco()
            except OSError as errore:
                self.filtri_esclusione = precedenti
                messagebox.showerror("Errore salvataggio filtri", f"Non è stato possibile salvare i filtri su disco:\n{errore}", parent=finestra)
                return
            self.folder_cache.clear()
            finestra.destroy()
            self.lbl_status.config(text="File da escludere salvati: cache invalidata. Premi Confronta per applicarli ai risultati.")

        tk.Button(fondo, text="Annulla", command=finestra.destroy, relief="flat", padx=12, pady=6).pack(side="right", padx=(6, 0))
        tk.Button(fondo, text="Salva filtri", command=salva, bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white", relief="flat", font=("Segoe UI", 10, "bold"), padx=14, pady=6, cursor="hand2").pack(side="right")
        entry.focus_set()

    def _verifica_cartelle_accessibili(self, sorgente, destinazione, consenti_destinazione_mancante=False):
        """Controlla che entrambe le cartelle siano directory leggibili prima dell'operazione.

        Con consenti_destinazione_mancante=True una destinazione che non esiste è accettata se
        esiste la cartella che la contiene; il chiamante la creerà solo dopo la conferma."""
        self._destinazione_da_creare = None
        for ruolo, percorso in (("sorgente", sorgente), ("destinazione", destinazione)):
            if (ruolo == "destinazione" and consenti_destinazione_mancante and percorso
                    and not os.path.exists(percorso)
                    and os.path.isdir(os.path.dirname(percorso))):
                self._destinazione_da_creare = percorso
                continue
            if not percorso or not os.path.isdir(percorso):
                messagebox.showerror(
                    "Cartella non disponibile",
                    f"La cartella {ruolo} non è disponibile o la rete è offline.\n\nPercorso:\n{percorso or '(non specificato)'}\n\nControlla la connessione e riprova."
                )
                return False
            try:
                # Aprire lo scanner forza un controllo reale dei permessi/accessibilità;
                # next(..., None) mantiene valido anche un percorso vuoto.
                with os.scandir(percorso) as elementi:
                    next(elementi, None)
            except OSError as errore:
                messagebox.showerror(
                    "Cartella non accessibile",
                    f"Impossibile accedere alla cartella {ruolo}. La rete potrebbe essere offline oppure mancano i permessi.\n\nPercorso:\n{percorso}\n\nDettaglio: {errore}"
                )
                return False
        return True

    def aggiorna_cartella_selezionata(self):
        """Riscansiona solo la cartella selezionata (e la corrispondente sull'altro lato)."""
        if self.is_scanning:
            messagebox.showinfo("Aggiornamento", "Attendi il completamento dell'operazione in corso.")
            return
        tree = getattr(self, "albero_attivo", None)
        selezione = tree.selection() if tree in (self.tree1, self.tree2) else ()
        if not selezione:
            messagebox.showinfo("Aggiornamento", "Seleziona prima una cartella o un file nell'albero.")
            return
        item = selezione[0]
        rel_item = self.ricava_chiave_relativa(tree, item)
        # Per un file aggiorna la cartella che lo contiene; per una cartella aggiorna quella stessa.
        is_dir = os.path.isdir(self.ricava_percorso_reale(tree, item))
        if is_dir:
            rel_dir = rel_item
        else:
            rel_dir = os.path.dirname(rel_item)
        rel_dir = rel_dir or ""
        c1, c2 = self.safe_combobox_get(self.combo_c1), self.safe_combobox_get(self.combo_c2)
        if not self._verifica_cartelle_accessibili(c1, c2):
            return
        # Un refresh parziale può aggiornare un ramo solo se esiste già una
        # fotografia completa delle due radici. Altrimenti partirebbe da cache
        # vuote e mostrerebbe un albero incompleto.
        if c1 not in self.folder_cache or c2 not in self.folder_cache:
            self.avvia_confronto()
            return
        self.is_scanning = True
        self.lbl_status.config(text=f"Aggiornamento della cartella: {rel_dir or os.path.basename(c1)}…")
        self.btn_stop.config(state="normal")
        self._cancel_scan.clear()
        threading.Thread(target=self._worker_aggiorna_sottocartella,
                         args=(c1, c2, rel_dir), daemon=True).start()

    def _worker_aggiorna_sottocartella(self, c1, c2, rel_dir):
        """Aggiorna in cache soltanto il ramo richiesto, senza riscanalizzare le radici."""
        try:
            def scan_subtree(root, rel):
                base = os.path.join(root, rel) if rel else root
                result = {}
                if not os.path.isdir(base):
                    return result
                def walk(folder):
                    if self._cancel_scan.is_set():
                        return
                    try:
                        with os.scandir(folder) as entries:
                            for entry in entries:
                                if self._cancel_scan.is_set():
                                    return
                                rel_full = os.path.relpath(entry.path, root)
                                if ".@__thumb" in entry.name or self._percorso_escluso(rel_full):
                                    continue
                                try:
                                    if entry.is_dir(follow_symlinks=False):
                                        result[rel_full] = {"type": "dir", "size": "", "mtime": ""}
                                        walk(entry.path)
                                    else:
                                        st = entry.stat()
                                        result[rel_full] = {"type": "file", "size": st.st_size, "mtime": st.st_mtime}
                                except OSError:
                                    continue
                    except OSError:
                        pass
                walk(base)
                return result

            nuovi1 = scan_subtree(c1, rel_dir)
            nuovi2 = scan_subtree(c2, rel_dir)
            # Conserva anche il nodo della cartella selezionata: scan_subtree
            # elenca i contenuti ma non inserisce la cartella base stessa.
            if rel_dir:
                for root, nuovi in ((c1, nuovi1), (c2, nuovi2)):
                    base_selezionata = os.path.join(root, rel_dir)
                    if os.path.isdir(base_selezionata):
                        nuovi[rel_dir] = {"type": "dir", "size": "", "mtime": ""}
            if self._cancel_scan.is_set():
                self.root.after(0, self._scansione_annullata)
                return
            def mostra():
                try:
                    # Conserva la posizione verticale prima del ridisegno:
                    # ricostruire gli alberi e chiamare see() su entrambi i lati
                    # può spostare la vista lontano dall'albero sotto il puntatore.
                    vista1_prima = self.tree1.yview()
                    vista2_prima = self.tree2.yview()
                    d1 = dict(self.folder_cache.get(c1, {}))
                    d2 = dict(self.folder_cache.get(c2, {}))
                    pref = rel_dir + os.sep if rel_dir else ""
                    for data in (d1, d2):
                        for k in list(data):
                            if (k == rel_dir and rel_dir) or (pref and k.startswith(pref)) or (not rel_dir):
                                data.pop(k, None)
                    d1.update(nuovi1)
                    d2.update(nuovi2)
                    self.folder_cache[c1] = d1
                    self.folder_cache[c2] = d2
                    self._aggiorna_dimensioni_totali(d1, d2)
                    self._elabora_e_disegna_risultati(d1, d2)
                    # Il ridisegno ricrea gli alberi chiusi: riapri il ramo
                    # aggiornato su entrambi i lati e portalo in vista, così
                    # i file con date/dimensioni differenti non sembrano spariti.
                    if rel_dir:
                        def trova_nodo(tree, relativo):
                            parent = ""
                            nodo = None
                            for parte in relativo.split(os.sep):
                                nodo = next((x for x in tree.get_children(parent)
                                             if tree.item(x, "text") == parte), None)
                                if nodo is None:
                                    return None
                                if parent:
                                    tree.item(parent, open=True)
                                parent = nodo
                            return nodo
                        for tree in (self.tree1, self.tree2):
                            nodo = trova_nodo(tree, rel_dir)
                            if nodo:
                                tree.item(nodo, open=True)
                                tree.selection_set(nodo)
                                tree.focus(nodo)
                    # Ripristina la posizione precedente su ciascun albero.
                    # Non usare tree.see(nodo): obbliga la vista a saltare al nodo
                    # selezionato e può sembrare che la rotellina muova l'albero sbagliato.
                    try:
                        self.tree1.yview_moveto(vista1_prima[0])
                        self.tree2.yview_moveto(vista2_prima[0])
                    except (tk.TclError, IndexError, TypeError):
                        pass
                    self.lbl_status.config(text=f"Cartella aggiornata: {rel_dir or c1}")
                except Exception as exc:
                    raise
                finally:
                    self.is_scanning = False
                    self.btn_avvia.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    for b in (self.btn_refresh, self.btn_espandi):
                        b.config(state="normal")
            self.root.after(0, mostra)
        except Exception as errore:
            self.root.after(0, lambda e=str(errore): self._errore_scansione(e))

    def _albero_sotto_puntatore(self, event):
        """Restituisce l'albero sotto il puntatore, anche sopra la scrollbar."""
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
            while widget is not None:
                if widget is self.tree1 or widget is self.tree2:
                    return widget
                widget = getattr(widget, "master", None)
        except (tk.TclError, AttributeError):
            pass
        return None

    def _scroll_rotellina_globale(self, event):
        """Instrada la rotellina all’albero sotto il puntatore."""
        tree = self._albero_sotto_puntatore(event)
        focus = self.root.focus_get()
        if tree is None:
            return None
        try:
            delta = int(event.delta)
            if not delta:
                return "break"
            # Dopo il refresh il Treeview può non avere più il focus Tk corretto.
            # Riattiva l'albero realmente sotto il puntatore prima di scorrere,
            # come avviene implicitamente quando l'utente preme una freccia.
            try:
                tree.focus_set()
            except tk.TclError:
                pass
            unita = max(1, abs(delta) // 120) * 3  # 3 righe per scatto, come il default di Windows
            tree.yview_scroll(-unita if delta > 0 else unita, "units")
        except (AttributeError, TypeError, ValueError, tk.TclError):
            pass
        return "break"

    def _scroll_rotellina_globale_x11(self, event, direzione):
        tree = self._albero_sotto_puntatore(event)
        if tree is None:
            return None
        try:
            try:
                tree.focus_set()
            except tk.TclError:
                pass
            tree.yview_scroll(direzione, "units")
        except tk.TclError:
            pass
        return "break"

    def _scroll_rotellina_albero(self, event, tree):
        """Scorre l'albero sotto il puntatore usando la rotellina del mouse."""
        try:
            delta = int(event.delta)
            if not delta:
                return "break"
            # Windows normalmente invia multipli di 120; macOS può inviare
            # valori più piccoli. Mantiene almeno uno scatto per evento.
            unita = max(1, abs(delta) // 120)
            tree.yview_scroll(-unita if delta > 0 else unita, "units")
        except (AttributeError, TypeError, ValueError, tk.TclError):
            pass
        return "break"

    def _scroll_rotellina_albero_x11(self, event, tree, direzione):
        """Compatibilità con eventi rotellina Button-4/5."""
        try:
            tree.yview_scroll(direzione, "units")
        except tk.TclError:
            pass
        return "break"

    def avvia_confronto(self):
        if self.is_scanning: return
        # Legge il contenuto attuale dei campi, senza sostituirlo con valori storici.
        c1 = os.path.abspath(os.path.normpath(self.safe_combobox_get(self.combo_c1))) if self.safe_combobox_get(self.combo_c1) else ""
        c2 = os.path.abspath(os.path.normpath(self.safe_combobox_get(self.combo_c2))) if self.safe_combobox_get(self.combo_c2) else ""

        # Se la sorgente salvata non esiste più, consente di selezionare quella reale
        # prima del confronto, evitando di insistere su un vecchio percorso in cronologia.
        if not c1 or not os.path.isdir(c1):
            nuovo = filedialog.askdirectory(
                parent=self.root,
                title="La sorgente non è disponibile: seleziona la cartella sorgente corretta",
                initialdir=os.path.expanduser("~"),
                mustexist=True,
            )
            if not nuovo:
                return
            c1 = os.path.normpath(os.path.abspath(nuovo))
            self.combo_c1.set(self._testo_combobox_percorso(c1))
            self.aggiungi_a_cronologia(self.cronologia_c1, self.combo_c1, c1)

        if not self._verifica_cartelle_accessibili(c1, c2):
            return
        # "Confronta" deve sempre rifare la scansione completa delle due radici.
        # L'aggiornamento parziale resta utile per rinfrescare una singola cartella,
        # ma non deve lasciare dati in cache che impediscano una nuova scansione.
        self.folder_cache.pop(c1, None)
        self.folder_cache.pop(c2, None)
        self.is_scanning = True
        self._cancel_scan.clear()
        self._avviso_dopo_confronto = None
        self.lbl_status.config(text=self._t("Scansione completa delle cartelle in corso...", "Full folder scan in progress..."))
        self.btn_avvia.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_dimensione_c1.config(text=self._t("Sorgente: calcolo dimensione...", "Source: calculating size..."), fg=self.lbl_status.cget("fg"))
        self.lbl_dimensione_c2.config(text=self._t("Da confrontare: calcolo dimensione...", "Target: calculating size..."), fg=self.lbl_status.cget("fg"))
        if hasattr(self, "summary_status"):
            self.summary_status.config(text=self._t("Scansione in corso…", "Scan in progress…"))
            for _etichetta in self.summary_counts.values(): _etichetta.config(text="…")
            self.old_summary_status.config(text=self._t("Scansione in corso…", "Scan in progress…"))
            for _etichetta in self.old_summary_counts.values(): _etichetta.config(text="…")
        if hasattr(self, "old_summary_size_left"):
            self.old_summary_size_left.config(text=self._t("Sorgente: calcolo…", "Source: calculating…"))
            self.old_summary_size_right.config(text=self._t("Destinazione: calcolo…", "Destination: calculating…"))
        for b in [self.btn_refresh, self.btn_espandi]: b.config(state="disabled")
        self.progress_bar["value"] = 0; threading.Thread(target=self._worker_confronto, args=(c1, c2), daemon=True).start()

    def annulla_scansione(self):
        """Richiede l'interruzione della scansione corrente (o della copia in background)."""
        if getattr(self, "_copia_nascosta", False):
            if messagebox.askyesno(self._t("Interrompi", "Stop"), self._t(
                    "Interrompere l'operazione in corso?\nI file già copiati restano; in una sincronizzazione non viene eliminato nulla.",
                    "Stop the running operation?\nFiles already copied are kept; a synchronization deletes nothing."), parent=self.root):
                self._interrompi_copia()
                self.btn_stop.config(state="disabled")
            return
        if self.is_scanning:
            self._cancel_scan.set()
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text=self._t("Annullamento scansione in corso…", "Cancelling scan…"))

    def forza_refresh(self): self.folder_cache.clear(); self.avvia_confronto()

    def _cerca_cache(self, percorso):
        """Scansione in cache per il percorso (anche scritto con slash diversi).
        Restituisce None se NON è in cache; un dizionario vuoto significa cartella vuota."""
        if not percorso:
            return None
        if percorso in self.folder_cache:
            return self.folder_cache[percorso]
        try:
            chiave = os.path.normcase(os.path.normpath(os.path.abspath(percorso)))
            for percorso_cache, dati in list(self.folder_cache.items()):
                try:
                    candidato = os.path.normcase(os.path.normpath(os.path.abspath(percorso_cache)))
                    if candidato == chiave:
                        return dati
                except (TypeError, ValueError, OSError):
                    continue
        except (TypeError, ValueError, OSError):
            pass
        return None

    def _recupera_cache_per_percorso(self, percorso):
        """Recupera la scansione anche se il percorso è scritto con slash diversi o senza normalizzazione."""
        dati = self._cerca_cache(percorso)
        return {} if dati is None else dati

    def rigenera_alberi_da_cache(self):
        c1, c2 = self.safe_combobox_get(self.combo_c1), self.safe_combobox_get(self.combo_c2)
        d1 = self._recupera_cache_per_percorso(c1)
        d2 = self._recupera_cache_per_percorso(c2)
        self._elabora_e_disegna_risultati(d1, d2)

    @staticmethod
    def _spazio_libero(percorso):
        """Spazio libero del volume (None se non disponibile). Può essere lento su reti/USB."""
        try:
            return shutil.disk_usage(percorso).free if percorso and os.path.exists(percorso) else None
        except (OSError, ValueError, TypeError):
            return None

    def _aggiorna_dimensioni_totali(self, d1, d2, liberi=None):
        """Mostra la dimensione complessiva dei file nelle due cartelle.

        `liberi` = (spazio libero sorgente, destinazione) già calcolato in un thread:
        evita di bloccare l'interfaccia su percorsi di rete lenti o scollegati."""
        totale1 = sum(int(v.get("size", 0) or 0) for v in d1.values() if v.get("type") == "file")
        totale2 = sum(int(v.get("size", 0) or 0) for v in d2.values() if v.get("type") == "file")
        gb1 = totale1 / (1024 ** 3)
        gb2 = totale2 / (1024 ** 3)
        files1 = sum(1 for v in d1.values() if v.get("type") == "file")
        dirs1 = sum(1 for v in d1.values() if v.get("type") == "dir")
        files2 = sum(1 for v in d2.values() if v.get("type") == "file")
        dirs2 = sum(1 for v in d2.values() if v.get("type") == "dir")
        testo_sorgente = (
            f"{self._t('Sorgente', 'Source')}: {files1:,} {self._t('file', 'files')} · "
            f"{dirs1:,} {self._t('directory', 'folders')} · "
            f"{totale1:,} {self._t('byte', 'bytes')} ({gb1:.2f} GB)"
        ).replace(",", ".")
        if liberi is not None:
            spazio_libero_sorgente = liberi[0]
        else:
            try:
                percorso_sorgente = self.safe_combobox_get(self.combo_c1)
                spazio_libero_sorgente = self._spazio_libero(percorso_sorgente)
            except AttributeError:
                spazio_libero_sorgente = None
        if spazio_libero_sorgente is not None:
            testo_sorgente += f"  |  {self._t('Spazio libero', 'Free space')}: {format_size(spazio_libero_sorgente)}"
        testo_destinazione = (
            f"{self._t('Destinazione', 'Destination')}: {files2:,} {self._t('file', 'files')} · "
            f"{dirs2:,} {self._t('directory', 'folders')} · "
            f"{totale2:,} {self._t('byte', 'bytes')} ({gb2:.2f} GB)"
        ).replace(",", ".")
        if liberi is not None:
            spazio_libero = liberi[1]
        else:
            try:
                percorso_destinazione = self.safe_combobox_get(self.combo_c2)
                spazio_libero = self._spazio_libero(percorso_destinazione)
            except AttributeError:
                spazio_libero = None
        if spazio_libero is not None:
            testo_destinazione += f"  |  {self._t('Spazio libero', 'Free space')}: {format_size(spazio_libero)}"
        # Evidenzia in arancione entrambe le dimensioni quando i totali differiscono.
        colore_dimensione = "#d97706" if totale1 != totale2 else self.lbl_status.cget("fg")
        self.lbl_dimensione_c1.config(text=testo_sorgente, fg=colore_dimensione)
        self.lbl_dimensione_c2.config(text=testo_destinazione, fg=colore_dimensione)
        if hasattr(self, "old_summary_size_left"):
            self.old_summary_size_left.config(text=f"Sorgente: {format_size(totale1)}")
            self.old_summary_size_right.config(text=f"Destinazione: {format_size(totale2)}")

    @staticmethod
    def _scansione_in_parallelo(p1, p2):
        """True se conviene scansionare le due cartelle contemporaneamente."""
        try:
            if os.path.normcase(os.path.abspath(p1)) == os.path.normcase(os.path.abspath(p2)):
                return False  # stessa cartella: una sola scansione, la seconda usa la cache
            if SCANSIONE_PARALLELA_STESSO_DISCO:
                return True
            if os.stat(p1).st_dev != os.stat(p2).st_dev:
                return True
            return False
        except OSError:
            return False

    def _worker_confronto(self, p1, p2):
        inizio_confronto = time.monotonic()
        try:
            # Avanzamento complessivo: media dei due avanzamenti, sul 90% della barra.
            avanzamento = [0.0, 0.0]
            def _cb(indice):
                def aggiorna(p):
                    avanzamento[indice] = p
                    totale = (avanzamento[0] + avanzamento[1]) / 2.0 * 0.9
                    self.root.after(0, lambda val=totale: self.progress_bar.config(value=val))
                return aggiorna
            if self._scansione_in_parallelo(p1, p2):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    f1 = pool.submit(self.analizza_directory_fast, p1, _cb(0))
                    f2 = pool.submit(self.analizza_directory_fast, p2, _cb(1))
                    # result() rilancia l'eventuale eccezione del thread; il blocco with
                    # attende comunque entrambi i thread prima di proseguire.
                    d1, d2 = f1.result(), f2.result()
            else:
                d1 = self.analizza_directory_fast(p1, _cb(0))
                if self._cancel_scan.is_set() or d1 is None:
                    self.root.after(0, self._scansione_annullata)
                    return
                d2 = self.analizza_directory_fast(p2, _cb(1))
            if self._cancel_scan.is_set() or d1 is None or d2 is None:
                self.root.after(0, self._scansione_annullata)
                return
            liberi = (self._spazio_libero(p1), self._spazio_libero(p2))
            def _mostra_risultati():
                try:
                    if self._cancel_scan.is_set():
                        self._scansione_annullata()
                        return
                    self._aggiorna_dimensioni_totali(d1, d2, liberi)
                    self._elabora_e_disegna_risultati(d1, d2)
                    if time.monotonic() - inizio_confronto >= 10:
                        self._notifica_fine_operazione()
                finally:
                    if self.is_scanning:
                        self._confronto_completato()
            self.root.after(0, _mostra_risultati)
        except Exception as errore:
            self.root.after(0, lambda e=str(errore): self._errore_scansione(e))

    def _scansione_annullata(self):
        self.is_scanning = False
        self.btn_avvia.config(state="normal")
        self.btn_stop.config(state="disabled")
        for b in [self.btn_refresh, self.btn_espandi]:
            b.config(state="normal")
        self.progress_bar["value"] = 0
        self.lbl_status.config(text="Scansione annullata. I risultati precedenti sono stati mantenuti.")

    def _errore_scansione(self, errore):
        self.is_scanning = False
        self.btn_avvia.config(state="normal")
        self.btn_stop.config(state="disabled")
        for b in [self.btn_refresh, self.btn_espandi]:
            b.config(state="normal")
        self.lbl_status.config(text=f"Errore durante la scansione: {errore}")

    def _elabora_e_disegna_risultati(self, d1, d2):
        self.tree1.delete(*self.tree1.get_children()); self.tree2.delete(*self.tree2.get_children())
        en = self.lingua == "en"
        etichetta_nome = "File / Subfolder name" if en else "Nome del File / Sottocartella"
        etichetta_dim = "Size" if en else "Dimensione"
        etichetta_mod = "Last modified" if en else "Ultima Modifica"
        testo_assente = "Missing file" if en else "File mancante"
        simbolo = " ▼" if self.sort_reverse else " ▲"
        for tree in (self.tree1, self.tree2):
            tree.heading("#0", text=etichetta_nome + (simbolo if self.sort_by == "name" else ""))
            tree.heading("size", text=etichetta_dim + (simbolo if self.sort_by == "size" else ""))
            tree.heading("modified", text=etichetta_mod + (simbolo if self.sort_by == "modified" else ""))
        
        chiavi_unite = sorted(list(set(d1.keys()) | set(d2.keys()))); stati_nodi = {}
        for k in chiavi_unite:
            if k in d1 and k not in d2: stati_nodi[k] = "mancante"
            elif k in d2 and k not in d1: stati_nodi[k] = "mancante"
            elif k in d1 and k in d2:
                if d1[k]["type"] != d2[k]["type"]:
                    stati_nodi[k] = "diverso"
                elif d1[k]["type"] == "file" and d2[k]["type"] == "file":
                    try:
                        stesso_size = int(d1[k]["size"] or 0) == int(d2[k]["size"] or 0)
                        stesso_mtime = abs(float(d1[k]["mtime"] or 0) - float(d2[k]["mtime"] or 0)) <= 2
                    except (TypeError, ValueError):
                        stesso_size, stesso_mtime = False, False
                    # Priorità cromatica del nome/riga: la dimensione ha precedenza.
                    # Se dimensione e data differiscono entrambe, il file resta giallo
                    # nell'albero; il riepilogo conta comunque entrambe le differenze.
                    # Il Treeview standard di Tkinter applica i tag all'intera riga,
                    # non alle singole celle: non è possibile colorare solo la cella
                    # della data senza sostituire il widget o creare una soluzione custom.
                    if not stesso_size:
                        stati_nodi[k] = "diverso"
                    elif not stesso_mtime:
                        stati_nodi[k] = "data_diversa"
                    else:
                        stati_nodi[k] = "cartella_ok"
                else: stati_nodi[k] = "cartella_ok"
        # Stato delle cartelle: arancione se contengono file mancanti ma la cartella
        # esiste su entrambi i lati; azzurro per differenze di dimensione/data.
        # Una cartella che manca interamente su un lato resta rossa.
        stati_cartelle = {}
        for chiave, stato in stati_nodi.items():
            parti = chiave.split(os.sep)
            cartella = ""
            for i in range(len(parti) - 1):
                cartella = parti[i] if i == 0 else cartella + os.sep + parti[i]
                precedente = stati_cartelle.get(cartella, "cartella_ok")
                if precedente == "mancante":
                    stati_cartelle[cartella] = "mancante"
                elif stato == "mancante":
                    # Il file/sott elemento manca, ma la cartella antenata sarà
                    # arancione; la presenza della cartella stessa viene verificata sotto.
                    if precedente not in ("cartella_file_mancante",):
                        stati_cartelle[cartella] = "cartella_file_mancante"
                elif stato in ("diverso", "data_diversa") or precedente in ("diverso", "data_diversa", "cartella_diff"):
                    if precedente != "cartella_file_mancante":
                        stati_cartelle[cartella] = "cartella_diff"
                else:
                    stati_cartelle.setdefault(cartella, "cartella_ok")
        # Anche una cartella presente su un solo lato è una differenza rossa.
        for chiave in chiavi_unite:
            if (chiave in d1) != (chiave in d2):
                if d1.get(chiave, {}).get("type") == "dir" or d2.get(chiave, {}).get("type") == "dir":
                    stati_cartelle[chiave] = "mancante"

        # Aggiorna il riepilogo con conteggi reali degli elementi trovati.
        if hasattr(self, "summary_counts"):
            # Conteggi per attributo, non categorie mutuamente esclusive:
            # un file con dimensione E data diverse viene contato in entrambi i conteggi.
            # In questo modo i numeri descrivono le differenze effettive senza nasconderne una.
            conteggi = {"identici": 0, "dimensione": 0, "data_vecchia": 0, "data_recente": 0, "mancanti": 0}
            for chiave, stato in stati_nodi.items():
                tipo1 = d1.get(chiave, {}).get("type")
                tipo2 = d2.get(chiave, {}).get("type")
                if tipo1 != "file" and tipo2 != "file":
                    continue
                if chiave not in d1 or chiave not in d2:
                    conteggi["mancanti"] += 1
                    continue
                if tipo1 != "file" or tipo2 != "file":
                    conteggi["dimensione"] += 1
                    continue
                try:
                    size_diff = int(d1[chiave].get("size") or 0) != int(d2[chiave].get("size") or 0)
                    m1 = float(d1[chiave].get("mtime") or 0)
                    m2 = float(d2[chiave].get("mtime") or 0)
                    date_diff = abs(m1 - m2) > 2
                except (TypeError, ValueError):
                    size_diff, date_diff, m1, m2 = True, False, 0.0, 0.0
                if size_diff:
                    conteggi["dimensione"] += 1
                if date_diff:
                    conteggi["data_vecchia" if m1 < m2 else "data_recente"] += 1
                if not size_diff and not date_diff:
                    conteggi["identici"] += 1
            for chiave, valore in conteggi.items():
                formatted = f"{valore:,}".replace(",", ".")
                if chiave in getattr(self, "old_summary_counts", {}):
                    self.old_summary_counts[chiave].config(text=formatted)
            stato_riepilogo = self._t(f"Confronto completato · {len(d1)} elementi sorgente / {len(d2)} destinazione · i conteggi dimensione/data sono indipendenti", f"Comparison complete · {len(d1)} source items / {len(d2)} target items · size/date counts are independent")
            self.summary_status.config(text=self._t(f"Confronto completato\n{len(d1)} elementi sorgente · {len(d2)} destinazione\nNota: un file può avere sia dimensione sia data diverse.", f"Comparison complete\n{len(d1)} source items · {len(d2)} target items\nNote: a file may differ in both size and date."))
            self.old_summary_status.config(text=stato_riepilogo)

        dim_cartelle1, dim_cartelle2 = {}, {}; mod_cartelle1, mod_cartelle2 = {}, {}
        for k in chiavi_unite:
            if k in d1 and d1[k]["type"] == "file":
                padre = os.path.dirname(k)
                dim_cartelle1[padre] = dim_cartelle1.get(padre, 0) + int(d1[k]["size"])
                mod_cartelle1[padre] = max(mod_cartelle1.get(padre, 0.0), float(d1[k]["mtime"]))
            if k in d2 and d2[k]["type"] == "file":
                padre = os.path.dirname(k)
                dim_cartelle2[padre] = dim_cartelle2.get(padre, 0) + int(d2[k]["size"])
                mod_cartelle2[padre] = max(mod_cartelle2.get(padre, 0.0), float(d2[k]["mtime"]))
                
        chiavi_ordinate_profondita = sorted([k for k in chiavi_unite if (k in d1 and d1[k]["type"] == "dir") or (k in d2 and d2[k]["type"] == "dir")], key=lambda x: x.count(os.sep), reverse=True)
        for k in chiavi_ordinate_profondita:
            padre = os.path.dirname(k)
            if k in dim_cartelle1:
                dim_cartelle1[padre] = dim_cartelle1.get(padre, 0) + dim_cartelle1[k]
                mod_cartelle1[padre] = max(mod_cartelle1.get(padre, 0.0), mod_cartelle1[k])
            if k in dim_cartelle2:
                dim_cartelle2[padre] = dim_cartelle2.get(padre, 0) + dim_cartelle2[k]
                mod_cartelle2[padre] = max(mod_cartelle2.get(padre, 0.0), mod_cartelle2[k])

        if self.sort_by != "name":
            def _numero(valore):
                try:
                    return float(valore or 0)
                except (TypeError, ValueError):
                    return 0.0
            def _valore_ordinamento(chiave):
                tipo1 = d1.get(chiave, {}).get("type")
                tipo2 = d2.get(chiave, {}).get("type")
                is_dir = tipo1 == "dir" or tipo2 == "dir"
                if self.sort_by == "size":
                    if is_dir: return max(dim_cartelle1.get(chiave, 0), dim_cartelle2.get(chiave, 0))
                    return max(_numero(d1.get(chiave, {}).get("size", 0)), _numero(d2.get(chiave, {}).get("size", 0)))
                else:
                    if is_dir: return max(mod_cartelle1.get(chiave, 0.0), mod_cartelle2.get(chiave, 0.0))
                    return max(_numero(d1.get(chiave, {}).get("mtime", 0.0)), _numero(d2.get(chiave, {}).get("mtime", 0.0)))
            chiavi_unite.sort(key=_valore_ordinamento, reverse=self.sort_reverse)

        m1, m2 = {}, {}
        nomi_nodi = {}  # id nodo -> nome in minuscolo, per ordinare senza interrogare Tk
        nodi_neutri, nodi_cartella = set(), set()  # righe senza differenze / nodi cartella (righe alternate)
        nodi_mancanti1, nodi_mancanti2 = {}, {}  # cartelle mancanti (sorgente / destinazione): id nodo -> (nome, etichetta, livello)
        nodi_simili1, nodi_simili2 = set(), set()   # nodi con nome simile (solo con il filtro «Nomi simili»)
        chiavi_simili = set()
        if getattr(self, "filtro_nomi_simili_attivo", False):
            chiavi_simili = trova_chiavi_nomi_simili(
                {k for dati in (d1, d2) for k, v in dati.items() if v.get("type") != "dir"})

        def _ins_file(tree, genitore, base, valori, tag, chiave=None):
            nid = tree.insert(genitore, "end", text=base, image=self._icona_per_file(base),
                              values=valori, tags=(tag,))
            if chiave is not None and chiave in chiavi_simili:
                (nodi_simili1 if tree is self.tree1 else nodi_simili2).add(nid)
            nomi_nodi[nid] = base.casefold()
            if tag == "cartella_ok":
                nodi_neutri.add(nid)
        def cn(rp, tree, mappa, ds, dims_calc, mods_calc):
            if not rp or rp in mappa: return mappa.get(rp, "")
            padre, base = os.path.split(rp); id_p = cn(padre, tree, mappa, ds, dims_calc, mods_calc)
            sz_val = dims_calc.get(rp, "")
            mt_val = mods_calc.get(rp, "")
            sz, mt = (format_size(sz_val), format_date(mt_val)) if sz_val != "" else ("", "")
            stato_cartella = stati_cartelle.get(rp, "cartella_ok")
            # Se una directory esiste nella sorgente ma manca nella destinazione,
            # la mostriamo a destra con icona cartella, tag rosso ed etichetta esplicita.
            # Simmetrico: un nodo-cartella senza una voce nei dati del SUO lato esiste nell'albero
            # solo per ospitare elementi dell'altro lato, quindi in quel pannello la cartella manca.
            directory_mancante_a_destra = (
                (tree is self.tree2 and rp not in d2)
                or (tree is self.tree1 and rp not in d1)
            )
            nome_visualizzato = base
            if directory_mancante_a_destra:
                nome_visualizzato = base + (" [MISSING FOLDER]" if en else " [CARTELLA MANCANTE]")
                # La cartella mancante è indicata nel nome, ma non deve colorare
                # di rosso l'intero sfondo del riquadro: il rosso pieno resta ai file mancanti.
                stato_cartella = "cartella_file_mancante"
            elif stato_cartella == "mancante":
                # A sinistra la directory è un contenitore di elementi da copiare:
                # arancione, mentre i singoli file mancanti restano rossi.
                stato_cartella = "cartella_file_mancante"
            nodo_id = tree.insert(
                id_p, "end", text=nome_visualizzato, image=self.folder_icon,
                values=(sz, mt), tags=(stato_cartella,)
            )
            nomi_nodi[nodo_id] = base.casefold()   # ordine per nome reale, indipendente dall'etichetta
            nodi_cartella.add(nodo_id)
            if directory_mancante_a_destra:
                # (nome reale, etichetta, livello): serve ad accorciare il nome se la colonna è stretta
                (nodi_mancanti1 if tree is self.tree1 else nodi_mancanti2)[nodo_id] = (
                    base, " [MISSING FOLDER]" if en else " [CARTELLA MANCANTE]", rp.count(os.sep))
            if stato_cartella == "cartella_ok":
                nodi_neutri.add(nodo_id)
            mappa[rp] = nodo_id; return nodo_id
            
        for k in chiavi_unite:
            padre, base = os.path.split(k); in1, in2 = k in d1, k in d2; tag_elemento = stati_nodi.get(k, "cartella_ok")
            if in1:
                if d1[k]["type"] == "dir":
                    cn(k, self.tree1, m1, d1, dim_cartelle1, mod_cartelle1)
                else:
                    ip1 = cn(padre, self.tree1, m1, d1, dim_cartelle1, mod_cartelle1)
                    tag_lato1 = tag_elemento
                    if tag_elemento == "mancante":
                        # File presente solo a sinistra: sul lato sorgente non va in rosso
                        # (il rosso resta alla riga "mancante" sul lato destinazione).
                        tag_lato1 = "mancante_sorgente"
                    if tag_elemento == "data_diversa":
                        tag_lato1 = "data_piu_nuova" if float(d1[k].get("mtime", 0) or 0) > float(d2[k].get("mtime", 0) or 0) else "data_piu_vecchia"
                    _ins_file(self.tree1, ip1, base, (format_size(d1[k]["size"]), format_date(d1[k]["mtime"])), tag_lato1, k)
            else:
                if d2.get(k, {}).get("type") == "dir":
                    # La directory assente a sinistra viene creata come nodo-cartella
                    # riutilizzabile dai figli: evita una riga duplicata senza icona.
                    cn(k, self.tree1, m1, d1, dim_cartelle1, mod_cartelle1)
                else:
                    ip1 = cn(padre, self.tree1, m1, d1, dim_cartelle1, mod_cartelle1)
                    _ins_file(self.tree1, ip1, base, (testo_assente, ""), "mancante", k)
            if in2:
                if d2[k]["type"] == "dir":
                    cn(k, self.tree2, m2, d2, dim_cartelle2, mod_cartelle2)
                else:
                    ip2 = cn(padre, self.tree2, m2, d2, dim_cartelle2, mod_cartelle2)
                    tag_lato2 = tag_elemento
                    if tag_elemento == "data_diversa":
                        tag_lato2 = "data_piu_nuova" if float(d2[k].get("mtime", 0) or 0) > float(d1[k].get("mtime", 0) or 0) else "data_piu_vecchia"
                    _ins_file(self.tree2, ip2, base, (format_size(d2[k]["size"]), format_date(d2[k]["mtime"])), tag_lato2, k)
            else:
                if d1.get(k, {}).get("type") == "dir":
                    # La directory assente a destra viene creata come nodo-cartella
                    # riutilizzabile dai figli: evita una riga duplicata senza icona.
                    cn(k, self.tree2, m2, d2, dim_cartelle2, mod_cartelle2)
                else:
                    ip2 = cn(padre, self.tree2, m2, d2, dim_cartelle2, mod_cartelle2)
                    _ins_file(self.tree2, ip2, base, (testo_assente, ""), "mancante", k)

        # In modalità nome, ordina insieme cartelle e file alfabeticamente,
        # senza dare priorità a un tipo di elemento rispetto all'altro.
        if self.sort_by == "name":
            def _ordina_alfabeticamente(tree, parent=""):
                figli = tree.get_children(parent)
                ordinati = sorted(
                    figli,
                    key=lambda item: nomi_nodi.get(item) or tree.item(item, "text").casefold(),
                    reverse=self.sort_reverse,
                )
                tree.set_children(parent, *ordinati)
                for figlio in ordinati:
                    _ordina_alfabeticamente(tree, figlio)

            _ordina_alfabeticamente(self.tree1)
            _ordina_alfabeticamente(self.tree2)

        # Righe alternate: tinta leggerissima sulle righe senza differenze, una ogni due
        # all'interno di ciascuna cartella. Le righe colorate (differenze) restano com'erano.
        def _righe_alternate(tree):
            pila = [""]
            while pila:
                genitore = pila.pop()
                for indice, figlio in enumerate(tree.get_children(genitore)):
                    if indice % 2 and figlio in nodi_neutri:
                        tree.item(figlio, tags=("cartella_ok_alt",))
                    if figlio in nodi_cartella:
                        pila.append(figlio)
        _righe_alternate(self.tree1); _righe_alternate(self.tree2)

        # Dopo il confronto, espande automaticamente le cartelle che contengono
        # differenze, su entrambi i pannelli.
        for percorso, stato_cartella in stati_cartelle.items():
            if stato_cartella != "cartella_ok":
                for tree, mappa in ((self.tree1, m1), (self.tree2, m2)):
                    item_cartella = mappa.get(percorso)
                    if item_cartella:
                        tree.item(item_cartella, open=True)
        if not hasattr(self, "panel_summary"):
            self.frame_tree1.pack(side="left", fill="both", expand=True, padx=(0, 5)); self.frame_tree2.pack(side="right", fill="both", expand=True, padx=(5, 0))
        self._nodi_cartella_mancante1 = nodi_mancanti1
        self._nodi_cartella_mancante = nodi_mancanti2   # pannello destro
        self._nodi_simili = (nodi_simili1, nodi_simili2)
        self.root.after_idle(self._adatta_etichette_cartelle_mancanti)
        self._applica_filtri_visualizzazione()

    @staticmethod
    def _testo_con_etichetta(font, base, etichetta, disponibile):
        """«nome + etichetta» se entra in `disponibile` pixel; altrimenti il nome viene
        accorciato con «…» in modo che l'etichetta resti sempre visibile."""
        pieno = base + etichetta
        if font.measure(pieno) <= disponibile:
            return pieno
        basso, alto, migliore = 1, len(base), 1
        while basso <= alto:
            medio = (basso + alto) // 2
            if font.measure(base[:medio].rstrip() + "…" + etichetta) <= disponibile:
                migliore, basso = medio, medio + 1
            else:
                alto = medio - 1
        return base[:migliore].rstrip() + "…" + etichetta

    def _font_treeview(self):
        try:
            specifica = self.style.lookup("Treeview", "font")
            if specifica:
                return _font_tk(str(specifica))
        except tk.TclError:
            pass
        return tkfont.nametofont("TkDefaultFont")

    def _adatta_etichette_cartelle_mancanti(self):
        """«nome [CARTELLA MANCANTE]» sempre per intero nella colonna Nome, in entrambi i pannelli."""
        etichetta = self._t(" [CARTELLA MANCANTE]", " [MISSING FOLDER]")  # lingua corrente
        for tree, nodi in ((getattr(self, "tree1", None), getattr(self, "_nodi_cartella_mancante1", None)),
                           (getattr(self, "tree2", None), getattr(self, "_nodi_cartella_mancante", None))):
            if not nodi or tree is None:
                continue
            try:
                larghezza = int(tree.column("#0", "width"))
                if larghezza < 80:
                    continue
                font = self._font_treeview()
                try:
                    indentazione = int(str(self.style.lookup("Treeview", "indent") or 20))
                except (tk.TclError, ValueError):
                    indentazione = 20
                indentazione = max(indentazione, 25)
                for nodo, (base, _etichetta_creazione, livello) in list(nodi.items()):
                    if not tree.exists(nodo):
                        continue
                    # spazio per frecce di espansione, indentazione, icona cartella e margini
                    disponibile = larghezza - (livello + 1) * indentazione - 31 - 8
                    tree.item(nodo, text=self._testo_con_etichetta(font, base, etichetta, disponibile))
            except tk.TclError:
                pass

    def _su_ridimensiona_albero_destro(self, _evento=None):
        if not (getattr(self, "_nodi_cartella_mancante", None) or getattr(self, "_nodi_cartella_mancante1", None)):
            return
        precedente = getattr(self, "_adatta_etichette_id", None)
        if precedente is not None:
            try:
                self.root.after_cancel(precedente)
            except tk.TclError:
                pass
        self._adatta_etichette_id = self.root.after(120, self._adatta_etichette_cartelle_mancanti)

    def _confronto_completato(self):
        self.is_scanning = False; self._confronto_eseguito = True; self.btn_avvia.config(state="normal"); self.btn_stop.config(state="disabled")
        for b in [self.btn_refresh, self.btn_espandi]: b.config(state="normal")
        self.progress_bar["value"] = 100
        avviso, self._avviso_dopo_confronto = self._avviso_dopo_confronto, None
        if avviso:
            self.lbl_status.avviso(avviso)   # es. «Sincronizzazione INTERROTTA…» in rosso
        else:
            self.lbl_status.config(text=self._t("Confronto completato!", "Comparison complete!"))
        if self._preview_dopo_confronto:
            self._preview_dopo_confronto = False
            self.root.after(150, self.anteprima_differenze)

# Evita che lo stesso programma venga aperto più volte su Windows.
# Il mutex rimane valido finché il processo mantiene il relativo handle.
_single_instance_mutex = None

def _assicura_istanza_unica():
    global _single_instance_mutex
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.GetLastError.restype = ctypes.c_ulong
        _single_instance_mutex = kernel32.CreateMutexW(None, False, r"Local\Media_Dir_File_compare_SingleInstance")
        errore_mutex = kernel32.GetLastError()
        if not _single_instance_mutex:
            # Se Windows non consente di creare il mutex, non bloccare l'avvio.
            return True
        ERROR_ALREADY_EXISTS = 183
        if errore_mutex == ERROR_ALREADY_EXISTS:
            try:
                user32 = ctypes.WinDLL("user32", use_last_error=True)
                user32.MessageBoxW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint)
                user32.MessageBoxW.restype = ctypes.c_int
                user32.MessageBoxW(None,
                    "File/Dir Compare & Sync è già aperto. Chiudi questa finestra e usa l'istanza già avviata.",
                    "Programma già in esecuzione", 0x40 | 0x1000)
            except Exception:
                # Fallback console per avvii da terminale; la finestra nativa è il canale principale.
                try:
                    print("File/Dir Compare & Sync è già in esecuzione.")
                except Exception:
                    pass
            return False
        return True
    except Exception:
        return True

if __name__ == "__main__":
    if _assicura_istanza_unica():
        root = tk.Tk(); app = AppConfrontoCartelle(root); root.mainloop()
