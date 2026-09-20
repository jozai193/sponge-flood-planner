# Design storms and antecedent wetness

SPONGE supports user-defined uniform rainfall, validated imported interval series, and NOAA Atlas 14 point precipitation-frequency totals for prepared US locations. The Atlas 14 path is available under **Storm → Load NOAA Atlas 14 design storm**.

The application requests the official NOAA PFDS annual-maximum-series metric-depth product for the prepared bundle coordinate. It records the exact source URL, retrieval time, response hash, Atlas volume/version, estimate, 90% confidence interval, annual exceedance probability, and coordinate. Responses are bounded to 1 MB, parsed as data without executing the returned JavaScript assignments, integrity-cached for 30 days, and rejected if their structure or confidence bounds are inconsistent.

Supported interactive durations are 10 minutes, 1 hour, and 6 hours; supported recurrence intervals are 2, 5, 10, 25, 50, 100, 200, and 500 years. The 100-year option is an annual-maximum-series point estimate with nominal annual exceedance probability `1 / 100 = 1%`; it is not a guarantee that an event occurs only once per century.

NOAA supplies a total point depth. It does not supply the time pattern selected in SPONGE. Uniform, centered-peak, front-loaded, and rear-loaded patterns are explicit SPONGE modelling assumptions. Each is represented by 12 non-overlapping constant-rate intervals whose integrated rainfall equals the published depth within the rainfall contract tolerance. The UI and exported report keep this distinction visible.

Antecedent saturation is part of the executable input identity and can be set to dry (10%), typical assumption (25%), wet (75%), or saturated (100%). Changing it invalidates an existing comparison. Baseline and planned runs use the same value.

Limits:

- Atlas 14 values are point estimates, not an areal rainfall field over the neighbourhood.
- The temporal patterns are sensitivity cases, not calibrated local hyetographs.
- Atlas 14 is a historical stationary-frequency product. It does not by itself represent future non-stationary climate.
- PFDS coverage is geographic. An unavailable or unsupported location returns an actionable error; SPONGE does not invent a nearby value.
- A design storm does not establish observed-event flood accuracy. Surveyed terrain, drainage, soil, boundary, and observed flood evidence remain necessary for engineering use.

Primary references: [NOAA Precipitation Frequency Data Server](https://hdsc.nws.noaa.gov/pfds/) and [HDSC frequently asked questions](https://www.weather.gov/owp/hdsc_faqs).
