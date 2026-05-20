#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import os.path
import datetime
import numpy as np
import pandas as pd
import talib as tl
import instock.core.tablestructure as tbs
import instock.lib.trade_time as trd
import instock.core.crawling.trade_date_hist as tdh
import instock.core.crawling.fund_etf_em as fee
import instock.core.crawling.stock_selection as sst
import instock.core.crawling.stock_lhb_em as sle
import instock.core.crawling.stock_lhb_sina as sls
import instock.core.crawling.stock_dzjy_em as sde
import instock.core.crawling.stock_hist_em as she
import instock.core.crawling.baostock_spot as bssp
import instock.core.spot_source as spot_src
import instock.core.crawling.stock_fund_em as sff
import instock.core.crawling.stock_fhps_em as sfe
import instock.core.crawling.stock_chip_race as scr
import instock.core.crawling.stock_limitup_reason as slr

__author__ = 'myh '
__date__ = '2023/3/10 '

# 设置基础目录，每次加载使用。
cpath_current = os.path.dirname(os.path.dirname(__file__))
stock_hist_cache_path = os.path.join(cpath_current, 'cache', 'hist')
if not os.path.exists(stock_hist_cache_path):
    os.makedirs(stock_hist_cache_path)  # 创建多个文件夹结构。


# 600 601 603 605开头的股票是上证A股
# 600开头的股票是上证A股，属于大盘股，其中6006开头的股票是最早上市的股票，
# 6016开头的股票为大盘蓝筹股；900开头的股票是上证B股；
# 688开头的是上证科创板股票；
# 000开头的股票是深证A股，001、002开头的股票也都属于深证A股，
# 其中002开头的股票是深证A股中小企业股票；
# 200开头的股票是深证B股；
# 300、301开头的股票是创业板股票；400开头的股票是三板市场股票。
# 430、83、87开头的股票是北证A股
def is_a_stock(code):
    # 上证A股  # 深证A股
    return code.startswith(('600', '601', '603', '605', '000', '001', '002', '003', '300', '301'))


_INDEX_NAME_RE = __import__("re").compile(
    r"指数|成指|综指|债指|债券|债$|基金|ETF|B股|A股指数|可转债",
    __import__("re").I,
)


def is_tradeable_a_share(code: str, name: str = "") -> bool:
    """可交易 A 股（排除指数、债、基金等；mootdx 列表里大量 000xxx 为深证指数）。"""
    code = str(code).zfill(6)[:6]
    if not is_a_stock(code):
        return False
    if code.startswith(("399", "999")):
        return False
    n = (name or "").strip().replace("\x00", "")
    if n and _INDEX_NAME_RE.search(n):
        return False
    return True


# 过滤掉 st 股票。
def is_not_st(name):
    return not name.startswith(('*ST', 'ST'))


# 过滤价格，如果没有基本上是退市了。
def is_open(price):
    return not np.isnan(price)


def is_open_with_line(price):
    return price != '-'


# 读取股票交易日历数据
def fetch_stocks_trade_date():
    try:
        data = tdh.tool_trade_date_hist_sina()
        if data is None or len(data.index) == 0:
            return None
        data_date = set(data['trade_date'].values.tolist())
        return data_date
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_trade_date处理异常：{e}")
    return None


# 读取当天股票数据
def fetch_etfs(date, spot_source=None):
    """
    :param spot_source: ``eastmoney`` | ``baostock`` | ``auto``；默认读 ``INSTOCK_SPOT_DATA_SOURCE``（未设则为东财）。
    """
    try:
        mode = spot_src.effective_spot_source(spot_source)
        data = None
        if mode in (spot_src.SPOT_SOURCE_EASTMONEY, spot_src.SPOT_SOURCE_AUTO):
            try:
                data = fee.fund_etf_spot_em()
            except Exception as e:
                if mode == spot_src.SPOT_SOURCE_AUTO:
                    logging.warning("东方财富 ETF 快照异常，尝试 Baostock：%s", e)
                    data = None
                else:
                    logging.error("stockfetch.fetch_etfs 东财异常：%s", e)
                    return None
            if (data is None or len(data.index) == 0) and mode == spot_src.SPOT_SOURCE_AUTO:
                logging.warning("东方财富 ETF 快照为空，改用 Baostock 回补")
                data = bssp.fund_etf_spot_baostock(date)
        else:
            data = bssp.fund_etf_spot_baostock(date)
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_ETF_SPOT['columns'])
        data = data.loc[data['new_price'].apply(is_open)]
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_etfs处理异常：{e}")
    return None


def _use_data_registry() -> bool:
    return os.environ.get("INSTOCK_USE_DATA_REGISTRY", "0").strip() in ("1", "true", "yes")


def _fetch_stocks_via_registry(date, spot_source=None):
    """经 DataRegistry 拉 spot（live/backtest profile + enrich）。"""
    try:
        from instock.core.data.registry import get_registry

        td = date
        if td is not None and hasattr(td, "date"):
            td = td.date()
        elif td is None:
            td = datetime.date.today()
        if spot_source:
            os.environ["INSTOCK_SPOT_DATA_SOURCE"] = spot_src.normalize_spot_source(spot_source)
        res = get_registry().fetch_domain("daily_spot_snapshot", trade_date=td)
        if res.ok and res.data is not None and not res.data.empty:
            return res.data
    except Exception as e:
        logging.warning("stockfetch._fetch_stocks_via_registry: %s", e)
    return None


# 读取当天股票数据
def fetch_stocks(date, spot_source=None):
    """
    :param spot_source: ``eastmoney`` | ``baostock`` | ``auto``；默认读 ``INSTOCK_SPOT_DATA_SOURCE``（未设则为东财）。
    """
    if _use_data_registry():
        data = _fetch_stocks_via_registry(date, spot_source)
        if data is not None:
            return data
    try:
        mode = spot_src.effective_spot_source(spot_source)
        data = None
        if mode in (spot_src.SPOT_SOURCE_EASTMONEY, spot_src.SPOT_SOURCE_AUTO):
            try:
                data = she.stock_zh_a_spot_em()
            except Exception as e:
                if mode == spot_src.SPOT_SOURCE_AUTO:
                    logging.warning("东方财富 A 股快照异常，尝试 Baostock：%s", e)
                    data = None
                else:
                    logging.error("stockfetch.fetch_stocks 东财异常：%s", e)
                    return None
            if (data is None or len(data.index) == 0) and mode == spot_src.SPOT_SOURCE_AUTO:
                logging.warning("东方财富 A 股快照为空，改用 Baostock 回补")
                data = bssp.stock_zh_a_spot_baostock(date)
        else:
            data = bssp.stock_zh_a_spot_baostock(date)
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_STOCK_SPOT['columns'])
        data = data.loc[data['code'].apply(is_a_stock)].loc[data['new_price'].apply(is_open)]
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks处理异常：{e}")
    return None


def fetch_stock_selection():
    try:
        data = sst.stock_selection()
        if data is None or len(data.index) == 0:
            return None
        data.columns = list(tbs.TABLE_CN_STOCK_SELECTION['columns'])
        data.drop_duplicates('code', keep='last', inplace=True)
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_selection处理异常：{e}")
    return None


# 读取股票资金流向
def fetch_stocks_fund_flow(index):
    try:
        cn_flow = tbs.CN_STOCK_FUND_FLOW[index]
        data = sff.stock_individual_fund_flow_rank(indicator=cn_flow['cn'])
        if data is None or len(data.index) == 0:
            return None
        data.columns = list(cn_flow['columns'])
        data = data.loc[data['code'].apply(is_a_stock)].loc[data['new_price'].apply(is_open_with_line)]
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_fund_flow处理异常：{e}")
    return None


# 读取板块资金流向
def fetch_stocks_sector_fund_flow(index_sector, index_indicator):
    try:
        cn_flow = tbs.CN_STOCK_SECTOR_FUND_FLOW[1][index_indicator]
        data = sff.stock_sector_fund_flow_rank(indicator=cn_flow['cn'], sector_type=tbs.CN_STOCK_SECTOR_FUND_FLOW[0][index_sector])
        if data is None or len(data.index) == 0:
            return None
        data.columns = list(cn_flow['columns'])
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_sector_fund_flow处理异常：{e}")
    return None


# 读取股票分红配送
def fetch_stocks_bonus(date):
    try:
        data = sfe.stock_fhps_em(date=trd.get_bonus_report_date())
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_STOCK_BONUS['columns'])
        data = data.loc[data['code'].apply(is_a_stock)]
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_bonus处理异常：{e}")
    return None


# 股票近三月上龙虎榜且必须有2次以上机构参与的
def fetch_stock_top_entity_data(date):
    run_date = date + datetime.timedelta(days=-90)
    start_date = run_date.strftime("%Y%m%d")
    end_date = date.strftime("%Y%m%d")
    code_name = '代码'
    entity_amount_name = '买方机构数'
    try:
        data = sle.stock_lhb_jgmmtj_em(start_date, end_date)
        if data is None or len(data.index) == 0:
            return None

        # 机构买入次数大于1计算方法，首先：每次要有买方机构数(>0),然后：这段时间买方机构数求和大于1
        mask = (data[entity_amount_name] > 0)  # 首先：每次要有买方机构数(>0)
        data = data.loc[mask]

        if len(data.index) == 0:
            return None

        grouped = data.groupby(by=data[code_name])
        data_series = grouped[entity_amount_name].sum()
        data_code = set(data_series[data_series > 1].index.values)  # 然后：这段时间买方机构数求和大于1

        if not data_code:
            return None

        return data_code
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_top_entity_data处理异常：{e}")
    return None

# 描述: 获取东方财富-龙虎榜-个股上榜统计
def fetch_stock_lhb_data(date,count=12):
    try:
        start_date = trd.get_previous_trade_date(date,count).strftime("%Y%m%d")
        end_date = date.strftime("%Y%m%d")

        data = sle.stock_lhb_detail_em(start_date, end_date)
        if data is None or len(data.index) == 0:
            return None
        _columns = list(tbs.TABLE_CN_STOCK_lHB['columns'])
        _columns.pop(0)
        data.columns = _columns
        data = data.loc[data['code'].apply(is_a_stock)]
        data.drop_duplicates('code', keep='last', inplace=True)
        # data = data.sort_values(by='ranking_times', ascending=False)
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_lhb_data处理异常：{e}")
    return None

# 描述: 获取新浪财经-龙虎榜-个股上榜统计
def fetch_stock_top_data(date):
    try:
        data = sls.stock_lhb_ggtj_sina()
        if data is None or len(data.index) == 0:
            return None
        _columns = list(tbs.TABLE_CN_STOCK_TOP['columns'])
        _columns.pop(0)
        data.columns = _columns
        data = data.loc[data['code'].apply(is_a_stock)]
        data.drop_duplicates('code', keep='last', inplace=True)
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_top_data处理异常：{e}")
    return None


# 描述: 获取东方财富网-数据中心-大宗交易-每日统计
def fetch_stock_blocktrade_data(date):
    date_str = date.strftime("%Y%m%d")
    try:
        data = sde.stock_dzjy_mrtj(start_date=date_str, end_date=date_str)
        if data is None or len(data.index) == 0:
            return None

        columns = list(tbs.TABLE_CN_STOCK_BLOCKTRADE['columns'])
        columns.insert(0, 'index')
        data.columns = columns
        data = data.loc[data['code'].apply(is_a_stock)]
        data.drop('index', axis=1, inplace=True)
        return data
    except TypeError:
        logging.error("处理异常：目前还没有大宗交易数据，请17:00点后再获取！")
        return None
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_blocktrade_data处理异常：{e}")
    return None

# 读取早盘抢筹
def fetch_stock_chip_race_open(date):
    try:
        date_str =""
        if date != datetime.datetime.now().date():
            date_str = date.strftime("%Y%m%d")
        data = scr.stock_chip_race_open(date_str)
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_STOCK_CHIP_RACE_OPEN['columns'])
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_chip_race_open处理异常：{e}")
    return None

# 读取尾盘抢筹
def fetch_stock_chip_race_end(date):
    try:
        date_str =""
        if date != datetime.datetime.now().date():
            date_str = date.strftime("%Y%m%d")
        data = scr.stock_chip_race_end(date_str)
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_STOCK_CHIP_RACE_END['columns'])
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_chip_race_end处理异常：{e}")
    return None

# 读取涨停原因
def fetch_stock_limitup_reason(date):

    try:
        data = slr.stock_limitup_reason(date.strftime("%Y-%m-%d"))
        if data is None or len(data.index) == 0:
            return None
        data.columns = list(tbs.TABLE_CN_STOCK_LIMITUP_REASON['columns'])
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_limitup_reason处理异常：{e}")
    return None

# 读取股票历史数据
def fetch_etf_hist(data_base, date_start=None, date_end=None, adjust='qfq'):
    date = data_base[0]
    code = data_base[1]

    if date_start is None:
        date_start, is_cache = trd.get_trade_hist_interval(date)  # 提高运行效率，只运行一次
    try:
        if date_end is not None:
            data = fee.fund_etf_hist_em(symbol=code, period="daily", start_date=date_start, end_date=date_end,
                                        adjust=adjust)
        else:
            data = fee.fund_etf_hist_em(symbol=code, period="daily", start_date=date_start, adjust=adjust)

        if data is None or len(data.index) == 0:
            return None
        data.columns = tuple(tbs.CN_STOCK_HIST_DATA['columns'])
        data = data.sort_index()  # 将数据按照日期排序下。
        if data is not None:
            data.loc[:, 'p_change'] = tl.ROC(data['close'].values, 1)
            data['p_change'].values[np.isnan(data['p_change'].values)] = 0.0
            data["volume"] = data['volume'].values.astype('double') * 100  # 成交量单位从手变成股。
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_etf_hist处理异常：{e}")
    return None


# 读取股票历史数据
def fetch_stock_hist(data_base, date_start=None, is_cache=True):
    date = data_base[0]
    code = data_base[1]

    if date_start is None:
        date_start, is_cache = trd.get_trade_hist_interval(date)  # 提高运行效率，只运行一次
        # date_end = date_end.strftime("%Y%m%d")
    try:
        data = stock_hist_cache(code, date_start, None, is_cache, 'qfq')
        if data is not None:
            data.loc[:, 'p_change'] = tl.ROC(data['close'].values, 1)
            data['p_change'].values[np.isnan(data['p_change'].values)] = 0.0
            data["volume"] = data['volume'].values.astype('double') * 100  # 成交量单位从手变成股。
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_hist处理异常：{e}")
    return None


def _align_hist_dataframe(stock: pd.DataFrame) -> pd.DataFrame:
    """统一为 CN_STOCK_HIST_DATA 的 11 列（含 date 列，与东财 hist 一致）。"""
    hist_cols = list(tbs.CN_STOCK_HIST_DATA["columns"].keys())
    out = stock.copy()
    out = out.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "quote_change",
            "涨跌额": "ups_downs",
            "换手率": "turnover",
        }
    )
    if "date" not in out.columns:
        out = out.reset_index()
        if "index" in out.columns:
            out = out.rename(columns={"index": "date"})
        elif out.columns[0] not in hist_cols:
            out = out.rename(columns={out.columns[0]: "date"})
    for c in hist_cols:
        if c not in out.columns:
            out[c] = np.nan
    out = out[hist_cols]
    if "date" in out.columns:
        out = out.sort_values("date")
    return out


# 增加读取股票缓存方法。加快处理速度。多线程解决效率
def stock_hist_cache(code, date_start, date_end=None, is_cache=True, adjust=''):
    cache_dir = os.path.join(stock_hist_cache_path, date_start[0:6], date_start)
    # 如果没有文件夹创建一个。月文件夹和日文件夹。方便删除。
    try:
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    except Exception:
        pass
    cache_suffix = adjust if adjust else "raw"
    cache_file = os.path.join(cache_dir, "%s%s.gzip.pickle" % (code, cache_suffix))
    # 如果缓存存在就直接返回缓存数据。压缩方式。
    try:
        if os.path.isfile(cache_file):
            return pd.read_pickle(cache_file, compression="gzip")
        else:
            stock = None
            provider_used = "eastmoney"
            use_reg = _use_data_registry() or os.environ.get("INSTOCK_BAR_MODE", "raw").strip().lower() == "raw"
            if use_reg and (not adjust or adjust in ("", "raw")):
                res = None
                try:
                    from instock.core.data.registry import get_registry
                    from instock.core.data.lineage import record_batch

                    res = get_registry().fetch_domain(
                        "daily_bar_raw",
                        code=code,
                        date_from=date_start,
                        date_to=date_end,
                    )
                    if res.ok and res.data is not None and not res.data.empty:
                        stock = res.data.copy()
                        if not isinstance(stock.index, pd.DatetimeIndex) and "date" in stock.columns:
                            stock = stock.set_index("date")
                        provider_used = res.provider_id or "registry"
                        if is_cache:
                            try:
                                stock.to_pickle(cache_file, compression="gzip")
                            except Exception:
                                pass
                            try:
                                res.domain_id = "daily_bar_raw"
                                res.scope_type = "code"
                                res.scope_key = code
                                res.metadata.setdefault("adjust_type", "raw")
                                record_batch(res, job_id="stock_hist_cache")
                            except Exception:
                                pass
                except Exception as e:
                    logging.warning("stock_hist_cache registry: %s", e)
                else:
                    if stock is None and res is not None and not res.ok:
                        logging.debug(
                            "stock_hist_cache %s: %s — %s",
                            code,
                            res.provider_id or "registry",
                            res.error or "无数据",
                        )
            if stock is None:
                from instock.core.data.profile import allow_eastmoney_hist_fallback

                if not allow_eastmoney_hist_fallback():
                    logging.info(
                        "stock_hist_cache %s: Registry 无数据，已禁用东财回退（日线源=%s）",
                        code,
                        os.environ.get("INSTOCK_BAR_DATA_SOURCE", "auto"),
                    )
                    return None
                em_adj = adjust if adjust else ("qfq" if not use_reg else "")
                if date_end is not None:
                    stock = she.stock_zh_a_hist(
                        symbol=code,
                        period="daily",
                        start_date=date_start,
                        end_date=date_end,
                        adjust=em_adj,
                    )
                else:
                    stock = she.stock_zh_a_hist(
                        symbol=code,
                        period="daily",
                        start_date=date_start,
                        adjust=em_adj,
                    )
                provider_used = "eastmoney"

            if stock is None or len(stock.index) == 0:
                return None
            stock = _align_hist_dataframe(stock)
            try:
                if is_cache and provider_used == "eastmoney":
                    stock.to_pickle(cache_file, compression="gzip")
            except Exception:
                pass
            return stock
    except Exception as e:
        logging.error(f"stockfetch.stock_hist_cache处理异常：{code}代码{e}")
    return None
