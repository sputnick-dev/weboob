# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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


from weboob.capabilities.recipe import Recipe, Comment
from weboob.capabilities.base import NotAvailable
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, method, ListElement
from weboob.browser.filters.standard import CleanText, Regexp, Env, Time
from weboob.browser.filters.html import XPath, CleanHTML

import re
import datetime


class CuisineazDuration(Time):
    klass = datetime.timedelta
    _regexp = re.compile(r'((?P<hh>\d+) h)?((?P<mm>\d+) min)?(?P<ss>\d+)?')
    kwargs = {'hours': 'hh', 'minutes': 'mm', 'seconds': 'ss'}


class ResultsPage(HTMLPage):
    """ Page which contains results as a list of recipies
    """

    @pagination
    @method
    class iter_recipes(ListElement):
        item_xpath = '//div[@id="divRecette"]'

        def next_page(self):
            next = CleanText('//li[@class="next"]/span/a/@href',
                             default=None)(self)
            if next:
                return next

        class item(ItemElement):
            klass = Recipe

            def condition(self):
                return Regexp(CleanText('./div[has-class("searchTitle")]/h2/a/@href'),
                              'http://www.cuisineaz.com/recettes/(.*).aspx',
                              default=None)(self.el)

            obj_id = Regexp(CleanText('./div[has-class("searchTitle")]/h2/a/@href'),
                            'http://www.cuisineaz.com/recettes/(.*).aspx')
            obj_title = CleanText('./div[has-class("searchTitle")]/h2/a')

            obj_thumbnail_url = CleanText('./div[has-class("searchImg")]/span/img[@data-src!=""]/@data-src|./div[has-class("searchImg")]/div/span/img[@src!=""]/@src',
                                          default=None)

            obj_short_description = CleanText('./div[has-class("searchIngredients")]')


class RecipePage(HTMLPage):
    """ Page which contains a recipe
    """
    @method
    class get_recipe(ItemElement):
        klass = Recipe

        obj_id = Env('_id')
        obj_title = CleanText('//div[@id="ficheRecette"]/h1')

        obj_picture_url = CleanText('//img[@id="shareimg" and @src!=""]/@src', default=None)

        obj_thumbnail_url = CleanText('//img[@id="shareimg" and @src!=""]/@src', default=None)

        def obj_preparation_time(self):
            _prep = CuisineazDuration(CleanText('//span[@id="ctl00_ContentPlaceHolder_LblRecetteTempsPrepa"]'))(self)
            return int(_prep.total_seconds() / 60)

        def obj_cooking_time(self):
            _cook = CuisineazDuration(CleanText('//span[@id="ctl00_ContentPlaceHolder_LblRecetteTempsCuisson"]'))(self)
            return int(_cook.total_seconds() / 60)

        def obj_nb_person(self):
            nb_pers = CleanText('//span[@id="ctl00_ContentPlaceHolder_LblRecetteNombre"]')(self)
            return [nb_pers] if nb_pers else NotAvailable

        def obj_ingredients(self):
            ingredients = []
            for el in XPath('//div[@id="ingredients"]/ul/li')(self):
                ingredients.append(CleanText('.')(el))
            return ingredients

        obj_instructions = CleanHTML('//div[@id="preparation"]/span[@class="instructions"]')

    @method
    class get_comments(ListElement):
        item_xpath = '//div[@class="comment pb15 row"]'

        class item(ItemElement):
            klass = Comment

            obj_author = CleanText('./div[has-class("comment-left")]/div/div/div[@class="fs18 txtcaz mb5 first-letter"]')

            obj_text = CleanText('./div[has-class("comment-right")]/div/p')
            obj_id = CleanText('./@id')

            def obj_rate(self):
                    return len(XPath('./div[has-class("comment-right")]/div/div/div/span/span[@class="icon icon-star"]')(self))
