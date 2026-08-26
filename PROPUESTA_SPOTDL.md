# Proposta: Integració yt-dlp amb JM-MusicAnalyzer

**Data:** 2026-06-26  
**Estat:** POC completat  
**Finalitat:** Descàrrega d'àudio per anàlisi i gestió musical  
**Backup:** `E:\OpenCode\backups\JM-MusicAnalizer_backup` (2026-06-29)

---

## 1. Resultat del POC

### ✅ Cadena YouTube → ffmpeg → MP3
- **yt-dlp**: Funciona correctament amb Python 3.13
- **FFmpeg**: Instal·lat a `~\.spotdl\ffmpeg.exe`
- **Descàrrega**: Rick Astley - Never Gonna Give You Up → 6.72 MB MP3 (264 kbps)
- **Conversió**: webm → MP3 automàtica

### ❌ spotDL (descartat)
- Error `KeyError: 'uri'` amb API de Spotify
- Incompatibilitat possible amb Python 3.13
- **Decisió**: Usar **yt-dlp directe** en lloc de spotDL

---

## 2. Flux proposat (actualitzat)

```
Usuari introdueix URL YouTube o cerca títol
    ↓
Plugin yt_dl busca i descarrega
    ↓
yt-dlp → ffmpeg → MP3 (264 kbps)
    ↓
Usuari selecciona carpeta destí
    ↓
JM-MusicAnalyzer analitza:
    - Metadades ID3 (mutagen)
    - Fingerprints (acoustid/chromaprint)
    - Qualitat d'àudio
    ↓
Resultat a la BD library.db
```

---

## 3. Disseny gràfic — Integració a la UI

### Opció recomanada: Diàleg modal des del menú principal

```
┌─────────────────────────────────────────────────┐
│  JM-MusicAnalyzer v4.44.0                       │
├─────────────────────────────────────────────────┤
│  [Menu] [Eina] [Config]                         │
│  ─────────────────────────────────────────────  │
│  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 📁 Música   │  │ 🎵 Detalls de la pista  │  │
│  │ ─────────── │  │ ─────────────────────── │  │
│  │ 📂 Jazz     │  │ Artista: Queen          │  │
│  │ 📂 Rock     │  │ Títol: Bohemian Rhapsody│  │
│  │ 📂 Pop      │  │ Àlbum: A Night at Opera │  │
│  │ 📂 Clàssica │  │ Durada: 5:55            │  │
│  │             │  │ Qualitat: 264 kbps      │  │
│  │ 🎵 track1   │  │ ─────────────────────── │  │
│  │ 🎵 track2   │  │ [▶ Reproduir]           │  │
│  │ 🎵 track3   │  │ [📝 Editar] [🗑 Eliminar]│  │
│  └─────────────┘  └─────────────────────────┘  │
│  ─────────────────────────────────────────────  │
│  [📥 Importar] [🔍 Cercar] [📊 Estadístiques] │  │
│  ▲▼ ← →  F2  F3  F4  F5  F6  F7  F8  F9      │  │
└─────────────────────────────────────────────────┘
```

### Nou diàleg: Importar des de YouTube

```
┌─────────────────────────────────────────────────┐
│  📥 Importar àudio des de YouTube               │
├─────────────────────────────────────────────────┤
│                                                 │
│  URL o cerca: [________________________________] │
│  🔍 Cercar                                      │
│                                                 │
│  ─── Resultats de la cerca ─────────────────── │
│  ☐ Bohemian Rhapsody - Queen (4:55)            │
│  ☐ Bohemian Rhapsody - Live Aid (6:00)         │
│  ☐ Bohemian Rhapsody - Cover (5:10)            │
│                                                 │
│  ─── Carpeta destí ─────────────────────────── │
│  [📁 Seleccionar carpeta] E:\Música\           │
│                                                 │
│  ─── Opcions ───────────────────────────────── │
│  ☑ Afegir metadades ID3                        │
│  ☑ Analitzar després de descarregar            │
│  ☐ Sobreescriure si existeix                   │
│                                                 │
│  [Descarregar] [Cancel·lar]                     │
└─────────────────────────────────────────────────┘
```

---

## 4. Flux de treball detallat

### Pas 1: Obertura del diàleg
- L'usuari clica **"Importar"** a la barra d'eines
- S'obre un diàleg modal (no substitueix la pantalla principal)

### Pas 2: Cerca o URL
- **Opció URL**: Enganxa un link de YouTube → yt-dlp cerca automàticament
- **Opció Cerca**: Esc un títol → es fa una ceraca a YouTube via yt-dlp
- **Resultat**: Llista de resultats amb títol, durada, font

### Pas 3: Selecció
- L'usuari selecciona les cançons que vol (checkbox)
- Pot pre-visualitzar (reproduir 10 segons de mostra)

### Pas 4: Carpeta destí
- **Per defecte**: La carpeta activa del panell esquerre
- **Selector**: Botó per canviar carpeta
- **Memòria**: Recorda l'última carpeta utilitzada

### Pas 5: Descàrrega
- Barra de progrés (multi-cançó)
- Log d'errors (vídeos no trobats, errors de xarxa)
- Opció de cancel·lar

### Pas 6: Analisi automàtica
- Després de descarregar, s'analitza cada MP3:
  - Metadades ID3 (mutagen)
  - Fingerprints (acoustid)
  - Qualitat d'àudio
- Resultat s'afegeix a la BD `library.db`

---

## 5. Arquitectura tècnica

### Plugin `yt_dl/`
```
src/plugins/yt_dl/
├── __init__.py
├── main.py           # Plugin principal + UI
├── downloader.py     # Lògica yt-dlp (subprocess)
├── analyzer.py       # Anàlisi post-descàrrega
└── plugin.json       # Configuració del plugin
```

### Dependències noves
```
yt-dlp              # Descàrrega YouTube
ffmpeg (sistema)     # Conversió àudio
mutagen             # Metadades ID3 (ja instal·lat)
pyacoustid          # Fingerprints (ja instal·lat)
```

### Mida del build
- **Actual**: ~211 MB
- **Amb yt-dlp**: ~220-230 MB (augment mínim)

---

## 6. Consideracions importants

| Aspecte | Detall |
|---------|--------|
| **Qualitat** | Màx 264 kbps (YouTube) — suficient per anàlisi |
| **Matching** | Pot baixar covers/live en lloc de la versió d'estudi |
| **Errors de xarxa** | Cal gestió robusta (timeouts, reintentar) |
| **Metadades** | ID3 de YouTube pot ser incomplet → completar amb mutagen |
| **Llicència** | Àrea grisa — ús personal tolerat |
| **Docker** | Funciona en Docker si es necessari |

---

## 7. Pròxims passos

1. ✅ POC yt-dlp completat
2. ✅ Plugin `yt_dl/` creat a JM-MusicAnalyzer
3. ✅ Diàleg d'importació implementat
4. ✅ Anàlisi post-descàrrega integrada
5. 🔲 Test d'integració completa (build + EXE verificat)
6. 🔲 Afegir tests al verify_automatica.py
