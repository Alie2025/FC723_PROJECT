"""
================================================================
  Apache Airlines — Burak757 Seat Booking System
  FC723 Programming Theory  |  Project Part B
================================================================
 
PURPOSE:
  This is the Part B refactored version of the Apache Airlines
  seat booking system. It extends Part A by adding:
 
    1. A unique 8-character alphanumeric booking reference
       algorithm (Part B Task 1).
 
    2. A SQLite database storing passenger details every time
       a seat is booked. When freed, the record is deleted
       (Part B Task 2).
 
PART B TASK 1 — BOOKING REFERENCE ALGORITHM:
  The ReferenceGenerator class uses this algorithm:
    Step 1: Build a pool of 36 characters (A-Z and 0-9).
    Step 2: Use random.choices() to pick 8 characters from
            the pool WITH replacement (repetition allowed).
    Step 3: Join the 8 characters into one string.
    Step 4: Check if this string already exists in the 'used'
            set (which tracks all previously issued refs).
    Step 5: If it IS in 'used' (collision) — go to Step 2.
    Step 6: If it is NOT in 'used' — add it and return it.
  With 36^8 = 2.8 trillion possible combinations, collisions
  are astronomically rare. The loop almost always exits on
  the very first iteration.
 
PART B TASK 2 — DATABASE:
  Python's built-in sqlite3 module creates 'bookings.db'.
  TABLE: bookings
    reference  TEXT PRIMARY KEY  (8-char unique code)
    passport   TEXT              (passenger passport number)
    first_name TEXT              (passenger first name)
    last_name  TEXT              (passenger last name)
    seat_row   INTEGER           (row number 1-30)
    seat_col   TEXT              (column letter A-F)
 
AIRCRAFT LAYOUT — Burak757:
  Row  0      : S S S S S S S  (front galley/storage)
  Rows 1-2    : First Class  (A B | X | D E — 2+2)
  Rows 3-30   : Business/Economy (A B C | X | D E F — 3+3)
  Row 31      : S S S S S S S  (rear galley/storage)
  F=Free  X=Aisle  S=Storage  ref=Reserved
 
CLASSES:
  Database           — creates and manages the SQLite database
  SeatMap            — stores and manages the aircraft grid
  ReferenceGenerator — generates unique 8-char booking codes
  BookingSystem      — all booking operations (grid + database)
  Menu               — displays the menu and runs the main loop
================================================================
"""
 
import random   # pick random characters for references
import string   # provides the A-Z letters and 0-9 digits
import sqlite3  # built in Python module for local SQL databases
 
 
#  CLASS 1 — Database
#  Creates and manages the SQLite bookings database

class Database:
    """
    Manages all interactions with the SQLite file 'bookings.db'.
 
    A database record is created when a seat is booked and
    deleted when a booking is cancelled. This keeps the
    database always in sync with the seat grid.
 
    TABLE: bookings
      reference  — unique 8-char booking code  (PRIMARY KEY)
      passport   — passenger passport number
      first_name — passenger first name
      last_name  — passenger last name
      seat_row   — row number of the booked seat (integer)
      seat_col   — column letter of the booked seat (A-F)
    """
 
    def __init__(self, db_name="bookings.db"):
        """
        Opens (or creates) the database file and builds the
        bookings table if it does not already exist.
        'IF NOT EXISTS' makes this safe to call every startup.
        """
        # Connect to the database file — creates it if missing
        self.connection = sqlite3.connect(db_name)
 
        # Cursor lets us run SQL commands against the database
        self.cursor = self.connection.cursor()
 
        # Create the bookings table if it does not exist yet
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                reference  TEXT PRIMARY KEY,
                passport   TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name  TEXT NOT NULL,
                seat_row   INTEGER NOT NULL,
                seat_col   TEXT NOT NULL
            )
        """)
 
        # Commit saves the table structure to the file
        self.connection.commit()
 
    def add_booking(self, reference, passport, first_name,
                    last_name, seat_row, seat_col):
        """
        Inserts one new booking record into the database.
        The '?' placeholders are parameterised queries —
        they prevent SQL injection attacks by separating
        the SQL structure from the actual data values.
        """
        self.cursor.execute("""
            INSERT INTO bookings
            (reference, passport, first_name, last_name,
             seat_row, seat_col)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (reference, passport, first_name, last_name,
              seat_row, seat_col))
 
        # Commit saves the new row to disk permanently
        self.connection.commit()
 
    def remove_booking(self, reference):
        """
        Deletes the booking record matching the given reference.
        Called when a seat is freed/cancelled.
        If no matching record exists, nothing happens.
        """
        self.cursor.execute(
            "DELETE FROM bookings WHERE reference = ?",
            (reference,)
        )
        self.connection.commit()
 
    def get_booking(self, reference):
        """
        Retrieves one booking record by its reference code.
        Returns a tuple (ref, passport, first, last, row, col)
        or None if no matching record is found.
        """
        self.cursor.execute(
            "SELECT * FROM bookings WHERE reference = ?",
            (reference,)
        )
        return self.cursor.fetchone()
 
    def get_all_bookings(self):
        """
        Returns all booking records as a list of tuples.
        Returns an empty list if no bookings have been made.
        """
        self.cursor.execute("SELECT * FROM bookings")
        return self.cursor.fetchall()
 
    def close(self):
        """
        Closes the database connection cleanly.
        Always call this before the program exits to prevent
        any data corruption in the database file.
        """
        self.connection.close()
 
 

#  CLASS 2 — SeatMap
#  Stores and manages the Burak757 cabin seating grid
class SeatMap:
    """
    Represents the physical Burak757 aircraft cabin as a 2-D list.
 
    Each cell holds one of:
      'F'           — free seat (available to book)
      'X'           — aisle (not a seat, cannot be booked)
      'S'           — storage or galley (cannot be booked)
      8-char string — a booking reference (seat is reserved)
    """
 
    def __init__(self):
        """
        Builds the full cabin grid at program startup.
        list() makes a fresh independent copy of each
        template row so editing one row never affects others.
        """
        # Row templates — each is 7 columns wide
        storage     = ['S', 'S', 'S', 'S', 'S', 'S', 'S']
        first_class = ['F', 'F', 'X', 'F', 'F', 'S', 'S']
        standard    = ['F', 'F', 'F', 'X', 'F', 'F', 'F']
 
        self.grid = []
        self.grid.append(list(storage))       # row 0: front galley
        for _ in range(2):                    # rows 1-2: First Class
            self.grid.append(list(first_class))
        for _ in range(28):                   # rows 3-30: standard
            self.grid.append(list(standard))
        self.grid.append(list(storage))       # row 31: rear galley
 
        # Column header labels printed above the grid
        self.col_labels = ['A', 'B', 'C', '|', 'D', 'E', 'F']
 
        # Converts the user's typed letter to the grid column index
        self.letter_to_index = {
            'A': 0, 'B': 1, 'C': 2,
            'D': 4, 'E': 5, 'F': 6
        }
 
        # Converts a column index back to the display letter
        self.index_to_letter = {
            0: 'A', 1: 'B', 2: 'C',
            4: 'D', 5: 'E', 6: 'F'
        }
 
    def get_seat(self, row, col):
        """Returns the status code stored at grid[row][col]."""
        return self.grid[row][col]
 
    def set_seat(self, row, col, value):
        """Writes a new value into grid[row][col]."""
        self.grid[row][col] = value
 
    def is_free(self, row, col):
        """Returns True only if the seat status is 'F'."""
        return self.grid[row][col] == 'F'
 
    def is_reserved(self, row, col):
        """
        Returns True if the seat holds a booking reference.
        Anything that is not F, X, or S must be a reference.
        """
        return self.grid[row][col] not in ('F', 'X', 'S')
 
    def is_valid_seat(self, row, col):
        """Returns True if the position is an actual bookable seat."""
        return self.grid[row][col] not in ('X', 'S')
 
    def display(self):
        """
        Prints the complete cabin grid with row numbers and
        column labels so the user can see every seat's status.
        References are truncated to 3 chars to keep alignment.
        """
        print()
        print("=" * 56)
        print("      APACHE AIRLINES  —  BURAK757 CABIN MAP")
        print("=" * 56)
        print("  Row |", end="")
        for label in self.col_labels:
            print(f"  {label} ", end="")
        print()
        print("  ----|" + "-" * 32)
        for idx, row in enumerate(self.grid):
            print(f"  {idx:3} |", end="")
            for seat in row:
                val = seat[:3] if len(seat) > 2 else seat
                print(f" {val:>3}", end="")
            print()
        print("=" * 56)
        print("  F=Free  X=Aisle  S=Storage  ref=Reserved")
        print("=" * 56)
        print()
 
 
#  CLASS 3 — ReferenceGenerator
#  Part B Task 1: Unique 8-character alphanumeric references
class ReferenceGenerator:
    """
    Generates random, unique 8-character alphanumeric booking
    references using the algorithm described below.
 
    ALGORITHM (Part B Task 1):
    ──────────────────────────
    1. CHARACTER POOL: combine all uppercase letters (A-Z, 26
       chars) with all digit characters (0-9, 10 chars) to
       get a pool of 36 characters total.
 
    2. RANDOM SELECTION: use random.choices(pool, k=8) to
       select 8 characters WITH REPLACEMENT. This means:
         - The same character can appear more than once.
         - Each character is chosen independently.
         - There are 36^8 = 2,821,109,907,456 possible
           combinations (about 2.8 trillion).
 
    3. JOIN: ''.join(...) combines the 8 characters into one
       string, e.g. ['A','3','K','X','7','P','2','Q']
       becomes 'A3KX7P2Q'.
 
    4. UNIQUENESS CHECK: compare the candidate against the
       'used' set, which stores all previously issued refs.
         - Collision (already in used): loop back to step 2.
         - Unique (not in used): record it and return it.
 
    5. WHY A SET? Python sets use O(1) hash-based lookup so
       checking membership is instant even with thousands
       of existing references stored.
 
    COLLISION PROBABILITY:
       Even after 1,000,000 bookings the chance of any new
       candidate being a duplicate is less than 0.00004%.
       The while loop almost always exits on the first try.
    """
 
    def __init__(self):
        """
        Creates the empty 'used' set.
        The set starts empty because no bookings exist yet.
        """
        self.used = set()   # tracks every reference ever issued
 
    def generate(self):
        """
        Runs the algorithm and returns a new unique reference.
 
        Returns:
            A string of exactly 8 uppercase alphanumeric chars
            that has never been returned by this instance before.
        """
        # Step 1: Build the 36-character pool
        pool = string.ascii_uppercase + string.digits
 
        while True:
            # Step 2 and 3: Pick 8 random chars, join to string
            candidate = ''.join(random.choices(pool, k=8))
 
            # Step 4: Check uniqueness
            if candidate not in self.used:
                # Unique — record it in the set, then return it
                self.used.add(candidate)
                return candidate
            # If we reach here it was a duplicate — loop again
 
 
#  CLASS 4 — BookingSystem
#  Part B Task 2: All booking operations with database support
class BookingSystem:
    """
    The central controller that links SeatMap, Database, and
    ReferenceGenerator together.
 
    PART B CHANGES FROM PART A:
      book_seat()  — now collects passenger details and saves
                     them to the database alongside the ref.
      free_seat()  — now also deletes the database record when
                     a booking is cancelled.
      view_all_bookings() — NEW: shows all database records.
 
    All other operations work the same as Part A.
    """
 
    def __init__(self):
        """
        Creates SeatMap, ReferenceGenerator and Database.
        All three share the same lifetime as the program.
        """
        self.seat_map = SeatMap()
        self.ref_gen  = ReferenceGenerator()
        self.db       = Database()
 
    def _ask_for_seat(self):
        """
        Asks the user for a valid row (1-30) and column letter.
        Returns (row_int, col_int) or None if cancelled.
        """
        print("    (Type 'cancel' to return to the menu)")
        while True:
            row_raw = input("    Row number (1-30): ").strip()
            if row_raw.lower() == 'cancel':
                return None
            if not row_raw.isdigit():
                print("    ✗  Please type a number.")
                continue
            row = int(row_raw)
            if row < 1 or row > 30:
                print("    ✗  Row must be 1 to 30.")
                continue
            col_raw = input(
                "    Seat letter (A/B/C/D/E/F): ").strip().upper()
            if col_raw.lower() == 'cancel':
                return None
            if col_raw not in self.seat_map.letter_to_index:
                print("    ✗  Letter must be A, B, C, D, E, or F.")
                continue
            return (row, self.seat_map.letter_to_index[col_raw])
 
    def _ask_for_passenger_details(self):
        """
        Part B addition: collects passport number, first name,
        and last name from the user for the database record.
        Returns (passport, first_name, last_name) or None.
        All three fields are required — empty input is rejected.
        """
        print("    (Type 'cancel' at any prompt to go back)")
 
        while True:
            passport = input("    Passport number: ").strip().upper()
            if passport.lower() == 'cancel':
                return None
            if passport:
                break
            print("    ✗  Passport cannot be empty.")
 
        while True:
            first_name = input("    First name: ").strip().title()
            if first_name.lower() == 'cancel':
                return None
            if first_name:
                break
            print("    ✗  First name cannot be empty.")
 
        while True:
            last_name = input("    Last name: ").strip().title()
            if last_name.lower() == 'cancel':
                return None
            if last_name:
                break
            print("    ✗  Last name cannot be empty.")
 
        return (passport, first_name, last_name)
 
    def check_availability(self):
        """
        Option 1: Check if a seat is free, reserved, or invalid.
        If reserved, retrieves and displays the passenger's
        name and passport from the database. Read-only.
        """
        print("\n  ── CHECK SEAT AVAILABILITY ──────────────────────")
        result = self._ask_for_seat()
        if result is None:
            print("    Cancelled.")
            return
 
        row, col = result
        col_letter = self.seat_map.index_to_letter[col]
        status = self.seat_map.get_seat(row, col)
 
        print()
        if status == 'F':
            print(f"    ✓  Seat {row}{col_letter} is AVAILABLE.")
        elif status == 'X':
            print(f"    ✗  Position {row}{col_letter} is the AISLE.")
        elif status == 'S':
            print(f"    ✗  Position {row}{col_letter} is STORAGE.")
        else:
            print(f"    ✗  Seat {row}{col_letter} is RESERVED.")
            print(f"       Reference: {status}")
            # Fetch the matching passenger record from the database
            record = self.db.get_booking(status)
            if record:
                print(f"       Passenger: {record[2]} {record[3]}")
                print(f"       Passport : {record[1]}")
 
    def book_seat(self):
        """
        Part B Task 2 — Option 2: Book a seat.
 
        Steps:
          1. Ask for seat location and validate it is free.
          2. Ask for passenger details (passport, names).
          3. Generate a unique 8-char reference.
          4. Store the reference in the seat grid.
          5. Save all passenger details + reference to database.
          6. Confirm the booking to the user.
 
        The grid and database are always updated together so
        they stay in sync throughout the session.
        """
        print("\n  ── BOOK A SEAT ──────────────────────────────────")
 
        # Step 1: Get and validate the seat location
        result = self._ask_for_seat()
        if result is None:
            print("    Cancelled.")
            return
 
        row, col = result
        col_letter = self.seat_map.index_to_letter[col]
 
        if not self.seat_map.is_valid_seat(row, col):
            print(f"\n    ✗  {row}{col_letter} is not a bookable seat.")
            return
 
        if not self.seat_map.is_free(row, col):
            existing = self.seat_map.get_seat(row, col)
            print(f"\n    ✗  Seat {row}{col_letter} is already RESERVED.")
            print(f"       Existing reference: {existing}")
            return
 
        # Step 2: Collect passenger details for the database
        print("\n    Please enter passenger details:")
        passenger = self._ask_for_passenger_details()
        if passenger is None:
            print("    Cancelled — no booking made.")
            return
 
        passport, first_name, last_name = passenger
 
        # Step 3: Generate a unique 8-character booking reference
        # The while loop in generate() guarantees uniqueness
        ref = self.ref_gen.generate()
 
        # Step 4: Store the reference in the seat grid
        # This visually marks the seat as reserved on the map
        self.seat_map.set_seat(row, col, ref)
 
        # Step 5: Save the full booking record to the database
        # Both the grid and database are now updated together
        self.db.add_booking(
            reference  = ref,
            passport   = passport,
            first_name = first_name,
            last_name  = last_name,
            seat_row   = row,
            seat_col   = col_letter
        )
 
        # Step 6: Confirm the successful booking
        print(f"\n    ✓  Seat {row}{col_letter} booked successfully.")
        print(f"       Passenger   : {first_name} {last_name}")
        print(f"       Passport    : {passport}")
        print(f"       Booking ref : {ref}")
        print("       Save this reference to cancel your booking.")
 
    def free_seat(self):
        """
        Part B Task 2 — Option 3: Free a seat (cancel booking).
 
        Steps:
          1. Ask for the seat location.
          2. Verify the seat is currently reserved.
          3. Ask the user to enter their booking reference.
          4. If the reference matches:
               a. Set the seat back to 'F' in the grid.
               b. Delete the matching record from the database.
          5. If the reference does NOT match: deny the request.
 
        The grid and database are updated together to stay
        in sync. If one fails, neither is changed.
        """
        print("\n  ── FREE A SEAT  (Cancel Booking) ────────────────")
 
        result = self._ask_for_seat()
        if result is None:
            print("    Cancelled.")
            return
 
        row, col = result
        col_letter = self.seat_map.index_to_letter[col]
 
        if not self.seat_map.is_valid_seat(row, col):
            print(f"\n    ✗  Position {row}{col_letter} is not a seat.")
            return
 
        if self.seat_map.is_free(row, col):
            print(f"\n    ✗  Seat {row}{col_letter} is already FREE.")
            return
 
        # Ask the user to provide their booking reference
        stored_ref  = self.seat_map.get_seat(row, col)
        entered_ref = input(
            "    Enter your booking reference: ").strip().upper()
 
        if entered_ref == stored_ref:
            # Reference matches — update grid and database together
            self.seat_map.set_seat(row, col, 'F')   # free the seat
            self.db.remove_booking(stored_ref)       # delete DB record
 
            print(f"\n    ✓  Seat {row}{col_letter} is now FREE.")
            print(f"       Booking {stored_ref} cancelled.")
            print("       Passenger record removed from database.")
        else:
            # Wrong reference — leave everything unchanged
            print("\n    ✗  Incorrect reference. Cancellation denied.")
 
    def show_booking_status(self):
        """
        Option 4: Display the full cabin map and seat counts.
        No changes made to the grid or database.
        """
        print("\n  ── FULL BOOKING STATUS ──────────────────────────")
        self.seat_map.display()
 
        free_count = reserved_count = 0
        for row in self.seat_map.grid:
            for seat in row:
                if seat == 'F':
                    free_count += 1
                elif seat not in ('X', 'S'):
                    reserved_count += 1
 
        print(f"    Free seats    : {free_count}")
        print(f"    Reserved seats: {reserved_count}")
        print(f"    Total seats   : {free_count + reserved_count}")
        print()
 
    def show_window_seats(self):
        """
        Option 5: List all currently free window seats.
        Window seats are the outermost columns:
          Rows 1-2:  A (index 0) and E (index 4)
          Rows 3-30: A (index 0) and F (index 6)
        """
        print("\n  ── AVAILABLE WINDOW SEATS ───────────────────────")
        print("    Window seats = outermost seat on each side.")
        print()
        found = False
        for row_idx in range(1, 31):
            wcols = [0, 4] if row_idx <= 2 else [0, 6]
            for col_idx in wcols:
                if self.seat_map.is_free(row_idx, col_idx):
                    cl = self.seat_map.index_to_letter[col_idx]
                    sec = ("First Class" if row_idx <= 2
                           else "Business" if row_idx <= 7
                           else "Economy")
                    print(f"    ✓  Row {row_idx:2}  Seat {cl}"
                          f"  —  {sec}")
                    found = True
        if not found:
            print("    ✗  No window seats currently available.")
        print()
 
    def view_all_bookings(self):
        """
        Option 6 (NEW in Part B): View all bookings from database.
 
        Retrieves every record from the bookings table and
        displays it in a neat table format. This proves the
        database is correctly storing and retrieving data.
        """
        print("\n  ── ALL BOOKINGS IN DATABASE ─────────────────────")
        records = self.db.get_all_bookings()
 
        if not records:
            print("    No bookings in the database yet.")
            print()
            return
 
        # Print formatted table header
        print()
        print(f"    {'Reference':<10} {'Passport':<12} "
              f"{'First Name':<12} {'Last Name':<12} {'Seat'}")
        print("    " + "─" * 56)
 
        # Print each booking record on its own line
        for rec in records:
            ref, passport, first, last, seat_row, seat_col = rec
            seat = f"{seat_row}{seat_col}"
            print(f"    {ref:<10} {passport:<12} "
                  f"{first:<12} {last:<12} {seat}")
 
        print()
        print(f"    Total bookings: {len(records)}")
        print()
 
    def close_database(self):
        """Closes the database connection cleanly on exit."""
        self.db.close()
 
 
#  CLASS 5 — Menu
#  Displays the menu and routes user choices to BookingSystem
class Menu:
    """
    Manages the user interface for the Part B program.
 
    Menu options:
      1. Check availability of a seat
      2. Book a seat  (now collects passenger details + DB)
      3. Free a seat  (now also removes DB record)
      4. Show full booking status
      5. Show available window seats
      6. View all bookings from database  (NEW in Part B)
      7. Exit program
    """
 
    def __init__(self):
        """Creates the BookingSystem for the whole session."""
        self.system = BookingSystem()
 
    def _print_menu(self):
        """Prints all 7 menu options."""
        print()
        print("  ╔══════════════════════════════════════════════╗")
        print("  ║    APACHE AIRLINES  —  BURAK757 BOOKING     ║")
        print("  ║              Part B — Database Mode          ║")
        print("  ╠══════════════════════════════════════════════╣")
        print("  ║   1.  Check availability of a seat           ║")
        print("  ║   2.  Book a seat                            ║")
        print("  ║   3.  Free a seat  (cancel booking)          ║")
        print("  ║   4.  Show full booking status               ║")
        print("  ║   5.  Show available window seats            ║")
        print("  ║   6.  View all bookings  (database)          ║")
        print("  ║   7.  Exit program                           ║")
        print("  ╚══════════════════════════════════════════════╝")
 
    def run(self):
        """
        Main loop: shows the menu and handles user choices
        until option 7 (Exit) is selected. The database
        connection is closed cleanly before the program ends.
        """
        print()
        print("  ══════════════════════════════════════════════")
        print("    Welcome to Apache Airlines Booking System")
        print("    Burak757 Fleet  —  Part B (Database Mode)")
        print("    Database file: bookings.db")
        print("  ══════════════════════════════════════════════")
 
        running = True
        while running:
            self._print_menu()
            choice = input("  Enter your choice (1-7): ").strip()
 
            if choice == '1':
                self.system.check_availability()
            elif choice == '2':
                self.system.book_seat()
            elif choice == '3':
                self.system.free_seat()
            elif choice == '4':
                self.system.show_booking_status()
            elif choice == '5':
                self.system.show_window_seats()
            elif choice == '6':
                self.system.view_all_bookings()
            elif choice == '7':
                self.system.close_database()
                print()
                print("  Database connection closed cleanly.")
                print("  Thank you for using Apache Airlines.")
                print("  Goodbye!")
                print()
                running = False
            else:
                print("\n  ✗  Please enter a number from 1 to 7.")
 
 
#  PROGRAM ENTRY POINT
if __name__ == "__main__":
    app = Menu()
    app.run()
 
