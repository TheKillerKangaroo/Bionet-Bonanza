# Implementation Notes

## Overview
This project implements an ArcGIS Python Toolbox (.pyt) that queries the NSW BioNet OData API to retrieve fauna species records with their State and Commonwealth conservation status classifications.

## Requirements Implemented

### Original Requirement
> "Can we create an ArcGIS Python toolbox that queries the NSW BioNet API and returns an up to date fauna species list with their state and commonwealth classifications"

### Updated Requirement
> "Can you change the api endpoint to https://data.bionet.nsw.gov.au/biosvcapp/odata"

## Solution Architecture

### Technology Stack
- **Python 3.x**: Core programming language (compatible with ArcGIS Pro)
- **ArcGIS Python Toolbox (.pyt)**: ArcGIS Pro integration
- **OData v4.0**: API protocol for data access
- **urllib**: HTTP requests (no external dependencies)
- **JSON**: Data format

### API Endpoint
- **Base URL**: `https://data.bionet.nsw.gov.au/biosvcapp/odata`
- **Entity Set**: `SpeciesSightings_CoreData`
- **Protocol**: OData v4.0 with standard query options ($filter, $select, $top)

### Key Features

1. **Fauna Group Filtering**
   - All Fauna
   - Mammals (Class = Mammalia)
   - Birds (Class = Aves)
   - Reptiles (Class = Reptilia)
   - Amphibians (Class = Amphibia)
   - Fish (multiple fish classes)

2. **Conservation Status Fields**
   - **BCActStatus**: NSW Biodiversity Conservation Act 2016 status
   - **EPBCActStatus**: Environment Protection and Biodiversity Conservation Act 1999 status

3. **Authentication Support**
   - Optional username/password for authenticated access
   - Anonymous access supported (with data restrictions)
   - Basic HTTP authentication

4. **Output**
   - ArcGIS Table format
   - Fields: ScientificName, CommonName, Class, Order, Family, Kingdom, BCActStatus, EPBCActStatus, SensitiveClass, EventDate
   - Distinct species records (duplicates removed)

## File Structure

```
Bionet-Bonanza/
├── BionetFaunaQuery.pyt        # Main ArcGIS Python Toolbox
├── example_usage.py            # Example scripts for programmatic usage
├── test_toolbox.py             # Test suite for validation
├── README.md                   # User documentation
├── IMPLEMENTATION_NOTES.md     # This file
└── .gitignore                  # Git ignore patterns
```

## Technical Implementation Details

### OData Query Construction

The toolbox constructs OData queries using standard query options:

```python
# Example query for mammals
GET /SpeciesSightings_CoreData?$filter=Class eq 'Mammalia'&$select=ScientificName,CommonName,BCActStatus,EPBCActStatus&$top=1000
# Note: Results are sorted client-side after fetching ($orderby not supported by API)
```

### Authentication Flow

1. User provides optional username/password
2. Credentials encoded with Base64
3. Added to HTTP Authorization header
4. If 401 error, user notified to check credentials
5. Anonymous access falls back if no credentials provided

### Data Processing

1. Query OData API with fauna group filter
2. Receive JSON response with 'value' array
3. Remove duplicate species by ScientificName
4. Parse date fields from ISO 8601 format
5. Create ArcGIS table with appropriate field types
6. Insert records using ArcGIS data access cursors

### Error Handling

- Network errors (URLError)
- HTTP errors (401, 403, 404, 500, etc.)
- JSON parsing errors
- Invalid credentials
- API timeouts
- Table creation errors

## Testing

### Test Coverage
1. ✅ Toolbox file structure validation
2. ⚠️ API availability (requires network access)
3. ⚠️ Fauna species queries (requires network access)
4. ⚠️ Multiple fauna groups (requires network access)
5. ⚠️ Conservation status fields (requires network access)

Note: Network-dependent tests cannot run in restricted environments but the toolbox structure is validated.

## Security

### CodeQL Analysis
- ✅ No security vulnerabilities detected
- ✅ No sensitive data exposure
- ✅ Proper credential handling (not logged or displayed)
- ✅ Secure HTTP requests using urllib

### Best Practices Followed
- Password field uses GPStringHidden datatype
- No credentials stored or cached
- HTTPS endpoint for secure transmission
- Input validation on parameters
- Error messages don't expose sensitive details

## Limitations and Known Issues

1. **OData Distinct Values**: OData doesn't have a built-in distinct clause like the REST API, so duplicate removal is done in Python after fetching results.

2. **Spatial Filtering**: The OData API doesn't support spatial geometry queries in the same way as the ArcGIS REST API. This feature was removed in the OData version.

3. **Authentication**: Some sensitive species data may require valid BioNet Atlas credentials. Anonymous access may have restrictions.

4. **Rate Limiting**: The API may have rate limits or throttling that aren't documented. Large queries should be broken into smaller batches.

5. **Date Format**: EventDate is returned in ISO 8601 format from OData, properly parsed to Python datetime objects.

## Future Enhancements

Potential improvements for future versions:

1. **Batch Processing**: Support for querying multiple regions or large datasets
2. **Spatial Filtering**: Investigate OData spatial query support or alternative approaches
3. **Caching**: Local caching of results to reduce API calls
4. **Export Formats**: Direct export to CSV, Excel, or Shapefile
5. **Progress Indicators**: Show progress for long-running queries
6. **Advanced Filters**: Additional filters for date ranges, threatened status only, etc.
7. **Metadata**: Include more detailed metadata in output
8. **Offline Mode**: Support for working with downloaded datasets

## References

### Documentation
- [NSW BioNet Web Services](https://www.environment.nsw.gov.au/topics/animals-and-plants/biodiversity/nsw-bionet/web-services)
- [BioNet Species Sightings Data Standard](https://www.environment.nsw.gov.au/sites/default/files/2025-06/bionet-species-sighting-data-standard-250124.pdf)
- [BioNet Developer Guidelines](https://www.environment.nsw.gov.au/sites/default/files/2025-02/bionet-developer-guidelines-250050_2.pdf)
- [OData v4.0 Protocol](https://www.odata.org/documentation/)
- [ArcGIS Python Toolbox Documentation](https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/a-quick-tour-of-python-toolboxes.htm)

### API Endpoints
- OData Base: `https://data.bionet.nsw.gov.au/biosvcapp/odata`
- Entity Set: `SpeciesSightings_CoreData`

## Changelog

### Version 1.1.0 (2025-11-11)
- Switched from ArcGIS REST API to OData API endpoint
- Added authentication support (username/password)
- Updated query syntax to OData v4.0
- Removed spatial filtering (not supported in OData)
- Updated field names (EventDate vs SightingDate)
- Improved error handling
- Enhanced documentation

### Version 1.0.0 (2025-11-11)
- Initial implementation with ArcGIS REST API
- Basic fauna group filtering
- Conservation status extraction
- Output to ArcGIS table

## Support

For issues or questions:
- **Toolbox Issues**: Open an issue on GitHub
- **API Issues**: Contact NSW DCCEEW BioNet team
- **ArcGIS Issues**: Consult Esri support resources

## License

This toolbox is provided as-is for educational and research purposes. Users are responsible for complying with NSW BioNet terms of use and data licensing requirements.
