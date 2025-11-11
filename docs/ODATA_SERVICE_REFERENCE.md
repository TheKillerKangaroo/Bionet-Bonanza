# NSW BioNet OData Service Reference

## Overview

This document describes the NSW BioNet OData API service structure and available entity sets (tables).

**Base URL:** `https://data.bionet.nsw.gov.au/biosvcapp/odata`  
**Protocol:** OData v4.0  
**Authentication:** Optional Basic Auth for accessing sensitive species data

## Entity Sets

The BioNet OData service exposes the following entity sets, organized by domain:

### 🐾 Species Sightings

#### SpeciesSightings_CoreData ⭐
**Primary entity set used by BionetFaunaQuery.pyt**

Contains core species sighting observations with conservation status.

**Key Fields:**
- `ScientificName` - Scientific name of the species
- `CommonName` - Common name of the species
- `Class` - Taxonomic class (e.g., Mammalia, Aves)
- `Order` - Taxonomic order
- `Family` - Taxonomic family
- `Kingdom` - Taxonomic kingdom
- `BCActStatus` - NSW Biodiversity Conservation Act 2016 status
- `EPBCActStatus` - Commonwealth EPBC Act 1999 status
- `SensitiveClass` - Sensitivity classification
- `EventDate` - Date of the sighting event

**OData Query Support:**
- `$filter` - Filter by fauna group (Class), date, location, etc.
- `$select` - Select specific fields
- `$top` - Limit number of records
- `$orderby` - Sort results
- `$skip` - Skip records for pagination

**Example Query:**
```
GET /SpeciesSightings_CoreData?$filter=Class eq 'Mammalia'&$select=ScientificName,CommonName,BCActStatus&$top=100
```

#### SpeciesSightings_AdditionalMeasurementsOrFacts
Contains additional measurements and observations related to species sightings.

#### SpeciesSightings_DeletedRecords
Tracks deleted sighting records for data synchronization purposes.

---

### 📖 Species Names & Taxonomy

#### SpeciesNames
Provides species nomenclature, taxonomy, and taxonomic hierarchies.

#### Thesaurus
Contains controlled vocabulary terms and standardized terminology used across the system.

---

### 🚨 Threatened Biodiversity

#### ThreatenedBiodiversity_Species
Profiles of threatened species including conservation status, threats, and management actions.

#### ThreatenedBiodiversity_EcologicalCommunities
Threatened ecological communities profiles and status.

#### ThreatenedBiodiversity_Populations
Endangered populations within species.

#### ThreatenedBiodiversity_KeyThreateningProcesses
Key threatening processes identified under conservation legislation.

#### ThreatenedBiodiversity_TSGeographicData
Geographic distribution data for threatened species.

#### ThreatenedBiodiversity_TECGeographicData
Geographic distribution data for threatened ecological communities.

#### ThreatenedBiodiversity_TPGeographicData
Geographic distribution data for threatened populations.

---

### 🌿 Vegetation Classification

#### VegetationClassification_PCTDefinition
Plant Community Type (PCT) definitions and classifications.

#### VegetationClassification_PCTBenchmarks
Benchmark data for Plant Community Types.

#### VegetationClassification_PCTStratumData
Vegetation stratum data for PCTs (tree, shrub, ground layers).

#### VegetationClassification_PCTGrowthForm
Growth form characteristics for Plant Community Types.

---

### 🗺️ NSW Landscapes

#### NSWLandscapes_MitchellLandscapes
Mitchell Landscapes bioregions of New South Wales.

---

### 🔬 Systematic Flora Surveys

#### SystematicFloraSurvey_SiteData
Site-level data from systematic flora surveys.

#### SystematicFloraSurvey_PlotData
Plot-level data and species observations from flora surveys.

---

## Relationships

```
SpeciesSightings_CoreData
  ├─→ SpeciesNames (taxonomic reference)
  ├─→ ThreatenedBiodiversity_Species (conservation profiles)
  └─→ SpeciesSightings_AdditionalMeasurementsOrFacts (extended data)

ThreatenedBiodiversity_Species
  └─→ ThreatenedBiodiversity_TSGeographicData (spatial data)

ThreatenedBiodiversity_EcologicalCommunities
  └─→ ThreatenedBiodiversity_TECGeographicData (spatial data)

ThreatenedBiodiversity_Populations
  └─→ ThreatenedBiodiversity_TPGeographicData (spatial data)
```

## Conservation Status Values

### BC Act (NSW Biodiversity Conservation Act 2016)
- **CE** - Critically Endangered
- **E** - Endangered
- **V** - Vulnerable
- **EX** - Extinct

### EPBC Act (Environment Protection and Biodiversity Conservation Act 1999)
- **CE** - Critically Endangered
- **E** - Endangered
- **V** - Vulnerable
- **EX** - Extinct
- **EW** - Extinct in the Wild
- **CD** - Conservation Dependent

## Usage in BionetFaunaQuery.pyt

The ArcGIS Python Toolbox primarily uses the `SpeciesSightings_CoreData` entity set to retrieve fauna species with their conservation status.

**Query Pattern:**
```python
base_url = "https://data.bionet.nsw.gov.au/biosvcapp/odata/SpeciesSightings_CoreData"
params = {
    "$filter": "Class eq 'Mammalia'",
    "$select": "ScientificName,CommonName,Class,Order,Family,BCActStatus,EPBCActStatus",
    "$top": "1000",
    "$orderby": "ScientificName"
}
```

## Authentication

- **Anonymous Access:** Supported but may have restrictions on sensitive species data
- **Authenticated Access:** Provide BioNet Atlas username/password via HTTP Basic Auth
- **Sensitive Data:** Precise locations of threatened species require authentication

## Additional Resources

- [BioNet Developer Guidelines](https://www.environment.nsw.gov.au/sites/default/files/2025-02/bionet-developer-guidelines-250050_2.pdf)
- [Species Sightings Data Standard](https://www.environment.nsw.gov.au/sites/default/files/2025-06/bionet-species-sighting-data-standard-250124.pdf)
- [OData v4.0 Documentation](https://www.odata.org/documentation/)

## Metadata Access

Full service metadata is available at:
```
https://data.bionet.nsw.gov.au/biosvcapp/odata/$metadata
```

---

**Last Updated:** 2025-11-11  
**Service Version:** OData v4.0
