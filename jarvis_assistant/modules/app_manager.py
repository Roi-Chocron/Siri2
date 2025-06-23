# Opens and closes applications
import os
import shutil # Required for shutil.which
import subprocess
import psutil
from jarvis_assistant.utils.logger import get_logger
from jarvis_assistant.config import USER_APP_PATHS # Import user-defined app paths

# Ensure get_logger can be found if this module is run standalone for testing
if __name__ == '__main__' and __package__ is None:
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from jarvis_assistant.utils.logger import get_logger
    from jarvis_assistant.config import USER_APP_PATHS


class AppManager:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        # Default common app names to their typical executable names.
        # This map can be overridden or extended by USER_APP_PATHS from config.py
        self.default_app_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe", # Windows specific, might need OS check
            "chrome": "chrome.exe" if os.name == 'nt' else "google-chrome", # google-chrome on Linux
            "firefox": "firefox.exe" if os.name == 'nt' else "firefox",
            "vscode": "code.exe" if os.name == 'nt' else "code",
            "browser": "chrome.exe" if os.name == 'nt' else "google-chrome", # Default browser to chrome
            "explorer": "explorer.exe", # Windows File Explorer
            "finder": "Finder.app", # macOS Finder (special handling)
            "textedit": "TextEdit.app", # macOS
            "gedit": "gedit", # Linux
            # Add more common apps with OS considerations
        }

        # Combine default map with user-configured paths. User paths take precedence.
        self.app_map = {**self.default_app_map, **USER_APP_PATHS}
        self.logger.info(f"AppManager initialized. Combined app map: {self.app_map}")


    def _find_app_path(self, app_name: str) -> str | None:
        """
        Tries to find the executable path for an application using a multi-step approach:
        1. Check if app_name is a direct path and exists.
        2. Check the combined app_map (defaults + user config).
        3. Check if app_name (or with .exe) is in PATH.
        4. Perform OS-specific searches in common installation locations.
        """
        app_name_lower = app_name.lower()
        self.logger.debug(f"Attempting to find path for app: '{app_name}'")

        # Handle special cases like "Microsoft Store" first
        if app_name_lower == "microsoft store":
            self.logger.info("Opening Microsoft Store is complex and may require specific shell commands not generically implemented. User should use 'explorer.exe shell:AppsFolder' or configure a shortcut if needed.")
            # Returning None will trigger the "could not find path" warning, which is appropriate.
            # Or, we could return a special marker or handle it in open_app, but for now, let _find_app_path fail.
            # For a slightly better UX, we can prevent further searching if it's a known complex case.
            return None # This will lead to the standard "Could not automatically find path" warning.

        # 0. If app_name itself is an existing path (absolute or relative to cwd)
        if os.path.exists(app_name):
            self.logger.debug(f"Found '{app_name}' as a direct existing path.")
            return os.path.abspath(app_name)

        # 1. Check combined app_map (user-defined paths first, then defaults)
        # User paths in USER_APP_PATHS from config.py might be aliases or full paths.
        # Default app_map also contains aliases to common executables.

        # Check app_name_lower first, then original app_name for case sensitivity in map keys
        mapped_path_keys = [app_name_lower, app_name]
        for key in mapped_path_keys:
            if key in self.app_map:
                path_from_map = self.app_map[key]
                self.logger.debug(f"Found '{key}' in app_map: '{path_from_map}'")
                # If the mapped path is already absolute and exists, use it
                if os.path.isabs(path_from_map) and os.path.exists(path_from_map):
                    return path_from_map
                # If it's not absolute, try finding it with shutil.which (treat as command/exe name)
                found_via_which = shutil.which(path_from_map)
                if found_via_which:
                    self.logger.debug(f"Path from map '{path_from_map}' found in PATH: '{found_via_which}'")
                    return found_via_which
                # If it was a name like "chrome.exe" and not found by which, it might be a relative path error or missing
                self.logger.debug(f"Path from map '{path_from_map}' for key '{key}' not found directly or in PATH.")


        # 2. Check if app_name (or app_name.exe for Windows) is an executable in PATH
        found_in_path = shutil.which(app_name)
        if found_in_path:
            self.logger.debug(f"Found '{app_name}' in PATH: '{found_in_path}'")
            return found_in_path
        if os.name == 'nt' and not app_name.endswith(".exe"): # Windows convenience: try adding .exe
            found_in_path_exe = shutil.which(app_name + ".exe")
            if found_in_path_exe:
                self.logger.debug(f"Found '{app_name}.exe' in PATH: '{found_in_path_exe}'")
                return found_in_path_exe

        # 3. Platform-specific searches in common installation locations
        # These are heuristics and might not cover all cases.
        if os.name == 'nt': # Windows
            # Search in Program Files, Program Files (x86), LocalAppData
            prog_files = [os.environ.get("ProgramFiles", "C:\\Program Files"),
                          os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")]
            local_app_data = os.environ.get("LocalAppData", "")

            # Common patterns: ProgFiles\AppName\AppName.exe or ProgFiles\Vendor\AppName\AppName.exe
            # Check for app_name as a directory containing app_name.exe
            for base_path in prog_files:
                path_to_check = os.path.join(base_path, app_name, app_name + ".exe")
                if os.path.exists(path_to_check):
                    self.logger.debug(f"Found in common Windows path: {path_to_check}")
                    return path_to_check

            # Check common vendor folders (e.g., Google for Chrome) - this is very heuristic
            # A more robust way would be to check Windows Registry for installed apps, which is complex.
            # Example: os.path.join(prog_files[0], "Google", "Chrome", "Application", "chrome.exe")

            if local_app_data:
                path_to_check = os.path.join(local_app_data, "Programs", app_name, app_name + ".exe")
                if os.path.exists(path_to_check):
                     self.logger.debug(f"Found in LocalAppData: {path_to_check}")
                     return path_to_check

            # Placeholder: Search for apps installed via Microsoft Store (very complex, involves PowerShell or registry)
            # self.logger.debug("Windows Store app path finding not yet implemented.")

        elif os.name == 'posix': # macOS or Linux
            if shutil.which(app_name_lower): # Check PATH again for lowercase if original check missed
                self.logger.debug(f"Found '{app_name_lower}' in PATH (second check).")
                return app_name_lower

            # macOS specific: /Applications/AppName.app or /Applications/AppName.app/Contents/MacOS/AppName
            if sys.platform == 'darwin': # macOS
                # Try common variations like "Google Chrome.app"
                variations = [app_name, app_name.capitalize(), app_name.title()]
                for variation in variations:
                    mac_app_bundle_path = f"/Applications/{variation}.app"
                    if os.path.exists(mac_app_bundle_path):
                        self.logger.debug(f"Found macOS app bundle: {mac_app_bundle_path}")
                        # For `open` command, the .app path is usually sufficient.
                        # If direct executable needed:
                        # executable_path = os.path.join(mac_app_bundle_path, "Contents", "MacOS", variation.split('.')[0])
                        # if os.path.exists(executable_path): return executable_path
                        return mac_app_bundle_path # Return .app path for 'open' command

        self.logger.warning(f"Could not automatically find path for '{app_name}'. User might need to specify full path or add to USER_APP_PATHS in config.")
        return None


    def open_app(self, app_name_or_path: str) -> bool:
        """Opens an application by its name, alias from config, or full path."""
        app_path = self._find_app_path(app_name_or_path)

        # If _find_app_path didn't find it, but app_name_or_path itself is a valid path (e.g. user provided full path)
        if not app_path and os.path.exists(app_name_or_path):
            app_path = os.path.abspath(app_name_or_path)
            self.logger.info(f"Using provided path directly: {app_path}")

        if not app_path:
            self.logger.error(f"Application '{app_name_or_path}' not found or path could not be determined.")
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
