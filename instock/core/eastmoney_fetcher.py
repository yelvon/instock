#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import random
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from instock.core.singleton_proxy import proxys

__author__ = 'myh '
__date__ = '2025/12/31 '

_log = logging.getLogger(__name__)


def _env_float(name: str, default: str) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def _default_request_timeout():
    """(connect, read) 秒；读超时略大以减轻东财大 JSON / 502 风暴下的 ReadTimeout。"""
    return (
        _env_float("INSTOCK_EM_HTTP_CONNECT_TIMEOUT", "10"),
        _env_float("INSTOCK_EM_HTTP_READ_TIMEOUT", "45"),
    )


def _outer_retry_count() -> int:
    try:
        return max(1, min(8, int(os.environ.get("INSTOCK_EM_OUTER_RETRIES", "4"))))
    except (TypeError, ValueError):
        return 4


class eastmoney_fetcher:
    """
    东方财富网数据获取器
    封装了Cookie管理、会话管理和请求发送功能
    """

    def __init__(self):
        """初始化获取器"""
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.session = self._create_session()
        self.proxies = proxys().get_proxies()

    def _get_cookie(self):
        """
        获取东方财富网的Cookie
        优先级：环境变量 > 文件 > 默认Cookie
        """
        # 1. 尝试从环境变量获取
        cookie = os.environ.get('EAST_MONEY_COOKIE')
        if cookie:
            # print("环境变量中的Cookie: 已设置")
            return cookie

        # 2. 尝试从文件获取
        cookie_file = Path(os.path.join(self.base_dir, 'config', 'eastmoney_cookie.txt'))
        if cookie_file.exists():
            with open(cookie_file, "r", encoding="utf-8", errors="replace") as f:
                cookie = f.read().strip()
            if cookie:
                # print("文件中的Cookie: 已设置")
                return cookie

        # 3. 默认Cookie（可能过期，仅作为备选）
        return 'st_si=78948464251292; st_psi=20260205091253851-119144370567-1089607836; st_pvi=07789985376191; st_sp=2026-02-05%2009%3A11%3A13; st_inirUrl=https%3A%2F%2Fxuangu.eastmoney.com%2FResult; st_sn=12; st_asi=20260205091253851-119144370567-1089607836-webznxg.dbssk.qxg-1'

    def _create_session(self):
        """创建并配置会话"""
        session = requests.Session()

        # 连接层重试：502/断连时略拉长间隔，减轻「too many 502」与对端掐连接
        retry_strategy = Retry(
            total=6,
            backoff_factor=0.9,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=24,
            pool_maxsize=24,
        )

        # 为http和https请求添加适配器
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://quote.eastmoney.com/',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            # 勿声明 br/zstd：未装 brotli 时服务端若返回 br，正文无法解压，r.json() 会报 Expecting value
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        ck = self._get_cookie()
        if ck:
            # 必须写在 headers 里：cookies.update({'Cookie': ...}) 会变成名为 Cookie 的单条 cookie，服务端认不出来
            headers["Cookie"] = ck
        session.headers.update(headers)
        return session

    def make_request(self, url, params=None, retry=None, timeout=None):
        """
        发送请求
        :param url: 请求URL
        :param params: 请求参数
        :param retry: 应用层重试次数（None 则读环境变量 INSTOCK_EM_OUTER_RETRIES，默认 4）
        :param timeout: 秒标量或 (connect, read) 元组；None 则用 INSTOCK_EM_HTTP_* 环境变量
        :return: 响应对象
        """
        if retry is None:
            retry = _outer_retry_count()
        if timeout is None:
            timeout = _default_request_timeout()
        for i in range(retry):
            try:
                response = self.session.get(
                    url,
                    proxies=self.proxies,
                    params=params,
                    timeout=timeout,
                )
                response.raise_for_status()  # 检查HTTP错误
                return response
            except requests.exceptions.RequestException as e:
                _log.warning("eastmoney GET 失败 %s/%s: %s", i + 1, retry, e)
                if i < retry - 1:
                    # 指数退避 + 抖动，减轻限流与 502 连击
                    base = 1.2 * (2**i)
                    time.sleep(random.uniform(base, base + 2.5))
                else:
                    raise

    def make_post_request(self, url, data=None, json=None, params=None, retry=None, timeout=None):
        """
        发送POST请求
        :param url: 请求URL
        :param data: 请求数据（表单形式）
        :param json: 请求数据（JSON形式）
        :param params: URL参数
        :param retry: 应用层重试次数（None 则同 make_request）
        :param timeout: 默认 (10, 60) 读略长便于大响应
        :return: 响应对象
        """
        if retry is None:
            retry = _outer_retry_count()
        if timeout is None:
            timeout = (
                _env_float("INSTOCK_EM_HTTP_CONNECT_TIMEOUT", "10"),
                max(60.0, _env_float("INSTOCK_EM_HTTP_READ_TIMEOUT", "45")),
            )
        for i in range(retry):
            try:
                response = self.session.post(
                    url,
                    proxies=self.proxies,
                    params=params,
                    data=data,
                    json=json,
                    timeout=timeout,
                )
                response.raise_for_status()  # 检查HTTP错误
                return response
            except requests.exceptions.RequestException as e:
                _log.warning("eastmoney POST 失败 %s/%s: %s", i + 1, retry, e)
                if i < retry - 1:
                    base = 1.2 * (2**i)
                    time.sleep(random.uniform(base, base + 2.5))
                else:
                    raise

    def update_cookie(self, new_cookie):
        """更新 Cookie（与浏览器 DevTools 中整段 Cookie 字符串一致）。"""
        if new_cookie:
            self.session.headers["Cookie"] = new_cookie
