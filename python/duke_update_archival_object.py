import requests
import json
import csv
import os

#This Script Works!! - Noah

# This script will create a new digital object and link it as an instance to an existing archival object
# This was written under the assumption that you might have a csv (or similar), exported from ASpace or
# compiled from an ASpace exported EAD, with an existing archival object's ref_id. Using only the ref_id,
# this will use the ASpace API to search for the existing archival object, retrieve its URI, store the archival
# object's JSON, create a new digital object using the title from the archival object and an identifier (also from the CSV),
# grab the URI for the newly created digital object, add the link as an instance to the archival object JSON,
# and repost the archival object to ASpace using the update archival object endpoint

# The hypothetical 5 column csv might look something like this:
# [Container number], [Component title], [ASpace ref_id], [an identifier], [uri to the digital object]
# Columns 3-5 are used in this script

# The archival_object_csv will be your starting csv with the ASpace ref_id of the archival object's to be updated,
# the identifier to be used in the newly created digital object (could be a barcode, a random string, etc) and the uri
# to the digital object that will be added as a file_uri in the ArchivesSpace digital object record
archival_object_csv = os.path.normpath("c:/users/nh48/desktop/rush_test/ben_rush_digguide.txt")

# The updated_archival_object_csv will be an updated csv that will be created at the end of this script, containing all of the same
# information as the starting csv, plus the ArchivesSpace uris for the archival and digital objects
updated_archival_object_csv = os.path.normpath("c:/users/nh48/desktop/rush_test/ben_rush_digguide_with_uris.csv")

# Modify your ArchivesSpace backend url, username, and password as necessary
aspace_url = 'http://localhost:8089' #Backend URL for ASpace
username= 'admin'
password = 'admin'

auth = requests.post(aspace_url+'/users/'+username+'/login?password='+password).json()
session = auth["session"]
headers = {'X-ArchivesSpace-Session':session}

#Modified for TSV input, which is default output of aspace_dig_guide_creator.xsl
with open(archival_object_csv,'rb') as tsvin, open(updated_archival_object_csv,'wb') as csvout:
    tsvin = csv.reader(tsvin, delimiter='\t')
    next(tsvin, None) #ignore header row
    csvout = csv.writer(csvout)
    for row in tsvin:

#Original code below assumes CSV input format
#with open(archival_object_csv,'rb') as csvfile:
#    reader = csv.reader(csvfile)
#    next(reader, None)
#    for row in reader:

        # Use an identifier and a file_uri from the csv to create the digital object
        # If you don't have specific identifiers and just want a random string,
        # you could import uuid up top and do something like 'identifier = uuid.uuid4()'
        identifier = row[13] #column 14 in TSV, first column is column 0
        file_uri = row[14] #column 15 in TSV

        #Set file version use statement values (image-service, audio-streaming, etc.)
        file_version_use_statement = 'image-service'

        # Grab the archival object's ArchivesSpace ref_id from the csv
        ref_id = row[2] #column 3

        print ref_id

        # Search ASpace for the ref_id
        search = requests.get(aspace_url+'/repositories/2/search?page=1&q='+ref_id,headers=headers).json() #change repository number as needed


        # Grab the archival object uri from the search results
        archival_object_uri = search['results'][0]['uri']

        print archival_object_uri

        # Submit a get request for the archival object and store the JSON
        archival_object_json = requests.get(aspace_url+archival_object_uri,headers=headers).json()

        # Continue only if the search-returned archival object's ref_id matches our starting ref_id, just to be safe
        if archival_object_json['ref_id'] == ref_id:

            # Add the archival object uri to the row from the csv to write it out at the end
            row.append(archival_object_uri)

            # Reuse the display string from the archival object as the digital object title
            # Note: a more sophisticated way of doing this would be to add the title and dates from the
            # archival object separately into the appropriate title and date records in the digital object
            # This also does not copy over any notes from the archival object
            display_string = archival_object_json['display_string']

            # Form the digital object JSON using the display string from the archival object and the identifier and the file_uri from the csv
            dig_obj = {'title':display_string,'digital_object_id':identifier,'file_versions':[{'file_uri':file_uri,'use_statement':file_version_use_statement}]}
            dig_obj_data = json.dumps(dig_obj)

            # Post the digital object
            dig_obj_post = requests.post(aspace_url+'/repositories/2/digital_objects',headers=headers,data=dig_obj_data).json()

            print 'Digital Object Status:', dig_obj_post['status']

            # Grab the digital object uri
            dig_obj_uri = dig_obj_post['uri']

            print 'Digital Object URI:', dig_obj_uri

            # Add the digital object uri to the row from the csv to write it out at the end
            row.append(dig_obj_uri)

            # Build a new instance to add to the archival object, linking to the digital object
            dig_obj_instance = {'instance_type':'digital_object', 'digital_object':{'ref':dig_obj_uri}}

            # Append the new instance to the existing archival object record's instances
            archival_object_json['instances'].append(dig_obj_instance)
            archival_object_data = json.dumps(archival_object_json)

            # Repost the archival object
            archival_object_update = requests.post(aspace_url+archival_object_uri,headers=headers,data=archival_object_data).json()

            print archival_object_update

            # Write a new csv with all the info from the initial csv + the ArchivesSpace uris for the archival and digital objects
            with open(updated_archival_object_csv,'ab') as csvout:
                writer = csv.writer(csvout)
                writer.writerow(row)
