import asyncio, getpass, json, os, websockets, traceback, copy, itertools, time
from typing import final

BOARD_X = None
BOARD_Y = None

LETTERS = {
    "[[3, 3], [4, 3], [3, 4], [4, 4]]": "O",
    "[[1, 2], [2, 2], [1, 3], [2, 3]]": "O",
    "[[2, 2], [3, 2], [4, 2], [5, 2]]": "I",
    "[[0, 1], [1, 1], [2, 1], [3, 1]]": "I",
    "[[4, 2], [4, 3], [5, 3], [4, 4]]": "T",
    "[[2, 1], [2, 2], [3, 2], [2, 3]]": "T",
    "[[4, 2], [4, 3], [4, 4], [5, 4]]": "L",
    "[[2, 1], [2, 2], [2, 3], [3, 3]]": "L",
    "[[4, 2], [5, 2], [4, 3], [4, 4]]": "J",
    "[[2, 1], [3, 1], [2, 2], [2, 3]]": "J",
    "[[4, 2], [3, 3], [4, 3], [3, 4]]": "S",
    "[[2, 1], [2, 2], [3, 2], [3, 3]]": "S",
    "[[4, 2], [4, 3], [5, 3], [5, 4]]": "Z",
    "[[2, 1], [1, 2], [2, 2], [1, 3]]": "Z"
}

ROTATIONS = {
    "O": [[[3, 3], [4, 3], [3, 4], [4, 4]]],
    "I": [[[2, 2], [3, 2], [4, 2], [5, 2]], [[4, 1], [4, 2], [4, 3], [4, 4]]],
    "T": [[[4, 2], [4, 3], [5, 3], [4, 4]], [[3, 3], [4, 3], [5, 3], [4, 4]], [[4, 2], [3, 3], [4, 3], [4, 4]], [[4, 2], [3, 3], [4, 3], [5, 3]]],
    "L": [[[4, 2], [4, 3], [4, 4], [5, 4]], [[3, 3], [4, 3], [5, 3], [3, 4]], [[3, 2], [4, 2], [4, 3], [4, 4]], [[5, 2], [3, 3], [4, 3], [5, 3]]],
    "J": [[[4, 2], [5, 2], [4, 3], [4, 4]], [[3, 3], [4, 3], [5, 3], [5, 4]], [[4, 2], [4, 3], [3, 4], [4, 4]], [[3, 2], [3, 3], [4, 3], [5, 3]]],
    "S": [[[4, 2], [3, 3], [4, 3], [3, 4]], [[3, 3], [4, 3], [4, 4], [5, 4]]],
    "Z": [[[4, 2], [4, 3], [5, 3], [5, 4]], [[4, 3], [5, 3], [3, 4], [4, 4]]]

}

def set_dimensions(dimensions):
    global BOARD_X, BOARD_Y
    BOARD_X = dimensions[0] - 1
    BOARD_Y = dimensions[1]

def calc_height(game):
    heights = {x: 30 for x in range(1,BOARD_X)}

    if len(game):
        for coords in game:
            x, y = coords
            if x not in heights:
                heights[x] = y
            elif y < heights[x]:
                heights[x] = y
        
    return (BOARD_X-1)*BOARD_Y - sum(heights.values()), heights

def calc_bumpiness(heights):
    return sum([abs(heights[i] - heights[i+1]) for i in range(1, len(heights)-1)])

def calc_holes(game):
    sorted_game = sorted(game)
    holes = 0
    if len(game):
        for i in range(len(sorted_game) - 1):
            x, y = sorted_game[i]
            next_x, next_y = sorted_game[i+1]

            if x == next_x: # if in same row
                if y + 1 != next_y:
                    holes += next_y - y - 1
            else:
                # calc first hole that is against the border
                if y != BOARD_Y-1:
                    holes += BOARD_Y - y - 1

        if sorted_game[-1][1] != BOARD_Y-1:
            holes += BOARD_Y - sorted_game[-1][1] - 1

    return holes

def calc_complete_lines(game):
    lst = [coord[1] for coord in game]
    lst = sorted(lst)

    complete_lines = 0
    counter = 0

    for i in range(len(lst) - 1):
        if lst[i] == lst[i+1]:
            counter += 1

            if counter == BOARD_X-2:
                complete_lines += 1
        else:
            counter = 0

    return complete_lines

def calc_possible_starting_positions(letter):
    '''Get every possible position'''
    positions = {} # { piece_coords : [key1, key2, key3] }

    for counter, v in enumerate(ROTATIONS[letter]):
        stop = False
        positions[str(v)] = ["s"] + ["w"] * counter # add possible piece starting position and keys to dict

        counter2 = 0
        new_piece = v
        while True: # translate left
            for coord in new_piece:
                if coord[0] == 1:
                    stop = True
                    break
            
            if stop:
                break

            counter2 += 1
            new_piece = [[x-1,y] for [x,y] in new_piece]
            positions[str(new_piece)] = ["s"] + ["a"] * counter2 + ["w"] * counter

        stop = False
        counter2 = 0
        new_piece = v
        while True: # translate right
            for coord in new_piece:
                if coord[0] == BOARD_X-1:
                    stop = True
                    break

            if stop:
                break

            counter2 += 1
            new_piece = [[x+1,y] for [x,y] in new_piece]
            positions[str(new_piece)] = ["s"] + ["d"] * counter2 + ["w"] * counter

    return positions

def calculate_final_positions(starting_positions, heights):
    final_positions = {}

    for pos,keys in starting_positions.items():
        pos = json.loads(pos) # convert str to 2d list
        max_travel = []
        for coord in pos: # calcular qual das rows e que pode viajar menos distancia
            x,y = coord
            max_travel.append(heights[x] - y - 1) # calcular qual das rows e que pode viajar menos distancia

        final_pos = [[x,y+min(max_travel)] for x,y in pos] # obter a final position da peca
        final_positions[str(final_pos)] = keys

    return final_positions

def evaluate_final_position(game, final_positions):
    evaluations = {}
    cl_weight = 0.760666
    height, _ = calc_height(game)

    if height > 100:
        cl_weight = 10.760666

    for pos in final_positions:
        pos = json.loads(pos) # convert str to 2d list
        # meter a peça no state_game
        board = [x[:] for x in game]
        board += pos

        complete_lines = calc_complete_lines(board)
        height, heights = calc_height(board)
        bumpiness = calc_bumpiness(heights)
        holes = calc_holes(board)
        evaluation = (-0.510066*height) + (cl_weight*complete_lines) + (-0.35663*holes) + (-0.184483*bumpiness)
        evaluations[str(pos)] = evaluation

    evaluations = dict(sorted(evaluations.items(), key=lambda item: item[1], reverse=True))
    candidate_moves = dict(itertools.islice(evaluations.items(), 5)) # 5 best moves

    return candidate_moves

def look_ahead1(candidate_moves, game, starting_positions):
    '''Para cada jogada candidata, calcula o melhor custo da próxima peça. Retorna a melhor jogada candidata'''
    max_eval = -99999

    for move in candidate_moves:
        board = [x[:] for x in game]
        board.extend(json.loads(move))
        _, heights = calc_height(board)

        final_positions = calculate_final_positions(starting_positions[1], heights)
        next_piece_candidate_moves = evaluate_final_position(board, final_positions)

        eval = list(next_piece_candidate_moves.values())[0]
        if eval > max_eval:
            max_eval = eval
            best_move = move

    return best_move

async def agent_loop(server_address="localhost:8000", agent_name="student"):
    next_pieces = None
    cache = {}
    keys_buffer = []

    async with websockets.connect(f"ws://{server_address}/player") as websocket:
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name})) # Receive information about static game properties

        while True:
            try:
                state = json.loads(
                    await websocket.recv()
                )  # receive game update, this must be called timely or your game will get out of sync with the server

                if "dimensions" in state:
                    set_dimensions(state["dimensions"])

                elif len(keys_buffer):
                    await websocket.send(json.dumps({"cmd": "key", "key": keys_buffer.pop()}))

                elif (next_pieces != state['next_pieces'] or next_pieces is None) and (state["piece"] != None): # wait for next piece                    
                    game = state["game"]
                    _, heights = calc_height(game)
                    letters = [ LETTERS[str(state["piece"])] ]

                    for p in state["next_pieces"]:
                        letters.append(LETTERS[str(p)])

                    starting_positions = []
                    for l in letters:
                        if l in cache:
                            starting_positions.append(cache[l])
                        else:
                            positions = calc_possible_starting_positions(l)
                            cache[l] = positions
                            starting_positions.append(positions)

                    current_piece_final_positions = calculate_final_positions(starting_positions[0], heights)
                    candidate_moves = evaluate_final_position(game, current_piece_final_positions)
                    best_move = look_ahead1(candidate_moves, game, starting_positions)
                    keys = current_piece_final_positions[best_move]
                    keys_buffer += keys
                    next_pieces = state["next_pieces"]

            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return
            except Exception as e:
                print(e, traceback.format_exc())

# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))