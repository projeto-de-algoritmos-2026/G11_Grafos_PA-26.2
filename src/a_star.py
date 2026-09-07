import heapq # biblioteca para heap
import math # para sqrt

# função de estimativa para o A*
# nesse caso usaremos distância euclidiana.
# será utilizada para estimar a distância do inimigo até o jogador

def heuristic(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

def get_neighbors(maze, cell):
    x, y = cell   # l, c

    # l linhas    
    l = len(maze)
    # c colunas
    c = len(maze[0])

    #vetor para guardar vizinhos válidos
    neighbors = []

    # para cada direção, verifica se célula é valida e se sim adiciona a lista de vizinhos
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        new_x = x + dx
        new_y = y + dy
        if (0 <= new_x < l and 0 <= new_y < c and maze[new_x][new_y] <= 0):
            neighbors.append((new_x, new_y))

    #retorna vizinhos
    return neighbors

def a_star(maze, start, goal):

    # verifica se já está em goal
    if(start == goal):
        return [start]

    # m colunas
    c = len(maze[0])
    # n linhas
    l = len(maze)

    # gaol 
    gx, gy = goal

    # vê se está dentro do labirinto
    if not (0 <= gx < c and 0 <= gy < l) or maze[gy][gx] > 0:
        return []

    
#TODO: finalizar implementação do algoritmo A estrela

