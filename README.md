web-payments-coinbase
======================

Usage:

add to PAYMENT_VARIANTS_API:

``` python
PAYMENT_VARIANTS_API = {
    ...
    'coinbase': ('web_payments_coinbase.CoinbaseProvider', {
      "key": "<key>",
      "secret": "<secret>",
      "endpoint": 'sandbox.coinbase.com',
      }
    )
  }
```
