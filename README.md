# Install

Only guaranteed to work on Python3, but PRs for Python2.7 will be accepted.

``` bash
pip3 install --upgrade --user git+https://github.com/qtrade-exchange/qtrade-py-client.git
```

## Basic Usage

``` python
from qtrade_client.api import QtradeAPI

# String is of the format "[key_id]:[key]"
hmac_keypair = "256:vwj043jtrw4o5igw4oi5jwoi45g"
client = QtradeAPI("https://api.qtrade.io", key=hmac_keypair)

result = client.post("/v1/user/sell_limit", amount="1", price="0.0001", market_id=12)
print(result)

# Only closed orders
print(client.orders(open=False))
# Print all orders before ID 25
print(client.orders(older_than=25))
# Print all orders after ID 25
print(client.orders(newer_than=25))
```

## Rate Limit

By default the `QtradeAPI` will honor and avoid rate limits. It does this with
three peices of logic:

1. If the rate limit would be hit, it will sleep until the reset time. (Hard
   limit avoidance)
2. If >50% of the limit has been used it will sleep a proportional amount of
   time to avoid hitting the hard limit. This allows bursting and avoids long
   sleeps. This can be configured by setting `client.rl_soft_threshold` to
   values between 0 and 1. A value of 1 will disable soft limits entirely (full burst).
3. If a `429 Limit Exceeded` is encountered, it will transparently retry one
   time. This is to prime the rate limit counter variables in the case that the
   very first request hits the rate limit.

`client.honor_ratelimit` may be set to `False` to disable rate limit logic completely.

## Logging

Verbose logging from the QtradeAPI class can help debug integration problems.
See snippet below for getting log output from the `QtradeAPI` class.

``` python
import logging
import sys

# Setup standard logging for Python to stdout, read more at
# https://stackoverflow.com/questions/14058453/making-python-loggers-output-all-messages-to-stdout-in-addition-to-log-file
root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

# To get logging output from the QtradeAPI class for debugging:
logging.getLogger('qtrade').setLevel(logging.DEBUG)
```
