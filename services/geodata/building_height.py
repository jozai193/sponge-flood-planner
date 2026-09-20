"""Preserve sourced heights and distinguish floor-derived display estimates."""
import math
import re


def metres(value):
    if isinstance(value, bool):return None
    if isinstance(value, (int, float)):
        result=float(value)
    elif isinstance(value, str):
        match=re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(m|metres?|meters?|ft|feet|')?\s*",value,re.IGNORECASE)
        if not match:return None
        result=float(match[1])*(0.3048 if (match[2] or '').lower() in ('ft','feet',"'") else 1)
    else:return None
    return result if math.isfinite(result) and 1<=result<=1000 else None

def building_height(properties):
    height=metres(properties.get('height'))
    if height is not None:return height,('provider Philadelphia approximate height (feet converted to metres); not independently verified' if properties.get('_sponge_height_source')=='philadelphia_approx_hgt' else 'provider height; not independently verified')
    floors=properties.get('building:levels',properties.get('num_floors'))
    try:
        floors=float(floors)
        if not isinstance(properties.get('building:levels',properties.get('num_floors')),bool) and math.isfinite(floors) and 1<=floors<=200:
            return floors*3.,'estimated from mapped floors at assumed 3 m per floor'
    except (ValueError,TypeError):pass
    return 9.,'assumed display height'


def philadelphia_height_properties(properties):
    """The municipal footprint layer documents its measurements in feet."""
    result=dict(properties)
    fields={k.lower():v for k,v in properties.items()}
    value=fields.get('approx_hgt')
    if not isinstance(value,bool) and isinstance(value,(float,int,str)):
        height=metres(str(value)+' ft')
        if height is not None:
            result['height']=height
            result['_sponge_height_source']='philadelphia_approx_hgt'
    return result
