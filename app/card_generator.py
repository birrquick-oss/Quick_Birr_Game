import random

def generate_bingo_card():
    """1 የቢንጎ ካርድ ማትሪክስ ያመነጫል"""
    card = {
        "B": random.sample(range(1, 16), 5),
        "I": random.sample(range(16, 31), 5),
        "N": random.sample(range(31, 46), 5),
        "G": random.sample(range(46, 61), 5),
        "O": random.sample(range(61, 76), 5)
    }
    # የ 'N' አምድ መካከለኛው ነጻ (FREE space) ነው
    card["N"][2] = "FREE"
    return card

def generate_all_cards(total_cards: int = 1000):
    """የተፈለገውን ያህል (1000) ካርዶች ያመነጫል"""
    cards = []
    for _ in range(total_cards):
        cards.append(generate_bingo_card())
    return cards
