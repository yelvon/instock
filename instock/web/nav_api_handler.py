#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vue 前端侧栏：与经典版相同的模块分组与链接。"""

import json
from abc import ABC

import tornado.web

import instock.web.base as webBase
from instock.core.singleton_stock_web_module_data import stock_web_module_data


class NavApiHandler(webBase.BaseHandler, ABC):
    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        sw = stock_web_module_data()
        groups = []
        seen = set()
        for item in sw.get_data_list():
            if item.type not in seen:
                seen.add(item.type)
                groups.append({"type": item.type, "ico": item.ico, "items": []})
            for g in groups:
                if g["type"] == item.type:
                    g["items"].append({"name": item.name, "url": item.url})
                    break
        self.write(json.dumps({"ok": True, "groups": groups}, ensure_ascii=False))
