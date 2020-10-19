# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions
import datetime
import logging
import requests
from odoo.tools.safe_eval import safe_eval
import json

_logger = logging.getLogger(__name__)


def call_sbif(currency_name,currency_date):

    apikey="?apikey=59c44c6a3ed8d27130d419c7406fdeee0ce84823"
    data_format="&formato=json"
    valor_uf=1
    valor_dolar=1
    valor=1
   
                  
    if currency_name!="CLP":
        try:
        
            if currency_name == "UF":
                base_url="http://api.sbif.cl/api-sbifv3/recursos_api/uf/"
                search_sign='UFs'
                
            if currency_name=="USD":
                base_url="http://api.sbif.cl/api-sbifv3/recursos_api/dolar/"
                search_sign='Dolares'                     
        
            year=currency_date.year
            month=currency_date.month
            day=currency_date.day
            ufurl=base_url+str(year)+"/"+str(month)+"/dias/"+str(day)+apikey+data_format
            r=requests.get(ufurl)
            _logger.info("sbifdata=%s",r.text)
            data=r.text
            raw_data=safe_eval(data)
            raw_list=raw_data.get(search_sign, False)
            raw_value=raw_list[0]["Valor"]
            valor_str=raw_value.replace(".","").replace(",",".")
            valor=float(valor_str)

        except Exception as e:                  
            message='No se podia conseguir Tasa de Cambio. Por favor contactese con el Admin del sistema!\n\n'+str(e)                    
            _logger.info(message)
            pass

    if currency_name == "UF":
        return valor, valor_dolar       
    elif currency_name == "USD":
        return valor_uf,valor

    else:
        return valor_uf,valor_dolar
        
        
        
def call_mindicator(currency_name,currency_date):

    
    valor_uf=1
    valor_dolar=1
    valor=1
   
                  
    if currency_name!="CLP":
        try:
           
            if currency_name == "UF":
                search_sign='uf'
                
            elif currency_name=="USD":
                search_sign='dolar'                     
            else:
                search_sign='clp'
        
            search_year='-'.join((str(currency_date.day),str(currency_date.month),str(currency_date.year)))
        
        
            url = f'https://mindicador.cl/api/{search_sign}/{search_year}'
            response = requests.get(url)
            data = json.loads(response.text.encode("utf-8"))
            _logger.info("mindicadordata=%s",data)
            valor=data.get('serie',{})[0].get('valor',1)
        

        except Exception as e:                  
            message='No se podia conseguir Tasa de Cambio. Por favor contactese con el Admin del sistema!\n\n'+str(e)                    
            _logger.info(message)
            pass

    if currency_name == "UF":
        return valor, valor_dolar       
    elif currency_name == "USD":
        return valor_uf,valor

    else:
        return valor_uf,valor_dolar        
        
        