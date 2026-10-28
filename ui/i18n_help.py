"""Textos d'ajuda en els idiomes suportats (ES/CA).

Patró idèntic a `ui/i18n_menu.py`: es llegeix `settings["language"]` a
l'obertura del diàleg; canviar d'idioma requereix reiniciar (vegeu
`SettingsDialog`). Per defecte ES (comportament anterior conservat).

Contingut verificat contra el codi a v4.54.17 (vegeu CHANGELOG).
"""

from ui.i18n_menu import LANG_CA, LANG_ES, get_language

_HELP = {
    "help_prefix": {"es": "Ayuda", "ca": "Ajuda"},
    # --- Manager: títols del menú ? ---
    "m_db": {"es": "Base de Datos", "ca": "Base de dades"},
    "m_filters": {"es": "Filtros y Búsqueda", "ca": "Filtres i cerca"},
    "m_player": {"es": "Reproductor", "ca": "Reproductor"},
    "m_metadata": {"es": "Metadatos", "ca": "Metadades"},
    "m_files": {"es": "Gestión Archivos", "ca": "Gestió de fitxers"},
    "m_reports": {"es": "Informes", "ca": "Informes"},
    # --- Manager: continguts ---
    "h_db": {
        "es": "<b>Limpiar</b>: Elimina todas las pistas de la BD. Los archivos no se borran del disco.<br><br>"
        "<b>Optimizar</b>: Compacta la BD (VACUUM) y actualiza estadísticas. Muestra MB liberados.<br><br>"
        "<b>Eliminar Inexistentes</b>: Borra de la BD las pistas cuyo archivo ya no existe en disco.<br><br>"
        "<b>Reconstruir</b>: Re-escanea pistas con datos incompletos (título, artista, duración o bitrate vacíos).<br><br>"
        "<b>Copia de Seguridad</b>: Guarda una copia de la BD con fecha y hora en backups/.<br><br>"
        "<b>Restaurar Copia</b>: Reemplaza la BD actual por una copia de seguridad anterior.",
        "ca": "<b>Neteja</b>: Esborra totes les pistes de la BD. Els fitxers no s'esborren del disc.<br><br>"
        "<b>Optimitza</b>: Compacta la BD (VACUUM) i actualitza estadístiques. Mostra els MB alliberats.<br><br>"
        "<b>Elimina inexistents</b>: Esborra de la BD les pistes que ja no existeixen al disc.<br><br>"
        "<b>Reconstrueix</b>: Torna a escanejar les pistes amb dades incompletes (títol, artista, durada o bitrate buits).<br><br>"
        "<b>Còpia de seguretat</b>: Desa una còpia de la BD amb data i hora a backups/.<br><br>"
        "<b>Restaura la còpia</b>: Substitueix la BD actual per una còpia de seguretat anterior.",
    },
    "h_filters": {
        "es": "<b>Género / Rating / BPM</b>: Combos para filtrar las pistas de la tabla. Se pueden combinar.<br><br>"
        "<b>Buscar</b>: Busca por texto (artista, título, género). Pulsa Enter.<br><br>"
        "<b>Reset</b>: Limpia todos los filtros y muestra todas las pistas.<br><br>"
        "<b>Árbol de carpetas</b>: Clic en una carpeta o favorito (+⭐) para ver solo sus pistas.",
        "ca": "<b>Gènere / Rating / BPM</b>: Combos per filtrar les pistes de la taula. Es poden combinar.<br><br>"
        "<b>Cerca</b>: Cerca per text (artista, títol, gènere). Prem Enter.<br><br>"
        "<b>Reset</b>: Neteja tots els filtres i mostra totes les pistes.<br><br>"
        "<b>Arbre de carpetes</b>: Clic en una carpeta o favorit (+⭐) per veure només les seves pistes.",
    },
    "h_player": {
        "es": "<b>Play / Pause</b>: Reproduce o pausa la canción seleccionada.<br><br>"
        "<b>⏮ / ⏭</b>: Canción anterior / siguiente. Se reproduce automáticamente.<br><br>"
        "<b>CUE (🎧)</b>: Pre-escucha por auriculares (salida CUE) sin que suene por los altavoces. Tiene su propio control de volumen.<br><br>"
        "<b>Clic en una fila</b>: Carga la canción en el reproductor (sin reproducirla).",
        "ca": "<b>Play / Pausa</b>: Reprodueix o posa en pausa la cançó seleccionada.<br><br>"
        "<b>⏮ / ⏭</b>: Cançó anterior / següent. Es reprodueix automàticament.<br><br>"
        "<b>CUE (🎧)</b>: Pre-escolta per auriculars (sortida CUE) sense que soni pels altaveus. Té el seu propi control de volum.<br><br>"
        "<b>Clic en una fila</b>: Carrega la cançó al reproductor (sense reproduir-la).",
    },
    "h_metadata": {
        "es": "<b>GUARDAR (💾)</b>: Guarda los cambios en el archivo y en la BD. Con varias pistas seleccionadas (N) solo se aplican los campos modificados.<br><br>"
        "<b>Carátula (📂 / 🗑)</b>: Añade o cambia la carátula desde un JPG/PNG, o quítala. Se aplica al GUARDAR, incluso si no había carátula.<br><br>"
        "<b>Información técnica</b>: Bitrate, frecuencia, canales, duración, tamaño e ID3 de la pista. ✓/✗ indica si el análisis espectral confirma el bitrate declarado.<br><br>"
        "<b>Buscar (MusicBrainz / iTunes)</b>: Busca metadatos online por artista y título, con comparativa para elegir qué aplicar.<br><br>"
        "<b>Fingerprint (AcoustID)</b>: Identifica por huella acústica. Útil sin metadatos o si son incorrectos.<br><br>"
        "<b>Forzar Lectura</b>: Re-lee el archivo ignorando la caché.<br><br>"
        "<b>Rating (★)</b>: Puntúa con las estrellas y pulsa GUARDAR. En la tabla, el rating se guarda solo.",
        "ca": "<b>DESA (💾)</b>: Desa els canvis al fitxer i a la BD. Amb diverses pistes seleccionades (N) només s'apliquen els camps modificats.<br><br>"
        "<b>Caràtula (📂 / 🗑)</b>: Afegeix o canvia la caràtula des d'un JPG/PNG, o treu-la. S'aplica en DESAR, encara que no n'hi hagués.<br><br>"
        "<b>Informació tècnica</b>: Bitrate, freqüència, canals, durada, mida i ID3 de la pista. ✓/✗ indica si l'anàlisi espectral confirma el bitrate declarat.<br><br>"
        "<b>Cerca (MusicBrainz / iTunes)</b>: Cerca metadades en línia per artista i títol, amb comparativa per triar què s'aplica.<br><br>"
        "<b>Fingerprint (AcoustID)</b>: Identifica per petjada acústica. Útil sense metadades o si són incorrectes.<br><br>"
        "<b>Força la lectura</b>: Torna a llegir el fitxer ignorant la cau.<br><br>"
        "<b>Rating (★)</b>: Puntua amb les estrelles i prem DESA. A la taula, el rating es desa sol.",
    },
    "h_files": {
        "es": "<b>🖱 Botón derecho sobre una pista:</b><br><br>"
        "<b>➕ Añadir a Playlist → 🎧 Añadir a Master Playlist (DJ)</b>: Envía la pista a la playlist principal del modo DJ. <b>📁 Crear nueva playlist...</b>: Crea una lista con la pista.<br><br>"
        "<b>📑 Duplicar Archivo</b>: Copia física. <b>📋 Copiar a Carpeta...</b> / <b>🚚 Mover Archivo...</b>: Copia o mueve y actualiza la BD.<br><br>"
        "<b>🗑 Eliminar de Disco</b>: Borra del disco y de la BD.<br><br>"
        "<b>🔄 Forçar Lectura Metadades</b> / <b>🎵 Identificar por Fingerprint</b>: Re-lee o identifica por huella acústica.<br><br>"
        "<b>📂 Abrir en Explorador</b> / <b>📋 Copiar Ruta</b>: Utilidades.<br><br>"
        "Con varias pistas: eliminar N, copiar rutas, <b>🏷️ Cambiar Género...</b>, añadir a Master e identificar la selección.",
        "ca": "<b>🖱 Botó dret sobre una pista:</b><br><br>"
        "<b>➕ Añadir a Playlist → 🎧 Añadir a Master Playlist (DJ)</b>: Envia la pista a la playlist principal del mode DJ. <b>📁 Crear nueva playlist...</b>: Crea una llista amb la pista.<br><br>"
        "<b>📑 Duplicar Archivo</b>: Còpia física. <b>📋 Copiar a Carpeta...</b> / <b>🚚 Mover Archivo...</b>: Copia o mou i actualitza la BD.<br><br>"
        "<b>🗑 Eliminar de Disco</b>: Esborra del disc i de la BD.<br><br>"
        "<b>🔄 Forçar Lectura Metadades</b> / <b>🎵 Identificar por Fingerprint</b>: Torna a llegir o identifica per petjada acústica.<br><br>"
        "<b>📂 Abrir en Explorador</b> / <b>📋 Copiar Ruta</b>: Utilitats.<br><br>"
        "Amb diverses pistes: esborrar N, copiar rutes, <b>🏷️ Cambiar Género...</b>, afegir a Master i identificar la selecció.",
    },
    "h_reports": {
        "es": "<b>Pistas de Baja Calidad</b>: Muestra pistas con bitrate &lt; 128 kbps o duración &lt; 10s. ▶ Preview, ✅ Ignorar, 🗑 Eliminar archivo, 📄 Exportar TXT.<br><br>"
        "<b>Pistas Corruptas</b>: Muestra pistas con duración &lt;= 0. Mismos botones.<br><br>"
        "<b>Archivos Duplicados</b>: Detecta duplicados por SHA256. 5 modos: SHA256, nombre, título+artista, duración, tamaño+duración.<br><br>"
        "<b>Duplicados en Favoritos</b>: Busca pistas que aparecen en más de una carpeta favorita.",
        "ca": "<b>Pistes de baixa qualitat</b>: Mostra pistes amb bitrate &lt; 128 kbps o durada &lt; 10s. ▶ Preview, ✅ Ignora, 🗑 Esborra el fitxer, 📄 Exporta TXT.<br><br>"
        "<b>Pistes malmeses</b>: Mostra pistes amb durada &lt;= 0. Mateixos botons.<br><br>"
        "<b>Fitxers duplicats</b>: Detecta duplicats per SHA256. 5 modes: SHA256, nom, títol+artista, durada, mida+durada.<br><br>"
        "<b>Duplicats als favorits</b>: Cerca pistes que apareixen a més d'una carpeta favorita.",
    },
    # --- DJ: títols ---
    "d_playback": {"es": "Reproducción y Decks", "ca": "Reproducció i decks"},
    "d_mix": {"es": "Crossfader y Mezcla", "ca": "Crossfader i mescla"},
    "d_playlists": {"es": "Playlists", "ca": "Playlists"},
    "d_audio": {"es": "Audio y CUE", "ca": "Àudio i CUE"},
    # --- DJ: continguts ---
    "h_d_playback": {
        "es": "<b>Deck A / Deck B</b>: Dos reproductores independientes. Carga canciones desde las playlists (doble clic alterna A/B).<br><br>"
        "<b>⏭ SKIP</b>: Salta a la siguiente canción sin esperar el fade.<br><br>"
        "<b>⏭️ CROSSFADER</b>: Inicia la transición al siguiente tema inmediatamente.<br><br>"
        "<b>🔁 LOOP</b>: Efecto visual de 15 s con bordes de colores (no repite el audio).<br><br>"
        "<b>▶ LANZAR MIX</b>: Automix con crossfade entre pistas consecutivas.<br><br>"
        "<b>🗔 COMPACT</b> (o Espacio, salvo editando texto): Oculta platos y mixer. La barra compacta trae play/pause, stop, info, progreso, volumen y crossfader.",
        "ca": "<b>Deck A / Deck B</b>: Dos reproductors independents. Carrega cançons des de les playlists (doble clic alterna A/B).<br><br>"
        "<b>⏭ SKIP</b>: Salta a la següent cançó sense esperar el fade.<br><br>"
        "<b>⏭️ CROSSFADER</b>: Inicia la transició al següent tema immediatament.<br><br>"
        "<b>🔁 LOOP</b>: Efecte visual de 15 s amb vores de colors (no repeteix l'àudio).<br><br>"
        "<b>▶ LANZAR MIX</b>: Automix amb crossfade entre pistes consecutives.<br><br>"
        "<b>🗔 COMPACT</b> (o Espai, excepte editant text): Amaga plats i mixer. La barra compacta porta play/pausa, stop, info, progrés, volum i crossfader.",
    },
    "h_d_mix": {
        "es": "<b>Crossfader</b>: Desliza para mezclar entre Deck A (izquierda) y Deck B (derecha).<br><br>"
        "<b>Fade/Silencio (s)</b>: Segundos de crossfade (positivo) o de silencio entre temas (negativo, p. ej. -5 = 5 s).<br><br>"
        "<b>Vol Master</b>: Volumen general (hasta 300 %). El botón 100% lo deja sin ganancia extra.<br><br>"
        "<b>CLIP</b>: Se ilumina con picos de señal: baja el master.<br><br>"
        "<b>VU Meters</b>: Nivel de señal de cada deck.",
        "ca": "<b>Crossfader</b>: Llisca per mesclar entre Deck A (esquerra) i Deck B (dreta).<br><br>"
        "<b>Fade/Silencio (s)</b>: Segons de crossfade (positiu) o de silenci entre temes (negatiu, p. ex. -5 = 5 s).<br><br>"
        "<b>Vol Master</b>: Volum general (fins al 300 %). El botó 100% el deixa sense guany extra.<br><br>"
        "<b>CLIP</b>: S'il·lumina amb pics de senyal: baixa el master.<br><br>"
        "<b>VU Meters</b>: Nivell de senyal de cada deck.",
    },
    "h_d_playlists": {
        "es": "<b>Cargar lista</b>: Lee un archivo .m3u (la LISTA 2 también acepta una carpeta).<br><br>"
        "<b>💾 Guardar</b>: Guarda la playlist actual como .m3u.<br><br>"
        "<b>🆕 Nueva playlist</b>: Crea una playlist vacía desde cero (pide nombre y guarda como .m3u).<br><br>"
        "<b>📋 LISTA 2</b>: Segunda lista independiente para el Deck B.<br><br>"
        "<b>CUE (🎧)</b>: Pre-escucha por auriculares. <b>Vol CUE</b>: Volumen de pre-escucha.<br><br>"
        "<b>Rating</b>: Estrellas por fila, se guardan solas. <b>🗑 Reset Plays</b> / <b>📜 Sessió</b>: Contadores de sesión.",
        "ca": "<b>Carrega llista</b>: Llegeix un fitxer .m3u (la LLISTA 2 també accepta una carpeta).<br><br>"
        "<b>💾 Guardar</b>: Desa la playlist actual com a .m3u.<br><br>"
        "<b>🆕 Nova playlist</b>: Crea una playlist buida des de zero (demana nom i desa com a .m3u).<br><br>"
        "<b>📋 LISTA 2</b>: Segona llista independent per al Deck B.<br><br>"
        "<b>CUE (🎧)</b>: Pre-escolta per auriculars. <b>Vol CUE</b>: Volum de pre-escolta.<br><br>"
        "<b>Rating</b>: Estrelles per fila, es desen soles. <b>🗑 Reset Plays</b> / <b>📜 Sessió</b>: Comptadors de sessió.",
    },
    "h_d_audio": {
        "es": "<b>🎧 CONFIG AUDIO</b>: Abre el diálogo de dispositivos: salida principal (altavoces) y CUE (auriculares/DAC), con 🔄 Recargar para redetectar.<br><br>"
        "<b>Vol CUE</b>: Volumen de pre-escucha, independiente del master.<br><br>"
        "<b>⚙️</b>: Ajustes generales (incluye el idioma de los menús).<br><br>"
        "Si un DAC nuevo no aparece, al guardar se ofrece reiniciar la app.",
        "ca": "<b>🎧 CONFIG AUDIO</b>: Obre el diàleg de dispositius: sortida principal (altaveus) i CUE (auriculars/DAC), amb 🔄 Recargar per redetectar.<br><br>"
        "<b>Vol CUE</b>: Volum de pre-escolta, independent del master.<br><br>"
        "<b>⚙️</b>: Ajustos generals (inclou l'idioma dels menús).<br><br>"
        "Si un DAC nou no apareix, en desar s'ofereix reiniciar l'app.",
    },
}


def help_text(key: str) -> str:
    """Retorna el text d'ajuda per a `key` en l'idioma configurat (ES per defecte)."""
    entry = _HELP.get(key, {})
    return entry.get(get_language(), entry.get(LANG_ES, key))


def help_prefix() -> str:
    """Prefix del títol del diàleg («Ayuda» / «Ajuda»)."""
    return help_text("help_prefix")
