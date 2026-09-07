from random import randint, choice

def neighbors(maze, X, Y, n, m):
    # returns unvisited neighbors of a cell at pos X, Y
    N = []
    for x, y, count in [(X, Y-1, 0), (X+1, Y, 1), (X, Y+1, 2), (X-1, Y, 3)]:
        if 0 <= x < m and 0 <= y < n and not maze[y][x][4]:
            N.append([(x, y), count]) # position in the maze, neighbor index
    return N

def gen(n, m):
    # generates a maze with n lines and m columns

    # [N, E, S, W, cell value]
    maze = [[[1, 1, 1, 1, 0] for _ in range(m)] for _ in range(n)]
    maze[0][0][3] = maze[n-1][m-1][1] = 0 # open goal

    # push a random cell in the stack
    free = [(x, y) for x in range(m) for y in range(n) if not maze[y][x][4]]
    pos = choice(free) # current cell
    stack = [pos] # previously visited cells

    while len(stack):
        x, y = pos
        maze[y][x][4] = 1 # cell has been visited

        # get unvisited neighbors
        N = neighbors(maze, x, y, n, m)
        if len(N):
            # mark this cell as visited
            maze[y][x][4] = 1

            # if neighbors, choose a random one and open the way
            pos_, index = choice(N)
            x_, y_ = pos_
            index_ = {0: 2, 1: 3, 2: 0, 3: 1}[index]
            maze[y][x][index] = 0
            maze[y_][x_][index_] = 0

            # add the current pos to the stack and continue with the neighbor
            stack.append(pos)
            pos = (x_, y_)
        else:
            # go back to the previous cell if not free neighbors
            pos = stack.pop()

    return maze

def to_blocks(maze, max_wall):
    # convert a maze with walls to an array of 1s or 0s
    new = []
    m, n = len(maze[0])*2 + 1, len(maze)*2 + 1
    for y in range(n):
        new.append([])
        for x in range(m):
            if x%2 and y%2:
                new[-1].append(0) # maze cells
            elif not x%2 and not y%2: # corner touching 4 cells
                new[-1].append(1)
            elif x%2: # horizontal walls
                if y == n-1: # bottom wall
                    new[-1].append(maze[y//2 - 1][x//2][2])
                else: # use top walls of cells
                    new[-1].append(maze[y//2][x//2][0])
            else: # vertical walls
                if x == m-1: # right wall
                    new[-1].append(maze[y//2][x//2 - 1][1])
                else: # use left walls of cells
                    new[-1].append(maze[y//2][x//2][3])

    # attibute random values to choose textures
    for y in range(n):
        for x in range(m):
            if new[y][x] == 1:
                # random texture
                value = 0
                again = True
                while again and value < max_wall:
                    value += 1
                    again = not randint(0, 3)
                new[y][x] = value
            elif (x, y) not in  [(0, 1), (1, 1)]:
                # random mob
                if not randint(0, 8):
                    if randint(0, 2):
                        new[y][x] = -1
                    else:
                        new[y][x] = -2
    return new
