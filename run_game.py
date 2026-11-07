from game.app import input as game_input
from game.app import run_game
from game.app import update as game_update


def input(key):
    game_input(key)


def update():
    game_update()


if __name__ == "__main__":
    run_game()
