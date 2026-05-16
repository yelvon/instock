#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建后的 Vue SPA：index.html 与 assets 静态资源。"""

import os
from typing import Any, Dict, Optional

import tornado.web

_WEB_DIR = os.path.dirname(os.path.abspath(__file__))
VUE_DIST = os.path.join(_WEB_DIR, "vue-dist")


def vue_dist_dir() -> str:
    return VUE_DIST


class VueIndexHandler(tornado.web.RequestHandler):
    """任意 /instock/app/* 非 assets 路径均返回 index.html（Vue Router history）。"""

    def get(self, path: str = "") -> None:
        index_path = os.path.join(VUE_DIST, "index.html")
        if not os.path.isfile(index_path):
            self.set_status(503)
            self.set_header("Content-Type", "text/html; charset=utf-8")
            self.write(
                "<!DOCTYPE html><html><head><meta charset=utf-8><title>InStock</title></head><body>"
                "<p>Vue 前端尚未构建。请在仓库内执行：</p>"
                "<pre>cd instock/instock/web/vue-app && npm install && npm run build</pre>"
                "<p>完成后重启 Web 服务。</p></body></html>"
            )
            return
        self.set_header("Content-Type", "text/html; charset=utf-8")
        with open(index_path, "rb") as f:
            self.write(f.read())
