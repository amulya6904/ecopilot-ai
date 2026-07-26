# Weather setup

| Field | Value |
|---|---|
| Submission file | `phase4_weather.epw` |
| Repository source | `energyplus/weather/phase4_weather.epw` |
| Included | Yes |
| SHA-256 | `b24506e034c43d31950862232b97b404e573de4c8bee04204f62d0890bcae478` |
| EPW location | Bengaluru-Hindustan.AP, Karnataka, India |
| WMO station | `432960` |
| Coordinates | 12.95° N, 77.668° E |
| Time zone | UTC+05:30 |
| Elevation | 888 m |

Configure the existing project setting to point to the repository EPW:

```text
ENERGYPLUS_WEATHER=energyplus\weather\phase4_weather.epw
```

Both the baseline and controlled annual simulations must use this exact file.
The compatibility gate verifies the weather hash before any quantitative claim
is allowed. EnergyPlus reports that the EPW location overrides the retained
IDF `Location` object; this is an accepted, disclosed warning and not a severe
or fatal error.
