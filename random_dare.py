
import os
import trello

trello_client = trello.TrelloClient(
    api_key=os.getenv('TRELLO_API_KEY'),
    api_secret=os.getenv('TRELLO_API_SECRET'),
    token=os.getenv('TRELLO_TOKEN')
)

all_boards = trello_client.list_boards()
last_board = all_boards[0]
print(last_board.name)
print(all_boards[0].list_lists()[3].id)