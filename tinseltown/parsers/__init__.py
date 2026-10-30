"""One parser per website. Each takes (fetcher, venue, start, end) and returns Screenings.

`venue` is the venue's entry from venues.yaml; `start` and `end` bound the week (inclusive).
"""
from . import (academy, acropolis, alamo, chinese, cinematheque, elcapitan, filmforum, laemmle,
               landmark, newbev, ucla, vidiots, vista)

PARSERS = {
    "newbev": newbev.collect,
    "cinematheque": cinematheque.collect,
    "academy": academy.collect,
    "alamo": alamo.collect,
    "chinese": chinese.collect,
    "elcapitan": elcapitan.collect,
    "laemmle": laemmle.collect,
    "filmforum": filmforum.collect,
    "acropolis": acropolis.collect,
    "ucla": ucla.collect,
    "landmark": landmark.collect,
    "vidiots": vidiots.collect,
    "vista": vista.collect,
}
