import pytest
import json
import requests
import unittest.mock as mock
from decimal import Decimal

from qtrade_client.api import QtradeAPI, QtradeAuth


@pytest.fixture
def api():
    return QtradeAPI("http://localhost:9898/")


@mock.patch('time.time', mock.MagicMock(return_value=12345))
def test_hmac():
    s = requests.Session()
    s.auth = QtradeAuth("256:vwj043jtrw4o5igw4oi5jwoi45g")
    r = s.prepare_request(requests.Request("GET", "http://google.com/"))
    assert r.headers['Authorization'] == "HMAC-SHA256 256:iyfC4n+bE+3hLgMJns1Z67FKA7O5qm5PgDvZHGraMTQ="


def test_balances(api):
    api._req = mock.MagicMock(return_value=json.loads("""
  {
    "balances": [
      {
        "currency": "TAO",
        "balance": "1"
      },
      {
        "currency": "ZANO",
        "balance": "0.14355714"
      },
      {
        "currency": "VLS",
        "balance": "0"
      }
    ]
  }"""))
    bal = api.balances()
    assert bal == {'TAO': Decimal('1'), 'ZANO': Decimal('0.14355714'), 'VLS': Decimal('0')}


def test_balances_all(api):
    api._req = mock.MagicMock(return_value=json.loads("""
  {
    "balances": [
      {
        "currency": "BIS",
        "balance": "6.97936"
      },
      {
        "currency": "BTC",
        "balance": "0.1970952"
      }
    ],
    "order_balances": [
      {
        "currency": "BAN",
        "balance": "401184.76191351"
      },
      {
        "currency": "BTC",
        "balance": "0.1708"
      }
    ],
    "limit_used": 0,
    "limit_remaining": 50000,
    "limit": 50000
  }"""))
    bal = api.balances_merged()
    assert bal == {'BIS': Decimal('6.97936'), 'BTC': Decimal('0.3678952'), 'BAN': Decimal('401184.76191351')}
    bal = api.balances_all()
    assert bal == {'spendable': {'BIS': Decimal('6.97936'), 'BTC': Decimal('0.1970952')}, 'in_orders': {'BAN': Decimal('401184.76191351'), 'BTC': Decimal('0.1708')}}
