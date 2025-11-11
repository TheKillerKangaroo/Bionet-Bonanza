# Bionet-Bonanza

ArcGIS Python Toolbox for querying the NSW BioNet API to retrieve up-to-date fauna species lists with State and Commonwealth conservation classifications.

## Overview

This toolbox provides an ArcGIS Python tool that connects to the NSW Government BioNet OData API and retrieves fauna species records with their conservation status under:
- **BC Act**: NSW Biodiversity Conservation Act 2016 (State)
- **EPBC Act**: Environment Protection and Biodiversity Conservation Act 1999 (Commonwealth)

## Features

- Query fauna species from NSW BioNet OData API
- Filter by fauna group (Mammals, Birds, Reptiles, Amphibians, Fish, or All)
- Optional authentication for accessing sensitive species data
- Returns distinct species list with conservation status
- Outputs results as ArcGIS table

## Documentation

- **[OData Service Reference](docs/ODATA_SERVICE_REFERENCE.md)** - Complete reference for all available entity sets
- **[Service Metadata](docs/ODATA_METADATA.json)** - JSON metadata for the OData service
- **[UML Diagram](docs/BIONET_ODATA_DIAGRAM.puml)** - PlantUML diagram of service structure
- **[Mermaid Diagram](docs/BIONET_ODATA_DIAGRAM.mmd)** - Mermaid diagram of service structure
- **[Implementation Notes](IMPLEMENTATION_NOTES.md)** - Technical implementation details

## Requirements

- ArcGIS Pro 2.x or later
- Python 3.x (included with ArcGIS Pro)
- Internet connection to access NSW BioNet API

## Installation

1. Download the `BionetFaunaQuery.pyt` file
2. In ArcGIS Pro, open the Catalog pane
3. Navigate to Toolboxes
4. Right-click and select "Add Toolbox"
5. Browse to and select `BionetFaunaQuery.pyt`

## Usage

### Tool Parameters

1. **BioNet Username (Optional)**: Your BioNet Atlas username for authenticated access to sensitive data
2. **BioNet Password (Optional)**: Your BioNet Atlas password
3. **Fauna Group**: Select from:
   - All Fauna
   - Mammals
   - Birds
   - Reptiles
   - Amphibians
   - Fish
4. **Maximum Records**: Maximum number of records to retrieve (default: 1000)
5. **Output Table**: Location and name for the output table

**Note on Authentication**: Anonymous access is supported but may have restrictions on sensitive species data. For full access to threatened species records with precise locations, provide your BioNet Atlas credentials.

### Output Fields

The output table includes the following fields:

- **ScientificName**: Scientific name of the species
- **CommonName**: Common name of the species
- **Class**: Taxonomic class (e.g., Mammalia, Aves)
- **Order**: Taxonomic order
- **Family**: Taxonomic family
- **Kingdom**: Taxonomic kingdom
- **BCActStatus**: Conservation status under NSW BC Act (e.g., Endangered, Vulnerable)
- **EPBCActStatus**: Conservation status under Commonwealth EPBC Act
- **SensitiveClass**: Sensitivity classification for the species
- **EventDate**: Date of the species sighting event

### Example Workflow

1. Open ArcGIS Pro and add the toolbox
2. Open the "Query BioNet Fauna Species" tool
3. (Optional) Enter your BioNet username and password for authenticated access
4. Choose a fauna group (e.g., "Mammals")
5. Set maximum records (e.g., 1000)
6. Specify output table location
7. Run the tool
8. View results in the output table

## API Information

This toolbox queries the NSW BioNet OData API:
- **Endpoint**: https://data.bionet.nsw.gov.au/biosvcapp/odata
- **Entity Set**: SpeciesSightings_CoreData
- **Protocol**: OData v4.0
- **Data Standard**: [BioNet Species Sighting Data Standard](https://www.environment.nsw.gov.au/sites/default/files/2025-06/bionet-species-sighting-data-standard-250124.pdf)
- **Developer Guide**: [BioNet Web Service Developer Guidelines](https://www.environment.nsw.gov.au/sites/default/files/2025-02/bionet-developer-guidelines-250050_2.pdf)

## Conservation Status Categories

### BC Act (NSW Biodiversity Conservation Act 2016)
- Critically Endangered (CE)
- Endangered (E)
- Vulnerable (V)
- Extinct (EX)

### EPBC Act (Environment Protection and Biodiversity Conservation Act 1999)
- Critically Endangered (CE)
- Endangered (E)
- Vulnerable (V)
- Extinct (EX)
- Extinct in the Wild (EW)
- Conservation Dependent (CD)

## Troubleshooting

### No records returned
- Check your internet connection
- Try providing BioNet credentials for authenticated access
- Try increasing the maximum records parameter
- Try selecting "All Fauna" instead of a specific group

### Authentication errors
- Verify your BioNet Atlas username and password are correct
- Create a BioNet account at https://www.bionet.nsw.gov.au if you don't have one
- Try running without credentials for anonymous access (limited data)

### API timeout
- Reduce the maximum records parameter
- Try again later if the API is experiencing high traffic
- Check your network firewall settings

### Table creation errors
- Ensure you have write permissions to the output location
- Check that the output path is valid
- Verify your geodatabase is not locked by another process

## License

This toolbox is provided as-is for educational and research purposes.

## Data Attribution

Species data is provided by NSW BioNet, a service of the NSW Department of Climate Change, Energy, the Environment and Water.

## Support

For issues with:
- **This toolbox**: Open an issue on GitHub
- **BioNet API**: Contact NSW DCCEEW via their [BioNet website](https://www.environment.nsw.gov.au/topics/animals-and-plants/biodiversity/nsw-bionet)

## Version History

- **1.1.0** (2025-11-11): Updated to use OData API
  - Changed from REST API to OData endpoint
  - Added authentication support for sensitive data
  - Updated field names to match OData schema
  - Improved error handling
  
- **1.0.0** (2025-11-11): Initial release
  - Query fauna species from NSW BioNet API
  - Filter by fauna group
  - Conservation status (BC Act and EPBC Act)
