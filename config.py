"""Configuration and UI classes."""

import os
import sys
import tempfile
import time
import curses
import threading
import subprocess
import unicodedata
from datetime import datetime


# Configuration constants
CLAUDE_CACHE = os.path.join(tempfile.gettempdir(), "claude_api_key_cache.json")
OVPN_CACHE = os.path.expanduser("~/.config/vpn_config_path.json")
ZLIB_AUTH_CACHE = os.path.expanduser("~/.config/zlib_auth.json")
CACHE_DAYS = 2
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-7-sonnet-latest"
BASE_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "children_books")

# These will be set dynamically based on language in run_download_process()
DOWNLOAD_DIR = None
URL_LOG_FILE = None
SEARCH_LOG_FILE = None
SEARCH_ROUND = 1  # Track which search round we're on
FAILED_CONVERSIONS = set()  # Track titles that failed text extraction in current session


def display_width(text):
    """Calculate the display width of text, accounting for Unicode characters"""
    width = 0
    for char in text:
        # Skip variation selectors and other combining/modifier characters
        category = unicodedata.category(char)
        if category in ('Mn', 'Mc', 'Me'):  # Combining marks don't add width
            continue
        if 0xFE00 <= ord(char) <= 0xFE0F:  # Variation selectors
            continue
        if 0xE0100 <= ord(char) <= 0xE01EF:  # Variation selectors supplement
            continue
            
        # East Asian characters are typically full-width (2 columns)
        eaw = unicodedata.east_asian_width(char)
        if eaw in ('F', 'W'):  # Fullwidth or Wide
            width += 2
        elif eaw == 'H':  # Halfwidth
            width += 1
        elif category[0] == 'C':  # Control characters
            width += 0
        else:  # Neutral, Ambiguous, or Narrow
            width += 1
    return width


class NCursesUI:
    def __init__(self):
        self.stdscr = None
        self.height = 0
        self.width = 0
        self.log_lines = []
        self.status = "Ready"
        self.search_logging = False
        self.search_log_file = None
        self.current_progress_title = None  # Track current progress bar title
        self.is_showing_progress = False    # Track if we're currently showing a progress bar
        self.separator_position = None     # Fixed position for the column separator
        self.scroll_offset = 0             # For scrolling through logs
        self.scrollbar_dragging = False    # Track if user is dragging scrollbar
        self.last_refresh_time = 0         # For debouncing refreshes
        self.refresh_interval = 0.1        # Minimum time between refreshes (100ms)
        self.pending_refresh = False       # Track if a refresh is pending
        self.last_drawn_scroll_offset = -1 # Track last drawn scroll position
        self.last_drawn_log_count = 0      # Track last drawn log count
        self.last_visible_lines = []       # Cache of last drawn lines
        self.scroll_accumulator = 0        # Accumulate scroll changes during debounce
        self.last_progress_time = 0        # For throttling progress updates

    def init_colors(self):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Header
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Success
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # Error
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Warning
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Info
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Input field
        curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK) # Light blue for completed words
        curses.init_pair(8, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Yellow for current word being typed

    def setup_screen(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)  # Enable special keys (arrow keys, function keys, etc.)
        stdscr.leaveok(True)  # Prevent cursor artifacts
        
        # Enable mouse support
        try:
            curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        except:
            pass  # Mouse support might not be available in all terminals
            
        self.init_colors()
        stdscr.clear()
        # Calculate fixed separator position based on terminal width
        self._calculate_separator_position()

    def draw_header(self):
        title = "📚 Children's Book Downloader"
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, (self.width - len(title)) // 2, title)
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    def draw_status(self):
        # Add scroll position info
        visible_lines = self.height - 6
        total_lines = len(self.log_lines)
        if total_lines > visible_lines:
            scroll_info = f" | Scroll: {self.scroll_offset}/{max(0, total_lines - visible_lines)}"
        else:
            scroll_info = ""
        
        status_line = f"Status: {self.status}{scroll_info}"
        self.stdscr.addstr(self.height - 1, 0, status_line[:self.width-1])

    def draw_log_window(self, start_row=3, height=None):
        if height is None:
            height = self.height - 5

        # Only clear lines that will actually change
        scroll_changed = self.scroll_offset != self.last_drawn_scroll_offset
        
        # Draw border only if this is a full redraw (height changed or first draw)
        current_log_count = len(self.log_lines)
        border_redraw_needed = (self.last_drawn_scroll_offset == -1 or 
                               self.scroll_offset != self.last_drawn_scroll_offset or 
                               current_log_count != self.last_drawn_log_count)
        
        if border_redraw_needed:
            for i in range(height):
                self.stdscr.addstr(start_row + i, 0, "│")
                self.stdscr.addstr(start_row + i, self.width - 1, "│")

            self.stdscr.addstr(start_row - 1, 0, "┌" + "─" * (self.width - 2) + "┐")
            self.stdscr.addstr(start_row + height, 0, "└" + "─" * (self.width - 2) + "┘")

        # Show log lines with scrolling support
        visible_lines = height - 1
        total_lines = len(self.log_lines)
        
        if total_lines <= visible_lines:
            # All lines fit, no scrolling needed
            recent_logs = self.log_lines
            self.scroll_offset = 0
        else:
            # Handle scrolling
            max_scroll = total_lines - visible_lines
            self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))
            
            start_index = total_lines - visible_lines - self.scroll_offset
            end_index = start_index + visible_lines
            recent_logs = self.log_lines[start_index:end_index]

        # Clear and update only lines that changed
        for i, line in enumerate(recent_logs):
            if start_row + i + 1 < start_row + height:
                # Check if this line needs updating
                line_changed = (scroll_changed or 
                               i >= len(self.last_visible_lines) or 
                               line != self.last_visible_lines[i] if i < len(self.last_visible_lines) else True)
                
                if line_changed:
                    # Clear this specific line
                    try:
                        self.stdscr.addstr(start_row + i + 1, 1, " " * (self.width - 4))
                    except curses.error:
                        pass
                # Check for progress bar color markers
                is_progress_success = "✅PROGRESS_SUCCESS" in line
                is_progress_failure = "❌PROGRESS_FAILURE" in line
                
                if is_progress_success or is_progress_failure:
                    # Handle colored progress bars - split the line and color parts separately
                    if " │ " in line:
                        title_part, status_part = line.split(" │ ", 1)
                        
                        # Remove the color markers from display
                        if is_progress_success:
                            status_part = status_part.replace(" ✅PROGRESS_SUCCESS", "")
                        elif is_progress_failure:
                            status_part = status_part.replace(" ❌PROGRESS_FAILURE", "")
                        
                        # Draw title part in normal color (leave space for scrollbar)
                        max_content_width = self.width - 4  # Reserve space for borders and scrollbar
                        self.stdscr.addstr(start_row + i + 1, 1, title_part[:max_content_width])
                        
                        # Draw separator in normal color
                        separator_pos = 1 + len(title_part)
                        if separator_pos < max_content_width:
                            self.stdscr.addstr(start_row + i + 1, separator_pos, " │ ")
                        
                        # Draw progress bar in colored background
                        progress_color = curses.color_pair(2) if is_progress_success else curses.color_pair(3)
                        self.stdscr.attron(progress_color)
                        progress_pos = separator_pos + 3
                        if progress_pos < max_content_width:
                            max_progress_len = max_content_width - progress_pos
                            self.stdscr.addstr(start_row + i + 1, progress_pos, status_part[:max_progress_len])
                        self.stdscr.attroff(progress_color)
                    else:
                        # Fallback for lines without separator
                        color = curses.color_pair(2) if is_progress_success else curses.color_pair(3)
                        self.stdscr.attron(color)
                        max_content_width = self.width - 4  # Reserve space for borders and scrollbar
                        display_line = line[:max_content_width]
                        if is_progress_success:
                            display_line = display_line.replace(" ✅PROGRESS_SUCCESS", "")
                        elif is_progress_failure:
                            display_line = display_line.replace(" ❌PROGRESS_FAILURE", "")
                        self.stdscr.addstr(start_row + i + 1, 1, display_line)
                        self.stdscr.attroff(color)
                else:
                    # Handle regular lines with existing color logic
                    color = curses.color_pair(0)
                    if line.startswith("✅") or "Found PDF" in line:
                        color = curses.color_pair(2)
                    elif line.startswith("❌") or line.startswith("⚠️") or "No PDF found" in line:
                        color = curses.color_pair(3)
                    elif line.startswith("🔍") or line.startswith("🔎"):
                        color = curses.color_pair(5)

                    self.stdscr.attron(color)
                    max_content_width = self.width - 4  # Reserve space for borders and scrollbar
                    display_line = line[:max_content_width]
                    self.stdscr.addstr(start_row + i + 1, 1, display_line)
                    self.stdscr.attroff(color)

        # Clear any remaining lines if new content is shorter
        if len(self.last_visible_lines) > len(recent_logs):
            for i in range(len(recent_logs), len(self.last_visible_lines)):
                if start_row + i + 1 < start_row + height:
                    try:
                        self.stdscr.addstr(start_row + i + 1, 1, " " * (self.width - 4))
                    except curses.error:
                        pass

        # Draw scrollbar if needed
        if total_lines > visible_lines:
            self.draw_scrollbar(start_row, height, visible_lines, total_lines)
        
        # Update tracking state for next time
        self.last_drawn_scroll_offset = self.scroll_offset
        self.last_drawn_log_count = current_log_count
        self.last_visible_lines = recent_logs.copy() if 'recent_logs' in locals() else []

    def draw_scrollbar(self, start_row, height, visible_lines, total_lines):
        """Draw a visual scrollbar on the right side of the log window"""
        scrollbar_col = self.width - 2  # Position just inside the right border
        scrollbar_height = height - 1  # Height of scrollable area
        
        if scrollbar_height < 3:  # Not enough space for meaningful scrollbar
            return
            
        # Calculate scrollbar thumb position and size
        # Thumb size represents what portion of content is visible
        thumb_size = max(1, int(scrollbar_height * visible_lines / total_lines))
        
        # Current scroll position as a ratio (0.0 = at bottom, 1.0 = at top)
        if total_lines <= visible_lines:
            scroll_ratio = 0.0
        else:
            scroll_ratio = self.scroll_offset / (total_lines - visible_lines)
        
        # Position of thumb (0 = top, scrollbar_height - thumb_size = bottom)
        # Note: we invert because scroll_offset=0 means showing newest (bottom)
        thumb_pos = int((scrollbar_height - thumb_size) * (1.0 - scroll_ratio))
        
        # Draw scrollbar track
        for i in range(scrollbar_height):
            try:
                if i >= thumb_pos and i < thumb_pos + thumb_size:
                    # Draw thumb (solid block with different color)
                    self.stdscr.attron(curses.color_pair(6))  # Use input field color (black on white)
                    self.stdscr.addstr(start_row + i + 1, scrollbar_col, "█")
                    self.stdscr.attroff(curses.color_pair(6))
                else:
                    # Draw track (lighter character)
                    self.stdscr.addstr(start_row + i + 1, scrollbar_col, "░")
            except curses.error:
                # Ignore if we can't draw at this position
                pass

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format message with fixed column layout
        formatted_message = self._format_with_columns(f"[{timestamp}] {message}")
        
        # Don't clear progress state when adding regular log messages
        # This allows progress bars to remain visible after completion
        
        self.log_lines.append(formatted_message)
        if len(self.log_lines) > 1000:  # Keep log manageable
            self.log_lines = self.log_lines[-500:]
        
        # Also write to search log file if search logging is enabled (original message)
        if self.search_logging and self.search_log_file:
            try:
                # Write original full message to file
                original_formatted = f"[{timestamp}] {message}"
                with open(self.search_log_file, "a", encoding="utf-8") as f:
                    f.write(original_formatted + "\n")
            except Exception as e:
                pass  # Don't fail if logging fails
        
        self.refresh_display()
    
    def log_to_file_only(self, message):
        """Log message only to file, not to ncurses display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Only write to search log file if search logging is enabled
        if self.search_logging and self.search_log_file:
            try:
                with open(self.search_log_file, "a", encoding="utf-8") as f:
                    f.write(formatted_message + "\n")
            except Exception as e:
                pass  # Don't fail if logging fails

    def set_status(self, status):
        self.status = status
        self.refresh_display()
    
    def show_progress(self, current, total, title="", description="Checking URLs"):
        """Display a progress bar with fixed two-column layout"""
        if total == 0:
            return
        
        # Throttle progress updates to reduce lag - only update every 20ms max
        current_time = time.time()
        if current_time - self.last_progress_time < 0.02 and current != total:
            return  # Skip this update unless it's the final one
        self.last_progress_time = current_time
        
        # Ensure separator position is calculated
        if self.separator_position is None:
            self._calculate_separator_position()
        
        progress = current / total
        percentage = int(progress * 100)
        
        # Calculate available space for progress info (right of separator)
        available_status_width = self.width - self.separator_position - 2  # 2 for " │"
        
        # Format counter and percentage
        counter_text = f"{current}/{total}"
        percentage_text = f"({percentage}%)"
        
        # Calculate space for progress bar (reserve space for counter, percentage, brackets, spaces)
        static_text = f"[] {counter_text} {percentage_text}"
        bar_width = max(8, available_status_width - len(static_text))
        
        # Create the progress bar
        filled_width = int(bar_width * progress)
        
        # Special handling for 0% - show a different character to make it more visible
        if current == 0:
            bar = "▒" * bar_width  # Use medium shade for 0% to make it more distinct
        else:
            bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Format complete progress info
        progress_info = f"[{bar}] {counter_text} {percentage_text}"
        
        # Use title or description for the message
        display_title = title if title else description
        
        # Add timestamp and progress icon to match format of regular log messages
        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamped_title = f"[{timestamp}] 🔄 {display_title}"
        
        # Format with consistent column layout
        progress_line = self._format_with_columns(timestamped_title, progress_info)
        
        # Check if we're continuing progress for the same title
        if (self.is_showing_progress and 
            self.current_progress_title == title and 
            self.log_lines):
            # Update the existing progress bar line for the same title
            self.log_lines[-1] = progress_line
        else:
            # Starting progress for a new title or first progress
            self.log_lines.append(progress_line)
            self.current_progress_title = title
            self.is_showing_progress = True
        
        self.debounced_refresh()
    
    def _calculate_separator_position(self):
        """Calculate the fixed separator position based on terminal width"""
        if self.width <= 20:
            self.separator_position = self.width - 5  # Very narrow terminal
        else:
            # Position separator to leave reasonable space for progress bars
            # Aim for about 2/3 of the width, but ensure minimum space for status
            self.separator_position = min(self.width - 30, max(self.width * 2 // 3, 40))
    
    def _format_with_columns(self, message, status_column=""):
        """Format message with consistent column layout using fixed separator position"""
        if self.width <= 10:  # Safety check for very small terminals
            return message[:self.width-1] if len(message) >= self.width else message
        
        # Ensure separator position is calculated
        if self.separator_position is None:
            self._calculate_separator_position()
        
        # Title width is always separator_position - 1 (for the space before separator)
        title_width = self.separator_position - 1
        
        # Truncate message to fit in title column based on display width
        if display_width(message) > title_width:
            # Reserve space for ellipsis (3 chars: "...")
            max_text_width = title_width - 3
            if max_text_width > 0:
                # Truncate character by character until it fits
                truncated = ""
                for char in message:
                    if display_width(truncated + char) > max_text_width:
                        break
                    truncated += char
                message = truncated + "..."
            else:
                # If no space for text + ellipsis, just truncate without ellipsis
                truncated = ""
                for char in message:
                    if display_width(truncated + char) > title_width:
                        break
                    truncated += char
                message = truncated
        
        # Pad message to exactly reach separator position based on display width
        current_width = display_width(message)
        padding_needed = title_width - current_width
        title_column = message + " " * padding_needed
        
        # Build the formatted line
        if status_column:
            # Calculate available space for status column
            available_status_width = self.width - self.separator_position - 2  # 2 for " │"
            
            # Truncate status column if it's too long based on display width
            if display_width(status_column) > available_status_width:
                # Reserve space for ellipsis (3 chars: "...")
                max_status_width = available_status_width - 3
                if max_status_width > 0:
                    # Truncate character by character until it fits
                    truncated = ""
                    for char in status_column:
                        if display_width(truncated + char) > max_status_width:
                            break
                        truncated += char
                    status_column = truncated + "..."
                else:
                    # If no space for text + ellipsis, just truncate without ellipsis
                    truncated = ""
                    for char in status_column:
                        if display_width(truncated + char) > available_status_width:
                            break
                        truncated += char
                    status_column = truncated
            
            # Pad status column to fill remaining space to right edge based on display width
            current_status_width = display_width(status_column)
            status_padding_needed = available_status_width - current_status_width
            status_column = status_column + " " * status_padding_needed
            formatted_line = f"{title_column} │ {status_column}"
        else:
            # Regular message - ensure separator appears at same position as two-column format
            # title_column is already padded to separator_position - 1
            remaining_space = self.width - self.separator_position - 3  # 3 for " │ "
            formatted_line = f"{title_column} │ {' ' * remaining_space}"
        
        # Ensure line doesn't exceed terminal width based on display width
        if display_width(formatted_line) > self.width:
            # Truncate character by character until it fits
            truncated = ""
            for char in formatted_line:
                if display_width(truncated + char) > self.width:
                    break
                truncated += char
            formatted_line = truncated
        
        return formatted_line
    
    def finish_progress(self, final_message):
        """Complete progress bar and show final result message with full progress bar"""
        if self.is_showing_progress and self.log_lines:
            # Extract the title from the current progress line to show completed progress
            current_line = self.log_lines[-1]
            
            # Try to extract the title portion before the separator
            if " │ " in current_line:
                title_part = current_line.split(" │ ")[0]
                # Remove timestamp if present
                if "] " in title_part:
                    title_part = title_part.split("] ", 1)[1] if "] " in title_part else title_part
            else:
                title_part = final_message
            
            # Determine if this is success or failure based on the message
            is_success = "Found PDF" in final_message or "📄" in final_message
            is_failure = "No PDF found" in final_message or "❌" in final_message
            
            # Calculate available space for progress info (right of separator)
            available_status_width = self.width - self.separator_position - 2  # 2 for " │"
            
            # Create a completed progress bar (100%)
            counter_text = "COMPLETE"
            static_text = f"[] {counter_text}"
            bar_width = max(8, available_status_width - len(static_text))
            
            # Full progress bar with color markers
            bar = "█" * bar_width
            if is_success:
                # Add success marker for green coloring
                progress_info = f"[{bar}] {counter_text} ✅PROGRESS_SUCCESS"
            elif is_failure:
                # Add failure marker for red coloring
                progress_info = f"[{bar}] {counter_text} ❌PROGRESS_FAILURE"
            else:
                # Default (no special coloring)
                progress_info = f"[{bar}] {counter_text}"
            
            # Add timestamp to match format of regular log messages
            timestamp = datetime.now().strftime("%H:%M:%S")
            timestamped_final_message = f"[{timestamp}] {final_message}"
            
            # Format with consistent column layout showing completed progress
            completed_line = self._format_with_columns(timestamped_final_message, progress_info)
            
            # Replace the progress bar with the completed version
            self.log_lines[-1] = completed_line
        else:
            # Add as new line if no progress was showing
            # Add timestamp to match format of regular log messages
            timestamp = datetime.now().strftime("%H:%M:%S")
            timestamped_final_message = f"[{timestamp}] {final_message}"
            formatted_message = self._format_with_columns(timestamped_final_message)
            self.log_lines.append(formatted_message)
        
        # Clear progress state - ready for next title
        self.current_progress_title = None
        self.is_showing_progress = False
        self.debounced_refresh()

    def refresh_display(self):
        if self.stdscr:
            # Check if terminal size changed and recalculate separator position
            new_height, new_width = self.stdscr.getmaxyx()
            if new_width != self.width:
                self.width = new_width
                self.height = new_height
                self._calculate_separator_position()
            
            self.draw_header()
            self.draw_log_window()
            self.draw_status()
            self.stdscr.refresh()
    
    def debounced_refresh(self):
        """Debounced refresh to prevent flickering during rapid scroll events"""
        current_time = time.time()
        if current_time - self.last_refresh_time >= self.refresh_interval:
            self.last_refresh_time = current_time
            self.pending_refresh = False
            if self.stdscr:
                self.draw_log_window()
                self.draw_status()
                self.stdscr.refresh()
        else:
            self.pending_refresh = True
    
    def process_pending_refresh(self):
        """Process any pending refresh requests"""
        if self.pending_refresh:
            current_time = time.time()
            if current_time - self.last_refresh_time >= self.refresh_interval:
                self.last_refresh_time = current_time
                self.pending_refresh = False
                if self.stdscr:
                    self.draw_log_window()
                    self.draw_status()
                    self.stdscr.refresh()
    
    def handle_scroll_keys(self):
        """Handle keyboard input for scrolling. Returns True if a scroll key was pressed."""
        if not self.stdscr:
            return False
        
        self.stdscr.timeout(0)  # Non-blocking input with no timeout for immediate response
        key = self.stdscr.getch()
        
        if key == curses.KEY_UP:
            # Scroll up (show older messages)
            visible_lines = self.height - 6
            max_scroll = max(0, len(self.log_lines) - visible_lines)
            if self.scroll_offset < max_scroll:
                self.scroll_offset += 1
                self.debounced_refresh()
            return True
        elif key == curses.KEY_DOWN:
            # Scroll down (show newer messages)
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
                self.debounced_refresh()
            return True
        elif key == curses.KEY_HOME:
            # Go to top
            visible_lines = self.height - 6  # Approximate visible lines
            self.scroll_offset = max(0, len(self.log_lines) - visible_lines)
            self.debounced_refresh()
            return True
        elif key == curses.KEY_END:
            # Go to bottom
            self.scroll_offset = 0
            self.debounced_refresh()
            return True
        elif key == ord('j'):
            # Scroll down (show newer messages) - vim style
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
                self.debounced_refresh()
            return True
        elif key == ord('k'):
            # Scroll up (show older messages) - vim style
            visible_lines = self.height - 6
            max_scroll = max(0, len(self.log_lines) - visible_lines)
            if self.scroll_offset < max_scroll:
                self.scroll_offset += 1
                self.debounced_refresh()
            return True
        elif key == curses.KEY_MOUSE:
            # Handle mouse events for scrollbar
            try:
                _, mouse_x, mouse_y, _, button_state = curses.getmouse()
                if self.handle_scrollbar_click(mouse_x, mouse_y, button_state):
                    return True
            except curses.error:
                pass  # Ignore mouse errors
        
        return False

    def handle_scrollbar_click(self, mouse_x, mouse_y, button_state):
        """Handle mouse clicks on the scrollbar and scroll wheel in log area"""
        scrollbar_col = self.width - 2
        log_start_row = 3
        log_height = self.height - 5
        scrollbar_height = log_height - 1
        
        visible_lines = self.height - 6
        total_lines = len(self.log_lines)
        
        # Handle scroll wheel events anywhere in the log area
        if mouse_y >= log_start_row and mouse_y < log_start_row + log_height:
            if button_state & curses.BUTTON4_PRESSED:  # Scroll up
                max_scroll = max(0, total_lines - visible_lines)
                if self.scroll_offset < max_scroll:
                    self.scroll_offset += 1
                    self.debounced_refresh()
                return True
            elif button_state & curses.BUTTON5_PRESSED:  # Scroll down
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
                    self.debounced_refresh()
                return True
        
        # Check if click is specifically on the scrollbar column for clicking
        if mouse_x != scrollbar_col:
            return False
            
        # Check if click is within scrollbar area
        if mouse_y < log_start_row + 1 or mouse_y >= log_start_row + scrollbar_height + 1:
            return False
        
        # Handle mouse button events for scrollbar clicking and dragging
        if button_state & curses.BUTTON1_PRESSED:  # Mouse down - start dragging
            self.scrollbar_dragging = True
        elif button_state & curses.BUTTON1_RELEASED:  # Mouse up - stop dragging
            self.scrollbar_dragging = False
        elif button_state & curses.REPORT_MOUSE_POSITION and self.scrollbar_dragging:
            # Mouse drag - update scroll position
            pass  # Will be handled below
        elif button_state & curses.BUTTON1_CLICKED:
            # Single click
            pass  # Will be handled below
        else:
            return False
            
        # Calculate clicked position within scrollbar
        click_pos = mouse_y - (log_start_row + 1)  # Position within scrollbar (0 to scrollbar_height-1)
        
        # Convert click position to scroll offset
        if total_lines <= visible_lines:
            # No scrolling needed
            return True
            
        max_scroll = max(0, total_lines - visible_lines)
        
        # Calculate scroll ratio (0.0 = top of scrollbar = max scroll, 1.0 = bottom = 0 scroll)
        scroll_ratio = click_pos / (scrollbar_height - 1) if scrollbar_height > 1 else 0
        
        # Invert ratio because scroll_offset=0 means newest (bottom)
        new_scroll_offset = int(max_scroll * (1.0 - scroll_ratio))
        new_scroll_offset = max(0, min(new_scroll_offset, max_scroll))
        
        if new_scroll_offset != self.scroll_offset:
            self.scroll_offset = new_scroll_offset
            self.debounced_refresh()
            
        return True

    def get_input(self, prompt, password=False, default=""):
        # Create input window
        input_height = 7
        input_width = min(60, self.width - 4)
        start_y = (self.height - input_height) // 2
        start_x = (self.width - input_width) // 2

        input_win = curses.newwin(input_height, input_width, start_y, start_x)
        input_win.keypad(True)  # Enable arrow keys for input navigation
        input_win.nodelay(False)  # Ensure blocking mode for proper input
        input_win.box()
        input_win.attron(curses.color_pair(1) | curses.A_BOLD)
        input_win.addstr(1, 2, "Input Required")
        input_win.attroff(curses.color_pair(1) | curses.A_BOLD)

        # Wrap prompt text
        prompt_lines = []
        words = prompt.split()
        current_line = ""
        max_width = input_width - 4

        for word in words:
            if len(current_line + " " + word) <= max_width:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    prompt_lines.append(current_line)
                current_line = word
        if current_line:
            prompt_lines.append(current_line)

        for i, line in enumerate(prompt_lines[:2]):  # Show max 2 lines
            input_win.addstr(2 + i, 2, line)

        # Input field
        field_y = 4
        input_win.attron(curses.color_pair(6))
        input_win.addstr(field_y, 2, " " * (input_width - 4))
        input_win.attroff(curses.color_pair(6))

        input_win.addstr(input_height - 2, 2, "Press Enter to confirm, Ctrl+V to paste")
        input_win.refresh()

        # Get input
        curses.curs_set(1)  # Show cursor
        input_str = default
        cursor_pos = len(input_str)
        last_display = ""  # Track last displayed string to reduce refreshes

        def refresh_input():
            nonlocal last_display
            # Only refresh if the display has actually changed
            display_str = ("*" * len(input_str)) if password else input_str
            truncated_display = display_str[:input_width-4]
            
            if truncated_display != last_display:
                input_win.attron(curses.color_pair(6))
                input_win.addstr(field_y, 2, (" " * (input_width - 4)))
                input_win.addstr(field_y, 2, truncated_display)
                input_win.attroff(curses.color_pair(6))
                last_display = truncated_display
            
            input_win.move(field_y, 2 + min(cursor_pos, input_width - 5))
            input_win.refresh()

        # Initial display
        refresh_input()

        while True:
            try:
                # Process any pending refresh requests
                self.process_pending_refresh()
                key = input_win.getch()

                if key == 10 or key == 13:  # Enter
                    break
                elif key == 27:  # Escape
                    input_str = ""
                    break
                elif key == 22:  # Ctrl+V (paste)
                    try:
                        # Try to get clipboard content
                        import subprocess
                        if hasattr(subprocess, 'run'):
                            # Try xclip first (Linux)
                            try:
                                result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], 
                                                      capture_output=True, text=True, timeout=1)
                                if result.returncode == 0:
                                    clipboard_text = result.stdout
                                    # Insert clipboard text at cursor position
                                    input_str = input_str[:cursor_pos] + clipboard_text + input_str[cursor_pos:]
                                    cursor_pos += len(clipboard_text)
                                    refresh_input()
                                    continue
                            except (subprocess.TimeoutExpired, FileNotFoundError):
                                pass
                            
                            # Try xsel as fallback (Linux)
                            try:
                                result = subprocess.run(['xsel', '--clipboard', '--output'], 
                                                      capture_output=True, text=True, timeout=1)
                                if result.returncode == 0:
                                    clipboard_text = result.stdout
                                    input_str = input_str[:cursor_pos] + clipboard_text + input_str[cursor_pos:]
                                    cursor_pos += len(clipboard_text)
                                    refresh_input()
                                    continue
                            except (subprocess.TimeoutExpired, FileNotFoundError):
                                pass
                    except Exception:
                        pass  # Ignore paste errors and continue
                elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                    if cursor_pos > 0:
                        input_str = input_str[:cursor_pos-1] + input_str[cursor_pos:]
                        cursor_pos -= 1
                        refresh_input()
                elif key == curses.KEY_LEFT:
                    cursor_pos = max(0, cursor_pos - 1)
                    refresh_input()
                elif key == curses.KEY_RIGHT:
                    cursor_pos = min(len(input_str), cursor_pos + 1)
                    refresh_input()
                elif key == curses.KEY_HOME or key == 1:  # Ctrl+A
                    cursor_pos = 0
                    refresh_input()
                elif key == curses.KEY_END or key == 5:  # Ctrl+E
                    cursor_pos = len(input_str)
                    refresh_input()
                elif key == 21:  # Ctrl+U (clear line)
                    input_str = ""
                    cursor_pos = 0
                    refresh_input()
                elif 32 <= key <= 126:  # Printable characters
                    input_str = input_str[:cursor_pos] + chr(key) + input_str[cursor_pos:]
                    cursor_pos += 1
                    refresh_input()

            except KeyboardInterrupt:
                input_str = ""
                break

        curses.curs_set(0)  # Hide cursor
        del input_win
        self.refresh_display()
        return input_str.strip()

    def show_menu(self, title, options):
        # Calculate optimal menu dimensions with scrolling support
        max_visible_options = min(len(options), self.height - 8)  # Reserve space for title, borders, and instructions
        menu_height = max_visible_options + 6  # Title + borders + instructions
        menu_width = max(len(title), max(len(opt) for opt in options)) + 8
        start_y = (self.height - menu_height) // 2
        start_x = (self.width - menu_width) // 2

        menu_win = curses.newwin(menu_height, menu_width, start_y, start_x)
        menu_win.keypad(True)  # Enable arrow keys for this window

        current = 0
        scroll_offset = 0
        last_scroll_offset = -1
        
        def draw_menu():
            """Draw the complete menu"""
            menu_win.clear()
            menu_win.box()

            menu_win.attron(curses.color_pair(1) | curses.A_BOLD)
            menu_win.addstr(1, (menu_width - len(title)) // 2, title)
            menu_win.attroff(curses.color_pair(1) | curses.A_BOLD)
            
            # Display visible options
            for i in range(max_visible_options):
                option_index = scroll_offset + i
                if option_index >= len(options):
                    break
                    
                y = 3 + i
                option = options[option_index]
                
                if option_index == current:
                    menu_win.attron(curses.color_pair(6))
                    menu_win.addstr(y, 2, f"> {option}")
                    menu_win.attroff(curses.color_pair(6))
                else:
                    menu_win.addstr(y, 2, f"  {option}")

            # Show scroll indicators if needed
            instructions = "↑↓: Navigate, j/k/wheel/click: Scroll logs, Enter: Select"
            if len(options) > max_visible_options:
                scroll_info = f" ({current + 1}/{len(options)})"
                instructions += scroll_info
                
                # Show scroll arrows
                if scroll_offset > 0:
                    menu_win.addstr(2, menu_width - 3, "↑")
                if scroll_offset + max_visible_options < len(options):
                    menu_win.addstr(menu_height - 3, menu_width - 3, "↓")

            menu_win.addstr(menu_height - 2, 2, instructions[:menu_width - 4])
            menu_win.refresh()
            
        def update_selection_only():
            """Update only the selection highlighting without full redraw"""
            for i in range(max_visible_options):
                option_index = scroll_offset + i
                if option_index >= len(options):
                    break
                    
                y = 3 + i
                option = options[option_index]
                
                # Clear the line first
                menu_win.addstr(y, 2, " " * (menu_width - 4))
                
                if option_index == current:
                    menu_win.attron(curses.color_pair(6))
                    menu_win.addstr(y, 2, f"> {option}")
                    menu_win.attroff(curses.color_pair(6))
                else:
                    menu_win.addstr(y, 2, f"  {option}")
            menu_win.refresh()
        
        # Initial draw
        draw_menu()
        
        while True:
            # Process any pending refresh requests
            self.process_pending_refresh()
            key = menu_win.getch()  # Get key input
            
            old_current = current
            old_scroll_offset = scroll_offset
            
            if key == curses.KEY_UP:
                current = (current - 1) % len(options)
            elif key == curses.KEY_DOWN:
                current = (current + 1) % len(options)
            
            # Calculate scroll offset to keep current selection visible
            if current < scroll_offset:
                scroll_offset = current
            elif current >= scroll_offset + max_visible_options:
                scroll_offset = current - max_visible_options + 1
            
            # Update display only if something changed
            if old_current != current or old_scroll_offset != scroll_offset:
                if old_scroll_offset != scroll_offset:
                    # Scroll position changed, need full redraw
                    draw_menu()
                else:
                    # Only selection changed, partial update
                    update_selection_only()
                    
            if key == curses.KEY_LEFT:
                # Scroll up in background logs (show older messages)
                visible_lines = self.height - 6
                max_scroll = max(0, len(self.log_lines) - visible_lines)
                if self.scroll_offset < max_scroll:
                    self.scroll_offset += 1
                    self.debounced_refresh()
                    menu_win.refresh()  # Refresh menu on top of logs
            elif key == curses.KEY_RIGHT:
                # Scroll down in background logs (show newer messages)
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
                    self.debounced_refresh()
                    menu_win.refresh()  # Refresh menu on top of logs
            elif key == curses.KEY_HOME:
                # Go to top of background logs
                visible_lines = self.height - 6
                self.scroll_offset = max(0, len(self.log_lines) - visible_lines)
                self.debounced_refresh()
                menu_win.refresh()
            elif key == curses.KEY_END:
                # Go to bottom of background logs
                self.scroll_offset = 0
                self.debounced_refresh()
                menu_win.refresh()
            elif key == ord('j'):
                # Scroll down in background logs (show newer messages) - vim style
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
                    self.debounced_refresh()
                    menu_win.refresh()
            elif key == ord('k'):
                # Scroll up in background logs (show older messages) - vim style
                visible_lines = self.height - 6
                max_scroll = max(0, len(self.log_lines) - visible_lines)
                if self.scroll_offset < max_scroll:
                    self.scroll_offset += 1
                    self.debounced_refresh()
                    menu_win.refresh()
            elif key == curses.KEY_MOUSE:
                # Handle mouse events for scrollbar in menu
                try:
                    _, mouse_x, mouse_y, _, button_state = curses.getmouse()
                    if self.handle_scrollbar_click(mouse_x, mouse_y, button_state):
                        menu_win.refresh()  # Refresh menu after scrollbar click
                except curses.error:
                    pass  # Ignore mouse errors
            elif key == 10 or key == 13:  # Enter
                del menu_win
                self.refresh_display()
                return current
            elif key == 27:  # Escape
                del menu_win
                self.refresh_display()
                return -1


# Global UI instance
ui = NCursesUI()

# Global language state
selected_language = None