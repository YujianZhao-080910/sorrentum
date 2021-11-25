# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
import logging
import os

import pandas as pd
import seaborn as sns

import core.config.config_ as cconconf
import helpers.dbg as hdbg
import helpers.env as henv
import helpers.printing as hprint
import helpers.s3 as hs3
import im_v2.common.universe.universe as imvcounun
import research_amp.cc.statistics as rccstat
import research_amp.cc.volume as rccvolu
import im_v2.ccxt.data.client.clients as imcdaclcl

import core.plotting as coplotti


# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
def get_cmtask260_config() -> cconconf.Config:
    """
    Get task260-specific config.
    """
    config = cconconf.Config()
    # Load parameters.
    config.add_subconfig("load")
    config["load"]["aws_profile"] = "am"
    config["load"]["data_dir"] = os.path.join(hs3.get_path(), "data")
    # Data parameters.
    config.add_subconfig("data")
    config["data"]["data_type"] = "OHLCV"
    config["data"]["universe_version"] = "v03"
    config["data"]["vendor"] = "CCXT"
    # Column names.
    config.add_subconfig("column_names")
    config["column_names"]["volume"] = "volume"
    config["column_names"]["currency_pair"] = "currency_pair"
    config["column_names"]["exchange"] = "exchange_id"
    config["column_names"]["close"] = "close"
    return config


config = get_cmtask260_config()
print(config)

# %% [markdown]
# # Load the data

# %%
vendor_universe = imvcounun.get_vendor_universe_as_tuples(
    config["data"]["universe_version"], config["data"]["vendor"]
)
vendor_universe

# %%
compute_daily_cumul_volume_ = lambda data: rccvolu.get_daily_cumul_volume(
    data, config, is_notional_volume=False
)

cumul_daily_volume = rccstat.compute_stats_for_universe(
    vendor_universe, config, compute_daily_cumul_volume_
)

# %%
_LOG.info(
    "The number of (exchanges, currency pairs) =%s", cumul_daily_volume.shape[0]
)
cumul_daily_volume.head(3)

# %% [markdown]
# # Compute total volume per exchange

# %%
total_volume_by_exchange = rccvolu.get_total_exchange_volume(
    cumul_daily_volume, config, avg_daily=False
)
print(total_volume_by_exchange)

# %% [markdown]
# # Compute total volume per currency

# %%
total_volume_by_coins = rccvolu.get_total_coin_volume(
    cumul_daily_volume, config, avg_daily=False
)
print(total_volume_by_coins)

# %% [markdown]
# # Rolling Plots

# %% [markdown]
# ## By exchange

# %%
rolling_volume_per_exchange = rccvolu.get_rolling_volume_per_exchange(
    cumul_daily_volume, config, window=90
)
print(rolling_volume_per_exchange)

# %% [markdown]
# ## By coins

# %%
rolling_volume_per_coin = rccvolu.get_rolling_volume_per_coin(
    cumul_daily_volume, config, window=90
)
print(rolling_volume_per_coin)

# %% [markdown]
# # Compare weekday volumes

# %%
total_volume_by_weekdays = rccvolu.compare_weekday_volumes(
    cumul_daily_volume, config
)
print(total_volume_by_weekdays)


# %% [markdown]
# # Compare ATH volumes

# %% [markdown]
# ## Functions

# %%
def get_initial_df_with_volumes(coins, exchange, is_notional_volume):
    """
    Return DataFrame with the volume of all coins for exchange with initial timestamps
    Parameters: list of coins, exchange name
    """
    result = []
    loader = imcdaclcl.CcxtFileSystemClient(
        data_type="OHLCV",
        root_dir=os.path.join(hs3.get_path(), "data"),
        aws_profile="am",
    )
    for coin in coins:
        # TODO(Grisha): use `_` as currencies separator #579.
        coin = coin.replace("/", "_")
        # TODO(Grisha): use `FullSymbols` #587.
        full_symbol = f"{exchange}::{coin}"
        df = loader.read_data(full_symbol)
        if is_notional_volume:
            df["volume"] = df["volume"] * df["close"]
        result.append(df["volume"])
    final_result = pd.concat(result, axis=1)
    return final_result


def plot_ath_volumes_comparison(df_list):
    """
    Return the graph with the comparison of average minute total trading volume
    in ATH vs.

    non-ATH
    Parameters: dataframe with volumes from a given exchange
    """
    plot_df = []
    for df in df_list:
        df_ath = df.iloc[df.index.indexer_between_time("09:30", "16:00")]
        df_not_ath = df.loc[~df.index.isin(df_ath.index)]
        ath_stat = pd.DataFrame()
        ath_stat.loc[df.name, f"minute_avg_total_volume_ath_{df.name}"] = (
            df_ath.sum().sum() / df_ath.shape[0]
        )
        ath_stat.loc[df.name, f"minute_avg_total_volume_not_ath_{df.name}"] = (
            df_not_ath.sum().sum() / df_not_ath.shape[0]
        )
        plot_df.append(ath_stat)
    plot_df = pd.concat(plot_df)
    plot_df.plot.bar(figsize=(15, 7), logy=True)


# %% [markdown]
# ## Load the data

# %%
# get the list of all coin paires for each exchange
binance_coins = imvcounun.get_trade_universe("v03")["CCXT"]["binance"]
ftx_coins = imvcounun.get_trade_universe("v03")["CCXT"]["ftx"]
gateio_coins = imvcounun.get_trade_universe("v03")["CCXT"]["gateio"]
kucoin_coins = imvcounun.get_trade_universe("v03")["CCXT"]["kucoin"]

# load all the dataframes
binance_1 = get_initial_df_with_volumes(
    binance_coins, "binance", is_notional_volume=True
)
ftx_1 = get_initial_df_with_volumes(ftx_coins, "ftx", is_notional_volume=True)
gateio_1 = get_initial_df_with_volumes(
    gateio_coins, "gateio", is_notional_volume=True
)
kucoin_1 = get_initial_df_with_volumes(
    kucoin_coins, "kucoin", is_notional_volume=True
)

# supportive variables
exchange_list = [binance_1, ftx_1, gateio_1, kucoin_1]
binance_1.name = "binance"
ftx_1.name = "ftx"
gateio_1.name = "gateio"
kucoin_1.name = "kucoin"

# %% [markdown]
# ## Plot

# %%
plot_ath_volumes_comparison(exchange_list)