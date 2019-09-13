# Install

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
