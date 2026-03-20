"""
================================================================
  Apache Airlines — Burak757 Seat Booking System
  FC723 Programming Theory  |  Project Part A
================================================================

PURPOSE:
  This program manages seat reservations for the Apache Airlines
  Burak757 aircraft. Staff or customers use a numbered menu to
  check seat availability, make bookings, cancel bookings, and
  view the current state of the entire cabin.

AIRCRAFT LAYOUT — Burak757 floor plan:
  The Burak757 is a narrow-body jet with a single centre aisle.
  The cabin grid has 7 columns and uses the following codes:

      Column index:  0    1    2    3    4    5    6
      Column label:  A    B    C    |    D    E    F

  Row 0         : S  S  S  S  S  S  S   (front galley / storage)
  Rows 1–2      : First Class  — A  B  X  D  E  (2+2, narrower)
  Rows 3–7      : Business     — A  B  C  X  D  E  F (3+3)
  Rows 8–30     : Economy      — A  B  C  X  D  E  F (3+3)
  Row 31        : S  S  S  S  S  S  S   (rear galley / storage)

  Key:
      'F'  = Free seat          (available to book)
      'R'  = Reserved           (used only in Part A — Part B uses ref)
      'X'  = Aisle              (cannot be booked)
      'S'  = Storage / Galley   (cannot be booked)

CLASSES USED:
  SeatMap            — stores and manages the aircraft seating grid
  ReferenceGenerator — produces unique 8-character booking codes
  BookingSystem      — handles all booking operations
  Menu               — displays the menu and drives the main loop

AUTHOR  : ALI
DATE    : [Submission Date]
MODULE  : FC723 Programming Theory
================================================================
"""

# ── Standard library imports ──────────────────────────────────
import random   # needed to pick random characters for booking refs
import string   # provides A-Z letters and 0-9 digits as strings


# ================================================================
#  CLASS 1 — SeatMap
#  Stores the Burak757 seating grid and provides read/write access
# ================================================================
class SeatMap:
    """
    Represents the physical layout of the Burak757 aircraft cabin.

    The cabin is stored as a 2-D list (a list of rows, where each
    row is a list of seat-status strings).  This mirrors how the
    floor plan looks on paper — rows top-to-bottom, seats left-to-right.

    Seat status codes:
        'F'  — free (can be booked)
        'X'  — aisle (not a seat)
        'S'  — storage / galley (not a seat)
        Any 8-char string — a booking reference (seat is reserved)
    """

    def __init__(self):
        """
        Builds the complete cabin grid when a SeatMap object is created.

        Layout details:
            Row  0      : front storage/galley  — all 7 positions are 'S'
            Rows 1-2    : First Class (2+2 layout)
                          cols 0-1 = seats A B, col 2 = aisle X,
                          cols 3-4 = seats D E,  cols 5-6 = padding 'S'
                          (First Class is narrower — only 4 seats per row)
            Rows 3-30   : Business + Economy (3+3 layout)
                          cols 0-2 = seats A B C, col 3 = aisle X,
                          cols 4-6 = seats D E F
            Row 31      : rear storage/galley — all 7 positions are 'S'

        A fresh copy of each template row is added for every row so that
        changing one row does not accidentally affect the others.
        """

        # --- row templates (7 columns each) -----------------------

        # Storage row: used at the very front and very back
        storage = ['S', 'S', 'S', 'S', 'S', 'S', 'S']

        # First Class row: 2 seats | aisle | 2 seats | 2 unused spaces
        # Columns:          A   B     X      D   E       padding
        first_class = ['F', 'F', 'X', 'F', 'F', 'S', 'S']

        # Standard row (Business and Economy): 3 seats | aisle | 3 seats
        # Columns:                              A   B   C   X   D   E   F
        standard = ['F', 'F', 'F', 'X', 'F', 'F', 'F']

        # --- build the grid row by row ----------------------------

        self.grid = []   # this list will hold every row of the cabin

        # Row 0 — front galley / storage
        self.grid.append(list(storage))        # list() makes a fresh copy

        # Rows 1-2 — First Class (2 rows)
        for _ in range(2):
            self.grid.append(list(first_class))

        # Rows 3-30 — Business and Economy (28 rows)
        for _ in range(28):
            self.grid.append(list(standard))

        # Row 31 — rear galley / storage
        self.grid.append(list(storage))

        # --- column display labels --------------------------------
        # These labels are printed above the grid so the user can
        # see which column is which.  '|' represents the aisle visually.
        self.col_labels = ['A', 'B', 'C', '|', 'D', 'E', 'F']

        # --- column letter → grid index mapping ------------------
        # The user types a letter (e.g. 'D') and we convert it to the
        # correct index in the row list (e.g. index 4).
        self.letter_to_index = {
            'A': 0, 'B': 1, 'C': 2,
            'D': 4, 'E': 5, 'F': 6
        }

        # Reverse lookup: index → letter (used when printing results)
        self.index_to_letter = {0: 'A', 1: 'B', 2: 'C', 4: 'D', 5: 'E', 6: 'F'}

    # ── Seat access helpers ──────────────────────────────────────

    def get_seat(self, row, col):
        """
        Returns the current status code stored at [row][col].
        This will be 'F', 'X', 'S', or an 8-character reference.
        """
        return self.grid[row][col]

    def set_seat(self, row, col, value):
        """
        Writes a new value into the seat at [row][col].
        Used when booking (writes a reference) or freeing (writes 'F').
        """
        self.grid[row][col] = value

    def is_free(self, row, col):
        """
        Returns True if the seat is available to book (status == 'F').
        Returns False for any other status.
        """
        return self.grid[row][col] == 'F'

    def is_reserved(self, row, col):
        """
        Returns True if the seat is currently booked.
        A seat is booked when its value is NOT 'F', 'X', or 'S'.
        In Part A this will be 'R'; in Part B it will be a reference string.
        """
        status = self.grid[row][col]
        # Anything that is not a fixed code must be a booking
        return status not in ('F', 'X', 'S')

    def is_valid_seat(self, row, col):
        """
        Returns True if this position is an actual seat (not aisle or storage).
        Used before trying to book or free a position.
        """
        status = self.grid[row][col]
        return status not in ('X', 'S')

    # ── Display method ───────────────────────────────────────────

    def display(self):
        """
        Prints the full Burak757 cabin map to the terminal.

        Format example:
            Row  |  A   B   C   |   D   E   F
            -----|-------------------------------
              0  |  S   S   S   S   S   S   S
              1  |  F   F   X   F   F   S   S
              ...

        Seats showing 'F' are free, anything else is occupied or non-bookable.
        If a booking reference is stored it appears truncated to 8 chars.
        """
        print()
        print("=" * 52)
        print("     APACHE AIRLINES  —  BURAK757 CABIN MAP")
        print("=" * 52)

        # Print the column header row
        print("  Row |", end="")
        for label in self.col_labels:
            # Each label is printed in a fixed 4-character space
            print(f"  {label} ", end="")
        print()   # newline after headers

        # Separator line under the headers
        print("  ----|" + "-" * 30)

        # Print every row in the grid
        for row_idx, row in enumerate(self.grid):
            # Row number, padded to 3 characters for neat alignment
            print(f"  {row_idx:3} |", end="")

            for seat in row:
                # Trim any long reference to 8 chars so columns stay aligned
                display_val = seat[:3] if len(seat) > 2 else seat
                print(f" {display_val:>3}", end="")
            print()   # newline after each row

        print("=" * 52)
        # Show the legend so the user always knows what the codes mean
        print("  F = Free    X = Aisle    S = Storage/Galley")
        print("  A booking reference shown = Reserved seat")
        print("=" * 52)
        print()


# ================================================================
#  CLASS 2 — ReferenceGenerator
#  Produces unique 8-character alphanumeric booking references
# ================================================================
class ReferenceGenerator:
    """
    Generates random, unique booking reference codes.

    Each reference is exactly 8 characters long and made up of
    uppercase letters (A-Z) and digits (0-9), giving 36^8 =
    approximately 2.8 trillion possible combinations.

    A Python set is used to track which references have already
    been issued, ensuring no two bookings ever share the same code.
    """

    def __init__(self):
        """
        Creates an empty set to store all references that have been used.
        The set starts empty because no bookings exist yet.
        """
        # A set is ideal here because checking "is X in the set?"
        # is extremely fast even if thousands of references have been issued.
        self.used = set()

    def generate(self):
        """
        Produces and returns a new unique 8-character booking reference.

        Algorithm step-by-step:
          1. Build the pool of allowed characters: A-Z plus 0-9 (36 chars).
          2. Use random.choices() to pick 8 characters from this pool.
             random.choices() allows repetition, so the same letter or
             digit can appear more than once in the same reference.
          3. Join the 8 characters into a single string.
          4. Check whether this string already exists in self.used.
          5. If it DOES exist (a collision), go back to step 2 and try again.
          6. If it does NOT exist, add it to self.used and return it.

        In practice step 5 almost never happens because the chance of a
        collision among 2.8 trillion possibilities is astronomically small.
        """
        # Build the character pool (uppercase letters + digits)
        pool = string.ascii_uppercase + string.digits  # 'ABCDE...Z0123456789'

        while True:   # keep trying until we find a unique reference
            # Pick 8 random characters from the pool and join them
            candidate = ''.join(random.choices(pool, k=8))

            # Only use this candidate if it has not been issued before
            if candidate not in self.used:
                # Record the reference so it will never be reused
                self.used.add(candidate)
                # Return the new unique reference to the caller
                return candidate
            # If we reach here, candidate was a duplicate — loop and try again


# ================================================================
#  CLASS 3 — BookingSystem
#  Central controller for all seat-booking operations
# ================================================================
class BookingSystem:
    """
    Connects the SeatMap and ReferenceGenerator and implements all
    the actions a user can perform:

        1. Check whether a specific seat is available
        2. Book a free seat (generates and stores a reference)
        3. Free (cancel) a reserved seat after verifying the reference
        4. Show the complete cabin map with a seat-count summary
        5. List all currently available window seats  [extra feature]

    Input validation is handled here so the user can never crash
    the program by typing unexpected values.
    """

    def __init__(self):
        """
        Creates fresh instances of SeatMap and ReferenceGenerator.
        Both objects persist for the entire session so that all
        operations share the same cabin state.
        """
        # The cabin grid — all seats start as 'F' (free)
        self.seat_map = SeatMap()

        # The reference generator — starts with no references issued
        self.ref_gen = ReferenceGenerator()

    # ── Private input helper ─────────────────────────────────────

    def _ask_for_seat(self):
        """
        Asks the user to enter a row number and a column letter.
        Keeps asking until valid input is provided or the user cancels.

        The method is 'private' (prefixed with _) because it is only
        used internally by other methods in this class.

        Returns:
            (row_int, col_int)  — a tuple of two integers if valid input
            None                — if the user types 'cancel'

        Validation rules:
            - Row must be an integer between 1 and 30 (skipping storage rows)
            - Column must be one of A, B, C, D, E, F
        """
        print("    (Type 'cancel' to return to the main menu)")

        while True:
            # --- ask for row number --------------------------------
            row_raw = input("    Row number (1–30): ").strip()

            # Allow the user to abort and go back to the menu
            if row_raw.lower() == 'cancel':
                return None

            # Make sure the input is actually a number
            if not row_raw.isdigit():
                print("    ✗  Please type a number for the row.")
                continue

            row = int(row_raw)

            # Rows 0 and 31 are storage — only 1-30 are valid seating rows
            if row < 1 or row > 30:
                print("    ✗  Row must be between 1 and 30.")
                continue

            # --- ask for column letter -----------------------------
            col_raw = input("    Seat letter (A / B / C / D / E / F): ").strip().upper()

            if col_raw.lower() == 'cancel':
                return None

            # Check the letter is in our mapping dictionary
            if col_raw not in self.seat_map.letter_to_index:
                print("    ✗  Seat letter must be A, B, C, D, E, or F.")
                continue

            # Convert the letter to the matching column index
            col = self.seat_map.letter_to_index[col_raw]

            # All checks passed — return the row and column as a tuple
            return (row, col)

    # ── Menu operation 1 — Check availability ───────────────────

    def check_availability(self):
        """
        Task A4 — Menu Option 1: Check Availability of Seat

        Asks the user for a seat location and reports whether that
        seat is free, already reserved, or not a bookable position.

        This does NOT make any changes to the cabin grid.
        """
        print("\n  ── CHECK SEAT AVAILABILITY ──────────────────────")

        # Get the seat the user wants to check
        result = self._ask_for_seat()

        # If the user cancelled, go back to the menu
        if result is None:
            print("    Cancelled — returning to menu.")
            return

        row, col = result
        col_letter = self.seat_map.index_to_letter[col]  # e.g. index 4 → 'D'
        status = self.seat_map.get_seat(row, col)

        print()
        if status == 'F':
            # The seat is free and available for booking
            print(f"    ✓  Seat {row}{col_letter} is AVAILABLE.")

        elif status == 'X':
            # This column is the centre aisle — not a seat
            print(f"    ✗  Position {row}{col_letter} is the AISLE — not a seat.")

        elif status == 'S':
            # This row or column is storage space
            print(f"    ✗  Position {row}{col_letter} is a STORAGE area — not a seat.")

        else:
            # The seat holds a booking reference, so it is already reserved
            print(f"    ✗  Seat {row}{col_letter} is RESERVED.")
            print(f"       Booking reference: {status}")

    # ── Menu operation 2 — Book a seat ──────────────────────────

    def book_seat(self):
        """
        Task A4 — Menu Option 2: Book a Seat

        Asks the user for a seat location, checks it is free, then:
          - Generates a unique 8-character booking reference
          - Stores that reference in the seat grid (replacing 'F')
          - Displays the reference to the user

        If the seat is not free, a helpful error message is shown
        and no changes are made.
        """
        print("\n  ── BOOK A SEAT ──────────────────────────────────")

        # Get the seat the user wants to book
        result = self._ask_for_seat()

        if result is None:
            print("    Cancelled — returning to menu.")
            return

        row, col = result
        col_letter = self.seat_map.index_to_letter[col]

        # Check the seat is actually free before proceeding
        if not self.seat_map.is_valid_seat(row, col):
            # The position is an aisle or storage — cannot be booked
            print(f"\n    ✗  Seat {row}{col_letter} is not a bookable seat position.")
            return

        if not self.seat_map.is_free(row, col):
            # The seat exists but is already reserved by someone else
            existing_ref = self.seat_map.get_seat(row, col)
            print(f"\n    ✗  Seat {row}{col_letter} is already RESERVED.")
            print(f"       Existing reference: {existing_ref}")
            return

        # The seat is free — generate a new unique booking reference
        ref = self.ref_gen.generate()

        # Write the reference into the seat grid to mark it as reserved
        self.seat_map.set_seat(row, col, ref)

        # Confirm the booking to the user and show their reference
        print(f"\n    ✓  Seat {row}{col_letter} has been successfully BOOKED.")
        print(f"       Your booking reference: {ref}")
        print("       Please save this reference — you will need it to cancel.")

    # ── Menu operation 3 — Free a seat ──────────────────────────

    def free_seat(self):
        """
        Task A4 — Menu Option 3: Free a Seat (Cancel a Booking)

        Asks the user for a seat location and their booking reference.
        Only cancels the booking if the reference they provide matches
        the one stored in the seat grid.

        If the reference is wrong, the booking is left unchanged.
        This prevents customers from cancelling each other's seats.
        """
        print("\n  ── FREE A SEAT  (Cancel Booking) ────────────────")

        # Get the seat the user wants to cancel
        result = self._ask_for_seat()

        if result is None:
            print("    Cancelled — returning to menu.")
            return

        row, col = result
        col_letter = self.seat_map.index_to_letter[col]

        # Make sure the seat is actually reserved before trying to free it
        if not self.seat_map.is_valid_seat(row, col):
            print(f"\n    ✗  Position {row}{col_letter} is not a seat.")
            return

        if self.seat_map.is_free(row, col):
            # The seat is already free — there is nothing to cancel
            print(f"\n    ✗  Seat {row}{col_letter} is already FREE. No booking to cancel.")
            return

        # The seat is reserved — ask for the reference to verify ownership
        stored_ref = self.seat_map.get_seat(row, col)
        entered_ref = input("    Enter your booking reference: ").strip().upper()

        if entered_ref == stored_ref:
            # The reference matches — release the seat back to free
            self.seat_map.set_seat(row, col, 'F')
            print(f"\n    ✓  Seat {row}{col_letter} is now FREE. Booking {stored_ref} cancelled.")
        else:
            # Wrong reference — do not cancel
            print("\n    ✗  Incorrect booking reference. Cancellation denied.")
            print("       The seat remains reserved.")

    # ── Menu operation 4 — Show booking status ──────────────────

    def show_booking_status(self):
        """
        Task A4 — Menu Option 4: Show Booking Status

        Displays the full cabin map and then prints a summary showing
        how many seats are free, how many are reserved, and the total.

        No changes are made to the cabin grid.
        """
        print("\n  ── FULL BOOKING STATUS ──────────────────────────")

        # Print the visual cabin grid
        self.seat_map.display()

        # Count free and reserved seats across the whole cabin
        free_count = 0
        reserved_count = 0

        for row in self.seat_map.grid:
            for seat in row:
                if seat == 'F':
                    free_count += 1        # this position is free
                elif seat not in ('X', 'S'):
                    reserved_count += 1    # this position has a booking reference

        # Display the summary numbers
        print(f"    Free seats    : {free_count}")
        print(f"    Reserved seats: {reserved_count}")
        print(f"    Total seats   : {free_count + reserved_count}")
        print()

    # ── Menu operation 5 — Window seats [extra feature] ─────────

    def show_window_seats(self):
        """
        Task A5 — Extra Functionality: Show Available Window Seats

        Window seats are the outermost seats on each side of the cabin.
        In a real airline booking system this is one of the most commonly
        requested features — many passengers specifically want a window
        seat for the view during the flight.

        Window seat definitions for the Burak757:
          Rows 1-2  (First Class)  : Column A (index 0) and Column E (index 4)
                                     The right-side window is column E because
                                     First Class only has 4 seats (A B | X | D E).
          Rows 3-30 (Bus./Economy) : Column A (index 0) and Column F (index 6)
                                     These are the leftmost and rightmost seats.

        The method scans the entire grid and lists every window seat that
        currently shows 'F' (free).
        """
        print("\n  ── AVAILABLE WINDOW SEATS ───────────────────────")
        print("    Window seats are the outermost seats on each side.")
        print()

        found = False   # will become True if at least one window seat is free

        # Check rows 1-30 (skip row 0 and 31 which are storage)
        for row_idx in range(1, 31):

            if row_idx <= 2:
                # First Class — narrower layout, right window is column E (index 4)
                window_cols = [0, 4]
            else:
                # Business and Economy — right window is column F (index 6)
                window_cols = [0, 6]

            for col_idx in window_cols:
                seat_status = self.seat_map.get_seat(row_idx, col_idx)
                col_letter = self.seat_map.index_to_letter[col_idx]

                if seat_status == 'F':
                    # This window seat is currently free — display it
                    section = "First Class" if row_idx <= 2 else (
                              "Business" if row_idx <= 7 else "Economy")
                    print(f"    ✓  Row {row_idx:2}  Seat {col_letter}  —  {section}  (window — available)")
                    found = True

        if not found:
            # Every window seat has been booked
            print("    ✗  No window seats are currently available.")

        print()


# ================================================================
#  CLASS 4 — Menu
#  Shows the main menu and routes user choices to BookingSystem
# ================================================================
class Menu:
    """
    Manages the user interface for the entire program.

    Creates a single BookingSystem object that is shared across all
    menu interactions, so that every booking persists for the whole
    session.

    The run() method loops indefinitely, showing the menu after each
    completed action, until the user selects the Exit option.
    """

    def __init__(self):
        """
        Creates the BookingSystem that this menu will control.
        """
        # One BookingSystem is created and used for the whole session
        self.system = BookingSystem()

    def _print_menu(self):
        """
        Prints the list of menu options to the terminal.
        This is a private helper called by run() each loop iteration.
        """
        print()
        print("  ╔══════════════════════════════════════════════╗")
        print("  ║    APACHE AIRLINES  —  BURAK757 BOOKING      ║")
        print("  ╠══════════════════════════════════════════════╣")
        print("  ║   1.  Check availability of a seat           ║")
        print("  ║   2.  Book a seat                            ║")
        print("  ║   3.  Free a seat  (cancel booking)          ║")
        print("  ║   4.  Show full booking status               ║")
        print("  ║   5.  Show available window seats            ║")
        print("  ║   6.  Exit program                           ║")
        print("  ╚══════════════════════════════════════════════╝")

    def run(self):
        """
        Starts the main program loop.

        Displays a welcome message, then repeatedly shows the menu
        and calls the appropriate BookingSystem method based on the
        user's choice.

        The loop continues until the user enters '6' to exit.
        Any input that is not 1-6 shows an error and re-displays
        the menu without crashing the program.
        """
        # Welcome message shown once at startup
        print()
        print("  ══════════════════════════════════════════════")
        print("    Welcome to Apache Airlines Booking System")
        print("    Burak757 Fleet  —  Seat Management Terminal")
        print("  ══════════════════════════════════════════════")

        running = True   # controls the main loop — set to False to exit

        while running:
            # Show the menu options every iteration
            self._print_menu()

            # Ask the user to choose an option
            choice = input("  Enter your choice (1–6): ").strip()

            # Route the choice to the correct method
            if choice == '1':
                # Option 1: check if a specific seat is free or taken
                self.system.check_availability()

            elif choice == '2':
                # Option 2: reserve a free seat for the customer
                self.system.book_seat()

            elif choice == '3':
                # Option 3: cancel an existing reservation
                self.system.free_seat()

            elif choice == '4':
                # Option 4: display the complete cabin map and counts
                self.system.show_booking_status()

            elif choice == '5':
                # Option 5 (extra feature): list all free window seats
                self.system.show_window_seats()

            elif choice == '6':
                # Option 6: terminate the program gracefully
                print()
                print("  Thank you for using the Apache Airlines Booking System.")
                print("  Have a great flight.  Goodbye!")
                print()
                running = False   # this ends the while loop

            else:
                # The user typed something other than 1-6
                print("\n  ✗  Invalid option. Please enter a number from 1 to 6.")


# ================================================================
#  PROGRAM ENTRY POINT
#
#  Python runs this block only when the file is executed directly
#  (e.g.  python apache_booking.py).
#  If this file were imported by another script, this block would
#  be skipped — which prevents unintended side-effects.
# ================================================================
if __name__ == "__main__":
    # Create the Menu object and start the program loop
    app = Menu()
    app.run()
