# API-Dependent Geocoding Methods

⚠️ **WARNING: These scripts require external API access and are NOT recommended for production use.**

## Scripts in this folder:

### `ADI_Distance.py`
- **Method**: Google Maps Geocoding API
- **Requirements**: Google Maps API key
- **Issues**: Requires internet, API costs, rate limits, privacy concerns
- **Status**: Legacy - use `../geocoding_zipcentroid.py` instead

### `ADI_Distance_noAPI.py` 
- **Method**: Google Maps Geocoding API (alternative version)
- **Requirements**: Google Maps API key
- **Issues**: Same as above
- **Status**: Legacy - use `../geocoding_zipcentroid.py` instead

### `geocoding_comparison_api.py`
- **Method**: Nominatim (OpenStreetMap) API comparison
- **Requirements**: Internet connection
- **Purpose**: Compare API geocoding vs local methods
- **Issues**: External dependency, privacy concerns
- **Status**: Research tool only

## Recommended Alternatives:

Instead of using these API-dependent scripts, use the comprehensive offline methods:

- **For most research**: `../geocoding_zipcentroid.py` (covers all US ZIP codes)
- **For highest accuracy**: `../geocoding_addrfeat.py` (385 counties with street-level precision)
- **For accuracy testing**: `../geocoding_accuracy_test.py`

**With 385 ADDRFEAT files now available, there is no compelling reason to use API methods for Arkansas + surrounding states research.**

## Why avoid API methods?

1. **Privacy**: Your address data is sent to external servers
2. **Cost**: APIs often charge per request
3. **Reliability**: Dependent on internet and service availability
4. **Rate Limits**: May be slow for large datasets
5. **Reproducibility**: Results may change over time

The offline methods provide better privacy, reliability, and performance for research use. With 385 ADDRFEAT files providing comprehensive coverage, the offline system now offers superior capabilities compared to API methods.