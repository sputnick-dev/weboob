# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from decimal import Decimal
import re

from mechanize import Cookie

from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.deprecated.browser import Page, BrowserUnavailable
from weboob.deprecated.mech import ClientForm
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date
from weboob.tools.js import Javascript



class PromoPage(Page):
    def on_loaded(self):
        # We land sometimes on this page, it's better to raise an unavailable browser
        # than an Incorrect Password
        raise BrowserUnavailable('Promo Page')

class LoginPage(Page):
    def login(self, login, password):
        #Paypal use this to check if we accept cookie
        c = Cookie(0, 'cookie_check', 'yes',
                      None, False,
                      '.' + self.browser.DOMAIN, True, True,
                      '/', False,
                      False,
                      None,
                      False,
                      None,
                      None,
                      {})
        cookiejar = self.browser._ua_handlers["_cookies"].cookiejar
        cookiejar.set_cookie(c)

        self.browser.select_form(name='login_form')
        self.browser['login_email'] = login.encode(self.browser.ENCODING)
        self.browser['login_password'] = password.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)

    def validate_useless_captacha(self):
        #paypal use a captcha page after login, but don't use the captcha
        self.browser.select_form(name='challenge')
        self.browser.form.set_all_readonly(False)

        #paypal add this on the captcha page when the validate should be automatique
        self.browser.controls.append(ClientForm.TextControl('text', 'ads_token_js', {'value': ''}))

        code = ''.join(self.document.xpath('//script[contains(text(), "autosubmit")]/text()'))
        code = re.search('(function .*)try', code).group(1)
        js = Javascript(code)
        func_name = re.search(r'function (\w+)\(e\)', code).group(1)
        self.browser['ads_token_js'] = str(js.call(func_name, self.browser['ads_token']))

        self.browser.submit(nologin=True)

class ErrorPage(Page):
    pass

class UselessPage(Page):
    pass


class HomePage(Page):
    pass


class AccountPage(Page):
    def get_account(self, _id):
        return self.get_accounts().get(_id)

    def get_accounts(self):
        accounts = {}
        content = self.document.xpath('//div[@id="moneyPage"]')[0]

        # Primary currency account
        primary_account = Account()
        primary_account.type = Account.TYPE_CHECKING
        try:
            balance = self.parser.tocleanstring(content.xpath('//div[contains(@class, "col-md-6")][contains(@class, "available")]')[0])
        except IndexError:
            primary_account.id = 'EUR'
            primary_account.currency = 'EUR'
            primary_account.balance = NotAvailable
            primary_account.label = u'%s' % (self.browser.username)
        else:
            primary_account.currency = Account.get_currency(balance)
            primary_account.id = unicode(primary_account.currency)
            primary_account.balance = Decimal(FrenchTransaction.clean_amount(balance))
            primary_account.label = u'%s %s*' % (self.browser.username, primary_account.currency)

        accounts[primary_account.id] = primary_account

        return accounts


class HistoryPage(Page):
    def iter_transactions(self, account):
        for trans in self.parse(account):
            yield trans

    def parse(self, account):
        transactions = list()

        transacs = self.get_transactions()

        for t in transacs:
            tran = self.parse_transaction(t, account)
            if tran:
                transactions.append(tran)

        for t in transactions:
            yield t

    def format_amount(self, to_format, is_credit):
        m = re.search(r"\D", to_format[::-1])
        amount = Decimal(re.sub(r'[^\d]', '', to_format))/Decimal((10 ** m.start()))
        if is_credit:
            return abs(amount)
        else:
            return -abs(amount)

class ProHistoryPage(HistoryPage):
    def transaction_left(self):
        return len(self.document['data']['transactions']) > 0

    def get_transactions(self):
        return self.document['data']['transactions']

    def parse_transaction(self, transaction, account):
        if transaction['transactionStatus'] in [u'Créé', u'Annulé', u'Suspendu', u'Mis à jour', u'Actif']:
            return
        t = FrenchTransaction(transaction['transactionId'])
        if not transaction['transactionAmount']['currencyCode'] == account.currency:
            cc = self.browser.convert_amount(account, transaction, 'https://www.paypal.com/cgi-bin/webscr?cmd=_history-details-from-hub&id=' + transaction['transactionId'])
            if not cc:
                return
            t.original_amount = Decimal(transaction['transactionAmount']['currencyDoubleValue'])
            t.original_currency = u'' + transaction['transactionAmount']['currencyCode']
            t.set_amount(cc)
        else:
            t.amount = Decimal(transaction['transactionAmount']['currencyDoubleValue'])
        date = parse_french_date(transaction['transactionTime'])
        raw = transaction['transactionDescription']
        t.commission = Decimal(transaction['fee']['currencyDoubleValue'])
        t.parse(date=date, raw=raw)
        return t


class PartHistoryPage(HistoryPage):
    def on_loaded(self):
        self.browser.is_new_api = self.document['viewName'] == 'activityBeta/index'

    def transaction_left(self):
        if self.browser.is_new_api:
            return self.document['data']['activity']['hasTransactionsCompleted'] or self.document['data']['activity']['hasTransactionsPending']
        return len(self.document['data']['activity']['COMPLETED']) > 0 or len(self.document['data']['activity']['PENDING']) > 0

    def get_transactions(self):
        if self.browser.is_new_api:
            transacs = self.document['data']['activity']['transactions']
        else:
            for status in ['PENDING', 'COMPLETED']:
                transacs = list()
                transacs += self.document['data']['activity'][status]
        return transacs

    def parse_new_api_transaction(self, transaction, account):
        t = FrenchTransaction(transaction['id'])
        if not transaction['isPrimaryCurrency']:
            cc = self.browser.convert_amount(account, transaction, transaction['detailsLink'])
            if not cc:
                return
            t.original_amount = self.format_amount(transaction['amounts']['net']['value'], transaction["isCredit"])
            t.original_currency = u'' + transaction['amounts']['txnCurrency']
            t.amount = self.format_amount(cc, transaction['isCredit'])
        else:
            t.amount = self.format_amount(transaction['amounts']['net']['value'], transaction['isCredit'])
        date = parse_french_date(transaction['date']['formattedDate'] + ' ' + transaction['date']['year'])
        raw = transaction.get('counterparty', transaction['displayType'])
        t.parse(date=date, raw=raw)

        return t

    def parse_transaction(self, transaction, account):
        if self.browser.is_new_api:
            return self.parse_new_api_transaction(transaction, account)

        t = FrenchTransaction(transaction['transactionId'])
        date = parse_french_date(transaction['date'])
        if not transaction['txnIsInPrimaryCurrency']:
            cc = self.browser.convert_amount(account, transaction, transaction['actions']['details']['url'])
            if not cc:
                return
            t.original_amount = self.format_amount(transaction['netAmount'], transaction["isCredit"])
            t.original_currency = u'' + transaction["currencyCode"]
            t.amount = self.format_amount(cc, transaction['isCredit'])
        else:
            t.amount = self.format_amount(transaction['netAmount'], transaction["isCredit"])
        raw = transaction.get('counterparty', transaction['displayType'])
        t.parse(date=date, raw=raw)

        return t

class HistoryDetailsPage(Page):
    def get_converted_amount(self, account):
        find_td = self.document.xpath('//td[contains(text(),"' + account.currency + ')")]')
        if len(find_td) > 0 :
            convert_td = find_td[0].text
            m = re.match('.* ([^ ]+) ' + account.currency + '\).*', convert_td)
            if m:
                return m.group(1)
        return False
