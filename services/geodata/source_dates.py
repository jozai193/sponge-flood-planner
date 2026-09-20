"""Separate observation dates from publication and download metadata."""
import re
from datetime import date, datetime
from urllib.parse import urlparse


def _date(value):
    if not isinstance(value,str):return None
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return date.fromisoformat(value).isoformat()
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:return None


def source_dates(sources):
    rows=[];seen=set()
    for source in sources:
        if not isinstance(source,dict):continue
        url=source.get('source_url','');url=url if isinstance(url,str) else ''
        observed=[]
        for field,label in (('observed_at','Observed'),('acquired_at','Acquired'),('acquisition_date','Acquired'),('survey_date','Surveyed')):
            value=_date(source.get(field))
            if value and (label,value) not in observed:observed.append((label,value))
        year=source.get('year');period=str(year) if type(year) is int and 1800<=year<=2200 else None
        # This adapter uses a named annual WorldCover product. Its product year
        # describes the classification period, not a per-pixel capture date.
        parsed=urlparse(url)
        if not period and parsed.hostname=='esa-worldcover.s3.eu-central-1.amazonaws.com':
            match=re.search(r'/ESA_WorldCover_10m_(\d{4})_v\d+_',parsed.path)
            if match:period=match[1]
        title=source.get('title') or source.get('provider') or (parsed.path.rsplit('/',1)[-1] if url else 'Unlabelled source')
        release=source.get('release')
        row={'title': str(title),'source_url': url if parsed.scheme in ('http','https') else None,
            'observation_dates': [{'kind': k,'date': v} for k,v in observed],'product_period': period,
            'published_date': _date(source.get('publication_date')),
            'release': str(release) if isinstance(release,(str,int)) else None,
            'retrieved_date': _date(source.get('retrieved_at'))}
        identity=repr(row)
        if identity in seen:continue
        seen.add(identity);rows.append(row)
    return rows
