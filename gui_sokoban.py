#!/usr/bin/env python3
"""
Colab-friendly Sokoban GUI.

This replaces Tkinter with an in-notebook renderer (PIL + matplotlib) and ipywidgets controls.
It preserves the original gameplay/solver integration:
- Warehouse loading
- Move player with box pushing rules
- Show box weights
- Call solve_weighted_sokoban and step/play the returned plan

Run in Google Colab / Jupyter.
"""

import os
import time
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List, Union

from sokoban import Warehouse

try:
    from fredSokobanSolver import solve_weighted_sokoban
    print("Using Fred's solver")
except ModuleNotFoundError:
    from mySokobanSolver import solve_weighted_sokoban
    print("Using submitted solver")

# Notebook UI/Rendering
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from IPython.display import display, clear_output
import ipywidgets as widgets

__author__ = "Frederic Maire (original), Colab adaptation"
__version__ = "2.0-colab"


# Move actions
direction_offset = {
    "Left": (-1, 0),
    "Right": (1, 0),
    "Up": (0, -1),
    "Down": (0, 1),
}

CELL_SIZE = 50  # pixels, like original


@dataclass
class Assets:
    tiles: Dict[str, Image.Image]
    font: Optional[ImageFont.ImageFont]


def _load_assets(app_root_folder: str) -> Assets:
    """
    Load the original gif assets using PIL. If missing, create simple placeholders.
    """
    def load_gif(path: str, fallback_color: Tuple[int, int, int], label: str) -> Image.Image:
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            # Some gifs might be larger/smaller; normalize to CELL_SIZE
            if img.size != (CELL_SIZE, CELL_SIZE):
                img = img.resize((CELL_SIZE, CELL_SIZE))
            return img
        # fallback placeholder
        img = Image.new("RGBA", (CELL_SIZE, CELL_SIZE), fallback_color + (255,))
        d = ImageDraw.Draw(img)
        d.text((4, 16), label[:6], fill=(0, 0, 0, 255))
        return img

    images_dir = os.path.join(app_root_folder, "images")

    tiles = {
        "wall": load_gif(os.path.join(images_dir, "wall.gif"), (120, 120, 120), "wall"),
        "target": load_gif(os.path.join(images_dir, "hole.gif"), (240, 220, 120), "tgt"),
        "box_on_target": load_gif(os.path.join(images_dir, "crate-in-hole.gif"), (200, 150, 80), "b@t"),
        "box": load_gif(os.path.join(images_dir, "crate.gif"), (200, 150, 80), "box"),
        "worker": load_gif(os.path.join(images_dir, "player.gif"), (120, 180, 255), "me"),
        "smiley": load_gif(os.path.join(images_dir, "smiley.gif"), (255, 255, 120), ":)"),
        "worker_on_target": load_gif(os.path.join(images_dir, "player-in-hole.gif"), (120, 180, 255), "me@t"),
    }

    # Try to get a reasonable font; fall back to default
    font = None
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

    return Assets(tiles=tiles, font=font)


class SokobanColabGUI:
    def __init__(self, app_root_folder: Optional[str] = None):
        self.app_root_folder = app_root_folder or os.getcwd()
        self.assets = _load_assets(self.app_root_folder)

        self.warehouse_path: Optional[str] = None
        self.warehouse: Optional[Warehouse] = None

        # solution is either None, 'Impossible', or list[str]
        self.solution: Optional[Union[str, List[str]]] = None
        self.total_cost: Optional[float] = None

        # UI widgets
        self.out = widgets.Output()
        self.status = widgets.HTML()

        self.path_box = widgets.Text(
            description="Warehouse:",
            placeholder="e.g. warehouses/warehouse_01.txt",
            layout=widgets.Layout(width="650px"),
        )
        self.load_btn = widgets.Button(description="Load", button_style="primary")
        self.reset_btn = widgets.Button(description="Reset (r)", button_style="")
        self.solve_btn = widgets.Button(description="Solve", button_style="warning")
        self.step_btn = widgets.Button(description="Step (s)", button_style="")
        self.play_btn = widgets.Button(description="Play", button_style="success")
        self.stop_btn = widgets.Button(description="Stop", button_style="danger")

        self.left_btn = widgets.Button(description="←")
        self.right_btn = widgets.Button(description="→")
        self.up_btn = widgets.Button(description="↑")
        self.down_btn = widgets.Button(description="↓")

        self.speed = widgets.IntSlider(description="Delay ms", min=50, max=1000, step=50, value=300)

        self._playing = False

        # Wire events
        self.load_btn.on_click(lambda _b: self.load_warehouse(self.path_box.value.strip() or None))
        self.reset_btn.on_click(lambda _b: self.reset_level())
        self.solve_btn.on_click(lambda _b: self.solve_puzzle())
        self.step_btn.on_click(lambda _b: self.step_solution())
        self.play_btn.on_click(lambda _b: self.play_solution())
        self.stop_btn.on_click(lambda _b: self.stop())

        self.left_btn.on_click(lambda _b: self.move_player("Left"))
        self.right_btn.on_click(lambda _b: self.move_player("Right"))
        self.up_btn.on_click(lambda _b: self.move_player("Up"))
        self.down_btn.on_click(lambda _b: self.move_player("Down"))

    # ----------------------------
    # Core game logic (ported)
    # ----------------------------

    def get_box_weight(self, x: int, y: int) -> int:
        """
        Get the weight of the box at position (x,y) in the current warehouse.
        If no weight given return 0.
        """
        if not self.warehouse:
            return 0
        try:
            return self.warehouse.weights[self.warehouse.boxes.index((x, y))]
        except Exception:
            return 0

    def load_warehouse(self, warehouse_path: Optional[str]):
        if not warehouse_path:
            self._set_status("Provide a warehouse path (relative to repo or absolute path).", error=True)
            return

        self.warehouse_path = warehouse_path
        w = Warehouse()
        w.load_warehouse(warehouse_path)
        self.warehouse = w
        self.solution = None
        self.total_cost = None
        self._set_status(f"Loaded: {warehouse_path}")
        self.render()

    def reset_level(self):
        if not self.warehouse_path:
            self._set_status("Nothing to reset: load a warehouse first.", error=True)
            return
        self.load_warehouse(self.warehouse_path)

    def try_move_box(self, location: Tuple[int, int], next_location: Tuple[int, int]) -> bool:
        """
        Move the box from 'location' to 'next_location' if possible.
        Return True if moved else False.
        """
        assert self.warehouse is not None
        x, y = location
        nx, ny = next_location

        assert (x, y) in self.warehouse.boxes
        if (nx, ny) not in self.warehouse.walls and (nx, ny) not in self.warehouse.boxes:
            bi = self.warehouse.boxes.index((x, y))
            self.warehouse.boxes[bi] = (nx, ny)
            return True
        return False

    def move_player(self, direction: str):
        if not self.warehouse:
            self._set_status("Load a warehouse first.", error=True)
            return
        if direction not in direction_offset:
            return

        x, y = self.warehouse.worker
        dx, dy = direction_offset[direction]
        nx, ny = x + dx, y + dy

        # blocked by wall
        if (nx, ny) in self.warehouse.walls:
            return

        # pushing a box?
        if (nx, ny) in self.warehouse.boxes:
            if not self.try_move_box((nx, ny), (nx + dx, ny + dy)):
                return

        self.warehouse.worker = (nx, ny)
        self.render()

    def puzzle_solved(self) -> bool:
        if not self.warehouse:
            return False
        return all(b in self.warehouse.targets for b in self.warehouse.boxes)

    # ----------------------------
    # Solver integration
    # ----------------------------

    def solve_puzzle(self):
        if not self.warehouse:
            self._set_status("First load a warehouse.", error=True)
            return

        self._set_status("Starting to think...")
        t0 = time.time()
        solution, total_cost = solve_weighted_sokoban(self.warehouse)
        t1 = time.time()

        self.solution = solution
        self.total_cost = total_cost

        if solution == "Impossible":
            self._set_status(f"No solution found. (analysis {t1 - t0:.6f}s)", error=True)
        else:
            self._set_status(f"Solution found. cost={total_cost} (analysis {t1 - t0:.6f}s), steps={len(solution)}")
        self.render()

    def step_solution(self):
        if not self.solution or self.solution == "Impossible":
            return
        if isinstance(self.solution, list) and len(self.solution) > 0:
            step = self.solution.pop(0)
            self.move_player(step)

    def play_solution(self):
        if not self.solution or self.solution == "Impossible":
            return
        self._playing = True
        while self._playing and isinstance(self.solution, list) and len(self.solution) > 0:
            self.step_solution()
            time.sleep(self.speed.value / 1000.0)
        self._playing = False

    def stop(self):
        self._playing = False

    # ----------------------------
    # Rendering (board -> image)
    # ----------------------------

    def _set_status(self, msg: str, error: bool = False):
        color = "#b00020" if error else "#1b5e20"
        self.status.value = f"<b>Status:</b> <span style='color:{color}'>{msg}</span>"

    def render(self):
        with self.out:
            clear_output(wait=True)
            if not self.warehouse:
                print("Welcome to Sokoban (Colab edition).\nLoad a warehouse to begin.")
                return

            w = self.warehouse
            img = Image.new("RGBA", (w.ncols * CELL_SIZE, w.nrows * CELL_SIZE), (255, 255, 255, 255))

            # Base: blank -> draw targets -> walls -> boxes -> worker
            # (Order chosen to mimic original look.)
            for (x, y) in w.targets:
                img.alpha_composite(self.assets.tiles["target"], (x * CELL_SIZE, y * CELL_SIZE))

            for (x, y) in w.walls:
                img.alpha_composite(self.assets.tiles["wall"], (x * CELL_SIZE, y * CELL_SIZE))

            # Boxes
            for (x, y) in w.boxes:
                tile_key = "box_on_target" if (x, y) in w.targets else "box"
                img.alpha_composite(self.assets.tiles[tile_key], (x * CELL_SIZE, y * CELL_SIZE))

                # Weight overlay
                weight = self.get_box_weight(x, y)
                if weight and self.assets.font:
                    d = ImageDraw.Draw(img)
                    d.text(
                        (x * CELL_SIZE + 18, y * CELL_SIZE + 15),
                        str(weight),
                        fill=(0, 0, 0, 255),
                        font=self.assets.font,
                    )

            # Worker / solved smiley
            wx, wy = w.worker
            if self.puzzle_solved():
                img.alpha_composite(self.assets.tiles["smiley"], (wx * CELL_SIZE, wy * CELL_SIZE))
            else:
                tile_key = "worker_on_target" if (wx, wy) in w.targets else "worker"
                img.alpha_composite(self.assets.tiles[tile_key], (wx * CELL_SIZE, wy * CELL_SIZE))

            # Show
            plt.figure(figsize=(w.ncols * 0.55, w.nrows * 0.55))
            plt.imshow(img)
            plt.axis("off")
            plt.show()

            # Some extra info
            if self.solution == "Impossible":
                print("Solver: Impossible")
            elif isinstance(self.solution, list):
                print(f"Solver: {len(self.solution)} remaining steps. (press Step/Play)")
            else:
                print("Solver: not run yet.")

    # ----------------------------
    # Display UI
    # ----------------------------

    def show(self):
        controls_top = widgets.HBox([self.path_box, self.load_btn, self.reset_btn])
        controls_solver = widgets.HBox([self.solve_btn, self.step_btn, self.play_btn, self.stop_btn, self.speed])
        controls_moves = widgets.HBox([self.up_btn, self.left_btn, self.down_btn, self.right_btn])
        ui = widgets.VBox([self.status, controls_top, controls_solver, controls_moves, self.out])

        self._set_status("Ready. Enter a warehouse path and click Load.")
        display(ui)
        self.render()


# Convenience entry point
def launch_colab_gui(app_root_folder: Optional[str] = None, warehouse_path: Optional[str] = None):
    gui = SokobanColabGUI(app_root_folder=app_root_folder)
    gui.show()
    if warehouse_path:
        gui.path_box.value = warehouse_path
        gui.load_warehouse(warehouse_path)
    return gui
