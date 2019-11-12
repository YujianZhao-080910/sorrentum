"""
Import as:

import core.timeseries_study as tss
"""

import logging
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd

import helpers.dbg as dbg

_LOG = logging.getLogger(__name__)


# TODO(gp): -> TimeSeriesAnalyzer?
class _TimeSeriesStudy:
    """
    Perform basic study of time series, such as:
        - analysis at different time frequencies by resampling
        - plot time series for column
            - by year
            - by month
            - by day of week
            - by hour
    """

    def __init__(
        self,
        time_series: pd.Series,
        freq_name: str,
        data_name: Optional[str] = None,
    ):
        """
        :param time_series: pd.Series for which the study needs to be
            conducted
        :param freq_name: The name of the data frequency to add to plot
            titles (for example, 'daily').
        :param data_name: The name of the data to add to plot titles
            (for example, symbol).
        """
        self._time_series = time_series
        self._ts_name = time_series.name
        self._data_name = data_name
        self._freq_name = freq_name

    def plot_time_series(self):
        """
        Plot timeseries on its original time scale.
        """
        self._time_series.plot()
        plt.title(
            f"{self._freq_name.capitalize()} {self._ts_name}"
            f"{self._title_suffix}"
        )
        plt.xticks(
            self._time_series.resample("YS").sum().index,
            ha="right",
            rotation=30,
            rotation_mode="anchor",
        )
        plt.show()

    # TODO(Julia): I would use sharey=True so it's on the same scale.
    def plot_by_year(self, sharey=False):
        """
        Resample yearly and then plot each year on a different plot.
        """
        # Split by year.
        yearly_resample = self._time_series.resample("y")
        # Create as many subplots as years.
        _, axis = plt.subplots(
            len(yearly_resample),
            figsize=(20, 5 * len(yearly_resample)),
            sharey=sharey,
        )
        # Plot each year in a subplot.
        for i, year_ts in enumerate(yearly_resample):
            # resample() is a groupby() returning the value on which we
            # perform the split and the extracted time series.
            group_by, ts = year_ts
            ts.plot(ax=axis[i], title=group_by.year)
        plt.suptitle(
            f"{self._freq_name.capitalize()} {self._ts_name} by year"
            f"{self._title_suffix}",
            # TODO(Julia): Add a comment explaining this.
            y=1.005,
        )
        plt.tight_layout()

    # TODO(gp): Think if it makes sense to generalize this by passing a lambda
    #  that define the timescale, e.g.,
    #   groupby_func = lambda ts: ts.index.day
    #  to sample on many frequencies (e.g., monthly, hourly, minutely, ...)
    #  The goal is to look for seasonality at many frequencies.
    # TODO(gp): It would be nice to plot the timeseries broken down by
    #  different timescales instead of doing the mean in each step
    #  (see https://en.wikipedia.org/wiki/Seasonality#Detecting_seasonality)
    def boxplot_day_of_month(self):
        """
        Plot the mean value of the timeseries for each day.
        """
        self._boxplot(self._time_series, self._time_series.index.day)
        plt.xlabel("day of month")
        plt.title(
            f"{self._freq_name} {self._ts_name} on different days of "
            f"month{self._title_suffix}"
        )
        plt.show()

    def boxplot_day_of_week(self):
        """
        Plot the mean value of the timeseries for year.
        """
        self._boxplot(self._time_series, self._time_series.index.dayofweek)
        plt.xlabel("day of week")
        plt.title(
            f"{self._freq_name} {self._ts_name} on different days of "
            f"week{self._title_suffix}"
        )
        plt.show()

    @staticmethod
    def _boxplot(ts, groupby):
        ts_df = pd.DataFrame(ts)
        ts_df["groupby"] = groupby
        ts_df.boxplot(by="groupby", column=ts.name)
        plt.suptitle("")

    def _check_data_index(self):
        dbg.dassert_isinstance(
            self._time_series.index, pd.DatetimeIndex
        ), "The index should have pd.DatetimeIndex format."
        dbg.dassert_monotonic_index(
            self._time_series.index, "The index should be monotonic increasing"
        )

    @property
    def _title_suffix(self):
        if self._data_name is not None:
            ret = f" for {self._data_name}"
        else:
            ret = ""
        return ret


# TODO(gp): Not sure this is needed if we generalize the super class to work
#  at different frequency. We can have a check that makes sure we always
#  downsample (e.g., we don't plot at minutely timescale if the frequency of the
#  timeseries is hourly).
class TimeSeriesDailyStudy(_TimeSeriesStudy):
    def __init__(
        self,
        time_series: pd.Series,
        freq_name: Optional[str] = None,
        data_name: Optional[str] = None,
    ):
        if not freq_name:
            freq_name = "daily"
        super(TimeSeriesDailyStudy, self).__init__(
            time_series=time_series, freq_name=freq_name, data_name=data_name
        )

    def execute(self):
        self.plot_time_series()
        self.plot_by_year()
        self.boxplot_day_of_month()
        self.boxplot_day_of_week()


class TimeSeriesMinuteStudy(_TimeSeriesStudy):
    def __init__(
        self,
        time_series: pd.Series,
        freq_name: Optional[str] = None,
        data_name: Optional[str] = None,
    ):
        if not freq_name:
            freq_name = "minutely"
        super(TimeSeriesMinuteStudy, self).__init__(
            time_series=time_series, freq_name=freq_name, data_name=data_name
        )

    def execute(self):
        self.plot_time_series()
        self.plot_by_year()
        self.boxplot_day_of_week()
        self.boxplot_minutely_hour()

    def boxplot_minutely_hour(self):
        self._boxplot(self._time_series, self._time_series.index.hour)
        plt.title(
            f"{self._ts_name} during different hours" f"{self._title_suffix}"
        )
        plt.xlabel("hour")
        plt.show()
