"""
Example script demonstrating how to use the BioNet Fauna Query toolbox programmatically.

This script shows different ways to call the toolbox tool from Python code.
Note: The toolbox now uses the NSW BioNet OData API.
"""

import arcpy
import os

# Set the workspace
arcpy.env.workspace = arcpy.env.scratchGDB

# Path to the toolbox (adjust this to your actual path)
toolbox_path = r"C:\path\to\BionetFaunaQuery.pyt"

# Import the toolbox
arcpy.ImportToolbox(toolbox_path)

# BioNet credentials (optional - leave as None for anonymous access)
bionet_username = None  # Replace with your BioNet username if needed
bionet_password = None  # Replace with your BioNet password if needed

# Example 1: Query all fauna anonymously (up to 500 records)
print("Example 1: Query all fauna species anonymously (up to 500 records)")
output_table1 = os.path.join(arcpy.env.scratchGDB, "all_fauna")
arcpy.bionetfauna.QueryBioNetFaunaSpecies(
    username=bionet_username,
    password=bionet_password,
    fauna_group="All Fauna",
    max_records=500,
    output_table=output_table1
)
print(f"Results saved to: {output_table1}")

# Example 2: Query only mammals with authentication
print("\nExample 2: Query only mammals with authentication (up to 1000 records)")
output_table2 = os.path.join(arcpy.env.scratchGDB, "mammals_only")
arcpy.bionetfauna.QueryBioNetFaunaSpecies(
    username="your_username",  # Replace with actual username
    password="your_password",  # Replace with actual password
    fauna_group="Mammals",
    max_records=1000,
    output_table=output_table2
)
print(f"Results saved to: {output_table2}")
print("Note: Replace 'your_username' and 'your_password' with actual credentials")

# Example 3: Filter results to show only threatened species
print("\nExample 3: Post-process to show only threatened species")
output_table3 = os.path.join(arcpy.env.scratchGDB, "reptiles_all")
arcpy.bionetfauna.QueryBioNetFaunaSpecies(
    username=bionet_username,
    password=bionet_password,
    fauna_group="Reptiles",
    max_records=1000,
    output_table=output_table3
)

# Create a table view with only threatened species
threatened_view = "threatened_reptiles_view"
where_clause = "BCActStatus IS NOT NULL AND BCActStatus <> '' OR EPBCActStatus IS NOT NULL AND EPBCActStatus <> ''"
arcpy.MakeTableView_management(output_table3, threatened_view, where_clause)

# Get count
result = arcpy.GetCount_management(threatened_view)
count = int(result.getOutput(0))
print(f"Found {count} threatened reptile species")

# Example 4: Export results to CSV
print("\nExample 4: Export results to CSV")
output_table4 = os.path.join(arcpy.env.scratchGDB, "amphibians")
arcpy.bionetfauna.QueryBioNetFaunaSpecies(
    username=bionet_username,
    password=bionet_password,
    fauna_group="Amphibians",
    max_records=500,
    output_table=output_table4
)

# Export to CSV
csv_path = os.path.join(os.path.expanduser("~"), "Documents", "amphibians_bionet.csv")
arcpy.conversion.TableToTable(output_table4, os.path.dirname(csv_path), os.path.basename(csv_path))
print(f"Exported to CSV: {csv_path}")

print("\nAll examples completed!")
print("\nNote: This toolbox now uses the NSW BioNet OData API.")
print("For access to sensitive species data, provide valid BioNet credentials.")
