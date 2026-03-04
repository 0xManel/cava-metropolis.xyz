#!/usr/bin/env python3
"""
Apply comprehensive grape variety corrections to bodega_webapp.json.
Research data from 7 parallel agents covering all 588 uncertain wines.
"""

import json
import re

# ============================================================
# CORRECTIONS BY POD (from all research agents)
# Format: "POD123456": (["Grape1", "Grape2"], "alta"/"estimada")
# ============================================================

corrections_by_pod = {

    # ── GALICIA WHITES (agent afbd71a) ──────────────────────
    "POD012953": (["Godello"], "estimada"),
    "POD016497": (["Godello"], "estimada"),
    "POD018553": (["Godello"], "estimada"),
    "POD013185": (["Albariño"], "alta"),
    "POD013184": (["Albariño"], "alta"),
    "POD019463": (["Albariño"], "estimada"),
    "POD018494": (["Albariño"], "alta"),
    "POD015846": (["Godello"], "alta"),
    "POD018997": (["Godello"], "alta"),
    "POD016565": (["Caiño Blanco"], "alta"),
    "POD016566": (["Loureiro", "Albariño", "Caiño Blanco"], "estimada"),
    "POD015306": (["Albariño"], "estimada"),
    "POD017771": (["Albariño"], "alta"),
    "POD018753": (["Albariño"], "alta"),
    "POD018301": (["Albariño"], "alta"),
    "POD019665": (["Treixadura", "Torrontés", "Godello", "Albariño"], "estimada"),
    "POD019160": (["Godello"], "alta"),
    "POD017756": (["Treixadura", "Godello", "Torrontés"], "estimada"),
    "POD018878": (["Albariño"], "alta"),
    "POD018377": (["Godello", "Treixadura"], "alta"),
    "POD018101": (["Godello", "Lado", "Treixadura"], "alta"),
    "POD019143": (["Godello", "Lado", "Treixadura"], "alta"),
    "POD018921": (["Treixadura", "Torrontés", "Lado", "Loureiro", "Albariño"], "alta"),
    "POD012368": (["Albariño"], "alta"),
    "POD018449": (["Treixadura", "Godello", "Torrontés"], "estimada"),
    "POD019664": (["Godello", "Doña Blanca"], "estimada"),
    "POD017871": (["Albariño"], "alta"),
    "POD019086": (["Albariño"], "alta"),
    "POD019085": (["Albariño"], "alta"),
    "POD017033": (["Caiño Blanco"], "alta"),
    "POD019158": (["Caiño Blanco"], "alta"),
    "POD017057": (["Treixadura", "Godello", "Loureiro", "Torrontés"], "alta"),
    "POD019458": (["Godello", "Treixadura", "Doña Blanca"], "estimada"),
    "POD018412": (["Godello"], "estimada"),
    "POD018497": (["Albariño"], "alta"),
    "POD018333": (["Albariño"], "estimada"),
    "POD018382": (["Albariño"], "alta"),
    "POD018026": (["Godello"], "alta"),
    "POD008791": (["Albariño"], "alta"),
    "POD016099": (["Albariño"], "alta"),
    "POD017538": (["Godello"], "alta"),
    "POD012742": (["Godello"], "alta"),
    "POD019667": (["Treixadura", "Torrontés", "Godello"], "estimada"),
    "POD018331": (["Albariño"], "alta"),
    "POD019461": (["Albariño"], "alta"),
    "POD019462": (["Albariño"], "alta"),
    "POD018100": (["Albariño"], "alta"),
    "POD017626": (["Albariño"], "alta"),
    "POD016572": (["Treixadura", "Torrontés", "Albariño", "Loureiro", "Godello"], "estimada"),
    "POD012359": (["Godello"], "alta"),
    "POD010576": (["Godello"], "alta"),
    "POD012358": (["Godello"], "alta"),
    "POD019150": (["Albariño"], "estimada"),
    "POD017212": (["Godello"], "estimada"),

    # ── BIERZO WHITES (Godello, not Verdejo/Sauvignon) ──────
    "POD019164": (["Godello"], "alta"),   # Raúl Pérez Ultreia La Claudina
    "POD019443": (["Godello"], "alta"),   # Verónica Ortega Llorona
    "POD018816": (["Godello"], "alta"),   # Verónica Ortega Tormenta
    "POD017277": (["Godello"], "estimada"), # La Vizcaína la del Vivo

    # ── RIBERA DEL DUERO REDS (agent a3a5acd) ───────────────
    "POD018042": (["Tempranillo", "Cabernet Sauvignon", "Syrah"], "alta"),   # AR Cuvée Palomar
    "POD018041": (["Tempranillo"], "alta"),         # AR Pago Negralada
    "POD017937": (["Tempranillo", "Cabernet Sauvignon", "Merlot", "Petit Verdot"], "estimada"),  # AR X Aniversario
    "POD016261": (["Tempranillo"], "alta"),         # Aalto PS 06
    "POD015645": (["Tempranillo"], "alta"),         # AR Pago Garduña
    "POD016582": (["Cabernet Sauvignon"], "alta"),  # AR Pago Valdebellón (100% CS!)
    "POD015880": (["Petit Verdot"], "alta"),        # AR Petit Verdot (100% PV!)
    "POD018922": (["Tempranillo", "Cabernet Sauvignon", "Syrah"], "alta"),  # AR Sel Especial 21
    "POD012811": (["Tempranillo", "Cabernet Sauvignon", "Syrah"], "alta"),  # AR Sel Especial NV
    "POD017253": (["Tempranillo"], "alta"),         # Alonso del Yerro 20
    "POD019695": (["Tempranillo"], "alta"),         # Arrocal Casablanca 23
    "POD017351": (["Tempranillo"], "alta"),         # Arrocal Paraje Colmenares
    "POD013712": (["Tempranillo"], "alta"),         # Aurelio García La Guia
    "POD018249": (["Tempranillo"], "alta"),         # Ausas Interpretación
    "POD019773": (["Tempranillo"], "estimada"),     # Bendito Destino Camino Destino
    "POD019774": (["Tempranillo"], "estimada"),     # Bendito Destino Hontanares
    "POD013769": (["Tempranillo", "Merlot"], "alta"),  # Bosque de Matasnos Ed. Limitada
    "POD016574": (["Tempranillo", "Merlot"], "alta"),  # Bosque Matasnos Et. Blanca
    "POD013798": (["Tempranillo", "Syrah", "Merlot"], "alta"),  # Carmelo Rodero TSM
    "POD019697": (["Tempranillo"], "estimada"),     # Casa Lebai Matadiablos
    "POD017815": (["Tempranillo"], "alta"),         # Cepa 21
    "POD018082": (["Tempranillo"], "alta"),         # Cepa 21 Malabrigo
    "POD017140": (["Tempranillo", "Merlot", "Cabernet Sauvignon"], "alta"),  # Conde San Cristóbal
    "POD018632": (["Tempranillo"], "alta"),         # Corimbo
    "POD017118": (["Tempranillo"], "alta"),         # Corimbo I
    "POD015868": (["Tempranillo"], "alta"),         # Cuesta de las Liebres 20
    "POD014733": (["Tempranillo"], "alta"),         # Cuesta Las Liebres 19
    "POD018033": (["Tempranillo"], "alta"),         # Figuero Viñas Viejas 23
    "POD015818": (["Tempranillo", "Cabernet Sauvignon", "Merlot"], "alta"),  # Finca Villacreces
    "POD012936": (["Tempranillo"], "alta"),         # Garmón 21
    "POD014241": (["Tempranillo", "Cabernet Sauvignon", "Merlot", "Petit Verdot"], "alta"),  # Hacienda Monasterio Rva
    "POD015579": (["Tempranillo"], "alta"),         # Malleolus Valderramiro
    "POD017763": (["Tempranillo"], "alta"),         # María Alonso del Yerro
    "POD016257": (["Tempranillo"], "alta"),         # Mg. Aalto PS 13
    "POD016263": (["Tempranillo", "Garnacha"], "estimada"),  # Mg. Cartago (Mauro)
    "POD014522": (["Tempranillo"], "alta"),         # Mg. Cuesta Las Liebres 18
    "POD015819": (["Tempranillo"], "alta"),         # Nebro 21
    "POD014245": (["Tempranillo"], "alta"),         # Peña Lobera 21
    "POD015108": (["Tempranillo", "Cabernet Sauvignon"], "alta"),  # Pesus 18
    "POD014777": (["Tempranillo"], "alta"),         # Pícaro del Águila TO
    "POD016022": (["Tempranillo", "Garnacha", "Albillo Mayor"], "alta"),  # PSI 22
    "POD018039": (["Tempranillo"], "alta"),         # San Cobate Cucufate Altos del Viso
    "POD018040": (["Tempranillo"], "alta"),         # San Cobate Cucufate Bancales Jalón
    "POD018038": (["Tempranillo"], "alta"),         # San Cobate Cucufate Monasterio
    "POD018037": (["Tempranillo"], "alta"),         # San Cobate La Finca
    "POD019082": (["Tempranillo"], "alta"),         # Sanchomartin
    "POD018826": (["Tempranillo"], "alta"),         # Solano Viñas Viejas
    "POD019797": (["Tempranillo", "Merlot"], "alta"),  # TM de Tr3smano
    "POD016536": (["Tempranillo", "Merlot", "Cabernet Franc"], "alta"),  # Tr3smano Vendimia
    "POD015067": (["Tempranillo"], "alta"),         # Valduero 6 Años
    "POD018859": (["Tempranillo"], "alta"),         # Valduero Una Cepa
    "POD016117": (["Tempranillo"], "estimada"),     # Valeyo
    "POD017304": (["Tempranillo"], "alta"),         # Viña Sastre Pago Santa Cruz

    # Harlan Estate 20 (California, found in Ribera batch by mistake)
    "POD016264": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc", "Petit Verdot"], "alta"),

    # Abadía Retuerta clarete
    "POD017936": (["Tempranillo", "Garnacha"], "alta"),  # AR Clarete 21 (rosé)
    "POD014007": (["Tempranillo", "Albillo Mayor", "Garnacha"], "alta"),  # Dominio Águila Peñas Aladas
    "POD018962": (["Tempranillo"], "alta"),          # Le Rosé Antídoto 23
    "POD016972": (["Tempranillo", "Albillo Mayor"], "alta"),  # Pícaro Águila Clarete RO
    "POD014990": (["Tempranillo", "Albillo Mayor"], "alta"),  # Territorio Luthier Clarete 2020
    "POD019724": (["Tempranillo", "Albillo Mayor"], "estimada"),  # Palito V Clarete 24

    # ── RIOJA WHITES (agent a6b8423) ─────────────────────────
    "POD019789": (["Viura"], "alta"),               # Abel Mendoza V5
    "POD018339": (["Viura"], "alta"),               # Capellanía Rva 20
    "POD019745": (["Viura"], "estimada"),            # Costumbres BL 23
    "POD012651": (["Viura"], "estimada"),            # Cuentaviñas Arriscado BL
    "POD017575": (["Viura", "Garnacha Blanca", "Malvasía"], "alta"),  # Finca Emperatriz BL
    "POD018643": (["Viura", "Malvasía", "Garnacha Blanca", "Tempranillo Blanco"], "alta"),  # Flor de Muga BL
    "POD016107": (["Viura"], "estimada"),            # Mg. Baynos BL 21
    "POD016778": (["Viura", "Malvasía"], "alta"),    # Mg. Remírez Ganuza GR Olagar 15
    "POD018513": (["Viura", "Malvasía"], "alta"),    # Olagar BL Gran Rva 18
    "POD018756": (["Viura"], "estimada"),            # Oxer Kalamity BL 23
    "POD008838": (["Viura"], "alta"),                # Placet 22
    "POD016949": (["Viura"], "estimada"),            # Que Bonito Cacareaba 23
    "POD018620": (["Viura", "Garnacha Blanca", "Malvasía", "Roussanne", "Marsanne",
                   "Sauvignon Blanc", "Chardonnay"], "alta"),  # Remelluri Blanco
    "POD003990": (["Viura", "Malvasía"], "alta"),    # Remírez de Ganuza BL FB 16
    "POD015771": (["Viura"], "estimada"),            # Roda I Blanco (flagged: possible error)
    "POD012656": (["Viura"], "estimada"),            # Sierra Cantabria Gran Vino BL 10
    "POD017869": (["Viura"], "estimada"),            # Trascuevas 23
    "POD015112": (["Viura", "Malvasía"], "alta"),    # Viña Tondonia RV BL 13

    # ── RUEDA / VERDEJO (agent a6b8423) ──────────────────────
    "POD019641": (["Verdejo"], "alta"),              # Álvar de Dios Las Vidres
    "POD019642": (["Verdejo"], "alta"),              # Álvar de Dios Vaguera
    "POD019439": (["Verdejo"], "estimada"),          # Arenas de SantYuste
    "POD017755": (["Verdejo"], "alta"),              # Barco del Corneta
    "POD012663": (["Verdejo"], "alta"),              # Belondrade Les Parcelles
    "POD016481": (["Verdejo"], "alta"),              # Belondrade y Lurton
    "POD018854": (["Verdejo"], "alta"),              # Cantalapiedra Chiviritero
    "POD019457": (["Verdejo"], "alta"),              # Cantalapiedra Otea
    "POD013822": (["Verdejo"], "alta"),              # César Márquez El Val 22
    "POD017709": (["Verdejo"], "alta"),              # César Márquez El Val 23
    "POD017705": (["Verdejo"], "alta"),              # César Márquez La Salvación
    "POD014013": (["Verdejo", "Albillo Mayor"], "alta"),  # Dominio Águila VV BL 19
    "POD018383": (["Verdejo"], "alta"),              # El Transistor 24
    "POD019438": (["Verdejo"], "estimada"),          # Esmeralda García En Blanco
    "POD019708": (["Verdejo"], "alta"),              # José Pariente 25 Años Barrica
    "POD015910": (["Verdejo"], "alta"),              # José Pariente La Medina
    "POD019707": (["Verdejo"], "estimada"),          # Las Comas 22
    "POD018268": (["Verdejo"], "alta"),              # Menade La Misión
    "POD018588": (["Verdejo"], "alta"),              # Nisia Las Suertes
    "POD016482": (["Verdejo"], "alta"),              # Ossian 22
    "POD018123": (["Verdejo"], "alta"),              # Ossian Capitel
    "POD019661": (["Verdejo"], "estimada"),          # Otro Cuento
    "POD016116": (["Malvasía"], "alta"),             # San Román Malvasía 22 (Castilla)
    "POD017772": (["Verdejo"], "estimada"),          # Sangarida La Guiana BL
    "POD017773": (["Verdejo"], "estimada"),          # Sangarida La Yegua
    "POD018500": (["Verdejo"], "alta"),              # Sanz Malcorta
    "POD018393": (["Verdejo"], "estimada"),          # Sin Nombre 22
    "POD014734": (["Verdejo"], "alta"),              # Teiro 22
    "POD017677": (["Verdejo"], "estimada"),          # Territorio Luthier 2021

    # ── CATALUÑA WHITES (agent aca06ac) ─────────────────────
    "POD018127": (["Chardonnay", "Macabeo"], "alta"),            # Abadia del Poblet BL 21
    "POD015872": (["Sauvignon Blanc", "Sémillon"], "alta"),      # Castel d'Encus Taleia
    "POD015450": (["Macabeo", "Chardonnay", "Sauvignon Blanc"], "estimada"),  # Castell Remei GR
    "POD016310": (["Garnacha Blanca", "Viognier"], "alta"),      # Clos Erasmus Laurel BL
    "POD019721": (["Macabeo"], "alta"),                          # Credo Capficat
    "POD019722": (["Garnacha Blanca"], "alta"),                  # Credo Ratpenat
    "POD012820": (["Garnacha Blanca", "Macabeo", "Pedro Ximénez"], "alta"),  # Dido BL 22
    "POD012985": (["Garnacha Blanca"], "alta"),                  # Electio (Terroir al Limit)
    "POD019440": (["Garnacha Blanca", "Macabeo"], "estimada"),   # Finca l'Argata BL
    "POD016923": (["Garnacha Blanca", "Macabeo"], "alta"),       # Les Sorts BL 23
    "POD019777": (["Garnacha Blanca", "Pedro Ximénez", "Viognier"], "alta"),  # Mas d'en Gil Coma Blanca
    "POD016307": (["Macabeo"], "alta"),                          # Mas Doix Salix 23
    "POD017027": (["Garnacha Blanca", "Macabeo", "Pedro Ximénez"], "alta"),  # Mas Martinet Brissat
    "POD014644": (["Chardonnay"], "alta"),                       # Milmanda FB
    "POD016505": (["Macabeo"], "alta"),                          # Murmuri Mas Doix 23
    "POD019613": (["Macabeo"], "alta"),                          # Murmuri Mas Doix 24
    "POD018590": (["Garnacha Blanca", "Pedro Ximénez"], "alta"), # Terroir al Limit Pedra de Guix
    "POD018877": (["Garnacha Blanca", "Macabeo", "Pedro Ximénez"], "alta"),  # Venus La Cartoixa

    # ── CATALUÑA REDS (agent aca06ac) ───────────────────────
    "POD015749": (["Garnacha", "Cariñena", "Syrah", "Cabernet Sauvignon", "Merlot"], "alta"),  # Clos Martinet
    "POD013954": (["Garnacha", "Cariñena", "Syrah"], "alta"),    # Dido Tinto 22
    "POD001707": (["Cariñena"], "alta"),                         # Dits del Terra (100% Cariñena!)
    "POD018544": (["Cariñena", "Garnacha"], "alta"),             # Doix 22
    "POD019737": (["Garnacha"], "alta"),                         # Les Manyes (100% Garnacha!)
    "POD019643": (["Garnacha", "Cariñena"], "alta"),             # Mas d'en Gil Clos Fontà
    "POD019644": (["Garnacha", "Cariñena", "Syrah"], "estimada"), # Mas d'en Gil Maçanella
    "POD011511": (["Cariñena", "Garnacha"], "alta"),             # Mas Doix 1902 Tossal D'En Bou
    "POD019675": (["Cariñena", "Garnacha"], "alta"),             # Mas Doix 1903 Coma de Cases
    "POD011510": (["Garnacha", "Cariñena"], "alta"),             # Mas Doix Salanques 21
    "POD018766": (["Garnacha", "Cariñena"], "alta"),             # Mas Doix Salanques 22
    "POD012989": (["Garnacha", "Cariñena"], "alta"),             # Murmuri Mas Doix 22 (tinto)
    "POD017258": (["Garnacha", "Cariñena", "Syrah"], "alta"),    # Venus de la Figuera 20
    "POD019441": (["Garnacha"], "estimada"),                     # Vinya de la Gloria 20
    "POD018552": (["Garnacha", "Syrah"], "alta"),                # Dido La Solució Rosada 23

    # ── ARAGÓN (Frontonio - Garnacha) ───────────────────────
    "POD018822": (["Garnacha"], "alta"),    # Alas de Frontonio La Tejera
    "POD019623": (["Garnacha"], "alta"),    # Frontonio Telescópico
    "POD019622": (["Garnacha"], "alta"),    # Psicodélico
    "POD017594": (["Garnacha Blanca"], "alta"),  # El Jardín de las Iguales BL
    "POD017674": (["Garnacha Blanca"], "alta"),  # Frontonio La Loma & Los Santos BL

    # ── CANARY ISLANDS ───────────────────────────────────────
    "POD019772": (["Listán Blanco"], "estimada"),  # Jable de Tao 23
    "POD016462": (["Listán Blanco"], "alta"),       # Puro Rofe Blanco 23
    "POD019729": (["Listán Blanco"], "alta"),       # Puro Rofe Morro La Virgen
    "POD019728": (["Diego"], "alta"),               # Puro Rofe Tinasoria (Diego = uva canaria)
    "POD018556": (["Listán Blanco", "Marmajuelo", "Vijariego Blanco"], "alta"),  # Suertes El Trenzado
    "POD019470": (["Listán Blanco"], "alta"),        # Suertes Vidonia 24
    "POD019472": (["Marmajuelo"], "alta"),           # Tameran Marmajuelo 24
    "POD019471": (["Vijariego Blanco"], "alta"),     # Tameran Vijariego 24
    "POD019442": (["Listán Blanco", "Marmajuelo"], "estimada"),  # Victoria Torres Sin Título BL

    # ── ANDALUCÍA / JEREZ ────────────────────────────────────
    "POD008709": (["Palomino Fino"], "alta"),    # Atlántida Blanco 19
    "POD018965": (["Palomino Fino"], "estimada"),  # Socaire BL 23
    "POD010889": (["Palomino Fino"], "alta"),    # Santa Petronila Flor Macharnudo
    "POD018812": (["Moscatel de Alejandría"], "alta"),  # Victoria N2 J. Ordóñez

    # ── NAVARRA ──────────────────────────────────────────────
    "POD019659": (["Garnacha Blanca", "Viura"], "estimada"),  # Jirafas 22
    "POD019723": (["Garnacha Blanca"], "alta"),  # Viña Zorzal Señora Alturas BL

    # ── VALENCIA / MURCIA ────────────────────────────────────
    "POD017912": (["Merseguera", "Macabeo"], "estimada"),  # Cerrón El Cerrico 23
    "POD018064": (["Merseguera"], "alta"),        # Javi Revert Micalet 24
    "POD019650": (["Merseguera", "Malvasía"], "estimada"),  # Luca Bernasconi Temide
    "POD019636": (["Mandó", "Garnacha Tintorera", "Monastrell"], "alta"),  # Celler del Roure La Pebrella
    "POD016186": (["Bobal"], "alta"),             # Finca El Terrerazo 22
    "POD018063": (["Bobal"], "alta"),             # Javi Revert Forada 23
    "POD018062": (["Garnacha Tintorera"], "alta"),  # Javi Revert Simeta 23
    "POD014813": (["Bobal"], "alta"),             # Quincha Corral 19

    # ── EXTREMADURA / BALEARES / CASTILLA-LA MANCHA ─────────
    "POD017303": (["Tempranillo", "Garnacha"], "estimada"),  # Barbas de Gata 20
    "POD008914": (["Tempranillo", "Garnacha"], "estimada"),  # Viña del Hombre 17
    "POD019750": (["Callet", "Mantonegro"], "estimada"),     # Alba Rose 24 (Mallorca)
    "POD019177": (["Callet", "Fogoneu", "Mantonegro"], "alta"),  # 4 kilos 23 (Mallorca)
    "POD019734": (["Callet", "Mantonegro"], "estimada"),     # Son Agulló 22 (Mallorca)
    "POD019765": (["Airén"], "estimada"),          # Las Tinadas 20 (Castilla-La Mancha)
    "POD019465": (["Albillo Real"], "alta"),       # Ponce Albilla BL 24 (Manchuela)
    "POD019752": (["Bobal", "Garnacha"], "estimada"),  # El Reflejo de Mikaela 22

    # ── FRANCE – ALSACE / JURA (agent aa3a7f4) ─────────────
    "POD015678": (["Riesling"], "alta"),   # Schieferkopf Fels 2016
    "POD017256": (["Riesling"], "alta"),   # Trimbach Clos Saint Hune 2018
    "POD012872": (["Riesling"], "alta"),   # Trimbach Frédéric Emile 2017
    "POD016661": (["Savagnin"], "alta"),   # Macle Côtes du Jura Sous Voile
    "POD017569": (["Savagnin"], "alta"),   # Macle Château Chalon 2018
    "POD017004": (["Savagnin"], "alta"),   # Tissot Château Chalon 2016
    "POD019656": (["Poulsard"], "alta"),   # Pieds Sur Terre Poulsard 2023
    "POD017000": (["Poulsard"], "alta"),   # Tissot Arbois Poulsard VV 2023

    # ── FRANCE – LANGUEDOC / ROUSSILLON ─────────────────────
    "POD016980": (["Chardonnay", "Viognier", "Sauvignon Blanc"], "alta"),  # Cigalus Blanc 2023
    "POD019790": (["Grenache Blanc", "Vermentino", "Viognier"], "estimada"),  # Villa Soleia 2021
    "POD016246": (["Grenache", "Carignan"], "alta"),    # Clos des Fées Petit Sibérie
    "POD016245": (["Grenache", "Carignan", "Syrah"], "alta"),   # Clos des Fées VV
    "POD017927": (["Syrah", "Mourvèdre", "Cabernet Sauvignon"], "alta"),  # Grange des Pères 2021
    "POD017308": (["Grenache", "Syrah", "Mourvèdre", "Carignan"], "alta"),  # Clos d'Ora
    "POD017888": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Château L'Hospitalet
    "POD018173": (["Grenache", "Cinsault", "Syrah", "Viognier"], "alta"),  # Clos du Temple (rosé)
    "POD019733": (["Grenache", "Cinsault", "Vermentino"], "estimada"),  # Source of Joy 2024

    # ── FRANCE – LOIRE ───────────────────────────────────────
    "POD019376": (["Sauvignon Blanc"], "alta"),   # Cherrier Cuvée Phillipa (Sancerre)
    "POD018160": (["Chenin Blanc"], "alta"),      # Clos Rougeard Brézé 2019
    "POD011634": (["Chenin Blanc"], "alta"),      # Clos Rougeard Brézé 2018
    "POD017920": (["Sauvignon Blanc"], "alta"),   # Dagueneau Blanc Fumé ETC 2022
    "POD018056": (["Sauvignon Blanc"], "alta"),   # Dagueneau Mont Damné 2022
    "POD017921": (["Sauvignon Blanc"], "alta"),   # Dagueneau Pur Sang 2022
    "POD017787": (["Sauvignon Blanc"], "alta"),   # Dagueneau Silex 2009
    "POD017923": (["Sauvignon Blanc"], "alta"),   # Dagueneau Silex 2022
    "POD017922": (["Sauvignon Blanc"], "alta"),   # Dagueneau Buisson Renard 2022
    "POD011987": (["Sauvignon Blanc"], "alta"),   # Dagueneau XXI 2021
    "POD013215": (["Sauvignon Blanc"], "alta"),   # Bouchot MCMLV 2022
    "POD013216": (["Sauvignon Blanc"], "alta"),   # Bouchot Terres Blanches 2022
    "POD015332": (["Chenin Blanc"], "alta"),      # Eric Morgat Anjou Croisée 2017
    "POD010021": (["Chenin Blanc"], "alta"),      # Eric Morgat Fides 2018
    "POD019467": (["Sauvignon Blanc"], "alta"),   # Pascal Cotat La Grande Côte
    "POD019468": (["Sauvignon Blanc"], "alta"),   # Pascal Cotat Monts Damnés
    "POD019764": (["Cabernet Franc"], "alta"),    # Antoine Sanzay Saumur Les Poyeux
    "POD018159": (["Cabernet Franc"], "alta"),    # Clos Rougeard Le Bourg 2019
    "POD018157": (["Cabernet Franc"], "alta"),    # Clos Rougeard Le Clos 2019
    "POD011632": (["Cabernet Franc"], "alta"),    # Clos Rougeard Les Poyeux 2018
    "POD018158": (["Cabernet Franc"], "alta"),    # Clos Rougeard Saumur Les Poyeux 2019
    "POD018161": (["Cabernet Franc"], "alta"),    # Closiers Les Closiers 2023
    "POD018162": (["Cabernet Franc"], "alta"),    # Closiers Les Coudraies 2021
    "POD018163": (["Cabernet Franc"], "alta"),    # Closiers Trézellières 2021
    "POD019763": (["Cabernet Franc"], "alta"),    # Guiberteau Arboises 2022

    # ── FRANCE – PROVENCE ────────────────────────────────────
    "POD017306": (["Grenache", "Cinsault", "Rolle"], "alta"),   # Whispering Angel (rosé)
    "POD016928": (["Cinsault", "Grenache", "Syrah", "Rolle"], "alta"),  # Miraval (rosé)
    "POD018029": (["Grenache", "Cinsault", "Cabernet Sauvignon", "Tibouren"], "alta"),  # Ott Selle (rosé)

    # ── FRANCE – RHÔNE ───────────────────────────────────────
    "POD017847": (["Marsanne"], "alta"),           # Chapoutier De L'Orée (Hermitage BL)
    "POD016414": (["Marsanne"], "alta"),           # Chapoutier Le Méal BL 2010
    "POD013867": (["Marsanne"], "alta"),           # Chapoutier Saint-Joseph Deschants BL
    "POD016430": (["Grenache Blanc", "Clairette", "Bourboulenc"], "alta"),  # Domaine des Tours Vaucluse BL
    "POD019267": (["Viognier"], "alta"),           # Vernay Condrieu Terrasses
    "POD019270": (["Viognier"], "alta"),           # Vernay Condrieu Coteau de Vernon
    "POD019327": (["Grenache Blanc", "Clairette", "Roussanne", "Bourboulenc"], "alta"),  # Le Vieux Donjon CDP BL
    "POD017484": (["Grenache", "Mourvèdre", "Syrah"], "alta"),  # Tardieu-Laurent CDP Cuvée Spéciale
    "POD017483": (["Grenache Blanc", "Clairette", "Roussanne"], "alta"),  # Tardieu-Laurent Nobles Origines BL
    "POD017486": (["Marsanne", "Roussanne"], "alta"),  # Tardieu-Laurent Hermitage BL
    "POD017827": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Chapoutier Croix de Bois (Rasteau)
    "POD017825": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Chapoutier La Mordorée (CDP)
    "POD017824": (["Syrah"], "alta"),              # Chapoutier Le Méal (Hermitage rouge)
    "POD011777": (["Syrah"], "alta"),              # Chapoutier Le Pavillon 2014
    "POD017826": (["Syrah"], "alta"),              # Chapoutier Les Granits (Saint-Joseph rouge)
    "POD013983": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Château des Tours 2019
    "POD018469": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Château des Tours 2020
    "POD011715": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Château des Tours CDR 2019
    "POD017931": (["Grenache"], "alta"),           # Château Rayas 2008
    "POD018475": (["Grenache"], "alta"),           # Château Rayas 2009
    "POD009898": (["Grenache"], "alta"),           # Château Rayas 2010
    "POD016879": (["Grenache"], "alta"),           # Château Rayas 2011
    "POD018165": (["Syrah", "Grenache"], "alta"),  # Clape CDR 2023
    "POD018474": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Domaine des Tours 2007
    "POD013984": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Domaine des Tours Vaucluse 2020
    "POD019269": (["Syrah", "Viognier"], "alta"),  # Vernay Côte-Rôtie Blonde du Seigneur
    "POD018167": (["Syrah"], "alta"),              # Gérin Champin Le Seigneur
    "POD018168": (["Syrah"], "alta"),              # Gérin Les Grandes Places
    "POD016703": (["Grenache"], "alta"),           # Henri Bonneau Réserve des Célestins
    "POD015816": (["Grenache"], "alta"),           # Henri Bonneau VdF Rouliers
    "POD012541": (["Syrah"], "alta"),              # Souhaut La Souteronne 2022
    "POD019292": (["Syrah"], "alta"),              # Souhaut La Souteronne 2023
    "POD017556": (["Grenache", "Syrah", "Mourvèdre"], "alta"),  # Pierre Usseglio CDP 2007

    # ── USA – CALIFORNIA (agent aab9a9a) ─────────────────────
    "POD012659": (["Sauvignon Blanc"], "alta"),    # Eisele Vineyard SB 21
    "POD017494": (["Chardonnay"], "alta"),         # Kistler Les Noisetiers BL
    "POD017498": (["Chardonnay"], "alta"),         # Sandhi SRH Chardonnay
    "POD017790": (["Roussanne", "Chardonnay", "Viognier", "Grenache Blanc"], "estimada"),  # SQN Distenta BL
    "POD011420": (["Cabernet Sauvignon", "Cabernet Franc", "Merlot", "Petit Verdot"], "alta"),  # Bond Pluribus
    "POD011421": (["Cabernet Sauvignon"], "alta"), # Bond Quella 19
    "POD016171": (["Tempranillo"], "alta"),        # Cayuse Impulsivo 20 (Walla Walla Tempranillo)
    "POD018345": (["Pinot Noir"], "alta"),         # Ceritas Peter Martin Ray
    "POD016882": (["Cabernet Franc", "Cabernet Sauvignon"], "alta"),  # Dalla Valle Maya
    "POD017490": (["Pinot Noir"], "alta"),         # Domaine de la Côte Estate
    "POD019314": (["Cabernet Sauvignon", "Cabernet Franc", "Merlot"], "alta"),  # Eisele Altagracia
    "POD010951": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc", "Petit Verdot"], "alta"),  # Harlan Estate 19
    "POD017496": (["Pinot Noir"], "alta"),         # Kistler Sonoma Coast TO
    "POD017553": (["Cabernet Sauvignon"], "alta"), # La Joie 13 (Staglin)
    "POD017558": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc", "Petit Verdot"], "alta"),  # Harlan Estate (other vintage if different)
    "POD012447": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc", "Petit Verdot", "Malbec"], "alta"),  # Opus One 2021
    "POD017710": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc", "Petit Verdot", "Malbec"], "alta"),  # Opus One Overture
    "POD017813": (["Cabernet Sauvignon", "Cabernet Franc", "Merlot", "Petit Verdot"], "alta"),  # Promontory 2016
    "POD018702": (["Cabernet Sauvignon", "Cabernet Franc", "Merlot", "Petit Verdot"], "alta"),  # Promontory 2018
    "POD018703": (["Cabernet Sauvignon", "Cabernet Franc", "Merlot", "Petit Verdot"], "alta"),  # Promontory 2019
    "POD016544": (["Cabernet Sauvignon", "Cabernet Franc", "Merlot", "Petit Verdot"], "alta"),  # Promontory 2015
    "POD017499": (["Pinot Noir"], "alta"),         # Sandhi SRH Pinot Noir
    "POD017795": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # Screaming Eagle 2007
    "POD015792": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # SE 2011
    "POD015791": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # SE 2012
    "POD015790": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # SE 2013
    "POD015789": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # SE 2018
    "POD015788": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # SE 2019
    "POD015784": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # SE 2020
    "POD015783": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # SE 2021
    "POD015786": (["Cabernet Sauvignon", "Merlot", "Cabernet Franc"], "alta"),  # SE The Flight 2020
    "POD017503": (["Merlot", "Cabernet Sauvignon", "Cabernet Franc", "Malbec"], "alta"),  # Shafer TD-9
    "POD016892": (["Grenache"], "alta"),           # SQN Chemin Vers l'Hérésie Grenache 2015
    "POD012430": (["Grenache", "Syrah"], "estimada"),  # SQN Cumulus/Next of Kyn 2017
    "POD017504": (["Syrah"], "alta"),              # SQN Distenta III Syrah 2021
    "POD017933": (["Syrah", "Grenache", "Roussanne"], "estimada"),  # SQN Rattrapante 2012
    "POD017242": (["Syrah", "Grenache"], "alta"),  # SQN Short in the Dark 2006
    "POD017932": (["Grenache", "Syrah"], "alta"),  # SQN Touche 2012

    # ── ITALY – CAMPANIA ─────────────────────────────────────
    "POD014827": (["Fiano"], "alta"),              # Quintodecimo Exultet (Fiano d'Avellino)
    "POD015694": (["Fiano"], "alta"),              # Terredora Campore Riserva
    "POD018191": (["Greco"], "alta"),              # Terredora Loggia della Serra (Greco di Tufo)

    # ── ITALY – PIEMONTE ─────────────────────────────────────
    "POD019460": (["Nascetta"], "estimada"),       # Baricchi Ça Va Sans Dire 2016
    "POD016873": (["Chardonnay"], "alta"),         # Gaja Gaia & Rey Langhe Chard
    "POD014184": (["Chardonnay", "Sauvignon Blanc"], "alta"),  # Gaja Rossj-Bass
    "POD018869": (["Chardonnay"], "alta"),         # Pio Cesare L'Altro 2024
    "POD018408": (["Barbera"], "alta"),            # Cascina Roera Barbera d'Alba Tre Stelle
    "POD018410": (["Barbera"], "alta"),            # Cascina Rose Barbera Marcorino
    "POD018409": (["Barbera"], "alta"),            # Cascina Rose Barbera Rio Sordo
    "POD018407": (["Nebbiolo"], "alta"),           # Cascina Rose Langhe Nebbiolo
    "POD019754": (["Nebbiolo"], "alta"),           # Ferdinando Principiano Langhe Nebbiolo
    "POD015862": (["Nebbiolo"], "alta"),           # Gaja Sperss Barolo
    "POD017547": (["Nebbiolo"], "alta"),           # Giovanni Canonica Barolo
    "POD014760": (["Nebbiolo"], "alta"),           # Pelissero Vanotu Barbaresco
    "POD018430": (["Nebbiolo"], "alta"),           # Roagna Barbaresco Crichet Pajé
    "POD011998": (["Nebbiolo"], "alta"),           # Trediberri Barolo Rocche dell'Annunziata
    "POD018722": (["Riesling"], "alta"),           # G.D. Vajra Aurelj Contracorrente (Riesling!)

    # ── ITALY – SICILIA ──────────────────────────────────────
    "POD017654": (["Carricante"], "alta"),         # Terre Nere Calderara Sottana BL 22
    "POD018790": (["Carricante"], "alta"),         # Terre Nere Calderara Sottana BL 23
    "POD018788": (["Carricante"], "alta"),         # Terre Nere Salice BL 23
    "POD018791": (["Carricante"], "alta"),         # Terre Nere Santo Spirito BL 23
    "POD019760": (["Nero d'Avola", "Nerello Mascalese"], "estimada"),  # Firriato Soria 22
    "POD019447": (["Frappato"], "alta"),           # Arianna Occhipinti Il Frappato (NOT Nero!)
    "POD017655": (["Nerello Mascalese"], "alta"),  # Terre Nere Calderara Rosso 22
    "POD017653": (["Nerello Mascalese"], "alta"),  # Terre Nere Bellacolonna
    "POD017657": (["Nerello Mascalese"], "alta"),  # Terre Nere Moganazzi
    "POD018797": (["Nerello Mascalese"], "alta"),  # Terre Nere Santo Spirito Rosso

    # ── ITALY – TOSCANA ──────────────────────────────────────
    "POD018290": (["Vermentino", "Viognier"], "estimada"),  # Colle Massari Melacce BL
    "POD014226": (["Vernaccia"], "alta"),          # Guicciardini Strozzi Vernaccia di SG
    "POD011999": (["Sangiovese"], "alta"),         # Cerbaiona Grammatica
    "POD017917": (["Sangiovese Grosso"], "alta"),  # Le Ragnaie Lume Spento Brunello
    "POD011837": (["Sangiovese", "Canaiolo"], "alta"),  # Monteraponi Bragantino
    "POD014661": (["Sangiovese", "Canaiolo", "Colorino"], "alta"),  # Montevertine 2019
    "POD017916": (["Sangiovese Grosso"], "alta"),  # Le Ragnaie Brunello Casanovina Montosoli
    "POD019759": (["Cabernet Sauvignon", "Merlot"], "alta"),  # Tenuta San Guido Guidalberto

    # ── ITALY – ALTO ADIGE / VENETO ──────────────────────────
    "POD019792": (["Kerner"], "alta"),             # Pacherhof Kerner 2023
    "POD014977": (["Sauvignon Blanc"], "alta"),    # Cantina Terlano Quartz
    "POD014940": (["Garganega"], "alta"),          # Suavia Soave Monte Carbonare

    # ── ARGENTINA ────────────────────────────────────────────
    "POD019649": (["Chardonnay"], "estimada"),     # Escala Humana Credo 2022
    "POD019796": (["Torrontés"], "estimada"),      # Lágrima de Canela 2020
    "POD018152": (["Chardonnay", "Viognier"], "estimada"),  # Michelini Agua Roca BL
    "POD019628": (["Malbec", "Cabernet Franc"], "estimada"),  # Bira Rosso d'Uco 2023
    "POD019629": (["Cabernet Sauvignon", "Malbec", "Petit Verdot", "Cabernet Franc"], "alta"),  # Bressia Conjuro
    "POD018941": (["Malbec"], "alta"),             # Catena Zapata Nicasia Malbec
    "POD015922": (["Cabernet Franc"], "alta"),     # Gran Enemigo Gualtallary (100% CF!)
    "POD018146": (["Malbec", "Cabernet Franc"], "estimada"),  # PerSe Inseparable
    "POD018148": (["Malbec"], "estimada"),         # PerSe Lubileus
    "POD018149": (["Chardonnay"], "estimada"),     # PerSe La Craie
    "POD018147": (["Malbec", "Cabernet Sauvignon", "Cabernet Franc"], "estimada"),  # PerSe Volare
    "POD018154": (["Cabernet Franc"], "alta"),     # Riccitelli CF de la Montaña
    "POD019631": (["Malbec", "Cabernet Franc", "Cabernet Sauvignon"], "estimada"),  # Vuelo Andino Blend
    "POD018153": (["Malbec", "Cabernet Franc"], "estimada"),  # Y La Nave Va 2020
    "POD018510": (["Malbec"], "alta"),             # Zuccardi Valle Concreto Malbec
    "POD011185": (["Malbec"], "alta"),             # Zuccardi Piedra Infinita 2019
    "POD011157": (["Malbec"], "alta"),             # Zuccardi Piedra Infinita Gravascal
    "POD018092": (["Malbec"], "alta"),             # Zuccardi Piedra Infinita Supercal
    "POD018093": (["Malbec"], "alta"),             # Zuccardi Polígonos San Pablo

    # ── AUSTRALIA ────────────────────────────────────────────
    "POD012451": (["Cabernet Sauvignon"], "alta"),  # Penfolds Bin 707 CS 2022
    "POD017648": (["Cabernet Sauvignon"], "alta"),  # Penfolds Bin 707 CS 2018
    "POD012464": (["Shiraz"], "alta"),              # Penfolds RWT Bin 798 Barossa Shiraz
    "POD012461": (["Shiraz", "Cabernet Sauvignon"], "alta"),  # Penfolds St Henri
    "POD017646": (["Grenache", "Shiraz", "Mourvèdre"], "estimada"),  # Penfolds g3 Superblend
    "POD016832": (["Shiraz", "Viognier"], "alta"),  # The Standish The Relic
    "POD016833": (["Shiraz"], "alta"),              # The Standish The Schubert Theorem
    "POD016834": (["Shiraz", "Viognier"], "alta"),  # The Standish The Standish
    "POD018536": (["Syrah"], "alta"),               # Timo Mayer Bloody Hill Syrah
    "POD018534": (["Pinot Noir"], "alta"),           # Timo Mayer Close Planted PN
    "POD018535": (["Pinot Noir"], "alta"),           # Timo Mayer The Doktor
    "POD018216": (["Shiraz", "Viognier"], "alta"),   # Torbreck Runrig 2020
    "POD018217": (["Shiraz", "Viognier"], "alta"),   # Torbreck Runrig 2021
    "POD018221": (["Shiraz"], "alta"),               # Torbreck The Laird
    "POD018212": (["Shiraz"], "alta"),               # Torbreck The Struie

    # ── PORTUGAL ─────────────────────────────────────────────
    "POD019338": (["Rabigato", "Viosinho", "Gouveio", "Arinto"], "alta"),  # Niepoort Coche Branco
    "POD013118": (["Baga", "Bical", "Maria Gomes"], "alta"),   # António Madeira VV (Bairrada)
    "POD013111": (["Baga"], "alta"),               # Filipa Pato DNMC Baga
    "POD019335": (["Baga"], "alta"),               # Niepoort Bairrada Poeirinho
    "POD011809": (["Touriga Nacional", "Touriga Franca", "Tinta Barroca", "Tinta Roriz"], "alta"),  # Casa Ferreirinha Rva Esp
    "POD016788": (["Touriga Nacional", "Touriga Franca", "Tinta Roriz", "Tinta Barroca"], "alta"),  # Monte Meão Vinha da Cantina
    "POD016789": (["Touriga Nacional", "Touriga Franca", "Tinta Roriz"], "alta"),  # Monte Meão Vinha dos Novos
    "POD014680": (["Touriga Nacional", "Tinta Roriz", "Tinta Amarela", "Touriga Franca"], "alta"),  # Niepoort Batuta
    "POD012649": (["Touriga Nacional", "Touriga Franca", "Tinta Roriz", "Tinta Amarela"], "alta"),  # Niepoort Charme
    "POD016808": (["Touriga Nacional", "Touriga Franca", "Tinta Roriz", "Tinta Barroca", "Tinta Amarela"], "alta"),  # QVM Douro
    "POD015577": (["Touriga Nacional", "Tinta Roriz", "Touriga Franca"], "estimada"),  # Xisto Cru

    # ── SOUTH AFRICA ─────────────────────────────────────────
    "POD015864": (["Chardonnay"], "alta"),         # Springfield Méthode Ancienne Chard
    "POD018073": (["Chardonnay"], "alta"),         # Storm Wines Vrede Chardonnay
    "POD019671": (["Syrah", "Grenache", "Mourvèdre"], "alta"),  # Richard Kershaw Smuggler's Boot
    "POD018076": (["Chenin Blanc"], "alta"),       # Savage Wines Follow the Line

    # ── NEW ZEALAND ──────────────────────────────────────────
    "POD018222": (["Pinot Noir"], "alta"),         # Escarpment Pahi PN

    # ── CHILE ────────────────────────────────────────────────
    "POD019731": (["Riesling"], "alta"),           # Baettig Los Parientes

    # ── GERMANY ──────────────────────────────────────────────
    "POD018213": (["Pinot Noir"], "alta"),         # Twardowski Ardoise Spätburgunder
}


def apply_corrections(input_path, output_path):
    print(f"Loading {input_path}...")
    with open(input_path, encoding='utf-8') as f:
        wines = json.load(f)

    print(f"Total wines: {len(wines)}")

    updated = 0
    pod_updated = 0
    systematic_bierzo_red = 0
    systematic_toro = 0
    skipped_none_pod = 0

    for wine in wines:
        pod = wine.get('pod')
        region = (wine.get('region') or '').lower()
        tipo_codigo = (wine.get('tipo') or {}).get('codigo', '')
        current_confidence = wine.get('uvas_confianza')

        changed = False

        # 1. POD-specific corrections (highest priority)
        if pod and pod in corrections_by_pod:
            new_uvas, new_confianza = corrections_by_pod[pod]
            old_uvas = wine.get('uvas', [])
            old_conf = wine.get('uvas_confianza')

            if old_uvas != new_uvas or old_conf != new_confianza:
                wine['uvas'] = new_uvas
                wine['uvas_confianza'] = new_confianza
                pod_updated += 1
                changed = True

        # 2. Systematic correction: Bierzo reds → Mencía
        elif 'bierzo' in region and tipo_codigo == 'TO' and current_confidence != 'alta':
            if wine.get('uvas') != ['Mencía']:
                wine['uvas'] = ['Mencía']
                wine['uvas_confianza'] = 'estimada'
                systematic_bierzo_red += 1
                changed = True

        # 3. Systematic correction: Toro reds → Tinta de Toro
        elif 'toro' in region and tipo_codigo == 'TO' and current_confidence != 'alta':
            if wine.get('uvas') != ['Tinta de Toro']:
                wine['uvas'] = ['Tinta de Toro']
                wine['uvas_confianza'] = 'estimada'
                systematic_toro += 1
                changed = True

        if pod is None and changed:
            skipped_none_pod += 1

        if changed:
            updated += 1

    print(f"\n{'='*50}")
    print(f"Corrections applied:")
    print(f"  POD-specific corrections:  {pod_updated}")
    print(f"  Bierzo reds → Mencía:      {systematic_bierzo_red}")
    print(f"  Toro reds → Tinta de Toro: {systematic_toro}")
    print(f"  Total wines updated:        {updated}")
    print(f"{'='*50}")

    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(wines, f, ensure_ascii=False, indent=2)

    # Verify result
    remaining_uncertain = sum(1 for w in wines if w.get('uvas_confianza') != 'alta')
    remaining_estimada = sum(1 for w in wines if w.get('uvas_confianza') == 'estimada')
    remaining_null = sum(1 for w in wines if w.get('uvas_confianza') is None)
    alta_count = sum(1 for w in wines if w.get('uvas_confianza') == 'alta')

    print(f"\nFinal state:")
    print(f"  alta:     {alta_count}")
    print(f"  estimada: {remaining_estimada}")
    print(f"  null:     {remaining_null}")
    print(f"  uncertain total: {remaining_uncertain}")
    print("\nDone!")


if __name__ == '__main__':
    apply_corrections('data/bodega_webapp.json', 'data/bodega_webapp.json')
