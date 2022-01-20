import copy
import enum
import random
from collections import namedtuple
import time
import tkinter as tk 

root = tk.Tk()
root.title("The Go Game")
root.geometry("580x380")

PIECE_SIZE = 10
board_size = 9

click_x = 0
click_y = 0

pieces_x = [i for i in range(32, 313, 35)]
pieces_y = [i for i in range(38, 319, 35)]
#[32, 67, 102, 137, 172, 207, 242, 277, 312]
#[38, 73, 108, 143, 178, 213, 248, 283, 318]

piece_color = "black"
user_row = -1
user_col = -1
bot_pass = 0
user_pass = 0

class Move():
    def __init__(self, point=None, is_pass=False, is_resign=False):
        self.point = point
        self.is_play = (self.point is not None)
        self.is_pass = is_pass
        self.is_resign = is_resign

    @classmethod
    def play(cls, point):
        return Move(point=point)

    @classmethod
    def pass_turn(cls):
        return Move(is_pass=True)

    @classmethod
    def resign(cls):
        return Move(is_resign=True)

class GoString():
    def __init__(self, color, stones, liberties):
        self.color = color
        self.stones = set(stones)
        self.liberties = set(liberties)

    def remove_liberty(self, point):
        self.liberties.remove(point)

    def add_liberty(self, point):
        self.liberties.add(point)

    def merged_with(self, go_string):
        assert go_string.color == self.color
        combined_stones = self.stones | go_string.stones
        return GoString(
            self.color,
            combined_stones,
            (self.liberties | go_string.liberties) - combined_stones)

    @property
    def num_liberties(self):
        return len(self.liberties)

    def __eq__(self, other):
        return isinstance(other, GoString) and \
            self.color == other.color and \
            self.stones == other.stones and \
            self.liberties == other.liberties

class Board():  
    def __init__(self, num_rows, num_cols):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self._grid = {}    #empty dictionary

    def place_stone(self, player, point):
        assert self.is_on_grid(point)
        assert self._grid.get(point) is None
        adjacent_same_color = []
        adjacent_opposite_color = []
        liberties = []
        for neighbor in point.neighbors():  #function will return 4 adj place
            if not self.is_on_grid(neighbor):  #will check if there is any stone at that place or not
                continue
            neighbor_string = self._grid.get(neighbor) #will check which which player stone is in the place
            if neighbor_string is None:
                liberties.append(neighbor)  #if there is no stone it will add that place to liberty
            elif neighbor_string.color == player: # for same color stone
                if neighbor_string not in adjacent_same_color:
                    adjacent_same_color.append(neighbor_string)  #if that stone is not in list then add it
            else:
                if neighbor_string not in adjacent_opposite_color:
                    adjacent_opposite_color.append(neighbor_string) 
        new_string = GoString(player, [point], liberties)   #player, point for stone, empty adj place

        for same_color_string in adjacent_same_color:  #add same stone adj to the instance
            new_string = new_string.merged_with(same_color_string) 
        for new_string_point in new_string.stones:      #give new_string to all the stone in instance
            self._grid[new_string_point] = new_string
        for other_color_string in adjacent_opposite_color:  #if other stone is on adj remove that from liberty
            other_color_string.remove_liberty(point)     
        for other_color_string in adjacent_opposite_color:  
            if other_color_string.num_liberties == 0:
                self._remove_string(other_color_string)

    def _remove_string(self, string):    #will remove the capture stone
        for point in string.stones:
            for neighbor in point.neighbors():   
                neighbor_string = self._grid.get(neighbor)
                if neighbor_string is None:
                    continue
                if neighbor_string is not string:
                    neighbor_string.add_liberty(point)
            del(self._grid[point])
            remove_stone(point.row,point.col)

    def is_on_grid(self, point):
        return 1 <= point.row <= self.num_rows and \
            1 <= point.col <= self.num_cols

    def get(self, point):  
        string = self._grid.get(point)
        if string is None:
            return None
        return string.color

    def get_go_string(self, point):  
        string = self._grid.get(point)
        if string is None:
            return None
        return string

class GameState():
    def __init__(self, board, next_player, previous, move):
        self.board = board
        self.next_player = next_player
        self.previous_state = previous
        self.last_move = move

    def apply_move(self, move):  
        if move.is_play:
            next_board = copy.deepcopy(self.board)
            next_board.place_stone(self.next_player, move.point)
        else:
            next_board = self.board
        return GameState(next_board, self.next_player.other, self, move)

    @classmethod
    def new_game(cls, board_size):
        if isinstance(board_size, int):
            board_size = (board_size, board_size)
        board = Board(*board_size)
        return GameState(board, Player.black, None, None)

    def is_over(self):
        if self.last_move is None:
            return False
        if self.last_move.is_resign:
            return True
        second_last_move = self.previous_state.last_move
        if second_last_move is None:
            return False
        return self.last_move.is_pass and second_last_move.is_pass

    def is_move_self_capture(self, player, move): #will check if stone has any liberty by playing th move temp
        if not move.is_play:
            return False
        next_board = copy.deepcopy(self.board)
        next_board.place_stone(player, move.point)
        new_string = next_board.get_go_string(move.point)
        return new_string.num_liberties == 0

    @property
    def situation(self):
        return (self.next_player, self.board)

    def does_move_violate_ko(self, player, move): #will check the ko rule of not creating same state again
        if not move.is_play:
            return False
        next_board = copy.deepcopy(self.board)
        next_board.place_stone(player, move.point) #play on copy of board
        next_situation = (player.other, next_board)
        past_state = self.previous_state
        while past_state is not None:  #check the new temp other board to every past state
            if past_state.situation == next_situation:
                return True
            past_state = past_state.previous_state
        return False

    def is_valid_move(self, move):
        if self.is_over():
            return False
        if move.is_pass or move.is_resign:
            return True
        return (
            self.board.get(move.point) is None and
            not self.is_move_self_capture(self.next_player, move) and
            not self.does_move_violate_ko(self.next_player, move)) #true and not false and not false

class Player(enum.Enum):
    black = 1
    white = 2

    @property
    def other(self):
        return Player.black if self == Player.white else Player.white

class Point(namedtuple('Point', 'row col')):
    def neighbors(self):
        return [
            Point(self.row - 1, self.col),
            Point(self.row + 1, self.col),
            Point(self.row, self.col - 1),
            Point(self.row, self.col + 1),
        ]

class RandomBot():
    def select_move(self, game_state):
        global game
        candidates = []
        for r in range(1, game_state.board.num_rows + 1):
            for c in range(1, game_state.board.num_cols + 1):
                candidate = Point(row=r, col=c)
                if game_state.is_valid_move(Move.play(candidate)) and \
                        not is_point_an_eye(game_state.board,
                                            candidate,
                                            game_state.next_player):
                    candidates.append(candidate)
        if not candidates:
            bot_pass = 1
            return Move.pass_turn()
        bot_coor = random.choice(candidates)
        bot_coormove(bot_coor)
        bot_pass = 0
        return Move.play(bot_coor)

class UserMove():
    def select_move(self, game_state):
        global user_row,user_col,game,user_pass
        place = Point(row=0,col=0)
        user_row = 9 - user_row
        candidate = Point(row=user_row, col=user_col+1)
        if game_state.is_valid_move(Move.play(candidate)) and \
            not is_point_an_eye(game_state.board, 
                                candidate, 
                                game_state.next_player):
                place = Move.play(candidate)
                user_pass = 0
        else:
            user_pass = 1
            return Move.pass_turn()
        return place

def is_point_an_eye(board, point, color):
    if board.get(point) is not None:
        return False
    for neighbor in point.neighbors():
        if board.is_on_grid(neighbor):
            neighbor_color = board.get(neighbor)
            if neighbor_color != color:
                return False

    friendly_corners = 0
    off_board_corners = 0
    corners = [
        Point(point.row - 1, point.col - 1),
        Point(point.row - 1, point.col + 1),
        Point(point.row + 1, point.col - 1),
        Point(point.row + 1, point.col + 1),
    ]
    for corner in corners:
        if board.is_on_grid(corner):
            corner_color = board.get(corner)
            if corner_color == color:
                friendly_corners += 1
        else:
            off_board_corners += 1
    if off_board_corners > 0:
        return off_board_corners + friendly_corners == 4
    return friendly_corners >= 3

COLS = 'ABCDEFGHIKLMN'
STONE_TO_CHAR = {
    None: '-',
    Player.black: 'x',
    Player.white: 'o',
}

def print_board(board):
    for row in range(board.num_rows, 0, -1):
        line = []
        for col in range(1, board.num_cols + 1):
            stone = board.get(Point(row=row, col=col))
            line.append(STONE_TO_CHAR[stone])
        print('%d %s' % (row, ''.join(line)))
    print('  ' + COLS[:board.num_cols])

def count(board):
    black_score = 0
    white_score = 0 
    for i in range(board.num_rows, 0, -1):
        for j in range(1, board.num_cols + 1):
            stone_count = board.get(Point(row=i,col=j))
            if stone_count == Player.black:
              black_score += 1
            elif stone_count == Player.white:
              white_score += 1
    tag = 'Black Score: '+str(black_score)+'\nWhite Score: '+str(white_score)
    if black_score > white_score:
      tag += '\nBlack Wins'
      var1.set(tag)
    elif white_score > black_score:
      tag += '\nWhite Wins'
      var1.set(tag)
    else:
      tag += '\nTie'
      var1.set(tag)

game = GameState.new_game(board_size)
bots = {
    Player.black: RandomBot(),
    Player.white: UserMove(),
}

def start():
    global game,bot_pass 
    if game.is_over():
        count(game.board)
    else:
        bot_move = bots[Player.black].select_move(game)
        if bot_pass == 0:
            game = game.apply_move(bot_move)

def showChange(color):
    global piece_color
    piece_color = color
    side_canvas.delete("show_piece")
    side_canvas.create_oval(110 - PIECE_SIZE, 25 - PIECE_SIZE,
                        110 + PIECE_SIZE, 25 + PIECE_SIZE,
                        fill = piece_color, tags = ("show_piece"))

def remove_stone(row,col):
    x = 9-row
    y = col-1
    tag = 'tag'
    tag += str(x)+str(y)
    canvas.delete(tag)

def bot_coormove(bot_coor): #place to black stone on the board
    global piece_color
    bot_row = 9-bot_coor.row
    bot_col = bot_coor.col
    x_value = pieces_x[bot_col-1]
    y_value = pieces_y[bot_row]
    tag = 'tag'
    tag += str(bot_row)+str(bot_col-1)
    canvas.create_oval(x_value - PIECE_SIZE, y_value - PIECE_SIZE,
                       x_value + PIECE_SIZE, y_value + PIECE_SIZE, 
                       fill = piece_color, tags = (tag))
    if piece_color == "black":
        piece_color = "white"
        var.set("White Stone")
        showChange("white")
    elif piece_color == "white":
        piece_color = "black"
        var.set("Black Stone")
        showChange("black") 

def user_coormove(event):
    global click_x, click_y, piece_color,user_row,user_col,game,user_pass
    click_x = event.x
    click_y = event.y
    absolute_difference_function_x = lambda list_value : abs(list_value - click_x)
    x_value = min(pieces_x, key=absolute_difference_function_x)
    absolute_difference_function_y = lambda list_value : abs(list_value - click_y)
    y_value = min(pieces_y, key=absolute_difference_function_y)
    user_row = pieces_y.index(y_value)
    user_col = pieces_x.index(x_value)
    tag = 'tag'
    tag += str(user_row)+str(user_col)
    if game.is_over():
        count(game.board)
    else:
        user_move = bots[Player.white].select_move(game)
        if user_pass == 0:
            game = game.apply_move(user_move)
            canvas.create_oval(x_value - PIECE_SIZE, y_value - PIECE_SIZE,
                       x_value + PIECE_SIZE, y_value + PIECE_SIZE, 
                       fill = piece_color, tags = (tag))
            if piece_color == "black":
                piece_color = "white"
                var.set("White Stone")
                showChange("white")
            elif piece_color == "white":
                piece_color = "black"
                var.set("Black Stone")
                showChange("black")
        start()
    
def pass_stone():
    global game    
    bot_move = Move.pass_turn()
    game = game.apply_move(bot_move)
    piece_color = "black"
    var.set("Black Stone")
    showChange("black")
    start()

def player_resign():
    global game
    bot_move = Move.resign()
    game = game.apply_move(bot_move)
    piece_color = "white"
    var.set("White Stone Resign")
    showChange("White")
    count(game.board)
    canvas.unbind("<Button-1>") 

def gameReset():
    global piece_color,game,bots      
    var.set("Black Stone")      
    var1.set("") 
    showChange("black")
    for i in range(9):
        for j in range(9):
            tag = 'tag'
            tag += str(i)+str(j)  
            canvas.delete(tag) #Delete all pieces
    canvas.bind("<Button-1>", user_coormove)     
    game = GameState.new_game(board_size)
    bots = {
        Player.black: RandomBot(),
        Player.white: UserMove(),
    }
    start()
#stone oval
side_canvas = tk.Canvas(root, width = 220, height = 50)
side_canvas.grid(row = 0, column = 1)
side_canvas.create_oval(110 - PIECE_SIZE, 25 - PIECE_SIZE,
                        110 + PIECE_SIZE, 25 + PIECE_SIZE,
                        fill = piece_color, tags = ("show_piece") )
#Player Label
var = tk.StringVar()
var.set("Black Stone")
person_label = tk.Label(root, textvariable = var, width = 15, anchor = tk.CENTER, 
                        font = ("Arial", 12) )
person_label.grid(row = 1, column = 1)
#Win and Loss Label
var1 = tk.StringVar()
var1.set("")
result_label = tk.Label(root, textvariable = var1, width = 12, height = 4, 
                        anchor = tk.CENTER, font = ("Arial", 12) )
result_label.grid(row = 2, column = 1)
#Reset button
reset_button = tk.Button(root, text = "Restart", font = 20, 
                          width = 8, command = gameReset)
reset_button.grid(row = 5, column = 1)
#Resign button
resign_button = tk.Button(root, text = "Resign", font = 20, 
                          width = 8, command = player_resign)
resign_button.grid(row = 4, column = 1)
#Pass button
pass_button = tk.Button(root, text = "Pass", font = 20, 
                          width = 8, command = pass_stone)
pass_button.grid(row = 3, column = 1)

#background
canvas = tk.Canvas(root, bg = "saddlebrown", width = 340, height = 340)
canvas.bind("<Button-1>", user_coormove) 
canvas.grid(row = 0, column = 0, rowspan = 6)
#line
for i in range(9):
    canvas.create_line(32, (35 * i + 38), 313, (35 * i + 38))
    canvas.create_line((35 * i + 32), 38, (35 * i + 32), 319)
#Number coordinates
num = 10    
for i in range(9):
    label = tk.Label(canvas, text = str(num - 1), fg = "black", bg = "saddlebrown",
                     width = 2, anchor = tk.E)
    label.place(x = 2, y = 35 * i + 28)
    num = num - 1
#LETTER COORDINATE
countl = 0
for i in range(65, 74):
    label = tk.Label(canvas, text = chr(i), fg = "black", bg = "saddlebrown")
    label.place(x = 35 * countl + 25, y = 2)
    countl += 1

start()
root.mainloop()