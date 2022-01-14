"""
Import as:

import dataflow.system.real_time_dag_adapter as dtfsrtdaad
"""

from typing import Optional

import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system.sink_nodes as dtfsysinod
import dataflow.system.source_nodes as dtfsysonod
import oms.portfolio as omportfo


class RealTimeDagAdapter(dtfcore.DagAdapter):
    """
    Adapt a DAG builder to RT execution by injecting real-time nodes.
    """

    # TODO(gp): Expose more parameters as needed.
    def __init__(
        self,
        dag_builder: dtfcore.DagBuilder,
        portfolio: omportfo.AbstractPortfolio,
        prediction_col: str,
        volatility_col: str,
        period: str,
        asset_id_col: str,
        log_dir: Optional[str] = None,
    ):
        market_data = portfolio.market_data
        #
        overriding_config = cconfig.Config()
        # Configure a DataSourceNode.
        source_node_kwargs = {
            "market_data": market_data,
            "period": period,
            "asset_id_col": asset_id_col,
            "multiindex_output": True,
        }
        overriding_config["load_prices"] = {
            "source_node_name": "RealTimeDataSource",
            "source_node_kwargs": source_node_kwargs,
        }
        # Configure a ProcessForecast node.
        order_type = "price@twap"
        overriding_config["process_forecasts"] = {
            "prediction_col": prediction_col,
            "volatility_col": volatility_col,
            "portfolio": portfolio,
            "process_forecasts_config": {},
        }
        # We could also write the `process_forecasts_config` key directly but we
        # want to show a `Config` created with multiple pieces.
        overriding_config["process_forecasts"]["process_forecasts_config"] = {
            "market_data": market_data,
            "order_type": order_type,
            "order_duration": 5,
            "ath_start_time": pd.Timestamp(
                "2000-01-01 09:30:00-05:00", tz="America/New_York"
            ).time(),
            "trading_start_time": pd.Timestamp(
                "2000-01-01 09:30:00-05:00", tz="America/New_York"
            ).time(),
            "ath_end_time": pd.Timestamp(
                "2000-01-01 16:40:00-05:00", tz="America/New_York"
            ).time(),
            "trading_end_time": pd.Timestamp(
                "2000-01-01 16:40:00-05:00", tz="America/New_York"
            ).time(),
            "execution_mode": "real_time",
            "log_dir": log_dir,
        }
        # Insert a node.
        nodes_to_insert = []
        stage = "load_prices"
        node_ctor = dtfsysonod.data_source_node_factory
        nodes_to_insert.append((stage, node_ctor))
        # Append a ProcessForecastNode node.
        nodes_to_append = []
        stage = "process_forecasts"
        node_ctor = dtfsysinod.ProcessForecasts
        nodes_to_append.append((stage, node_ctor))
        #
        super().__init__(
            dag_builder, overriding_config, nodes_to_insert, nodes_to_append
        )