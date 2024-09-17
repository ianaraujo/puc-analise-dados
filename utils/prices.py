import time
import warnings
import requests
import pandas as pd
import yfinance as yf
from bcb import sgs, PTAX

from datetime import datetime
from typing import Optional


def historic_cdi(start: str, end: str) -> pd.Series:
    """
    Baixa os dados históricos do Banco Central em relação ao rendimento do CDI.
    """
    cdi = sgs.get(('CDI', 11), start=start, end=end).squeeze()
    cdi.index = pd.to_datetime(cdi.index, dayfirst=True).date

    cdi_returns = (1 + (cdi / 100)).cumprod()
    cdi_returns = (cdi_returns / cdi_returns.iloc[0])

    return cdi_returns


def historic_imab5(start: Optional[str] = None, end: Optional[str] = None) -> pd.Series:
    """
    Baixa os dados históricos da ANBIMA em relação ao rendimento do índica IMA-B 5.
    """
    ambima = 'https://adata-precos-prod.s3.amazonaws.com/arquivos/indices-historico/IMAB5-HISTORICO.xls'

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = pd.read_excel(ambima)

    imab = data[['Data de Referência', 'Número Índice']]

    imab = imab.set_index('Data de Referência')
    imab.index = pd.to_datetime(imab.index).date

    if start:
        start = datetime.strptime(start, '%Y-%m-%d').date()
        imab = imab.loc[imab.index >= start]

    if end:
        end = datetime.strptime(end, '%Y-%m-%d').date()
        imab = imab.loc[imab.index <= end]

    imab = imab.sort_index()

    imab_normalized = (imab / imab.iloc[0])

    return imab_normalized.squeeze()


def historic_sp500(start: Optional[str] = None, end: Optional[str] = None, brl: bool = False) -> pd.Series:

    SP500 = yf.Ticker('^GSPC')

    sp500_prices = SP500.history(start=start, end=end)['Close']
    sp500_prices.index = pd.to_datetime(sp500_prices.index).date

    if brl:

        start = datetime.strptime(start, '%Y-%m-%d').strftime('%m-%d-%Y')
        end = datetime.strptime(end, '%Y-%m-%d').strftime('%m-%d-%Y')
        
        max_retries = 3
        wait_seconds = 5

        for attempt in range(1, max_retries + 1):
            try:
                ptax = PTAX()
                ep = ptax.get_endpoint(endpoint='CotacaoMoedaPeriodo')

                cotacao_dolar = ep.query() \
                    .parameters(
                        moeda='USD',
                        dataInicial=start,
                        dataFinalCotacao=end
                    )
                
                dolar = cotacao_dolar.collect()
                break

            except Exception as e:
                if attempt < max_retries:
                    print(f"Attempt {attempt} failed with error: {e}. Retrying in 5 seconds...")
                    
                    time.sleep(wait_seconds)
                
                else:
                    print(f"All {max_retries} attempts failed.")
                    raise e 

        dolar = dolar.loc[dolar['tipoBoletim'] == 'Fechamento', :]
        dolar = dolar.set_index('dataHoraCotacao')
        
        dolar.index = pd.to_datetime(dolar.index).date

        sp500_dolar = dolar.join(sp500_prices.to_frame(), how='right')

        sp500_dolar['SP500 BRL'] = sp500_dolar['Close'] * sp500_dolar['cotacaoVenda']

        return sp500_dolar['SP500 BRL'].squeeze()

    return sp500_prices


if __name__ == '__main__':
    sp500 = historic_sp500(start='2004-01-01', end='2024-09-09', brl=True)
    print(sp500)