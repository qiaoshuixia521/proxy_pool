import scrapy

from ..items import RawProxyUrlItem
from ..rules import TASKS
from ..task_queue import RedisTaskQueue
# from ...crawler_booter import TASK_ITEMS

class BaseSpider(scrapy.Spider):
    name="base_spider"
    task_queue=RedisTaskQueue()#提取要爬去的网站的名字，和该网站的带爬取的url

    custom_settings={
        "DOWNLOAD_DELAY": 0.8,
        "ITEM_PIPELINES":{
            "proxypool.pipelines.RedisRawProxyPipeline": 200,#存储爬去到的代理ip
        }
    }

    def __init__(self):
        super().__init__()
        self.parser={
            "page": self.parse_page,#不同的url（网站返回的数据类型）使用不同的解析函数
            "json": self.parse_json,
        }

    def start_requests(self):
        # for item in self.TASK_ITEIMS:
        #     yield scrapy.Request(item["url"], meta={"name": item["name"]}, callback=self.parse)
        # while not self.task_queue.empty():
        while True:
            item=self.task_queue.get()
            if not item:
                break
            yield scrapy.Request(item["url"], meta={"name": item["name"]}, callback=self.parse)

    def parse(self, response):
        task=TASKS[response.meta["name"]]
        parser_type=task["parser_type"]
        parse_rule=task.get("parse_rule")
        func=self.parser[parser_type]
        if parse_rule:
            return func(response, parse_rule)# **parse_rule)在TASK中记录了发去的规则，只要使用响应的函数，取用resposne.xpath()取提取即可
        else:
            return func(response)

    def parse_page(self, response, rule):
        tables=response.xpath(rule["prefix"])[rule["start_pos"]:rule["end_pos"]]
        for element in tables:
            ip      = element.xpath( rule["detail"] )[rule["ip_pos"]    ].extract()
            port    = element.xpath( rule["detail"] )[rule["port_pos"]  ].extract()
            protocal= "http"
            if rule.get("protocal_pos")!=None:
                protocal=self.get_protocal(
                      element.xpath( rule["detail"] )[rule["protocal_pos"]].extract())
            yield RawProxyUrlItem(url=self.construct_proxy_url(protocal, ip, port))

    def parse_json(self, response, rule):
        pass

    def get_protocal(self, protocal):
        if "sock5" in protocal:
            return "sock5"
        else:
            return "http"

    def construct_proxy_url(self, protocal, ip, port):
        return "%s://%s:%s"%(protocal, ip, port)


