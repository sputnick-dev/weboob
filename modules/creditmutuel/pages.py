# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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


from datetime import date

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Account
from weboob.capabilities.bank import Transaction

class LoginPage(BasePage):
    def login(self, login, passwd):
        self.browser.select_form(nr=0)
        self.browser['_cm_user'] = login
        self.browser['_cm_pwd'] = passwd
        self.browser.submit()

class LoginErrorPage(BasePage):
    pass

class InfoPage(BasePage):
    pass

class TransfertPage(BasePage):
    pass

class UserSpacePage(BasePage):
    pass

class AccountsPage(BasePage):
    def get_list(self):
        l = []

        for tr in self.document.getiterator('tr'):
            first_td = tr.getchildren()[0]
            if first_td.attrib.get('class', '') == 'i g' or first_td.attrib.get('class', '') == 'p g':
                account = Account()
                account.label = u"%s"%first_td.find('a').text.strip()
                account.link_id = first_td.find('a').get('href', '')
                if account.link_id.startswith('POR_SyntheseLst'):
                    continue

                account.id = first_td.find('a').text.split(' ')[0]+first_td.find('a').text.split(' ')[1]
                s = tr.getchildren()[2].text
                if s.strip() == "":
                    s = tr.getchildren()[1].text
                balance = u''
                for c in s:
                    if c.isdigit() or c == '-':
                        balance += c
                    if c == ',':
                        balance += '.'
                account.balance = float(balance)
                l.append(account)
            #raise NotImplementedError()
        return l

    def next_page_url(self):
        """ TODO pouvoir passer à la page des comptes suivante """
        return 0

class OperationsPage(BasePage):
    def get_history(self):
        index = 0
        for tr in self.document.getiterator('tr'):
            tds = tr.getchildren()
            if len(tds) < 4:
                continue

            if tds[0].attrib.get('class', '') == 'i g' or \
               tds[0].attrib.get('class', '') == 'p g' or \
               tds[0].attrib.get('class', '').endswith('_c1 c _c1'):
                operation = Transaction(index)
                index += 1

                d = tds[0].text.strip().split('/')
                operation.date = date(*reversed([int(x) for x in d]))

                operation.raw = tds[-3].text.replace('\n',' ').strip()
                if tds[-1].text is not None and len(tds[-1].text) > 2:
                    s = tds[-1].text.strip()
                elif tds[-1].text is not None and len(tds[-2].text) > 2:
                    s = tds[-2].text.strip()
                else:
                    s = "0"
                balance = u''
                for c in s:
                    if c.isdigit() or c == "-":
                        balance += c
                    if c == ',':
                        balance += '.'
                operation.amount = float(balance)
                yield operation

    def next_page_url(self):
        """ TODO pouvoir passer à la page des opérations suivantes """
        return 0
