# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Roger Philibert
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


from weboob.deprecated.browser import Page
from weboob.tools.capabilities.thumbnail import Thumbnail

from datetime import datetime
import re

from .gallery import EHentaiGallery


class LoginPage(Page):
    def is_logged(self):
        success_p = self.document.xpath(
                '//p[text() = "Login Successful. You will be returned momentarily."]')
        if len(success_p):
            return True
        else:
            return False


class HomePage(Page):
    pass


class IndexPage(Page):
    def iter_galleries(self):
        lines = self.document.xpath('//table[@class="itg"]//tr[@class="gtr0" or @class="gtr1"]')
        for line in lines:
            a = line.xpath('.//div[@class="it3"]/a')[-1]
            url = a.attrib["href"]
            title = a.text.strip()
            yield EHentaiGallery(re.search('(?<=/g/)\d+/[\dabcdef]+', url).group(0), title=title)


class GalleryPage(Page):
    def image_pages(self):
        return self.document.xpath('//div[@class="gdtm"]//a/attribute::href')

    def _page_numbers(self):
        return [n for n in self.document.xpath("(//table[@class='ptt'])[1]//td/text()") if re.match(r"\d+", n)]

    def gallery_exists(self, gallery):
        if self.document.xpath("//h1"):
            return True
        else:
            return False

    def fill_gallery(self, gallery):
        gallery.title = self.document.xpath("//h1[@id='gn']/text()")[0]
        cardinality_string = self.document.xpath("//div[@id='gdd']//tr[td[@class='gdt1']/text()='Length:']/td[@class='gdt2']/text()")[0]
        gallery.cardinality = int(re.match(r"\d+", cardinality_string).group(0))
        date_string = self.document.xpath("//div[@id='gdd']//tr[td[@class='gdt1']/text()='Posted:']/td[@class='gdt2']/text()")[0]
        gallery.date = datetime.strptime(date_string, "%Y-%m-%d %H:%M")
        rating_string = self.document.xpath("//td[@id='rating_label']/text()")[0]
        rating_match = re.search(r"\d+\.\d+", rating_string)
        if rating_match is None:
            gallery.rating = None
        else:
            gallery.rating = float(rating_match.group(0))

        gallery.rating_max = 5

        try:
            thumbnail_url = self.document.xpath("//div[@class='gdtm']/a/img/attribute::src")[0]
        except IndexError:
            thumbnail_style = self.document.xpath("//div[@class='gdtm']/div/attribute::style")[0]
            thumbnail_url = re.search(r"background:[^;]+url\((.+?)\)", thumbnail_style).group(1)

        gallery.thumbnail = Thumbnail(thumbnail_url)


class ImagePage(Page):
    def get_url(self):
        return self.document.xpath('//div[@class="sni"]/a/img/attribute::src')[0]
