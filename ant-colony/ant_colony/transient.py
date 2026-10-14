"""Opt-in bounded continuation after a finished, failed HTTP transport.

The request is never replayed here. Its full reservation remains held; the
engine skips that turn and can schedule a later, independently funded turn.
"""

from decimal import Decimal
from http.client import IncompleteRead
import time
from urllib.error import HTTPError


class TransientPolicy:
    def __init__(self, deadline, *, enabled=False):
        self.deadline = deadline
        self.enabled = enabled
        self.failures = self.consecutive = 0
        self.held = Decimal(0)
        self.not_before = 0

    def success(self):
        self.consecutive = 0
        self.not_before = 0

    def retain_and_continue(self, error, reservation):
        recognized = (isinstance(error, IncompleteRead)
                      or isinstance(error, HTTPError) and error.code in {429, 502, 503, 504})
        reserve = Decimal(str(reservation))
        if (not self.enabled or not recognized or self.deadline is None
                or time.time() >= self.deadline or self.consecutive >= 2
                or self.failures >= 8 or self.held + reserve > Decimal(10)):
            return False
        self.failures += 1
        self.consecutive += 1
        self.held += reserve
        self.not_before = time.time() + min(60, 15 * 2 ** (self.consecutive - 1))
        return True
