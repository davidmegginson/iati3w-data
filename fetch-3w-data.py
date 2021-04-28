""" Import data from the latest Somalia 3W """

import hxl, hashlib, json, sys

from iati3w_common import *


#
# Utility functions
#

def make_pseudo_identifier (data):
    """ Since 3W data doesn't have unique activity identifiers, construct a pseudo one """
    return hashlib.sha256(json.dumps([
        data["title"],
        data["description"],
        data["orgs"],
        data["sectors"],
        data["locations"],
    ]).encode("utf-8")).hexdigest()[:8]


def fix_cluster_name (name):
    """ Look up the normalised version of a cluster name """
    table = get_lookup_table("inputs/humanitarian-cluster-map.json")
    key = make_token(name)
    if key in table and "name" in table[key]:
        return table[key]["name"]
    else:
        return normalise_string(name)

    
#
# Read Somalia 3W activities via the HXL Proxy (which adds HXL hashtags)
#

def make_activity(row):
    """ Construct an activity object from the HXL row provided """
    
    # Rough in the activity object (fill in details later)
    data = {
        "identifier": None,
        "source": "3W",
        "reported_by": "OCHA Somalia",
        "humanitarian": True,
        "title": row.get("#activity+programme", default=row.get("#activity+project")),
        "description": row.get("#activity+project"),
        "active": row.get("#status") == "Ongoing",
        "orgs": {
            "implementing": [],
            "programming": [],
            "funding": [],
        },
        "sectors": {
            "humanitarian": [],
            "dac": [],
        },
        "locations": {
            "unclassified": [],
            "admin2": [],
            "admin1": [],
            "countries": ["SO"],
        },
        "dates": {
            "start": row.get("#date+start"),
            "end": row.get("#date+end"),
        },
        "modalities": [],
        "targeted": {},
    }

    # add the participating organisations
    for params in [
            ["#org+impl", "implementing"],
            ["#org+prog", "programming"],
            ["#org+funding", "funding"],
    ]:
        org_name = row.get(params[0])
        if org_name:
            org = lookup_org(org_name, create=True)
            if org is not None and not org.get("skip", False):
                add_unique(org["shortname"], data["orgs"][params[1]])

    # add the clusters
    add_unique(fix_cluster_name(row.get("#sector")), data["sectors"]["humanitarian"])

    # add the locations
    for params in [
            ["#adm1+name", "admin1"],
            ["#adm2+name", "admin2"],
            ["#loc+name", "unclassified"],
    ]:
        locname = row.get(params[0])
        if locname:
            location = lookup_location(locname)
            # For 3W, must match the stated admin level
            if location and not location.get("skip", False):
                add_unique(location["name"], data["locations"][location["level"]])
                if "admin1" in location:
                    add_unique(location["admin1"], data["locations"]["admin1"])
                if "admin2" in location:
                    add_unique(location["admin2"], data["locations"]["admin2"])
                if params[1] != location["level"] and params[1] != "unclassified" and locname != "Banadir":
                    print("Mismatch {}, {}: {}".format(params[1], location["level"], locname), file=sys.stderr)

    # add modality (e.g. for cash programming)
    modality = normalise_string(row.get("#modality"))
    if modality and not is_empty(modality):
        data["modalities"].append(modality)

    # add intended targeted
    for params in [
            ["#targeted+ind+all", "total_individuals"],
            ["#targeted+hh+all", "total_households"],
            ["#targeted+f+adults", "women"],
            ["#targeted+m+adults", "men"],
            ["#targeted+f+children", "girls"],
            ["#targeted+m+children", "boys"],
    ]:
        try:
            s = normalise_string(row.get(params[0]))
            if not is_empty(s):
                v = int(s)
                data["targeted"][params[1]] = v
        except:
            pass


    # Generate pseudo-identifier
    data["identifier"] = make_pseudo_identifier(data)

    return data

    

def fetch_3w(filenames):
    """ Fetch 3W data from all the filenames provided """

    result = []
    for filename in filenames:
        for row in hxl.data(filename, allow_local=True):
            data = make_activity(row)
            result.append(data)
    return result


#
# Script entry point
#

if __name__ == "__main__":
    data = fetch_3w(sys.argv[1:])
    print("Found {} 3W activities".format(len(data)), file=sys.stderr)
    print(json.dumps(data))

# end
