# -*- coding: utf-8 -*-
"""
NSW BioNet Fauna Query Toolbox

This ArcGIS Python Toolbox queries the NSW BioNet OData API to retrieve an up-to-date
fauna species list with their State (BC Act) and Commonwealth (EPBC Act) 
conservation classifications.

API Endpoint: https://data.bionet.nsw.gov.au/biosvcapp/odata
"""

import arcpy
import json
import urllib.request
import urllib.parse
import urllib.error
import base64
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
        
        # Parameter 0: Username (optional, for authenticated access)
        param0 = arcpy.Parameter(
            displayName="BioNet Username (Optional)",
            name="username",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        # Parameter 1: Password (optional, for authenticated access)
        param1 = arcpy.Parameter(
            displayName="BioNet Password (Optional)",
            name="password",
            datatype="GPStringHidden",
            parameterType="Optional",
            direction="Input")
        
        # Parameter 2: Fauna Group filter
        param2 = arcpy.Parameter(
            displayName="Fauna Group",
            name="fauna_group",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["All Fauna", "Mammals", "Birds", "Reptiles", "Amphibians", "Fish"]
        param2.value = "All Fauna"
        
        # Parameter 3: Maximum number of records
        param3 = arcpy.Parameter(
            displayName="Maximum Records",
            name="max_records",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3.value = 1000
        
        # Parameter 4: Output Table
        param4 = arcpy.Parameter(
            displayName="Output Table",
            name="output_table",
            datatype="DETable",
            parameterType="Required",
            direction="Output")
        
        params = [param0, param1, param2, param3, param4]
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
        username = parameters[0].valueAsText
        password = parameters[1].valueAsText
        fauna_group = parameters[2].valueAsText
        max_records = parameters[3].value
        output_table = parameters[4].valueAsText
        
        arcpy.AddMessage("Starting NSW BioNet fauna species query...")
        arcpy.AddMessage(f"Fauna Group: {fauna_group}")
        arcpy.AddMessage(f"Maximum Records: {max_records}")
        
        try:
            # Build the OData filter
            odata_filter = self._build_odata_filter(fauna_group)
            arcpy.AddMessage(f"Query filter: {odata_filter}")
            
            # Query the BioNet OData API
            species_data = self._query_bionet_odata_api(
                odata_filter, 
                max_records, 
                username, 
                password, 
                messages
            )
            
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

    def _build_odata_filter(self, fauna_group):
        """Build the OData $filter clause based on fauna group selection"""
        
        fauna_class_map = {
            "Mammals": "Class eq 'Mammalia'",
            "Birds": "Class eq 'Aves'",
            "Reptiles": "Class eq 'Reptilia'",
            "Amphibians": "Class eq 'Amphibia'",
            "Fish": "(Class eq 'Actinopterygii' or Class eq 'Chondrichthyes' or Class eq 'Myxini' or Class eq 'Petromyzontida')"
        }
        
        if fauna_group == "All Fauna":
            # Query all fauna classes using OData syntax
            return ("(Class eq 'Mammalia' or Class eq 'Aves' or Class eq 'Reptilia' or "
                   "Class eq 'Amphibia' or Class eq 'Actinopterygii' or Class eq 'Chondrichthyes' or "
                   "Class eq 'Myxini' or Class eq 'Petromyzontida')")
        else:
            return fauna_class_map.get(fauna_group, "")

    def _query_bionet_odata_api(self, odata_filter, max_records, username, password, messages):
        """Query the NSW BioNet OData API and return species data"""
        
        # BioNet OData API endpoint for Species Sightings Core Data
        base_url = "https://data.bionet.nsw.gov.au/biosvcapp/odata/SpeciesSightings_CoreData"
        
        # Build OData query parameters
        # Select fields we need and apply filter
        query_params = {
            "$select": "ScientificName,CommonName,Class,Order,Family,Kingdom,BCActStatus,EPBCActStatus,SensitiveClass,EventDate",
            "$top": str(max_records)
        }
        
        # Add filter if provided
        if odata_filter:
            query_params["$filter"] = odata_filter
        
        # Build the full URL
        query_string = urllib.parse.urlencode(query_params)
        full_url = f"{base_url}?{query_string}"
        
        arcpy.AddMessage("Querying NSW BioNet OData API...")
        arcpy.AddMessage(f"URL: {base_url}")
        
        try:
            # Create the request
            req = urllib.request.Request(full_url)
            req.add_header('Accept', 'application/json')
            
            # Add authentication if provided
            if username and password:
                arcpy.AddMessage("Using authenticated access")
                credentials = f"{username}:{password}"
                encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                req.add_header('Authorization', f'Basic {encoded_credentials}')
            else:
                arcpy.AddMessage("Using anonymous access (some data may be restricted)")
            
            # Make the request
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            # OData returns data in 'value' array
            if 'value' in result:
                records = result['value']
                
                # Get distinct species (OData doesn't have built-in distinct)
                # Use a dictionary to track unique species by scientific name
                unique_species = {}
                for record in records:
                    sci_name = record.get('ScientificName', '')
                    if sci_name and sci_name not in unique_species:
                        unique_species[sci_name] = record
                
                # Sort by scientific name in Python (API doesn't allow $orderby on this field)
                sorted_species = sorted(unique_species.values(), 
                                      key=lambda x: x.get('ScientificName', '').lower())
                
                return sorted_species
            else:
                arcpy.AddWarning("No data returned from OData API")
                return []
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else "No error details"
            arcpy.AddError(f"HTTP Error {e.code} querying BioNet OData API: {e.reason}")
            arcpy.AddError(f"Details: {error_body}")
            if e.code == 401:
                arcpy.AddError("Authentication failed. Please provide valid BioNet credentials.")
            return []
        except urllib.error.URLError as e:
            arcpy.AddError(f"Network error querying BioNet OData API: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error parsing OData API response: {str(e)}")
            return []
        except Exception as e:
            arcpy.AddError(f"Unexpected error querying OData API: {str(e)}")
            import traceback
            arcpy.AddError(traceback.format_exc())
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
            
            # Add fields - EventDate instead of SightingDate for OData
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
                ("EventDate", "DATE", None)
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
                        
                        # Handle date conversion for OData format
                        if field == "EventDate" and value:
                            try:
                                # OData dates are in ISO 8601 format (e.g., "2023-01-15T00:00:00Z")
                                # Parse the date string
                                if isinstance(value, str):
                                    # Remove timezone info if present
                                    date_str = value.replace('Z', '').split('.')[0]
                                    value = datetime.fromisoformat(date_str)
                                else:
                                    value = None
                            except:
                                value = None
                        
                        # Handle None/null values for text fields
                        if value is None and field != "EventDate":
                            value = ""
                        
                        row.append(value)
                    
                    cursor.insertRow(row)
            
            arcpy.AddMessage(f"Inserted {len(species_data)} records into output table")
            
            # Set output parameter (parameter 4 now due to added username/password)
            arcpy.SetParameter(4, full_table_path)
            
        except Exception as e:
            arcpy.AddError(f"Error creating output table: {str(e)}")
            raise
