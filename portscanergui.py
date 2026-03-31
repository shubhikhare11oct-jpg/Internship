import socket
import asyncio
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ---------------------------
# CONFIG
# ---------------------------
COMMON_PORTS = {
    21: 'FTP', 22: 'SSH', 23: 'Telnet',
    80: 'HTTP', 443: 'HTTPS', 3306: 'MySQL'
}

SCAN_MODES = {
    "Fast": range(1, 1025),
    "Medium": range(1, 5000),
    "Full": range(1, 20000)
}

SUBDOMAINS = ["www","api","admin","dev","test","mail","beta","staging"]

# ---------------------------
# SCANNER CLASS
# ---------------------------
class Scanner:
    def __init__(self, target, ports, callback, stat_callback, show_closed):
        self.target = target
        self.ports = ports
        self.callback = callback
        self.stat_callback = stat_callback
        self.show_closed = show_closed

        self.stop_flag = False
        self.open_ports = 0
        self.scanned = 0

    async def scan_port(self, port):
        if self.stop_flag:
            return

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.target, port), timeout=1
            )

            service = COMMON_PORTS.get(port, "Unknown")

            self.open_ports += 1
            self.callback(f"[OPEN] Port {port} ({service})", "open")

            writer.close()
            await writer.wait_closed()

        except:
            if self.show_closed:
                self.callback(f"[CLOSED] Port {port}", "closed")

        self.scanned += 1
        self.stat_callback(self.scanned, self.open_ports)

        await asyncio.sleep(0.001)

    async def run(self):
        tasks = []
        for port in self.ports:
            if self.stop_flag:
                break
            tasks.append(self.scan_port(port))

        await asyncio.gather(*tasks)


# ---------------------------
# SUBDOMAIN SCAN
# ---------------------------
def scan_subdomains(domain):
    results = []
    for sub in SUBDOMAINS:
        try:
            ip = socket.gethostbyname(f"{sub}.{domain}")
            results.append(f"{sub}.{domain} -> {ip}")
        except:
            pass
    return results


# ---------------------------
# GUI APP
# ---------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("💀 Ultimate Port Scanner")
        self.geometry("1000x650")

        self.scanner = None

        self.create_ui()

    # ---------------------------
    # UI
    # ---------------------------
    def create_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.tab_scan = ttk.Frame(notebook)
        self.tab_sub = ttk.Frame(notebook)
        self.tab_results = ttk.Frame(notebook)

        notebook.add(self.tab_scan, text="Scanner")
        notebook.add(self.tab_sub, text="Subdomains")
        notebook.add(self.tab_results, text="Results")

        # ---- Scan Tab ----
        top = ttk.Frame(self.tab_scan)
        top.pack(fill="x", pady=10)

        ttk.Label(top, text="Target:").grid(row=0, column=0)
        self.target_entry = ttk.Entry(top, width=30)
        self.target_entry.grid(row=0, column=1)

        ttk.Label(top, text="Mode:").grid(row=0, column=2)
        self.mode = ttk.Combobox(top, values=list(SCAN_MODES.keys()))
        self.mode.set("Fast")
        self.mode.grid(row=0, column=3)

        self.show_closed_var = tk.BooleanVar()
        ttk.Checkbutton(top, text="Show Closed", variable=self.show_closed_var)\
            .grid(row=0, column=4)

        ttk.Button(top, text="Start", command=self.start_scan).grid(row=0, column=5)
        ttk.Button(top, text="Stop", command=self.stop_scan).grid(row=0, column=6)

        # Stats
        stat_frame = ttk.Frame(self.tab_scan)
        stat_frame.pack(fill="x")

        self.stat_label = tk.StringVar(value="Scanned: 0 | Open: 0")
        ttk.Label(stat_frame, textvariable=self.stat_label).pack(side="left", padx=10)

        # Output
        self.output = tk.Text(self.tab_scan, bg="black", fg="white")
        self.output.pack(fill="both", expand=True)

        self.output.tag_config("open", foreground="lime")
        self.output.tag_config("closed", foreground="red")

        # ---- Subdomain Tab ----
        ttk.Label(self.tab_sub, text="Domain:").pack()
        self.sub_entry = ttk.Entry(self.tab_sub)
        self.sub_entry.pack()

        ttk.Button(self.tab_sub, text="Scan Subdomains", command=self.run_sub)\
            .pack(pady=5)

        self.sub_output = tk.Text(self.tab_sub, bg="black", fg="cyan")
        self.sub_output.pack(fill="both", expand=True)

        # ---- Results Tab ----
        self.result_box = tk.Text(self.tab_results)
        self.result_box.pack(fill="both", expand=True)

        ttk.Button(self.tab_results, text="Save Results", command=self.save)\
            .pack()

    # ---------------------------
    # SCAN CONTROL
    # ---------------------------
    def start_scan(self):
        target = self.target_entry.get().strip()

        if not target:
            messagebox.showerror("Error", "Enter target")
            return

        try:
            ip = socket.gethostbyname(target)
        except:
            messagebox.showerror("Error", "Invalid target")
            return

        ports = SCAN_MODES[self.mode.get()]

        self.output.insert(tk.END, f"\nScanning {target} ({ip})\n")

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self.scanner = Scanner(
                ip,
                ports,
                self.add_result,
                self.update_stats,
                self.show_closed_var.get()
            )

            loop.run_until_complete(self.scanner.run())

            self.add_result("Scan Completed", "open")

        threading.Thread(target=run, daemon=True).start()

    def stop_scan(self):
        if self.scanner:
            self.scanner.stop_flag = True

    def add_result(self, text, tag):
        self.output.insert(tk.END, text + "\n", tag)
        self.output.see(tk.END)
        self.result_box.insert(tk.END, text + "\n")

    def update_stats(self, scanned, open_ports):
        self.stat_label.set(f"Scanned: {scanned} | Open: {open_ports}")

    # ---------------------------
    # SUBDOMAIN
    # ---------------------------
    def run_sub(self):
        domain = self.sub_entry.get().strip()

        if not domain:
            return

        self.sub_output.insert(tk.END, "\nScanning...\n")

        results = scan_subdomains(domain)

        for r in results:
            self.sub_output.insert(tk.END, r + "\n")
            self.result_box.insert(tk.END, r + "\n")

    # ---------------------------
    # SAVE
    # ---------------------------
    def save(self):
        file = filedialog.asksaveasfilename(defaultextension=".txt")
        if file:
            with open(file, "w") as f:
                f.write(self.result_box.get("1.0", tk.END))
            messagebox.showinfo("Saved", "Results saved")


# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()