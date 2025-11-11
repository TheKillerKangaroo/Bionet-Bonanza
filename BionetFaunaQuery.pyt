# -*- coding: utf-8 -*-
"""
NSW BioNet Fauna Query Toolbox

This ArcGIS Python Toolbox queries the NSW BioNet API to retrieve an up-to-date
fauna species list with their State (BC Act) and Commonwealth (EPBC Act) 
conservation classifications.

API Endpoint: https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/EDP/BionetSpeciesSightings/MapServer/0/query
"""

import arcpy
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "NSW BioNet Fauna Query"
        self.alias = "bionetfauna"
        self.description = "Query NSW BioNet API for fauna species with conservation status"
        
        # List of tool classes associated with this toolbox
        self.tools = [BionetFaunaQueryTool]


class BionetFaunaQueryTool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Query BioNet Fauna Species"
        self.description = ("Queries the NSW BioNet API to retrieve fauna species "
                           "sightings with State (BC Act) and Commonwealth (EPBC Act) "
                           "conservation status classifications.")
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        # Parameter 0: Area of Interest (optional polygon feature class)
        param0 = arcpy.Parameter(
            displayName="Area of Interest (Optional)",
            name="area_of_interest",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param0.filter.list = ["Polygon"]
        
        # Parameter 1: Fauna Group filter
        param1 = arcpy.Parameter(
            displayName="Fauna Group",
            name="fauna_group",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["All Fauna", "Mammals", "Birds", "Reptiles", "Amphibians", "Fish"]
        param1.value = "All Fauna"
        
        # Parameter 2: Maximum number of records
        param2 = arcpy.Parameter(
            displayName="Maximum Records",
            name="max_records",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param2.value = 1000
        
        # Parameter 3: Output Table
        param3 = arcpy.Parameter(
            displayName="Output Table",
            name="output_table",
            datatype="DETable",
            parameterType="Required",
            direction="Output")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed. This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        # Get parameters
        area_of_interest = parameters[0].valueAsText
        fauna_group = parameters[1].valueAsText
        max_records = parameters[2].value
        output_table = parameters[3].valueAsText
        
        arcpy.AddMessage("Starting NSW BioNet fauna species query...")
        arcpy.AddMessage(f"Fauna Group: {fauna_group}")
        arcpy.AddMessage(f"Maximum Records: {max_records}")
        
        try:
            # Build the query
            where_clause = self._build_where_clause(fauna_group)
            arcpy.AddMessage(f"Query filter: {where_clause}")
            
            # Get geometry filter if area of interest is provided
            geometry_filter = None
            if area_of_interest:
                geometry_filter = self._get_geometry_from_feature(area_of_interest)
                arcpy.AddMessage("Using spatial filter from Area of Interest")
            
            # Query the BioNet API
            species_data = self._query_bionet_api(where_clause, geometry_filter, max_records, messages)
            
            if not species_data:
                arcpy.AddWarning("No species records found matching the criteria")
                return
            
            arcpy.AddMessage(f"Retrieved {len(species_data)} species records")
            
            # Create output table
            self._create_output_table(species_data, output_table, messages)
            
            arcpy.AddMessage("Query completed successfully!")
            arcpy.AddMessage(f"Output table created: {output_table}")
            
        except Exception as e:
            arcpy.AddError(f"Error executing tool: {str(e)}")
            raise

    def _build_where_clause(self, fauna_group):
        """Build the WHERE clause based on fauna group selection"""
        
        fauna_class_map = {
            "Mammals": "Class = 'Mammalia'",
            "Birds": "Class = 'Aves'",
            "Reptiles": "Class = 'Reptilia'",
            "Amphibians": "Class = 'Amphibia'",
            "Fish": "Class IN ('Actinopterygii', 'Chondrichthyes', 'Myxini', 'Petromyzontida')"
        }
        
        if fauna_group == "All Fauna":
            # Query all fauna classes
            return ("Class IN ('Mammalia', 'Aves', 'Reptilia', 'Amphibia', "
                   "'Actinopterygii', 'Chondrichthyes', 'Myxini', 'Petromyzontida')")
        else:
            return fauna_class_map.get(fauna_group, "1=1")

    def _get_geometry_from_feature(self, feature_layer):
        """Extract geometry from feature layer for spatial query"""
        try:
            # Get the extent of the input feature
            desc = arcpy.Describe(feature_layer)
            extent = desc.extent
            
            # Return extent as JSON for API query
            geometry_json = {
                "xmin": extent.XMin,
                "ymin": extent.YMin,
                "xmax": extent.XMax,
                "ymax": extent.YMax,
                "spatialReference": {"wkid": extent.spatialReference.factoryCode}
            }
            return geometry_json
        except Exception as e:
            arcpy.AddWarning(f"Could not extract geometry: {str(e)}")
            return None

    def _query_bionet_api(self, where_clause, geometry_filter, max_records, messages):
        """Query the NSW BioNet API and return species data"""
        
        # BioNet Species Sightings API endpoint
        base_url = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/EDP/BionetSpeciesSightings/MapServer/0/query"
        
        # Build query parameters
        params = {
            "where": where_clause,
            "outFields": "ScientificName,CommonName,Class,Order,Family,Kingdom,BCActStatus,EPBCActStatus,SensitiveClass,SightingDate",
            "returnGeometry": "false",
            "returnDistinctValues": "true",
            "orderByFields": "ScientificName",
            "resultRecordCount": max_records,
            "f": "json"
        }
        
        # Add geometry filter if provided
        if geometry_filter:
            params["geometry"] = json.dumps(geometry_filter)
            params["geometryType"] = "esriGeometryEnvelope"
            params["spatialRel"] = "esriSpatialRelIntersects"
        
        try:
            # Encode parameters
            data = urllib.parse.urlencode(params).encode('utf-8')
            
            arcpy.AddMessage("Querying NSW BioNet API...")
            
            # Make the request
            req = urllib.request.Request(base_url, data=data)
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            # Check for errors in response
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                arcpy.AddError(f"API Error: {error_msg}")
                return []
            
            # Extract features
            if 'features' in result:
                return [feature['attributes'] for feature in result['features']]
            else:
                arcpy.AddWarning("No features returned from API")
                return []
                
        except urllib.error.URLError as e:
            arcpy.AddError(f"Network error querying BioNet API: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error parsing API response: {str(e)}")
            return []
        except Exception as e:
            arcpy.AddError(f"Unexpected error querying API: {str(e)}")
            return []

    def _create_output_table(self, species_data, output_table, messages):
        """Create output table with species data"""
        
        try:
            # Create the output table
            out_path = arcpy.env.workspace if arcpy.env.workspace else arcpy.env.scratchGDB
            table_name = arcpy.ValidateTableName(arcpy.Describe(output_table).baseName, out_path)
            
            # If output path is specified, use it
            if "/" in output_table or "\\" in output_table:
                import os
                out_path = os.path.dirname(output_table)
                table_name = os.path.basename(output_table)
            
            arcpy.AddMessage(f"Creating table: {table_name} in {out_path}")
            
            # Create table
            arcpy.management.CreateTable(out_path, table_name)
            full_table_path = f"{out_path}/{table_name}"
            
            # Add fields
            field_definitions = [
                ("ScientificName", "TEXT", 255),
                ("CommonName", "TEXT", 255),
                ("Class", "TEXT", 100),
                ("Order", "TEXT", 100),
                ("Family", "TEXT", 100),
                ("Kingdom", "TEXT", 100),
                ("BCActStatus", "TEXT", 100),
                ("EPBCActStatus", "TEXT", 100),
                ("SensitiveClass", "TEXT", 100),
                ("SightingDate", "DATE", None)
            ]
            
            for field_name, field_type, field_length in field_definitions:
                if field_length:
                    arcpy.management.AddField(full_table_path, field_name, field_type, 
                                            field_length=field_length)
                else:
                    arcpy.management.AddField(full_table_path, field_name, field_type)
            
            arcpy.AddMessage(f"Added {len(field_definitions)} fields to table")
            
            # Insert data
            fields = [f[0] for f in field_definitions]
            
            with arcpy.da.InsertCursor(full_table_path, fields) as cursor:
                for record in species_data:
                    row = []
                    for field in fields:
                        value = record.get(field)
                        
                        # Handle date conversion
                        if field == "SightingDate" and value:
                            try:
                                # BioNet dates are in milliseconds since epoch
                                value = datetime.fromtimestamp(value / 1000.0)
                            except:
                                value = None
                        
                        # Handle None/null values for text fields
                        if value is None and field != "SightingDate":
                            value = ""
                        
                        row.append(value)
                    
                    cursor.insertRow(row)
            
            arcpy.AddMessage(f"Inserted {len(species_data)} records into output table")
            
            # Set output parameter
            arcpy.SetParameter(3, full_table_path)
            
        except Exception as e:
            arcpy.AddError(f"Error creating output table: {str(e)}")
            raise
