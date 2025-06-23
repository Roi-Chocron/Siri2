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

    def create_text_file(self, filepath: str, content: str = "") -> tuple[bool, str]:
        """Creates a text file with the given content."""
        try:
            # Ensure the directory exists for the file
            dir_name = os.path.dirname(filepath)
            if dir_name: # If filepath includes a directory
                os.makedirs(dir_name, exist_ok=True)

            with open(filepath, 'w') as f:
                f.write(content)
            message = f"File created: {filepath}"
            self.logger.info(message)
            return True, message
        except Exception as e:
            message = f"Error creating file {filepath}: {e}"
            self.logger.error(message)
            return False, message

    # Placeholder for document/spreadsheet creation - will require specific libraries
    def create_document_file(self, filepath: str, content: str = "") -> tuple[bool, str]:
        message = f"Placeholder: Create document {filepath} with content: '{content[:50]}...'"
        self.logger.info(message)
        # Example: using python-docx
        # from docx import Document
        # document = Document()
        # document.add_paragraph(content)
        # document.save(filepath)
        return True, message

    def create_spreadsheet_file(self, filepath: str, data: list = None) -> tuple[bool, str]:
        message = f"Placeholder: Create spreadsheet {filepath}"
        self.logger.info(message)
        # Example: using openpyxl
        # from openpyxl import Workbook
        # wb = Workbook()
        # sheet = wb.active
        # if data:
        #     for row_idx, row_data in enumerate(data, 1):
        #         for col_idx, cell_value in enumerate(row_data, 1):
        #             sheet.cell(row=row_idx, column=col_idx, value=cell_value)
        # wb.save(filepath)
        return True, message

    def execute_command(self, command: str, shell_type: str = "cmd") -> tuple[bool, str]:
        """Executes a command in CMD or PowerShell."""
        self.logger.info(f"Attempting to execute {shell_type} command: {command}")
        try:
            if os.name == 'nt': # Windows specific handling for shell=True safety
                if shell_type.lower() == "powershell":
                    # Using list form for powershell is generally safer
                    process = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True, timeout=30)
                else: # Default to CMD
                    # For CMD, shell=True is often used but ensure command is sanitized if coming from LLM directly
                    # A safer way for specific commands is to not use shell=True and pass command and args as a list
                    process = subprocess.run(command, capture_output=True, text=True, check=True, shell=True, timeout=30)
            else: # POSIX (Linux/macOS)
                # shell=True can be a security hazard if command is constructed from external input.
                # If shell_type is 'bash' or 'sh', it implies shell features are needed.
                # For simple commands, shell=False and passing command as list is safer.
                # Given the project's nature, we might receive complex shell commands.
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
            # Linux: using amixer (alsa-utils)
            if shutil.which("amixer"):
                try:
                    # Example: amixer sset Master 50%
                    command = ["amixer", "-q", "sset", "Master", f"{int(level*100)}%"]
                    subprocess.run(command, check=True)
                    message = f"Volume set to {level*100:.0f}% on Linux using amixer."
                    self.logger.info(message)
                    return True, message
                except Exception as e:
                    message = f"Error setting volume on Linux using amixer: {e}"
                    self.logger.error(message)
                    return False, message
            # macOS: using osascript
            elif hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
                try:
                    # Convert 0.0-1.0 to 0-100 for osascript
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
    os_interaction.logger = logger # Assign the test logger

    # Test directory creation
    test_dir = "test_jarvis_os_dir"
    success, msg = os_interaction.create_directory(test_dir)
    logger.info(f"Create directory '{test_dir}': {success} - {msg}")
    if success:
        assert os.path.isdir(test_dir)

    # Test file creation
    test_file_path = os.path.join(test_dir, "test_os_interaction.txt")
    success, msg = os_interaction.create_text_file(test_file_path, "Hello from OSInteraction module!")
    logger.info(f"Create file '{test_file_path}': {success} - {msg}")
    if success:
        assert os.path.isfile(test_file_path)

    # Test list directory
    success, contents = os_interaction.list_directory_contents(test_dir)
    logger.info(f"List directory '{test_dir}': {success} - {contents}")
    if success and isinstance(contents, list):
        assert "test_os_interaction.txt" in contents

    # Test move file
    moved_file_path = os.path.join(test_dir, "moved_test_file.txt")
    success, msg = os_interaction.move_path(test_file_path, moved_file_path)
    logger.info(f"Move file: {success} - {msg}")
    if success:
        assert not os.path.exists(test_file_path)
        assert os.path.isfile(moved_file_path)
        test_file_path = moved_file_path # Update for subsequent deletion

    # Test delete file
    success, msg = os_interaction.delete_path(test_file_path)
    logger.info(f"Delete file '{test_file_path}': {success} - {msg}")
    if success:
        assert not os.path.exists(test_file_path)

    # Test delete directory
    success, msg = os_interaction.delete_path(test_dir)
    logger.info(f"Delete directory '{test_dir}': {success} - {msg}")
    if success:
        assert not os.path.exists(test_dir)

    # Test command execution
    logger.info("\nTesting CMD/Shell command (e.g., 'echo Hello World'):")
    # Using a simple echo command for cross-platform compatibility in testing.
    # Actual commands like ipconfig or Get-Process are harder to assert consistently in a generic test.
    cmd_to_run = "echo Hello Jarvis Assistant"
    shell = "cmd" if os.name == 'nt' else "sh" # Use 'sh' for POSIX, 'cmd' for Windows
    success, output = os_interaction.execute_command(cmd_to_run, shell_type=shell)
    logger.info(f"Execute command '{cmd_to_run}' via '{shell}': {success}\nOutput: {output}")
    assert success
    assert "Hello Jarvis Assistant" in output

    # Test settings (actual hardware interaction might not occur in sandbox)
    logger.info("\nTesting system settings (brightness/volume):")
    success, msg = os_interaction.set_brightness(75)
    logger.info(f"Set brightness: {success} - {msg}")

    success, msg = os_interaction.set_volume(0.5)
    logger.info(f"Set volume: {success} - {msg}")

    logger.info("OSInteraction tests complete.")
