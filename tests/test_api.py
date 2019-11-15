import pytest
import json
import requests
import unittest.mock as mock
import time
from decimal import Decimal

from qtrade_client.api import QtradeAPI, QtradeAuth, APIException


@pytest.fixture
def api():
    return QtradeAPI("http://localhost:9898/")


@mock.patch("time.time", mock.MagicMock(return_value=12345))
def test_hmac():
    s = requests.Session()
    s.auth = QtradeAuth("256:vwj043jtrw4o5igw4oi5jwoi45g")
    r = s.prepare_request(requests.Request("GET", "http://google.com/"))
    assert r.headers["Authorization"] == "HMAC-SHA256 256:iyfC4n+bE+3hLgMJns1Z67FKA7O5qm5PgDvZHGraMTQ="


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
    try:
        api.rs.request = mock.MagicMock(return_value=mock.MagicMock(status_code=300))
        api.get("/v1/common")
        raise AssertionError
    except(APIException):
        pass


def test_429_status(api):
    try:
        api.rs.request = mock.MagicMock(return_value=mock.MagicMock(status_code=429))
        api.get("/v1/common")
        raise AssertionError
    except(APIException):
        # the client should retry once on a 429
        assert api.rs.request.call_count == 2


def test_200_exception_status(api):
    def res_json():
        raise Exception

    api.rs.request = mock.MagicMock(return_value=mock.MagicMock(status_code=200, json=res_json))
    assert api.get("/v1/common") is True


def test_300_exception_status(api):
    def res_json():
        raise Exception

    try:
        api.rs.request = mock.MagicMock(return_value=mock.MagicMock(status_code=300, json=res_json))
        api.get("/v1/common")
        raise AssertionError
    except(APIException):
        pass


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
    assert bal == {"TAO": Decimal("1"), "ZANO": Decimal("0.14355714"), "VLS": Decimal("0")}


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
    assert bal == {"BIS": Decimal("6.97936"), "BTC": Decimal("0.3678952"), "BAN": Decimal("401184.76191351")}
    bal = api.balances_all()
    assert bal == {"spendable": {"BIS": Decimal("6.97936"), "BTC": Decimal("0.1970952")}, "in_orders": {"BAN": Decimal("401184.76191351"), "BTC": Decimal("0.1708")}}


def test_refresh_common(api):
    api._req = mock.MagicMock(return_value=json.loads("""
{"currencies": [
    {"can_withdraw": false,
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
    {"can_withdraw": true,
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
    {"can_withdraw": true,
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
    {"can_withdraw": true,
        "code": "BIS",
        "config": {"data_max": 1000,
            "default_signer": 54,
            "enable_address_data": true,
            "explorerAddressURL": "https://bismuth.online/search?quicksearch=",
            "explorerTransactionURL": "https://bismuth.online/search?quicksearch=",
            "price": 0.11933604157103646,
            "required_confirmations": 35,
            "withdraw_fee": "0.25"},
        "long_name": "Bismuth",
        "metadata": {"deposit_notices": [], "hidden": false},
        "precision": 8,
        "status": "ok",
        "type": "bismuth"}],
"markets": [
    {"base_currency": "BTC",
        "can_cancel": false,
        "can_trade": false,
        "can_view": false,
        "id": 23,
        "maker_fee": "0",
        "market_currency": "GRIN",
        "metadata": {"delisting_date": "4/11/2019",
            "labels": [],
            "market_notices": [{"message": "Delisting Notice: This market is being closed. Please cancel your orders and withdraw your funds by 4/11/2019.",
                "type": "warning"}]},
            "taker_fee": "0.0075"},
    {"base_currency": "BTC",
        "can_cancel": true,
        "can_trade": true,
        "can_view": true,
        "id": 1,
        "maker_fee": "0",
        "market_currency": "LTC",
        "metadata": {},
        "taker_fee": "0.005"},
    {"base_currency": "BTC",
        "can_cancel": true,
        "can_trade": true,
        "can_view": true,
        "id": 20,
        "maker_fee": "0",
        "market_currency": "BIS",
        "metadata": {"labels": []},
        "taker_fee": "0.005"}],
 "tickers": [{"ask": "0.00714721",
              "bid": "0.00672976",
              "day_avg_price": "0.0071178566133255",
              "day_change": "-0.013393009668933",
              "day_high": "0.00734334",
              "day_low": "0.00693048",
              "day_open": "0.00702456",
              "day_volume_base": "0.00635845",
              "day_volume_market": "0.89330965",
              "id": 1,
              "id_hr": "LTC_BTC",
              "last": "0.00693048"},
             {"ask": "0.0000163",
              "bid": "0.0000153",
              "day_avg_price": "0.0000157158062873",
              "day_change": "0.01875",
              "day_high": "0.00001643",
              "day_low": "0.00001313",
              "day_open": "0.000016",
              "day_volume_base": "0.27043909",
              "day_volume_market": "17208.09515317",
              "id": 20,
              "id_hr": "BIS_BTC",
              "last": "0.0000163"}]}"""))
    assert api.markets == {'GRIN_BTC': {'base_currency': {'can_withdraw': True, 'code': 'BTC', 'long_name': 'Bitcoin', 'type': 'bitcoin_like', 'status': 'ok', 'precision': 8, 'config': {'price': 8595.59, 'withdraw_fee': '0.0005', 'default_signer': 6, 'address_version': 0, 'satoshi_per_byte': 15, 'explorerAddressURL': 'https://live.blockcypher.com/btc/address/', 'p2sh_address_version': 5, 'explorerTransactionURL': 'https://live.blockcypher.com/btc/tx/', 'required_confirmations': 2, 'required_generate_confirmations': 100}, 'metadata': {'withdraw_notices': []}}, 'can_cancel': False, 'can_trade': False, 'can_view': False, 'id': 23, 'maker_fee': '0', 'market_currency': {'can_withdraw': False, 'code': 'GRIN', 'config': {'default_signer': 61, 'price': 10.537737418408733, 'required_confirmations': 10, 'withdraw_fee': '0.25'}, 'long_name': 'Grin', 'metadata': {'delisting_date': '4/11/2019', 'deposit_notices': [{'message': 'Deposits MUST be greater than 0.75 GRIN. Deposits for less than that amount will be rejected!', 'type': 'warning'}]}, 'precision': 9, 'status': 'delisted', 'type': 'grin'}, 'metadata': {'delisting_date': '4/11/2019', 'labels': [], 'market_notices': [{'message': 'Delisting Notice: This market is being closed. Please cancel your orders and withdraw your funds by 4/11/2019.', 'type': 'warning'}]}, 'taker_fee': '0.0075', 'string': 'GRIN_BTC'}, 'LTC_BTC': {'base_currency': {'can_withdraw': True, 'code': 'BTC', 'long_name': 'Bitcoin', 'type': 'bitcoin_like', 'status': 'ok', 'precision': 8, 'config': {'price': 8595.59, 'withdraw_fee': '0.0005', 'default_signer': 6, 'address_version': 0, 'satoshi_per_byte': 15, 'explorerAddressURL': 'https://live.blockcypher.com/btc/address/', 'p2sh_address_version': 5, 'explorerTransactionURL': 'https://live.blockcypher.com/btc/tx/', 'required_confirmations': 2, 'required_generate_confirmations': 100}, 'metadata': {'withdraw_notices': []}}, 'can_cancel': True, 'can_trade': True, 'can_view': True, 'id': 1, 'maker_fee': '0', 'market_currency': {'can_withdraw': True, 'code': 'LTC', 'config': {'additional_versions': [5], 'address_version': 48, 'default_signer': 5, 'explorerAddressURL': 'https://live.blockcypher.com/ltc/address/', 'explorerTransactionURL': 'https://live.blockcypher.com/ltc/tx/', 'p2sh_address_version': 50, 'price': 60.63, 'required_confirmations': 10, 'required_generate_confirmations': 100, 'satoshi_per_byte': 105, 'withdraw_fee': '0.001'}, 'long_name': 'Litecoin', 'metadata': {}, 'precision': 8, 'status': 'ok', 'type': 'bitcoin_like'}, 'metadata': {}, 'taker_fee': '0.005', 'string': 'LTC_BTC'}, 'BIS_BTC': {'base_currency': {'can_withdraw': True, 'code': 'BTC', 'long_name': 'Bitcoin', 'type': 'bitcoin_like', 'status': 'ok', 'precision': 8, 'config': {'price': 8595.59, 'withdraw_fee': '0.0005', 'default_signer': 6, 'address_version': 0, 'satoshi_per_byte': 15, 'explorerAddressURL': 'https://live.blockcypher.com/btc/address/', 'p2sh_address_version': 5, 'explorerTransactionURL': 'https://live.blockcypher.com/btc/tx/', 'required_confirmations': 2, 'required_generate_confirmations': 100}, 'metadata': {'withdraw_notices': []}}, 'can_cancel': True, 'can_trade': True, 'can_view': True, 'id': 20, 'maker_fee': '0', 'market_currency': {'can_withdraw': True, 'code': 'BIS', 'config': {'data_max': 1000, 'default_signer': 54, 'enable_address_data': True, 'explorerAddressURL': 'https://bismuth.online/search?quicksearch=', 'explorerTransactionURL': 'https://bismuth.online/search?quicksearch=', 'price': 0.11933604157103646, 'required_confirmations': 35, 'withdraw_fee': '0.25'}, 'long_name': 'Bismuth', 'metadata': {'deposit_notices': [], 'hidden': False}, 'precision': 8, 'status': 'ok', 'type': 'bismuth'}, 'metadata': {'labels': []}, 'taker_fee': '0.005', 'string': 'BIS_BTC'}, 23: {'base_currency': {'can_withdraw': True, 'code': 'BTC', 'long_name': 'Bitcoin', 'type': 'bitcoin_like', 'status': 'ok', 'precision': 8, 'config': {'price': 8595.59, 'withdraw_fee': '0.0005', 'default_signer': 6, 'address_version': 0, 'satoshi_per_byte': 15, 'explorerAddressURL': 'https://live.blockcypher.com/btc/address/', 'p2sh_address_version': 5, 'explorerTransactionURL': 'https://live.blockcypher.com/btc/tx/', 'required_confirmations': 2, 'required_generate_confirmations': 100}, 'metadata': {'withdraw_notices': []}}, 'can_cancel': False, 'can_trade': False, 'can_view': False, 'id': 23, 'maker_fee': '0', 'market_currency': {'can_withdraw': False, 'code': 'GRIN', 'config': {'default_signer': 61, 'price': 10.537737418408733, 'required_confirmations': 10, 'withdraw_fee': '0.25'}, 'long_name': 'Grin', 'metadata': {'delisting_date': '4/11/2019', 'deposit_notices': [{'message': 'Deposits MUST be greater than 0.75 GRIN. Deposits for less than that amount will be rejected!', 'type': 'warning'}]}, 'precision': 9, 'status': 'delisted', 'type': 'grin'}, 'metadata': {'delisting_date': '4/11/2019', 'labels': [], 'market_notices': [{'message': 'Delisting Notice: This market is being closed. Please cancel your orders and withdraw your funds by 4/11/2019.', 'type': 'warning'}]}, 'taker_fee': '0.0075', 'string': 'GRIN_BTC'}, 1: {'base_currency': {'can_withdraw': True, 'code': 'BTC', 'long_name': 'Bitcoin', 'type': 'bitcoin_like', 'status': 'ok', 'precision': 8, 'config': {'price': 8595.59, 'withdraw_fee': '0.0005', 'default_signer': 6, 'address_version': 0, 'satoshi_per_byte': 15, 'explorerAddressURL': 'https://live.blockcypher.com/btc/address/', 'p2sh_address_version': 5, 'explorerTransactionURL': 'https://live.blockcypher.com/btc/tx/', 'required_confirmations': 2, 'required_generate_confirmations': 100}, 'metadata': {'withdraw_notices': []}}, 'can_cancel': True, 'can_trade': True, 'can_view': True, 'id': 1, 'maker_fee': '0', 'market_currency': {'can_withdraw': True, 'code': 'LTC', 'config': {'additional_versions': [5], 'address_version': 48, 'default_signer': 5, 'explorerAddressURL': 'https://live.blockcypher.com/ltc/address/', 'explorerTransactionURL': 'https://live.blockcypher.com/ltc/tx/', 'p2sh_address_version': 50, 'price': 60.63, 'required_confirmations': 10, 'required_generate_confirmations': 100, 'satoshi_per_byte': 105, 'withdraw_fee': '0.001'}, 'long_name': 'Litecoin', 'metadata': {}, 'precision': 8, 'status': 'ok', 'type': 'bitcoin_like'}, 'metadata': {}, 'taker_fee': '0.005', 'string': 'LTC_BTC'}, 20: {'base_currency': {'can_withdraw': True, 'code': 'BTC', 'long_name': 'Bitcoin', 'type': 'bitcoin_like', 'status': 'ok', 'precision': 8, 'config': {'price': 8595.59, 'withdraw_fee': '0.0005', 'default_signer': 6, 'address_version': 0, 'satoshi_per_byte': 15, 'explorerAddressURL': 'https://live.blockcypher.com/btc/address/', 'p2sh_address_version': 5, 'explorerTransactionURL': 'https://live.blockcypher.com/btc/tx/', 'required_confirmations': 2, 'required_generate_confirmations': 100}, 'metadata': {'withdraw_notices': []}}, 'can_cancel': True, 'can_trade': True, 'can_view': True, 'id': 20, 'maker_fee': '0', 'market_currency': {'can_withdraw': True, 'code': 'BIS', 'config': {'data_max': 1000, 'default_signer': 54, 'enable_address_data': True, 'explorerAddressURL': 'https://bismuth.online/search?quicksearch=', 'explorerTransactionURL': 'https://bismuth.online/search?quicksearch=', 'price': 0.11933604157103646, 'required_confirmations': 35, 'withdraw_fee': '0.25'}, 'long_name': 'Bismuth', 'metadata': {'deposit_notices': [], 'hidden': False}, 'precision': 8, 'status': 'ok', 'type': 'bismuth'}, 'metadata': {'labels': []}, 'taker_fee': '0.005', 'string': 'BIS_BTC'}}
    assert api.currencies == {'GRIN': {'can_withdraw': False, 'code': 'GRIN', 'config': {'default_signer': 61, 'price': 10.537737418408733, 'required_confirmations': 10, 'withdraw_fee': '0.25'}, 'long_name': 'Grin', 'metadata': {'delisting_date': '4/11/2019', 'deposit_notices': [{'message': 'Deposits MUST be greater than 0.75 GRIN. Deposits for less than that amount will be rejected!', 'type': 'warning'}]}, 'precision': 9, 'status': 'delisted', 'type': 'grin'}, 'LTC': {'can_withdraw': True, 'code': 'LTC', 'config': {'additional_versions': [5], 'address_version': 48, 'default_signer': 5, 'explorerAddressURL': 'https://live.blockcypher.com/ltc/address/', 'explorerTransactionURL': 'https://live.blockcypher.com/ltc/tx/', 'p2sh_address_version': 50, 'price': 60.63, 'required_confirmations': 10, 'required_generate_confirmations': 100, 'satoshi_per_byte': 105, 'withdraw_fee': '0.001'}, 'long_name': 'Litecoin', 'metadata': {}, 'precision': 8, 'status': 'ok', 'type': 'bitcoin_like'}, 'BTC': {'can_withdraw': True, 'code': 'BTC', 'long_name': 'Bitcoin', 'type': 'bitcoin_like', 'status': 'ok', 'precision': 8, 'config': {'price': 8595.59, 'withdraw_fee': '0.0005', 'default_signer': 6, 'address_version': 0, 'satoshi_per_byte': 15, 'explorerAddressURL': 'https://live.blockcypher.com/btc/address/', 'p2sh_address_version': 5, 'explorerTransactionURL': 'https://live.blockcypher.com/btc/tx/', 'required_confirmations': 2, 'required_generate_confirmations': 100}, 'metadata': {'withdraw_notices': []}}, 'BIS': {'can_withdraw': True, 'code': 'BIS', 'config': {'data_max': 1000, 'default_signer': 54, 'enable_address_data': True, 'explorerAddressURL': 'https://bismuth.online/search?quicksearch=', 'explorerTransactionURL': 'https://bismuth.online/search?quicksearch=', 'price': 0.11933604157103646, 'required_confirmations': 35, 'withdraw_fee': '0.25'}, 'long_name': 'Bismuth', 'metadata': {'deposit_notices': [], 'hidden': False}, 'precision': 8, 'status': 'ok', 'type': 'bismuth'}}


def test_refresh_tickers(api):
    api._req = mock.MagicMock(return_value=json.loads("""
    {"markets": [
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
            "ask": null,
            "bid": null,
            "day_avg_price": null,
            "day_change": null,
            "day_high": null,
            "day_low": null,
            "day_open": null,
            "day_volume_base": "0",
            "day_volume_market": "0",
            "id": 8,
            "id_hr": "MMO_BTC",
            "last": "0.00000076"
    }]}"""))
    assert api.tickers == {20: {'ask': '0.00001499', 'bid': '0.00001332', 'day_avg_price': '0.0000146739216644', 'day_change': '-0.0893074119076549', 'day_high': '0.00001641', 'day_low': '0.00001292', 'day_open': '0.00001646', 'day_volume_base': '0.37996235', 'day_volume_market': '25893.7153059', 'id': 20, 'id_hr': 'BIS_BTC', 'last': '0.00001499'}, 8: {'ask': None, 'bid': None, 'day_avg_price': None, 'day_change': None, 'day_high': None, 'day_low': None, 'day_open': None, 'day_volume_base': '0', 'day_volume_market': '0', 'id': 8, 'id_hr': 'MMO_BTC', 'last': '0.00000076'}, 'BIS_BTC': {'ask': '0.00001499', 'bid': '0.00001332', 'day_avg_price': '0.0000146739216644', 'day_change': '-0.0893074119076549', 'day_high': '0.00001641', 'day_low': '0.00001292', 'day_open': '0.00001646', 'day_volume_base': '0.37996235', 'day_volume_market': '25893.7153059', 'id': 20, 'id_hr': 'BIS_BTC', 'last': '0.00001499'}, 'MMO_BTC': {'ask': None, 'bid': None, 'day_avg_price': None, 'day_change': None, 'day_high': None, 'day_low': None, 'day_open': None, 'day_volume_base': '0', 'day_volume_market': '0', 'id': 8, 'id_hr': 'MMO_BTC', 'last': '0.00000076'}}


def test_orders(api):
    api._req = mock.MagicMock(return_value=json.loads("""
    {"orders": [
        {
            "id": 8980903,
            "market_amount": "0.5672848",
            "market_amount_remaining": "0.5672848",
            "created_at": "2019-11-14T16:34:20.424601Z",
            "price": "0.00651044",
            "base_amount": "0.00371174",
            "order_type": "buy_limit",
            "market_id": 1,
            "open": true,
            "trades": null
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
            "open": true,
            "trades": null
        },
        {
            "id": 8980901,
            "market_amount": "12973.17366652",
            "market_amount_remaining": "12973.17366652",
            "created_at": "2019-11-14T16:34:20.328834Z",
            "price": "0.00000037",
            "order_type": "sell_limit",
            "market_id": 36,
            "open": true,
            "trades": null
        }
    ]}"""))
    assert api.orders(open=True) == [{'id': 8980903, 'market_amount': '0.5672848', 'market_amount_remaining': '0.5672848', 'created_at': '2019-11-14T16:34:20.424601Z', 'price': '0.00651044', 'base_amount': '0.00371174', 'order_type': 'buy_limit', 'market_id': 1, 'open': True, 'trades': None}, {'id': 8980902, 'market_amount': '0.37039118', 'market_amount_remaining': '0.37039118', 'created_at': '2019-11-14T16:34:20.380538Z', 'price': '0.00664751', 'base_amount': '0.00247449', 'order_type': 'buy_limit', 'market_id': 1, 'open': True, 'trades': None}, {'id': 8980901, 'market_amount': '12973.17366652', 'market_amount_remaining': '12973.17366652', 'created_at': '2019-11-14T16:34:20.328834Z', 'price': '0.00000037', 'order_type': 'sell_limit', 'market_id': 36, 'open': True, 'trades': None}]


def test_order(api):
    # manually set lazily loaded properties
    api._markets_map = {'LTC_BTC': {'base_currency': {'can_withdraw': True, 'code': 'BTC', 'config': {'address_version': 0, 'default_signer': 6, 'explorerAddressURL': 'https: //live.blockcypher.com/btc/address/', 'explorerTransactionURL': 'https: //live.blockcypher.com/btc/tx/', 'p2sh_address_version': 5, 'price': 8614.27, 'required_confirmations': 2, 'required_generate_confirmations': 100, 'satoshi_per_byte': 15, 'withdraw_fee': '0.0005'}, 'long_name': 'Bitcoin', 'metadata': {'withdraw_notices': []}, 'precision': 8, 'status': 'ok', 'type': 'bitcoin_like'}, 'can_cancel': True, 'can_trade': True, 'can_view': True, 'id': 1, 'maker_fee': '0', 'market_currency': {'can_withdraw': True, 'code': 'LTC', 'config': {'additional_versions': [5], 'address_version': 48, 'default_signer': 5, 'explorerAddressURL': 'https: //live.blockcypher.com/ltc/address/', 'explorerTransactionURL': 'https: //live.blockcypher.com/ltc/tx/', 'p2sh_address_version': 50, 'price': 58.73, 'required_confirmations': 10, 'required_generate_confirmations': 100, 'satoshi_per_byte': 105, 'withdraw_fee': '0.001'}, 'long_name': 'Litecoin', 'metadata': {}, 'precision': 8, 'status': 'ok', 'type': 'bitcoin_like'}, 'metadata': {}, 'string': 'LTC_BTC', 'taker_fee': '0.005'}, 1: {'base_currency': {'can_withdraw': True, 'code': 'BTC', 'config': {'address_version': 0, 'default_signer': 6, 'explorerAddressURL': 'https: //live.blockcypher.com/btc/address/', 'explorerTransactionURL': 'https: //live.blockcypher.com/btc/tx/', 'p2sh_address_version': 5, 'price': 8614.27, 'required_confirmations': 2, 'required_generate_confirmations': 100, 'satoshi_per_byte': 15, 'withdraw_fee': '0.0005'}, 'long_name': 'Bitcoin', 'metadata': {'withdraw_notices': []}, 'precision': 8, 'status': 'ok', 'type': 'bitcoin_like'}, 'can_cancel': True, 'can_trade': True, 'can_view': True, 'id': 1, 'maker_fee': '0', 'market_currency': {'can_withdraw': True, 'code': 'LTC', 'config': {'additional_versions': [5], 'address_version': 48, 'default_signer': 5, 'explorerAddressURL': 'https: //live.blockcypher.com/ltc/address/', 'explorerTransactionURL': 'https: //live.blockcypher.com/ltc/tx/', 'p2sh_address_version': 50, 'price': 58.73, 'required_confirmations': 10, 'required_generate_confirmations': 100, 'satoshi_per_byte': 105, 'withdraw_fee': '0.001'}, 'long_name': 'Litecoin', 'metadata': {}, 'precision': 8, 'status': 'ok', 'type': 'bitcoin_like'}, 'metadata': {}, 'string': 'LTC_BTC', 'taker_fee': '0.005'}}
    api._tickers = {1: {'ask': '0.00707017', 'bid': '0.00664751', 'day_avg_price': '0.0071579647440367', 'day_change': '0.0173330516998029', 'day_high': '0.00727268', 'day_low': '0.00713415', 'day_open': '0.00714877', 'day_volume_base': '0.00169664', 'day_volume_market': '0.23702827', 'id': 1, 'id_hr': 'LTC_BTC', 'last': '0.00727268'}, 'LTC_BTC': {'ask': '0.00707017', 'bid': '0.00664751', 'day_avg_price': '0.0071579647440367', 'day_change': '0.0173330516998029', 'day_high': '0.00727268', 'day_low': '0.00713415', 'day_open': '0.00714877', 'day_volume_base': '0.00169664', 'day_volume_market': '0.23702827', 'id': 1, 'id_hr': 'LTC_BTC', 'last': '0.00727268'}}

    # prevent lazily loaded properties from updating and making api calls
    def ret(*args, **kwargs):
        return
    api._refresh_tickers = ret
    api._refresh_common = ret

    # test successful sell order
    def req_1(method, endpoint, silent_codes=[], headers={}, json=None, params=None, is_retry=False, **kwargs):
        assert endpoint == "/v1/user/sell_limit"
        assert kwargs == {'amount': '0.01', 'price': '1.00000000', 'market_id': 1}
        return {'order': {'id': 8987684, 'market_amount': '0.01', 'market_amount_remaining': '0.01', 'created_at': '2019-11-14T23:46:52.897345Z', 'price': '1', 'order_type': 'sell_limit', 'market_id': 1, 'open': True, 'trades': []}}

    api._req = mock.MagicMock(side_effect=req_1)
    o = api.order("sell_limit", 1, amount=.01, market_string="LTC_BTC", prevent_taker=True)
    assert o == {'order': {'id': 8987684, 'market_amount': '0.01', 'market_amount_remaining': '0.01', 'created_at': '2019-11-14T23:46:52.897345Z', 'price': '1', 'order_type': 'sell_limit', 'market_id': 1, 'open': True, 'trades': []}}

    # test successful buy order
    def req_2(method, endpoint, silent_codes=[], headers={}, json=None, params=None, is_retry=False, **kwargs):
        assert endpoint == "/v1/user/buy_limit"
        assert kwargs == {'amount': '1.99004975', 'price': '0.00500000', 'market_id': 1}
        return {'order': {'id': 8987684, 'market_amount': '1.99004975', 'market_amount_remaining': '1.99004975', 'created_at': '2019-11-14T23:46:52.897345Z', 'price': '0.00500000', 'order_type': 'buy_limit', 'market_id': 1, 'open': True, 'trades': []}}

    api._req = mock.MagicMock(side_effect=req_2)
    o = api.order("buy_limit", .005, value=.01, market_id=1)
    assert o == {'order': {'id': 8987684, 'market_amount': '1.99004975', 'market_amount_remaining': '1.99004975', 'created_at': '2019-11-14T23:46:52.897345Z', 'price': '0.00500000', 'order_type': 'buy_limit', 'market_id': 1, 'open': True, 'trades': []}}

    # test successful sell order which uses value
    def req_3(method, endpoint, silent_codes=[], headers={}, json=None, params=None, is_retry=False, **kwargs):
        assert endpoint == "/v1/user/sell_limit"
        assert kwargs == {'amount': '0.01000000', 'price': '1.00000000', 'market_id': 1}
        return {'order': {'id': 8987684, 'market_amount': '0.01000000', 'market_amount_remaining': '0.01000000', 'created_at': '2019-11-14T23:46:52.897345Z', 'price': '1.00000000', 'order_type': 'sell_limit', 'market_id': 1, 'open': True, 'trades': []}}

    api._req = mock.MagicMock(side_effect=req_3)
    o = api.order("sell_limit", 1, value=.01, market_id=1)
    assert o == {'order': {'id': 8987684, 'market_amount': '0.01000000', 'market_amount_remaining': '0.01000000', 'created_at': '2019-11-14T23:46:52.897345Z', 'price': '1.00000000', 'order_type': 'sell_limit', 'market_id': 1, 'open': True, 'trades': []}}

    # test prevented taker buy order
    o = api.order("buy_limit", .1, value=.01, market_id=1, prevent_taker=True)
    assert o == "order not placed"

    # test prevented taker sell order
    o = api.order("sell_limit", .001, value=.01, market_id=1, prevent_taker=True)
    assert o == "order not placed"

    # test attempted order when neither value nor amount are provided
    try:
        o = api.order("sell_limit", .001, market_id=1)
        raise AssertionError
    except(ValueError):
        pass

    # test attempted order when both value and amount are provided
    try:
        o = api.order("sell_limit", .001, value=.01, amount=.01, market_id=1)
        raise AssertionError
    except(ValueError):
        pass

    # test attempted order when neither market_id nor market_string are provided
    try:
        o = api.order("sell_limit", .001, value=.01)
        raise AssertionError
    except(ValueError):
        pass

    # test attempted order when both market_id and market_string are provided
    try:
        o = api.order("sell_limit", .001, value=.01, market_id=1, market_string='LTC_BTC')
        raise AssertionError
    except(ValueError):
        pass


def test_clone(api):
    api.set_hmac('1:11111111111')
    assert api.rs.auth is not None
    c = api.clone()
    assert c != api
    assert c.rs.auth is None
