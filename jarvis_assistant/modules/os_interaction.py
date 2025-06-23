# Manages files, folders, executes CMD/PowerShell, controls system settings

import os
import shutil
import subprocess
from jarvis_assistant.utils.logger import get_logger # Corrected import path

# Ensure get_logger can be found if this module is run standalone for testing
if __name__ == '__main__' and __package__ is None:
    import sys
    # Temporarily add the project root to sys.path if running standalone
    # This assumes the script is in jarvis_assistant/modules/
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from jarvis_assistant.utils.logger import get_logger


class OSInteraction:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        # Initialize any OS-specific components here if needed
        pass

    def create_directory(self, dir_path: str) -> tuple[bool, str]:
        """Creates a directory."""
        # Expand environment variables like %USERNAME% or %USERPROFILE%
        dir_path = os.path.expandvars(dir_path)
        try:
            os.makedirs(dir_path, exist_ok=True)
            message = f"Directory created or already exists: {dir_path}"
            self.logger.info(message)
            return True, message
        except Exception as e:
            message = f"Error creating directory {dir_path}: {e}"
            self.logger.error(message)
            return False, message

    def delete_path(self, path: str) -> tuple[bool, str]:
        """Deletes a file or directory (recursively for directories)."""
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
                message = f"File deleted: {path}"
            elif os.path.isdir(path):
                shutil.rmtree(path)
                message = f"Directory deleted: {path}"
            else:
                message = f"Path does not exist: {path}"
                self.logger.warning(message)
                return False, message
            self.logger.info(message)
            return True, message
        except Exception as e:
            message = f"Error deleting path {path}: {e}"
            self.logger.error(message)
            return False, message

    def move_path(self, source_path: str, destination_path: str) -> tuple[bool, str]:
        """Moves a file or directory."""
        try:
            shutil.move(source_path, destination_path)
            message = f"Moved '{source_path}' to '{destination_path}'"
            self.logger.info(message)
            return True, message
        except Exception as e:
            message = f"Error moving '{source_path}' to '{destination_path}': {e}"
            self.logger.error(message)
            return False, message

    def list_directory_contents(self, dir_path: str) -> tuple[bool, str | list[str]]:
        """Lists contents of a directory."""
        if not os.path.isdir(dir_path):
            message = f"Error: Directory not found - {dir_path}"
            self.logger.warning(message)
            return False, message
        try:
            contents = os.listdir(dir_path)
            self.logger.info(f"Listed contents of {dir_path}: {contents}")
            if not contents:
                return True, "The directory is empty."
            return True, contents
        except Exception as e:
            message = f"Error listing directory {dir_path}: {e}"
            self.logger.error(message)
            return False, message

    def create_file(self, filepath: str, content: str = "", file_type: str = "txt") -> tuple[bool, str]:
        """
        Creates a file with the given content.
        For 'document', it creates a .txt file but logs it as a document placeholder.
        For 'spreadsheet', it creates a .csv file but logs it as a spreadsheet placeholder.
        Actual .docx or .xlsx creation would require dedicated libraries.
        """
        try:
            # Ensure the directory exists for the file
            dir_name = os.path.dirname(filepath)
            if dir_name:  # If filepath includes a directory
                os.makedirs(dir_name, exist_ok=True)

            actual_filepath = filepath
            if file_type == "document":
                # For now, create as .txt, but acknowledge it's a document.
                if not actual_filepath.endswith((".txt", ".md", ".rtf")): # basic text-based doc types
                    actual_filepath += ".txt"
                self.logger.info(f"Creating document (as text file): {actual_filepath}")
            elif file_type == "spreadsheet":
                # For now, create as .csv if content is suitable, or .txt
                if not actual_filepath.endswith((".csv", ".tsv")):
                    actual_filepath += ".csv"
                self.logger.info(f"Creating spreadsheet (as CSV): {actual_filepath}")
            else: # Default to text file (.txt)
                if "." not in os.path.basename(actual_filepath): # Add .txt if no extension
                    actual_filepath += ".txt"
                self.logger.info(f"Creating text file: {actual_filepath}")

            with open(actual_filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            message = f"{file_type.capitalize()} file created: {actual_filepath}"
            if actual_filepath != filepath:
                message += f" (requested as {filepath})"
            self.logger.info(message)
            return True, message
        except PermissionError as pe:
            message = f"Permission denied when trying to create file {filepath} (type: {file_type}): {pe}. Please try a different location."
            self.logger.error(message)
            return False, message
        except Exception as e:
            message = f"Error creating file {filepath} (type: {file_type}): {e}"
            self.logger.error(message)
            return False, message

    def read_file_content(self, filepath: str) -> tuple[bool, str]:
        """Reads the content of a file."""
        self.logger.info(f"Attempting to read file: {filepath}")
        try:
            if not os.path.isfile(filepath):
                message = f"Error: File not found at {filepath}"
                self.logger.warning(message)
                return False, message

            # Expand user path just in case it wasn't done before, though typically it should be.
            filepath = os.path.expanduser(filepath)

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.logger.info(f"Successfully read file: {filepath}")
            return True, content
        except FileNotFoundError: # Double check after expanduser, though os.path.isfile should catch it.
            message = f"Error: File not found at the expanded path {filepath}"
            self.logger.error(message)
            return False, message
        except PermissionError as pe:
            message = f"Permission denied when trying to read file {filepath}: {pe}."
            self.logger.error(message)
            return False, message
        except Exception as e:
            message = f"Error reading file {filepath}: {e}"
            self.logger.error(message)
            return False, message

    def execute_command(self, command: str, shell_type: str = None) -> tuple[bool, str]:
        """
        Executes a command.
        Determines shell_type if not provided (cmd for Windows, sh for POSIX).
        Handles multi-line commands for PowerShell and POSIX shells.
        """
        if shell_type is None:
            shell_type = "cmd" if os.name == 'nt' else "sh"
        shell_type = shell_type.lower()

        self.logger.info(f"Attempting to execute {shell_type} command: {command[:200]}{'...' if len(command) > 200 else ''}")
        try:
            if os.name == 'nt': # Windows specific handling for shell=True safety
                if shell_type.lower() == "powershell":
                    # Using list form for powershell is generally safer
                    process = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True, timeout=30)
                else: # Default to CMD
                    process = subprocess.run(command, capture_output=True, text=True, check=True, shell=True, timeout=30)
            else: # POSIX (Linux/macOS)
                if shell_type.lower() in ["bash", "sh", "zsh", "powershell"]: # powershell can be on linux too
                     process = subprocess.run([shell_type, "-c", command], capture_output=True, text=True, check=True, timeout=30)
                else: # Treat as a direct command if shell_type is not a known shell
                    process = subprocess.run(command.split(), capture_output=True, text=True, check=True, shell=False, timeout=30)

            output = process.stdout if process.stdout else ""
            if process.stderr:
                output += "\nSTDERR:\n" + process.stderr

            self.logger.info(f"Executed '{shell_type}' command: {command}\nOutput:\n{output.strip()}")
            return True, output.strip()
        except subprocess.CalledProcessError as e:
            error_message = f"Error executing command '{command}': {e}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
            self.logger.error(error_message)
            return False, error_message.strip()
        except subprocess.TimeoutExpired:
            error_message = f"Command '{command}' timed out after 30 seconds."
            self.logger.error(error_message)
            return False, error_message
        except FileNotFoundError:
            error_message = f"Error: '{shell_type}' or command base not found. Is it in your PATH?"
            self.logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"An unexpected error occurred while executing command '{command}': {e}"
            self.logger.error(error_message)
            return False, error_message

    def set_brightness(self, level: int) -> tuple[bool, str]:
        """Sets screen brightness (0-100)."""
        self.logger.info(f"Attempting to set brightness to {level}%")
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(level)
            message = f"Brightness set to {level}%"
            self.logger.info(message)
            return True, message
        except ImportError:
            message = "screen_brightness_control library not found. Cannot set brightness."
            self.logger.warning(message)
            return False, message
        except Exception as e:
            message = f"Error setting brightness: {e}"
            self.logger.error(message)
            return False, message

    def set_volume(self, level: float) -> tuple[bool, str]:
        """Sets master system volume (0.0-1.0)."""
        self.logger.info(f"Attempting to set volume to {level * 100}%")
        if not (0.0 <= level <= 1.0):
            message = "Volume level must be between 0.0 and 1.0."
            self.logger.warning(message)
            return False, message

        if os.name == 'nt': # Windows
            try:
                from comtypes import CLSCTX_ALL, CoInitialize, CoUninitialize
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

                CoInitialize() # Initialize COM library
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                volume.SetMasterVolumeLevelScalar(level, None)
                CoUninitialize() # Uninitialize COM library
                message = f"Volume set to {level*100:.0f}% on Windows."
                self.logger.info(message)
                return True, message
            except ImportError:
                message = "pycaw or comtypes library not found. Cannot set volume on Windows."
                self.logger.warning(message)
                return False, message
            except Exception as e:
                message = f"Error setting volume on Windows: {e}"
                self.logger.error(message)
                return False, message
        elif os.name == 'posix': # Linux/macOS
            if shutil.which("amixer"):
                try:
                    command = ["amixer", "-q", "sset", "Master", f"{int(level*100)}%"]
                    subprocess.run(command, check=True)
                    message = f"Volume set to {level*100:.0f}% on Linux using amixer."
                    self.logger.info(message)
                    return True, message
                except Exception as e:
                    message = f"Error setting volume on Linux using amixer: {e}"
                    self.logger.error(message)
                    return False, message
            elif hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
                try:
                    mac_volume = int(level * 100)
                    script = f"set volume output volume {mac_volume}"
                    subprocess.run(["osascript", "-e", script], check=True)
                    message = f"Volume set to {mac_volume}% on macOS."
                    self.logger.info(message)
                    return True, message
                except Exception as e:
                    message = f"Error setting volume on macOS using osascript: {e}"
                    self.logger.error(message)
                    return False, message
            else:
                message = "Volume control not implemented for this POSIX system (amixer not found or not macOS)."
                self.logger.warning(message)
                return False, message
        else:
            message = f"Volume control not implemented for OS: {os.name}"
            self.logger.warning(message)
            return False, message

if __name__ == '__main__':
    from jarvis_assistant.utils.logger import get_logger # Relative import for testing
    logger = get_logger("OSInteractionTest") # Initialize logger for the test scope
    os_interaction = OSInteraction()
    os_interaction.logger = logger

    # Test directory creation
    test_dir = os.path.join(os.path.expanduser("~"), "test_jarvis_os_dir_home") # Test in home
    os_interaction.create_directory(test_dir) # Create first for file tests

    # Test file creation
    test_file_path = os.path.join(test_dir, "test_os_interaction.txt")
    success, msg = os_interaction.create_file(test_file_path, "Hello from OSInteraction module!\nThis is a test file.")
    logger.info(f"Create file '{test_file_path}': {success} - {msg}")
    if success:
        assert os.path.isfile(test_file_path)

    # Test read file content
    if success: # Only if file creation was successful
        read_success, content = os_interaction.read_file_content(test_file_path)
        logger.info(f"Read file '{test_file_path}': {read_success} - Content: '{content[:50]}...'")
        assert read_success
        assert "Hello from OSInteraction module!" in content

    # Test list directory
    success_list, contents = os_interaction.list_directory_contents(test_dir)
    logger.info(f"List directory '{test_dir}': {success_list} - {contents}")
    if success_list and isinstance(contents, list):
        assert "test_os_interaction.txt" in contents

    # Test move file
    moved_file_path = os.path.join(test_dir, "moved_test_file.txt")
    success_move, msg_move = os_interaction.move_path(test_file_path, moved_file_path)
    logger.info(f"Move file: {success_move} - {msg_move}")
    if success_move:
        assert not os.path.exists(test_file_path)
        assert os.path.isfile(moved_file_path)
        test_file_path = moved_file_path

    # Test delete file
    success_del_file, msg_del_file = os_interaction.delete_path(test_file_path)
    logger.info(f"Delete file '{test_file_path}': {success_del_file} - {msg_del_file}")
    if success_del_file:
        assert not os.path.exists(test_file_path)

    # Test delete directory (cleanup)
    if os.path.exists(test_dir): # Ensure it exists before trying to delete
        success_del_dir, msg_del_dir = os_interaction.delete_path(test_dir)
        logger.info(f"Delete directory '{test_dir}': {success_del_dir} - {msg_del_dir}")
        if success_del_dir:
            assert not os.path.exists(test_dir)
    else:
        logger.info(f"Test directory '{test_dir}' already deleted or was not created.")


    logger.info("\nTesting CMD/Shell command (e.g., 'echo Hello World'):")
    cmd_to_run = "echo Hello Jarvis Assistant"
    shell = "cmd" if os.name == 'nt' else "sh"
    success_cmd, output_cmd = os_interaction.execute_command(cmd_to_run, shell_type=shell)
    logger.info(f"Execute command '{cmd_to_run}' via '{shell}': {success_cmd}\nOutput: {output_cmd}")
    assert success_cmd
    assert "Hello Jarvis Assistant" in output_cmd

    logger.info("\nTesting system settings (brightness/volume):")
    success_bright, msg_bright = os_interaction.set_brightness(75)
    logger.info(f"Set brightness: {success_bright} - {msg_bright}")

    success_vol, msg_vol = os_interaction.set_volume(0.5)
    logger.info(f"Set volume: {success_vol} - {msg_vol}")

    logger.info("OSInteraction tests complete.")
