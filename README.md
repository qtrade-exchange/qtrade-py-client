# Install

Only guaranteed to work on Python3, but PRs for Python2.7 will be accepted.

``` bash
pip3 install --user git+https://github.com/qtrade-exchange/qtrade-py-client.git
```

## Basic Usage

``` python
from qtrade_client.api import QtradeAPI

# String is of the format "[key_id]:[key]"
hmac_keypair = "256:vwj043jtrw4o5igw4oi5jwoi45g"
client = QtradeAPI("https://api.qtrade.io", key=hmac_keypair)

result = client.post("/v1/user/sell_limit", amount="1", price="0.0001", market_id=12)
print(result)
```

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
