# -*- coding: utf-8 -*-
"""
Bionet Fauna Query -> ArcGIS Online all_species sync (v11 - Dr. Petrov Edition)

This toolbox fetches the Power Query "all_species" OData resource
(SpeciesNames) from NSW BioNet and syncs it into a hosted non-spatial
ArcGIS Online table. If the hosted table does not exist it will be
published from a temporary CSV. If it exists the tool will truncate
(or delete) existing rows and append refreshed rows.

v11 Features:
- Robust paging with retry logic
- Tactical 'order' field handling (rename or fallback)
- Case-insensitive sorting with original case preservation
- Attribute index creation on key fields
- Formal legal metadata injection
- CSV item cleanup (evidence incinerator)
- Progress percentage logging

Security: the toolbox accepts AGOL credentials as parameters. Do NOT
hardcode credentials. Use an ArcGIS profile if possible.

Prerequisites:
 - arcgis (ArcGIS API for Python)
 - pandas
 - requests
 - openpyxl (if you also plan to read Excel)

Install with: pip install arcgis pandas requests openpyxl
"""

import arcpy
import os
import json
import tempfile
import requests
import urllib.parse
import pandas as pd
from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection
from time import sleep
from datetime import datetime
import math
import traceback

# constants
ODATA_BASE = "https://data.bionet.nsw.gov.au/biosvcapp/odata"
RESOURCE = "SpeciesNames"
REQUEST_COLUMNS = [
    "kingdom",
    "class",
    "order",
    "family",
    "specificEpithet",
    "infraspecificEpithet",
    "scientificNameID",
    "speciesCode_Synonym",
    "scientificName",
    "vernacularName",
    "taxonID",
    "currentScientificNameCode",
    "currentScientificName",
    "isCurrent",
    "establishmentMeans",
    "primaryGrowthForm",
    "primaryGrowthFormGroup",
    "secondaryGrowthForms",
    "secondaryGrowthFormGroups",
    "stateConservation",
    "countryConservation",
    "highThreatWeed",
]
# v11: Keep all REQUEST_COLUMNS in final output
FINAL_COLUMNS = REQUEST_COLUMNS
ADD_CHUNK = 500
MAX_RETRIES = 3
RETRY_DELAY = 2

# Formal legal metadata policy
FORMAL_LEGAL_POLICY = """
**DATA OWNERSHIP AND ACCESS POLICY**

This dataset is the exclusive property of Anderson Environmental Planning (AEP). 
Access to this data is restricted to authorized AEP staff members only. 

**Terms of Use:**
- The data contained herein is proprietary and confidential
- Unauthorized access, distribution, or reproduction is strictly prohibited
- Data may not be shared with external parties without explicit written authorization from AEP management

**Data Access Requests:**
For inquiries regarding data access, permissions, or licensing, please contact:
Anderson Environmental Planning
Data Management Office
Email: data@aep.example.com

**Disclaimer:**
AEP makes no warranties, express or implied, regarding the accuracy, completeness, 
or fitness for a particular purpose of this data. Use of this data is at the user's own risk.

**Last Updated:** {timestamp}
**Total Records:** {record_count}
"""

def petrov_warning(msg):
    """Log warning message in Dr. Petrov style."""
    arcpy.AddWarning(f"[PETROV WARNING] {msg}")

def petrov_message(msg):
    """Log informational message in Dr. Petrov style."""
    arcpy.AddMessage(f"[PETROV] {msg}")

def petrov_error(msg):
    """Log error message in Dr. Petrov style."""
    arcpy.AddError(f"[PETROV ERROR] {msg}")

def _build_url(resource, params):
    safe = "()',"
    q = urllib.parse.urlencode(params, safe=safe, quote_via=urllib.parse.quote)
    return f"{ODATA_BASE}/{resource}?{q}"

def attempt_field_rename_order(flc):
    """
    Attempt to rename 'taxonOrder' field to 'order' in the hosted service.
    
    Strategy:
    1. Try to use updateDefinition to rename field taxonOrder -> order
    2. If rename not supported, add new 'order' field, copy values, delete 'taxonOrder'
    
    Returns True if successful, False otherwise.
    """
    try:
        petrov_message("Attempting tactical 'order' field handling...")
        
        # Get current definition
        service_definition = flc.properties
        
        # Check if 'order' field already exists
        layers_or_tables = flc.layers if flc.layers else flc.tables
        if not layers_or_tables:
            petrov_warning("No layers or tables found in FeatureLayerCollection")
            return False
        
        target = layers_or_tables[0]
        fields = target.properties.fields
        
        has_order = any(f['name'].lower() == 'order' for f in fields)
        has_taxon_order = any(f['name'] == 'taxonOrder' for f in fields)
        
        if has_order and not has_taxon_order:
            petrov_message("Field 'order' already exists, no rename needed")
            return True
        
        if not has_taxon_order:
            petrov_warning("Field 'taxonOrder' not found, cannot rename")
            return False
        
        # Strategy 1: Try to rename using updateDefinition
        petrov_message("Strategy 1: Attempting field rename via updateDefinition...")
        try:
            # Find the taxonOrder field definition
            taxon_order_field = next(f for f in fields if f['name'] == 'taxonOrder')
            field_def = dict(taxon_order_field)
            field_def['name'] = 'order'
            
            # Try to update definition
            update_def = {
                "fields": [field_def]
            }
            
            result = flc.manager.update_definition(update_def)
            if result.get('success'):
                petrov_message("Field rename successful via updateDefinition")
                return True
            else:
                petrov_warning(f"Field rename via updateDefinition returned: {result}")
        except Exception as e:
            petrov_warning(f"Field rename via updateDefinition failed: {e}")
        
        # Strategy 2: Add new field, copy values, delete old field
        petrov_message("Strategy 2: Fallback to add/copy/delete sequence...")
        try:
            # Add new 'order' field
            petrov_message("Adding new 'order' field...")
            add_field_def = {
                "fields": [{
                    "name": "order",
                    "type": "esriFieldTypeString",
                    "alias": "Order",
                    "length": 255,
                    "nullable": True
                }]
            }
            
            add_result = flc.manager.add_to_definition(add_field_def)
            if not add_result.get('success'):
                petrov_warning(f"Failed to add 'order' field: {add_result}")
                return False
            
            petrov_message("New 'order' field added successfully")
            
            # Copy values from taxonOrder to order
            petrov_message("Copying values from 'taxonOrder' to 'order'...")
            all_features = target.query(where="1=1", return_all_records=True)
            
            updates = []
            for feature in all_features.features:
                if 'taxonOrder' in feature.attributes and feature.attributes['taxonOrder']:
                    updates.append({
                        "attributes": {
                            target.properties.objectIdField: feature.attributes[target.properties.objectIdField],
                            "order": feature.attributes['taxonOrder']
                        }
                    })
            
            if updates:
                # Update in chunks
                chunk_size = 500
                for i in range(0, len(updates), chunk_size):
                    chunk = updates[i:i+chunk_size]
                    target.edit_features(updates=chunk)
                    petrov_message(f"Copied {min(i+chunk_size, len(updates))}/{len(updates)} values")
                
                petrov_message(f"Value copy complete: {len(updates)} records updated")
            
            # Delete taxonOrder field
            petrov_message("Deleting 'taxonOrder' field...")
            delete_field_def = {
                "fields": [{"name": "taxonOrder"}]
            }
            
            delete_result = flc.manager.delete_from_definition(delete_field_def)
            if delete_result.get('success'):
                petrov_message("Successfully deleted 'taxonOrder' field")
                return True
            else:
                petrov_warning(f"Failed to delete 'taxonOrder' field: {delete_result}")
                # Still consider success if we got this far
                return True
                
        except Exception as e:
            petrov_warning(f"Add/copy/delete sequence failed: {e}")
            return False
            
    except Exception as e:
        petrov_warning(f"Field rename operation failed: {e}")
        traceback.print_exc()
        return False

def create_attribute_indexes(flc, index_fields=None):
    """
    Create attribute indexes on specified fields using add_to_definition.
    
    Default fields: kingdom, class, family, scientificName
    """
    if index_fields is None:
        index_fields = ["kingdom", "class", "family", "scientificName"]
    
    try:
        petrov_message(f"Creating attribute indexes on fields: {', '.join(index_fields)}")
        
        layers_or_tables = flc.layers if flc.layers else flc.tables
        if not layers_or_tables:
            petrov_warning("No layers or tables found for index creation")
            return False
        
        target = layers_or_tables[0]
        existing_indexes = target.properties.get('indexes', [])
        
        # Build index definitions
        indexes_to_add = []
        for field in index_fields:
            # Check if index already exists
            index_name = f"idx_{field}"
            if any(idx.get('name') == index_name for idx in existing_indexes):
                petrov_message(f"Index '{index_name}' already exists, skipping")
                continue
            
            index_def = {
                "name": index_name,
                "fields": field,
                "isAscending": True,
                "isUnique": False,
                "description": f"Index on {field} field"
            }
            indexes_to_add.append(index_def)
        
        if not indexes_to_add:
            petrov_message("All requested indexes already exist")
            return True
        
        # Add indexes
        index_payload = {"indexes": indexes_to_add}
        result = flc.manager.add_to_definition(index_payload)
        
        if result.get('success'):
            petrov_message(f"Successfully created {len(indexes_to_add)} indexes")
            return True
        else:
            petrov_warning(f"Index creation returned: {result}")
            return False
            
    except Exception as e:
        petrov_warning(f"Index creation failed: {e}")
        traceback.print_exc()
        return False

def update_item_metadata(item, record_count):
    """
    Update item metadata with formal legal policy and statistics.
    """
    try:
        petrov_message("Updating item metadata with formal legal policy...")
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        description = FORMAL_LEGAL_POLICY.format(
            timestamp=timestamp,
            record_count=record_count
        )
        
        # Update item properties
        update_props = {
            "description": description,
            "snippet": f"AEP proprietary BioNet species data. {record_count} records. Last updated: {timestamp}"
        }
        
        result = item.update(item_properties=update_props)
        
        if result:
            petrov_message("Item metadata updated successfully")
            return True
        else:
            petrov_warning("Item metadata update returned False")
            return False
            
    except Exception as e:
        petrov_warning(f"Metadata update failed: {e}")
        traceback.print_exc()
        return False

def fetch_all_species_df(username=None, password=None, page_size=1000, sleep_between_pages=0.2, timeout=60):
    """Fetches SpeciesNames records and returns a pandas DataFrame with robust paging and retry logic.
    
    v11 features:
    - Retry logic for failed requests
    - Progress percentage logging
    - Case-insensitive sorting (kingdom, class, order, family, scientificName)
    - Returns all REQUEST_COLUMNS
    """
    session = requests.Session()
    headers = {"Accept": "application/json"}
    if username and password:
        session.auth = (username, password)

    select_param = ",".join(REQUEST_COLUMNS)
    params = {
        "$select": select_param,
        "$orderby": "scientificName asc",
        "$top": str(page_size),
        "$count": "true",  # Request total count if available
    }
    url = _build_url(RESOURCE, params)

    records = []
    next_link = None
    page_num = 0
    total_count = None

    petrov_message(f"Beginning BioNet SpeciesNames fetch with page_size={page_size}")

    while True:
        req_url = next_link if next_link else url
        page_num += 1
        
        # Retry logic
        retry_count = 0
        success = False
        while retry_count < MAX_RETRIES and not success:
            try:
                resp = session.get(req_url, headers=headers, timeout=timeout)
                if resp.status_code != 200:
                    raise RuntimeError(f"OData request failed (HTTP {resp.status_code}): {resp.text}")
                success = True
            except Exception as e:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    petrov_error(f"Page {page_num} failed after {MAX_RETRIES} retries: {e}")
                    raise
                petrov_warning(f"Page {page_num} failed (attempt {retry_count}/{MAX_RETRIES}), retrying in {RETRY_DELAY}s: {e}")
                sleep(RETRY_DELAY)
        
        data = resp.json()
        
        # Extract total count if available (first page only)
        if page_num == 1 and isinstance(data, dict):
            total_count = data.get("@odata.count") or data.get("odata.count")
            if total_count:
                petrov_message(f"Total count from OData: {total_count}")
        
        # Extract records
        if isinstance(data, dict) and "value" in data:
            page_values = data["value"]
        elif isinstance(data, list):
            page_values = data
        else:
            raise RuntimeError("Unexpected OData response format")
        
        records.extend(page_values)
        
        # Progress logging
        if total_count and total_count > 0:
            progress_pct = min(100.0, (len(records) / total_count) * 100)
            petrov_message(f"Page {page_num}: fetched {len(page_values)} rows (total: {len(records)}, {progress_pct:.1f}%)")
        else:
            petrov_message(f"Page {page_num}: fetched {len(page_values)} rows (total: {len(records)})")

        # Follow next link
        if isinstance(data, dict):
            next_link = data.get("@odata.nextLink") or data.get("odata.nextLink")
        else:
            next_link = None
        if not next_link:
            break
        sleep(sleep_between_pages)

    if not records:
        petrov_warning("No records fetched from BioNet OData")
        return pd.DataFrame(columns=FINAL_COLUMNS)

    petrov_message(f"Fetch complete: {len(records)} total records")

    df = pd.DataFrame.from_records(records)
    
    # Ensure all expected request columns exist
    for col in REQUEST_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # v11: Case-insensitive sorting by kingdom, class, order, family, scientificName
    # Create temporary lowercase columns for sorting
    sort_columns = ["kingdom", "class", "order", "family", "scientificName"]
    temp_sort_cols = []
    for col in sort_columns:
        if col in df.columns:
            temp_col = f"_sort_{col}"
            df[temp_col] = df[col].astype(str).str.lower()
            temp_sort_cols.append(temp_col)
    
    if temp_sort_cols:
        petrov_message(f"Sorting DataFrame by: {', '.join(sort_columns)} (case-insensitive)")
        df = df.sort_values(by=temp_sort_cols, ascending=True, kind="mergesort").reset_index(drop=True)
        # Remove temporary sorting columns
        df = df.drop(columns=temp_sort_cols)

    # Build final df with all REQUEST_COLUMNS
    df_final = df[FINAL_COLUMNS].copy()
    return df_final


class Toolbox(object):
    def __init__(self):
        self.label = "Bionet Fauna: all_species -> AGOL"
        self.alias = "bionet_all_species"
        self.tools = [AllSpeciesSyncTool]


class AllSpeciesSyncTool(object):
    def __init__(self):
        self.label = "Sync all_species to ArcGIS Online"
        self.description = "Fetch all_species from BioNet OData and sync to a hosted table on ArcGIS Online"
        self.canRunInBackground = False

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="AGOL URL",
            name="ago_url",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        p0.value = "https://andersonep.maps.arcgis.com/"

        p1 = arcpy.Parameter(
            displayName="AGOL Username (optional)",
            name="username",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        p2 = arcpy.Parameter(
            displayName="AGOL Password (optional)",
            name="password",
            datatype="GPStringHidden",
            parameterType="Optional",
            direction="Input")

        p3 = arcpy.Parameter(
            displayName="Target hosted table title",
            name="target_title",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        p4 = arcpy.Parameter(
            displayName="Create if missing?",
            name="create_if_missing",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        p4.value = True

        p5 = arcpy.Parameter(
            displayName="Page size (rows per OData request)",
            name="page_size",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        p5.value = 1000

        return [p0, p1, p2, p3, p4, p5]

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
        ago_url = parameters[0].valueAsText
        username = parameters[1].valueAsText
        password = parameters[2].valueAsText
        target_title = parameters[3].valueAsText
        create_if_missing = bool(parameters[4].value)
        page_size = int(parameters[5].value) if parameters[5].value is not None else 1000

        petrov_message(f"=== BionetFaunaQuery v11 Execution Started ===")
        petrov_message(f"Target: {target_title}")
        
        petrov_message(f"Connecting to {ago_url} ...")
        try:
            if username and password:
                gis = GIS(ago_url, username, password)
            else:
                gis = GIS(ago_url)
            petrov_message(f"Connected. Logged in: {gis.properties.user.username if gis.logged_in else 'anonymous'}")
        except Exception as e:
            petrov_error(f"Failed to connect to GIS: {e}")
            raise

        petrov_message("Fetching all_species from BioNet OData...")
        try:
            df = fetch_all_species_df(username=None, password=None, page_size=page_size)
        except Exception as e:
            petrov_error(f"Failed to fetch all_species: {e}")
            raise

        record_count = len(df)
        petrov_message(f"Fetched {record_count} rows; preparing to sync to '{target_title}'")

        # Find existing hosted item (robust search)
        owner = gis.users.me.username if gis.logged_in else None
        q = f"title:\"{target_title}\""
        if owner:
            q += f" AND owner:{owner}"
        items = gis.content.search(query=q, item_type="Feature Layer", max_items=10)
        item = items[0] if items else None

        csv_item = None
        csv_item_id = None
        
        if item is None:
            if not create_if_missing:
                petrov_warning("Target not found and creation disabled; exiting")
                return
            petrov_message("Target not found; publishing new hosted table from DataFrame...")
            tmpdir = tempfile.mkdtemp(prefix="bionet_")
            csv_path = os.path.join(tmpdir, f"{target_title}.csv")
            
            # Handle 'order' field for CSV: rename to taxonOrder to avoid portal rejection
            df_for_csv = df.copy()
            if 'order' in df_for_csv.columns:
                df_for_csv = df_for_csv.rename(columns={'order': 'taxonOrder'})
                petrov_message("Renamed 'order' -> 'taxonOrder' in CSV to avoid portal rejection")
            
            df_for_csv.to_csv(csv_path, index=False, encoding="utf-8")
            petrov_message(f"Wrote temporary CSV: {csv_path}")
            
            item_props = {
                "title": target_title, 
                "tags": "bionet,all_species,automated,v11",
                "snippet": "BioNet species data - AEP proprietary"
            }
            csv_item = gis.content.add(item_properties=item_props, data=csv_path)
            csv_item_id = csv_item.id
            petrov_message(f"Uploaded CSV item (id: {csv_item_id})")
            
            try:
                published = csv_item.publish()
                petrov_message(f"Published hosted table: item id {published.id}")
                item = published
                flc = FeatureLayerCollection.fromitem(published)
            except Exception as e:
                petrov_error(f"Publish failed: {e}")
                raise
        else:
            petrov_message(f"Found existing hosted item (id={item.id})")
            flc = FeatureLayerCollection.fromitem(item)
            
            # Try truncate
            try:
                if hasattr(flc.manager, 'truncate'):
                    petrov_message("Truncating existing hosted table...")
                    flc.manager.truncate()
                    petrov_message("Truncate complete.")
                else:
                    petrov_message("Truncate not supported; attempting delete where=1=1 on first table/layer")
                    target_table = flc.tables[0] if flc.tables else (flc.layers[0] if flc.layers else None)
                    if target_table is not None:
                        target_table.delete_features(where="1=1")
                        petrov_message("Delete complete.")
            except Exception as e:
                petrov_warning(f"Truncate/delete failed: {e}; continuing to append which may create duplicates.")

        # Determine target table object
        target_table_obj = None
        if hasattr(flc, 'tables') and flc.tables:
            target_table_obj = flc.tables[0]
        elif hasattr(flc, 'layers') and flc.layers:
            target_table_obj = flc.layers[0]
        else:
            petrov_error("No table or layer found in published service.")
            return

        # Build features list
        features = []
        petrov_message(f"Building features from {record_count} records...")
        for idx, row in df.fillna("").iterrows():
            attrs = {}
            for col in df.columns:
                # Handle 'order' field: use 'taxonOrder' for publishing
                field_name = 'taxonOrder' if col == 'order' else col
                val = row[col]
                if isinstance(val, pd.Timestamp):
                    attrs[field_name] = val.isoformat()
                elif isinstance(val, (float, int, str, bool)) or val == "" or val is None:
                    attrs[field_name] = val if not (isinstance(val, float) and math.isnan(val)) else None
                else:
                    try:
                        attrs[field_name] = str(val)
                    except Exception:
                        attrs[field_name] = None
            features.append({"attributes": attrs})

        petrov_message(f"Appending {len(features)} rows in chunks of {ADD_CHUNK}...")
        try:
            total_chunks = math.ceil(len(features) / ADD_CHUNK)
            for i in range(0, len(features), ADD_CHUNK):
                chunk = features[i:i+ADD_CHUNK]
                chunk_num = i // ADD_CHUNK + 1
                progress_pct = (chunk_num / total_chunks) * 100
                petrov_message(f"Appending chunk {chunk_num}/{total_chunks} ({len(chunk)} rows) - {progress_pct:.1f}% complete")
                target_table_obj.edit_features(adds=chunk)
                sleep(0.2)
            petrov_message("Append complete.")
        except Exception as e:
            petrov_error(f"Append failed: {e}")
            raise

        # v11: Tactical 'order' field handling
        attempt_field_rename_order(flc)
        
        # v11: Create attribute indexes
        create_attribute_indexes(flc)
        
        # v11: Update item metadata with formal legal policy
        update_item_metadata(item, record_count)
        
        # v11: Evidence incinerator - delete CSV item if it was created
        if csv_item is not None and csv_item_id is not None:
            try:
                petrov_message(f"Evidence incinerator: Removing intermediate CSV item (id: {csv_item_id})")
                csv_item.delete()
                petrov_message("CSV item successfully deleted")
            except Exception as e:
                petrov_warning(f"Failed to delete CSV item: {e}")

        petrov_message("=== Sync complete. All v11 operations executed. ===")
