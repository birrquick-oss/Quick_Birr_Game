import random
import json

def generate_bingo_card_matrix():
    """1 የቢንጎ ካርድ 5x5 Matrix (Row-wise) ያመነጫል"""
    b = random.sample(range(1, 16), 5)
    i = random.sample(range(16, 31), 5)
    n = random.sample(range(31, 46), 5)
    g = random.sample(range(46, 61), 5)
    o = random.sample(range(61, 76), 5)
    
    # የ 'N' አምድ መካከለኛው ነጻ (FREE space) ነው
    n[2] = "FREE"

    # በ Column የተቀመጡትን ወደ 5x5 Row Matrix መቀየር
    matrix = []
    for r in range(5):
        row = [b[r], i[r], n[r], g[r], o[r]]
        matrix.append(row)
        
    return matrix

def generate_all_cards(total_cards: int = 600):
    """600 ሙሉ በሙሉ የተለያዩ (Unique) የቢንጎ ካርዶችን ያመነጫል"""
    cards = []
    seen_hashes = set()

    while len(cards) < total_cards:
        card_matrix = generate_bingo_card_matrix()
        
        # የካርዱን ልዩነት ለማረጋገጥ Hash ማድረግ
        card_hash = json.dumps(card_matrix)
        if card_hash not in seen_hashes:
            seen_hashes.add(card_hash)
            cards.append(card_matrix)

    print(f"✅ {len(cards)} የተለያዩ የቢንጎ ካርዶች ተዘጋጅተዋል!")
    return cards
