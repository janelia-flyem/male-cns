"""
Some global variables and constants for the build tools.
"""

import os

import nglscenes as ngl
import navis.interfaces.neuprint as neu

from pathlib import Path
from requests_futures.sessions import FuturesSession
from jinja2 import Environment, FileSystemLoader, select_autoescape

# FutureSession for async requests
FUTURE_SESSION = FuturesSession(max_workers=10)


#####
# Philipp's nglscenes library excludes archived layers; I need them;
# reimplement a couple functions here until I have time to submit
# a PR to nglscenes
# original source is https://github.com/schlegelp/nglscenes; it's GPL3
# by Philipp, who is a collaborator on this project, which is also GPL3,
# so in spirit if not letter of the license, this should be fine
#####

# additional imports needed for this hack
import inspect
from urllib.parse import urldefrag

from nglscenes import utils
from nglscenes.scenes import LAYER_FACTORY


def parse_layers_with_archived(layer, skip_unknown=False):
    if isinstance(layer, list):
        res = [parse_layers_with_archived(l) for l in layer]
        # Drop "None" if skip_unknown=True
        return [l for l in res if l]

    if not isinstance(layer, dict):
        raise TypeError(f'Expected dicts or list thereof, got "{type(layer)}"')

    ty = layer.get("type", "NA")
    if ty not in LAYER_FACTORY:
        if skip_unknown:
            return
        raise ValueError(
            f'Unable to parse layer "{layer.get("name", "")}" of type "{ty}"'
        )

    return LAYER_FACTORY[ty](**layer)


class SceneWithArchived(ngl.Scene):
    @classmethod
    def from_string(cls, string, skip_archived=True):
        """Generate scene from either a JSON or URL."""

        # Extract json
        state = utils.parse_json_scene(string)

        # If input is URL, reuse the base URL
        sig = inspect.signature(cls)
        has_url = "url" in sig.parameters or "base_url" in sig.parameters
        if utils.is_url(string) and has_url:
            url, frag = urldefrag(string)
            x = cls(base_url=url)
        else:
            x = cls()

        layers = parse_layers_with_archived(state.pop("layers", []), skip_archived)

        # Update properties
        x._state.update(state)

        if layers:
            x.add_layers(*layers)

        return x


#####
# A basic Neuroglancer scene to use as a base for the visualisation
#
# these scenes are based on Stuart's public release scene, with the viewpoint
#   copied into it from Philipp's original scene, save manually by me (Don)
#####
# for each region, old v0.9 commented out, new v1.0 link added
# NGL_BASE_URL = "https://neuroglancer-demo.appspot.com/#!gs://flyem-user-links/short/MaleCNS-v0.9-brain.json"
NGL_BASE_URL = "https://neuroglancer-demo.appspot.com/#!gs://flyem-user-links/short/MaleCNS-v1.0-brain.json"
NGL_BASE_SCENE = SceneWithArchived.from_url(NGL_BASE_URL)
# NGL_BASE_URL_VNC = "https://neuroglancer-demo.appspot.com/#!gs://flyem-user-links/short/MaleCNS-v0.9-vnc.json"
NGL_BASE_URL_VNC = "https://neuroglancer-demo.appspot.com/#!gs://flyem-user-links/short/MaleCNS-v1.0-vnc.json"
NGL_BASE_SCENE_VNC = SceneWithArchived.from_url(NGL_BASE_URL_VNC)
# NGL_BASE_URL_TOP = "https://neuroglancer-demo.appspot.com/#!gs://flyem-user-links/short/MaleCNS-v0.9-brain+vnc.json"
NGL_BASE_URL_TOP = "https://neuroglancer-demo.appspot.com/#!gs://flyem-user-links/short/MaleCNS-v1.0-brain+vnc.json"
NGL_BASE_SCENE_TOP = SceneWithArchived.from_url(NGL_BASE_URL_TOP)




# Make sure the segmentation layers are empty and visible
for scene in (NGL_BASE_SCENE, NGL_BASE_SCENE_VNC, NGL_BASE_SCENE_TOP):
    for l in ("cns-seg", "flywire-meshes"):
        # Remove any selected segments
        scene.layers[l]["segments"] = []
        # Make sure the layer is visible (and not archived)
        if scene.layers[l].get("visible", True) is False:
            scene.layers[l]["visible"] = True
        if scene.layers[l].get("archived", False) is True:
            scene.layers[l]["archived"] = False

# Make backgrounds white
# for scene in (NGL_BASE_SCENE, NGL_BASE_SCENE_VNC, NGL_BASE_SCENE_TOP):
#     scene["projectionBackgroundColor"] = "#ffffff"

#####
# URLs for the MCNS and FlyWire meta data
#####
# FLYWIRE_SOURCE = NGL_BASE_SCENE.layers["female (FlyWire)"][
#     "source"
# ]  # precomputed layer
# print(f"Philipp's flywire source: {FLYWIRE_SOURCE}")
# switched to hardcoded; the ng scene we use now has this info in an archived
#   layer, and ngl.Scene.from_url() doesn't load them
FLYWIRE_SOURCE = (
    "precomputed://https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire2mcns/783_v2"
)

# used to get DVID info from the NG scene, but that info is no longer there;
#   now it's passed in via env var, as we might use an internal server
#   whose name we don't want to commit  
# MCNS_SOURCE = NGL_BASE_SCENE.layers["maleCNS"]["source"]["url"]  # DVID layer
# DVID_SERVER = "https://" + MCNS_SOURCE.replace("dvid://https://", "").split("/")[0]
# DVID_NODE = MCNS_SOURCE.replace("dvid://https://", "").split("/")[1]
DVID_SERVER = os.environ["DVID_SERVER"]
DVID_NODE = os.environ["DVID_NODE"]

print(f"Using DVID server: {DVID_SERVER}")
print(f"Using DVID node: {DVID_NODE}")

#####
# Mappings between MCNS -> FlyWire/MANC
#####
# These mappings are re-generated on a 30-minute CRON job on the server
# MCNS_FW_MAPPING_URL = (
#     "https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/mappings/mcns_fw_mapping.json"
# )
# MCNS_MANC_MAPPING_URL = (
#     "https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/mappings/mcns_manc_mapping.json"
# )
# static mappings for 0.13 = 1.0 release
MCNS_FW_MAPPING_URL = (
    "https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/mappings/mcns0.13_fw_mapping.json"
)
MCNS_MANC_MAPPING_URL = (
    "https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/mappings/mcns0.13_manc_mapping.json"
)


#####
# URLs for downloading data for the FlyWire connectome
#####
# This file is the grouped edge list from https://zenodo.org/records/10676866
# FW_EDGES_URL = "https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_connectivity/proofread_connections_783_grouped.feather"
# This file is the grouped edges list for the new Princeton synapse predictions
FW_EDGES_URL = "https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_connectivity/connections_princeton_no_threshold.feather"
# The FlyWire annotations
# v0.9
# FW_META_URL = "https://github.com/flyconnectome/flywire_annotations/raw/refs/heads/main/supplemental_files/Supplemental_file1_neuron_annotations.tsv"
# preliminary v1.0, not released yet:
FW_META_URL = "https://github.com/flyconnectome/flywire_annotations/raw/refs/heads/staging3/supplemental_files/Supplemental_file1_neuron_annotations.tsv"

#####
# URLs for downloading data for the MCNS connectome
#####
# This edge list was compiled straight from neuPrint for all neurons with a superclass (320Mb)
# Crucially it has the edges broken down by ROI which allows us to subset to connections within the brain
# v0.9
# MCNS_EDGES_URL = "https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_connectivity/mcns_all_edges_by_roi_v0.9.feather"
# v0.13 == v1.0
MCNS_EDGES_URL = "https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_connectivity/connectome-weights-male-cns-v0.13-minconf-0.5-with_rois.feather"

# VNC neuropils (we will use these to filter the MCNS edges)
MCNS_VNC_NEUROPILS = [
    "ANm",
    "HTct(UTct-T3)(L)",
    "HTct(UTct-T3)(R)",
    "IntTct",
    "LTct",
    "LegNp(T1)(L)",
    "LegNp(T1)(R)",
    "LegNp(T2)(L)",
    "LegNp(T2)(R)",
    "LegNp(T3)(L)",
    "LegNp(T3)(R)",
    "NTct(UTct-T1)(L)",
    "NTct(UTct-T1)(R)",
    "Ov(L)",
    "Ov(R)",
    "WTct(UTct-T2)(L)",
    "WTct(UTct-T2)(R)",
    "mVAC(T1)(L)",
    "mVAC(T1)(R)",
    "mVAC(T2)(L)",
    "mVAC(T2)(R)",
    "mVAC(T3)(L)",
    "mVAC(T3)(R)",
    "ADMN(L)",
    "ADMN(R)",
    "AbN1(L)",
    "AbN1(R)",
    "AbN2(L)",
    "AbN2(R)",
    "AbN3(L)",
    "AbN3(R)",
    "AbN4(L)",
    "AbN4(R)",
    "AbNT(L)",
    "AbNT(R)",
    "CvN(L)",
    "CvN(R)",
    "DMetaN(L)",
    "DMetaN(R)",
    "DProN(L)",
    "DProN(R)",
    "MesoAN(L)",
    "MesoAN(R)",
    "MesoLN(L)",
    "MesoLN(R)",
    "MetaLN(L)",
    "MetaLN(R)",
    "PDMN(L)",
    "PDMN(R)",
    "PrN(L)",
    "PrN(R)",
    "ProAN(L)",
    "ProAN(R)",
    "ProCN(L)",
    "ProCN(R)",
    "ProLN(L)",
    "ProLN(R)",
    "VProN(L)",
    "VProN(R)",
    "VNC-unspecified",
]

#####
# Various directories for the build / cache
#####

# Basepath for the repository
REPO_BASE_PATH = Path(__file__).parent.parent

# Directory for the JINJA templates
TEMPLATE_DIR = REPO_BASE_PATH / "templates"

# Directory for the generated HTML files
BUILD_DIR = REPO_BASE_PATH / "docs/build"
SUMMARY_TYPES_DIR = BUILD_DIR / "summary_types"
THUMBNAILS_DIR = BUILD_DIR / "thumbnails"
GRAPH_DIR = BUILD_DIR / "graphs"
TABLES_DIR = BUILD_DIR / "tables"
SUPERTYPE_DIR = BUILD_DIR / "supertypes"
HEMILINEAGE_DIR = BUILD_DIR / "hemilineages"
SYNONYMS_DIR = BUILD_DIR / "synonyms"

# Directory for the final HTML files
SITE_DIR = REPO_BASE_PATH / "site"

# Directory for the some cached data (use the --update-metadata flag to trigger a refresh)
CACHE_DIR = REPO_BASE_PATH / ".cache"
MCNS_META_DATA_CACHE = CACHE_DIR / "mcns_meta_data.feather"
MCNS_ROI_INFO_CACHE = CACHE_DIR / "mcns_roi_info.feather"
FW_META_DATA_CACHE = CACHE_DIR / "fw_meta_data.feather"
FW_ROI_INFO_CACHE = CACHE_DIR / "fw_roi_info.feather"
MAPPING_CACHE = CACHE_DIR / "mapping.json"

# Make sure the directories exist
for dir in (
    CACHE_DIR,
    BUILD_DIR,
    SUMMARY_TYPES_DIR,
    THUMBNAILS_DIR,
    GRAPH_DIR,
    TABLES_DIR,
    SUPERTYPE_DIR,
    HEMILINEAGE_DIR,
    SYNONYMS_DIR,
):
    dir.mkdir(parents=True, exist_ok=True)

#####
# Set up the Jinja2 environment
#####
JINJA_ENV = Environment(
    loader=FileSystemLoader(searchpath=TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)

#####
# A global neuprint client
#####
# v0.9:
# NEUPRINT_CLIENT = neu.Client(server="https://neuprint.janelia.org", dataset="male-cns:v0.9")
# v1.0, internal server:
NEUPRINT_SERVER = os.environ["NEUPRINT_SERVER"]
NEUPRINT_CLIENT = neu.Client(server=NEUPRINT_SERVER, dataset="male-cns:v1.0")

#####
# Some BASE URLs for neuPrint
#####

# Basic neuPrint search
# v0.9
# NEUPRINT_SEARCH_URL = "https://neuprint.janelia.org/results?dataset=male-cns%3Av0.9&qt=findneurons&q=1&qr%5B0%5D%5Bcode%5D=fn&qr%5B0%5D%5Bds%5D=male-cns%3Av0.9&qr%5B0%5D%5Bpm%5D%5Bdataset%5D=male-cns%3Av0.9&qr%5B0%5D%5Bpm%5D%5BinputMatchAny%5D=false&qr%5B0%5D%5Bpm%5D%5BoutputMatchAny%5D=false&qr%5B0%5D%5Bpm%5D%5Ball_segments%5D=false&qr%5B0%5D%5Bpm%5D%5Benable_contains%5D=true&qr%5B0%5D%5Bpm%5D%5Bneuron_name%5D={neuron_name}&qr%5B0%5D%5BvisProps%5D%5BrowsPerPage%5D=25&tab=0"
# v1.0 (just replace version number)
NEUPRINT_SEARCH_URL = "https://neuprint.janelia.org/results?dataset=male-cns%3Av1.0&qt=findneurons&q=1&qr%5B0%5D%5Bcode%5D=fn&qr%5B0%5D%5Bds%5D=male-cns%3Av1.0&qr%5B0%5D%5Bpm%5D%5Bdataset%5D=male-cns%3Av1.0&qr%5B0%5D%5Bpm%5D%5BinputMatchAny%5D=false&qr%5B0%5D%5Bpm%5D%5BoutputMatchAny%5D=false&qr%5B0%5D%5Bpm%5D%5Ball_segments%5D=false&qr%5B0%5D%5Bpm%5D%5Benable_contains%5D=true&qr%5B0%5D%5Bpm%5D%5Bneuron_name%5D={neuron_name}&qr%5B0%5D%5BvisProps%5D%5BrowsPerPage%5D=25&tab=0"

# v0.9
# Connectivity search
# NEUPRINT_CONNECTIVITY_URL = "https://neuprint.janelia.org/results?dataset=male-cns%3Av0.9&qt=simpleconnection&q=1&qr%5B0%5D%5Bcode%5D=sc&qr%5B0%5D%5Bds%5D=male-cns%3Av0.9&qr%5B0%5D%5Bpm%5D%5Bdataset%5D=male-cns%3Av0.9&qr%5B0%5D%5Bpm%5D%5Benable_contains%5D=true&qr%5B0%5D%5Bpm%5D%5Bneuron_name%5D={neuron_name}&qr%5B0%5D%5Bpm%5D%5Bfind_inputs%5D=false&qr%5B0%5D%5BvisProps%5D%5BpaginateExpansion%5D=true&tab=0"
# v1.0 (just replace version number)
NEUPRINT_CONNECTIVITY_URL = "https://neuprint.janelia.org/results?dataset=male-cns%3Av1.0&qt=simpleconnection&q=1&qr%5B0%5D%5Bcode%5D=sc&qr%5B0%5D%5Bds%5D=male-cns%3Av1.0&qr%5B0%5D%5Bpm%5D%5Bdataset%5D=male-cns%3Av1.0&qr%5B0%5D%5Bpm%5D%5Benable_contains%5D=true&qr%5B0%5D%5Bpm%5D%5Bneuron_name%5D={neuron_name}&qr%5B0%5D%5Bpm%5D%5Bfind_inputs%5D=false&qr%5B0%5D%5BvisProps%5D%5BpaginateExpansion%5D=true&tab=0"
