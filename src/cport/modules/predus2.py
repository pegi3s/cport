import io
import logging
import re
import sys
import tempfile
import time

import mechanicalsoup as ms
import pandas as pd
import requests

from cport.url import PREDUS2_URL

log = logging.getLogger("cportlog")

# Total wait (seconds) = WAIT_INTERVAL * NUM_RETRIES
WAIT_INTERVAL = 10  # seconds
NUM_RETRIES = 6
# first run of a protein takes longer, repeat runs use stored data


class Predus2:
    def __init__(self, pdb_id, chain_id):
        self.pdb_id = pdb_id
        self.chain_id = chain_id
        self.wait = WAIT_INTERVAL
        self.tries = NUM_RETRIES

    def submit(self):
        """Makes a submission to the PredUs2 server"""
        browser = ms.StatefulBrowser()
        browser.open(PREDUS2_URL, verify=False)

        input_form = browser.select_form(nr=0)
        input_form.set(name="pdbid", value=self.pdb_id)
        input_form.set(name="chain", value=self.chain_id)
        browser.submit_selected()

        # finds the submission url from the many links present on the page
        # https://regex101.com/r/Do6b51/1
        submission_url = re.findall(
            r"Result page:.*?\n.*?href=\"(.*?)\">Click to access results",
            str(browser.page),
        )[0]

        browser.close()

        return submission_url

    def retrieve_prediction_link(self, url=None, page_text=None):
        """Waits until the prediction has finished and returns url for results"""
        browser = ms.StatefulBrowser()

        if page_text:
            # used for testing
            browser.open_fake_page(page_text=page_text)
        else:
            browser.open(url, verify=False)

        completed = False
        while not completed:
            # Check if the result page exists
            match = re.search(r"PredUs2.0 result file:", str(browser.page))
            if match:
                completed = True
            else:
                # still running, wait a bit
                log.debug(f"Waiting for PredUs2 to finish... {self.tries}")
                time.sleep(self.wait)
                browser.refresh()
                self.tries -= 1

            if self.tries == 0:
                # if tries is 0, then the server is not responding
                log.error(f"PredUs2 server is not responding, url was {url}")
                sys.exit()

        final_url = f"https://honiglab.c2b2.columbia.edu/hfpd/tmp/{self.pdb_id}_{self.chain_id.capitalize()}.pd2.txt"

        browser.close()

        return final_url

    @staticmethod
    def download_result(download_link):
        """Download the results while avoiding SSL errors"""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.name = requests.get(download_link, verify=False).content

        return temp_file.name

    def parse_prediction(self, url=None, test_file=None):
        """Takes the results extracts the active and passive residue predictions"""
        prediction_dict = {"active": [], "passive": []}

        if test_file:
            # for testing purposes
            final_predictions = pd.read_csv(
                test_file,
                delim_whitespace=True,
                header=0,
                names=["Residue", "Score"],
            )
        else:
            file = self.download_result(url)
            final_predictions = pd.read_csv(
                io.StringIO(file.decode("utf-8")),
                delim_whitespace=True,
                header=0,
                names=["Residue", "Score"],
            )

        for row in final_predictions.itertuples():
            if row.Score >= 0:  # positive score indicates potential for interaction
                prediction_dict["active"].append(row.Residue)
            elif row.Score < 0:
                prediction_dict["passive"].append(row.Residue)

        return prediction_dict

    def run(self, test=False):
        """Execute the PredUs2 prediction."""
        log.info("Running PredUs2")
        log.info(f"Will try {self.tries} times waiting {self.wait}s between tries")

        submitted_url = self.submit()
        prediction_url = self.retrieve_prediction_link(url=submitted_url)
        self.prediction_dict = self.parse_prediction(url=prediction_url)

        return self.prediction_dict