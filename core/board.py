"""
board.py — 10×20 grid, collision detection, line clearing, and cascade gravity.

grid[row][col]       stores color_id of the placed block (0 = empty).
piece_grid[row][col] stores the piece_id that owns that cell (0 = no identity).
Row 0 is the top of the board; row ROWS-1 is the floor.

Piece identity lets intact pieces fall as units after a line clear — only cells
that were part of a cleared row lose their coherence and fall independently.
"""
from constants import COLS, ROWS
from piece import Piece


class Board:
    def __init__(self):
        self.grid: list[list[int]]       = [[0] * COLS for _ in range(ROWS)]
        self.piece_grid: list[list[int]] = [[0] * COLS for _ in range(ROWS)]
        self._next_pid: int = 1

    def is_valid(self, piece: Piece, dx: int = 0, dy: int = 0,
                 shape: list[list[int]] | None = None) -> bool:
        """Return True if the piece (optionally offset/rotated) fits on the board.

        dx/dy are trial offsets; shape overrides piece.shape for rotation tests.
        Cells above row 0 (y < 0) are allowed — pieces spawn partially off-screen.
        """
        s = shape if shape is not None else piece.shape
        for row_i, row in enumerate(s):
            for col_i, val in enumerate(row):
                if not val:
                    continue
                nx = piece.x + col_i + dx
                ny = piece.y + row_i + dy
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return False
                if ny >= 0 and self.grid[ny][nx]:
                    return False
        return True

    def place(self, piece: Piece) -> None:
        """Stamp the piece's color IDs into the grid and assign a fresh piece_id."""
        pid = self._next_pid
        self._next_pid += 1
        for row_i, row in enumerate(piece.shape):
            for col_i, val in enumerate(row):
                if val:
                    r = piece.y + row_i
                    c = piece.x + col_i
                    self.grid[r][c]       = val
                    self.piece_grid[r][c] = pid

    def full_rows(self) -> list[int]:
        """Return row indices that are completely filled, without clearing."""
        return [i for i, row in enumerate(self.grid) if all(row)]

    def clear_lines(self) -> int:
        """Remove all full rows, shift remaining rows down, return clear count."""
        full = self.full_rows()
        for i in full:
            self.grid.pop(i)
            self.grid.insert(0, [0] * COLS)
            self.piece_grid.pop(i)
            self.piece_grid.insert(0, [0] * COLS)
        return len(full)

    def ghost_y(self, piece: Piece) -> int:
        """Return the lowest y the piece can occupy without collision (ghost position)."""
        y = piece.y
        while self.is_valid(piece, dy=y - piece.y + 1):
            y += 1
        return y

    def apply_singleton_gravity(self) -> bool:
        """After a row clear, drop only completely isolated blocks.

        A block is a singleton if it has no orthogonally adjacent filled
        neighbours.  Singletons fall independently to the lowest open row in
        their column.  Processed bottom-up so multiple singletons in the same
        column settle in the correct stacking order.
        Returns True if anything moved.
        """
        singletons = []
        for row in range(ROWS):
            for col in range(COLS):
                if not self.grid[row][col]:
                    continue
                isolated = all(
                    not (0 <= row + dr < ROWS and 0 <= col + dc < COLS
                         and self.grid[row + dr][col + dc])
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                )
                if isolated:
                    singletons.append((row, col))

        if not singletons:
            return False

        singletons.sort(reverse=True)   # bottom-up: highest row index first
        moved = False
        for row, col in singletons:
            color  = self.grid[row][col]
            pid    = self.piece_grid[row][col]
            target = row
            while target + 1 < ROWS and not self.grid[target + 1][col]:
                target += 1
            if target != row:
                self.grid[target][col]       = color
                self.piece_grid[target][col] = pid
                self.grid[row][col]          = 0
                self.piece_grid[row][col]    = 0
                moved = True
        return moved

    def apply_block_gravity(self) -> bool:
        """Move every block that has an empty cell directly below it down one row.

        Scans bottom-up so each block only falls one row per call.
        Returns True if anything moved.
        """
        moved = False
        for row in range(ROWS - 2, -1, -1):
            for col in range(COLS):
                if self.grid[row][col] and not self.grid[row + 1][col]:
                    self.grid[row + 1][col]       = self.grid[row][col]
                    self.piece_grid[row + 1][col] = self.piece_grid[row][col]
                    self.grid[row][col]            = 0
                    self.piece_grid[row][col]      = 0
                    moved = True
        return moved

    def apply_block_gravity_from_col(self, min_col: int) -> bool:
        """Like apply_block_gravity but only operates on columns >= min_col.

        Used by the waterfall cascade animation to stagger column-by-column
        settling from right to left.
        Returns True if anything moved.
        """
        moved = False
        for row in range(ROWS - 2, -1, -1):
            for col in range(min_col, COLS):
                if self.grid[row][col] and not self.grid[row + 1][col]:
                    self.grid[row + 1][col]       = self.grid[row][col]
                    self.piece_grid[row + 1][col] = self.piece_grid[row][col]
                    self.grid[row][col]            = 0
                    self.piece_grid[row][col]      = 0
                    moved = True
        return moved

    def settle_blocks(self) -> bool:
        """Apply block gravity repeatedly until the board is fully settled.

        Returns True if anything moved (i.e. floating blocks existed).
        """
        moved_any = False
        while self.apply_block_gravity():
            moved_any = True
        return moved_any

    def broken_pids_in_rows(self, rows: list[int]) -> set:
        """Return piece IDs that have any cell in the given rows."""
        result = set()
        for r in rows:
            for c in range(COLS):
                pid = self.piece_grid[r][c]
                if pid:
                    result.add(pid)
        return result

    def apply_piece_gravity(self, broken_ids: set) -> bool:
        """One gravity step that preserves intact piece shapes.

        Intact pieces (piece_id not in broken_ids and non-zero) fall as rigid
        units — the whole piece only moves if EVERY cell has clear space below.
        Broken/unidentified cells (piece_id in broken_ids or 0) fall individually.

        Processes pieces bottom-first so a lower piece clears the way for the
        piece above it within the same step.
        Returns True if anything moved.
        """
        intact: dict[int, list[tuple[int, int]]] = {}
        broken_cells: list[tuple[int, int]] = []

        for row in range(ROWS):
            for col in range(COLS):
                if not self.grid[row][col]:
                    continue
                pid = self.piece_grid[row][col]
                if pid == 0 or pid in broken_ids:
                    broken_cells.append((row, col))
                else:
                    intact.setdefault(pid, []).append((row, col))

        moved = False

        # Move intact pieces bottom-first so lower pieces vacate space for those above.
        for pid, cells in sorted(intact.items(), key=lambda kv: -max(r for r, c in kv[1])):
            can_fall = all(
                r + 1 < ROWS and (self.grid[r + 1][c] == 0
                                  or self.piece_grid[r + 1][c] == pid)
                for r, c in cells
            )
            if can_fall:
                for r, c in sorted(cells, key=lambda x: -x[0]):   # bottom-up within piece
                    self.grid[r + 1][c]       = self.grid[r][c]
                    self.piece_grid[r + 1][c] = self.piece_grid[r][c]
                    self.grid[r][c]            = 0
                    self.piece_grid[r][c]      = 0
                moved = True

        # Move broken/unidentified cells individually, bottom-first.
        for r, c in sorted(broken_cells, reverse=True):
            if r + 1 < ROWS and self.grid[r + 1][c] == 0:
                self.grid[r + 1][c]       = self.grid[r][c]
                self.piece_grid[r + 1][c] = self.piece_grid[r][c]
                self.grid[r][c]            = 0
                self.piece_grid[r][c]      = 0
                moved = True

        return moved

    def settle_piece_gravity(self, broken_ids: set) -> None:
        """Apply piece-coherent gravity repeatedly until the board is fully settled."""
        while self.apply_piece_gravity(broken_ids):
            pass

    def remove_color(self, color_id: int) -> list:
        """Remove every cell of color_id from the board.

        Returns a list of (col, row, color_id) tuples for particle spawning.
        """
        removed = []
        for row in range(ROWS):
            for col in range(COLS):
                if self.grid[row][col] == color_id:
                    removed.append((col, row, color_id))
                    self.grid[row][col]       = 0
                    self.piece_grid[row][col] = 0
        return removed
