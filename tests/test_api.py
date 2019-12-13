import pytest
import json
import requests
import copy

try:
    import unittest.mock as mock
except ImportError:
    import mock
import time
from decimal import Decimal

from qtrade_client.api import QtradeAPI, QtradeAuth, APIException


@pytest.fixture
def api():
    return QtradeAPI("http://localhost:9898/")

@pytest.fixture
def api_with_market():
    api = QtradeAPI("http://localhost:9898/")
# manually set lazily loaded properties
    api._markets_map = {
        "LTC_BTC": {
            "base_currency": {
                "can_withdraw": True,
                "code": "BTC",
                "config": {
                    "address_version": 0,
                    "default_signer": 6,
                    "explorerAddressURL": "https: //live.blockcypher.com/btc/address/",
                    "explorerTransactionURL": "https: //live.blockcypher.com/btc/tx/",
                    "p2sh_address_version": 5,
                    "price": 8614.27,
                    "required_confirmations": 2,
                    "required_generate_confirmations": 100,
                    "satoshi_per_byte": 15,
                    "withdraw_fee": "0.0005",
                },
                "long_name": "Bitcoin",
                "metadata": {"withdraw_notices": []},
                "precision": 8,
                "status": "ok",
                "type": "bitcoin_like",
            },
            "can_cancel": True,
            "can_trade": True,
            "can_view": True,
            "id": 1,
            "maker_fee": "0",
            "market_currency": {
                "can_withdraw": True,
                "code": "LTC",
                "config": {
                    "additional_versions": [5],
                    "address_version": 48,
                    "default_signer": 5,
                    "explorerAddressURL": "https: //live.blockcypher.com/ltc/address/",
                    "explorerTransactionURL": "https: //live.blockcypher.com/ltc/tx/",
                    "p2sh_address_version": 50,
                    "price": 58.73,
                    "required_confirmations": 10,
                    "required_generate_confirmations": 100,
                    "satoshi_per_byte": 105,
                    "withdraw_fee": "0.001",
                },
                "long_name": "Litecoin",
                "metadata": {},
                "precision": 8,
                "status": "ok",
                "type": "bitcoin_like",
            },
            "metadata": {},
            "string": "LTC_BTC",
            "taker_fee": "0.005",
        },
        1: {
            "base_currency": {
                "can_withdraw": True,
                "code": "BTC",
                "config": {
                    "address_version": 0,
                    "default_signer": 6,
                    "explorerAddressURL": "https: //live.blockcypher.com/btc/address/",
                    "explorerTransactionURL": "https: //live.blockcypher.com/btc/tx/",
                    "p2sh_address_version": 5,
                    "price": 8614.27,
                    "required_confirmations": 2,
                    "required_generate_confirmations": 100,
                    "satoshi_per_byte": 15,
                    "withdraw_fee": "0.0005",
                },
                "long_name": "Bitcoin",
                "metadata": {"withdraw_notices": []},
                "precision": 8,
                "status": "ok",
                "type": "bitcoin_like",
            },
            "can_cancel": True,
            "can_trade": True,
            "can_view": True,
            "id": 1,
            "maker_fee": "0",
            "market_currency": {
                "can_withdraw": True,
                "code": "LTC",
                "config": {
                    "additional_versions": [5],
                    "address_version": 48,
                    "default_signer": 5,
                    "explorerAddressURL": "https: //live.blockcypher.com/ltc/address/",
                    "explorerTransactionURL": "https: //live.blockcypher.com/ltc/tx/",
                    "p2sh_address_version": 50,
                    "price": 58.73,
                    "required_confirmations": 10,
                    "required_generate_confirmations": 100,
                    "satoshi_per_byte": 105,
                    "withdraw_fee": "0.001",
                },
                "long_name": "Litecoin",
                "metadata": {},
                "precision": 8,
                "status": "ok",
                "type": "bitcoin_like",
            },
            "metadata": {},
            "string": "LTC_BTC",
            "taker_fee": "0.005",
        },
    }
    api._tickers = {
        1: {
            "ask": "0.00707017",
            "bid": "0.00664751",
            "day_avg_price": "0.0071579647440367",
            "day_change": "0.0173330516998029",
            "day_high": "0.00727268",
            "day_low": "0.00713415",
            "day_open": "0.00714877",
            "day_volume_base": "0.00169664",
            "day_volume_market": "0.23702827",
            "id": 1,
            "id_hr": "LTC_BTC",
            "last": "0.00727268",
        },
        "LTC_BTC": {
            "ask": "0.00707017",
            "bid": "0.00664751",
            "day_avg_price": "0.0071579647440367",
            "day_change": "0.0173330516998029",
            "day_high": "0.00727268",
            "day_low": "0.00713415",
            "day_open": "0.00714877",
            "day_volume_base": "0.00169664",
            "day_volume_market": "0.23702827",
            "id": 1,
            "id_hr": "LTC_BTC",
            "last": "0.00727268",
        },
    }

    # prevent lazily loaded properties from updating and making http calls
    def ret(*args, **kwargs):
        return

    api._refresh_tickers = ret
    api._refresh_common = ret

    return api


@mock.patch("time.time", mock.MagicMock(return_value=12345))
def test_hmac():
    s = requests.Session()
    s.auth = QtradeAuth("256:vwj043jtrw4o5igw4oi5jwoi45g")
    r = s.prepare_request(requests.Request("GET", "http://google.com/"))
    assert (
        r.headers["Authorization"]
        == "HMAC-SHA256 256:iyfC4n+bE+3hLgMJns1Z67FKA7O5qm5PgDvZHGraMTQ="
    )


@mock.patch("time.time", mock.MagicMock(return_value=10))
def test_hard_limit(api):
    api.rl_remaining = 0
    api.rl_reset_at = 15
    time.sleep = mock.MagicMock()
    # Just to not bomb out on an actual request
    api.rs.request = mock.MagicMock(return_value=mock.MagicMock(status_code=200))
    api.get("/v1/common")
    # Test that the rate limit sleep was called
    time.sleep.assert_called_with(5)


@mock.patch("time.time", mock.MagicMock(return_value=10))
def test_soft_limit(api):
    api.rl_remaining = 1
    api.rl_reset_at = 12
    api.rl_limit = 60
    api.rl_soft_threshold = -30
    time.sleep = mock.MagicMock()
    # Just to not bomb out on an actual request
    api.rs.request = mock.MagicMock(return_value=mock.MagicMock(status_code=200))
    api.get("/v1/common")
    # Test that the rate limit sleep was called
    time.sleep.assert_called_with(2)


def test_300_status(api):
    api.rs.request = mock.MagicMock(return_value=mock.MagicMock(status_code=300))
    with pytest.raises(APIException):
        api.get("/v1/common")


def test_429_status(api):
    api.rs.request = mock.MagicMock(return_value=mock.MagicMock(status_code=429))
    with pytest.raises(APIException):
        api.get("/v1/common")
    # the client should retry once on a 429
    assert api.rs.request.call_count == 2


def test_200_exception_status(api):
    # trying to parse the request's json will raise an exception
    def res_json():
        raise Exception

    api.rs.request = mock.MagicMock(
        return_value=mock.MagicMock(status_code=200, json=res_json)
    )
    assert api.get("/v1/common") is True


def test_300_exception_status(api):
    # trying to parse the request's json will raise an exception
    def res_json():
        raise Exception

    with pytest.raises(APIException):
        api.rs.request = mock.MagicMock(
            return_value=mock.MagicMock(status_code=300, json=res_json)
        )
        api.get("/v1/common")


def test_balances(api):
    api._req = mock.MagicMock(
        return_value=json.loads(
            """
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
  }"""
        )
    )
    bal = api.balances()
    assert bal == {
        "TAO": Decimal("1"),
        "ZANO": Decimal("0.14355714"),
        "VLS": Decimal("0"),
    }


def test_balances_all(api):
    api._req = mock.MagicMock(
        return_value=json.loads(
            """
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
  }"""
        )
    )
    bal = api.balances_merged()
    assert bal == {
        "BIS": Decimal("6.97936"),
        "BTC": Decimal("0.3678952"),
        "BAN": Decimal("401184.76191351"),
    }
    bal = api.balances_all()
    assert bal == {
        "spendable": {"BIS": Decimal("6.97936"), "BTC": Decimal("0.1970952")},
        "in_orders": {"BAN": Decimal("401184.76191351"), "BTC": Decimal("0.1708")},
    }


def test_refresh_common(api):
    ret = {"currencies": [
    {"can_withdraw": False,
        "code": "GRIN",
        "config": {"default_signer": 61,
                   "price": 10.537737418408733,
                   "required_confirmations": 10,
                   "withdraw_fee": "0.25"},
        "long_name": "Grin",
        "metadata": {"delisting_date": "4/11/2019",
                     "deposit_notices": [{
                        "message": "Deposits MUST be greater than 0.75 GRIN. Deposits for less than that amount will be rejected!",
                        "type": "warning"}]},
        "precision": 9,
        "status": "delisted",
        "type": "grin"},
    {"can_withdraw": True,
        "code": "LTC",
        "config": {"additional_versions": [5],
                   "address_version": 48,
                   "default_signer": 5,
                   "explorerAddressURL": "https://live.blockcypher.com/ltc/address/",
                   "explorerTransactionURL": "https://live.blockcypher.com/ltc/tx/",
                   "p2sh_address_version": 50,
                   "price": 60.63,
                   "required_confirmations": 10,
                   "required_generate_confirmations": 100,
                   "satoshi_per_byte": 105,
                   "withdraw_fee": "0.001"},
        "long_name": "Litecoin",
        "metadata": {},
        "precision": 8,
        "status": "ok",
        "type": "bitcoin_like"},
    {"can_withdraw": True,
        "code": "BTC",
        "long_name": "Bitcoin",
        "type": "bitcoin_like",
        "status": "ok",
        "precision": 8,
        "config": {
            "price": 8595.59,
            "withdraw_fee": "0.0005",
            "default_signer": 6,
            "address_version": 0,
            "satoshi_per_byte": 15,
            "explorerAddressURL": "https://live.blockcypher.com/btc/address/",
            "p2sh_address_version": 5,
            "explorerTransactionURL": "https://live.blockcypher.com/btc/tx/",
            "required_confirmations": 2,
            "required_generate_confirmations": 100
        },
        "metadata": {
            "withdraw_notices": []
        }
    },
    {"can_withdraw": True,
        "code": "BIS",
        "config": {"data_max": 1000,
            "default_signer": 54,
            "enable_address_data": True,
            "explorerAddressURL": "https://bismuth.online/search?quicksearch=",
            "explorerTransactionURL": "https://bismuth.online/search?quicksearch=",
            "price": 0.11933604157103646,
            "required_confirmations": 35,
            "withdraw_fee": "0.25"},
        "long_name": "Bismuth",
        "metadata": {"deposit_notices": [], "hidden": False},
        "precision": 8,
        "status": "ok",
        "type": "bismuth"}],
"markets": [
    {"base_currency": "BTC",
        "can_cancel": False,
        "can_trade": False,
        "can_view": False,
        "id": 23,
        "maker_fee": "0",
        "market_currency": "GRIN",
        "metadata": {"delisting_date": "4/11/2019",
            "labels": [],
            "market_notices": [{"message": "Delisting Notice: This market is being closed. Please cancel your orders and withdraw your funds by 4/11/2019.",
                "type": "warning"}]},
            "taker_fee": "0.0075"},
    {"base_currency": "BTC",
        "can_cancel": True,
        "can_trade": True,
        "can_view": True,
        "id": 1,
        "maker_fee": "0",
        "market_currency": "LTC",
        "metadata": {},
        "taker_fee": "0.005"},
    {"base_currency": "BTC",
        "can_cancel": True,
        "can_trade": True,
        "can_view": True,
        "id": 20,
        "maker_fee": "0",
        "market_currency": "BIS",
        "metadata": {"labels": []},
        "taker_fee": "0.005"}]}
    api._req = mock.MagicMock(return_value=ret)
    assert api.markets["GRIN_BTC"] == ret["markets"][0]
    assert api.markets["LTC_BTC"] == ret["markets"][1]
    assert api.markets["BIS_BTC"] == ret["markets"][2]
    assert api.currencies["GRIN"] == ret["currencies"][0]
    assert api.currencies["LTC"] == ret["currencies"][1]
    assert api.currencies["BTC"] == ret["currencies"][2]
    assert api.currencies["BIS"] == ret["currencies"][3]


def test_refresh_tickers(api):
    ret = {"markets": [
        {
            "ask": "0.00001499",
            "bid": "0.00001332",
            "day_avg_price": "0.0000146739216644",
            "day_change": "-0.0893074119076549",
            "day_high": "0.00001641",
            "day_low": "0.00001292",
            "day_open": "0.00001646",
            "day_volume_base": "0.37996235",
            "day_volume_market": "25893.7153059",
            "id": 20,
            "id_hr": "BIS_BTC",
            "last": "0.00001499"
        },
        {
            "ask": None,
            "bid": None,
            "day_avg_price": None,
            "day_change": None,
            "day_high": None,
            "day_low": None,
            "day_open": None,
            "day_volume_base": "0",
            "day_volume_market": "0",
            "id": 8,
            "id_hr": "MMO_BTC",
            "last": "0.00000076"
    }]}
    api._req = mock.MagicMock(return_value=ret)
    assert api.tickers[20] == api.tickers["BIS_BTC"] == ret['markets'][0]
    assert api.tickers[8] == api.tickers["MMO_BTC"] == ret['markets'][1]


def test_orders(api):
    ret = {"orders": [
        {
            "id": 8980903,
            "market_amount": "0.5672848",
            "market_amount_remaining": "0.5672848",
            "created_at": "2019-11-14T16:34:20.424601Z",
            "price": "0.00651044",
            "base_amount": "0.00371174",
            "order_type": "buy_limit",
            "market_id": 1,
            "open": True,
            "trades": None
        },
        {
            "id": 8980902,
            "market_amount": "0.37039118",
            "market_amount_remaining": "0.37039118",
            "created_at": "2019-11-14T16:34:20.380538Z",
            "price": "0.00664751",
            "base_amount": "0.00247449",
            "order_type": "buy_limit",
            "market_id": 1,
            "open": True,
            "trades": None
        },
        {
            "id": 8980901,
            "market_amount": "12973.17366652",
            "market_amount_remaining": "12973.17366652",
            "created_at": "2019-11-14T16:34:20.328834Z",
            "price": "0.00000037",
            "order_type": "sell_limit",
            "market_id": 36,
            "open": True,
            "trades": None
        }
    ]}
    api._req = mock.MagicMock(return_value=ret)
    assert api.orders(open=True) == ret['orders']
    calls = [
        mock.call("get", "/v1/user/orders", newer_than=None, older_than=None, open='true'),
    ]
    api._req.assert_has_calls(calls)


order_return = {
        "order": {
            "id": 8987684,
            "market_amount": "0.01",
            "market_amount_remaining": "0.01",
            "created_at": "2019-11-14T23:46:52.897345Z",
            "price": "1",
            "order_type": "sell_limit",
            "market_id": 1,
            "open": True,
            "trades": [],
        }
    }

def test_sell_order(api_with_market):
    api = api_with_market
    ret = copy.deepcopy(order_return)

    api._req = mock.MagicMock(return_value=ret)
    o = api.order(
        "sell_limit", 1, amount=0.01, market_string="LTC_BTC", prevent_taker=True
    )
    assert o == ret
    api._req.assert_called_with('post', '/v1/user/sell_limit', amount='0.01', market_id=1, price='1.00000000')


def test_buy_order(api_with_market):
    api = api_with_market
    ret = copy.deepcopy(order_return)
    ret['order']['market_amount'] = "1.99004975"
    ret['order']['market_amount_remaining'] = "1.99004975"

    api._req = mock.MagicMock(return_value=ret)
    o = api.order("buy_limit", 0.005, value=0.01, market_id=1)
    assert o == ret
    api._req.assert_called_with('post', '/v1/user/buy_limit', amount='1.99004975', market_id=1, price='0.00500000')


def test_sell_order_value(api_with_market):
    api = api_with_market
    ret = copy.deepcopy(order_return)
    ret['order']['market_amount'] = "0.01000000"
    ret['order']['market_amount_remaining'] = "0.01000000"
    ret['order']['price'] = "1.00000000"

    api._req = mock.MagicMock(return_value=ret)
    o = api.order("sell_limit", 1, value=0.01, market_id=1)
    assert o['order']['market_amount'] == ret['order']['market_amount']
    assert o['order']['market_amount_remaining'] == ret['order']['market_amount_remaining']
    assert o ['order']['price'] == ret['order']['price']
    api._req.assert_called_with('post', '/v1/user/sell_limit', amount='0.01000000', market_id=1, price='1.00000000')


def test_prevented_taker_buy(api_with_market):
    api = api_with_market
    api._req = mock.MagicMock(return_value=order_return)
    o = api.order("buy_limit", 0.1, value=0.01, market_id=1, prevent_taker=True)
    assert o == "order not placed"


def test_prevented_taker_sell(api_with_market):
    api = api_with_market
    api._req = mock.MagicMock(return_value=order_return)
    o = api.order("sell_limit", 0.001, value=0.01, market_id=1, prevent_taker=True)
    assert o == "order not placed"


def test_sell_null_bid(api_with_market):
    api = api_with_market
    api._req = mock.MagicMock(return_value=order_return)
    api._tickers[1]["bid"] = None
    o = api.order("sell_limit", 1, value=0.01, market_id=1, prevent_taker=True)
    assert o != "order not placed"


def test_sell_null_ask(api_with_market):
    api = api_with_market
    api._req = mock.MagicMock(return_value=order_return)
    api._tickers[1]["ask"] = None
    o = api.order("sell_limit", 1, value=0.01, market_id=1, prevent_taker=True)
    assert o != "order not placed"


def test_order_no_value_amount(api):
    # test attempted order when neither value nor amount are provided
    with pytest.raises(ValueError):
        api.order("sell_limit", 0.001, market_id=1)


def test_order_both_value_amount(api):
    with pytest.raises(ValueError):
        api.order("sell_limit", 0.001, value=0.01, amount=0.01, market_id=1)


def test_order_no_id_string(api):
    with pytest.raises(ValueError):
        api.order("sell_limit", 0.001, value=0.01)


def test_order_both_id_string(api):
    with pytest.raises(ValueError):
        api.order(
            "sell_limit", 0.001, value=0.01, market_id=1, market_string="LTC_BTC"
        )


def test_clone(api):
    api.set_hmac("1:11111111111")
    assert api.rs.auth is not None
    c = api.clone()
    assert c != api
    assert c.rs.auth is None


def test_cancel_all_orders(api):
    api._req = mock.MagicMock()
    ords = [
        {
            "id": 8980903,
            "market_amount": "0.5672848",
            "market_amount_remaining": "0.5672848",
            "created_at": "2019-11-14T16:34:20.424601Z",
            "price": "0.00651044",
            "base_amount": "0.00371174",
            "order_type": "buy_limit",
            "market_id": 1,
            "open": True,
            "trades": None,
        },
        {
            "id": 8980902,
            "market_amount": "0.37039118",
            "market_amount_remaining": "0.37039118",
            "created_at": "2019-11-14T16:34:20.380538Z",
            "price": "0.00664751",
            "base_amount": "0.00247449",
            "order_type": "buy_limit",
            "market_id": 1,
            "open": True,
            "trades": None,
        },
        {
            "id": 8980901,
            "market_amount": "12973.17366652",
            "market_amount_remaining": "12973.17366652",
            "created_at": "2019-11-14T16:34:20.328834Z",
            "price": "0.00000037",
            "order_type": "sell_limit",
            "market_id": 36,
            "open": True,
            "trades": None,
        },
    ]
    api.orders = mock.MagicMock(return_value=ords)

    # create a calls list, call cancel_all_orders and check the _req calls
    api.cancel_all_orders()
    calls = [
        mock.call("post", "/v1/user/cancel_order", json={"id": 8980903}),
        mock.call("post", "/v1/user/cancel_order", json={"id": 8980902}),
        mock.call("post", "/v1/user/cancel_order", json={"id": 8980901}),
    ]
    api._req.assert_has_calls(calls, any_order=True)

    # also check orders(open=True) call
    api.orders.assert_called_with(open=True)


def test_cancel_market_orders(api_with_market):
    api = api_with_market
    api._req = mock.MagicMock()
    ords = [
        {
            "id": 8980903,
            "market_amount": "0.5672848",
            "market_amount_remaining": "0.5672848",
            "created_at": "2019-11-14T16:34:20.424601Z",
            "price": "0.00651044",
            "base_amount": "0.00371174",
            "order_type": "buy_limit",
            "market_id": 1,
            "open": True,
            "trades": None,
        },
        {
            "id": 8980902,
            "market_amount": "0.37039118",
            "market_amount_remaining": "0.37039118",
            "created_at": "2019-11-14T16:34:20.380538Z",
            "price": "0.00664751",
            "base_amount": "0.00247449",
            "order_type": "buy_limit",
            "market_id": 1,
            "open": True,
            "trades": None,
        },
        {
            "id": 8980901,
            "market_amount": "12973.17366652",
            "market_amount_remaining": "12973.17366652",
            "created_at": "2019-11-14T16:34:20.328834Z",
            "price": "0.00000037",
            "order_type": "sell_limit",
            "market_id": 36,
            "open": True,
            "trades": None,
        },
    ]
    api.orders = mock.MagicMock(return_value=ords)

    api.cancel_market_orders(market_string="LTC_BTC")
    calls = [
        mock.call("post", "/v1/user/cancel_order", json={"id": 8980903}),
        mock.call("post", "/v1/user/cancel_order", json={"id": 8980902}),
    ]
    api._req.assert_has_calls(calls, any_order=True)


def test_cancel_market_orders_no_string_id(api):
    with pytest.raises(ValueError):
        api.cancel_market_orders()


def test_cancel_market_orders_both_string_id(api):
    with pytest.raises(ValueError):
        api.cancel_market_orders(market_string="LTC_BTC", market_id=36)
