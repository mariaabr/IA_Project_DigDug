"""Example client."""
import asyncio
import datetime
import getpass
import json
import os

import websockets


dug_path = []

def distance(a, b):
    """Dadas duas posições, digdug e enimigo, calcula a distância entre os dois."""

    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** (1/2)

def get_enemies_pos(state):
    """"Dado o estado atual, calcula a posição do enimigo"""

    #verifica se acabou o nível 
    if len(state["enemies"]) == 0 or "digdug" not in state or len(state["rocks"]) == 0: 
        return [1,1]
    enemies = state['enemies']

    #ordena os inimigos com base na distância ao digdug
    enemies.sort(key=lambda x: distance(x["pos"], state["digdug"]))
    return enemies

def get_rocks_pos(state):
    """"Devolve a posição das rochas no estado state"""

    rocks = []
    for r in state["rocks"]:
        rocks.append(r["pos"])
    return rocks

def set_dug_path(state):
    """Define o caminho escavado do digdug"""

    #Verifica se a posição do digdug está no estado do jogo
    if "digdug" in state:
        digdug_pos = state["digdug"]

        #Adiciona a posição do digdug ao caminho se ainda não tiver sido percorrida
        if digdug_pos not in dug_path:
            dug_path.append(digdug_pos)
    else:
        # se o estado do jogo não possui a posição do digdug(1ºstate)
        # percorre o "map" do estado
        x = 0
        for l in state["map"]:
            y = 0
            for c in l:
                if c == 0:
                    #caso a célula do mapa tenha valor 0, acrescenta ao caminho escavado
                    dug_path.append([x, y]) 
                y += 1
            x += 1

def get_path_to_enemies(state):
    """Devolve os caminhos até aos inimigos"""
    
    enemies_path = []
    enemies = get_enemies_pos(state)
    digdug_pos = state["digdug"]

    #se é [1,1] o nível terminou
    if enemies == [1,1]:
        return [1,1]
    
    #calcula as coordenadas do caminho do digdug, até cada um dos inimigos
    #e retorna a lista dos caminhos até ao inimigos
    for enemy in enemies:
        enemies_path.append([enemy["pos"][0]-digdug_pos[0], enemy["pos"][1]-digdug_pos[1]])
    return enemies_path

def check_if_no_wall(digdug_pos, object):
    """Verifica se existe uma parede ao redor do digdug(não está escavado)"""
    
    #calcula o caminho entre o digdug e o objeto
    path = [object[0]-digdug_pos[0], object[1]-digdug_pos[1]]
    
    #se o movimento é vertical
    if path[0] == 0:
        #verifica as células acima do digdug
        if path[1] > 0:
            for i in range(path[1]):
                if [digdug_pos[0], digdug_pos[1]+i+1] not in dug_path:
                    return False
        #verifica as céĺulas abaixo do digdug
        else:
            for i in range(abs(path[1])):
                if [digdug_pos[0], digdug_pos[1]-i-1] not in dug_path:
                    return False
    #se o movimento é horizontal
    elif path[1] == 0:
        #verifica as células à direita do digdug
        if path[0] > 0:
            for i in range(path[0]):
                if [digdug_pos[0]+i+1, digdug_pos[1]] not in dug_path:
                    return False
        #verifica as células à esquerda do digdug
        else:
            for i in range(abs(path[0])):
                if [digdug_pos[0]-i-1, digdug_pos[1]] not in dug_path:
                    return False
    return True
        
    
def check_possible_fire(enemies, digdug):
    """Dadas as posições dos inimigos e a posição do digdug, verifica se podemos ser atingidos pelo fogo do Fygar"""

    fygars = []
    enemies = reversed(enemies)
    #verifica se são Fygar
    for enemy in enemies:
        if enemy["name"] == "Fygar":
            fygars.append(enemy)
    if len(fygars) == 0:
        return False
    else:
        for Fygar in fygars:
            #se não está na mesma linha do digdug false
            if Fygar["pos"][1] != digdug[1]:
                continue

            #se está na mesma linha
            elif Fygar["pos"][1] == digdug[1]:
                #verifica se está á esquerda
                if Fygar["pos"][0] < digdug[0]:
                    #verifica se o digdug está a 3 ou a menos de 3 de distância do Fygar
                    if abs(digdug[0] - Fygar["pos"][0]) <= 3:
                        #verifica se o Fygar está orientado na direção do digdug
                        if Fygar["dir"] == 1:
                            #verifica se existe parede entre o digdug e o Fygar
                            if check_if_no_wall(digdug, Fygar["pos"]):
                                return True
                        #verifica se está orientado na direção oposta á posição do digdug
                        elif Fygar["dir"] == 3:
                            #verifica se existe parede imediatamente á frente do Fygar
                            if wall_ahead(3, Fygar["pos"]):
                                return True
                        else:
                            if wall_ahead(Fygar["dir"], Fygar["pos"]):
                                return True
                #verifica se está á direita
                elif Fygar["pos"][0] > digdug[0]:
                    if abs(digdug[0] - Fygar["pos"][0]) <= 3:
                        if Fygar["dir"] == 3:
                            if check_if_no_wall(digdug, Fygar["pos"]):
                                return True
                        elif Fygar["dir"] == 1:
                            if wall_ahead(1, Fygar["pos"]):
                                return True
                        else:
                            if wall_ahead(Fygar["dir"], Fygar["pos"]):
                                return True
    return False
                    
                    
def check_if_rocks_in_path(next_pos, rocks):
    """Verifica se existe uma pedra posição seguinte do digdug"""

    if next_pos in rocks:
        return True
    else:
        return False
            
def get_enemy_last_move(closest_enemy_last_pos, closest_enemy_pos):
    """Calcula o último movimento do inimigo com base na posição atual e na posição anterior"""

    #se o jogo terminou a posição será None e devolve [0,0]
    if closest_enemy_pos == None or closest_enemy_last_pos == None:
        return [0,0]
    else:
        return [closest_enemy_pos[0]-closest_enemy_last_pos[0], closest_enemy_pos[1]-closest_enemy_last_pos[1]]
    
def left_is_clear(state, rocks, enemies, enemies_pos):
    """Verifica se há espaço seguro/livre á esquerda do digdug"""

    predicted_enemies_pos = predict_enemies_pos(rocks, enemies)

    #Verifica se não está no limite esquerdo do mapa, 
    # se não há uma rocha a impedir o caminho
    # se não se arrisca a ser morto por um Fygar
    # se não estão inimigos nessa posição
    # e se não estão inimigos previstos nessa posição
    if (state["digdug"][0]-1 != -1) and (not check_if_rocks_in_path([state["digdug"][0]-1, state["digdug"][1]], rocks)) and (not check_possible_fire(enemies, [state["digdug"][0]-1, state["digdug"][1]])) and ([state["digdug"][0]-1, state["digdug"][1]] not in enemies_pos) and ([state["digdug"][0]-1, state["digdug"][1]] not in predicted_enemies_pos):
        return True
    else:
        return False
    
def right_is_clear(state, rocks, enemies, enemies_pos):
    """Verifica se há espaço seguro/livre á direita do digdug"""
    predicted_enemies_pos = predict_enemies_pos(rocks, enemies)

    if (state["digdug"][0]+1 != 48) and (not check_if_rocks_in_path([state["digdug"][0]+1, state["digdug"][1]], rocks)) and (not check_possible_fire(enemies, [state["digdug"][0]+1, state["digdug"][1]])) and ([state["digdug"][0]+1, state["digdug"][1]] not in enemies_pos) and ([state["digdug"][0]+1, state["digdug"][1]] not in predicted_enemies_pos):
        return True
    else:
        return False
    
def up_is_clear(state, rocks, enemies, enemies_pos):
    """Verifica se há espaço seguro/livre acima do digdug"""
    predicted_enemies_pos = predict_enemies_pos(rocks, enemies)

    if (state["digdug"][1]-1 != -1) and (not check_if_rocks_in_path([state["digdug"][0], state["digdug"][1]-1], rocks)) and (not check_possible_fire(enemies, [state["digdug"][0], state["digdug"][1]-1])) and ([state["digdug"][0], state["digdug"][1]-1] not in enemies_pos) and ([state["digdug"][0], state["digdug"][1]-1] not in predicted_enemies_pos):
        return True
    else:
        return False

def down_is_clear(state, rocks, enemies, enemies_pos):
    """Verifica se há espaço seguro/livre abaixo do digdug"""
    predicted_enemies_pos = predict_enemies_pos(rocks, enemies)

    if (state["digdug"][1]+1 != 24) and (not check_if_rocks_in_path([state["digdug"][0], state["digdug"][1]+1], rocks)) and (not check_possible_fire(enemies, [state["digdug"][0], state["digdug"][1]+1])) and ([state["digdug"][0], state["digdug"][1]+1] not in enemies_pos) and ([state["digdug"][0], state["digdug"][1]+1] not in predicted_enemies_pos):
        return True
    else:
        return False
    
def clear_surroundings(enemies, enemies_pos, digdug, dug_direction):
    """Verifica se a existência se enimigos numa determinada direção"""

    #Verifica se existe um enimigo á esquerda do digdug e este não está orientado para lá
    if [digdug[0]-1, digdug[1]] in enemies_pos and dug_direction != 3:
        return False
    #Verifica se existe um enimigo á direita do digdug e este não está orientado para lá
    elif [digdug[0]+1, digdug[1]] in enemies_pos and dug_direction != 1:
        return False
    #Verifica se existe um enimigo acima do digdug e este não está orientado para lá
    elif [digdug[0], digdug[1]-1] in enemies_pos and dug_direction != 0:
        return False
    #Verifica se existe um enimigo abaixo do digdug e este não está orientado para lá
    elif [digdug[0], digdug[1]+1] in enemies_pos and dug_direction != 2:
        return False
    else:
        return True
    
def enemy_is_stuck(closest_enemy_pos, rocks):
    """Verificar se o inimigo se encontra preso numa célula apenas"""

    if ([closest_enemy_pos[0]+1, closest_enemy_pos[1]] not in dug_path) or ([closest_enemy_pos[0]+1, closest_enemy_pos[1]] in rocks):
        if ([closest_enemy_pos[0]-1, closest_enemy_pos[1]] not in dug_path) or ([closest_enemy_pos[0]-1, closest_enemy_pos[1]] in rocks):
            if ([closest_enemy_pos[0], closest_enemy_pos[1]+1] not in dug_path) or ([closest_enemy_pos[0], closest_enemy_pos[1]+1] in rocks):
                if ([closest_enemy_pos[0], closest_enemy_pos[1]-1] not in dug_path) or ([closest_enemy_pos[0], closest_enemy_pos[1]-1] in rocks):
                    return True
    return False

def wall_ahead(direction, object_pos):
    """Verifica a existencia de parede imediatamente à frente de um objeto"""

    #verifica se está orientado para cima
    if direction == 0:
        #verifica se está no limite superior do mapa ou se não está no caminho já escavado
        if object_pos[1]-1 == -1 or [object_pos[0], object_pos[1]-1] not in dug_path:
            return True
    #verifica se está orientado para a direita
    elif direction == 1:
        #verifica se está no limite direito do mapa ou se não está no caminho já escavado
        if object_pos[0]+1 == 48 or [object_pos[0]+1, object_pos[1]] not in dug_path:
            return True
    #verifica se está orientado para baixo
    elif direction == 2:
        #verifica se está no limite inferior do mapa ou se não está no caminho já escavado
        if object_pos[1]+1 == 24 or [object_pos[0], object_pos[1]+1] not in dug_path:
            return True
    #verifica se está orientado para a esquerda
    elif direction == 3:
        #verifica se está no limite esquerdo do mapa ou se não está no caminho já escavado
        if object_pos[0]-1 == -1 or [object_pos[0]-1, object_pos[1]] not in dug_path:
            return True

def predict_enemies_pos(rocks, enemies):
    """Prevê a posição dos inimigos na iteração seguinte"""

    #inicializa a lista de posições previstas dos inimigos
    enemies_predicted_pos = []

    #para cada inimigo
    for enemie in enemies:
        #se o inimigo está preso numa célula, adiciona a sua posição atual á lista de posições previstas
        if enemy_is_stuck(enemie["pos"],rocks):
            enemies_predicted_pos.append(enemie["pos"])

        #se estiver uma parede imediatamente á frente do inimigo, adiciona a sua posição atual á lista de posições previstas
        elif wall_ahead(enemie["dir"], enemie["pos"]):
            enemies_predicted_pos.append(enemie["pos"])

        #adiciona a posição prevista do inimigo á lista de posições previstas
        else:
            if enemie["dir"] == 0:
                enemies_predicted_pos.append([enemie["pos"][0], enemie["pos"][1]-1])
            elif enemie["dir"] == 1:
                enemies_predicted_pos.append([enemie["pos"][0]+1, enemie["pos"][1]])
            elif enemie["dir"] == 2:
                enemies_predicted_pos.append([enemie["pos"][0], enemie["pos"][1]+1])
            elif enemie["dir"] == 3:
                enemies_predicted_pos.append([enemie["pos"][0]-1, enemie["pos"][1]])
    return enemies_predicted_pos


async def agent_loop(server_address="localhost:8000", agent_name="student"):
    """Example client loop.Define o funcionamento geral do DigDug"""
    async with websockets.connect(f"ws://{server_address}/player") as websocket:
        # Receive information about static game properties
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))

        # Next 3 lines are not needed for AI agent
        # SCREEN = pygame.display.set_mode((299, 123))
        # SPRITES = pygame.image.load("data/pad.png").convert_alpha()
        # SCREEN.blit(SPRITES, (0, 0))


        #variáveis de controlo do digdug:
        #direção inicial(esquerda)
        dug_direction = 3
        #variavél que identifica se o digdugbestá pronto para atacar
        kill_setup = False
        #contagem para utilizar nas rochas para não ser morto pela rocha
        rock_counter = 0
        #posição do inimigo mais próximo da iteração anterior
        closest_enemy_last_pos = None

        while True:
            try:
                state = json.loads(
                    await websocket.recv()
                )  # receive game update, this must be called timely or your game will get out of sync with the server
                set_dug_path(state)
                
                # Next lines are only for the Human Agent, the key values are nonetheless the correct ones!
                key = ""
                if "digdug" in state:
                    #determina as posições das rochas
                    rocks = get_rocks_pos(state)
                    #dertermina as posições dos inimigos
                    enemies = get_enemies_pos(state)
                    enemies_pos = []

                    #se o jogo não terminou, guarda a posição dos inimigos
                    if enemies != [1,1]:
                        for e in enemies:
                            enemies_pos.append(e["pos"])
                    
                    #determina o inimigo mais próximo
                    closest_enemy = enemies[0] if enemies != [1,1] else None
                    #determina a posição do inimigo mais próximo
                    closest_enemy_pos = get_enemies_pos(state)[0]["pos"] if get_enemies_pos(state) != [1,1] else None
                    #determina o último movimento do inimigo mais próximo
                    closest_enemy_last_move = get_enemy_last_move(closest_enemy_last_pos, closest_enemy_pos)

                    #se o inimigo mais próximo não existe, limpa o caminho escavado
                    if closest_enemy_pos == None:
                        dug_path.clear()
                        closest_enemy_pos = [0,0]
                        path_to_enemy = [0,0]
                    else:
                        path_to_enemy = get_path_to_enemies(state)[0]

                    # calcula a distância entre o digdug e o enimigo mais próximo
                    enemy_distance = distance(state["digdug"], closest_enemy_pos)    

                    #se a distãncia é igual ou inferior a 3 (alcance do disparo)
                    if enemy_distance <= 3:
                        #se existe uma rocha acima do digdug e inicia um timer para sair debaixo da rocha
                        if [state["digdug"][0],state["digdug"][1]-1] in rocks:
                            rock_counter += 1

                        #se a contagem regressiva atingir 3 ou ultrapassar
                        if rock_counter >= 3:
                            #mover para a esquerda se estiver livre
                            if left_is_clear(state, rocks, enemies, enemies_pos):
                                key = "a"
                            #mover para a direita se estiver segura
                            elif right_is_clear(state, rocks, enemies, enemies_pos):
                                key = "d"
                            #mover para baixo
                            else:
                                key = "s"

                        # se o inimigo está na mesma linha que o digdug
                        elif path_to_enemy[1] == 0:
                            #se está a uma distancia de 1 a 3 blocos à direita do digdug
                            if (path_to_enemy[0] <= 3 and path_to_enemy[0] > 0): 
                                #se o digdug está orientado para a direita
                                if dug_direction==1:
                                    #se o inimigo está no caminho, o digdug move-se/vira-se para a esquerda
                                    if closest_enemy_pos not in dug_path or "traverse" in closest_enemy:
                                        key = "a"

                                    #se está escavado, verifica se existe parede entre o digdug e o inimigo mais pŕoximo
                                    elif check_if_no_wall(state["digdug"], closest_enemy_pos):
                                        #se não existe parede, verifica se o digdug por ser atingido pelo Fygar
                                        if check_possible_fire(enemies, state["digdug"]):
                                            #se pode ser atingido e pode mover-se seguramente para cima, move-se para cima, senão move-se para baixo
                                            if up_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "w"
                                            else:    
                                                key = "s"
                                        else:
                                            #dispara na direção em que se encontra se existirem inimigos nessa direção
                                            if clear_surroundings(enemies, enemies_pos, state["digdug"], dug_direction):
                                                key = "A"
                                            #move-se para outra posição segura ou dispara
                                            else:
                                                if left_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "a"
                                                elif down_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "s"
                                                elif up_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "w"
                                                elif right_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "d"
                                                else:
                                                    key = "A"    
                                    # se não estiver escavado entre o digdug e o inimigo mais próximo
                                    else:
                                        #se o inimigo mais próximo existe e está virado para a esquerda 
                                        if (closest_enemy is not None) and (closest_enemy["dir"]==3):
                                            #se a esquerda é segura movimenta-se nessa direção
                                            if left_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "a"
                                        # se o inimigo mais próximo existe e não está virado para a esquerda, o digdug move-se para a direita
                                        elif (closest_enemy is not None) and (closest_enemy["dir"]!=3):
                                            key = "d"

                                #se o digdug está orientado para qualquer direção que não a direita
                                else:
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        #se o lado esquerdo é seguro e o inimigo está colado ao digdug, foge para a esquerda
                                        if enemy_distance == 1:
                                            key = "a"
                                        else:
                                            #se o lado esquerdo é seguro, o inimigo mais próximo está a 2 blocos de distância, está orientado para o lado esquerdo e o seu ultimo movimento não foi na mesma linha para a direita continua
                                            if enemy_distance == 2 and (closest_enemy_pos not in dug_path or "traverse" in closest_enemy):
                                                continue
                                            else:
                                                if right_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "d"
                                                
                                    #se abaixo está livre move-se para baixo
                                    elif down_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "s"
                                    #ou move-se para cima
                                    else:    
                                        key = "w"

                            #mesma lógica mas para a direção oposta
                            # se o inimgo está a uma distancia de 1 a 3 blocos, à esquerda do digdug
                            elif(path_to_enemy[0] >= -3 and path_to_enemy[0] < 0):
                                # se o digdug está orientado para a esquerda
                                if dug_direction==3:
                                    #não está no caminho do digdug, move-se para a direita
                                    if closest_enemy_pos not in dug_path or "traverse" in closest_enemy:
                                        key = "d"

                                    #se não ha parede entre o digdug e o inimigo
                                    elif check_if_no_wall(state["digdug"], closest_enemy_pos):
                                        
                                        if check_possible_fire(enemies, state["digdug"]):
                                            # se pode ser atingido e acima tem caminho seguro, move-se para cima
                                            if up_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "w"
                                            #caso contrário move-se para baixo
                                            else:    
                                                key = "s"

                                        # se não pode ser atingido pelo Fygar
                                        else:
                                            # dispara se tiver um inimigo em frente
                                            if clear_surroundings(enemies, enemies_pos, state["digdug"], dug_direction):
                                                key = "A"

                                            #move-se para outra posição segura ou dispara 
                                            else:
                                                if right_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "d"
                                                elif down_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "s"
                                                elif up_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "w"
                                                elif left_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "a"
                                                else:
                                                    key = "A"

                                    # se não estiver escavado entre o digdug e o inimigo mais próximo
                                    else:
                                        # se exitir inimigo mais proximo e estiver orientado para a direita
                                        if (closest_enemy is not None) and (closest_enemy["dir"]==1):
                                            # o digdug move-se para a direita
                                            key = "d"
                                        #se não estiver orientado para a direita, move-se para a esquerda
                                        elif (closest_enemy is not None) and (closest_enemy["dir"]!=1):
                                            key = "a"

                                # se o digdug não está orientado para a esquerda
                                else:
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        # se a direita é segura, e se o inimigo está a 1 bloco de distancia, o didug move-se para a direita
                                        if enemy_distance == 1:
                                            key = "d"
                                            
                                        else:
                                            #se o lado direito é seguro, o inimigo mais perto está a 2 blocos de distância, está orientado para o lado direito e o seu ultimo movimento não foi na mesma linha para a esquerda continua
                                            if enemy_distance == 2 and (closest_enemy_pos not in dug_path or "traverse" in closest_enemy):
                                                continue
                                            else:
                                                if left_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "a"

                                                        
                                    #se abaixo está livre move-se para baixo
                                    elif down_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "s"
                                    #move-se para cima
                                    else:
                                        key = "w"

                        # se o inimigo está na mesma coluna que o digdug
                        elif path_to_enemy[0] == 0:
                            # se o inimigo está a uma distância de 1 a 3 blocos, abaixo do digdug
                            if(path_to_enemy[1] <= 3 and path_to_enemy[1] > 0):
                                #se o digdug está orientado para baixo 
                                if dug_direction==2:
                                    # se o inimigo não está no caminho do digdug, o digdug move-se para cima
                                    if closest_enemy_pos not in dug_path or "traverse" in closest_enemy:
                                        key = "w"
                                    
                                    # se não há parede entre o digdug e o inimigo
                                    elif check_if_no_wall(state["digdug"], closest_enemy_pos):
                                        # se existe um inimigo abaixo do digdug este dispara
                                        if clear_surroundings(enemies, enemies_pos, state["digdug"], dug_direction):
                                            key = "A"
                                        
                                        #move-se para outra posição segura ou dispara
                                        else:
                                            if up_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "w"
                                            elif right_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "d"
                                            elif left_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "a"
                                            elif down_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "s"
                                            else:
                                                key = "A"

                                    # se não estiver escavado entre o digdug e o inimigo mais próximo
                                    else:
                                        # se exitir inimigo mais proximo e estiver orientado para cima, o digdug move-se para cima
                                        if (closest_enemy is not None) and (closest_enemy["dir"]==0):
                                            key = "w"
                                        #se o inimigo não estiver orientado para cima, move-se para baixo
                                        elif (closest_enemy is not None) and (closest_enemy["dir"]!=0):
                                            key = "s"

                                # se o digdug não está orientado para baixo
                                else:
                                    if up_is_clear(state, rocks, enemies, enemies_pos):
                                        # se em cima é seguro e o inimigo está a 1 bloco de distância, o digdug move-se para cima
                                        if enemy_distance == 1:
                                            key = "w"
                                        else:
                                            # se o inimigo está a 2 blocos, orientado para cima, e o ultimo movimento não foi para cima continua
                                            if enemy_distance == 2 and (closest_enemy_pos not in dug_path or "traverse" in closest_enemy):
                                                continue
                                            # caso contrário, se embaixo está seguro, o digdug move-se para baixo
                                            else:
                                                if down_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "s"

                                    # se o lado direito está livre, o digdug move-se para a direita
                                    elif right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                                    #senão move-se para a esquerda
                                    else:
                                        key = "a"
                                    
                            # o inimigo está na mesma coluna que o digdug e está a um distânci de 1 a 3 blocos acima
                            elif(path_to_enemy[1] >= -3 and path_to_enemy[1] < 0):
                                # se o digdug está orientado para cima
                                if dug_direction==0:
                                    # se o inimigo mais próximo não está no caminho do digdug, o digdu move-se para baixo
                                    if closest_enemy_pos not in dug_path or "traverse" in closest_enemy:
                                        key = "s"
                                    
                                    #se não existe parede entre o digdug e o inimigo mais próximo
                                    elif check_if_no_wall(state["digdug"], closest_enemy_pos):
                                        # se o inimigo se encontra na direção do digdug, ele dispara
                                        if clear_surroundings(enemies, enemies_pos, state["digdug"], dug_direction):
                                            key = "A"
                                        #senão move-se para outra posição segura ou dispara
                                        else:
                                            if down_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "s"
                                            elif right_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "d"
                                            elif left_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "a"
                                            elif up_is_clear(state, rocks, enemies, enemies_pos):
                                                key = "w"
                                            else:
                                                key = "A"
                                    # se não estiver escavado entre o digdug e o inimigo mais próximo
                                    else:
                                        #inimigo orientado para baixo, digdug move para baixo
                                        if (closest_enemy is not None) and (closest_enemy["dir"]==2):
                                            key = "s"
                                        #inimigo não oreintado para baixo, digdug move para cima
                                        elif (closest_enemy is not None) and (closest_enemy["dir"]!=2):
                                            key = "w"

                                # se o digdug não está orientado para cima
                                else:
                                    
                                    if down_is_clear(state, rocks, enemies, enemies_pos):
                                        #se o caminho abaixo é seguro e o inimigo está a 1 bloco, digdug move-se para baixo
                                        if enemy_distance == 1:
                                            key = "s"
                                        else:
                                            #se inimigo a 2 blocos, orientado para baixo e ultimo movimento não para cima continua
                                            if enemy_distance == 2 and (closest_enemy_pos not in dug_path or "traverse" in closest_enemy):
                                                continue
                                            # caso contrário se acima for seguro digdug move-se para lá
                                            else:
                                                if up_is_clear(state, rocks, enemies, enemies_pos):
                                                    key = "w"

                                    # se o caminho á direita é seguro, move-se para a direita
                                    elif right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                                    #sa não move-se para a esuqerda
                                    else:
                                        key = "a"
                        #se o inimigo se encontra na diagonal inferior direita do digdug
                        elif path_to_enemy[0] == 1 and path_to_enemy[1] == 1:
                            # se o inimigo se moveu para a esquerda
                            if closest_enemy_last_move[0] == -1 and closest_enemy_last_move[1] == 0:
                                # se está no caminho do digdug e a direção do digdug não é para baixo
                                if closest_enemy_pos in dug_path and dug_direction != 2 and "traverse" not in closest_enemy:
                                    #se acima está seguro, o digdug move-se para cima e está pronto a atacar
                                    if up_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "w"
                                        kill_setup = True
                            # se o inimigo se moveu para cima, está no caminho do digdug e a sua esquerda está segura o digdug move-se para a esuqerda e fica pronto para atacar 
                            elif closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == -1:
                                if closest_enemy_pos in dug_path and dug_direction != 1 and "traverse" not in closest_enemy:
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "a"
                                        kill_setup = True
                            # se o inimigo se moveu para a baixo, está no caminho do digdug e a sua direita está segura o digdug move-se para a direita 
                            elif closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 1:
                                if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                            # se o inimigo se moveu para a direita, está no caminho do digdug e abaixo está seguro o digdug move-se para baixo 
                            elif closest_enemy_last_move[0] == 1 and closest_enemy_last_move[1] == 0:
                                if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                    if down_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "s"

                        # se o digdug se encontra na diagonal inferior esquerda do digdug
                        elif path_to_enemy[0] == -1 and path_to_enemy[1] == 1:
                            # se o inimigo se moveu para direita, está no caminho do digdug, o digdug não está orientado para baixo e acima está seguro o digdug move-se para a cima e fica pronto para atacar
                            if closest_enemy_last_move[0] == 1 and closest_enemy_last_move[1] == 0:
                                if closest_enemy_pos in dug_path and dug_direction != 2 and "traverse" not in closest_enemy:
                                    if up_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "w"
                                        kill_setup = True
                            # se o inimigo se moveu para a cima, está no caminho do digdug, o digdug não está orientado para a esquerda e a sua direita está segura o digdug move-se para a direita e fica pronto para atacar
                            elif closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == -1:
                                if closest_enemy_pos in dug_path and dug_direction != 3 and "traverse" not in closest_enemy:
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                                        kill_setup = True
                            # se o inimigo se moveu para a baixo, está no caminho do digdug e a sua esquerda está segura o digdug move-se para a esquerda 
                            elif closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 1:
                                if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "a"
                            # se o inimigo se moveu para a esquerda, está no caminho do digdug e abaixo está seguro o digdug move-se para baixo 
                            elif closest_enemy_last_move[0] == -1 and closest_enemy_last_move[1] == 0:
                                if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                    if down_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "s"

                        # se o inimigo está na diagonal superior direita do digdug
                        elif path_to_enemy[0] == 1 and path_to_enemy[1] == -1:
                            # se o inimigo se moveu para a esquerda, está no caminho do digdug, o digdug não está orientado para cima e abaixo está segura o digdug move-se para baixo e fica pronto para atacar
                            if closest_enemy_last_move[0] == -1 and closest_enemy_last_move[1] == 0:
                                if closest_enemy_pos in dug_path and dug_direction != 0 and "traverse" not in closest_enemy:
                                    if down_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "s"
                                        kill_setup = True
                            # se o inimigo se moveu para a baixo, está no caminho do digdug, o digdug não está orientado para a direita e a sua esquerda está segura o digdug move-se para a esuqerda e fica pronto para atacar
                            elif closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 1:
                                if closest_enemy_pos in dug_path and dug_direction != 1 and "traverse" not in closest_enemy:
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "a"
                                        kill_setup = True
                            # se o inimigo se moveu para cima, está no caminho do digdug e a sua direita está segura o digdug move-se para a direita 
                            elif closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == -1:
                                if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                            # se o inimigo se moveu para a direita, está no caminho do digdug e acima está seguro o digdug move-se para cima 
                            elif closest_enemy_last_move[0] == 1 and closest_enemy_last_move[1] == 0:
                                if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                    if up_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "w"

                        #se o inimigo está na diagonal superior esquerda do digdug
                        elif path_to_enemy[0] == -1 and path_to_enemy[1] == -1:
                            # se o inimigo se moveu para direita, está no caminho do digdug, o digdug não está orientado para cima e abaixo está segura o digdug move-se para baixo e fica pronto para atacar
                            if closest_enemy_last_move[0] == 1 and closest_enemy_last_move[1] == 0:
                                if closest_enemy_pos in dug_path and dug_direction != 0 and "traverse" not in closest_enemy:
                                    if down_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "s"
                                        kill_setup = True
                            # se o inimigo se moveu para baixo, está no caminho do digdug, o digudg não está orientado para a esquerda e a direita está segura o digdug move-se para a direita e fica pronto para atacar
                            elif closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 1:
                                if closest_enemy_pos in dug_path and dug_direction != 3 and "traverse" not in closest_enemy:
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                                        kill_setup = True
                            # se o inimigo se moveu para cima, está no caminho do digdug e a sua esquerda está segura o digdug move-se para a esuqerda
                            elif closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == -1:
                                if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "a"
                            # se o inimigo se moveu para a esuqerda, está no caminho do digdug e acima está segura o digdug move-se para cima
                            elif closest_enemy_last_move[0] == -1 and closest_enemy_last_move[1] == 0:
                                if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                    if up_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "w"


                        # se o inimigo se encontra dois blocos á direita e 1 abaixo            
                        elif path_to_enemy[0] == 2 and path_to_enemy[1] == 1:
                            #se o digdug está preparado para atacar, o inimigo se moveu para cima, quando está no caminho do digdug ou o inimigo não está em modo fantasma move-se para a direita
                            if kill_setup:
                                if closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == -1:
                                    if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                        key = "d"
                                        kill_setup = False
                            #se o inimigose moveu para a direita ou ficou parado, o inimigo é um Fygar e a direita é segure, o digdug move-se para a direita 
                            if (closest_enemy_last_move[0] == 1 and closest_enemy_last_move[1] == 0) or (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 0):
                                if closest_enemy["name"] == "Fygar":
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                                        kill_setup = False

                        # se o inimigo se encontra dois blocos á direita e 1 acima
                        elif path_to_enemy[0] == 2 and path_to_enemy[1] == -1:
                            #se o digdug está preparado para atacar, o inimigo se moveu para baixo, quando está no caminho do digdug ou o inimigo não está em modo fantasma move-se para a direita
                            if kill_setup:
                                if closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 1:
                                    if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                        key = "d"
                                        kill_setup = False
                            #se o inimigose moveu para a direita ou ficou parado, o inimigo é um Fygar e a direita é segure, o digdug move-se para a direita 
                            if (closest_enemy_last_move[0] == 1 and closest_enemy_last_move[1] == 0) or (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 0):
                                if closest_enemy["name"] == "Fygar":
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                                        kill_setup = False
                        

                        #se o inimigo se encontra a 2 blocos à esquerda e 1 abaixo
                        elif path_to_enemy[0] == -2 and path_to_enemy[1] == 1:
                            #se o digdug está preparado para atacar, o inimigo se moveu para cima, quando está no caminho do digdug ou o inimigo não está em modo fantasma move-se para a direita
                            if kill_setup:
                                if closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == -1:
                                    if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                        key = "a"
                                        kill_setup = False
                            #se o inimigo se moveu para a esquerda ou ficou parado, o inimigo é um Fygar e a esquerda é segura, o digdug move-se para a esquerda 
                            if (closest_enemy_last_move[0] == -1 and closest_enemy_last_move[1] == 0) or (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 0):
                                if closest_enemy["name"] == "Fygar":
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "a"
                                        kill_setup = False

                        #se o inimigo se encontra a 2 blocos à esquerda e 1 acima
                        elif path_to_enemy[0] == -2 and path_to_enemy[1] == -1:
                            #se o digdug está preparado para atacar, o inimigo se moveu para baixo, quando está no caminho do digdug ou o inimigo não está em modo fantasma move-se para a direita
                            if kill_setup:
                                if closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 1:
                                    if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                        key = "a"
                                        kill_setup = False
                            #se o inimigo se moveu para a esquerda ou ficou parado, o inimigo é um Fygar e a esquerda é segura, o digdug move-se para a esquerda
                            if (closest_enemy_last_move[0] == -1 and closest_enemy_last_move[1] == 0) or (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 0):
                                if closest_enemy["name"] == "Fygar":
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "a"
                                        kill_setup = False

                        #se o inimigo se encontra a 1 blocos à direita e 2 abaixo
                        elif path_to_enemy[0] == 1 and path_to_enemy[1] == 2:
                            #se o digdug está preparado para atacar, o inimigo se moveu para a esuqerda, quando está no caminho do digdug ou o inimigo não está em modo fantasma move-se para baixo
                            if kill_setup:
                                if closest_enemy_last_move[0] == -1 and closest_enemy_last_move[1] == 0:
                                    if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:    
                                        key = "s"
                                        kill_setup = False
                            #se o inimigo se moveu para baixo ou ficou parado, o inimigo é um Fygar e a direita é segura, o digdug move-se para a direita
                            if (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 1) or (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 0):
                                if closest_enemy["name"] == "Fygar":
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                                        kill_setup = False

                        #se o inimigo se encontra a 1 blocos à esquerda e 2 abaixo
                        elif path_to_enemy[0] == -1 and path_to_enemy[1] == 2:
                            #se o digdug está preparado para atacar, o inimigo se moveu para a direita, quando está no caminho do digdug ou o inimigo não está em modo fantasma move-se para baixo
                            if kill_setup:
                                if closest_enemy_last_move[0] == 1 and closest_enemy_last_move[1] == 0:
                                    if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                        key = "s"
                                        kill_setup = False
                            #se o inimigo se moveu para baixo ou ficou parado, o inimigo é um Fygar e a esquerda é segura, o digdug move-se para a esquerda
                            if (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 1) or (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 0):
                                if closest_enemy["name"] == "Fygar":
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "a"
                                        kill_setup = False

                        #se o inimigo se encontra a 1 blocos à direita e 2 acima
                        elif path_to_enemy[0] == 1 and path_to_enemy[1] == -2:
                            #se o digdug está preparado para atacar, o inimigo se moveu para a esuqerda, quando está no caminho do digdug ou o inimigo não está em modo fantasma move-se para cima
                            if kill_setup:
                                if closest_enemy_last_move[0] == -1 and closest_enemy_last_move[1] == 0:
                                    if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                        key = "w"
                                        kill_setup = False
                            #se o inimigo se moveu para cima ou ficou parado, o inimigo é um Fygar e a direita é segura, o digdug move-se para a direita
                            if (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == -1) or (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 0):
                                if closest_enemy["name"] == "Fygar":
                                    if right_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "d"
                                        kill_setup = False


                        #se o inimigo se encontra a 1 blocos à esquerda e 2 acima
                        elif path_to_enemy[0] == -1 and path_to_enemy[1] == -2:
                            #se o digdug está preparado para atacar, o inimigo se moveu para a direita, quando está no caminho do digdug ou o inimigo não está em modo fantasma move-se para cima
                            if kill_setup:
                                if closest_enemy_last_move[0] == 1 and closest_enemy_last_move[1] == 0:
                                    if closest_enemy_pos in dug_path and "traverse" not in closest_enemy:
                                        key = "w"
                                        kill_setup = False
                            #se o inimigo se moveu para cima ou ficou parado, o inimigo é um Fygar e a esquerda é segura, o digdug move-se para a esquerda
                            if (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == -1) or (closest_enemy_last_move[0] == 0 and closest_enemy_last_move[1] == 0):
                                if closest_enemy["name"] == "Fygar":
                                    if left_is_clear(state, rocks, enemies, enemies_pos):
                                        key = "a"
                                        kill_setup = False
                        
                        #se o inimigo está na diagonal inferior direita, a uma distancia de 2 blocos do inimigo em cada eixo       
                        elif(path_to_enemy[0]==2 and path_to_enemy[1]==2):  
                            # se o inimigo está preso e for um Fygar, o digdug move-se para a direita para o atacar
                            if enemy_is_stuck(closest_enemy_pos, rocks):
                                if closest_enemy["name"] == "Fygar":
                                    key = "d"
                                    kill_setup = False
                            else:
                                kill_setup = True

                        #se o inimigo está na diagonal superior direita, a uma distancia de 2 blocos do inimigo em cada eixo
                        elif(path_to_enemy[0]==2 and path_to_enemy[1]==-2):
                            # se o inimigo está preso e for um Fygar, o digdug move-se para a direita para o atacar
                            if enemy_is_stuck(closest_enemy_pos, rocks):
                                if closest_enemy["name"] == "Fygar":
                                    key = "d"
                                    kill_setup = False
                            else:
                                kill_setup = True

                        #se o inimigo está na diagonal superior direita, a uma distancia de 2 blocos do inimigo em cada eixo
                        elif(path_to_enemy[0]==-2 and path_to_enemy[1]==2):
                            # se o inimigo está preso e for um Fygar, o digdug move-se para a esquerda para o atacar
                            if enemy_is_stuck(closest_enemy_pos, rocks):
                                if closest_enemy["name"] == "Fygar":
                                    key = "a"
                                    kill_setup = False
                            else:
                                kill_setup = True

                        #se o inimigo está na diagonal superior esquerda, a uma distancia de 2 blocos do inimigo em cada eixo
                        elif(path_to_enemy[0]==-2 and path_to_enemy[1]==-2):
                            # se o inimigo está preso e for um Fygar, o digdug move-se para a esuqerda para o atacar
                            if enemy_is_stuck(closest_enemy_pos, rocks):
                                if closest_enemy["name"] == "Fygar":
                                    key = "a"
                                    kill_setup = False
                            else:
                                kill_setup = True


                    #se o inimigo está a uma distância superior a 3
                    else:
                        kill_setup = False
                        # se o inimigo se encontra acima do digdug e se o inimigo está mais proximo horizontalmente do que verticalmente
                        if path_to_enemy[1] > 0 and abs(path_to_enemy[0]) <= abs(path_to_enemy[1]):
                            # Se há uma rocha em frente, move-se para a esquerda ou direita
                            if (check_if_rocks_in_path([state["digdug"][0], state["digdug"][1]+1], rocks)):
                                if path_to_enemy[0]<=0:
                                    key = "a"
                                else:
                                    key = "d"
                            #senão move-se para baixo
                            else:
                                key = "s"

                        # se o inimigo se encontra abaixo do digdug e se o inimigo está mais proximo horizontalmente do que verticalmente
                        elif path_to_enemy[1] < 0 and abs(path_to_enemy[0]) <= abs(path_to_enemy[1]):
                            # Se há uma rocha em frente, move-se para a esquerda ou direita
                            if (check_if_rocks_in_path([state["digdug"][0], state["digdug"][1]-1], rocks)):
                                if path_to_enemy[0]<=0:
                                    key = "a"
                                else:
                                    key = "d"
                            #senão move-se para cima
                            else:
                                key = "w"

                        # se o inimigo se encontra à direita do digdug e se o inimigo está mais proximo verticalmente do que horizontalmente
                        elif path_to_enemy[0] > 0 and abs(path_to_enemy[0]) > abs(path_to_enemy[1]):
                            # Se há uma rocha em frente, move-se para cima ou para baixo
                            if (check_if_rocks_in_path([state["digdug"][0]+1, state["digdug"][1]], rocks)):
                                if path_to_enemy[1]<=0:
                                    key = "w"
                                else:
                                    key = "s"
                            #senão move-se para a direita
                            else:
                                key = "d"

                        # se o inimigo se encontra à esquerda do digdug e se o inimigo está mais proximo verticalmente do que horizontalmente
                        elif path_to_enemy[0] < 0 and abs(path_to_enemy[0]) > abs(path_to_enemy[1]):
                            # Se há uma rocha em frente, move-se para cima ou para baixo
                            if (check_if_rocks_in_path([state["digdug"][0]-1, state["digdug"][1]], rocks)):
                                if path_to_enemy[1]<=0:
                                    key = "w"
                                else:
                                    key = "s"
                            #senão move-se para a esquerda
                            else:
                                key = "a"

                    # atualiza a última posição conhecida do inimigo mais próximo
                    closest_enemy_last_pos = closest_enemy_pos


                # imprimir alteração na etapa do jogo
                if "step" in state:
                    step = state["step"]
                    print("latency: ", datetime.datetime.now().timestamp()-float(state["ts"]),"s")
                    print("step: ", step)
                    print("rocks: ", rocks)
                    print("digdug: ", state["digdug"])
                    print("dug_direction: ", dug_direction)
                    print("enemies: ", enemies_pos)
                    print("closest enemy: ", closest_enemy)
                    print("distance: ", enemy_distance)
                    print("lives: ", state["lives"])
                    
                    if state["lives"] == 0 or step == 3000:
                        #se o jogo terminou, gurada a pontuação
                        with open("score.txt", "a") as f:
                            f.write(str(state["score"])+"\n")

                #mapear a direção do digdug
                if key == "w":
                    dug_direction = 0
                elif key == "d":
                    dug_direction = 1
                    rock_counter = 0
                elif key == "s":
                    if rock_counter >= 3:
                        rock_counter = 3
                    else:
                        rock_counter = 0
                    dug_direction = 2
                elif key == "a":
                    rock_counter = 0
                    dug_direction = 3

                


                print("key: ", key)
                print()

                await websocket.send(
                    json.dumps({"cmd": "key", "key": key})
                )  # send key command to server - you must implement this send in the AI agent
            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return

# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))