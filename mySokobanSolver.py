
'''

    Sokoban Assignment Group 37 2026 Semester 1


The functions and classes defined in this module will be called by a marker script. 
You should complete the functions and classes according to their specified interfaces.

No partial marks will be awarded for functions that do not meet the specifications
of the interfaces.

You are NOT allowed to change the defined interfaces.
In other words, you must fully adhere to the specifications of the 
functions, their arguments and returned values.
Changing the interfacce of a function will likely result in a fail 
for the test of your code. This is not negotiable! 

You have to make sure that your code works with the files provided 
(search.py and sokoban.py) as your code will be tested 
with the original copies of these files. 

Last modified by 2021-08-17  by f.maire@qut.edu.au
- clarifiy some comments, rename some functions
  (and hopefully didn't introduce any bug!)

'''

# You have to make sure that your code works with 
# the files provided (search.py and sokoban.py) as your code will be tested 
# with these files
import search
import sokoban


# Dictionary of legal movement directions.
DIRECTIONS = {
    'Left': (-1, 0),
    'Right': (1, 0),
    'Up': (0, -1),
    'Down': (0, 1),
}


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def my_team():
    '''
    Return the list of the team members of this assignment submission as a list
    of triplet of the form (student_number, first_name, last_name)
    
    '''
#    return [ (1234567, 'Ada', 'Lovelace'), (1234568, 'Grace', 'Hopper'), (1234569, 'Eva', 'Tardos') ]
    raise NotImplementedError()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# Helpwer functions

def _board_size_from_walls(walls):
    '''
    Compute board width and height from wall coordinates.

    @param walls : list[tuple[int, int]] | set[tuple[int, int]]
        Wall positions.

    @param return: tuple[int, int]
        (width, height)
    '''
    max_x = 0
    max_y = 0

    for x, y in walls:
        if x > max_x:
            max_x = x
        if y > max_y:
            max_y = y

    return max_x + 1, max_y + 1


def _is_corner(cell, wall_set):
    '''
    Check if a cell is a corner using wall adjacency.

    A corner means one horizontal wall and one vertical wall around the cell.

    @param cell : tuple[int, int]
        Candidate position.

    @ param wall_set : set[tuple[int, int]]
        All wall positions.

    @ return bool
        True if corner, else False.
    '''
    x, y = cell

    wall_left = (x - 1, y) in wall_set
    wall_right = (x + 1, y) in wall_set
    wall_up = (x, y - 1) in wall_set
    wall_down = (x, y + 1) in wall_set

    # Four possible corner types.
    if wall_left and wall_up:
        return True
    if wall_left and wall_down:
        return True
    if wall_right and wall_up:
        return True
    if wall_right and wall_down:
        return True

    return False


def _simple_inside_cells(warehouse):
    '''
    Compute "inside" cells using a simple row scan approach.

    This method is intentionally simple: for each row, cells between the first
    and last wall in that row are considered inside (except wall cells).

    @param warehouse: sokoban.Warehouse
        Warehouse object.

    @return: set[tuple[int, int]]
        Candidate inside non-wall cells.
    '''
    wall_set = set(warehouse.walls)
    width, height = _board_size_from_walls(wall_set)

    inside = set()

    # Scan each row and keep cells between first and last wall.
    for y in range(height):
        wall_x_values = [x for x, wy in wall_set if wy == y]
        if len(wall_x_values) < 2:
            continue

        left_wall = min(wall_x_values)
        right_wall = max(wall_x_values)

        for x in range(left_wall + 1, right_wall):
            if (x, y) not in wall_set:
                inside.add((x, y))

    return inside


def _taboo_coordinates(warehouse):
    '''
    Find taboo cells using Rule 1 and Rule 2 from the assignment.

    Rule 1: non-target corners are taboo.
    Rule 2: cells between two corners are taboo if they lie along one wall
            and there are no targets between those corners.

    @param warehouse: a Warehouse object

    @return: set[tuple[int, int]]
        Taboo cell coordinates.
    '''
    wall_set = set(warehouse.walls)
    target_set = set(warehouse.targets)
    inside_set = _simple_inside_cells(warehouse)

    # Rule 1: find all corner cells that are not targets.
    corners = []
    for cell in inside_set:
        if cell in target_set:
            continue
        if _is_corner(cell, wall_set):
            corners.append(cell)

    taboo = set(corners)

    # Rule 2 horizontal checks.
    for i in range(len(corners)):
        x1, y1 = corners[i]
        for j in range(i + 1, len(corners)):
            x2, y2 = corners[j]

            # Must be in same row.
            if y1 != y2:
                continue

            start_x = min(x1, x2)
            end_x = max(x1, x2)

            # Need at least one cell between corners.
            if end_x - start_x <= 1:
                continue

            between = []
            valid_segment = True

            # Build list of cells between corners and validate quickly.
            for x in range(start_x + 1, end_x):
                c = (x, y1)
                between.append(c)

                # All between cells must be inside and not targets.
                if c not in inside_set:
                    valid_segment = False
                    break
                if c in target_set:
                    valid_segment = False
                    break

            if not valid_segment:
                continue

            # At least one full side must be wall along the whole segment.
            wall_above = True
            wall_below = True

            for x in range(start_x, end_x + 1):
                if (x, y1 - 1) not in wall_set:
                    wall_above = False
                if (x, y1 + 1) not in wall_set:
                    wall_below = False

            if wall_above or wall_below:
                for c in between:
                    taboo.add(c)

    # Rule 2 vertical checks.
    for i in range(len(corners)):
        x1, y1 = corners[i]
        for j in range(i + 1, len(corners)):
            x2, y2 = corners[j]

            # Must be in same column.
            if x1 != x2:
                continue

            start_y = min(y1, y2)
            end_y = max(y1, y2)

            if end_y - start_y <= 1:
                continue

            between = []
            valid_segment = True

            for y in range(start_y + 1, end_y):
                c = (x1, y)
                between.append(c)

                if c not in inside_set:
                    valid_segment = False
                    break
                if c in target_set:
                    valid_segment = False
                    break

            if not valid_segment:
                continue

            wall_left = True
            wall_right = True

            for y in range(start_y, end_y + 1):
                if (x1 - 1, y) not in wall_set:
                    wall_left = False
                if (x1 + 1, y) not in wall_set:
                    wall_right = False

            if wall_left or wall_right:
                for c in between:
                    taboo.add(c)

    return taboo


def taboo_cells(warehouse):
    '''  
    Identify the taboo cells of a warehouse. A "taboo cell" is by definition
    a cell inside a warehouse such that whenever a box get pushed on such 
    a cell then the puzzle becomes unsolvable. 
    
    Cells outside the warehouse are not taboo. It is a fail to tag one as taboo.
    
    When determining the taboo cells, you must ignore all the existing boxes, 
    only consider the walls and the target  cells.  
    Use only the following rules to determine the taboo cells;
     Rule 1: if a cell is a corner and not a target, then it is a taboo cell.
     Rule 2: all the cells between two corners along a wall are taboo if none of 
             these cells is a target.
    
    @param warehouse: 
        a Warehouse object with a worker inside the warehouse

    @return
       A string representing the warehouse with only the wall cells marked with 
       a '#' and the taboo cells marked with a 'X'.  
       The returned string should NOT have marks for the worker, the targets,
       and the boxes.  
    '''
    wall_set = set(warehouse.walls)
    taboo_set = _taboo_coordinates(warehouse)
    width, height = _board_size_from_walls(wall_set)

    # Start with blank canvas.
    grid = []
    for _ in range(height):
        row = []
        for _ in range(width):
            row.append(' ')
        grid.append(row)

    # Draw taboo cells first.
    for x, y in taboo_set:
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = 'X'

    # Draw walls after so walls are never overwritten.
    for x, y in wall_set:
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = '#'

    return '\n'.join(''.join(row) for row in grid)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class SokobanPuzzle(search.Problem):
    '''
    An instance of the class 'SokobanPuzzle' represents a Sokoban puzzle.
    An instance contains information about the walls, the targets, the boxes
    and the worker.

    Your implementation should be fully compatible with the search functions of 
    the provided module 'search.py'. 
    
    '''

    def __init__(self, warehouse):
        '''
        Build a puzzle instance from an initial warehouse.

        @param warehouse: sokoban.Warehouse
            Starting state.
        '''
        self.walls = set(warehouse.walls)
        self.targets = set(warehouse.targets)
        self.taboo = _taboo_coordinates(warehouse)
        self.box_weights = tuple(warehouse.weights)

        initial_state = (warehouse.worker, tuple(warehouse.boxes))
        super().__init__(initial=initial_state)

    def actions(self, state):
        '''
        Return the list of actions that can be executed in the given state.

        @param state: tuple
            Current state (worker, boxes).

        @return: list[str]
            Legal actions from Left/Right/Up/Down.
        '''
        worker_pos, box_positions = state
        box_set = set(box_positions)
        legal_actions = []

        for action_name, (dx, dy) in DIRECTIONS.items():
            next_worker = (worker_pos[0] + dx, worker_pos[1] + dy)

            # Cannot move into walls.
            if next_worker in self.walls:
                continue

            # If no box in front, move is legal.
            if next_worker not in box_set:
                legal_actions.append(action_name)
                continue

            # If there is a box, attempt push.
            next_box = (next_worker[0] + dx, next_worker[1] + dy)

            # Illegal push into wall or another box.
            if next_box in self.walls:
                continue
            if next_box in box_set:
                continue

            # Avoid pushing into taboo cell unless it is a target.
            if next_box in self.taboo and next_box not in self.targets:
                continue

            legal_actions.append(action_name)

        return legal_actions

    def result(self, state, action):
        '''
        Apply one action to a state and return the new state.

        @param: state : tuple
            Current state (worker, boxes).
        @param action : str
            One action name.

        @return: tuple
            New state.
        '''
        worker_pos, box_positions = state
        dx, dy = DIRECTIONS[action]
        next_worker = (worker_pos[0] + dx, worker_pos[1] + dy)

        # If we moved into a box, push that box by one step.
        if next_worker in box_positions:
            box_index = box_positions.index(next_worker)
            new_boxes = list(box_positions)
            new_boxes[box_index] = (next_worker[0] + dx, next_worker[1] + dy)
            return (next_worker, tuple(new_boxes))

        # Normal worker move.
        return (next_worker, box_positions)

    def goal_test(self, state):
        '''
        Check if every box is on a target.

        @param state : tuple
            Current state.

        @return: bool
            True when solved.
        '''
        _, box_positions = state
        for box in box_positions:
            if box not in self.targets:
                return False
        return True

    def path_cost(self, c, state1, action, state2):
        '''
        Compute step cost for weighted Sokoban.

        Cost model:
        - Move without push: +1
        - Move with push of box i: +1 + weight_i

        @param c : int
            Existing path cost.
        @param state1 : tuple
            Previous state.
        @param action : str
            Action taken.
        @param state2 : tuple
            New state.

        @return: int
            Updated path cost.
        '''
        _, boxes_before = state1
        _, boxes_after = state2

        # No box changed => simple worker move.
        if boxes_before == boxes_after:
            return c + 1

        # Find which box moved to get its weight.
        moved_index = None
        for i in range(len(boxes_before)):
            if boxes_before[i] != boxes_after[i]:
                moved_index = i
                break

        if moved_index is None:
            return c + 1

        return c + 1 + self.box_weights[moved_index]

    def heuristic(self, state):
        '''
        Very simple heuristic (admissible, not strong):
        sum of Manhattan distances from each box to its nearest target.

        @param state : tuple
            Current state.

        @return: int
            Heuristic value.
        '''
        _, box_positions = state

        total = 0
        for box_x, box_y in box_positions:
            min_distance = None

            for target_x, target_y in self.targets:
                distance = abs(box_x - target_x) + abs(box_y - target_y)
                if min_distance is None or distance < min_distance:
                    min_distance = distance

            if min_distance is not None:
                total += min_distance

        return total


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def check_elem_action_seq(warehouse, action_seq):
    '''
    
    Determine if the sequence of actions listed in 'action_seq' is legal or not.
    
    Important notes:
      - a legal sequence of actions does not necessarily solve the puzzle.
      - an action is legal even if it pushes a box onto a taboo cell.
        
    @param warehouse: a valid Warehouse object

    @param action_seq: a sequence of legal actions.
           For example, ['Left', 'Down', Down','Right', 'Up', 'Down']
           
    @return
        The string 'Impossible', if one of the action was not valid.
           For example, if the agent tries to push two boxes at the same time,
                        or push a box into a wall.
        Otherwise, if all actions were successful, return                 
               A string representing the state of the puzzle after applying
               the sequence of actions.  This must be the same string as the
               string returned by the method  Warehouse.__str__()
    '''

    worker_pos = warehouse.worker
    box_positions = list(warehouse.boxes)
    box_set = set(box_positions)
    wall_set = set(warehouse.walls)

    for action_name in action_seq:
        if action_name not in DIRECTIONS:
            return 'Impossible'

        dx, dy = DIRECTIONS[action_name]
        next_worker = (worker_pos[0] + dx, worker_pos[1] + dy)

        # Worker cannot walk into a wall.
        if next_worker in wall_set:
            return 'Impossible'

        # If worker touches a box, that box must be pushable.
        if next_worker in box_set:
            next_box = (next_worker[0] + dx, next_worker[1] + dy)

            if next_box in wall_set:
                return 'Impossible'
            if next_box in box_set:
                return 'Impossible'

            # Move the box in both list and set representations.
            box_index = box_positions.index(next_worker)
            box_positions[box_index] = next_box
            box_set.remove(next_worker)
            box_set.add(next_box)

        # Update worker position.
        worker_pos = next_worker

    # Build final warehouse string without mutating original object.
    final_warehouse = warehouse.copy(worker=worker_pos, boxes=box_positions)
    return str(final_warehouse)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def solve_weighted_sokoban(warehouse):
    '''
    This function analyses the given warehouse.
    It returns the two items. The first item is an action sequence solution. 
    The second item is the total cost of this action sequence.
    
    @param 
     warehouse: a valid Warehouse object

    @return
    
        If puzzle cannot be solved 
            return 'Impossible', None
        
        If a solution was found, 
            return S, C 
            where S is a list of actions that solves
            the given puzzle coded with 'Left', 'Right', 'Up', 'Down'
            For example, ['Left', 'Down', Down','Right', 'Up', 'Down']
            If the puzzle is already in a goal state, simply return []
            C is the total cost of the action sequence C

    '''
    problem = SokobanPuzzle(warehouse)

    # Early return if puzzle starts solved.
    if problem.goal_test(problem.initial):
        return [], 0

    solution_node = search.astar_graph_search(
        problem,
        h=lambda node: problem.heuristic(node.state)
    )

    if solution_node is None:
        return 'Impossible', None

    return solution_node.solution(), solution_node.path_cost

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
