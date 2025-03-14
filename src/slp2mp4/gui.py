import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pathlib
import tomllib
import json
import queue
import threading
import subprocess
from typing import Optional
import sys
import os

import slp2mp4.config as config
import slp2mp4.modes as modes

class OutputRedirector:
    def __init__(self, queue):
        self.queue = queue

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass

class SettingsWindow:
    def __init__(self, parent, current_settings):
        self.window = tk.Toplevel(parent)
        self.window.title("Settings")
        self.window.geometry("600x400")
        self.settings = current_settings

        # Create notebook for tabbed settings
        self.notebook = ttk.Notebook(self.window)
        
        # Paths tab
        self.paths_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.paths_frame, text="Paths")
        
        # Video settings tab
        self.video_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.video_frame, text="Video")
        
        # Runtime settings tab
        self.runtime_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.runtime_frame, text="Runtime")
        
        self.notebook.pack(expand=True, fill="both", padx=10, pady=5)
        
        self._create_paths_tab()
        self._create_video_tab()
        self._create_runtime_tab()
        
        # Save button
        self.save_btn = ttk.Button(self.window, text="Save Settings", command=self.save_settings)
        self.save_btn.pack(pady=10)

    def _create_paths_tab(self):
        # FFmpeg path
        ttk.Label(self.paths_frame, text="FFmpeg Path:").pack(anchor="w", padx=5, pady=2)
        self.ffmpeg_path = ttk.Entry(self.paths_frame, width=50)
        self.ffmpeg_path.insert(0, str(self.settings["paths"]["ffmpeg"]))
        self.ffmpeg_path.pack(anchor="w", padx=5)
        ttk.Button(self.paths_frame, text="Browse", 
                  command=lambda: self._browse_file(self.ffmpeg_path)).pack(anchor="w", padx=5)

        # Slippi Playback path
        ttk.Label(self.paths_frame, text="Slippi Playback Path:").pack(anchor="w", padx=5, pady=2)
        self.slippi_path = ttk.Entry(self.paths_frame, width=50)
        self.slippi_path.insert(0, str(self.settings["paths"]["slippi_playback"]))
        self.slippi_path.pack(anchor="w", padx=5)
        ttk.Button(self.paths_frame, text="Browse", 
                  command=lambda: self._browse_file(self.slippi_path)).pack(anchor="w", padx=5)

        # SSBM ISO path
        ttk.Label(self.paths_frame, text="SSBM ISO Path:").pack(anchor="w", padx=5, pady=2)
        self.ssbm_path = ttk.Entry(self.paths_frame, width=50)
        self.ssbm_path.insert(0, str(self.settings["paths"]["ssbm_ini"]))
        self.ssbm_path.pack(anchor="w", padx=5)
        ttk.Button(self.paths_frame, text="Browse", 
                  command=lambda: self._browse_file(self.ssbm_path, [("ISO files", "*.iso")])).pack(anchor="w", padx=5)

    def _create_video_tab(self):
        # Backend selection
        ttk.Label(self.video_frame, text="Backend:").pack(anchor="w", padx=5, pady=2)
        self.backend_var = tk.StringVar(value=self.settings["video"]["backend"])
        ttk.Radiobutton(self.video_frame, text="Direct3D 11", value="DX11", 
                       variable=self.backend_var).pack(anchor="w", padx=5)
        ttk.Radiobutton(self.video_frame, text="Direct3D 12", value="D3D12", 
                       variable=self.backend_var).pack(anchor="w", padx=5)
        ttk.Radiobutton(self.video_frame, text="Direct3D 9", value="DX9", 
                       variable=self.backend_var).pack(anchor="w", padx=5)
        ttk.Radiobutton(self.video_frame, text="OpenGL", value="OGL", 
                       variable=self.backend_var).pack(anchor="w", padx=5)
        ttk.Radiobutton(self.video_frame, text="Vulkan (experimental)", value="Vulkan", 
                       variable=self.backend_var).pack(anchor="w", padx=5)

        # Resolution selection
        ttk.Label(self.video_frame, text="Resolution:").pack(anchor="w", padx=5, pady=2)
        self.resolution_var = tk.StringVar(value=self.settings["video"]["resolution"])
        resolutions = ["480p", "720p", "1080p", "1440p", "2160p"]
        resolution_combo = ttk.Combobox(self.video_frame, textvariable=self.resolution_var, 
                                      values=resolutions, state="readonly")
        resolution_combo.pack(anchor="w", padx=5)

        # Bitrate
        ttk.Label(self.video_frame, text="Bitrate (kbps):").pack(anchor="w", padx=5, pady=2)
        self.bitrate_var = tk.StringVar(value=str(self.settings["video"]["bitrate"]))
        ttk.Entry(self.video_frame, textvariable=self.bitrate_var).pack(anchor="w", padx=5)

        # Reencode option
        self.reencode_var = tk.BooleanVar(value=self.settings["video"]["reencode_when_merging_audio_and_video"])
        ttk.Checkbutton(self.video_frame, text="Reencode when merging audio and video", 
                       variable=self.reencode_var).pack(anchor="w", padx=5, pady=5)

    def _create_runtime_tab(self):
        ttk.Label(self.runtime_frame, text="Parallel Processing:").pack(anchor="w", padx=5, pady=2)
        self.parallel_var = tk.StringVar(value=str(self.settings["runtime"]["parallel"]))
        ttk.Entry(self.runtime_frame, textvariable=self.parallel_var).pack(anchor="w", padx=5)
        ttk.Label(self.runtime_frame, 
                 text="(0 for automatic, 1 for sequential, >1 for specific number of processes)"
                 ).pack(anchor="w", padx=5)

    def _browse_file(self, entry_widget, filetypes=None):
        if filetypes:
            filename = filedialog.askopenfilename(filetypes=filetypes)
        else:
            filename = filedialog.askopenfilename()
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def save_settings(self):
        self.settings["paths"]["ffmpeg"] = self.ffmpeg_path.get()
        self.settings["paths"]["slippi_playback"] = self.slippi_path.get()
        self.settings["paths"]["ssbm_ini"] = self.ssbm_path.get()
        
        self.settings["video"]["backend"] = self.backend_var.get()
        self.settings["video"]["resolution"] = self.resolution_var.get()
        self.settings["video"]["bitrate"] = int(self.bitrate_var.get())
        self.settings["video"]["reencode_when_merging_audio_and_video"] = self.reencode_var.get()
        
        self.settings["runtime"]["parallel"] = int(self.parallel_var.get())

        config_path = pathlib.Path(".slp2mp4.toml").expanduser().resolve()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        import tomli_w
        with open(config_path, "wb") as f:
            tomli_w.dump(self.settings, f)
        
        messagebox.showinfo("Success", "Settings saved successfully!")
        self.window.destroy()

class FirstTimeSetup:
    def __init__(self, parent, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("First Time Setup")
        self.window.geometry("600x400")
        self.callback = callback
        
        ttk.Label(self.window, text="Welcome to SLP2MP4!", 
                 font=("", 14, "bold")).pack(pady=10)
        ttk.Label(self.window, 
                 text="Please configure the following required settings to get started:").pack(pady=5)
        
        # Create form
        form_frame = ttk.Frame(self.window)
        form_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # FFmpeg path
        ttk.Label(form_frame, text="FFmpeg Path:").pack(anchor="w")
        self.ffmpeg_path = ttk.Entry(form_frame, width=50)
        self.ffmpeg_path.pack(anchor="w")
        ttk.Button(form_frame, text="Browse", 
                  command=lambda: self._browse_file(self.ffmpeg_path)).pack(anchor="w")
        
        # Slippi Playback path
        ttk.Label(form_frame, text="Slippi Playback Path:").pack(anchor="w", pady=(10, 0))
        self.slippi_path = ttk.Entry(form_frame, width=50)
        self.slippi_path.pack(anchor="w")
        ttk.Button(form_frame, text="Browse", 
                  command=lambda: self._browse_file(self.slippi_path)).pack(anchor="w")
        
        # SSBM ISO path
        ttk.Label(form_frame, text="SSBM ISO Path:").pack(anchor="w", pady=(10, 0))
        self.ssbm_path = ttk.Entry(form_frame, width=50)
        self.ssbm_path.pack(anchor="w")
        ttk.Button(form_frame, text="Browse", 
                  command=lambda: self._browse_file(self.ssbm_path, [("ISO files", "*.iso")])).pack(anchor="w")
        
        # Save button
        ttk.Button(self.window, text="Save and Continue", 
                  command=self.save_settings).pack(pady=20)

    def _browse_file(self, entry_widget, filetypes=None):
        if filetypes:
            filename = filedialog.askopenfilename(filetypes=filetypes)
        else:
            filename = filedialog.askopenfilename()
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def save_settings(self):
        if not all([self.ffmpeg_path.get(), self.slippi_path.get(), self.ssbm_path.get()]):
            messagebox.showerror("Error", "All fields are required!")
            return

        settings = {
            "paths": {
                "ffmpeg": self.ffmpeg_path.get(),
                "slippi_playback": self.slippi_path.get(),
                "ssbm_ini": self.ssbm_path.get()
            },
            "video": {
                "backend": "Software",
                "resolution": "1080p",
                "bitrate": 16000,
                "reencode_when_merging_audio_and_video": True
            },
            "runtime": {
                "parallel": 1
            }
        }

        config_path = pathlib.Path(".slp2mp4.toml").expanduser().resolve()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        import tomli_w
        with open(config_path, "wb") as f:
            tomli_w.dump(settings, f)
        
        self.callback(settings)
        messagebox.showinfo("Success", "Initial setup complete!")
        self.window.destroy()

class ConversionArgs:
    def __init__(self, input_dir, output_dir, dry_run):
        self.input_dir = pathlib.Path(input_dir)
        self.output_dir = pathlib.Path(output_dir)
        self.dry_run = dry_run

    def run(self):
        args = ["slp2mp4", "-o", str(self.output_dir)]
        if self.dry_run:
            args.append("-n")
        args.extend(["directory", str(self.input_dir)])
        try:
            completed = subprocess.run(args, check=True, stderr=subprocess.PIPE, text=True)
            print(completed.stderr)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"CLI command failed: {e}")

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("SLP2MP4 Converter")
        self.root.geometry("800x600")
        
        # Queue for output redirection
        self.output_queue = queue.Queue()
        self.original_stdout = sys.stdout
        sys.stdout = OutputRedirector(self.output_queue)
        
        # Load config or show first-time setup
        try:
            self.settings = config.get_config()
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.settings = {
                "paths": {
                    "ffmpeg": "ffmpeg",
                    "slippi_playback": str(pathlib.Path("~/AppData/Roaming/Slippi Launcher/playback/Slippi Dolphin.exe").expanduser()),
                    "ssbm_ini": ""
                },
                "video": {
                    "backend": "Software",
                    "resolution": "1080p",
                    "bitrate": 16000,
                    "reencode_when_merging_audio_and_video": True
                },
                "runtime": {
                    "parallel": 1
                }
            }
            self.show_first_time_setup()

        self._create_widgets()
        self._setup_layout()
        
        # Start output monitoring
        self.monitor_output()

    def _create_widgets(self):
        # Input frame
        self.input_frame = ttk.LabelFrame(self.root, text="Input")
        self.input_path = ttk.Entry(self.input_frame, width=70)
        self.input_browse = ttk.Button(self.input_frame, text="Browse", 
                                     command=self._browse_input)
        
        # Output frame
        self.output_frame = ttk.LabelFrame(self.root, text="Output")
        self.output_path = ttk.Entry(self.output_frame, width=70)
        self.output_browse = ttk.Button(self.output_frame, text="Browse", 
                                      command=self._browse_output)
        
        # Settings and conversion frame
        self.control_frame = ttk.Frame(self.root)
        self.settings_btn = ttk.Button(self.control_frame, text="Settings", 
                                     command=self.show_settings)
        self.dry_run_var = tk.BooleanVar()
        self.dry_run_cb = ttk.Checkbutton(self.control_frame, text="Dry Run", 
                                         variable=self.dry_run_var)
        self.convert_btn = ttk.Button(self.control_frame, text="Start Conversion", 
                                    command=self.start_conversion)
        
        # Progress frame
        self.progress_frame = ttk.LabelFrame(self.root, text="Progress")
        self.progress_text = tk.Text(self.progress_frame, height=15, width=80)
        self.scrollbar = ttk.Scrollbar(self.progress_frame, orient="vertical", 
                                     command=self.progress_text.yview)
        self.progress_text.configure(yscrollcommand=self.scrollbar.set)
        self.progress_text.configure(state='disabled')  # Make read-only

    def _setup_layout(self):
        # Configure main window grid
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Input frame layout
        self.input_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.input_path.grid(row=0, column=0, padx=5, pady=5)
        self.input_browse.grid(row=0, column=1, padx=5, pady=5)
        
        # Output frame layout
        self.output_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.output_path.grid(row=0, column=0, padx=5, pady=5)
        self.output_browse.grid(row=0, column=1, padx=5, pady=5)
        
        # Control frame layout
        self.control_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.settings_btn.pack(side=tk.LEFT, padx=5)
        self.dry_run_cb.pack(side=tk.LEFT, padx=5)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress frame layout
        self.progress_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)

    def _browse_input(self):
        dirname = filedialog.askdirectory(title="Select Input Directory")
        if dirname:
            self.input_path.delete(0, tk.END)
            self.input_path.insert(0, dirname)
            
            # Auto-set output path if empty
            if not self.output_path.get():
                self.output_path.insert(0, dirname)

    def _browse_output(self):
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_path.delete(0, tk.END)
            self.output_path.insert(0, dirname)

    def show_settings(self):
        SettingsWindow(self.root, self.settings)

    def show_first_time_setup(self):
        def callback(new_settings):
            self.settings = new_settings
        FirstTimeSetup(self.root, callback)

    def append_to_progress(self, text):
        self.progress_text.configure(state='normal')
        self.progress_text.insert(tk.END, text)
        self.progress_text.see(tk.END)
        self.progress_text.configure(state='disabled')

    def monitor_output(self):
        """Monitor the output queue and update the progress text"""
        try:
            while True:
                text = self.output_queue.get_nowait()
                self.append_to_progress(text)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.monitor_output)

    def start_conversion(self):
        input_path = self.input_path.get()
        output_path = self.output_path.get()

        if not input_path or not output_path:
            messagebox.showerror("Error", "Please select input and output directories!")
            return

        # Check if paths exist
        if not os.path.exists(input_path):
            messagebox.showerror("Error", f"Input directory does not exist: {input_path}")
            return

        # Clear progress log
        self.progress_text.configure(state='normal')
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.configure(state='disabled')

        self.convert_btn.configure(state='disabled')

        # Start conversion thread
        def conversion_thread():
            try:
                self.append_to_progress(f"Starting conversion...\nInput: {input_path}\nOutput: {output_path}\n")
                args = ConversionArgs(input_path, output_path, self.dry_run_var.get())
                args.run()
                self.append_to_progress("Conversion completed successfully!\n")
                messagebox.showinfo("Success", "Conversion completed successfully!")
            except Exception as e:
                self.append_to_progress(f"Error during conversion: {e}\n")
                messagebox.showerror("Error", f"Conversion failed: {e}")
            finally:
                self.convert_btn.configure(state='normal')

        threading.Thread(target=conversion_thread, daemon=True).start()

def main():
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()
