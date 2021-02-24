import requests
from urllib3 import encode_multipart_formdata
from tools import pdb, predictors
import os

def run(input_params, main_dir,pdb_name):
    url = "http://bioinfo41.weizmann.ac.il/promate-bin/processBSF.cgi"
    name = input_params.name
    pdb_string = input_params.pdb_file.as_string

    file = {'fileup': (name, pdb_string, 'text/plan'),
            'pdbId': "dmmy",
            'chain': input_params.chain_id,
            'scConf': 1,
            'sc_init': 0,
            'outFormat': 'cbOutAAFull'}

    temp_dir = os.path.join(main_dir, "temp")
    temp_file = os.path.join(temp_dir, "promate.status")
    print("Promate: Start", file=open(temp_file, "a"))

    (content, header) = encode_multipart_formdata(file)
    req = requests.post(url, data=content, headers={'Content-Type': header})
    print("Promate: Processing", file=open(temp_file, "a"))
    if "href" not in req.text:
        print(f"Promate: Failed: {url}", file=open(temp_file, "a"))
        return predictors.Predictor(pdb=input_params.pdb_file, success=False)
    else:
        temp_url = req.url

        temp_url = temp_url[:temp_url.rfind('/')]

        results_url = temp_url + "/BSFout.AA.full.pdb"

        results_pdb = pdb.from_url(results_url,
                                   name=f"{pdb_name}_ProMate",
                                   main_dir=main_dir)
        print("Promate: Finished successfully", file=open(temp_file, "a"))
        return predictors.Predictor(pdb=results_pdb,name="ProMate", success=True)
