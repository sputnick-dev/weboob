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


from weboob.capabilities.bank import Account
from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import LoginPage, SummaryPage, UselessPage


__all__ = ['CitelisBrowser']


class CitelisBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'adminpayment.citelis.fr'
    ENCODING = 'UTF-8'
    CERTHASH = 'a0ded00e08b1320b89329cc5e0b59aef13fbb1919290492f622834fa6cff2c68'

    PAGES = {
        '%s://%s/userManager\.do\?reqCode=prepareLogin.*' % (PROTOCOL, DOMAIN): LoginPage,
        '%s://%s/summarySearch\.do\?reqCode=search.*' % (PROTOCOL, DOMAIN): SummaryPage,
        '%s://%s/userManager\.do\?reqCode=goToHomePage.+' % (PROTOCOL, DOMAIN): UselessPage,
    }

    def __init__(self, merchant_id, *args, **kwargs):
        self.merchant_id = merchant_id
        BaseBrowser.__init__(self, *args, **kwargs)

    def login(self):
        if not self.is_on_page(LoginPage):
            self.location('%s://%s/userManager.do?reqCode=prepareLogin' % (self.PROTOCOL, self.DOMAIN))
        self.page.login(self.merchant_id, self.username, self.password)
        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def get_accounts_list(self):
        self.location('%s://%s/summarySearch.do?reqCode=search' % (self.PROTOCOL, self.DOMAIN))
        account = Account()
        account.id = u'1'
        account.currency = Account.CUR_EUR
        account.balance = self.page.get_balance()
        account.label = u'Synthèse financière'
        return [account]
