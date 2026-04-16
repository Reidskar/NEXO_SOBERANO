import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import subprocess
import os
import sys
import queue
import shutil
import webbrowser
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.join(BASE_PATH, "frontend")


class NexoDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NEXO Soberano - Centro de Control")
        self.geometry("1180x760")
        self.minsize(1024, 700)
        self.configure(bg="#0f172a")

        self.backend_proc = None
        self.frontend_proc = None
        self.running = False
        self.log_queue = queue.Queue()

        self.palette = {
            "bg": "#0f172a",
            "panel": "#111827",
            "card": "#1f2937",
            "text": "#e5e7eb",
            "ok": "#22c55e",
            "warn": "#f59e0b",
            "err": "#ef4444",
            "info": "#38bdf8",
            "violet": "#8b5cf6",
        }

        self.sources = [
            {"name": "WarRoomFeed", "type": "OBS", "priority": 1, "status": "Activo"},
            {"name": "CrisisMonitor", "type": "YouTube", "priority": 1, "status": "Activo"},
            {"name": "GeoSentinel", "type": "OSINT", "priority": 2, "status": "Activo"},
            {"name": "tvScreener", "type": "Mercado", "priority": 2, "status": "Activo"},
            {"name": "IranMonitor", "type": "Discord", "priority": 3, "status": "En cola"},
        ]

        self._build_styles()
        self._build_layout()
        self._set_badge(self.backend_badge, "Backend: OFF", self.palette["err"])
        self._set_badge(self.frontend_badge, "Frontend: OFF", self.palette["err"])
        self._set_badge(self.ia_badge, "IA: LISTA", self.palette["warn"])
        self.refresh_osint()

        self.after(250, self._drain_logs)
        self.after(2500, self._heartbeat)

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Nexo.TNotebook", background=self.palette["bg"], borderwidth=0)
        style.configure("Nexo.TNotebook.Tab", background=self.palette["card"], foreground=self.palette["text"], padding=(16, 8))
        style.map("Nexo.TNotebook.Tab", background=[("selected", self.palette["info"])], foreground=[("selected", "#0b1020")])

    def _build_layout(self):
        header = tk.Frame(self, bg=self.palette["bg"])
        header.pack(fill="x", padx=14, pady=(12, 8))

        title = tk.Label(
            header,
            text="NEXO SOBERANO · Centro de Control IA + Web",
            bg=self.palette["bg"],
            fg=self.palette["text"],
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(side="left")

        self.timestamp_label = tk.Label(
            header,
            text="",
            bg=self.palette["bg"],
            fg=self.palette["info"],
            font=("Segoe UI", 10),
        )
        self.timestamp_label.pack(side="right")

        status_row = tk.Frame(self, bg=self.palette["bg"])
        status_row.pack(fill="x", padx=14, pady=(0, 10))

        self.backend_badge = tk.Label(status_row, width=18, font=("Segoe UI", 10, "bold"), bd=0)
        self.backend_badge.pack(side="left", padx=(0, 8))
        self.frontend_badge = tk.Label(status_row, width=18, font=("Segoe UI", 10, "bold"), bd=0)
        self.frontend_badge.pack(side="left", padx=(0, 8))
        self.ia_badge = tk.Label(status_row, width=18, font=("Segoe UI", 10, "bold"), bd=0)
        self.ia_badge.pack(side="left", padx=(0, 8))

        controls = tk.Frame(status_row, bg=self.palette["bg"])
        controls.pack(side="right")

        tk.Button(controls, text="Iniciar", command=self.start_system, bg=self.palette["ok"], fg="white", relief="flat", padx=14).pack(side="left", padx=4)
        tk.Button(controls, text="Detener", command=self.stop_system, bg=self.palette["err"], fg="white", relief="flat", padx=14).pack(side="left", padx=4)
        tk.Button(controls, text="Web", command=lambda: self._open_url("http://localhost:3000/"), bg=self.palette["info"], fg="#0b1020", relief="flat", padx=14).pack(side="left", padx=4)
        tk.Button(controls, text="API", command=lambda: self._open_url("http://localhost:8080/"), bg=self.palette["violet"], fg="white", relief="flat", padx=14).pack(side="left", padx=4)

        body = tk.Frame(self, bg=self.palette["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        notebook = ttk.Notebook(body, style="Nexo.TNotebook")
        notebook.pack(fill="both", expand=True)

        self.tab_ops = tk.Frame(notebook, bg=self.palette["panel"])
        self.tab_flows = tk.Frame(notebook, bg=self.palette["panel"])
        self.tab_ia = tk.Frame(notebook, bg=self.palette["panel"])

        notebook.add(self.tab_ops, text="Operación")
        notebook.add(self.tab_flows, text="Flujos OBS/YouTube")
        notebook.add(self.tab_ia, text="IA y Evolución")

        self._build_ops_tab()
        self._build_flows_tab()
        self._build_ia_tab()

    def _build_ops_tab(self):
        top = tk.Frame(self.tab_ops, bg=self.palette["panel"])
        top.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.LabelFrame(top, text="Logs en Vivo", fg=self.palette["text"], bg=self.palette["card"], bd=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.log_text = scrolledtext.ScrolledText(left, bg="#030712", fg="#86efac", insertbackground="white", font=("Consolas", 10), wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        right = tk.LabelFrame(top, text="Errores y Alertas", fg=self.palette["text"], bg=self.palette["card"], bd=1)
        right.pack(side="left", fill="both", expand=True)
        self.error_text = scrolledtext.ScrolledText(right, bg="#1a0d10", fg="#fca5a5", insertbackground="white", font=("Consolas", 10), wrap="word")
        self.error_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_flows_tab(self):
        controls = tk.Frame(self.tab_flows, bg=self.palette["panel"])
        controls.pack(fill="x", padx=10, pady=(10, 6))

        tk.Label(controls, text="Ordenar por:", bg=self.palette["panel"], fg=self.palette["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
        self.sort_mode = tk.StringVar(value="priority")
        ttk.Combobox(controls, textvariable=self.sort_mode, values=["priority", "type", "name"], state="readonly", width=12).pack(side="left", padx=8)
        tk.Button(controls, text="Aplicar", command=self.refresh_osint, bg=self.palette["info"], fg="#0b1020", relief="flat").pack(side="left", padx=4)
        tk.Button(controls, text="Actualizar", command=self.refresh_osint, bg=self.palette["ok"], fg="white", relief="flat").pack(side="left", padx=4)

        table_frame = tk.Frame(self.tab_flows, bg=self.palette["panel"])
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("name", "type", "priority", "status")
        self.osint_table = ttk.Treeview(table_frame, columns=cols, show="headings", height=14)
        self.osint_table.heading("name", text="Fuente")
        self.osint_table.heading("type", text="Tipo")
        self.osint_table.heading("priority", text="Prioridad")
        self.osint_table.heading("status", text="Estado")
        self.osint_table.column("name", width=240)
        self.osint_table.column("type", width=120)
        self.osint_table.column("priority", width=100, anchor="center")
        self.osint_table.column("status", width=140, anchor="center")
        self.osint_table.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.osint_table.yview)
        self.osint_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def _build_ia_tab(self):
        top = tk.Frame(self.tab_ia, bg=self.palette["panel"])
        top.pack(fill="x", padx=10, pady=(10, 6))

        tk.Button(top, text="Analizar y Sugerir", command=self.analyze_ia, bg=self.palette["violet"], fg="white", relief="flat", padx=12).pack(side="left")
        tk.Button(top, text="Registrar Evento IA", command=self._push_ia_event, bg=self.palette["info"], fg="#0b1020", relief="flat", padx=12).pack(side="left", padx=8)

        pane = tk.Frame(self.tab_ia, bg=self.palette["panel"])
        pane.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = tk.LabelFrame(pane, text="Sugerencias de Evolución", fg=self.palette["text"], bg=self.palette["card"], bd=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.ia_suggestions = scrolledtext.ScrolledText(left, bg="#120a2a", fg="#ddd6fe", insertbackground="white", font=("Consolas", 10), wrap="word")
        self.ia_suggestions.pack(fill="both", expand=True, padx=8, pady=8)

        right = tk.LabelFrame(pane, text="Bandeja IA (entradas/salidas)", fg=self.palette["text"], bg=self.palette["card"], bd=1)
        right.pack(side="left", fill="both", expand=True)
        self.ia_inbox = scrolledtext.ScrolledText(right, bg="#082f49", fg="#bae6fd", insertbackground="white", font=("Consolas", 10), wrap="word")
        self.ia_inbox.pack(fill="both", expand=True, padx=8, pady=8)

    def _set_badge(self, widget, text, bg_color):
        widget.config(text=text, bg=bg_color, fg="white", padx=10, pady=6)

    def _open_url(self, url):
        try:
            webbrowser.open(url)
        except Exception as exc:
            self.log(f"No se pudo abrir URL {url}: {exc}")

    def _resolve_npm(self):
        npm_cmd = shutil.which("npm")
        if npm_cmd:
            return npm_cmd
        windows_npm = r"C:\Program Files\nodejs\npm.cmd"
        if os.path.exists(windows_npm):
            return windows_npm
        return None

    def start_system(self):
        self.log("Iniciando backend y frontend...")
        self._set_badge(self.ia_badge, "IA: MONITOREANDO", self.palette["ok"])
        self.running = True
        threading.Thread(target=self.launch_backend, daemon=True).start()
        threading.Thread(target=self.launch_frontend, daemon=True).start()

    def stop_system(self):
        self.log("Deteniendo servicios...")
        self.running = False
        if self.backend_proc:
            self.backend_proc.terminate()
            self.backend_proc = None
        if self.frontend_proc:
            self.frontend_proc.terminate()
            self.frontend_proc = None
        self._set_badge(self.backend_badge, "Backend: OFF", self.palette["err"])
        self._set_badge(self.frontend_badge, "Frontend: OFF", self.palette["err"])
        self._set_badge(self.ia_badge, "IA: LISTA", self.palette["warn"])

    def launch_backend(self):
        try:
            self.backend_proc = subprocess.Popen([
                sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--port", "8000"
            ], cwd=BASE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self._set_badge(self.backend_badge, "Backend: ON", self.palette["ok"])
            for line in self.backend_proc.stdout:
                self.log_queue.put(line.decode(errors="ignore").rstrip())
        except Exception as exc:
            self.log_queue.put(f"ERROR backend: {exc}")
            self._set_badge(self.backend_badge, "Backend: ERROR", self.palette["err"])

    def launch_frontend(self):
        if not os.path.exists(FRONTEND_PATH):
            self.log_queue.put("Frontend no encontrado.")
            self._set_badge(self.frontend_badge, "Frontend: OFF", self.palette["err"])
            return

        npm_cmd = self._resolve_npm()
        if not npm_cmd:
            self.log_queue.put("ERROR frontend: npm no encontrado.")
            self._set_badge(self.frontend_badge, "Frontend: npm faltante", self.palette["err"])
            return

        try:
            self.frontend_proc = subprocess.Popen([
                npm_cmd, "run", "dev", "--", "--host", "0.0.0.0"
            ], cwd=FRONTEND_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self._set_badge(self.frontend_badge, "Frontend: ON", self.palette["ok"])
            for line in self.frontend_proc.stdout:
                self.log_queue.put(line.decode(errors="ignore").rstrip())
        except Exception as exc:
            self.log_queue.put(f"ERROR frontend: {exc}")
            self._set_badge(self.frontend_badge, "Frontend: ERROR", self.palette["err"])

    def log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {msg}"
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        if "error" in msg.lower() or "traceback" in msg.lower() or "exception" in msg.lower():
            self.error_text.insert(tk.END, line + "\n")
            self.error_text.see(tk.END)

    def refresh_osint(self):
        sort_by = self.sort_mode.get()
        if sort_by == "priority":
            ordered = sorted(self.sources, key=lambda item: item["priority"])
        elif sort_by == "type":
            ordered = sorted(self.sources, key=lambda item: item["type"])
        else:
            ordered = sorted(self.sources, key=lambda item: item["name"])

        for row in self.osint_table.get_children():
            self.osint_table.delete(row)

        for src in ordered:
            self.osint_table.insert("", "end", values=(src["name"], src["type"], src["priority"], src["status"]))

        self.log("Fuentes OSINT actualizadas.")

    def analyze_ia(self):
        sugerencias = [
            "Mejorar correlación de eventos en YouTube feed",
            "Optimizar ingestión de datos OBS",
            "Unificar alertas push en frontend",
            "Actualizar lógica de análisis financiero en backend",
            "Agregar panel de control para IA en la web"
        ]
        self.ia_suggestions.delete(1.0, tk.END)
        self.ia_suggestions.insert(tk.END, "Sugerencias IA:\n" + "\n".join(sugerencias))
        self.ia_inbox.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] IA completó análisis de contexto.\n")
        self.ia_inbox.see(tk.END)
        self.log("IA analizó contexto y generó sugerencias.")

    def _push_ia_event(self):
        self.ia_inbox.insert(
            tk.END,
            f"[{datetime.now().strftime('%H:%M:%S')}] Evento IA recibido: nueva recomendación para flujo OBS/YouTube.\n"
        )
        self.ia_inbox.see(tk.END)
        self.log("Se registró un evento en la bandeja IA.")

    def _heartbeat(self):
        self.timestamp_label.config(text=datetime.now().strftime("Actualizado %Y-%m-%d %H:%M:%S"))

        backend_alive = self.backend_proc is not None and self.backend_proc.poll() is None
        frontend_alive = self.frontend_proc is not None and self.frontend_proc.poll() is None

        if backend_alive:
            self._set_badge(self.backend_badge, "Backend: ON", self.palette["ok"])
        elif self.running:
            self._set_badge(self.backend_badge, "Backend: Reiniciar", self.palette["warn"])

        if frontend_alive:
            self._set_badge(self.frontend_badge, "Frontend: ON", self.palette["ok"])
        elif self.running:
            self._set_badge(self.frontend_badge, "Frontend: Revisar", self.palette["warn"])

        try:
            urlopen("http://localhost:8080/api/estado", timeout=1)
            self._set_badge(self.ia_badge, "IA/API: RESPONDE", self.palette["ok"])
        except URLError:
            if self.running:
                self._set_badge(self.ia_badge, "IA/API: SIN RESPUESTA", self.palette["warn"])

        self.after(2500, self._heartbeat)

    def _drain_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            if msg:
                self.log(msg)
        self.after(250, self._drain_logs)

if __name__ == "__main__":
    app = NexoDashboard()
    app.mainloop()
