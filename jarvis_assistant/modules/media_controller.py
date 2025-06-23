# Integrates with media players for playback control

import subprocess
import os
import shutil # For shutil.which, used in _execute_player_command
from jarvis_assistant.utils.logger import get_logger

# Ensure get_logger can be found if this module is run standalone for testing
if __name__ == '__main__' and __package__ is None:
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from jarvis_assistant.utils.logger import get_logger

class MediaController:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        # For more direct control, platform-specific libraries or APIs would be better
        # e.g., dbus for Spotify on Linux, AppleScript for Apple Music/Spotify on macOS
        pass

    def _execute_player_command(self, player_name: str, command: str, track_or_playlist: str = None) -> tuple[bool, str]:
        """
        Generic helper to send commands. This is highly dependent on CLI support of players.
        Returns (success, message)
        """
        player_lower = player_name.lower() if player_name else "default"
        self.logger.info(f"Attempting to execute '{command}' for player '{player_lower}'" + (f" with track/playlist '{track_or_playlist}'" if track_or_playlist else ""))

        # --- macOS Specific Examples using osascript ---
        if os.name == 'posix' and hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
            if player_lower in ["spotify", "apple music", "music", "default"]: # Treat default as Music/Spotify
                player_app_name = "Spotify" if player_lower == "spotify" else "Music" # Default to Music for "default" or "apple music"
                if player_lower == "default" and not self._is_player_running_macos("Spotify") and self._is_player_running_macos("Music"):
                     player_app_name = "Music"
                elif player_lower == "default" and self._is_player_running_macos("Spotify"):
                     player_app_name = "Spotify"
                elif player_lower == "default": # Neither running, try spotify first
                    player_app_name = "Spotify"


                script = ""
                if command == "play":
                    if track_or_playlist:
                        # This is complex. For Spotify: `play track "{track_uri}"`
                        # For Apple Music: `play (first track of playlist "{playlist_name}" whose name is "{track_name}")`
                        # Simplified: if track_or_playlist is a spotify URI
                        if "spotify:track:" in track_or_playlist or "spotify:album:" in track_or_playlist or "spotify:playlist:" in track_or_playlist :
                             script = f'tell application "Spotify" to play track "{track_or_playlist}"'
                             player_app_name = "Spotify" # Force Spotify if URI is given
                        else:
                            script = f'tell application "{player_app_name}" to play' # General play
                            self.logger.info(f"Playing specific track/playlist '{track_or_playlist}' by name via AppleScript is complex and not fully implemented; attempting general play for {player_app_name}.")
                    else:
                        script = f'tell application "{player_app_name}" to play'
                elif command == "pause":
                    script = f'tell application "{player_app_name}" to pause'
                elif command == "next":
                    script = f'tell application "{player_app_name}" to next track'
                elif command == "previous":
                    script = f'tell application "{player_app_name}" to previous track'

                if script:
                    try:
                        subprocess.run(["osascript", "-e", script], check=True, timeout=5)
                        msg = f"Executed '{command}' for {player_app_name} on macOS."
                        self.logger.info(msg)
                        return True, msg
                    except subprocess.TimeoutExpired:
                        msg = f"Command '{command}' for {player_app_name} timed out on macOS."
                        self.logger.error(msg)
                        return False, msg
                    except Exception as e:
                        msg = f"Error executing AppleScript for {player_app_name}: {e}"
                        self.logger.error(msg)
                        return False, msg
                else:
                    msg = f"Command '{command}' not directly supported for {player_app_name} via simple AppleScript in this example."
                    self.logger.warning(msg)
                    return False, msg
            else:
                msg = f"Player {player_name} not directly supported with AppleScript in this example."
                self.logger.warning(msg)
                return False, msg

        # --- Linux Specific Examples (very basic, assuming CLI tools like playerctl) ---
        elif os.name == 'posix': # Generic Linux
            if not shutil.which("playerctl"):
                msg = "playerctl not found. Please install it to control media players on Linux."
                self.logger.warning(msg)
                return False, msg

            # Determine target player for playerctl. If 'default', playerctl might pick active or first available.
            # Specific player names for playerctl might be 'spotify', 'vlc', etc.
            playerctl_target = []
            if player_lower != "default":
                playerctl_target = ["-p", player_lower] # e.g. playerctl -p spotify play-pause

            base_cmd = ["playerctl"] + playerctl_target
            action_cmd_str = ""

            if command == "play":
                action_cmd_str = "play-pause" # playerctl play-pause toggles. Use "play" to ensure playing.
                if track_or_playlist: # playerctl can open URIs
                     try:
                        subprocess.run(base_cmd + ["open", track_or_playlist], check=True, timeout=5)
                        subprocess.run(base_cmd + ["play"], check=True, timeout=5) # Ensure it plays after opening
                        msg = f"Attempted to open and play '{track_or_playlist}' with {player_lower if player_lower != 'default' else 'default player'} via playerctl."
                        self.logger.info(msg)
                        return True, msg
                     except Exception as e:
                        msg = f"Error opening/playing '{track_or_playlist}' with playerctl: {e}"
                        self.logger.error(msg)
                        return False, msg
                else: # Just play/pause
                    action_cmd_str = "play" # More explicit
            elif command == "pause":
                action_cmd_str = "pause"
            elif command == "next":
                action_cmd_str = "next"
            elif command == "previous":
                action_cmd_str = "previous"

            if action_cmd_str:
                try:
                    subprocess.run(base_cmd + [action_cmd_str], check=True, timeout=5)
                    msg = f"Executed '{action_cmd_str}' for {player_lower if player_lower != 'default' else 'default player'} via playerctl on Linux."
                    self.logger.info(msg)
                    return True, msg
                except subprocess.TimeoutExpired:
                    msg = f"Command '{action_cmd_str}' for {player_lower} timed out with playerctl."
                    self.logger.error(msg)
                    return False, msg
                except Exception as e:
                    msg = f"Error using playerctl for {player_lower} on Linux: {e}"
                    self.logger.error(msg)
                    return False, msg
            else:
                msg = f"Command '{command}' not directly supported with playerctl in this example."
                self.logger.warning(msg)
                return False, msg

        # --- Windows Specific (very basic, if player has CLI) ---
        elif os.name == 'nt':
            msg = f"Direct CLI control for '{player_name}' on Windows is often limited or player-specific. This function is a placeholder for Windows."
            self.logger.warning(msg)
            if player_lower == "spotify":
                msg += " For Spotify on Windows, consider third-party tools or its Web API for robust control."
            return False, msg # Placeholder, as generic CLI is unreliable

        msg = f"Unsupported OS or player for direct CLI command: {os.name}, {player_name}"
        self.logger.warning(msg)
        return False, msg

    def _is_player_running_macos(self, app_name: str) -> bool:
        """Checks if a player is running on macOS."""
        try:
            # Count processes with the given name
            script = f'tell application "System Events" to count processes whose name is "{app_name}"'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True, timeout=2)
            return int(result.stdout.strip()) > 0
        except Exception:
            return False

    def play(self, player_name: str, track_or_playlist: str = None) -> tuple[bool, str]:
        """Plays a specific song or playlist, or resumes playback."""
        return self._execute_player_command(player_name, "play", track_or_playlist)

    def pause(self, player_name: str) -> tuple[bool, str]:
        """Pauses playback."""
        return self._execute_player_command(player_name, "pause")

    def skip_track(self, player_name: str) -> tuple[bool, str]:
        """Skips to the next track."""
        return self._execute_player_command(player_name, "next")

    def previous_track(self, player_name: str) -> tuple[bool, str]:
        """Goes to the previous track."""
        return self._execute_player_command(player_name, "previous")

    # Rewind/fast-forward are harder with generic CLIs.
    # Usually requires specific player support (e.g. `playerctl position 10-` or `playerctl position 10+`)

if __name__ == '__main__':
    import time
    # Ensure logger is available for standalone test
    logger = get_logger("MediaControllerTest")
    controller = MediaController()
    controller.logger = logger # Assign test logger

    # These tests are highly dependent on your OS and installed software (Spotify, Apple Music, playerctl)
    # They are more illustrative than guaranteed to work out-of-the-box.
    logger.info("Starting MediaController tests...")

    # --- macOS Test ---
    if os.name == 'posix' and hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
        logger.info("\n--- Testing on macOS ---")
        logger.info("Attempting to control Spotify (ensure it's running)...")
        # success, msg = controller.play("Spotify", "spotify:track:4uLU6hMCjMI75M1A2tKUQC") # Example track URI
        success, msg = controller.play("Spotify")
        logger.info(f"Play Spotify: {success} - {msg}")
        if success: time.sleep(3)

        success, msg = controller.pause("Spotify")
        logger.info(f"Pause Spotify: {success} - {msg}")
        if success: time.sleep(1)

        success, msg = controller.skip_track("Spotify")
        logger.info(f"Skip Spotify: {success} - {msg}")
        if success: time.sleep(1)

        success, msg = controller.play("Spotify")
        logger.info(f"Play Spotify (after skip): {success} - {msg}")
        if success: time.sleep(3)

        success, msg = controller.previous_track("Spotify")
        logger.info(f"Previous Spotify: {success} - {msg}")
        if success: time.sleep(3)

        success, msg = controller.pause("Spotify")
        logger.info(f"Pause Spotify (final): {success} - {msg}")

    # --- Linux Test (requires playerctl and a compatible player like Spotify running) ---
    elif os.name == 'posix':
        logger.info("\n--- Testing on Linux (requires playerctl and Spotify/compatible player) ---")
        if shutil.which("playerctl"):
            logger.info("playerctl found. Attempting to control Spotify (ensure it's running and supports MPRIS)...")
            # success, msg = controller.play("spotify", "spotify:track:4uLU6hMCjMI75M1A2tKUQC")
            # logger.info(f"Play Spotify track: {success} - {msg}")
            # if success: time.sleep(3)

            success, msg = controller.play("spotify")
            logger.info(f"Play/Pause Spotify: {success} - {msg}")
            if success: time.sleep(3)

            success, msg = controller.pause("spotify")
            logger.info(f"Pause Spotify: {success} - {msg}")
            if success: time.sleep(1)

            success, msg = controller.skip_track("spotify")
            logger.info(f"Skip Spotify: {success} - {msg}")
            if success: time.sleep(1)

            success, msg = controller.play("spotify")
            logger.info(f"Play Spotify (after skip): {success} - {msg}")
            if success: time.sleep(3)

            success, msg = controller.previous_track("spotify")
            logger.info(f"Previous Spotify: {success} - {msg}")
            if success: time.sleep(3)

            success, msg = controller.pause("spotify")
            logger.info(f"Pause Spotify (final): {success} - {msg}")
        else:
            logger.warning("playerctl not found. Skipping Linux media control tests.")

    # --- Windows Test (mostly informative as direct CLI is limited) ---
    elif os.name == 'nt':
        logger.info("\n--- Testing on Windows (CLI control is limited) ---")
        logger.info("Attempting to send 'play' to Spotify (likely won't work via generic CLI)...")
        success, msg = controller.play("Spotify")
        logger.info(f"Play Spotify (Windows): {success} - {msg}")
        logger.info("This command on Windows is a placeholder and unlikely to have an effect without specific tools/APIs.")

    logger.info("\nMedia controller tests finished.")
    # They are more illustrative than guaranteed to work out-of-the-box.

    # --- macOS Test ---
    if os.name == 'posix' and hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
        print("\n--- Testing on macOS ---")
        print("Attempting to control Spotify (ensure it's running)...")
        # controller.play("Spotify", "spotify:track:4uLU6hMCjMI75M1A2tKUQC") # Example track URI
        controller.play("Spotify")
        time.sleep(3)
        controller.pause("Spotify")
        time.sleep(1)
        controller.skip_track("Spotify")
        time.sleep(1)
        controller.play("Spotify") # Resume with new track
        time.sleep(3)
        controller.previous_track("Spotify")
        time.sleep(3)
        controller.pause("Spotify")

        # print("\nAttempting to control Apple Music (ensure it's running)...")
        # controller.play("Apple Music", "Your Playlist Name") # Playing specific playlist is complex
        # controller.play("Music")
        # time.sleep(3)
        # controller.pause("Music")

    # --- Linux Test (requires playerctl and a compatible player like Spotify running) ---
    elif os.name == 'posix':
        print("\n--- Testing on Linux (requires playerctl and Spotify/compatible player) ---")
        if shutil.which("playerctl"):
            print("playerctl found. Attempting to control Spotify (ensure it's running and supports MPRIS)...")
            # controller.play("Spotify", "spotify:track:4uLU6hMCjMI75M1A2tKUQC") # Example track URI
            controller.play("spotify") # Toggles play/pause or plays if URI given
            time.sleep(3)
            controller.pause("spotify")
            time.sleep(1)
            controller.skip_track("spotify")
            time.sleep(1)
            controller.play("spotify")
            time.sleep(3)
            controller.previous_track("spotify")
            time.sleep(3)
            controller.pause("spotify")
        else:
            print("playerctl not found. Skipping Linux media control tests.")

    # --- Windows Test (mostly informative as direct CLI is limited) ---
    elif os.name == 'nt':
        print("\n--- Testing on Windows (CLI control is limited) ---")
        print("Attempting to send 'play' to Spotify (likely won't work via generic CLI)...")
        controller.play("Spotify")
        print("This command on Windows is a placeholder and unlikely to have an effect without specific tools/APIs.")

    print("\nMedia controller tests finished.")
