# Opens and closes applications
import os
import shutil # Required for shutil.which
import subprocess
import psutil

class AppManager:
    def __init__(self):
        # Potential: Load a map of common app names to their executable paths from config
        self.app_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "chrome.exe", # This might need full path on some systems
            "firefox": "firefox.exe", # This might need full path
            # Add more common apps
        }
        # On Windows, ProgramFiles and ProgramFiles(x86) are common locations
        # On macOS, /Applications/
        # On Linux, usually apps are in PATH

    def _find_app_path(self, app_name: str) -> str | None:
        """Tries to find the executable path for an application."""
        app_name_lower = app_name.lower()

        # 1. Check common names map
        if app_name_lower in self.app_map:
            # Check if it's directly runnable (in PATH) or if it's a full path
            if os.path.exists(self.app_map[app_name_lower]) or shutil.which(self.app_map[app_name_lower]):
                 return self.app_map[app_name_lower]

        # 2. Check if app_name itself is an executable in PATH
        if shutil.which(app_name):
            return app_name
        if shutil.which(app_name + ".exe"): # For windows convenience
            return app_name + ".exe"

        # 3. Platform-specific searches (very basic examples)
        # This part would need to be more robust for a real application
        if os.name == 'nt': # Windows
            common_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), app_name, app_name + ".exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), app_name, app_name + ".exe"),
                os.path.join(os.environ.get("LocalAppData", ""), "Programs", app_name, app_name + ".exe")
            ]
            for path_to_check in common_paths:
                if os.path.exists(path_to_check):
                    return path_to_check
            # Search for apps installed via Microsoft Store (more complex)
            # Example: C:\Program Files\WindowsApps\Microsoft.WindowsCalculator_11.2311.0.0_x64__8wekyb3d8bbwe\CalculatorApp.exe

        elif os.name == 'posix': # macOS or Linux
            if shutil.which(app_name_lower): # Check PATH again for lowercase
                return app_name_lower
            # macOS specific
            mac_path = f"/Applications/{app_name}.app/Contents/MacOS/{app_name}"
            if os.path.exists(mac_path):
                return mac_path
            mac_path_alt = f"/Applications/{app_name.capitalize()}.app/Contents/MacOS/{app_name.capitalize()}"
            if os.path.exists(mac_path_alt):
                return mac_path_alt

        print(f"Could not automatically find path for '{app_name}'. User might need to specify full path or add to app_map.")
        return None


    def open_app(self, app_name_or_path: str) -> bool:
        """Opens an application by its name or full path."""
        app_path = self._find_app_path(app_name_or_path)
        if not app_path and os.path.exists(app_name_or_path): # If raw path was given and it exists
            app_path = app_name_or_path

        if not app_path:
            print(f"Application '{app_name_or_path}' not found or path could not be determined.")
            return False

        try:
            if os.name == 'nt': # Windows
                # For .exe files, os.startfile is often preferred as it behaves like double-clicking
                if app_path.lower().endswith(".exe"):
                    os.startfile(app_path)
                else: # For other file types or commands that open with associated app
                    subprocess.Popen(app_path, shell=True)
            elif os.name == 'posix': # macOS or Linux
                if app_path.endswith(".app"): # macOS .app bundle
                     subprocess.Popen(['open', app_path])
                else: # General command for Linux or macOS executables
                    subprocess.Popen([app_path])
            else:
                print(f"Unsupported OS: {os.name}")
                return False
            print(f"Attempting to open application: {app_path}")
            return True
        except Exception as e:
            print(f"Error opening application {app_path}: {e}")
            return False

    def close_app(self, app_name_or_exe: str) -> bool:
        """Closes an application by its name or executable name."""
        # Normalize to common executable name if found in map, otherwise use as is
        exe_name = self.app_map.get(app_name_or_exe.lower(), app_name_or_exe)
        if not exe_name.lower().endswith(('.exe', '.app')) and '.' not in exe_name: # Heuristic for Windows
            if os.name == 'nt':
                 exe_name += ".exe"
            # For macOS, app_name might be enough if it's the process name
            # For Linux, it's usually the command name

        closed_any = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Be careful with matching, process names can be tricky
                if exe_name.lower() in proc.info['name'].lower():
                    print(f"Found process {proc.info['name']} (PID: {proc.info['pid']}) matching '{exe_name}'. Terminating...")
                    p = psutil.Process(proc.info['pid'])
                    p.terminate() # Graceful termination
                    # p.kill() # Forceful termination if terminate fails
                    closed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass # Process might have already exited or access is denied
            except Exception as e:
                print(f"Error while trying to close {exe_name}: {e}")

        if closed_any:
            print(f"Attempted to close application(s) matching '{exe_name}'.")
        else:
            print(f"No running application found matching '{exe_name}' to close.")
        return closed_any

if __name__ == '__main__':
    import time
    app_manager = AppManager()

    # Test opening Notepad (Windows specific example, adjust for your OS)
    if os.name == 'nt':
        print("Testing Notepad on Windows...")
        opened = app_manager.open_app("notepad")
        if opened:
            time.sleep(3) # Give it time to open
            closed = app_manager.close_app("notepad.exe") # or "notepad"
            print(f"Notepad closed: {closed}")
        else:
            print("Failed to open Notepad.")

        print("\nTesting Calculator on Windows...")
        opened_calc = app_manager.open_app("calculator")
        if opened_calc:
            time.sleep(3)
            closed_calc = app_manager.close_app("calc.exe") # Or a more specific name if needed
            print(f"Calculator closed: {closed_calc}")
        else:
            print("Failed to open Calculator.")
    else:
        print("Skipping Windows-specific app tests (Notepad, Calculator).")
        # Add tests for macOS/Linux apps here
        # e.g., app_manager.open_app("TextEdit") on macOS
        # or app_manager.open_app("gedit") on Linux

    # Example for a generic command (like trying to open a browser)
    # This is highly dependent on your system and what's in PATH
    # print("\nTesting opening Chrome (ensure it's in PATH or app_map)...")
    # opened_chrome = app_manager.open_app("chrome")
    # if opened_chrome:
    #     time.sleep(5)
    #     closed_chrome = app_manager.close_app("chrome.exe") # or "chrome" on Linux/macOS
    #     print(f"Chrome closed: {closed_chrome}")
    # else:
    #     print("Failed to open Chrome. Ensure it's in your PATH or configured in app_map.")

    # Test closing a non-existent app
    print("\nTesting closing a non-existent app:")
    app_manager.close_app("nonexistentapp123")

    # Need to import shutil for _find_app_path
    import shutil
