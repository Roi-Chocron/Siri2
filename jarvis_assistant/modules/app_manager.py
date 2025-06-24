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
            # Base map with lowercase keys for easier lookup
            # Windows-centric initially, then adjusted for other OS
            "notepad": "notepad.exe",
            "calculator": "calc.exe", # Command to launch calculator
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "mozilla firefox": "firefox.exe",
            "edge": "msedge.exe",
            "microsoft edge": "msedge.exe",
            "browser": "msedge.exe", # Default browser to Edge on Windows
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "vscode": "code.exe",
            "visual studio code": "code.exe",
            "steam": "steam.exe", # For opening Steam client itself
            # Common macOS apps (will be overridden if not on macOS)
            "finder": "Finder.app",
            "textedit": "TextEdit.app",
            "safari": "Safari.app",
            # Common Linux apps (will be overridden if not on Linux)
            "gedit": "gedit",
        }

        # OS-specific adjustments for executable names or different defaults
        if os.name != 'nt':
            self.default_app_map["chrome"] = "google-chrome"
            self.default_app_map["google chrome"] = "google-chrome"
            self.default_app_map["firefox"] = "firefox"
            self.default_app_map["mozilla firefox"] = "firefox"
            self.default_app_map["vscode"] = "code"
            self.default_app_map["visual studio code"] = "code"
            self.default_app_map["browser"] = "google-chrome" # Default for Linux
            self.default_app_map.pop("explorer", None) # explorer.exe is Windows specific
            self.default_app_map.pop("file explorer", None)
            self.default_app_map.pop("edge", None) # msedge.exe is Windows specific
            self.default_app_map.pop("microsoft edge", None)
            self.default_app_map.pop("steam", None) # steam.exe is Windows specific, Linux has 'steam'

            if sys.platform == 'darwin': # macOS specific overrides
                self.default_app_map["browser"] = "Safari.app" # Or stick to chrome if preferred
                self.default_app_map.pop("gedit", None) # gedit not default on macOS
            else: # Linux (not darwin, not nt)
                self.default_app_map.pop("finder", None)
                self.default_app_map.pop("textedit", None)
                self.default_app_map.pop("safari", None)
                self.default_app_map["steam"] = "steam" # Linux command for steam

        # User-configured paths (keys should also ideally be lowercase for consistency)
        # We'll lowercase user keys when creating the final map.
        user_app_paths_lower = {k.lower(): v for k, v in USER_APP_PATHS.items()}
        self.app_map = {**self.default_app_map, **user_app_paths_lower}
        self.logger.info(f"AppManager initialized. Combined app map (keys lowercased): {self.app_map}")


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
        # The self.app_map keys are now all lowercase due to initialization logic.
        if app_name_lower in self.app_map:
            path_from_map = self.app_map[app_name_lower]
            self.logger.debug(f"Found '{app_name_lower}' in app_map, maps to: '{path_from_map}'")

            # If the mapped path is already an existing absolute path, use it directly.
            if os.path.isabs(path_from_map) and os.path.exists(path_from_map):
                self.logger.debug(f"Mapped path '{path_from_map}' is an existing absolute path.")
                return path_from_map

            # If not absolute, or absolute but not existing, treat path_from_map as an executable name
            # and try to find it with shutil.which (searches PATH).
            # This handles cases where app_map stores "msedge.exe" and shutil.which finds it.
            found_via_which = shutil.which(path_from_map)
            if found_via_which:
                self.logger.debug(f"Mapped name '{path_from_map}' (treated as command) found in PATH by shutil.which: '{found_via_which}'")
                return found_via_which

            # If path_from_map was, for example, "C:\\NonExistent\\Path.exe" from USER_APP_PATHS,
            # or "some_custom_command" not in PATH, it won't be found here.
            # The subsequent heuristic search might still find it if it's a common app name in a standard location.
            self.logger.debug(f"Mapped name '{path_from_map}' for key '{app_name_lower}' is not an existing absolute path and not found in PATH by shutil.which. Will proceed to other search methods.")
        else:
            self.logger.debug(f"'{app_name_lower}' not found in pre-defined app_map.")


        # 2. Check if app_name itself (or app_name.exe for Windows) is an executable in PATH
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

            # Search in Program Files, Program Files (x86)
            search_paths = [os.environ.get("ProgramFiles", "C:\\Program Files"),
                            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")]
            if local_app_data: # Add LocalAppData\Programs to search paths
                search_paths.append(os.path.join(local_app_data, "Programs"))

            possible_exe_names = [app_name + ".exe", app_name_lower + ".exe"]
            # If app_name is an alias in default_app_map, also try its mapped exe name
            # e.g. if app_name is "Firefox", default_app_map might map it to "firefox.exe"
            if app_name_lower in self.default_app_map and self.default_app_map[app_name_lower] not in possible_exe_names:
                possible_exe_names.append(self.default_app_map[app_name_lower])

            # Also consider if app_name itself is a common exe name but without .exe
            if not app_name_lower.endswith(".exe") and app_name_lower not in [name.replace(".exe","") for name in possible_exe_names]:
                 possible_exe_names.append(app_name_lower + ".exe")


            for base_dir in search_paths:
                if not base_dir or not os.path.isdir(base_dir):
                    continue

                # Scenario 1: base_dir\app_name\some_exe.exe (e.g. C:\Program Files\Mozilla Firefox\firefox.exe)
                # User might say "open firefox" or "open Mozilla Firefox"
                # We should check for a directory named app_name or variations.
                app_dir_variations = [app_name, app_name.title()]
                if app_name_lower in self.default_app_map: # e.g. "firefox" maps to "firefox.exe"
                    # if app_name is "Firefox", its entry in default_app_map might be "firefox" (the exe)
                    # or it might be a variation like "Mozilla Firefox".
                    # This part is tricky. For now, let's focus on the app_name as a directory.
                    pass


                for app_folder_name in os.listdir(base_dir):
                    # Check if app_name (or part of it) is in the folder name for broader matching
                    # e.g., app_name "Firefox" should match folder "Mozilla Firefox"
                    if app_name.lower() in app_folder_name.lower():
                        potential_app_dir = os.path.join(base_dir, app_folder_name)
                        if os.path.isdir(potential_app_dir):
                            self.logger.debug(f"Searching in potential app directory: {potential_app_dir}")
                            # Look for common executable names within this directory
                            for item in os.listdir(potential_app_dir):
                                for exe_name_candidate in possible_exe_names:
                                    if item.lower() == exe_name_candidate.lower():
                                        found_path = os.path.join(potential_app_dir, item)
                                        self.logger.info(f"Found executable '{item}' in '{potential_app_dir}' for app '{app_name}'")
                                        return found_path
                                # Also look for executables that simply contain the app_name (e.g. EADesktop.exe for EA)
                                if app_name_lower in item.lower() and item.lower().endswith(".exe"):
                                    found_path = os.path.join(potential_app_dir, item)
                                    self.logger.info(f"Found related executable '{item}' in '{potential_app_dir}' for app '{app_name}'")
                                    return found_path

                            # If no direct match, try common subfolders like 'bin' or the app_folder_name again
                            for sub_folder_name in [app_folder_name, "bin", "App"]: # Common sub-dir names
                                potential_sub_app_dir = os.path.join(potential_app_dir, sub_folder_name)
                                if os.path.isdir(potential_sub_app_dir):
                                    for item in os.listdir(potential_sub_app_dir):
                                         for exe_name_candidate in possible_exe_names:
                                            if item.lower() == exe_name_candidate.lower():
                                                found_path = os.path.join(potential_sub_app_dir, item)
                                                self.logger.info(f"Found executable '{item}' in sub-directory '{potential_sub_app_dir}' for app '{app_name}'")
                                                return found_path


            # Placeholder: Search for apps installed via Microsoft Store (very complex)
            # self.logger.debug("Windows Store app path finding not yet implemented.")

            # Specific check for Microsoft Edge if not found by other means yet
            if app_name_lower in ["edge", "microsoft edge"]:
                edge_paths_to_try = [
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Microsoft\\Edge\\Application\\msedge.exe"),
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft\\Edge\\Application\\msedge.exe")
                ]
                for edge_path in edge_paths_to_try:
                    if os.path.exists(edge_path):
                        self.logger.info(f"Found Microsoft Edge at specific known path: {edge_path}")
                        return edge_path

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
        app_name_lower = app_name_or_exe.lower()
        self.logger.info(f"Attempting to close application: '{app_name_or_exe}'")

        # Windows specific process name mapping for common apps
        # This helps bridge the gap between friendly names and actual process names.
        windows_process_map = {
            "calculator": ["calculatorapp.exe", "calculator.exe", "calc.exe"], # Modern UWP, older, launch command
            "calc": ["calculatorapp.exe", "calculator.exe", "calc.exe"],
            "microsoft edge": ["msedge.exe"],
            "edge": ["msedge.exe"],
            "notepad": ["notepad.exe"],
            "chrome": ["chrome.exe"],
            "google chrome": ["chrome.exe"],
            "firefox": ["firefox.exe"],
            "mozilla firefox": ["firefox.exe"],
            "vscode": ["code.exe"],
            "visual studio code": ["code.exe"],
            "steam": ["steam.exe", "steamwebhelper.exe"], # steamwebhelper is also common
            # Add more as needed
        }

        target_process_names = []
        if os.name == 'nt':
            # Use the map first if the friendly name is in it
            if app_name_lower in windows_process_map:
                target_process_names.extend(windows_process_map[app_name_lower])
            else:
                # Fallback: use the provided name, and with .exe
                target_process_names.append(app_name_lower)
                if not app_name_lower.endswith(".exe"):
                    target_process_names.append(app_name_lower + ".exe")
        else: # For macOS/Linux
            # Use the mapped name from self.app_map (which might be 'google-chrome' for 'chrome')
            # or the direct app_name_or_exe if not in map.
            mapped_exe = self.app_map.get(app_name_lower, app_name_lower)
            target_process_names.append(mapped_exe)
            # On Linux/macOS, .app is not a process name directly, but the executable inside is.
            # For simplicity, we're relying on the main executable name.
            if mapped_exe.endswith(".app") and sys.platform == "darwin": # e.g. Safari.app
                target_process_names.append(mapped_exe.replace(".app", "")) # Try "Safari"

        self.logger.debug(f"Target process names for closing '{app_name_or_exe}': {target_process_names}")

        closed_any = False
        terminated_pids = set()

        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                proc_name_lower = proc.info['name'].lower()
                proc_exe_lower = ""
                if proc.info['exe']: # proc.exe() can require higher privileges or fail
                    proc_exe_lower = os.path.basename(proc.info['exe']).lower()

                for target_name in target_process_names:
                    target_name_lower = target_name.lower()
                    # Match if process name is exactly the target OR
                    # if process executable basename is exactly the target.
                    # Using '==' for exact match is safer than 'in' to avoid partial matches.
                    if proc_name_lower == target_name_lower or \
                       (proc_exe_lower and proc_exe_lower == target_name_lower):

                        if proc.info['pid'] in terminated_pids: # Already terminated
                            continue

                        self.logger.info(f"Found process '{proc.info['name']}' (PID: {proc.info['pid']}, EXE: {proc.info['exe']}) matching target '{target_name}'. Terminating...")
                        p = psutil.Process(proc.info['pid'])
                        p.terminate() # Graceful termination
                        terminated_pids.add(proc.info['pid'])
                        closed_any = True
                        # Found a match for this target_name, break from inner loop for this proc
                        # To avoid trying to kill the same process multiple times if it matches multiple targets (unlikely here)
                        break

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                self.logger.debug(f"Process PID {proc.info.get('pid', 'N/A')} likely already exited or access denied.")
            except Exception as e:
                self.logger.error(f"Error while processing/terminating PID {proc.info.get('pid', 'N/A')} for app '{app_name_or_exe}': {e}")

        if closed_any:
            self.logger.info(f"Attempted to close application(s) matching '{app_name_or_exe}'.")
            # It might be good to wait a moment and check if processes actually closed
            # For now, we assume terminate() initiates the process.
        else:
            self.logger.warning(f"No running application found matching any of {target_process_names} to close for input '{app_name_or_exe}'.")
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
