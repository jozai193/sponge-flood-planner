from services.geodata.source_dates import source_dates


def test_new_download_and_release_do_not_become_survey_dates():
    source={'provider': 'Footprints','release': '2026-08-19.0','retrieved_at': '2026-09-13T13:00:00Z'}
    rows=source_dates([source,source])
    assert len(rows)==1 and rows[0]['observation_dates']==[]
    assert rows[0]['release']=='2026-08-19.0' and rows[0]['retrieved_date']=='2026-09-13'


def test_worldcover_product_year_is_not_an_acquisition_date():
    row=source_dates([{'source_url': 'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N12E078_Map.tif'}])[0]
    assert row['product_period']=='2021' and row['observation_dates']==[]
    assert source_dates([{'source_url': 'https://example.com/terrain-2021.tif'}])[0]['product_period'] is None


def test_explicit_dates_are_kept_separate_and_invalid_dates_remain_unknown():
    row=source_dates([{'observed_at': '2016-03-01T08:30:00+05:30','publication_date': '2019-02-05','retrieved_at': '2026-99-99','source_url': 'javascript:alert(1)'}])[0]
    assert row['observation_dates']==[{'kind': 'Observed','date': '2016-03-01'}]
    assert row['published_date']=='2019-02-05'
    assert row['retrieved_date'] is None and row['source_url'] is None
