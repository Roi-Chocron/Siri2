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
        self.logger.info("MediaController initialized. Relies on OS-specific tools: AppleScript (macOS), playerctl (Linux).")

        # Check for necessary tools during initialization (optional, or do it per command)
        if os.name == 'posix' and not hasattr(os, 'uname'): # Generic POSIX, likely Linux if not Darwin
            if not shutil.which("playerctl"):
                self.logger.warning("`playerctl` command-line tool not found. Media control on Linux will likely fail. Please install playerctl.")
        elif os.name == 'posix' and hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
            if not shutil.which("osascript"):
                 self.logger.warning("`osascript` command-line tool not found. Media control on macOS will likely fail (this is highly unusual).")


    def _get_active_player_macos(self) -> str | None:
        """Tries to determine the active (or most likely) media player on macOS."""
        # This is a heuristic. A more robust method might involve checking which app last had media focus.
        if self._is_player_running_macos("Spotify") and self._is_player_playing_macos("Spotify"):
            return "Spotify"
        if self._is_player_running_macos("Music") and self._is_player_playing_macos("Music"):
            return "Music"
        # Fallback if none are actively playing but one is running
        if self._is_player_running_macos("Spotify"):
            return "Spotify"
        if self._is_player_running_macos("Music"):
            return "Music"
        return None # Could also default to "Music" or "Spotify"

    def _is_player_playing_macos(self, app_name: str) -> bool:
        """Checks if a specific player is currently playing on macOS."""
        if not self._is_player_running_macos(app_name):
            return False
        try:
            # Spotify uses 'player state', Music uses 'player state' too
            script = f'tell application "{app_name}" to get player state as string'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True, timeout=2)
            return result.stdout.strip().lower() == "playing"
        except Exception as e:
            self.logger.debug(f"Could not determine playing state for {app_name} on macOS: {e}")
            return False

    def _execute_player_command(self, player_name: str, command: str, track_or_playlist: str = None) -> tuple[bool, str]:
        """
        Generic helper to send commands. This is highly dependent on CLI support of players.
        Returns (success, message)
        """
        player_lower = player_name.lower() if player_name else "default"
        self.logger.info(f"Attempting to execute '{command}' for player '{player_lower}'" + (f" with track/playlist '{track_or_playlist}'" if track_or_playlist else ""))

        # --- macOS Specific Examples using osascript ---
        if os.name == 'posix' and hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
            if not shutil.which("osascript"):
                msg = "`osascript` not found. Cannot control media on macOS."
                self.logger.error(msg)
                return False, msg

            target_player_app_name = None
            if player_lower == "spotify":
                target_player_app_name = "Spotify"
            elif player_lower in ["apple music", "music", "itunes"]: # iTunes is old name for Music
                target_player_app_name = "Music"
            elif player_lower == "default":
                target_player_app_name = self._get_active_player_macos()
                if not target_player_app_name:
                    # If no active player, try to launch Spotify by default or Music if Spotify isn't common for user.
                    # For now, let's assume user wants to control one if it's running, or default to Spotify.
                    target_player_app_name = "Spotify" # Could be configurable
                    self.logger.info(f"'Default' player on macOS, no active player identified, defaulting to control {target_player_app_name}.")
                else:
                    self.logger.info(f"'Default' player on macOS, identified active/running player as {target_player_app_name}.")
            else:
                msg = f"Player '{player_name}' is not explicitly supported on macOS. Supported: Spotify, Music, Default."
                self.logger.warning(msg)
                return False, msg

            if not self._is_player_running_macos(target_player_app_name) and command != "play":
                # Don't try to pause/skip if player isn't even running, unless it's a play command (which might launch it)
                msg = f"{target_player_app_name} is not running. Cannot execute '{command}'."
                self.logger.warning(msg)
                return False, msg

            script = ""
            if command == "play":
                if track_or_playlist:
                    if target_player_app_name == "Spotify":
                        if "spotify:" in track_or_playlist: # URI for track, album, playlist
                            script = f'tell application "Spotify" to play track "{track_or_playlist}"'
                        else: # Assume it's a song or playlist name
                            # Playing by name is complex, Spotify's AppleScript is better with URIs.
                            # This is a very simplified attempt, likely to fail for non-URI.
                            script = f'tell application "Spotify" to play track "{track_or_playlist}"'
                            self.logger.warning(f"Playing '{track_or_playlist}' by name on Spotify (macOS) is unreliable via AppleScript; URI preferred. Attempting anyway.")
                    elif target_player_app_name == "Music":
                        # Playing specific track/playlist by name in Music app is also non-trivial.
                        # Example: `play (first track of playlist "My Favs" whose name is "Cool Song")`
                        script = f'tell application "Music" to play playlist "{track_or_playlist}"' # Simplified to playlist
                        self.logger.info(f"Attempting to play playlist '{track_or_playlist}' in Music app on macOS. Playing specific tracks by name is more complex.")
                if not script: # General play, or play after attempting specific track
                    script = f'tell application "{target_player_app_name}" to play'
            elif command == "pause":
                script = f'tell application "{target_player_app_name}" to pause'
            elif command == "next":
                script = f'tell application "{target_player_app_name}" to next track'
            elif command == "previous":
                script = f'tell application "{target_player_app_name}" to previous track' # or 'back track' for Music for true previous

            if script:
                try:
                    subprocess.run(["osascript", "-e", script], check=True, timeout=5, capture_output=True)
                    msg = f"Executed '{command}' for {target_player_app_name} on macOS."
                    self.logger.info(msg)
                    return True, msg
                except subprocess.TimeoutExpired:
                    msg = f"Command '{command}' for {target_player_app_name} timed out on macOS."
                    self.logger.error(msg)
                    return False, msg
                except subprocess.CalledProcessError as e:
                    err_output = e.stderr.strip() if e.stderr else "No stderr output."
                    msg = f"Error executing AppleScript for {target_player_app_name} (command: {command}). Error: {e}. Details: {err_output}"
                    if "Application isn't running" in err_output:
                         msg = f"{target_player_app_name} is not running or not responding."
                         self.logger.warning(msg)
                    else:
                        self.logger.error(msg)
                    return False, msg
                except Exception as e: # Catch-all for other unexpected errors
                    msg = f"Unexpected error with AppleScript for {target_player_app_name}: {e}"
                    self.logger.error(msg)
                    return False, msg
            else:
                msg = f"Command '{command}' not mapped to an AppleScript action for {target_player_app_name}."
                self.logger.warning(msg)
                return False, msg

        # --- Linux Specific Examples using playerctl ---
        elif os.name == 'posix': # Generic Linux (already checked for osascript for macOS)
            if not shutil.which("playerctl"):
                msg = "`playerctl` not found. Please install it to control media players on Linux (e.g., `sudo apt install playerctl`)."
                self.logger.error(msg) # Changed to error as it's a hard requirement for Linux
                return False, msg

            playerctl_target_args = []
            if player_lower != "default":
                # playerctl can list players with `playerctl -l`. We could check if player_lower is valid.
                # For now, assume user provides a valid player name if not "default".
                playerctl_target_args = ["--player", player_lower] # e.g. playerctl --player spotify status

            # Check if any player or the specified player is available/running
            try:
                status_cmd = ["playerctl"] + playerctl_target_args + ["status"]
                status_process = subprocess.run(status_cmd, capture_output=True, text=True, check=True, timeout=2)
                player_status = status_process.stdout.strip().lower()
                self.logger.info(f"Playerctl status for '{player_lower}': {player_status}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                # This often means no player is running or the specified one isn't available via MPRIS
                # 'No players found' or 'Failed to connect to player' are common errors from playerctl
                err_msg = e.stderr.strip() if isinstance(e, subprocess.CalledProcessError) and e.stderr else str(e)
                if "no players found" in err_msg.lower() or "failed to connect" in err_msg.lower():
                    msg = f"No active media player found or '{player_lower}' is not available via playerctl. Cannot execute '{command}'."
                    self.logger.warning(msg)
                else:
                    msg = f"Could not get status for '{player_lower}' via playerctl. Error: {err_msg}. Cannot execute '{command}'."
                    self.logger.warning(msg)
                return False, msg # Can't proceed if player isn't controllable


            base_cmd = ["playerctl"] + playerctl_target_args
            action_cmd_str = ""

            if command == "play":
                if track_or_playlist: # playerctl can open URIs or search terms (depending on player)
                     try:
                        # playerctl open URI ; playerctl play
                        # Some players might need specific handling for search terms vs URIs.
                        # Assuming track_or_playlist is a URI for simplicity here.
                        subprocess.run(base_cmd + ["open", track_or_playlist], check=True, timeout=5, capture_output=True)
                        subprocess.run(base_cmd + ["play"], check=True, timeout=5, capture_output=True) # Ensure it plays after opening
                        msg = f"Attempted to open and play '{track_or_playlist}' with '{player_lower}' via playerctl."
                        self.logger.info(msg)
                        return True, msg
                     except subprocess.CalledProcessError as e:
                        err_output = e.stderr.strip() if e.stderr else "No stderr output."
                        msg = f"Error opening/playing '{track_or_playlist}' with playerctl for '{player_lower}'. Error: {e}. Details: {err_output}"
                        self.logger.error(msg)
                        return False, msg
                     except subprocess.TimeoutExpired:
                        msg = f"Timeout opening/playing '{track_or_playlist}' with playerctl for '{player_lower}'."
                        self.logger.error(msg)
                        return False, msg
                else:
                    action_cmd_str = "play" # Explicit play
            elif command == "pause":
                action_cmd_str = "pause"
            elif command == "next":
                action_cmd_str = "next"
            elif command == "previous":
                action_cmd_str = "previous"

            if action_cmd_str:
                try:
                    subprocess.run(base_cmd + [action_cmd_str], check=True, timeout=5, capture_output=True)
                    msg = f"Executed '{action_cmd_str}' for '{player_lower}' via playerctl on Linux."
                    self.logger.info(msg)
                    return True, msg
                except subprocess.TimeoutExpired:
                    msg = f"Command '{action_cmd_str}' for '{player_lower}' timed out with playerctl."
                    self.logger.error(msg)
                    return False, msg
                except subprocess.CalledProcessError as e:
                    err_output = e.stderr.strip() if e.stderr else "No stderr output."
                    msg = f"Error using playerctl for '{player_lower}' (command: {action_cmd_str}). Error: {e}. Details: {err_output}"
                    self.logger.error(msg)
                    return False, msg
                except Exception as e: # Catch-all
                    msg = f"Unexpected error with playerctl for '{player_lower}': {e}"
                    self.logger.error(msg)
                    return False, msg

            else: # If command was 'play' with track_or_playlist, it's handled above.
                  # This 'else' implies command was not mapped if it wasn't play with track.
                if not (command == "play" and track_or_playlist):
                    msg = f"Command '{command}' not directly mapped for playerctl in this scenario."
                    self.logger.warning(msg)
                    return False, msg
                # If it was play with track_or_playlist, success/failure already returned.
                # This path shouldn't be hit if play with track_or_playlist was processed.
                return True, "Play with track/playlist processed."


        # --- Windows Specific (Placeholder) ---
        elif os.name == 'nt':
            # Windows media control is complex without dedicated APIs or third-party tools.
            # Common methods involve simulating media keys, which is beyond simple subprocess.
            # For specific apps like Spotify, their Web API is the most reliable.
            msg = (f"Direct CLI control for '{player_name}' on Windows is not reliably supported by this module. "
                   "Consider using specific player APIs (e.g., Spotify Web API) or tools that simulate media key presses.")
            self.logger.warning(msg)
            return False, msg

        # Fallback if OS not matched or other issue
        msg = f"Media control for OS '{os.name}' and player '{player_name}' is not supported or failed."
        self.logger.error(msg) # Changed to error as it's a failure point
        return False, msg

    def _is_player_running_macos(self, app_name: str) -> bool:
        """Checks if a player application is running on macOS."""
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
