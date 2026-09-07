import math # para sqrt

# função de estimativa para o A*
# nesse caso usaremos distância euclidiana.
# será utilizada para estimar a distância do inimigo até o jogador

def heuristic(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

def get_neighbors(maze, cell):
    x, y = cell   # c, l

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
        if (0 <= new_x < c and 0 <= new_y < l and maze[new_y][new_x] <= 0):
            neighbors.append((new_x, new_y))

    #retorna vizinhos
    return neighbors

def criarHeap():
    heap = [1] # heap[0] sera usado como ultima posição livre, por isso heap[0] = 1
    return heap

def swap(heap, x, y):
    temp = heap[x] 
    heap[x] = heap[y]
    heap[y] = temp

def shiftup(heap, i):
    if i <= 1:
        return

    pai = i // 2
    if heap[pai] > heap[i]:
        swap(heap, pai, i)
        return shiftup(heap, pai)

def heapfy(heap, i):
    filhoE = i*2
    filhoD = i*2 + 1

    # heap[0] -> ultima posição livre, logo heap[0] - 1 é a ultima posição ocupada
    if filhoE > heap[0] - 1:
        return

    if filhoD > heap[0] - 1:
        if heap[filhoE] < heap[i]:
            swap(heap, i, filhoE)
            return heapfy(heap, filhoE)
        return
    
    if heap[i] > heap[filhoE] or heap[i] > heap[filhoD]:
        if heap[filhoE] <= heap[filhoD]:
            swap(heap, i, filhoE)
            return heapfy(heap, filhoE)
        else:
            swap(heap, i, filhoD)
            return heapfy(heap, filhoD)
    

def inserirHeap(heap, celula, custo):
    ultimo = heap[0]
    heap.append((custo, celula))
    heap[0] = ultimo + 1 # poderia ser ++ tambem
    shiftup(heap, ultimo)

def removerHeap(heap):
    if len(heap) > 1:
        swap(heap, heap[0] - 1, 1)
        valor = heap.pop()
        heap[0] -= 1
        heapfy(heap, 1)
        return valor


def a_star(maze, start, goal):

    # verifica se já está em goal
    if(start == goal):
        return [start]

    # l linhas    
    l = len(maze)
    # c colunas
    c = len(maze[0])

    # gaol 
    gx, gy = goal

    # vê se está dentro do labirinto ou é parede
    if not (0 <= gx < c and 0 <= gy < l) or maze[gy][gx] > 0:
        return []

    h = criarHeap()

    veio_por = {}
    g_score = {start: 0}
    visitados = set()

    inserirHeap(h, start, heuristic(start, goal))

    while h[0] > 1:
        custo, atual = removerHeap(h)

        if atual in visitados:
            continue

        visitados.add(atual)

        #vê se chegou ao objetivo
        if atual == goal:
            caminho = [atual]

            while atual in veio_por:
                atual = veio_por[atual]
                caminho.append(atual)

            caminho.reverse()
            return caminho

        vizinhos = get_neighbors(maze, atual)

        for celulav in vizinhos:
            if celulav in visitados:
                continue

            novo_custo = g_score[atual] + 1 # custo de cada célula é 1

            if novo_custo < g_score.get(celulav, float('inf')):
                veio_por[celulav] = atual
                g_score[celulav] = novo_custo

                f = novo_custo + heuristic(celulav, goal)

                inserirHeap(h, celulav, f)
    return []
    
