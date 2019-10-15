import requests
import requests.auth
import time
import json as _json
import urllib.parse
import logging
import base64

from hashlib import sha256
from urllib.parse import urlparse

log = logging.getLogger("qtrade")


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
        self.markets = {}
        self.origin = origin
        self.token = None
        self.rs = requests.Session()
        if key is not None:
            self.set_hmac(key)

    def clone(self):
        """ Returns a new QtradeAPI instance with stripped auth but the same
        endpoint configuration. Useful for testing toolchains that might point
        at multiple testing endpoints and 'inherit' from some base endpoint
        config """
        return type(self)(self.endpoint)

    def login(self, email, password):
        """ Login with username and password to get a JWT token. Not
        recommended for production use, but can be okay for quick testing. """
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
        return {b['currency']: b['balance'] for b in self.get("/v1/user/balances")['balances']}

    def get(self, endpoint, *args, **kwargs):
        return self._req('get', endpoint, *args, **kwargs)

    def post(self, endpoint, *args, **kwargs):
        return self._req('post', endpoint, *args, **kwargs)

    def orders(self, open=None, older_than=None, newer_than=None):
        if isinstance(open, bool):
            open = str(open).lower()
        return self.get("/v1/user/orders", open=open, older_than=older_than, newer_than=newer_than)['orders']

    def _req(self, method, endpoint, silent_codes=[], headers={}, json=None, params=None, **kwargs):
        # Inject the auth token header if applicable
        if self.token:
            headers['Authorization'] = "Bearer {}".format(self.token)

        # We remove all kwargs that might be intended for our session.request
        requests_kwarg_keys = ['data', 'cookies', 'files', 'auth', 'timeout', 'allow_redirects', 'proxies', 'hooks', 'stream', 'verify', 'cert']
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

        res = self.rs.request(method, url, headers=headers, json=json, params=params, **requests_kwargs)
        if requests_kwargs.get('stream') is True:
            log.debug("GET streaming {}".format(url))
            for ln in res.iter_lines():
                print(ln.decode('utf8'))
            return
        try:
            ret = res.json()
        except Exception:
            if res.status_code > 299:
                log.warn("{} {} {} req={} res=\n{}".format(
                    method, url, res.status_code, req_json, res.text))
                raise APIException("Invalid return code from backend", res.status_code, [])
            else:
                return True

        if res.status_code > 299:
            if res.status_code not in silent_codes:
                log.warn("{} {} {} req={} res=\n{}".format(
                    method, url, res.status_code, req_json, res.text))
            errors = [e['code'] for e in ret['errors']]
            raise APIException("Invalid return code from backend", res.status_code, errors)

        log.debug("GET {} req={} res={}".format(url, req_json, ret))
        return ret['data']
