import requests
import requests.auth
import time
import json as _json
import urllib.parse
import logging
import base64

from hashlib import sha256
from urllib.parse import urlparse
from decimal import Decimal

from pprint import pprint

log = logging.getLogger("qtrade")

COIN = Decimal('.00000001')


class APIException(Exception):

    def __init__(self, message, code, errors):
        super().__init__(message)
        self.code = code
        self.errors = errors


class QtradeAuth(requests.auth.AuthBase):

    def __init__(self, key):
        self.key_id, self.key = key.split(":")

    def __call__(self, req):
        # modify and return the request
        timestamp = str(int(time.time()))
        url_obj = urlparse(req.url)

        request_details = req.method + "\n"
        uri = url_obj.path
        if url_obj.query:
            uri += "?" + url_obj.query
        request_details += uri + "\n"
        request_details += timestamp + "\n"
        if req.body:
            if isinstance(req.body, str):
                request_details += req.body + "\n"
            else:
                request_details += req.body.decode('utf8') + "\n"
        else:
            request_details += "\n"
        request_details += self.key
        hsh = sha256(request_details.encode("utf8")).digest()
        signature = base64.b64encode(hsh)
        req.headers.update({
            "Authorization": "HMAC-SHA256 {}:{}".format(self.key_id, signature.decode("utf8")),
            "HMAC-Timestamp": timestamp
        })
        return req


class QtradeAPI(object):

    def __init__(self, endpoint, origin=None, email='Unk', key=None):
        self.user_id = None
        self.email = email
        self.endpoint = endpoint
        self.origin = origin
        self.token = None
        self.rs = requests.Session()
        if key is not None:
            self.set_hmac(key)

        self.tickers_update_interval = 180
        self.market_update_interval = 180

        self._markets_map = None
        self._markets_age = 0
        self._tickers = None
        self._tickers_age = 0
        self.honor_ratelimit = True
        self.rl_remaining = 99
        self.rl_reset_at = time.time()
        self.rl_limit = 120
        # Set to 1 to disable soft threshold, 0 will always sleep between calls
        # if needed (no burst at all)
        self.rl_soft_threshold = 0.5

    def clone(self):
        """ Returns a new QtradeAPI instance with stripped auth but the same
        endpoint configuration. Useful for testing toolchains that might point
        at multiple testing endpoints and 'inherit' from some base endpoint
        config """
        return type(self)(self.endpoint)

    def login(self, email, password):
        """ Login with username and password to get a JWT token.
        Intended for internal testing only. """
        resp = self._req('post', "/v1/login", json={
            "email": email,
            "password": password,
        })
        self.user_id = resp['user_id']
        self.token = resp['token']

    def set_hmac(self, hmac_pair):
        """ hmac_pair should be in "1:11111..." format, with keyid then key """
        self.rs.auth = QtradeAuth(hmac_pair)

    def balances(self):
        return {b['currency']: Decimal(b['balance']) for b in self.get("/v1/user/balances")['balances']}

    def get(self, endpoint, *args, **kwargs):
        return self._req('get', endpoint, *args, **kwargs)

    def post(self, endpoint, *args, **kwargs):
        return self._req('post', endpoint, *args, **kwargs)

    def orders(self, open=None, older_than=None, newer_than=None):
        if isinstance(open, bool):
            open = str(open).lower()
        return self.get("/v1/user/orders", open=open, older_than=older_than, newer_than=newer_than)['orders']

    def order(self, order_type, price, value=None, amount=None, market_id=None, market_string=None, prevent_taker=False):
        """ Place an order with the given parameters.
        value = amount * price """
        if market_id is not None and market_string is not None:
            raise ValueError(
                "market_id and market_string are mutually exclusive")
        elif market_id is None and market_string is None:
            raise ValueError("either market_id or market_string are required")
        if value is not None and amount is not None:
            raise ValueError("value and amount are mutually exclusive")
        elif value is None and amount is None:
            raise ValueError("either value or amount are required")

        if market_string is not None:
            market_id = self.markets[market_string]['id']
        price = Decimal(price).quantize(COIN)
        if prevent_taker is True:
            ticker = self.tickers[market_id]
            if order_type == "buy_limit" and price > Decimal(ticker['ask']):
                log.info("%s %s at %s was not placed.  Ask price is %s, so it would have been a taker order.",
                         market_id, order_type, price, ticker['ask'])
                return "order not placed"
            elif order_type == 'sell_limit' and price < Decimal(ticker['bid']):
                log.info("%s %s at %s was not placed.  Bid price is %s, so it would have been a taker order.",
                         market_id, order_type, price, ticker['bid'])
                return "order not placed"
        # convert value to amount if necessary
        if order_type == 'buy_limit' and value is not None:
            fee_perc = max(Decimal(self.markets[market_id]['taker_fee']), Decimal(
                self.markets[market_id]['maker_fee']))
            fee_mult = Decimal(fee_perc+1)
            amount = (Decimal(value) / (fee_mult * price)).quantize(COIN)
        elif order_type == 'sell_limit' and value is not None:
            amount = (Decimal(value) / price).quantize(COIN)
        logging.debug("Placing %s on %s market for %s at %s",
                      order_type, self.markets[market_id]['string'], amount, price)
        return self.post('/v1/user/{}'.format(order_type), amount=str(amount),
                         price=str(price), market_id=market_id)

    def balances_merged(self):
        """ Get total balances including order balances """
        bals = self.balances_all()
        merged = {}
        for k, v in list(bals['spendable'].items()) + list(bals['in_orders'].items()):
            merged.setdefault(k, 0)
            merged[k] += Decimal(v)
        return merged

    def balances_all(self):
        all_bal = self.get("/v1/user/balances_all")
        return {
            "spendable": {b['currency']: Decimal(b['balance']) for b in all_bal['balances']},
            "in_orders": {b['currency']: Decimal(b['balance']) for b in all_bal['order_balances']},
        }

    def cancel_all_orders(self):
        for o in self.orders(open=True):
            self.post('/v1/user/cancel_order', json={'id': o['id']})

    def cancel_market_orders(self, market_string=None, market_id=None):
        if market_id is not None and market_string is not None:
            raise ValueError(
                "market_id and market_string are mutually exclusive")
        elif market_id is None and market_string is None:
            raise ValueError("either market_id or market_string are required")
        if market_id is None:
            market_id = self.markets[market_string]['id']
        for o in self.orders(open=True):
            if o['market_id'] == market_id:
                self.post('/v1/user/cancel_order', json={'id': o['id']})

    @property
    def tickers(self):
        """ Tickers may be indexed either by market id or market string """
        self._refresh_tickers()
        return self._tickers

    def _refresh_tickers(self):
        """ Lazy load and reload every tickers_update_interval. """
        if self._tickers is None or (time.time() - self._tickers_age) > self.tickers_update_interval:
            res = self.get('/v1/tickers')
            self._tickers = {m['id']: m for m in res['markets']}
            self._tickers.update({m['id_hr']: m for m in res['markets']})
            self._tickers_age = time.time()

    @property
    def currencies(self):
        self._refresh_common()
        return self._currencies_map

    @property
    def markets(self):
        """ Markets may be indexed either by id or string """
        self._refresh_common()
        return self._markets_map

    def _refresh_common(self):
        """ Lazy load and reload every market_update_interval. """
        if self._markets_map is None or (time.time() - self._markets_age) > self.market_update_interval:
            # Index our market information by market string
            common = self.get("/v1/common")
            self._currencies_map = {c['code']: c for c in common['currencies']}
            # Set some convenience keys so we can pass around just the dict
            for m in common['markets']:
                m['string'] = "{market_currency}_{base_currency}".format(**m)
                m['base_currency'] = self._currencies_map[m['base_currency']]
                m['market_currency'] = self._currencies_map[m['market_currency']]
            self._markets_map = {m['string']: m for m in common['markets']}
            self._markets_map.update({m['id']: m for m in common['markets']})
            self._markets_age = time.time()

    def _req(self, method, endpoint, silent_codes=[], headers={}, json=None, params=None, is_retry=False, **kwargs):
        soft_limit = int(self.rl_limit * (1 - self.rl_soft_threshold))
        # If limit is completely exhausted, sleep until full reset. Clamp to
        # min 0 to not bomb out if reset_at is in past
        if self.honor_ratelimit and self.rl_remaining <= 0:
            must_wait = max(0, self.rl_reset_at - time.time())
            if must_wait >= 5:
                log.info("Ratelimit hit, sleeping for {:,}".format(must_wait))
            time.sleep(must_wait)

        # If limit is >self.rl_soft_threshold % used, sleep the appropriate
        # amount to avoid hitting a big wait
        elif self.honor_ratelimit and self.rl_remaining <= soft_limit:
            sec_to_reset = self.rl_reset_at - time.time()
            must_wait = max(0, sec_to_reset / float(self.rl_remaining))
            time.sleep(must_wait)

        # Inject the auth token header if applicable
        if self.token:
            headers['Authorization'] = "Bearer {}".format(self.token)

        # We remove all kwargs that might be intended for our session.request
        requests_kwarg_keys = ['data', 'cookies', 'files', 'auth', 'timeout',
                               'allow_redirects', 'proxies', 'hooks', 'stream', 'verify', 'cert']
        requests_kwargs = {}
        for key in requests_kwarg_keys:
            requests_kwargs[key] = kwargs.pop(key, None)

        url = urllib.parse.urljoin(self.endpoint, endpoint)

        # Support legacy usage of the json parameter, but prefer passing POST
        # params as kwargs
        if method.lower() == "post" and json is None:
            json = kwargs
        req_json = _json.dumps(json)

        # Support passing params just because...
        if method.lower() == "get" and params is None:
            params = kwargs

        res = self.rs.request(method, url, headers=headers,
                              json=json, params=params, **requests_kwargs)
        self.rl_reset_at = time.time() + int(res.headers.get('X-Ratelimit-Reset', 0))
        self.rl_limit = int(res.headers.get('X-Ratelimit-Limit', 100))
        self.rl_remaining = int(res.headers.get('X-Ratelimit-Remaining', 99))
        if requests_kwargs.get('stream') is True:
            log.debug("GET streaming {}".format(url))
            for ln in res.iter_lines():
                print(ln.decode('utf8'))
            return

        # We've hit the rate limit, so retry. Code at beginning of call
        # will proc now that we've populated rl_limit, etc
        if res.status_code == 429 and is_retry is False:
            return self._req(method, endpoint, silent_codes=silent_codes, headers=headers, json=json, params=params, is_retry=True, **kwargs)

        try:
            ret = res.json()
        except Exception:
            if res.status_code > 299:
                log.warn("{} {} {} req={} res=\n{}".format(
                    method, url, res.status_code, req_json, res.text))
                raise APIException(
                    "Invalid return code from backend", res.status_code, [])
            else:
                return True

        if res.status_code > 299:
            if res.status_code not in silent_codes:
                log.warn("{} {} {} req={} res=\n{}".format(
                    method, url, res.status_code, req_json, res.text))
            errors = [e['code'] for e in ret['errors']]
            raise APIException(
                "Invalid return code from backend", res.status_code, errors)

        log.debug("GET {} req={} res={}".format(url, req_json, ret))
        return ret['data']
