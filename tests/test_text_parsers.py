"""Parsers that read page text, checked against trimmed copies of the real pages."""
import datetime as dt

from tinseltown.fetch import Page
from tinseltown.parsers import acropolis, elcapitan, vista

START, END = dt.date(2026, 10, 30), dt.date(2026, 11, 5)


class FakeFetcher:
    def __init__(self, text):
        self.text = text

    def page(self, url, scroll=True):
        return Page(url, 200, "", self.text)


def venue(name):
    return {"venue": name, "urls": ["https://example.com/"]}


def test_elcapitan_runs_and_repeats():
    text = "\n".join([
        "TICKETS ON SALE NOW!", "The Nightmare Before Christmas in 4D", "OCT 30 - NOV 01", "1 HR 16 MIN",
        "TICKETS ON SALE NOW!", "DUMBO", "NOV 07", "1 HR 4 MIN",
        "TICKETS ON SALE NOW!", "The Nightmare Before Christmas in 4D", "OCT 30 - NOV 01", "1 HR 16 MIN",
    ])
    rows = elcapitan.collect(FakeFetcher(text), venue("El Capitan"), START, END)
    assert [(r.title, r.formats, len(r.dates)) for r in rows] == [("The Nightmare Before Christmas", [], 3)]
    assert rows[0].format_raw == "4D"


def test_vista_dates_come_before_title():
    text = "\n".join([
        "OCTOBER", "30TH", "Friday", "3:00 PM", "31ST", "Saturday", "3:00 PM",
        "KEN RUSSELL’S THE DEVILS", "1971 | 1h 54m | 35mm Presentation", "DIRECTOR", "Ken Russell",
        "NOVEMBER", "28TH", "Saturday", "10:00 AM", "MATINEE",
        "STATION WEST", "1948 | 1h 37m | 35mm Presentation",
    ])
    rows = vista.collect(FakeFetcher(text), venue("The Vista"), START, END)
    assert len(rows) == 1
    r = rows[0]
    assert (r.year, r.times, r.formats, r.dates) == ("1971", "3:00 pm", ["35mm"],
                                                     [dt.date(2026, 10, 30), dt.date(2026, 10, 31)])


def test_acropolis_director_and_note():
    text = "\n".join([
        "SCREENING CALENDAR", "November 1, 2026", "8:00pm", "Cenote", "(Dir. Kaori Oda, 2019)",
        "Los Angeles premiere! Director in person!", "MORE INFO", "PAST SCREENINGS",
    ])
    [r] = acropolis.collect(FakeFetcher(text), venue("Acropolis"), START, END)
    assert (r.title, r.director, r.year, r.times) == ("Cenote", "Kaori Oda", "2019", "8:00pm")
    assert r.events == ["Intro/guest", "Premiere"]
