import {test,expect} from '@playwright/test';

test('loads a sourced 100-year NOAA storm with explicit wetness and uncertainty',async({page})=>{
 const depth=.08,duration=3600,rate=depth/duration;
 await page.route('**/api/v1/bundles/*/design-storms/noaa?*',route=>route.fulfill({json:{
  schema_version:'sponge.v1',name:'NOAA Atlas 14 100-year 60-minute point precipitation',
  duration_s:duration,recession_s:3600,depth_m:depth,
  intervals:[{start_s:0,end_s:duration,rate_m_s:rate}],return_period_years:100,
  source_ids:['noaa-atlas14-volume-2-version-3'],distribution:'SPONGE centered-block synthetic pattern',antecedent_saturation:.75,
  evidence:{provider:'NOAA National Weather Service Hydrometeorological Design Studies Center',product:'NOAA Atlas 14 point precipitation frequency estimate',
   source_url:'https://hdsc.nws.noaa.gov/example',product_page:'https://hdsc.nws.noaa.gov/pfds/',retrieved_at:'2026-09-19T00:00:00Z',source_sha256:'a'.repeat(64),
   location:{label:'Spring Garden',latitude:39.965,longitude:-75.164},region:'Ohio River Basin',volume:'2',version:'3',series:'annual maximum series',
   annual_exceedance_probability:.01,estimate_mm:80,confidence_interval:{level:.9,lower_mm:72,upper_mm:88},
   spatial_support:'Point estimate; not an areal rainfall field.',temporal_distribution_source:'SPONGE pattern; NOAA supplies the total depth.'}
 }}));
 await page.goto('/?intro=0');
 await expect(page.getByRole('heading',{name:'Spring Garden, Philadelphia'})).toBeVisible({timeout:60000});
 await page.getByRole('button',{name:'2D plan view'}).click();
 await expect(page.locator('.maplabel')).toContainText('TOP-DOWN 2D PLAN');
 await expect(page.getByRole('button',{name:'3D overview'})).toHaveAttribute('aria-pressed','true');
 await page.getByLabel('Antecedent soil condition').selectOption('0.75');
 await page.getByText('Load NOAA Atlas 14 design storm').click();
 await page.getByLabel('NOAA return period').selectOption('100');
 await page.getByRole('button',{name:'Load NOAA point estimate'}).click();
 await expect(page.getByText('80 mm point estimate',{exact:false})).toBeVisible();
 await expect(page.getByText('90% interval 72–88 mm',{exact:false})).toBeVisible();
 await expect(page.getByText('annual exceedance probability 1.00%',{exact:false})).toBeVisible();
 await expect(page.getByLabel('Antecedent soil condition')).toHaveValue('0.75');
 await expect(page.getByText('Sourced rainfall intervals: NOAA Atlas 14 100-year',{exact:false})).toBeVisible();
});
