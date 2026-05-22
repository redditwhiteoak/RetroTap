"""
RetroTap Desktop Control Panel

Run this instead of opening the server in a terminal:

    python retrotap_control_panel.py

It starts/stops launchbox_server.py, shows live logs, and gives quick buttons
for the RetroTap library/settings pages.
"""

import os
import json
import re
import sys
import time
import queue
import socket
import signal
import threading
import subprocess
import webbrowser
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox


APP_TITLE = "RetroTap Control Panel"
DEFAULT_PORT = 5000
SERVER_SCRIPT = "launchbox_server.py"


class RetroTapControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("980x680")
        self.root.minsize(840, 560)

        self.process = None
        self.log_queue = queue.Queue()
        self.server_dir = os.path.dirname(os.path.abspath(__file__))
        self.server_script = os.path.join(self.server_dir, SERVER_SCRIPT)
        self.config_file = os.path.join(self.server_dir, "config.json")

        self.bg = "#03040a"
        self.panel = "#0a0e1c"
        self.panel2 = "#12182e"
        self.text = "#f8fbff"
        self.dim = "#aab4cf"
        self.blue = "#18c8ff"
        self.pink = "#ff2bbf"
        self.purple = "#a855ff"

        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.status_var = tk.StringVar(value="Stopped")
        self.local_url_var = tk.StringVar(value=f"http://127.0.0.1:{DEFAULT_PORT}")
        self.network_url_var = tk.StringVar(value=f"http://{self.get_lan_ip()}:{DEFAULT_PORT}")
        self.logging_status_var = tk.StringVar(value="Debug Logging: Disabled")

        self.configure_style()
        self.build_ui()
        self.poll_logs()
        self.refresh_urls()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def configure_style(self):
        self.root.configure(bg=self.bg)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=self.bg)
        style.configure("Panel.TFrame", background=self.panel)
        style.configure("TLabel", background=self.bg, foreground=self.text, font=("Segoe UI", 10))
        style.configure("Dim.TLabel", background=self.bg, foreground=self.dim, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=self.bg, foreground=self.blue, font=("Segoe UI", 24, "bold"))
        style.configure("Header.TLabel", background=self.panel, foreground=self.text, font=("Segoe UI", 13, "bold"))
        style.configure("Status.TLabel", background=self.panel, foreground=self.pink, font=("Segoe UI", 12, "bold"))

        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("Accent.TButton", background=self.blue, foreground="#050713")
        style.configure("Pink.TButton", background=self.pink, foreground="#050713")
        style.configure("Purple.TButton", background=self.purple, foreground="#050713")
        style.configure("Danger.TButton", background="#ef4444", foreground="#ffffff")

        style.configure("TEntry", fieldbackground=self.panel2, foreground=self.text, insertcolor=self.text)

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        top = ttk.Frame(outer)
        top.pack(fill="x")

        logo_path = os.path.join(self.server_dir, "static", "retrotap_logo.png")
        self.logo_img = None
        if os.path.exists(logo_path):
            try:
                self.logo_img = tk.PhotoImage(file=logo_path)
                # Subsample large logo for header
                w = max(1, self.logo_img.width() // 360)
                h = max(1, self.logo_img.height() // 130)
                self.logo_img = self.logo_img.subsample(w, h)
                logo_label = tk.Label(top, image=self.logo_img, bg=self.bg)
                logo_label.pack(side="left", padx=(0, 16))
            except Exception:
                ttk.Label(top, text="RetroTap", style="Title.TLabel").pack(side="left", padx=(0, 16))
        else:
            ttk.Label(top, text="RetroTap", style="Title.TLabel").pack(side="left", padx=(0, 16))

        title_wrap = ttk.Frame(top)
        title_wrap.pack(side="left", fill="x", expand=True)
        ttk.Label(title_wrap, text="Server Control Panel", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_wrap,
            text="Start the RetroTap server, view URLs, and monitor logs without using a terminal.",
            style="Dim.TLabel"
        ).pack(anchor="w")

        main = ttk.Frame(outer)
        main.pack(fill="both", expand=True, pady=(18, 0))

        left = ttk.Frame(main, style="Panel.TFrame", padding=16)
        left.pack(side="left", fill="y", padx=(0, 14))

        right = ttk.Frame(main, style="Panel.TFrame", padding=16)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Server", style="Header.TLabel").pack(anchor="w")
        ttk.Label(left, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(4, 14))

        port_row = ttk.Frame(left, style="Panel.TFrame")
        port_row.pack(fill="x", pady=(0, 14))
        ttk.Label(port_row, text="Port:", background=self.panel, foreground=self.text).pack(side="left")
        port_entry = ttk.Entry(port_row, textvariable=self.port_var, width=8)
        port_entry.pack(side="left", padx=(8, 0))
        port_entry.bind("<KeyRelease>", lambda _e: self.refresh_urls())

        ttk.Button(left, text="Start Server", style="Accent.TButton", command=self.start_server).pack(fill="x", pady=4)
        ttk.Button(left, text="Stop Server", style="Danger.TButton", command=self.stop_server).pack(fill="x", pady=4)
        ttk.Button(left, text="Restart Server", style="Purple.TButton", command=self.restart_server).pack(fill="x", pady=4)

        ttk.Separator(left).pack(fill="x", pady=16)

        ttk.Label(left, text="Open Pages", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Button(left, text="Open RetroTap Library", command=lambda: self.open_url("/")).pack(fill="x", pady=4)
        ttk.Button(left, text="Open Settings", command=lambda: self.open_url("/settings")).pack(fill="x", pady=4)
        ttk.Button(left, text="Open Refresh Status", command=lambda: self.open_url("/loading")).pack(fill="x", pady=4)
        ttk.Button(left, text="Open Mobile API: Games", command=lambda: self.open_url("/api/games")).pack(fill="x", pady=4)
        ttk.Button(left, text="Open Mobile API: Platforms", command=lambda: self.open_url("/api/platforms")).pack(fill="x", pady=4)

        ttk.Separator(left).pack(fill="x", pady=16)

        ttk.Label(left, text="Debug Logging", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(left, textvariable=self.logging_status_var, background=self.panel, foreground=self.dim).pack(anchor="w", pady=(0, 4))
        self.logging_button = ttk.Button(left, text="Enable Debug Logging", command=self.toggle_logging)
        self.logging_button.pack(fill="x", pady=4)
        ttk.Button(left, text="View Debug Log", command=lambda: self.open_url("/debug-log")).pack(fill="x", pady=4)

        ttk.Separator(left).pack(fill="x", pady=16)

        ttk.Label(left, text="Library Refresh", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Button(left, text="Start Fresh Scan", command=lambda: self.open_url("/refresh-library")).pack(fill="x", pady=4)
        ttk.Button(left, text="Pause Refresh", command=lambda: self.open_url("/pause-library-refresh")).pack(fill="x", pady=4)
        ttk.Button(left, text="Resume Refresh", command=lambda: self.open_url("/restart-library-refresh")).pack(fill="x", pady=4)
        ttk.Button(left, text="Clear Cache", style="Danger.TButton", command=lambda: self.open_url("/clear-library-cache")).pack(fill="x", pady=4)

        ttk.Separator(left).pack(fill="x", pady=16)

        ttk.Label(left, text="Connection URLs", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        self.url_box(left, "This PC:", self.local_url_var)
        self.url_box(left, "Phone / LAN:", self.network_url_var)

        ttk.Button(left, text="Copy Phone URL", command=self.copy_network_url).pack(fill="x", pady=(10, 4))

        ttk.Label(right, text="Live Server Log", style="Header.TLabel").pack(anchor="w")
        self.log = tk.Text(
            right,
            bg="#050713",
            fg=self.text,
            insertbackground=self.text,
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
            height=22
        )
        self.log.pack(fill="both", expand=True, pady=(10, 10))

        bottom = ttk.Frame(right, style="Panel.TFrame")
        bottom.pack(fill="x")

        ttk.Button(bottom, text="Clear Log", command=self.clear_log).pack(side="left")
        ttk.Button(bottom, text="Open Server Folder", command=self.open_folder).pack(side="left", padx=8)
        ttk.Button(bottom, text="Check Status", command=self.check_status).pack(side="left")

        self.append_log("RetroTap Control Panel ready.\n")
        self.append_log(f"Server folder: {self.server_dir}\n")
        self.append_log("Click Start Server to begin.\n\n")
        self.update_logging_controls()

    def url_box(self, parent, label, var):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="x", pady=4)
        ttk.Label(frame, text=label, background=self.panel, foreground=self.dim).pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(fill="x", pady=(2, 0))

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.append_log(f"Could not read config.json: {e}\n")
        return {}

    def save_config(self, config):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            self.append_log(f"Could not save config.json: {e}\n")
            messagebox.showerror("RetroTap", f"Could not save config.json:\n{e}")
            return False

    def logging_enabled(self):
        return bool(self.load_config().get("logging_enabled", False))

    def update_logging_controls(self):
        enabled = self.logging_enabled()
        self.logging_status_var.set("Debug Logging: Enabled" if enabled else "Debug Logging: Disabled")
        if hasattr(self, "logging_button"):
            self.logging_button.configure(text="Disable Debug Logging" if enabled else "Enable Debug Logging")

    def toggle_logging(self):
        config = self.load_config()
        new_value = not bool(config.get("logging_enabled", False))
        config["logging_enabled"] = new_value
        if self.save_config(config):
            self.update_logging_controls()
            state = "enabled" if new_value else "disabled"
            self.append_log(f"Debug logging {state}.\n")

            # If the server is running, hit the status page so the live page reflects config reloads.
            # The server reads config.json dynamically, so no restart is needed.
            if self.process and self.process.poll() is None:
                try:
                    urllib.request.urlopen(self.local_url_var.get().rstrip("/") + "/status", timeout=1).close()
                except Exception:
                    pass

    def kill_processes_on_port(self, port):
        killed = []

        # Preferred method: psutil, already used by the RetroTap server project.
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    for conn in proc.net_connections(kind="inet"):
                        if conn.laddr and conn.laddr.port == port:
                            if proc.pid == os.getpid():
                                continue
                            cmdline = " ".join(proc.info.get("cmdline") or [])
                            if "launchbox_server.py" in cmdline or port == self.get_port():
                                proc.terminate()
                                try:
                                    proc.wait(timeout=3)
                                except Exception:
                                    proc.kill()
                                killed.append(proc.pid)
                                break
                except Exception:
                    continue
        except Exception:
            pass

        # Windows fallback without psutil.
        if os.name == "nt" and not killed:
            try:
                output = subprocess.check_output(
                    f'netstat -ano | findstr :{port}',
                    shell=True,
                    text=True,
                    stderr=subprocess.DEVNULL
                )
                pids = set()
                for line in output.splitlines():
                    parts = line.split()
                    if len(parts) >= 5 and (f":{port}" in parts[1]):
                        pids.add(parts[-1])
                for pid in pids:
                    if pid and pid.isdigit() and int(pid) != os.getpid():
                        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, text=True)
                        killed.append(int(pid))
            except Exception:
                pass

        if killed:
            self.append_log(f"Stopped existing server process(es) on port {port}: {killed}\n")
        return killed

    def get_lan_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    def get_port(self):
        try:
            return int(self.port_var.get().strip())
        except Exception:
            return DEFAULT_PORT

    def refresh_urls(self):
        port = self.get_port()
        self.local_url_var.set(f"http://127.0.0.1:{port}")
        self.network_url_var.set(f"http://{self.get_lan_ip()}:{port}")

    def start_server(self):
        if self.process and self.process.poll() is None:
            messagebox.showinfo("RetroTap", "Server is already running.")
            return

        if not os.path.exists(self.server_script):
            messagebox.showerror("RetroTap", f"Could not find {SERVER_SCRIPT}")
            return

        self.refresh_urls()
        port = self.get_port()

        # Prevent stale old servers from continuing to serve old files on this port.
        self.kill_processes_on_port(port)

        env = os.environ.copy()
        env["RETROTAP_PORT"] = str(port)
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [sys.executable, "-u", self.server_script]  # uses the same Python that launched this GUI

        self.append_log(f"\nStarting RetroTap server on port {port}...\n")
        self.append_log(" ".join(cmd) + "\n\n")

        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

            self.process = subprocess.Popen(
                cmd,
                cwd=self.server_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                env=env,
                creationflags=creationflags
            )

            self.status_var.set("Running")
            threading.Thread(target=self.read_process_output, daemon=True).start()

            self.root.after(900, lambda: self.open_url("/"))
        except Exception as e:
            self.status_var.set("Failed")
            self.append_log(f"Failed to start server: {e}\n")
            messagebox.showerror("RetroTap", f"Failed to start server:\n{e}")

    def stop_server(self):
        port = self.get_port()

        if self.process and self.process.poll() is None:
            self.append_log("\nStopping RetroTap server...\n")
            try:
                if os.name == "nt":
                    try:
                        self.process.send_signal(signal.CTRL_BREAK_EVENT)
                    except Exception:
                        self.process.terminate()
                    time.sleep(0.8)
                    if self.process.poll() is None:
                        self.process.terminate()
                else:
                    self.process.terminate()

                try:
                    self.process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self.process.kill()

                self.append_log("Server process stopped.\n")
            except Exception as e:
                self.append_log(f"Error stopping tracked server process: {e}\n")

        # Also kill any stale server still occupying the port.
        self.kill_processes_on_port(port)
        self.process = None
        self.status_var.set("Stopped")
        self.append_log("Server stopped.\n")

    def restart_server(self):
        self.stop_server()
        self.root.after(600, self.start_server)

    def read_process_output(self):
        try:
            for line in self.process.stdout:
                self.log_queue.put(line)
        except Exception as e:
            self.log_queue.put(f"Log reader stopped: {e}\n")
        finally:
            code = self.process.poll() if self.process else None
            self.log_queue.put(f"\nServer process ended. Exit code: {code}\n")
            self.root.after(0, lambda: self.status_var.set("Stopped"))

    def poll_logs(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.append_log(line)
        except queue.Empty:
            pass
        self.root.after(120, self.poll_logs)

    def append_log(self, message):
        self.log.insert("end", message)
        self.log.see("end")

    def clear_log(self):
        self.log.delete("1.0", "end")

    def open_url(self, path="/"):
        self.refresh_urls()
        url = self.local_url_var.get().rstrip("/") + path
        webbrowser.open(url)
        self.append_log(f"Opened: {url}\n")

    def copy_network_url(self):
        self.refresh_urls()
        self.root.clipboard_clear()
        self.root.clipboard_append(self.network_url_var.get())
        self.append_log(f"Copied phone URL: {self.network_url_var.get()}\n")

    def open_folder(self):
        if os.name == "nt":
            os.startfile(self.server_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self.server_dir])
        else:
            subprocess.Popen(["xdg-open", self.server_dir])

    def check_status(self):
        if self.process and self.process.poll() is None:
            self.status_var.set("Running")
            self.append_log("Status: server process is running.\n")
        else:
            self.status_var.set("Stopped")
            self.append_log("Status: server process is stopped.\n")

    def on_close(self):
        # Closing the GUI should also close the server so old code does not stay active on port 5000.
        self.stop_server()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = RetroTapControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
