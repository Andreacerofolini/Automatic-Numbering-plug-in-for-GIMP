#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
#
# (c) Andrea Cerofolini & Michele Bertoncini 2025
#
#   History:
#
#   v1.0: 25/02/2025 First published version
#   v1.1: 21/05/2025 Improved text and rectangle sizing
#   v1.2: 21/05/2025 Fixed text visibility issues
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
#   This plug-in is inspired by (c) Ofnuts 2018, v0.0

import os
import re
from gimpfu import *
import datetime

# Definizione delle costanti
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PLUGIN_DIR, "data")
PARAMETERS_FILE = os.path.join(DATA_DIR, "parameters.txt")

# Assicurati che la directory dei dati esista
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Variabile globale per i parametri
global_params = {}

def aggiungi_zeri(number, num_digits):
    """Add zeros to the left of the number until you reach num_digits."""
    return str(number).zfill(num_digits)

def load_parameters():
    global global_params
    default_params = {
        "museum_code": "MUS",
        "collection_code": "COL",
        "font": "Arial Bold",
        "font_size": 20,
        "start_number": 1
    }
    
    if not os.path.exists(PARAMETERS_FILE):
        log_debug("Parameters file not found. Using default values.")
        global_params = default_params
        save_parameters() 
        return

    try:
        with open(PARAMETERS_FILE, 'r') as f:
            lines = f.readlines()
        
        params = {}
        for line in lines:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                params[key.strip()] = value.strip()
        
        for key, default_value in default_params.items():
            if key not in params:
                params[key] = default_value
            elif isinstance(default_value, int):
                params[key] = int(params[key])
        
        global_params = params
    except IOError as e:
        log_debug("Error loading parameters: %s. Using default values." % str(e))
        global_params = default_params

def save_parameters():
    """Save the correct parameters in the file"""
    global global_params
    try:
        with open(PARAMETERS_FILE, 'w') as f:
            for key, value in global_params.items():
                f.write("%s=%s\n" % (key, value))
    except IOError as e:
        log_debug("Error saving parameters: %s" % str(e))

def update_parameter(key, value):
    """Update single parameter and save the changes."""
    global global_params
    global_params[key] = value
    save_parameters()

def log_debug(message):
    """Print debug message with timestamp."""
    log_file = os.path.join(DATA_DIR, "debug_log.txt")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, 'a') as f:
        f.write("%s - %s\n" % (timestamp, message))

def pointsSequence(image, drawable, path, font, fontSize, auto_size, boxWidth, boxHeight, rectangle_opacity, 
                   museum_code, collection_code, use_saved_number, user_start_number, num_cifre, 
                   custom_field, custom_field_position):
    global global_params
    
    # Carica i parametri all'inizio della funzione
    load_parameters()
    
    if use_saved_number:
        start_number = global_params["start_number"]
        pdb.gimp_message("Using saved start number: %d" % start_number)
    else:
        if user_start_number == "" or not user_start_number.isdigit():
            start_number = global_params["start_number"]  # Usa il numero salvato se il campo è vuoto
            pdb.gimp_message("Using saved start number: %d (since no number was provided)" % start_number)
        else:
            start_number = int(user_start_number)
            update_parameter("start_number", start_number)
            pdb.gimp_message("Using user-provided start number: %d" % start_number)
    
    log_debug("Using start number: %d" % start_number)

    if museum_code:
        update_parameter("museum_code", museum_code)
    if collection_code:
        update_parameter("collection_code", collection_code)
    if font:
        update_parameter("font", font)
    if fontSize:
        update_parameter("font_size", int(fontSize))

    log_debug("Starting pointsSequence with parameters: museum_code=%s, collection_code=%s, font=%s, fontSize=%d, start_number=%d" % 
              (global_params["museum_code"], global_params["collection_code"], global_params["font"], 
               global_params["font_size"], start_number))

    # Salva i colori attuali prima di cambiarli
    old_fg = pdb.gimp_context_get_foreground()
    old_bg = pdb.gimp_context_get_background()
    
    # Imposta i colori: sfondo bianco per il rettangolo, testo nero per visibilità
    pdb.gimp_context_set_background((255, 255, 255))  # Bianco per il rettangolo
    pdb.gimp_context_set_foreground((0, 0, 0))        # Nero per il testo

    image.undo_group_start()
    try:
        if path is not None:
            for stroke in path.strokes:
                points, closed = stroke.points
                anchors = [(float(points[i]), float(points[i+1])) for i in range(2, len(points), 6) if i+1 < len(points)]

                log_debug("Number of anchors found: %d" % len(anchors))

                for x, y in anchors:
                    current_number = start_number
                    start_number += 1
                    parts = [
                        str(global_params["museum_code"]),
                        str(global_params["collection_code"]),
                        aggiungi_zeri(current_number, int(num_cifre))
                    ]

                    if custom_field:
                        parts.insert(custom_field_position, str(custom_field))

                    number_with_prefix = "-".join(parts)
                    log_debug("Creating label: %s" % number_with_prefix)
                    
                    # Approccio completamente diverso: creare un layer rettangolare 
                    # e usare gimp_text_fontname per aggiungere il testo direttamente
                    
                    # 1. Calcola le dimensioni appropriate per il rettangolo
                    if auto_size:
                        # Stima delle dimensioni del testo basata sulla lunghezza della stringa
                        char_width = global_params["font_size"] * 0.6  # Stima della larghezza media di un carattere
                        text_width = len(number_with_prefix) * char_width
                        text_height = global_params["font_size"] * 1.2  # Stima dell'altezza del testo
                        
                        # Aggiungi margini extra
                        margin_x = max(20, int(global_params["font_size"] * 0.8))
                        margin_y = max(15, int(global_params["font_size"] * 0.6))
                        
                        rect_width = int(text_width + 2*margin_x)
                        rect_height = int(text_height + 2*margin_y)
                    else:
                        rect_width = int(boxWidth)
                        rect_height = int(boxHeight)
                    
                    log_debug("Rectangle dimensions: width=%d, height=%d" % (rect_width, rect_height))
                    
                    # 2. Crea il layer del rettangolo
                    rect_x = int(x - rect_width / 2)
                    rect_y = int(y - rect_height / 2)
                    rect_layer = pdb.gimp_layer_new(image, rect_width, rect_height, RGBA_IMAGE, 
                                                   "Rectangle", 100, NORMAL_MODE)
                    
                    if rect_layer is not None:
                        rect_layer.set_offsets(rect_x, rect_y)
                        image.add_layer(rect_layer, 0)
                        pdb.gimp_edit_fill(rect_layer, BACKGROUND_FILL)
                        pdb.gimp_layer_set_opacity(rect_layer, rectangle_opacity)
                        log_debug("Rectangle layer created at position: (%d, %d)" % (rect_x, rect_y))
                    
                    # 3. Calcola la posizione centrale per il testo all'interno del rettangolo
                    text_x = rect_x + int(rect_width / 2)
                    text_y = rect_y + int(rect_height / 2)
                    
                    # 4. Crea il testo come LAYER SEPARATO
                    text_layer = pdb.gimp_text_fontname(
                        image,  # Immagine
                        None,   # Drawable (None perché stiamo creando un nuovo layer)
                        text_x - int(len(number_with_prefix) * char_width / 2),  # x position centrata
                        text_y - int(global_params["font_size"] / 2),  # y position centrata
                        number_with_prefix,  # Testo
                        0,       # Border
                        TRUE,    # Antialias
                        global_params["font_size"],  # Dimensione del font
                        PIXELS,  # Unità di misura
                        global_params["font"]  # Font
                    )
                    
                    if text_layer is not None:
                        log_debug("Text layer created with text: %s" % number_with_prefix)
                    
                    # 5. Unisci i livelli
                    if text_layer is not None and rect_layer is not None:
                        merged_layer = pdb.gimp_image_merge_down(image, text_layer, CLIP_TO_BOTTOM_LAYER)
                        merged_layer.name = "Label-%s-%s-%s" % (global_params["museum_code"], global_params["collection_code"], 
                                                               aggiungi_zeri(current_number, int(num_cifre)))
                        log_debug("Layers merged: %s" % merged_layer.name)

            update_parameter("start_number", start_number)
            log_debug("Parameters saved at end of execution. Next start number: %d" % start_number)
        else:
            log_debug("Error: Input path is invalid.")
            pdb.gimp_message("Error: Input path is invalid.")
            return
    except Exception as e:
        error_message = "Error in pointsSequence: %s" % str(e)
        log_debug(error_message)
        pdb.gimp_message(error_message)
    finally:
        # Ripristina i colori originali alla fine
        pdb.gimp_context_set_foreground(old_fg)
        pdb.gimp_context_set_background(old_bg)

    image.undo_group_end()
    log_debug("Script execution completed")
    pdb.gimp_message("Script execution completed")

def get_current_parameters(param_name):
    """Gets the current value of a specific parameter."""
    global global_params
    load_parameters()  
    return global_params.get(param_name, None)

def get_last_saved_number():
    """Gets the last save number."""
    global global_params
    load_parameters()  
    return global_params.get("start_number", 1)

register(
    "python-fu-entomology-labeling",
    "Add labels to entomology specimens",
    "Add a sequence of numbers on each stroke of the input path for labeling entomology specimens",
    "Andrea Cerofolini & Michele Bertoncini",
    "Andrea Cerofolini & Michele Bertoncini",
    "2025",
    "<Image>/Filters/Entomology/Add Labels",
    "*",
    [
        (PF_VECTORS, "path", "Input path", None),
        (PF_FONT, "font", "Font", get_current_parameters("font")),
        (PF_SPINNER, "fontSize", "Font size", get_current_parameters("font_size"), (6, 400, 1)),
        (PF_TOGGLE, "auto_size", "Auto-size rectangle", True),
        (PF_SPINNER, "boxWidth", "Box width (if not auto)", 175, (1, 1000, 1)),
        (PF_SPINNER, "boxHeight", "Box height (if not auto)", 30, (1, 1000, 1)),
        (PF_SLIDER, "rectangle_opacity", "Rectangle Opacity", 100, (0, 100, 1)),
        (PF_STRING, "museum_code", "Museum Code", get_current_parameters("museum_code")),
        (PF_STRING, "collection_code", "Collection Code", get_current_parameters("collection_code")),
        (PF_TOGGLE, "use_saved_number", "Use saved start number (current: %d)" % get_last_saved_number(), True),
        (PF_STRING, "start_number", "First specimen Code (editable if Use saved number is \"No\")", ""),
        (PF_SPINNER, "num_cifre", "Number of digits", 5, (1, 10, 1)),
        (PF_STRING, "custom_field", "Custom Field (optional)", ""),
        (PF_OPTION, "custom_field_position", "Custom Field Position", 2, 
         ["Before Museum Code", "After Museum Code", "After Collection Code", "At the End"]),
    ],
    [],
    pointsSequence
)

main()