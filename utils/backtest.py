import pandas as pd
import numpy as np

def _first_trading_days(window: pd.DataFrame) -> pd.Series: 
    time_series = pd.to_datetime(window.index).to_series()
    ftd = time_series.groupby(time_series.index.to_period('M')).apply(lambda x: x == x.min())

    return ftd

def calculate_returns(window: pd.DataFrame) -> dict:
    prices = (1 + window).cumprod()
    prices = (prices / prices.iloc[0])

    shifted_prices = prices.shift(21)
    momentum_returns = shifted_prices.pct_change(periods=231).dropna()

    first_trading_day = _first_trading_days(momentum_returns)

    conditions = [
        first_trading_day.values & (momentum_returns['IBOV'] > momentum_returns['SP500 BRL']) & (momentum_returns['IBOV'] > momentum_returns['CDI']),
        first_trading_day.values & (momentum_returns['IBOV'] < momentum_returns['SP500 BRL']) & (momentum_returns['SP500 BRL'] > momentum_returns['CDI']),
        first_trading_day.values & (momentum_returns[['IBOV', 'SP500 BRL']].max(axis=1) < momentum_returns['CDI'])
    ]

    cases = ['IBOV', 'SP500 BRL', 'IMA-B 5']

    momentum_returns['Investment'] = np.select(conditions, cases, default=None)
    momentum_returns['Investment'] = momentum_returns['Investment'].ffill()

    dual_momentum = prices.pct_change().join(momentum_returns[['Investment']], how='right')

    dual_momentum['Dual Momentum'] = dual_momentum.apply(lambda row: row[row['Investment']], axis=1)
    dual_momentum = dual_momentum.drop(columns=['Investment'])

    dual_momentum_eval = (1 + dual_momentum).cumprod()
    dual_momentum_eval = (dual_momentum_eval / dual_momentum_eval.iloc[0]) - 1

    results = {col: dual_momentum_eval[col].iloc[-1] for col in dual_momentum_eval.columns}

    return results