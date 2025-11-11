# Bionet-Bonanza

ArcGIS Python Toolbox for querying the NSW BioNet API to retrieve up-to-date fauna species lists with State and Commonwealth conservation classifications.

## Overview

This toolbox provides an ArcGIS Python tool that connects to the NSW Government BioNet Species Sightings API and retrieves fauna species records with their conservation status under:
- **BC Act**: NSW Biodiversity Conservation Act 2016 (State)
- **EPBC Act**: Environment Protection and Biodiversity Conservation Act 1999 (Commonwealth)

## Features

- Query fauna species from NSW BioNet API
- Filter by fauna group (Mammals, Birds, Reptiles, Amphibians, Fish, or All)
- Optional spatial filtering using Area of Interest polygon
- Returns distinct species list with conservation status
- Outputs results as ArcGIS table

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

1. **Area of Interest (Optional)**: Polygon feature layer to spatially filter results
2. **Fauna Group**: Select from:
   - All Fauna
   - Mammals
   - Birds
   - Reptiles
   - Amphibians
   - Fish
3. **Maximum Records**: Maximum number of records to retrieve (default: 1000)
4. **Output Table**: Location and name for the output table

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
- **SightingDate**: Date of the species sighting

### Example Workflow

1. Open ArcGIS Pro and add the toolbox
2. Open the "Query BioNet Fauna Species" tool
3. (Optional) Select a polygon feature layer as Area of Interest
4. Choose a fauna group (e.g., "Mammals")
5. Set maximum records (e.g., 1000)
6. Specify output table location
7. Run the tool
8. View results in the output table

## API Information

This toolbox queries the NSW BioNet Species Sightings REST API:
- **Endpoint**: https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/EDP/BionetSpeciesSightings/MapServer
- **Data Standard**: [BioNet Species Sighting Web Services Data Standard](https://www.environment.nsw.gov.au/sites/default/files/bionet-species-sighting-data-standard-200167.pdf)

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
- Verify the Area of Interest overlaps with NSW
- Try increasing the maximum records parameter
- Try selecting "All Fauna" instead of a specific group

### API timeout
- Reduce the maximum records parameter
- Use a smaller Area of Interest
- Try again later if the API is experiencing high traffic

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

- **1.0.0** (2025-11-11): Initial release
  - Query fauna species from NSW BioNet API
  - Filter by fauna group
  - Spatial filtering support
  - Conservation status (BC Act and EPBC Act)
