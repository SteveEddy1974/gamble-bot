
from math import comb
from models import ShoeState


def hypergeom_pmf(k, K, N, n):
    """Probability of drawing k successes in n draws from N items with K successes."""
    return comb(K, k) * comb(N - K, n - k) / comb(N, n)


def card_value(rank: int) -> int:
    # Ace=1, 2-9 face, 10/J/Q/K=0
    if rank == 1:
        return 1
    if 2 <= rank <= 9:
        return rank
    return 0


def prob_pocket_pair(shoe: ShoeState) -> float:
    """Exact probability at least one of Player/Banker has a pocket pair (first two cards per hand)."""
    N0 = shoe.cards_remaining
    counts0 = {r: shoe.card_counts.get(r, 0) for r in range(1, 14)}
    total_prob = 0.0
    for r1 in range(1, 14):
        if counts0[r1] == 0:
            continue
        p1 = counts0[r1] / N0
        counts1 = counts0.copy()
        counts1[r1] -= 1
        N1 = N0 - 1
        for r2 in range(1, 14):
            if counts1[r2] == 0:
                continue
            p2 = counts1[r2] / N1
            counts2 = counts1.copy()
            counts2[r2] -= 1
            N2 = N1 - 1
            for r3 in range(1, 14):
                if counts2[r3] == 0:
                    continue
                p3 = counts2[r3] / N2
                counts3 = counts2.copy()
                counts3[r3] -= 1
                N3 = N2 - 1
                for r4 in range(1, 14):
                    if counts3[r4] == 0:
                        continue
                    p4 = counts3[r4] / N3
                    # Player hand: r1 & r3, Banker: r2 & r4
                    has_pair = (r1 == r3) or (r2 == r4)
                    if has_pair:
                        total_prob += p1 * p2 * p3 * p4
    return total_prob


def prob_natural_win(shoe: ShoeState) -> float:
    """Exact probability that at least one hand is a natural 8 or 9 (first two cards sum to 8 or 9)."""
    N0 = shoe.cards_remaining
    counts0 = {r: shoe.card_counts.get(r, 0) for r in range(1, 14)}
    total_prob = 0.0
    for r1 in range(1, 14):
        if counts0[r1] == 0:
            continue
        p1 = counts0[r1] / N0
        counts1 = counts0.copy()
        counts1[r1] -= 1
        N1 = N0 - 1
        for r2 in range(1, 14):
            if counts1[r2] == 0:
                continue
            p2 = counts1[r2] / N1
            counts2 = counts1.copy()
            counts2[r2] -= 1
            N2 = N1 - 1
            for r3 in range(1, 14):
                if counts2[r3] == 0:
                    continue
                p3 = counts2[r3] / N2
                counts3 = counts2.copy()
                counts3[r3] -= 1
                N3 = N2 - 1
                for r4 in range(1, 14):
                    if counts3[r4] == 0:
                        continue
                    p4 = counts3[r4] / N3
                    player_val = (card_value(r1) + card_value(r3)) % 10
                    banker_val = (card_value(r2) + card_value(r4)) % 10
                    if player_val in (8, 9) or banker_val in (8, 9):
                        total_prob += p1 * p2 * p3 * p4
    return total_prob


def prob_natural_tie(shoe: ShoeState) -> float:
    """Probability that both hands are naturals and equal (both 8 or both 9)."""
    N0 = shoe.cards_remaining
    counts0 = {r: shoe.card_counts.get(r, 0) for r in range(1, 14)}
    total_prob = 0.0
    for r1 in range(1, 14):
        if counts0[r1] == 0:
            continue
        p1 = counts0[r1] / N0
        counts1 = counts0.copy()
        counts1[r1] -= 1
        N1 = N0 - 1
        for r2 in range(1, 14):
            if counts1[r2] == 0:
                continue
            p2 = counts1[r2] / N1
            counts2 = counts1.copy()
            counts2[r2] -= 1
            N2 = N1 - 1
            for r3 in range(1, 14):
                if counts2[r3] == 0:
                    continue
                p3 = counts2[r3] / N2
                counts3 = counts2.copy()
                counts3[r3] -= 1
                N3 = N2 - 1
                for r4 in range(1, 14):
                    if counts3[r4] == 0:
                        continue
                    p4 = counts3[r4] / N3
                    player_val = (card_value(r1) + card_value(r3)) % 10
                    banker_val = (card_value(r2) + card_value(r4)) % 10
                    if player_val in (8, 9) and player_val == banker_val:
                        total_prob += p1 * p2 * p3 * p4
    return total_prob


def prob_highest_hand_nine(shoe: ShoeState) -> float:
    """Probability that the highest of the two first-two-card hand totals is exactly 9."""
    N0 = shoe.cards_remaining
    counts0 = {r: shoe.card_counts.get(r, 0) for r in range(1, 14)}
    total_prob = 0.0
    for r1 in range(1, 14):
        if counts0[r1] == 0:
            continue
        p1 = counts0[r1] / N0
        counts1 = counts0.copy()
        counts1[r1] -= 1
        N1 = N0 - 1
        for r2 in range(1, 14):
            if counts1[r2] == 0:
                continue
            p2 = counts1[r2] / N1
            counts2 = counts1.copy()
            counts2[r2] -= 1
            N2 = N1 - 1
            for r3 in range(1, 14):
                if counts2[r3] == 0:
                    continue
                p3 = counts2[r3] / N2
                counts3 = counts2.copy()
                counts3[r3] -= 1
                N3 = N2 - 1
                for r4 in range(1, 14):
                    if counts3[r4] == 0:
                        continue
                    p4 = counts3[r4] / N3
                    player_val = (card_value(r1) + card_value(r3)) % 10
                    banker_val = (card_value(r2) + card_value(r4)) % 10
                    if max(player_val, banker_val) == 9:
                        total_prob += p1 * p2 * p3 * p4
    return total_prob


def prob_highest_hand_odd(shoe: ShoeState) -> float:
    """Probability that the highest of the two first-two-card hand totals is odd (1,3,5,7,9)."""
    N0 = shoe.cards_remaining
    counts0 = {r: shoe.card_counts.get(r, 0) for r in range(1, 14)}
    total_prob = 0.0
    for r1 in range(1, 14):
        if counts0[r1] == 0:
            continue
        p1 = counts0[r1] / N0
        counts1 = counts0.copy()
        counts1[r1] -= 1
        N1 = N0 - 1
        for r2 in range(1, 14):
            if counts1[r2] == 0:
                continue
            p2 = counts1[r2] / N1
            counts2 = counts1.copy()
            counts2[r2] -= 1
            N2 = N1 - 1
            for r3 in range(1, 14):
                if counts2[r3] == 0:
                    continue
                p3 = counts2[r3] / N2
                counts3 = counts2.copy()
                counts3[r3] -= 1
                N3 = N2 - 1
                for r4 in range(1, 14):
                    if counts3[r4] == 0:
                        continue
                    p4 = counts3[r4] / N3
                    player_val = (card_value(r1) + card_value(r3)) % 10
                    banker_val = (card_value(r2) + card_value(r4)) % 10
                    if max(player_val, banker_val) % 2 == 1:
                        total_prob += p1 * p2 * p3 * p4
    return total_prob
