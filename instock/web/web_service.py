#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import logging
import os.path
import sys
from abc import ABC

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado import gen

# 在项目运行时，临时将项目路径添加到环境变量
cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)
log_path = os.path.join(cpath_current, 'log')
if not os.path.exists(log_path):
    os.makedirs(log_path)
logging.basicConfig(format='%(asctime)s %(message)s', filename=os.path.join(log_path, 'stock_web.log'))
logging.getLogger().setLevel(logging.ERROR)
import instock.lib.torndb as torndb
import instock.lib.database as mdb
import instock.web.dataTableHandler as dataTableHandler
import instock.web.dataIndicatorsHandler as dataIndicatorsHandler
import instock.web.sync_job_handler as syncJobHandler
import instock.web.base as webBase
import instock.web.sync_job_service as syncJobService
import instock.web.scheduler_service as schedulerService
import instock.web.vue_spa_handler as vueSpaHandler
import instock.web.nav_api_handler as navApiHandler
import instock.web.table_meta_handler as tableMetaHandler
import instock.web.backtest_handler as backtestHandler
import instock.web.canonical_kline_handler as canonicalKlineHandler
import instock.web.host_ops_handler as hostOpsHandler
import tornado.web

__author__ = 'myh '
__date__ = '2023/3/10 '

_VUE_ASSETS = os.path.join(vueSpaHandler.VUE_DIST, "assets")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            # 设置路由
            (r"/", HomeHandler),
            (r"/instock/", HomeHandler),
            # 使用datatable 展示报表数据模块。
            (r"/instock/api_data", dataTableHandler.GetStockDataHandler),
            (r"/instock/data", dataTableHandler.GetStockHtmlHandler),
            # 获得股票指标数据。
            (r"/instock/data/indicators", dataIndicatorsHandler.GetDataIndicatorsHandler),
            # 加入关注
            (r"/instock/control/attention", dataIndicatorsHandler.SaveCollectHandler),
            # 数据同步（作业触发与记录）
            (r"/instock/sync", syncJobHandler.SyncPageHandler),
            (r"/instock/api/sync/jobs", syncJobHandler.SyncJobsApiHandler),
            (r"/instock/api/sync/runs", syncJobHandler.SyncRunsApiHandler),
            (r"/instock/api/sync/data_health", syncJobHandler.DataHealthApiHandler),
            (r"/instock/api/sync/run_detail", syncJobHandler.SyncRunDetailApiHandler),
            (r"/instock/api/sync/trigger", syncJobHandler.SyncRunPostHandler),
            (r"/instock/api/sync/cancel", syncJobHandler.SyncCancelHandler),
            (r"/instock/api/sync/retry", syncJobHandler.SyncRetryHandler),
            (r"/instock/api/sync/delete_run", syncJobHandler.SyncDeleteRunHandler),
            (r"/instock/api/sync/delete_runs", syncJobHandler.SyncDeleteRunsHandler),
            (r"/instock/api/sync/prune_runs", syncJobHandler.SyncPruneRunsHandler),
            (r"/instock/api/sync/cookie", syncJobHandler.SyncCookieApiHandler),
            (r"/instock/api/sync/prefs", syncJobHandler.SyncPrefsApiHandler),
            (r"/instock/api/sync/scheduler", syncJobHandler.SchedulerConfigApiHandler),
            (r"/instock/api/sync/data_batches", syncJobHandler.DataBatchesApiHandler),
            (r"/instock/api/sync/governance_env", syncJobHandler.DataGovernanceEnvApiHandler),
            (r"/instock/api/sync/eastmoney_probe", syncJobHandler.EastmoneyProbeApiHandler),
            (r"/instock/api/sync/mootdx_probe", syncJobHandler.MootdxProbeApiHandler),
            (r"/instock/api/sync/data_sources", syncJobHandler.DataSourcesApiHandler),
            (r"/instock/api/sync/canonical", syncJobHandler.CanonicalGovernanceApiHandler),
            (r"/instock/api/nav", navApiHandler.NavApiHandler),
            (r"/instock/api/table_meta", tableMetaHandler.TableMetaHandler),
            (r"/instock/api/kline_bundle", tableMetaHandler.KlineBundleApiHandler),
            (r"/instock/api/canonical/kline", canonicalKlineHandler.CanonicalKlineApiHandler),
            (r"/instock/api/backtest/strategies", backtestHandler.BacktestStrategiesApiHandler),
            (r"/instock/api/backtest/runs", backtestHandler.BacktestRunsApiHandler),
            (r"/instock/api/backtest/runs/([^/]+)/kline", backtestHandler.BacktestRunKlineApiHandler),
            (r"/instock/api/backtest/runs/([^/]+)/cancel", backtestHandler.BacktestRunCancelApiHandler),
            (r"/instock/api/backtest/runs/([^/]+)", backtestHandler.BacktestRunDetailApiHandler),
            (r"/instock/api/host_ops/status", hostOpsHandler.HostOpsStatusHandler),
            (r"/instock/api/host_ops/tasks", hostOpsHandler.HostOpsTasksHandler),
            (r"/instock/api/host_ops/runs", hostOpsHandler.HostOpsRunsHandler),
            (r"/instock/api/host_ops/run_detail", hostOpsHandler.HostOpsRunDetailHandler),
            (r"/instock/api/host_ops/trigger", hostOpsHandler.HostOpsTriggerHandler),
            (r"/instock/api/host_ops/cancel", hostOpsHandler.HostOpsCancelHandler),
            (r"/instock/app/assets/(.*)", tornado.web.StaticFileHandler, {"path": _VUE_ASSETS}),
            (r"/instock/app/?(.*)", vueSpaHandler.VueIndexHandler),
        ]
        settings = dict(  # 配置
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=False,  # True,
            # cookie加密
            cookie_secret="027bb1b670eddf0392cdda8709268a17b58b7",
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)
        # Have one global connection to the blog DB across all handlers
        self.db = torndb.Connection(**mdb.MYSQL_CONN_TORNDB)
        syncJobService.init_history()


# 首页 → Vue SPA
class HomeHandler(webBase.BaseHandler, ABC):
    @gen.coroutine
    def get(self):
        self.redirect("/instock/app/home", permanent=False)


def main():
    # tornado.options.parse_command_line()
    tornado.options.options.logging = None

    http_server = tornado.httpserver.HTTPServer(Application())
    port = 9988
    http_server.listen(port)

    print(f"服务已启动，web地址 : http://localhost:{port}/")
    logging.error(f"服务已启动，web地址 : http://localhost:{port}/")

    schedulerService.install_tornado_scheduler()

    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
