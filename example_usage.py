"""
Example script demonstrating how to use the BioNet Fauna Query toolbox programmatically.

This script shows different ways to call the toolbox tool from Python code.
"""

import arcpy
import os

# Set the workspace
arcpy.env.workspace = arcpy.env.scratchGDB

# Path to the toolbox (adjust this to your actual path)
toolbox_path = r"C:\path\to\BionetFaunaQuery.pyt"

# Import the toolbox
arcpy.ImportToolbox(toolbox_path)

# Example 1: Query all fauna without spatial filter
print("Example 1: Query all fauna species (up to 500 records)")
output_table1 = os.path.join(arcpy.env.scratchGDB, "all_fauna")
arcpy.bionetfauna.QueryBioNetFaunaSpecies(
    area_of_interest=None,
    fauna_group="All Fauna",
    max_records=500,
    output_table=output_table1
)
print(f"Results saved to: {output_table1}")

# Example 2: Query only mammals
print("\nExample 2: Query only mammals (up to 1000 records)")
output_table2 = os.path.join(arcpy.env.scratchGDB, "mammals_only")
arcpy.bionetfauna.QueryBioNetFaunaSpecies(
    area_of_interest=None,
    fauna_group="Mammals",
    max_records=1000,
    output_table=output_table2
)
print(f"Results saved to: {output_table2}")

# Example 3: Query birds with spatial filter
print("\nExample 3: Query birds within an area of interest")
# Assuming you have a feature layer called "study_area"
study_area = "study_area"  # Replace with your actual feature layer name
output_table3 = os.path.join(arcpy.env.scratchGDB, "birds_in_study_area")

try:
    arcpy.bionetfauna.QueryBioNetFaunaSpecies(
        area_of_interest=study_area,
        fauna_group="Birds",
        max_records=1000,
        output_table=output_table3
    )
    print(f"Results saved to: {output_table3}")
except:
    print("Note: Spatial filter example requires a 'study_area' polygon feature layer")

# Example 4: Filter results to show only threatened species
print("\nExample 4: Post-process to show only threatened species")
output_table4 = os.path.join(arcpy.env.scratchGDB, "reptiles_all")
arcpy.bionetfauna.QueryBioNetFaunaSpecies(
    area_of_interest=None,
    fauna_group="Reptiles",
    max_records=1000,
    output_table=output_table4
)

# Create a table view with only threatened species
threatened_view = "threatened_reptiles_view"
where_clause = "BCActStatus IS NOT NULL AND BCActStatus <> '' OR EPBCActStatus IS NOT NULL AND EPBCActStatus <> ''"
arcpy.MakeTableView_management(output_table4, threatened_view, where_clause)

# Get count
result = arcpy.GetCount_management(threatened_view)
count = int(result.getOutput(0))
print(f"Found {count} threatened reptile species")

# Example 5: Export results to CSV
print("\nExample 5: Export results to CSV")
output_table5 = os.path.join(arcpy.env.scratchGDB, "amphibians")
arcpy.bionetfauna.QueryBioNetFaunaSpecies(
    area_of_interest=None,
    fauna_group="Amphibians",
    max_records=500,
    output_table=output_table5
)

# Export to CSV
csv_path = os.path.join(os.path.expanduser("~"), "Documents", "amphibians_bionet.csv")
arcpy.conversion.TableToTable(output_table5, os.path.dirname(csv_path), os.path.basename(csv_path))
print(f"Exported to CSV: {csv_path}")

print("\nAll examples completed!")
