# -*- coding: utf-8 -*-
"""
Bionet Fauna Query -> ArcGIS Online all_species sync

This toolbox fetches the Power Query "all_species" OData resource
(SpeciesNames) from NSW BioNet and syncs it into a hosted non-spatial
ArcGIS Online table. If the hosted table does not exist it will be
published from a temporary CSV. If it exists the tool will truncate
(or delete) existing rows and append refreshed rows.

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
FINAL_COLUMNS = ["scientificName", "speciesCode_Synonym", "vernacularName"]
ADD_CHUNK = 500

def _build_url(resource, params):
    safe = "()',"
    q = urllib.parse.urlencode(params, safe=safe, quote_via=urllib.parse.quote)
    return f"{ODATA_BASE}/{resource}?{q}"

def fetch_all_species_df(username=None, password=None, page_size=1000, sleep_between_pages=0.2, timeout=60):
    """Fetches SpeciesNames records and returns a pandas DataFrame with final columns.

    Uses basic paging following @odata.nextLink when available.
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
    }
    url = _build_url(RESOURCE, params)

    records = []
    next_link = None

    while True:
        req_url = next_link if next_link else url
        resp = session.get(req_url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"OData request failed (HTTP {resp.status_code}): {resp.text}")
        data = resp.json()
        if isinstance(data, dict) and "value" in data:
            page_values = data["value"]
        elif isinstance(data, list):
            page_values = data
        else:
            raise RuntimeError("Unexpected OData response format")
        records.extend(page_values)

        # follow next link
        if isinstance(data, dict):
            next_link = data.get("@odata.nextLink") or data.get("odata.nextLink")
        else:
            next_link = None
        if not next_link:
            break
        sleep(sleep_between_pages)

    if not records:
        return pd.DataFrame(columns=FINAL_COLUMNS)

    df = pd.DataFrame.from_records(records)
    # ensure all expected request columns exist
    for col in REQUEST_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # sort defensively
    if "scientificName" in df.columns:
        df = df.sort_values(by="scientificName", ascending=True, kind="mergesort").reset_index(drop=True)

    # build final df with final columns present
    final_present = [c for c in FINAL_COLUMNS if c in df.columns]
    df_final = df[final_present].copy()
    for c in FINAL_COLUMNS:
        if c not in df_final.columns:
            df_final[c] = pd.NA
    df_final = df_final[FINAL_COLUMNS]
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

        arcpy.AddMessage(f"Connecting to {ago_url} ...")
        try:
            if username and password:
                gis = GIS(ago_url, username, password)
            else:
                gis = GIS(ago_url)
            arcpy.AddMessage(f"Connected. Logged in: {gis.properties.user.username if gis.logged_in else 'anonymous'}")
        except Exception as e:
            arcpy.AddError(f"Failed to connect to GIS: {e}")
            raise

        arcpy.AddMessage("Fetching all_species from BioNet OData...")
        try:
            df = fetch_all_species_df(username=None, password=None, page_size=page_size)
        except Exception as e:
            arcpy.AddError(f"Failed to fetch all_species: {e}")
            raise

        arcpy.AddMessage(f"Fetched {len(df)} rows; preparing to sync to '{target_title}'")

        # find existing hosted item
        owner = gis.users.me.username if gis.logged_in else None
        q = f"title:\"{target_title}\""
        if owner:
            q += f" AND owner:{owner}"
        items = gis.content.search(query=q, item_type="Feature Layer", max_items=10)
        item = items[0] if items else None

        if item is None:
            if not create_if_missing:
                arcpy.AddWarning("Target not found and creation disabled; exiting")
                return
            arcpy.AddMessage("Target not found; publishing new hosted table from DataFrame...")
            tmpdir = tempfile.mkdtemp(prefix="bionet_")
            csv_path = os.path.join(tmpdir, f"{target_title}.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8")
            arcpy.AddMessage(f"Wrote temporary CSV: {csv_path}")
            item_props = {"title": target_title, "tags": "bionet,all_species,automated"}
            csv_item = gis.content.add(item_properties=item_props, data=csv_path)
            try:
                published = csv_item.publish()
                arcpy.AddMessage(f"Published hosted table: item id {published.properties.serviceItemId}")
                flc = published
            except Exception as e:
                arcpy.AddError(f"Publish failed: {e}")
                raise
        else:
            arcpy.AddMessage(f"Found existing hosted item (id={{item.id}})")
            flc = FeatureLayerCollection.fromitem(item)
            # try truncate
            try:
                if hasattr(flc.manager, 'truncate'):
                    arcpy.AddMessage("Truncating existing hosted table...")
                    flc.manager.truncate()
                    arcpy.AddMessage("Truncate complete.")
                else:
                    arcpy.AddMessage("Truncate not supported; attempting delete where=1=1 on first table/layer")
                    target_table = flc.tables[0] if flc.tables else (flc.layers[0] if flc.layers else None)
                    if target_table is not None:
                        target_table.delete_features(where="1=1")
                        arcpy.AddMessage("Delete complete.")
            except Exception as e:
                arcpy.AddWarning(f"Truncate/delete failed: {e}; continuing to append which may create duplicates.")

        # determine target table object
        target_table_obj = None
        if hasattr(flc, 'tables') and flc.tables:
            target_table_obj = flc.tables[0]
        elif hasattr(flc, 'layers') and flc.layers:
            target_table_obj = flc.layers[0]
        else:
            arcpy.AddError("No table or layer found in published service.")
            return

        # build features list
        features = []
        for idx, row in df.fillna("").iterrows():
            attrs = {}
            for col in df.columns:
                val = row[col]
                if isinstance(val, pd.Timestamp):
                    attrs[col] = val.isoformat()
                elif isinstance(val, (float, int, str, bool)) or val == "" or val is None:
                    attrs[col] = val if not (isinstance(val, float) and math.isnan(val)) else None
                else:
                    try:
                        attrs[col] = str(val)
                    except Exception:
                        attrs[col] = None
            features.append({"attributes": attrs})

        arcpy.AddMessage(f"Appending {len(features)} rows in chunks of {ADD_CHUNK}...")
        try:
            for i in range(0, len(features), ADD_CHUNK):
                chunk = features[i:i+ADD_CHUNK]
                arcpy.AddMessage(f" - Appending chunk {i//ADD_CHUNK + 1} ({len(chunk)} rows)")
                target_table_obj.edit_features(adds=chunk)
                sleep(0.2)
            arcpy.AddMessage("Append complete.")
        except Exception as e:
            arcpy.AddError(f"Append failed: {e}")
            raise

        arcpy.AddMessage("Sync complete.")
