def _merge(forward: list, backward: list) -> list:
    """
    forward  = [start, …, meeting]   (tuples: (id, label, via))
    backward = [end,   …, meeting]
    result   = [start, …, meeting, …, end]

    Via labels shift when reversing the backward tail so each node shows
    the correct relationship to its predecessor:
      reversed_tail[i] gets backward[-(i+1)][2]
    which places the meeting's via on the first reversed node, then cascades.
    """
    tail_reversed = list(reversed(backward[:-1]))
    corrected_tail = [
        (eid, label, backward[-(i + 1)][2])
        for i, (eid, label, _) in enumerate(tail_reversed)
    ]
    return forward + corrected_tail