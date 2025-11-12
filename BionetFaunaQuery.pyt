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
from time import sleep
import re


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
        username = parameters[0].valueAsText
        password = parameters[1].valueAsText
        fauna_group = parameters[2].valueAsText
        output_table = parameters[3].valueAsText
        
        arcpy.AddMessage("Starting NSW BioNet fauna species query...")
        arcpy.AddMessage(f"Fauna Group: {fauna_group}")
        
        try:
            # Build the OData filter
            odata_filter = self._build_odata_filter(fauna_group)
            arcpy.AddMessage(f"Query filter: {odata_filter}")
            
            # Query the BioNet OData API (page through all results, follow nextLink if present,
            # deduplicate by ScientificName and stop once we've collected all unique species)
            species_data, server_count = self._query_bionet_odata_api(
                odata_filter, 
                username, 
                password, 
                messages
            )
            
            if not species_data:
                arcpy.AddWarning("No species records found matching the criteria")
                return
            
            arcpy.AddMessage(f"Retrieved {len(species_data)} unique species records (after deduplication)")
            if server_count is not None:
                arcpy.AddMessage(f"Server reported total raw rows matching filter: {server_count}")
                try:
                    server_count_int = int(server_count)
                    # server_count represents raw rows; unique species may be fewer due to duplicates
                    if server_count_int > 0 and server_count_int != len(species_data):
                        arcpy.AddMessage("Note: server count is for raw rows; unique species count may differ due to deduplication.")
                except Exception:
                    pass
            
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

    def _build_query_url(self, base_url, params):
        """Helper to construct OData query URL from a params dict and properly encode it.

        Params should be a dict with keys like '$select', '$filter', '$top', '$skip', '$count', '$apply', etc.
        This uses urllib.parse.urlencode with quote_via=urllib.parse.quote so spaces are encoded as %20.
        """
        # Remove None values
        safe_params = {k: v for k, v in params.items() if v is not None and v != ""}
        # urlencode with urllib.parse.quote to get %20 for spaces
        query = urllib.parse.urlencode(safe_params, safe="()'", quote_via=urllib.parse.quote)
        return base_url + "?" + query

    def _http_get_json(self, url, username=None, password=None, timeout=120):
        """Simple HTTP GET that returns parsed JSON"""
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json')
        if username and password:
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            req.add_header('Authorization', f'Basic {encoded_credentials}')
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))

    def _extract_missing_property_from_error(self, error_body):
        """Try to extract property name that the server reports as missing.

        The BioNet OData errors typically include a message like:
        "Could not find a property named 'CommonName' on type '...'"
        We try several ways to extract the property name.
        """
        try:
            # If JSON, try to dig into innererror.message
            jb = json.loads(error_body)
            # Try common paths
            for key in ("error",):
                if key in jb:
                    err = jb[key]
                    # nested message may be in .get('message') or innererror.message
                    msg = None
                    if isinstance(err, dict):
                        msg = err.get("message")
                        inner = err.get("innererror")
                        if inner and isinstance(inner, dict):
                            msg = msg or inner.get("message")
                    if msg:
                        # fall through to regex extraction
                        error_body = msg
                        break
        except Exception:
            # not JSON or unexpected structure; leave error_body as-is
            pass

        # regex to find the property name in quotes
        m = re.search(r"Could not find a property named '([^']+)"", error_body)
        if m:
            return m.group(1)
        # fallback: look for "property named \"X\"" or similar
        m = re.search(r'property named "?([^"'\s]+)"?', error_body)
        if m:
            return m.group(1)
        return None

    def _attempt_unique_species_count(self, base_url, odata_filter, username, password):
        """Try to determine the total number of unique ScientificName values server-side.

        Strategy:
        1) Attempt an OData $apply groupby(ScientificName) with $count=true and $top=0.
           If the server supports $apply and returns @odata.count, that should be the
           number of unique ScientificName groups.
        2) If that fails, return None so that the caller falls back to a heuristic.
        """
        try:
            params = {
                "$apply": "groupby((ScientificName))",
                "$count": "true",
                "$top": "0"
            }
            apply_url = self._build_query_url(base_url, params)
            arcpy.AddMessage(f"Attempting to get unique species count via $apply: {apply_url}")
            result = self._http_get_json(apply_url, username, password)
            unique_count = result.get("@odata.count") or result.get("odata.count") or result.get("count")
            if unique_count is not None:
                arcpy.AddMessage(f"Server reports unique ScientificName groups: {unique_count}")
                return int(unique_count)
        except Exception as e:
            arcpy.AddMessage(f"$apply/groupby method for unique count not supported or failed: {e}")
        return None

    def _query_bionet_odata_api(self, odata_filter, username, password, messages):
        """Query the NSW BioNet OData API with paging and deduplication.

        This version will stop once we've collected every unique ScientificName:
        - first, try to ask the server for the distinct ScientificName count using $apply/groupby;
        - if that succeeds, stop when unique_species size == that count;
        - otherwise, follow pages until the server provides no more pages or until we observe
        several consecutive pages that add zero new unique species (heuristic safety).
        It also handles unknown $select properties returned as 400 Bad Request by
        removing offending properties from the select list and retrying.
        Returns a tuple (sorted_unique_species_list, server_count_or_None)
        """
        
        # BioNet OData API endpoint for Species Sightings Core Data
        base_url = "https://data.bionet.nsw.gov.au/biosvcapp/odata/SpeciesSightings_CoreData"
        
        # Start with a broad list of fields we would like. If the server responds
        # that a property doesn't exist we'll remove it and retry automatically.
        select_fields_list = [
            "ScientificName",
            "CommonName",
            "Class",
            "Order",
            "Family",
            "Kingdom",
            "BCActStatus",
            "EPBCActStatus",
            "SensitiveClass",
            "EventDate"
        ]

        def build_select_string():
            return ",".join(select_fields_list)

        # Try to get the server raw-row count (as before). If server complains about unknown select
        # properties, remove them and retry the count request a few times.
        server_count = None
        for attempt in range(5):
            try:
                params = {
                    "$select": build_select_string(),
                    "$top": "0",
                    "$filter": odata_filter,
                    "$count": "true"
                }
                count_url = self._build_query_url(base_url, params)
                arcpy.AddMessage(f"Requesting server raw-row count with: {count_url}")
                count_result = self._http_get_json(count_url, username, password)
                server_count = count_result.get("@odata.count") or count_result.get("odata.count") or count_result.get("count")
                if server_count is not None:
                    arcpy.AddMessage(f"Server raw-row count: {server_count}")
                break
            except urllib.error.HTTPError as e:
                try:
                    error_body = e.read().decode("utf-8") if e.fp else ""
                except Exception:
                    error_body = str(e)
                missing = self._extract_missing_property_from_error(error_body)
                if missing and missing in select_fields_list:
                    arcpy.AddWarning(f"Server reports unknown property '{missing}' in $select; removing and retrying count.")
                    select_fields_list.remove(missing)
                    continue
                # if it's a different 400 reason or we couldn't parse the property, warn and stop trying count
                arcpy.AddWarning(f"Could not retrieve server raw-row count: {e} ({error_body}) — continuing with paging.")
                break
            except Exception as e:
                arcpy.AddWarning(f"Could not retrieve server raw-row count: {str(e)} — continuing with paging.")
                break

        # Attempt to determine number of unique ScientificName groups server-side
        unique_target = self._attempt_unique_species_count(base_url, odata_filter, username, password)
        if unique_target is not None:
            arcpy.AddMessage(f"Will stop when collected unique species == {unique_target}")
        else:
            arcpy.AddMessage("Could not determine unique species count server-side; will use heuristic stopping when no new species are found across multiple pages.")
        
        # Page through results until stopping condition
        unique_species = {}
        total_raw_rows = 0
        page_size = 1000  # sensible default; adjust if the API enforces different limits
        skip = 0
        next_link = None
        page_iteration = 0
        max_iterations = 10000  # safety to avoid infinite loops in case of unexpected server behaviour

        # Heuristic: stop if X consecutive pages add zero new unique species (fallback)
        NO_NEW_PAGE_LIMIT = 5
        consecutive_no_new = 0

        arcpy.AddMessage("Beginning paged retrieval from BioNet OData API (stopping once all unique species collected)...")
        while True:
            if page_iteration >= max_iterations:
                arcpy.AddWarning("Reached maximum page iteration safety limit; stopping further paging.")
                break
            page_iteration += 1

            try:
                top = str(page_size)
                if next_link:
                    url = next_link
                    arcpy.AddMessage(f"Following @odata.nextLink: {url}")
                else:
                    params = {
                        "$select": build_select_string(),
                        "$top": top,
                        "$skip": str(skip),
                        "$filter": odata_filter
                    }
                    url = self._build_query_url(base_url, params)
                    arcpy.AddMessage(f"Fetching page: skip={skip} top={page_size}")
                
                # Try the request; on HTTP 400 due to unknown $select property remove offending property and retry
                try:
                    data = self._http_get_json(url, username, password)
                except urllib.error.HTTPError as e:
                    # Read body safely
                    try:
                        error_body = e.read().decode("utf-8") if e.fp else ""
                    except Exception:
                        error_body = str(e)
                    if e.code == 400:
                        missing = self._extract_missing_property_from_error(error_body)
                        if missing and missing in select_fields_list:
                            arcpy.AddWarning(f"Server reports unknown property '{missing}' in $select; removing and retrying page request.")
                            select_fields_list.remove(missing)
                            # retry this iteration without incrementing skip/next_link
                            continue
                    # If not an unknown-property case, re-raise to be handled by outer except
                    raise

                # Prefer 'value' payload for OData; also accept direct arrays
                if isinstance(data, dict) and "value" in data:
                    page = data["value"]
                elif isinstance(data, list):
                    page = data
                else:
                    arcpy.AddWarning("Unexpected API response format; stopping pagination.")
                    break
                
                # Process page rows
                new_in_page = 0
                for record in page:
                    sci_name = (record.get('ScientificName') or "").strip()
                    if sci_name:
                        if sci_name not in unique_species:
                            unique_species[sci_name] = record
                            new_in_page += 1
                    total_raw_rows += 1
                
                arcpy.AddMessage(f"Fetched rows this page: {len(page)}  — total raw rows fetched: {total_raw_rows}  — new unique species this page: {new_in_page}")
                
                # If we discovered no new unique names this page, increment consecutive counter
                if new_in_page == 0:
                    consecutive_no_new += 1
                else:
                    consecutive_no_new = 0

                # If we have a server-side unique target, stop when satisfied
                if unique_target is not None and len(unique_species) >= unique_target:
                    arcpy.AddMessage("Collected all unique species as reported by server-side group count; stopping.")
                    break

                # If heuristic says we've seen many pages with no new species, assume we've collected all unique species
                if unique_target is None and consecutive_no_new >= NO_NEW_PAGE_LIMIT:
                    arcpy.AddMessage(f"No new unique species seen for {NO_NEW_PAGE_LIMIT} consecutive pages; assuming we've collected all unique species and stopping.")
                    break
                
                # Determine next link if present and follow it
                next_link = None
                if isinstance(data, dict):
                    next_link = data.get("@odata.nextLink") or data.get("odata.nextLink") or data.get("nextLink")
                
                if next_link:
                    # Follow the server-provided nextLink
                    sleep(0.2)
                    continue

                # If no nextLink and fewer records than 'top' were returned, this was the last page
                if len(page) < page_size:
                    arcpy.AddMessage("Last page received (fewer rows than requested).")
                    break

                # Otherwise increment skip for the next iteration and continue paging
                skip += page_size
                sleep(0.2)
                
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8') if e.fp else "No error details"
                arcpy.AddError(f"HTTP Error {e.code} querying BioNet OData API: {e.reason}")
                arcpy.AddError(f"Details: {error_body}")
                if e.code == 401:
                    arcpy.AddError("Authentication failed. Please provide valid BioNet credentials.")
                break
            except urllib.error.URLError as e:
                arcpy.AddError(f"Network error querying BioNet OData API: {str(e)}")
                break
            except json.JSONDecodeError as e:
                arcpy.AddError(f"Error parsing OData API response: {str(e)}")
                break
            except Exception as e:
                arcpy.AddError(f"Unexpected error querying OData API: {str(e)}")
                import traceback
                arcpy.AddError(traceback.format_exc())
                break
        
        # After fetching pages, build sorted list of unique species records
        sorted_species = sorted(unique_species.values(), key=lambda x: x.get('ScientificName', '').lower())
        
        # Log summary
        arcpy.AddMessage(f"Unique species after deduplication: {len(sorted_species)}")
        if server_count is not None:
            try:
                server_count_int = int(server_count)
                if server_count_int != total_raw_rows:
                    arcpy.AddMessage("Note: server raw-row count differs from the number of raw rows fetched. This could be due to authentication/restrictions or server-side changes during paging.")
            except Exception:
                pass
        
        return sorted_species, server_count

    def _create_output_table(self, species_data, output_table, messages):
        """Create output table with species data"""
        
        try:
            # Create the output table
            out_path = arcpy.env.workspace if arcpy.env.workspace else arcpy.env.scratchGDB
            table_name = arcpy.ValidateTableName(arcpy.Describe(output_table).baseName, out_path)
            
            # If output path is specified, use it
            if "/" in output_table or "\" in output_table:
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
            
            # Set output parameter (parameter 3 because we removed the Maximum Records param)
            arcpy.SetParameter(3, full_table_path)
            
        except Exception as e:
            arcpy.AddError(f"Error creating output table: {str(e)}")
            raise
