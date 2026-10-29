from .entries import Entry


def dedupe(entries):
    """Drop repeated submissions (the client retries on timeout)."""
    return list(set(entries))


def best_per_player(entries):
    best = {}
    for e in dedupe(entries):
        if e.player not in best or e.score > best[e.player].score:
            best[e.player] = e
    return list(best.values())


def standings(entries):
    ranked = sorted(best_per_player(entries), key=lambda e: e.score, reverse=True)
    return [(i + 1, e.player, e.score) for i, e in enumerate(ranked)]
