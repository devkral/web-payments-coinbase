from collections import OrderedDict

import hashlib
import hmac
import json
import time

import requests

from web_payments.logic import BasicProvider
from web_payments.forms import PaymentForm
from web_payments import PaymentStatus, NotSupported

class CoinbasePaymentForm(PaymentForm):
    method = 'get'

class CoinbaseProvider(BasicProvider):

    api_url = 'https://api.%(endpoint)s/v1/buttons'
    checkout_url = 'https://%(endpoint)s/checkouts'
    form_class = CoinbasePaymentForm

    def __init__(self, key, secret, endpoint='sandbox.coinbase.com', **kwargs):
        self.key = key
        self.secret = secret
        self.endpoint = endpoint
        super().__init__(**kwargs)
        if not self._capture:
            raise NotSupported(
                'Coinbase does not support pre-authorization.')

    def get_custom_token(self, payment):
        value = 'coinbase-%s-%s' % (payment.token, self.key)
        return hashlib.md5(value.encode('utf-8')).hexdigest()

    def get_checkout_code(self, payment):
        api_url = self.api_url % {'endpoint': self.endpoint}
        button_data = {
            'name': payment.description,
            'price_string': str(payment.total),
            'price_currency_iso': payment.currency,
            'callback_url': payment.get_process_url(),
            'success_url': payment.get_success_url(),
            'cancel_url': payment.get_failure_url(),
            'custom': self.get_custom_token(payment)}
        # ordered dict for stable JSON output
        data = {'button': OrderedDict(sorted(button_data.items()))}
        nonce = int(time.time() * 1e6)
        message = str(nonce) + api_url + json.dumps(data)
        signature = hmac.new(self.secret.encode(), message.encode(),
                             hashlib.sha256).hexdigest()
        headers = {
            'ACCESS_KEY': self.key,
            'ACCESS_SIGNATURE': signature,
            'ACCESS_NONCE': nonce,
            'Accept': 'application/json'}
        response = requests.post(
            api_url, data=json.dumps(data), headers=headers)

        response.raise_for_status()
        results = response.json()
        return results['button']['code']

    def get_action(self, payment):
        checkout_url = self.checkout_url % {'endpoint': self.endpoint}
        return '%s/%s' % (checkout_url, self.get_checkout_code(payment))

    def process_data(self, payment, request):
        try:
            results = json.loads(request.body)
        except (ValueError, TypeError):
            return False

        if results['order']['custom'] != self.get_custom_token(payment):
            return False

        if payment.status == PaymentStatus.WAITING:
            payment.transaction_id = results['order']['transaction']['id']
            payment.change_status(PaymentStatus.CONFIRMED)
            payment.save()
        return True
