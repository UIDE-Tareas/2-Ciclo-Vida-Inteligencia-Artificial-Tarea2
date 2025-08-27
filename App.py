import sys
import subprocess
import argparse
import os
from pathlib import Path
import random

LIBS = [
    "customtkinter",
    "requests",
]

models = ["gpt-4o-mini", "gpt-4.1", "o3-mini", "nuevo-1", "nuevo-2", "nuevo-3"]
def RunCommand(commandList: list[str], printCommand: bool = True, printError:bool=True) -> subprocess.CompletedProcess:
    print("⏳", " ".join(commandList))
    stdOutput = None if printCommand else subprocess.DEVNULL
    errorOutput = None if printError else subprocess.PIPE
    result = subprocess.run(commandList,stdout=stdOutput, stderr=errorOutput, text=True)
    if result.returncode != 0 and printError:
        print(result.stderr) 
    return result

def ShowEnvInfo():
    print("ℹ️  Environment Info:")
    print("Python Version:", sys.version)
    print("Platform:", sys.platform)
    print("Executable Path:", sys.executable)
    print("Current Working Directory:", os.getcwd())
    print("VIRTUAL_ENV:", os.environ.get("VIRTUAL_ENV"))
    print("sys.prefix:", sys.prefix)
    print("sys.base_prefix:", sys.base_prefix)

def InstallDeps():
    print("🟦 Installing deps.")
    RunCommand([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], printCommand=True) 
    RunCommand([sys.executable, "-m", "pip", "install", *LIBS], printCommand=True) 

ShowEnvInfo()
InstallDeps()

import customtkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
import requests
import json
import re

BASE_URL = "http://localhost:11434/api/generate"
MODELS_URL = "http://localhost:11434/api/tags"
MAX_TOKENS = 150

def fetch_models(alert_on_ok=False):
    try:
        response = requests.get(MODELS_URL)
        response.raise_for_status()
        models = response.json().get("models", [])
        if alert_on_ok:
            messagebox.showinfo("Info", f"Modelos actualizados: \n•{'\n• '.join([model['name'] for model in models])}")
        return [model["name"] for model in models]
    except requests.RequestException as e:
        messagebox.showerror("Error", f"Error fetching models: {e}")
        return []

def process_prompt(user_input):
    ethical_prompt = (
        "Como sistema de IA, asegurase de que sus respuestas sean imparciales, éticas y cumplan con las regulaciones de la IA. "
        "Considere la equidad, la privacidad y la inclusión en su respuesta. "
        "Por favor no respondas a preguntas que puedan ser censuradas con su contenido. "
        "Tus mensajes no deben ser mayores de doscientas palabras. "
        "Todas tus respuestas deben ser en Español."
        "Concéntrate en responder únicamente lo que voy a preguntar después de este párrafo y tomando en cuenta cada punto anterior. No quiero que me digas o expliques que estás considerando todos los puntos anteriores. "
    )
    return ethical_prompt + user_input

root = tk.CTk()
root.title("Chatbot ético - Grupo 5")
root.geometry("800x800")
root.configure(bg="#dbd5d5")
tk.set_appearance_mode("light")
tk.set_default_color_theme("blue")


menu_frame = tk.CTkFrame(root)
menu_frame.pack(pady=5, padx=5, fill="x")

model_label = tk.CTkLabel(menu_frame, text="Modelo:", font=("Arial", 12))
model_label.pack(side="left", padx=(0, 5))
models = fetch_models()
modelStringvar = tk.StringVar(value=models[0] if models else "")
model_menu = tk.CTkOptionMenu(menu_frame, variable=modelStringvar, values=models, width=150, font=("Arial", 10))
model_menu.pack(side="left", padx=(0, 15))

def refresh_models():
    models = fetch_models(True)
    if models:
        model_menu.configure(values=models)
        modelStringvar.set(models[0])
    else:
        model_menu.configure(values=[""])
        modelStringvar.set("")

btnRefresh = tk.CTkButton(
    menu_frame,
    text="Actualizar Modelos",
    command=lambda: refresh_models(),
    font=("Arial", 10)
).pack(side="left", padx=(0, 15))

temp_label = tk.CTkLabel(menu_frame, text="Temperatura:", font=("Arial", 12))
temp_label.pack(side="left", padx=(0, 5))
temp_var = tk.DoubleVar(value=0.7)
def update_temp_value(value):
    temp_value_label.configure(text=f"{float(value):.2f}")
temp_menu = tk.CTkSlider(menu_frame, variable=temp_var, from_=0.0, to=2.0, number_of_steps=10, width=120, command=update_temp_value)
temp_menu.pack(side="left")
temp_value_label = tk.CTkLabel(menu_frame, text=f"{temp_var.get():.2f}", font=("Arial", 12))
temp_value_label.pack(side="left", padx=(5, 0))

chat_frame = tk.CTkScrollableFrame(root, width=800, height=500)
chat_frame.pack(pady=5, padx=5, fill="both", expand=True)


welcome_label = tk.CTkLabel(
    chat_frame, text="Hola, ¿en qué te puedo ayudar?", anchor="center", justify="center",
    font=("Arial", 11), fg_color="#f5f5f5", text_color="#222", width=500
)
welcome_label.pack(anchor="center", pady=(10, 2), padx=10, fill="x")

input_label = tk.CTkLabel(root, text="Ingrese una pregunta:", fg_color="#f0f0f0", font=("Arial", 12))
input_label.pack(pady=5, padx=5)

input_frame = tk.CTkFrame(root)
input_frame.pack(pady=5, padx=5, fill="x")

user_input_field = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, width=60, height=4, font=("Arial", 10))
user_input_field.pack(side="left", pady=5, padx=(0, 5), fill="x", expand=True)

send_button = tk.CTkButton(
    input_frame,
    text="Enviar",
    command=lambda: get_ai_response(),
    width=100,
    height=90,
    font=("Arial", 12)
)
send_button.pack(side="left", pady=5, padx=(5, 0), fill="y")

def on_enter(event):
    get_ai_response()
    return "break"

user_input_field.bind("<Return>", on_enter)

def set_text(widget, text, min_lines=1, max_lines=100, px_per_line=18):
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", text)
    try:
        # widget._textbox es el tk.Text interno de CustomTkinter
        display_lines = widget._textbox.count("1.0", "end-1c", "displaylines")[0]
        display_lines = max(min_lines, min(display_lines, max_lines))
        widget.configure(height=int(display_lines * px_per_line))
    except Exception:
        # Fallback si no existe count/displaylines
        widget.update_idletasks()
        info = widget._textbox.dlineinfo("end-1c")
        if info:  # (x, y, w, h, baseline)
            y, h = info[1], info[3]
            total_px = y + h + 6  # pequeño margen
            total_px = max(int(min_lines * px_per_line),
                           min(total_px, int(max_lines * px_per_line)))
            widget.configure(height=total_px)
    widget.configure(state="disabled")

def get_ai_response():
    user_input = user_input_field.get("1.0", tk.END).strip()
    if not user_input:
        return
    user_input_field.delete("1.0", tk.END)

  
    user_label = tk.CTkLabel(
        chat_frame, text=user_input, anchor="e", justify="right",
        font=("Arial", 11), fg_color="#e1eaff", text_color="#222", width=500, wraplength=700, padx=5, pady=5
    )
    user_label.pack(anchor="e", pady=(10, 2), padx=10, fill="x")
    chat_frame._parent_canvas.yview_moveto(1.0)
    

    ia_entry = tk.CTkTextbox(
        chat_frame,
        width=500,
        font=("Arial", 11),
        fg_color="#f5f5f5",
        text_color="#888",
        wrap="word",
    )
    set_text(ia_entry, "Escribiendo...", max_lines=1)
    ia_entry.pack(anchor="w", pady=(2, 10), padx=10, fill="x")

    chat_frame._parent_canvas.yview_moveto(1.0)

    root.update_idletasks()

    modified_prompt = process_prompt(user_input)
    selected_model = modelStringvar.get()
    temperature = temp_var.get()
    import time
    start_time = time.time()
    try:
        response = requests.post(
            BASE_URL,
            json={
                "model": selected_model,
                "prompt": modified_prompt,
                "max_tokens": MAX_TOKENS,
                "temperature": temperature,
                "stream": True
            }
        )
        response.raise_for_status()
        complete_response = ""
        for line in response.iter_lines(decode_unicode=True):
            if line:
                data = json.loads(line)
                if "response" in data:
                    complete_response += data["response"]

        if "deepseek" in selected_model.lower():
            complete_response = re.sub(r'<think>.*?</think>', '', complete_response, flags=re.DOTALL).strip()

        elapsed = time.time() - start_time
    
        ia_entry.configure(text_color="#222")
        set_text(ia_entry, complete_response)

        time_label = tk.CTkLabel(
            chat_frame,
            text=f"{selected_model}  |  {elapsed:.2f} s",
            anchor="e",
            justify="right",
            font=("Arial", 9),
            fg_color="#f5f5f5",
            text_color="#888",
            width=500, wraplength=480, padx=5, pady=2
        )
        time_label.pack(anchor="e", pady=(0, 10), padx=10, fill="x")
        root.update_idletasks()
        chat_frame._parent_canvas.yview_moveto(1.0)

    except requests.RequestException as e:
        ia_entry.configure(text_color="#c00")
        ia_entry.insert(0,text=f"Error al obtener respuesta: {e}")
        root.update_idletasks()
        chat_frame._parent_canvas.yview_moveto(1.0)

root.mainloop()