import csv

import scrapy
import scrapy.exceptions as ex

import ib_crawler.items as it
import ib_crawler.spiders.ibroker as ib


class ExchangeUniquePipeline:
    seen = set()

    def process_item(self, item: scrapy.Item, spider: ib.IbrokerSpider):
        if isinstance(item, it.ExchangeItem):
            if item["market"] in self.seen:
                raise ex.DropItem("Market already parsed")
            self.seen.add(item["market"])
        return item


class CSVPipeline:
    def __init__(self, exchange_fname: str, symbol_fname: str):
        self.exchange = exchange_fname
        self.symbol = symbol_fname
        self.exchange_seen = set()

    @classmethod
    def from_crawler(cls, crawler: scrapy.Spider):
        return cls(
            exchange_fname=crawler.settings.get("EXCHANGE_FNAME"),
            symbol_fname=crawler.settings.get("SYMBOLS_FNAME"),
        )

    def open_spider(self, spider: ib.IbrokerSpider):
        self.exchange_f = open(self.exchange, "a")
        self.symbol_f = open(self.symbol, "a")
        self.exchange_csv = csv.writer(self.exchange_f, delimiter="\t")
        self.symbol_csv = csv.writer(self.symbol_f, delimiter="\t")

    def close_spider(self, spider: ib.IbrokerSpider):
        self.exchange_f.close()
        self.symbol_f.close()
        # with open(self.exchange) as f:
        #     self.exchange_buf.seek(0)
        #     f.write(self.exchange_buf.getvalue())
        # with open(self.symbol, "a") as f:
        #     self.symbol_buf.seek(0)
        #     f.write(self.symbol_buf.getvalue())

    def process_item(self, item: scrapy.Item, spider: ib.IbrokerSpider):
        if isinstance(item, it.ExchangeItem):
            return self._process_exchange(item)
        if isinstance(item, it.SymbolItem):
            return self._process_symbol(item)

    def _process_exchange(self, item: scrapy.Item):
        self.exchange_csv.writerow(
            [
                item["region"],
                item["country"],
                item["market"],
                item["link"],
                item["products"],
                item["hours"],
            ]
        )
        return item

    def _process_symbol(self, item: scrapy.Item):
        self.symbol_csv.writerow(
            [
                item["market"],
                item["product"],
                item["s_title"],
                item["ib_symbol"],
                item["symbol"],
                item["currency"],
            ]
        )
        return item